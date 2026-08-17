from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(500))
    file_type = Column(String(10))  # e.g., pdf, docx, txt
    file_size_bytes = Column(Integer)
    
    # Financial context metadata
    company_name = Column(String(255))
    ticker = Column(String(20))
    document_type = Column(String(100))  # e.g., annual_report, earnings_report
    reporting_period = Column(String(100))  # e.g., Q3 FY2024
    fiscal_year = Column(String(20))
    
    # Processing status
    status = Column(String(50), default="processing")  # processing, ready, failed
    num_chunks = Column(Integer, default=0)
    error_message = Column(String(1000))
    
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)  # position in document
    content = Column(Text, nullable=False)  # the actual chunk text
    
    # BGE-small-en-v1.5 produces 384-dimensional vectors
    embedding = Column(Vector(384))
    
    page_number = Column(Integer)  # page where this chunk starts
    section_title = Column(String(500))  # detected heading if any
    
    # Denormalized fields for fast retrieval filtering
    company_name = Column(String(255), index=True)
    document_type = Column(String(100))
    reporting_period = Column(String(100))
    filename = Column(String(255))
    
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500))  # auto-generated from first question
    document_ids = Column(JSON)  # list of document IDs in scope (None = all user docs)
    
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    sources = Column(JSON)  # list of citation dicts for assistant messages
    
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    chat = relationship("Chat", back_populates="messages")
