from __future__ import annotations

# This is the most important file for financial accuracy.
# The system prompt instructs the LLM on how to handle financial information.

FINANCIAL_RAG_SYSTEM_PROMPT = """
You are a financial research assistant. Your job is to answer questions about financial 
documents that have been provided to you as context.

CRITICAL RULES:
1. ONLY use information from the provided document excerpts to answer questions.
2. If the answer is not in the provided excerpts, clearly state: 
   'I could not find information about this in the retrieved document sections.'
3. NEVER fabricate financial numbers, percentages, dates, or metrics.
4. Preserve financial numbers exactly as they appear in the source:
   - '₹1,250 crore' must stay '₹1,250 crore', not '1250' or '$1,250'
   - '12.3%' must stay '12.3%', not '12%' or '0.123'
   - Preserve currency symbols, units, and periods exactly
5. Always attribute information to its source (document name and page).
6. Distinguish between:
   a) Facts directly stated in the document (use 'The document states...')
   b) Calculations you derive from document values (use 'Based on the figures above...')
   c) General financial concepts (use 'In general...' but keep this brief)
7. For risk factors, present them as reported by management, not as your assessment.
8. Do NOT provide investment advice or recommendations.

DISCLAIMER: This system is for financial research and educational purposes only 
and does not constitute investment advice.
"""

def build_rag_prompt(
    query: str,
    retrieved_chunks: list[dict],
    conversation_history: list[dict] = None,
) -> list[dict]:
    """
    Builds the complete message list for the LLM.
    
    Structure:
    - System message with financial research instructions
    - Conversation history (last N messages for context)
    - Context block with retrieved chunks, numbered and cited
    - User question
    """
    messages = [{"role": "system", "content": FINANCIAL_RAG_SYSTEM_PROMPT}]
    
    # Add conversation history
    if conversation_history:
        for msg in conversation_history:
            messages.append(msg)
        
    # Build context block
    context_blocks = []
    for i, item in enumerate(retrieved_chunks):
        if isinstance(item, dict) and 'chunk' in item:
            chunk = item['chunk']
        else:
            chunk = item
        
        # Handle dict or object
        if isinstance(chunk, dict):
            meta = chunk.get('metadata', {})
            filename = chunk.get('filename') or meta.get('document_name') or meta.get('filename') or 'Unknown Document'
            page_num = chunk.get('page_number') or meta.get('page_number') or 'N/A'
            section = chunk.get('section_title') or meta.get('section_title') or 'General'
            content = chunk.get('content') or chunk.get('text') or ''
        else:
            filename = getattr(chunk, 'filename', 'Unknown Document')
            page_num = getattr(chunk, 'page_number', 'N/A')
            section = getattr(chunk, 'section_title', 'General')
            content = getattr(chunk, 'content', getattr(chunk, 'text', ''))
        
        block = f"[{i+1}] Source: {filename}, Page {page_num}, Section: {section}\nContent: \"{content}\""
        context_blocks.append(block)
        
    context_text = "\n\n".join(context_blocks)
    
    # Final user message combining context and query
    user_prompt = f"""
Here are the relevant document excerpts for your research:

{context_text}

Question: {query}
"""
    
    messages.append({"role": "user", "content": user_prompt})
    
    return messages

def format_citations(retrieved_chunks: list[dict]) -> list[dict]:
    """
    Generates citation objects from retrieved chunk metadata.
    
    IMPORTANT: Citations come from actual chunk metadata, never from LLM output.
    """
    citations = []
    for i, item in enumerate(retrieved_chunks):
        if isinstance(item, dict) and 'chunk' in item:
            chunk = item['chunk']
            score = item.get('rerank_score') or item.get('hybrid_score') or item.get('dense_score') or 0.85
        else:
            chunk = item
            score = getattr(item, 'score', 0.85) if hasattr(item, 'score') else 0.85

        if isinstance(chunk, dict):
            meta = chunk.get('metadata', {})
            filename = chunk.get('filename') or meta.get('document_name') or meta.get('filename') or 'Unknown'
            page_number = chunk.get('page_number') or meta.get('page_number')
            section_title = chunk.get('section_title') or meta.get('section_title')
            doc_id = chunk.get('document_id') or meta.get('document_id')
            chunk_idx = chunk.get('chunk_index') or meta.get('chunk_index') or i
            content = chunk.get('content') or chunk.get('text') or ''
        else:
            filename = getattr(chunk, 'filename', 'Unknown')
            page_number = getattr(chunk, 'page_number', None)
            section_title = getattr(chunk, 'section_title', None)
            doc_id = getattr(chunk, 'document_id', None)
            chunk_idx = getattr(chunk, 'chunk_index', i)
            content = getattr(chunk, 'content', getattr(chunk, 'text', ''))

        snippet = content.strip()
        if len(snippet) > 250:
            snippet = snippet[:250] + "..."

        citations.append({
            "id": i + 1,
            "filename": filename,
            "document_name": filename,
            "page_number": page_number,
            "section_title": section_title,
            "document_id": doc_id,
            "chunk_index": chunk_idx,
            "relevance_score": float(score),
            "content_snippet": snippet,
            "citation_str": f"{filename} (Page {page_number})" if page_number else filename
        })
        
    return citations

