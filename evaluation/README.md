# Evaluation Framework

This directory contains the evaluation framework for the Financial Research Assistant's retrieval system.

## What it measures
The evaluation script measures the performance of the Retrieval-Augmented Generation (RAG) pipeline, specifically focusing on the retrieval component:
1. **Hit Rate @ K**: Did the expected financial section appear in the top-K retrieved chunks?
2. **Recall @ K**: Of the chunks identified as potentially relevant (via keyword matching), what fraction was retrieved in the top K?
3. **Latency**: How long did the search take to execute across dense, sparse, and reranking stages?

## Limitations
This evaluation uses **keyword matching as a proxy for relevance**. It checks if expected terms (like "revenue", "EBITDA") appear in the retrieved chunks. 
- It does **not** replace ground-truth human evaluation.
- It may produce false positives (e.g., retrieving a chunk that mentions "revenue" but isn't the main income statement).

## How to run it
You must have the backend running and an active user account to get a JWT token.

```bash
# 1. Start the backend
docker compose up backend -d

# 2. Get a JWT token by logging in (via Swagger UI or curl)
# curl -X POST "http://localhost:8000/auth/login" -d "username=user@example.com&password=yourpassword"

# 3. Run the evaluation script
python evaluation/evaluate_retrieval.py \
    --api-url http://localhost:8000 \
    --token YOUR_JWT_TOKEN \
    --questions evaluation/questions.json \
    --top-k 5
```

## Adding More Questions
You can add more questions to `questions.json`. Structure them as:
```json
{
  "id": 13,
  "question": "What is the current ratio?",
  "expected_section_keywords": ["current ratio", "current assets", "current liabilities"],
  "question_type": "factual",
  "financial_metric": "liquidity",
  "notes": "Balance sheet analysis"
}
```

## Interpreting Results
- **Hit Rate**: If this is low, the semantic search might not be aligning user queries with document phrasing. Consider tuning the query rewriting or hybrid search weights.
- **Latency**: If latency is too high, consider optimizing the BGE reranker, as cross-encoders are computationally expensive.
