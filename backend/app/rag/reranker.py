from __future__ import annotations

import logging
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

class Reranker:
    """
    Cross-encoder reranking for precision ranking of top candidate chunks.
    
    Uses hybrid score ranking as baseline with optional cross-encoder enhancement.
    Never blocks the request lifecycle.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        try:
            # Attempt to load if cached locally
            self.model = CrossEncoder(self.model_name, max_length=512)
            logger.info(f"Reranker {model_name} initialized.")
        except Exception as e:
            logger.info(f"Reranker cross-encoder deferred (using hybrid scoring): {e}")
    
    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Takes query + list of chunk dicts (with 'chunk' and 'hybrid_score' keys)
        Returns top_k chunks sorted by cross-encoder score or hybrid score.
        """
        if not chunks:
            return []

        # If model is loaded, try cross-encoder scoring
        if self.model is not None:
            try:
                texts = []
                for c in chunks:
                    chunk_obj = c.get('chunk', c)
                    content = getattr(chunk_obj, 'content', getattr(chunk_obj, 'text', ''))
                    texts.append(content)
                
                pairs = [[query, text] for text in texts]
                scores = self.model.predict(pairs)
                
                results = []
                for i, chunk_data in enumerate(chunks):
                    new_chunk_data = chunk_data.copy() if isinstance(chunk_data, dict) else {"chunk": chunk_data}
                    new_chunk_data['rerank_score'] = float(scores[i])
                    results.append(new_chunk_data)
                    
                results.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
                return results[:top_k]
            except Exception as e:
                logger.warning(f"Cross-encoder scoring skipped: {e}")

        # High-performance baseline: Sort by hybrid score
        results = []
        for c in chunks:
            item = c.copy() if isinstance(c, dict) else {"chunk": c}
            item['rerank_score'] = item.get('hybrid_score', item.get('dense_score', 0.85))
            results.append(item)

        results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
        return results[:top_k]

# Singleton
_reranker: Reranker | None = None

def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
