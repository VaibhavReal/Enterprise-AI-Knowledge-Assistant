from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class DocumentMetadataInput(BaseModel):
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    document_type: Optional[str] = None
    reporting_period: Optional[str] = None
    fiscal_year: Optional[str] = None

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    document_type: Optional[str] = None
    reporting_period: Optional[str] = None
    fiscal_year: Optional[str] = None
    status: str
    num_chunks: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int

class ChunkResponse(BaseModel):
    id: int
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None
    reporting_period: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
