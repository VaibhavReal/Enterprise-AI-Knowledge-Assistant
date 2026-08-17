"""
Retrieval Evaluation Script

Measures:
- Hit Rate: Did the correct section appear in top-K retrieved chunks?
- Recall@K: Of expected relevant chunks, how many were retrieved in top K?
- Latency: How long did retrieval take?

IMPORTANT: This script reports metrics from ACTUALLY RUNNING the system.
No metrics are fabricated. Run with actual uploaded documents to get real numbers.

Usage:
    python evaluation/evaluate_retrieval.py \
        --api-url http://localhost:8000 \
        --token YOUR_JWT_TOKEN \
        --questions evaluation/questions.json \
        --top-k 5
"""

from __future__ import annotations

import json
import time
import argparse
import httpx
from typing import List, Dict, Any

def evaluate_hit_rate(results: List[Dict[str, Any]], k: int) -> float:
    """
    Hit Rate @ K: fraction of questions where at least one retrieved chunk
    contains any of the expected_section_keywords.
    """
    hits = 0
    valid_count = 0
    for res in results:
        keywords = res.get("expected_section_keywords", [])
        chunks = res.get("retrieved_chunks", [])[:k]
        
        valid_count += 1
        hit = False
        for chunk in chunks:
            text = (chunk.get("content_snippet") or chunk.get("text") or chunk.get("section_title") or "").lower()
            if any(kw.lower() in text for kw in keywords):
                hit = True
                break
        if hit:
            hits += 1
            
    return hits / valid_count if valid_count > 0 else 0.0

def evaluate_recall_at_k(results: List[Dict[str, Any]], k: int) -> float:
    """
    Recall@K: of all chunks containing expected keywords, what fraction
    appeared in top-K?
    """
    total_recall = 0.0
    valid_count = 0
    for res in results:
        keywords = res.get("expected_section_keywords", [])
        chunks = res.get("retrieved_chunks", [])
        
        if not chunks:
            continue
            
        valid_count += 1
        relevant_in_all = sum(
            1 for c in chunks 
            if any(kw.lower() in (c.get("content_snippet") or c.get("text") or c.get("section_title") or "").lower() for kw in keywords)
        )
        relevant_in_k = sum(
            1 for c in chunks[:k] 
            if any(kw.lower() in (c.get("content_snippet") or c.get("text") or c.get("section_title") or "").lower() for kw in keywords)
        )
        
        if relevant_in_all > 0:
            total_recall += (relevant_in_k / relevant_in_all)
        else:
            # If at least one retrieved chunk matched in top-k
            total_recall += (1.0 if relevant_in_k > 0 else 0.0)
            
    return total_recall / valid_count if valid_count > 0 else 0.0

def run_evaluation(api_url: str, token: str, questions: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    For each question:
    1. Create research chat session
    2. Send question to RAG pipeline via message streaming
    3. Measure retrieval & response latency
    4. Extract real citations & chunks from the SSE stream
    5. Evaluate matching against expected keywords
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    results = []
    
    with httpx.Client(timeout=60.0) as client:
        for idx, q in enumerate(questions, 1):
            print(f"[{idx}/{len(questions)}] Evaluating: \"{q['question'][:60]}...\"")
            start_time = time.time()
            retrieved_chunks = []
            
            try:
                # 1. Create a dedicated chat session
                chat_res = client.post(
                    f"{api_url}/chats/",
                    headers=headers,
                    json={"title": f"Eval Q{idx}"}
                )
                chat_res.raise_for_status()
                chat_id = chat_res.json()["id"]

                # 2. Send message and consume SSE stream
                with client.stream(
                    "POST",
                    f"{api_url}/chats/{chat_id}/messages",
                    headers=headers,
                    json={"content": q["question"]}
                ) as sse_res:
                    sse_res.raise_for_status()
                    for line in sse_res.iter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                event = json.loads(data_str)
                                if event.get("done") and "citations" in event:
                                    retrieved_chunks = event["citations"]
                            except Exception:
                                pass

                latency = time.time() - start_time
                
                results.append({
                    "id": q.get("id", idx),
                    "question": q["question"],
                    "expected_section_keywords": q["expected_section_keywords"],
                    "retrieved_chunks": retrieved_chunks,
                    "latency_sec": latency
                })
                
            except Exception as e:
                latency = time.time() - start_time
                print(f"  Warning: Question failed evaluation: {e}")
                results.append({
                    "id": q.get("id", idx),
                    "question": q["question"],
                    "expected_section_keywords": q["expected_section_keywords"],
                    "retrieved_chunks": [],
                    "latency_sec": latency
                })
            
    return results

def print_results(results: List[Dict[str, Any]], top_k: int):
    """
    Print evaluation results clearly.
    """
    if not results:
        print("No results to display.")
        return
        
    print("\n" + "="*60)
    print("      RAG RETRIEVAL EVALUATION REPORT")
    print("="*60)
    
    hit_rate = evaluate_hit_rate(results, top_k)
    recall = evaluate_recall_at_k(results, top_k)
    avg_latency = sum(r["latency_sec"] for r in results) / len(results) if results else 0.0
    
    print(f"Total Questions Evaluated    : {len(results)}")
    print(f"Top-K Configuration          : {top_k}")
    print(f"Hit Rate @ {top_k}                 : {hit_rate:.2%}")
    print(f"Recall @ {top_k}                   : {recall:.2%}")
    print(f"Average Pipeline Latency     : {avg_latency:.3f}s per query")
    print("="*60)
    print("NOTE: Quantitative metrics are derived from actual citations and")
    print("retrieved document excerpts returned by the RAG pipeline.")
    print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG Retrieval Accuracy and Latency")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Base URL of FastAPI backend")
    parser.add_argument("--token", required=True, help="JWT bearer auth token")
    parser.add_argument("--questions", default="evaluation/questions.json", help="Path to test questions JSON")
    parser.add_argument("--top-k", type=int, default=5, help="Top K evaluation cut-off")
    args = parser.parse_args()
    
    with open(args.questions, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    print(f"Starting evaluation of {len(questions)} test queries...")
    eval_results = run_evaluation(args.api_url, args.token, questions, args.top_k)
    print_results(eval_results, args.top_k)
