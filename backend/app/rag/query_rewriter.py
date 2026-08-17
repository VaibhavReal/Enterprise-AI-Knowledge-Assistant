from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

class QueryRewriter:
    """
    Rewrites ambiguous follow-up questions into self-contained search queries.
    
    Why query rewriting:
    In multi-turn financial research, users often ask follow-up questions that
    depend on previous context:
    
    Example:
    Turn 1: 'What was Apple's revenue?'
    Turn 2: 'What about operating expenses?'  <- ambiguous!
    
    Without rewriting, 'What about operating expenses?' as a search query
    will miss the Apple/period context and retrieve irrelevant chunks.
    
    After rewriting: 'What were Apple's operating expenses in the reported period?'
    
    When NOT to rewrite:
    - First message in a chat (no context)
    - Self-contained questions ('What was Microsoft's Q3 2024 revenue?')
    - Questions that already contain company/period context
    
    Heuristics to detect ambiguous queries (before calling LLM):
    - Very short query (< 5 words)
    - Contains pronouns without clear referent (it, its, their, the company)
    - Contains 'what about', 'and', 'also', 'how about'
    - Contains relative terms without context ('same period', 'that year')
    """
    
    REWRITE_SYSTEM_PROMPT = """
You are a financial research assistant. Your task is to rewrite a follow-up question 
into a self-contained search query that can be used to retrieve relevant financial document chunks.

Rules:
- Only rewrite if the question is genuinely ambiguous without conversation context
- Preserve all specific financial terms, numbers, and periods mentioned
- Make the rewritten query specific and searchable
- Return ONLY the rewritten query, no explanation
- If the question is already self-contained, return it unchanged
"""
    
    def __init__(self, llm_service):
        # Takes the LLM service to call for rewriting
        self.llm = llm_service
    
    def should_rewrite(self, query: str, conversation_history: list[dict]) -> bool:
        """Quick heuristic check before calling the LLM."""
        if not conversation_history:
            return False
            
        words = query.lower().split()
        if len(words) < 5:
            return True
            
        ambiguous_terms = ['it', 'its', 'their', 'the company', 'this', 'that', 'same period', 'that year']
        ambiguous_phrases = ['what about', 'how about', 'and also']
        
        q_lower = query.lower()
        
        for term in ambiguous_terms:
            if term in words:
                return True
                
        for phrase in ambiguous_phrases:
            if phrase in q_lower:
                return True
                
        return False
    
    async def rewrite(
        self,
        query: str,
        conversation_history: list[dict],
    ) -> str:
        """
        Returns rewritten query or original query if rewrite not needed.
        Logs whether rewrite was performed.
        """
        if not self.should_rewrite(query, conversation_history):
            logger.info(f"Query rewrite skipped for: {query}")
            return query
            
        try:
            import asyncio
            # Build messages for LLM
            messages = [{"role": "system", "content": self.REWRITE_SYSTEM_PROMPT}]
            
            # Add context (limit to last 4 messages to save tokens)
            for msg in conversation_history[-4:]:
                messages.append(msg)
                
            # Add user query
            messages.append({"role": "user", "content": f"Rewrite this question if necessary: {query}"})
            
            response = await asyncio.wait_for(self.llm.complete(messages), timeout=3.0)
            rewritten = response.strip()
            
            if rewritten and len(rewritten) > 2:
                logger.info(f"Query rewritten: '{query}' -> '{rewritten}'")
                return rewritten
            return query
        except Exception as e:
            logger.info(f"Query rewrite skipped (using original query): {e}")
            return query

