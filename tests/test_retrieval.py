import pytest
from app.rag.hybrid_search import HybridSearcher

def test_bm25_scoring():
    searcher = HybridSearcher()
    corpus = [
        {"id": 1, "text": "The company reported revenue of 10M."},
        {"id": 2, "text": "Net income was positive."}
    ]
    scores = searcher.score_bm25("revenue", corpus)
    # The chunk with "revenue" should score higher
    assert scores[0] > scores[1]

def test_score_normalization():
    searcher = HybridSearcher()
    raw_scores = [0.1, 5.0, 2.5]
    norm_scores = searcher.normalize_scores(raw_scores)
    for s in norm_scores:
        assert 0.0 <= s <= 1.0
    assert max(norm_scores) == 1.0
    assert min(norm_scores) == 0.0

def test_hybrid_score_formula():
    searcher = HybridSearcher(dense_weight=0.7, bm25_weight=0.3)
    dense = [0.8, 0.4]
    sparse = [0.5, 0.9]
    hybrid = searcher.combine_scores(dense, sparse)
    
    assert abs(hybrid[0] - (0.8 * 0.7 + 0.5 * 0.3)) < 1e-5
    assert abs(hybrid[1] - (0.4 * 0.7 + 0.9 * 0.3)) < 1e-5

def test_empty_candidate_list():
    searcher = HybridSearcher()
    results = searcher.search("query", [], top_k=5)
    assert len(results) == 0
