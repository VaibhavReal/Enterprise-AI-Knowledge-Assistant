from app.rag.hybrid_search import HybridSearcher

def test_matching_keywords_score_higher():
    searcher = HybridSearcher()
    docs = [
        {"id": 1, "text": "The EBITDA was positive this quarter.", "dense_score": 0.5},
        {"id": 2, "text": "We sell apples.", "dense_score": 0.5}
    ]
    results = searcher.search("EBITDA", docs, top_k=2)
    assert results[0]["id"] == 1

def test_weight_configuration_affects_scores():
    searcher_dense_heavy = HybridSearcher(dense_weight=1.0, bm25_weight=0.0)
    searcher_sparse_heavy = HybridSearcher(dense_weight=0.0, bm25_weight=1.0)
    
    docs = [
        {"id": 1, "text": "EBITDA margin", "dense_score": 0.1}, # Poor dense, good sparse
        {"id": 2, "text": "Earnings", "dense_score": 0.9}      # Good dense, poor sparse
    ]
    
    res1 = searcher_dense_heavy.search("EBITDA", docs, top_k=2)
    res2 = searcher_sparse_heavy.search("EBITDA", docs, top_k=2)
    
    assert res1[0]["id"] == 2
    assert res2[0]["id"] == 1

def test_top_k_limits_results():
    searcher = HybridSearcher()
    docs = [{"id": i, "text": f"Doc {i}", "dense_score": 0.5} for i in range(10)]
    results = searcher.search("query", docs, top_k=3)
    assert len(results) == 3
