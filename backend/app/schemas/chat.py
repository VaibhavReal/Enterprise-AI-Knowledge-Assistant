from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class ChatCreate(BaseModel):
    title: Optional[str] = None
    document_ids: Optional[List[int]] = None

class ChatResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    document_ids: Optional[List[int]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    content: str
    document_ids: Optional[List[int]] = None

class Citation(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    chunk_index: int
    relevance_score: float
    content_snippet: str

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    sources: Optional[List[Citation]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatListResponse(BaseModel):
    items: List[ChatResponse]
    total: int
