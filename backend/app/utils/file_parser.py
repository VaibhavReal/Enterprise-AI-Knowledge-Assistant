"""
File parser utilities for PDF, DOCX, and TXT financial documents.

Each parser returns a list of ParsedPage objects — one per logical page.
Text is cleaned to remove noise while preserving financial structure.

Important notes on financial document parsing:
- Tables: PyMuPDF extracts table text as space-separated rows. The tabular
  structure (rows/columns) is NOT preserved. This is a known limitation.
- Footnotes: May be separated from their in-text reference markers.
- Scanned PDFs: Will produce empty or garbled text. OCR is not included
  in the default path; see docs/LIMITATIONS.md for details.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

import fitz  # PyMuPDF
from docx import Document as DocxDocument

from app.utils.logging_config import get_logger, timer

logger = get_logger(__name__)


@dataclass
class ParsedPage:
    """Represents one logical page of extracted text from a document."""
    page_number: int
    text: str
    metadata: dict = field(default_factory=dict)


def clean_text(text: str) -> str:
    """
    Clean extracted text while preserving financial structure.

    What we remove:
    - Null bytes (common in some PDF extractions)
    - Excessive horizontal whitespace
    - More than 2 consecutive newlines

    What we KEEP:
    - Single and double newlines (paragraph boundaries)
    - All numbers, currency symbols (₹, $, £, €), percentages
    - Commas in numbers (1,250 crore must stay 1,250 crore)
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")

    # Collapse multiple spaces into one (but not newlines)
    text = re.sub(r"[ \t]+", " ", text)

    # Strip trailing spaces from each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse 3+ consecutive newlines to 2 (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def parse_pdf(file_path: str) -> List[ParsedPage]:
    """
    Extract text from a PDF using PyMuPDF (fitz), one page at a time.

    Why PyMuPDF:
    - Fast and memory-efficient for large reports
    - Good text extraction for digitally-created PDFs
    - Page-level extraction lets us preserve page number metadata

    Limitation: Scanned PDFs produce no text. For those, OCR would be needed.
    """
    pages = []
    with timer(logger, f"PDF extraction: {file_path}"):
        try:
            doc = fitz.open(file_path)
            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                raw_text = page.get_text("text")
                cleaned = clean_text(raw_text)

                # Use 1-indexed page numbers for human readability
                pages.append(ParsedPage(
                    page_number=page_index + 1,
                    text=cleaned,
                    metadata={"source_type": "pdf"},
                ))
            doc.close()
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise ValueError(f"Failed to parse PDF: {e}")

    logger.info(f"Extracted {len(pages)} pages from PDF")
    return pages


def parse_docx(file_path: str) -> List[ParsedPage]:
    """
    Extract text from a DOCX file using python-docx.

    DOCX files have no native page boundaries, so we create synthetic pages
    by grouping every 50 paragraphs. This is an approximation.

    We also detect heading styles (Heading 1, Heading 2, etc.) and store
    the current heading in page metadata for section-aware retrieval.
    """
    pages = []
    PARAGRAPHS_PER_PAGE = 50

    with timer(logger, f"DOCX extraction: {file_path}"):
        try:
            doc = DocxDocument(file_path)
            current_page_lines = []
            current_heading = None
            page_num = 1

            for i, para in enumerate(doc.paragraphs):
                text = para.text.strip()
                if not text:
                    continue

                # Detect heading style for section tracking
                if para.style.name.startswith("Heading"):
                    current_heading = text

                current_page_lines.append(text)

                # Flush current page when limit reached or at end
                is_last = (i == len(doc.paragraphs) - 1)
                if len(current_page_lines) >= PARAGRAPHS_PER_PAGE or is_last:
                    page_text = "\n".join(current_page_lines)
                    pages.append(ParsedPage(
                        page_number=page_num,
                        text=clean_text(page_text),
                        metadata={
                            "source_type": "docx",
                            "last_heading": current_heading,
                        },
                    ))
                    current_page_lines = []
                    page_num += 1

        except Exception as e:
            logger.error(f"Failed to parse DOCX {file_path}: {e}")
            raise ValueError(f"Failed to parse DOCX: {e}")

    logger.info(f"Extracted {len(pages)} synthetic pages from DOCX")
    return pages


def parse_txt(file_path: str) -> List[ParsedPage]:
    """
    Extract text from a plain text file.

    We group content into synthetic pages of ~3000 characters, splitting
    on paragraph boundaries (double newlines) where possible.
    """
    pages = []
    PAGE_SIZE_CHARS = 3000

    with timer(logger, f"TXT extraction: {file_path}"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Split on paragraph boundaries
            paragraphs = content.split("\n\n")
            current_chunks = []
            current_len = 0
            page_num = 1

            for para in paragraphs:
                para_len = len(para)
                if current_len + para_len > PAGE_SIZE_CHARS and current_chunks:
                    page_text = "\n\n".join(current_chunks)
                    pages.append(ParsedPage(
                        page_number=page_num,
                        text=clean_text(page_text),
                        metadata={"source_type": "txt"},
                    ))
                    current_chunks = [para]
                    current_len = para_len
                    page_num += 1
                else:
                    current_chunks.append(para)
                    current_len += para_len

            # Flush remaining content
            if current_chunks:
                page_text = "\n\n".join(current_chunks)
                pages.append(ParsedPage(
                    page_number=page_num,
                    text=clean_text(page_text),
                    metadata={"source_type": "txt"},
                ))

        except Exception as e:
            logger.error(f"Failed to parse TXT {file_path}: {e}")
            raise ValueError(f"Failed to parse TXT: {e}")

    logger.info(f"Extracted {len(pages)} pages from TXT")
    return pages


def parse_document(file_path: str, file_type: str) -> List[ParsedPage]:
    """
    Dispatch file parsing to the correct handler based on file type.

    Args:
        file_path: Absolute path to the file on disk
        file_type: Extension without dot, e.g. 'pdf', 'docx', 'txt'

    Raises:
        ValueError: If the file type is not supported
    """
    file_type = file_type.lower().lstrip(".")

    if file_type == "pdf":
        return parse_pdf(file_path)
    elif file_type == "docx":
        return parse_docx(file_path)
    elif file_type == "txt":
        return parse_txt(file_path)
    else:
        raise ValueError(
            f"Unsupported file type '{file_type}'. Supported: pdf, docx, txt"
        )
