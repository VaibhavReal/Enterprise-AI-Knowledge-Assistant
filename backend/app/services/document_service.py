"""
Document ingestion service.

Orchestrates the full pipeline:
Upload -> Validate -> Extract Text -> Clean -> Chunk -> Embed -> Store in PostgreSQL/pgvector

This service is intentionally separated from the API layer so that:
1. It can be tested independently of HTTP
2. The ingestion logic can later be moved to a background task (e.g., Celery)
   without changing the API layer

Current design: synchronous ingestion (runs during the HTTP request).
For large documents (100+ pages), this will make the upload endpoint slow.
See FUTURE_SCOPE.md for the async ingestion design using background tasks.
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.core.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.rag.chunking import FinancialChunker
from app.services.financial_service import FinancialMetadataExtractor
from app.utils.file_parser import parse_document
from app.utils.logging_config import get_logger, timer

logger = get_logger(__name__)


class DocumentIngestionService:
    """
    Runs the complete document ingestion pipeline step by step.
    Each step is clearly separated so any failures are easy to diagnose.
    """

    async def ingest(
        self,
        file: UploadFile,
        user_id: int,
        metadata: dict,
        db: Session,
    ) -> Document:
        """
        Full ingestion pipeline. Creates a Document record in the database
        and processes the file into searchable chunks with embeddings.

        Args:
            file: The uploaded file from FastAPI
            user_id: Authenticated user's ID
            metadata: User-provided metadata (company_name, ticker, etc.)
            db: SQLAlchemy database session

        Returns:
            The completed Document ORM object (status='ready' on success)

        Raises:
            HTTPException: For validation errors or unrecoverable processing failures
        """
        settings = get_settings()

        # --- Step 1: Validate the file ---
        self._validate_file(
            file,
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
            allowed_extensions=settings.ALLOWED_EXTENSIONS,
        )

        # --- Step 2: Save file to disk ---
        upload_dir = os.path.join(settings.UPLOAD_DIR, f"user_{user_id}")
        file_path = await self._save_file(file, upload_dir)
        file_type = Path(file.filename or "").suffix.lstrip(".").lower()

        # --- Step 3: Create a Document record with status='processing' ---
        # We create this early so the user can see the document appearing
        # in the UI even while it's being processed.
        doc = Document(
            user_id=user_id,
            filename=os.path.basename(file_path),
            original_filename=file.filename,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=os.path.getsize(file_path),
            company_name=metadata.get("company_name"),
            ticker=metadata.get("ticker"),
            document_type=metadata.get("document_type"),
            reporting_period=metadata.get("reporting_period"),
            fiscal_year=metadata.get("fiscal_year"),
            status="processing",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        logger.info(f"Created Document record id={doc.id} for user {user_id}")

        try:
            # --- Step 4: Extract text from the document ---
            with timer(logger, f"text extraction for document {doc.id}"):
                pages = parse_document(file_path, file_type)

            if not pages:
                raise ValueError("No text could be extracted from the document. The file may be empty or unsupported.")

            total_chars = sum(len(p.text) for p in pages)
            logger.info(f"Extracted {len(pages)} pages, {total_chars} total characters")

            # --- Step 5: Auto-extract metadata from first page if not provided ---
            extractor = FinancialMetadataExtractor()
            first_page_text = pages[0].text if pages else ""
            auto_metadata = extractor.extract_from_text(first_page_text, file.filename or "")
            final_metadata = extractor.merge_with_user_provided(auto_metadata, metadata)

            # Update document with any auto-extracted metadata
            if not doc.company_name and final_metadata.get("company_name"):
                doc.company_name = final_metadata["company_name"]
            if not doc.ticker and final_metadata.get("ticker"):
                doc.ticker = final_metadata["ticker"]
            if not doc.document_type and final_metadata.get("document_type"):
                doc.document_type = final_metadata["document_type"]
            if not doc.reporting_period and final_metadata.get("reporting_period"):
                doc.reporting_period = final_metadata["reporting_period"]
            if not doc.fiscal_year and final_metadata.get("fiscal_year"):
                doc.fiscal_year = str(final_metadata["fiscal_year"])


            # --- Step 6: Chunk the document ---
            with timer(logger, f"chunking document {doc.id}"):
                chunker = FinancialChunker(
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP,
                )
                chunks = chunker.chunk_pages(
                    pages=pages,
                    document_id=doc.id,
                    document_metadata={
                        "company_name": doc.company_name,
                        "document_type": doc.document_type,
                        "reporting_period": doc.reporting_period,
                        "filename": doc.original_filename,
                    },
                )

            logger.info(f"Generated {len(chunks)} chunks for document {doc.id}")

            if not chunks:
                raise ValueError("Document produced no text chunks. The content may be too short or purely images.")

            # --- Step 7: Generate embeddings for all chunks ---
            embedding_service = get_embedding_service()
            chunk_texts = [c.content for c in chunks]

            with timer(logger, f"embedding {len(chunks)} chunks for document {doc.id}"):
                embeddings = embedding_service.encode_batch(chunk_texts, is_query=False)

            # --- Step 8: Store chunks and embeddings in PostgreSQL/pgvector ---
            with timer(logger, f"storing chunks in DB for document {doc.id}"):
                num_stored = self._store_chunks_with_embeddings(chunks, embeddings, doc.id, db)

            logger.info(f"Stored {num_stored} chunks with embeddings for document {doc.id}")

            # --- Step 9: Mark document as ready ---
            doc.status = "ready"
            doc.num_chunks = num_stored
            db.commit()
            db.refresh(doc)
            logger.info(f"Document {doc.id} ingestion complete: status=ready")

            return doc

        except HTTPException:
            raise  # Don't wrap HTTP exceptions
        except Exception as e:
            logger.error(f"Ingestion failed for document {doc.id}: {type(e).__name__}: {str(e)}")
            # Mark document as failed so the user knows something went wrong
            doc.status = "failed"
            doc.error_message = str(e)[:900]
            db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {str(e)[:200]}",
            )

    def _validate_file(
        self,
        file: UploadFile,
        max_size_mb: int,
        allowed_extensions: list,
    ) -> None:
        """
        Validate the uploaded file before processing.

        Checks:
        - File has a name and extension
        - Extension is in allowed list
        - Content type is reasonable (basic check)

        Note: We can't reliably check file size from UploadFile headers alone
        (Content-Length may not be set). Size is checked after saving to disk.
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")

        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' is not supported. Allowed types: {', '.join(allowed_extensions)}",
            )

    async def _save_file(self, file: UploadFile, upload_dir: str) -> str:
        """
        Save the uploaded file to disk with a UUID-prefixed name.

        We prefix with UUID to avoid filename collisions when the same
        user uploads files with identical names.
        """
        os.makedirs(upload_dir, exist_ok=True)

        # Use UUID prefix to avoid filename collisions
        safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
        # Sanitize: remove any path separators from the original filename
        safe_filename = safe_filename.replace("/", "_").replace("\\", "_")
        file_path = os.path.join(upload_dir, safe_filename)

        # Reset file position and write to disk
        await file.seek(0)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Validate size after saving
        settings = get_settings()
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            os.remove(file_path)
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {size_mb:.1f}MB. Maximum allowed: {settings.MAX_UPLOAD_SIZE_MB}MB",
            )

        logger.info(f"Saved file to {file_path} ({size_mb:.2f}MB)")
        return file_path

    def _store_chunks_with_embeddings(
        self,
        chunks: list,
        embeddings: list[list[float]],
        document_id: int,
        db: Session,
    ) -> int:
        """
        Bulk-insert all document chunks with their embeddings into PostgreSQL.

        We use bulk_save_objects instead of individual db.add() calls because:
        - For a 200-page report with 500+ chunks, individual inserts would be very slow
        - bulk_save_objects batches the INSERTs significantly reducing round-trips
        - Embeddings (384-dim vectors) are stored directly via pgvector's Vector column
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) doesn't match embedding count ({len(embeddings)})")

        db_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            db_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embedding,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                company_name=chunk.company_name,
                document_type=chunk.document_type,
                reporting_period=chunk.reporting_period,
                filename=chunk.filename,
            )
            db_chunks.append(db_chunk)

        db.bulk_save_objects(db_chunks)
        db.commit()
        return len(db_chunks)
