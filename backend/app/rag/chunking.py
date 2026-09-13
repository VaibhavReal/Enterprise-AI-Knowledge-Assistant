from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Chunk:
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    document_id: Optional[int] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None
    reporting_period: Optional[str] = None
    filename: Optional[str] = None

    @property
    def text(self) -> str:
        return self.content

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "section_title": self.section_title,
            "document_id": self.document_id,
            "company_name": self.company_name,
            "company": self.company_name,
            "document_type": self.document_type,
            "doc_type": self.document_type,
            "reporting_period": self.reporting_period,
            "period": self.reporting_period,
            "filename": self.filename,
        }

class FinancialChunker:
    """
    Splits financial documents into overlapping text chunks.
    
    Why chunking is needed:
    - LLMs have context window limits
    - Vector similarity search works better on focused, paragraph-level chunks
    - Smaller chunks allow pinpointing exactly where a fact appears in the document
    """
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(self, text: str, metadata: Optional[dict] = None) -> list[Chunk]:
        """
        Convenience method to chunk raw text directly.
        """
        if not text or not text.strip():
            return []
            
        metadata = metadata or {}
        chunks = []
        raw_chunks = self._split_into_chunks(text.strip())
        
        # Check section title from text
        section = self._detect_section_title(text)
        
        for idx, pc in enumerate(raw_chunks):
            chunks.append(Chunk(
                content=pc,
                chunk_index=idx,
                page_number=metadata.get("page_number"),
                section_title=section or metadata.get("section_title"),
                document_id=metadata.get("document_id"),
                company_name=metadata.get("company_name") or metadata.get("company"),
                document_type=metadata.get("document_type") or metadata.get("doc_type"),
                reporting_period=metadata.get("reporting_period") or metadata.get("period"),
                filename=metadata.get("filename") or metadata.get("source", "unknown")
            ))
        return chunks

    def chunk_pages(self, pages: list, document_id: int, document_metadata: dict) -> list[Chunk]:
        """
        Takes parsed pages (list of ParsedPage from file_parser) and produces chunks.
        """
        chunks = []
        chunk_idx = 0
        current_section = None
        
        for page in pages:
            page_text = getattr(page, 'text', '') or getattr(page, 'content', '')
            if not page_text:
                continue
                
            page_num = getattr(page, 'page_number', None)
            
            # Simple paragraph split
            paragraphs = re.split(r'\n\s*\n', page_text)
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                    
                # Detect section title
                detected_title = self._detect_section_title(para)
                if detected_title:
                    current_section = detected_title
                    
                # Split large paragraphs into chunks
                para_chunks = self._split_into_chunks(para)
                for pc in para_chunks:
                    chunks.append(Chunk(
                        content=pc,
                        chunk_index=chunk_idx,
                        page_number=page_num,
                        section_title=current_section,
                        document_id=document_id,
                        company_name=document_metadata.get('company_name'),
                        document_type=document_metadata.get('document_type'),
                        reporting_period=document_metadata.get('reporting_period'),
                        filename=document_metadata.get('filename', 'unknown')
                    ))
                    chunk_idx += 1
                    
        return chunks
    
    def _detect_section_title(self, text: str) -> Optional[str]:
        """
        Detect section title heuristic for financial documents.
        """
        lines = text.split('\n')
        if not lines:
            return None
            
        first_line = lines[0].strip()
        if len(first_line) > 80:
            return None
            
        if first_line.isupper() or first_line.istitle():
            return first_line
            
        financial_keywords = ['Revenue', 'Risk', 'Debt', 'Assets', 'Liabilities', 'Equity', 'Income', 'Cash Flow', 'Operations', 'Financial']
        if any(kw.lower() in first_line.lower() for kw in financial_keywords):
            return first_line
            
        return None
    
    def _split_into_chunks(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.
        """
        if len(text) <= self.chunk_size:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
                
            # Try to find a good breaking point (period, newline, space)
            break_point = -1
            for sep in ['\n\n', '\n', '. ', ' ']:
                idx = text.rfind(sep, start, end)
                if idx != -1 and (end - idx) < 100:
                    break_point = idx + len(sep)
                    break
                    
            if break_point == -1:
                break_point = end
                
            chunks.append(text[start:break_point].strip())
            start = break_point - self.chunk_overlap
            
            if start <= 0:
                start = break_point
                
        return chunks
