from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
import os

from app.db.database import get_db
from app.db.models import User, Document
from app.schemas.document import DocumentResponse
from app.core.security import get_current_user
from app.services.document_service import DocumentIngestionService
from app.services.financial_service import FinancialMetadataExtractor

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    company_name: Optional[str] = Form(None),
    ticker: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    reporting_period: Optional[str] = Form(None),
    fiscal_year: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a financial document.
    Accepts PDF, DOCX, TXT.
    Metadata can be provided by user; anything not provided will be auto-extracted.
    """
    user_metadata = {
        "company_name": company_name,
        "ticker": ticker,
        "document_type": document_type,
        "reporting_period": reporting_period,
        "fiscal_year": fiscal_year,
    }
    
    final_metadata = {k: v for k, v in user_metadata.items() if v is not None}
    
    service = DocumentIngestionService()
    doc = await service.ingest(
        file=file,
        user_id=current_user.id,
        metadata=final_metadata,
        db=db
    )
    
    return doc

@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    company_name: Optional[str] = None,
    document_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents belonging to current user, with optional filters."""
    query = db.query(Document).filter(Document.user_id == current_user.id)
    
    if company_name:
        query = query.filter(Document.company_name.ilike(f"%{company_name}%"))
    if document_type:
        query = query.filter(Document.document_type == document_type)
        
    return query.all()

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific document. 404 if not found or belongs to another user."""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a document and all its chunks.
    Also removes the uploaded file from disk.
    Cascade delete handles the DocumentChunk records.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Delete file from disk
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass
            
    db.delete(doc)
    db.commit()
    return None
