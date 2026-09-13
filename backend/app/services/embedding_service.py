from __future__ import annotations

import time
import logging
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Wraps BAAI/bge-small-en-v1.5 for generating document and query embeddings.
    
    BGE models use a special query prefix for retrieval tasks:
    - For queries: prefix with 'Represent this sentence for searching relevant passages: '
    - For documents: no prefix needed
    
    This prefix trick significantly improves retrieval quality for BGE models.
    """
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        # Load model once at startup
        # model_name comes from config
        self.model_name = model_name
        self.query_prefix = "Represent this sentence for searching relevant passages: "
        
        start_time = time.time()
        logger.info(f"Loading embedding model {model_name}...")
        self.model = SentenceTransformer(self.model_name)
        logger.info(f"Loaded {model_name} in {time.time() - start_time:.2f} seconds.")
    
    def encode_query(self, query: str) -> list[float]:
        # Add BGE query prefix for better retrieval
        prefixed_query = f"{self.query_prefix}{query}"
        embedding = self.model.encode(prefixed_query, normalize_embeddings=True)
        return embedding.tolist()
    
    def encode_document(self, text: str) -> list[float]:
        # No prefix for documents
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def encode_batch(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        # Batch encoding for efficiency during ingestion
        # Add prefix to all if is_query=True
        start_time = time.time()
        
        if is_query:
            texts = [f"{self.query_prefix}{t}" for t in texts]
            
        embeddings = self.model.encode(texts, batch_size=32, normalize_embeddings=True)
        logger.info(f"Batch encoded {len(texts)} texts in {time.time() - start_time:.2f} seconds.")
        
        return embeddings.tolist()

# Module-level singleton - initialized once at app startup
_embedding_service: EmbeddingService | None = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
