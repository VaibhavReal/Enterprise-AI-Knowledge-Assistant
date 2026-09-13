from app.rag.prompts import build_rag_prompt, format_citations

def test_citations_come_from_metadata():
    chunks = [
        {"text": "Data 1", "metadata": {"document_name": "report.pdf", "page_number": 5}},
        {"text": "Data 2", "metadata": {"document_name": "presentation.pdf", "page_number": 12}}
    ]
    citations = format_citations(chunks)
    assert len(citations) == 2
    assert citations[0]["filename"] == "report.pdf"
    assert citations[0]["page_number"] == 5
    assert citations[1]["filename"] == "presentation.pdf"
    assert citations[1]["page_number"] == 12

def test_prompt_includes_context_chunks():
    chunks = [{"text": "Revenue was $10M", "metadata": {}}]
    messages = build_rag_prompt("What was revenue?", chunks)
    user_message = next(m["content"] for m in messages if m["role"] == "user")
    assert "Revenue was $10M" in user_message

def test_financial_system_prompt_mentions_no_fabrication():
    messages = build_rag_prompt("Hi", [])
    system_message = next(m["content"] for m in messages if m["role"] == "system")
    assert "fabricat" in system_message.lower() or "invent" in system_message.lower()

def test_number_preservation_in_context():
    chunks = [{"text": "Net income: ₹1,250 crore", "metadata": {}}]
    messages = build_rag_prompt("Income?", chunks)
    user_message = next(m["content"] for m in messages if m["role"] == "user")
    assert "₹1,250 crore" in user_message
