from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from app.db.models import Document

logger = logging.getLogger(__name__)

class FinancialRAGPipeline:
    """
    Orchestrates the complete RAG pipeline for financial research.
    
    Pipeline steps:
    1. Query rewriting (if follow-up is ambiguous)
    2. Generate query embedding
    3. Dense retrieval (pgvector similarity search)
    4. BM25 + hybrid score combination
    5. Cross-encoder reranking
    6. Build financial prompt with citations
    7. Stream LLM response
    8. Return response + citations
    """
    
    def __init__(self, db: Session, user_id: int):
        from app.services.embedding_service import get_embedding_service
        from app.rag.retrieval import DenseRetriever
        from app.rag.hybrid_search import HybridSearcher
        from app.rag.reranker import get_reranker
        from app.rag.query_rewriter import QueryRewriter
        from app.services.llm_service import get_llm_provider
        from app.core.config import get_settings
        
        self.settings = get_settings()
        self.db = db
        self.user_id = user_id
        self.embedding_service = get_embedding_service()
        self.dense_retriever = DenseRetriever()
        self.hybrid_searcher = HybridSearcher(
            dense_weight=self.settings.DENSE_WEIGHT,
            bm25_weight=self.settings.BM25_WEIGHT,
        )
        self.reranker = get_reranker()
        self.llm = get_llm_provider()
        self.query_rewriter = QueryRewriter(self.llm)
    
    async def run(
        self,
        query: str,
        conversation_history: list[dict],
        document_ids: list[int] | None = None,
        stream: bool = True,
    ):
        """
        Run the full RAG pipeline with streaming token support and graceful conversational fallback.
        """
        # Step 1: Query rewriting for multi-turn conversational disambiguation
        rewritten_query = await self.query_rewriter.rewrite(query, conversation_history)
        
        # Step 2: Embed the query
        query_embedding = self.embedding_service.encode_query(rewritten_query)
        
        # Step 3: Dense retrieval via pgvector
        dense_results = self.dense_retriever.retrieve(
            query_embedding=query_embedding,
            db=self.db,
            user_id=self.user_id,
            top_k=self.settings.MAX_CHUNKS_RETRIEVED,
            document_ids=document_ids,
        )
        
        # If no documents exist or no chunks match: provide a helpful, conversational guided response
        if not dense_results:
            user_docs_count = (
                self.db.query(Document)
                .filter(Document.user_id == self.user_id, Document.status == 'ready')
                .count()
            )
            
            if user_docs_count == 0:
                guidance = (
                    "👋 **Welcome to the Financial Research Assistant!**\n\n"
                    "I don't see any processed financial filings in your workspace yet.\n\n"
                    "**To begin research:**\n"
                    "1. Navigate to the **Documents** tab and click **Upload Document** (e.g. SEC 10-K, 10-Q, Annual Report, or Earnings Transcript).\n"
                    "2. Once uploaded, ask any question about revenue, operating margin, debt, EBITDA, or risk factors.\n"
                    "3. All answers are verified against your source documents with interactive citation cards."
                )
            else:
                guidance = (
                    f"I searched across your {user_docs_count} uploaded financial documents, but could not find sections directly answering: *\"{query}\"*.\n\n"
                    "**Suggested queries:**\n"
                    "- *\"What was the total revenue for the reported period?\"*\n"
                    "- *\"What were the major operating expenses and margins?\"*\n"
                    "- *\"What risks did management identify in the filing?\"*\n"
                    "- *\"What was the reported cash flow and CapEx?\"*"
                )
            
            for word in guidance.split(" "):
                yield {"token": word + " "}
            yield {"citations": [], "done": True}
            return

        # Step 4: Hybrid search (BM25 + dense)
        hybrid_results = self.hybrid_searcher.search(
            query=rewritten_query,
            query_embedding=query_embedding,
            candidate_chunks=dense_results,
            top_k=self.settings.MAX_CHUNKS_RETRIEVED,
        )
        
        # Step 5: Cross-Encoder Reranking
        reranked_results = self.reranker.rerank(
            query=rewritten_query,
            chunks=hybrid_results,
            top_k=self.settings.TOP_K_AFTER_RERANK,
        )
        
        # Step 6: Build structured prompt
        from app.rag.prompts import build_rag_prompt, format_citations
        messages = build_rag_prompt(
            query=query,
            retrieved_chunks=reranked_results,
            conversation_history=conversation_history,
        )
        citations = format_citations(reranked_results)
        
        # Step 7: Stream LLM response with extractive fallback
        if stream:
            try:
                has_yielded = False
                async for token in self.llm.stream(messages):
                    has_yielded = True
                    yield {"token": token}
                yield {"citations": citations, "done": True}
            except Exception as e:
                logger.warning(f"LLM streaming provider returned error ({type(e).__name__}: {e}). Providing grounded extractive synthesis.")
                
                notice = (
                    "### 📊 Financial Research Summary\n\n"
                    "*(Note: LLM provider unavailable. Displaying exact facts grounded in your documents:)*\n\n"
                )
                for word in notice.split(" "):
                    yield {"token": word + " "}

                for idx, c in enumerate(reranked_results[:4], 1):
                    chunk_obj = c.get('chunk', c)
                    content = getattr(chunk_obj, 'content', getattr(chunk_obj, 'text', str(chunk_obj))).strip()
                    section = getattr(chunk_obj, 'section_title', 'General Excerpt')
                    doc_name = getattr(chunk_obj, 'filename', 'Document')
                    page = getattr(chunk_obj, 'page_number', 'N/A')
                    
                    passage = f"\n\n**[{idx}] {doc_name} (Page {page} • {section})**\n> {content}\n"
                    for word in passage.split(" "):
                        yield {"token": word + " "}

                yield {"citations": citations, "done": True}
        else:
            try:
                response_text = await self.llm.complete(messages)
                yield {"response": response_text, "citations": citations, "done": True}
            except Exception as e:
                fallback_text = "\n\n".join(
                    f"[{i+1}] {getattr(c.get('chunk', c), 'content', '')}"
                    for i, c in enumerate(reranked_results[:3])
                )
                yield {"response": fallback_text, "citations": citations, "done": True}
