from __future__ import annotations

from rank_bm25 import BM25Plus, BM25Okapi
import string
from typing import Optional, List, Dict, Any

class HybridSearcher:
    """
    Combines dense (semantic) and sparse (BM25) retrieval for better financial research.
    
    Why hybrid retrieval for financial documents:
    - Dense retrieval (BGE embeddings) captures semantic meaning
    - BM25 captures exact keyword matches (e.g. EBITDA, EPS, Capex)
    
    Score fusion formula:
        final_score = dense_weight * normalized_dense_score + bm25_weight * normalized_bm25_score
    
    Default weights: dense=0.7, bm25=0.3
    """
    
    def __init__(self, dense_weight: float = 0.7, bm25_weight: float = 0.3):
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight
    
    def search(
        self,
        query: str,
        *args,
        candidate_chunks: Optional[List[Dict[str, Any]]] = None,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Flexible search signature supporting:
          search(query, query_embedding, candidate_chunks, top_k=20)
          search(query, candidate_chunks, top_k=20)
        """
        candidates = candidate_chunks
        if args:
            if len(args) == 1:
                if isinstance(args[0], list) and args[0] and isinstance(args[0][0], (float, int)):
                    query_embedding = args[0]
                else:
                    candidates = args[0]
            elif len(args) >= 2:
                if isinstance(args[0], list) and (not args[0] or isinstance(args[0][0], (float, int))):
                    query_embedding = args[0]
                    candidates = args[1]
                else:
                    candidates = args[0]
                    if isinstance(args[1], int):
                        top_k = args[1]

        if "top_k" in kwargs:
            top_k = kwargs["top_k"]

        if not candidates:
            return []
            
        texts = []
        for c in candidates:
            if isinstance(c, dict):
                if 'chunk' in c:
                    inner = c['chunk']
                    texts.append(getattr(inner, 'content', getattr(inner, 'text', str(inner))))
                else:
                    texts.append(c.get('content') or c.get('text') or '')
            elif hasattr(c, 'content'):
                texts.append(c.content)
            elif hasattr(c, 'text'):
                texts.append(c.text)
            else:
                texts.append(str(c))
                
        if not texts:
            return candidates[:top_k]
            
        # BM25 Scoring
        bm25_scores = self.score_bm25(query, texts)
        
        # Dense Scoring
        dense_scores = [c.get('dense_score', 0.0) if isinstance(c, dict) else getattr(c, 'dense_score', 0.0) for c in candidates]
        
        # Normalize
        norm_bm25 = self.normalize_scores(bm25_scores)
        norm_dense = self.normalize_scores(dense_scores)
        
        # Combine
        hybrid_scores = self.combine_scores(norm_dense, norm_bm25)
        
        results = []
        for i, chunk_data in enumerate(candidates):
            if i < len(hybrid_scores):
                if isinstance(chunk_data, dict):
                    new_chunk_data = chunk_data.copy()
                else:
                    new_chunk_data = {"chunk": chunk_data}
                new_chunk_data['bm25_score'] = bm25_scores[i]
                new_chunk_data['hybrid_score'] = hybrid_scores[i]
                results.append(new_chunk_data)
                
        # Sort by hybrid score
        results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
        return results[:top_k]
    
    def score_bm25(self, query: str, corpus: List[Any]) -> List[float]:
        """
        Scores a list of texts or dictionaries against the query using BM25.
        Uses BM25Plus for strictly non-negative scores and robust handling of small corpora.
        """
        if not corpus:
            return []
        texts = []
        for doc in corpus:
            if isinstance(doc, dict):
                texts.append(doc.get('text') or doc.get('content') or '')
            elif hasattr(doc, 'text'):
                texts.append(doc.text)
            elif hasattr(doc, 'content'):
                texts.append(doc.content)
            else:
                texts.append(str(doc))

        tokenized_corpus = [self._tokenize(t) for t in texts]
        if not any(tokenized_corpus):
            return [0.0] * len(corpus)

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return [0.0] * len(corpus)

        try:
            bm25 = BM25Plus(tokenized_corpus)
            scores = bm25.get_scores(tokenized_query).tolist()
            # If all docs have equal term frequency or small N, check exact term occurrence
            if max(scores) == min(scores) and max(scores) > 0:
                # Differentiate based on query token matches
                for idx, doc_tokens in enumerate(tokenized_corpus):
                    matches = sum(1 for q in tokenized_query if q in doc_tokens)
                    scores[idx] += matches
            return scores
        except Exception:
            # Fallback simple term frequency scoring
            scores = []
            for doc_tokens in tokenized_corpus:
                matches = sum(1 for q in tokenized_query if q in doc_tokens)
                scores.append(float(matches))
            return scores

    def normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Min-max normalization to [0, 1].
        Handles edge case where all scores are equal (returns 0.5).
        """
        if not scores:
            return []
            
        min_val = min(scores)
        max_val = max(scores)
        
        if max_val == min_val:
            return [0.5] * len(scores)
            
        return [(s - min_val) / (max_val - min_val) for s in scores]

    def combine_scores(self, dense_scores: List[float], sparse_scores: List[float]) -> List[float]:
        """
        Compute weighted combination of dense and sparse scores.
        """
        combined = []
        for d, s in zip(dense_scores, sparse_scores):
            combined.append((self.dense_weight * d) + (self.bm25_weight * s))
        return combined
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace + lowercase tokenizer for BM25."""
        if not text:
            return []
        translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
        return text.translate(translator).lower().split()
