"""
Dense retrieval using pgvector cosine similarity search.

This module handles the vector similarity search part of the RAG pipeline.
Given a query embedding, we find the most semantically similar document chunks
stored in PostgreSQL using the pgvector extension.
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.models import DocumentChunk, Document
from app.utils.logging_config import get_logger, timer

logger = get_logger(__name__)


class DenseRetriever:
    """
    Performs semantic similarity search using BGE embeddings stored in pgvector.

    pgvector supports three distance operators:
    - <-> L2 (Euclidean) distance
    - <=> cosine distance  <- we use this
    - <#> negative inner product

    Why cosine similarity:
    BGE embeddings are L2-normalized, meaning they all have unit length.
    For normalized vectors, cosine similarity and dot product give equivalent
    rankings, and cosine similarity is bounded in [-1, 1] which makes it
    easy to interpret.

    Security note:
    We always filter by user_id via the document ownership join.
    A user can never retrieve chunks from another user's documents.
    """

    def retrieve(
        self,
        query_embedding: list[float],
        db: Session,
        user_id: int,
        top_k: int = 20,
        document_ids: Optional[list[int]] = None,
        company_name: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Find the top_k most similar chunks to the query embedding.

        Args:
            query_embedding: The 384-dim vector from BGE embedding of the query
            db: SQLAlchemy session
            user_id: The authenticated user's ID (for security filtering)
            top_k: How many candidates to return before reranking
            document_ids: If provided, only search within these specific documents
            company_name: Optional filter by company
            document_type: Optional filter by document type

        Returns:
            List of dicts, each with:
            - 'chunk': DocumentChunk ORM object
            - 'dense_score': float in [0, 1] (higher = more similar)
        """
        with timer(logger, f"dense retrieval (top_k={top_k})"):
            # Convert the Python list to a PostgreSQL vector literal
            # pgvector accepts arrays formatted as '[0.1, 0.2, ...]'
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            # Build the base query using raw SQL for pgvector operators
            # We join DocumentChunk -> Document -> User to enforce ownership
            # The cosine distance (<=> operator) returns 0 for identical vectors,
            # 2 for completely opposite vectors. We convert to similarity: 1 - distance/2
            # Actually pgvector's cosine distance is in [0, 2], so similarity = 1 - distance
            # For normalized vectors it's in [0, 1] so similarity = 1 - distance

            sql = text("""
                SELECT 
                    dc.id,
                    dc.document_id,
                    dc.chunk_index,
                    dc.content,
                    dc.page_number,
                    dc.section_title,
                    dc.company_name,
                    dc.document_type,
                    dc.reporting_period,
                    dc.filename,
                    1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity_score
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.user_id = :user_id
                  AND d.status = 'ready'
                  {doc_filter}
                  {company_filter}
                  {type_filter}
                ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """.format(
                doc_filter="AND dc.document_id = ANY(:document_ids)" if document_ids else "",
                company_filter="AND dc.company_name ILIKE :company_name" if company_name else "",
                type_filter="AND dc.document_type = :document_type" if document_type else "",
            ))

            params = {
                "embedding": embedding_str,
                "user_id": user_id,
                "top_k": top_k,
            }
            if document_ids:
                params["document_ids"] = document_ids
            if company_name:
                params["company_name"] = f"%{company_name}%"
            if document_type:
                params["document_type"] = document_type

            rows = db.execute(sql, params).fetchall()

            if not rows:
                logger.info(f"Dense retrieval: no results for user_id={user_id}")
                return []

            # Fetch full DocumentChunk objects to include in results
            chunk_ids = [row.id for row in rows]
            chunks_by_id = {
                chunk.id: chunk
                for chunk in db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()
            }

            results = []
            for row in rows:
                chunk = chunks_by_id.get(row.id)
                if chunk:
                    results.append({
                        "chunk": chunk,
                        "dense_score": float(row.similarity_score),
                    })

            logger.info(f"Dense retrieval returned {len(results)} chunks")
            return results
