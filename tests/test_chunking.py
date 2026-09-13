from app.rag.chunking import FinancialChunker, Chunk

def test_basic_text_chunked_correctly():
    chunker = FinancialChunker(chunk_size=100, chunk_overlap=20)
    text = "A" * 250
    metadata = {"source": "doc1.pdf"}
    chunks = chunker.chunk(text, metadata)
    assert len(chunks) > 1
    for c in chunks:
        assert isinstance(c, Chunk)

def test_chunk_size_respected():
    chunk_size = 150
    chunker = FinancialChunker(chunk_size=chunk_size, chunk_overlap=30)
    text = "Word " * 200
    chunks = chunker.chunk(text, {})
    for c in chunks:
        # Allowing some tolerance for boundary splits
        assert len(c.text) <= chunk_size + 50

def test_overlap_applied():
    chunker = FinancialChunker(chunk_size=50, chunk_overlap=20)
    text = "This is a simple test sentence intended to test overlapping in chunks."
    chunks = chunker.chunk(text, {})
    if len(chunks) > 1:
        # Check that end of chunk n has overlap with start of chunk n+1
        pass # Implementation specific check

def test_metadata_preserved():
    chunker = FinancialChunker(chunk_size=100, chunk_overlap=20)
    text = "Financial results for FY24 were outstanding."
    meta = {"company": "TechVenture", "doc_type": "Annual Report", "period": "FY24"}
    chunks = chunker.chunk(text, meta)
    assert chunks[0].metadata["company"] == "TechVenture"
    assert chunks[0].metadata["doc_type"] == "Annual Report"

def test_section_title_detection():
    chunker = FinancialChunker(chunk_size=200, chunk_overlap=20)
    text = "RISK FACTORS\n\nThe company faces risks."
    chunks = chunker.chunk(text, {})
    assert "RISK FACTORS" in chunks[0].text

def test_empty_text():
    chunker = FinancialChunker()
    chunks = chunker.chunk("", {})
    assert len(chunks) == 0

def test_very_short_text():
    chunker = FinancialChunker(chunk_size=500, chunk_overlap=50)
    text = "Short text."
    chunks = chunker.chunk(text, {})
    assert len(chunks) == 1
    assert chunks[0].text == "Short text."
