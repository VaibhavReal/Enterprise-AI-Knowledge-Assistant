# Evaluation Framework

This document explains the evaluation framework designed for the RAG pipeline.

## What Are We Evaluating?

In a RAG system, the final answer is only as good as the documents retrieved. If the search engine fails to find the paragraph containing the revenue figures, the LLM cannot answer the question accurately, no matter how powerful it is.

Therefore, our evaluation focuses specifically on **Retrieval Performance**.

## Metrics

### 1. Hit Rate @ K
*   **Definition**: The percentage of test queries where *at least one* relevant document chunk appeared in the top K retrieved results.
*   **Why it matters**: If Hit Rate @ 5 is high, it means the LLM almost always has the necessary context to answer the question.
*   **Calculation**: (Number of queries with at least one hit in top K) / (Total number of queries).

### 2. Recall @ K
*   **Definition**: Of all the relevant chunks that exist in the database for a query, what fraction of them were successfully retrieved in the top K?
*   **Approximation**: Because we don't have human-labeled datasets indicating exactly which chunks are relevant, we use keyword matching as a proxy. We assume any chunk containing specific financial keywords (e.g., "revenue", "income from operations") is "relevant."
*   **Why it matters**: For multi-fact questions ("What were all the risk factors?"), the system needs to retrieve *all* relevant chunks, not just one.

### 3. Latency
*   **Definition**: Time taken to execute the query rewriting, dense search, sparse search, and reranking.
*   **Why it matters**: Cross-encoder rerankers are slow. We must measure latency to ensure the system remains responsive.

## How to Run the Evaluation

1.  Ensure your backend is running.
2.  Obtain a JWT auth token.
3.  Run the script:
    ```bash
    python evaluation/evaluate_retrieval.py \
        --token YOUR_JWT_TOKEN \
        --questions evaluation/questions.json \
        --top-k 5
    ```

**IMPORTANT NOTE**: The script queries the live database. It will return actual metrics based on the documents you have uploaded. It does not fabricate numbers.

## Limitations

1.  **Keyword Proxy**: Using keyword matching to define "relevance" is flawed. A chunk might contain the word "revenue" but be discussing an industry trend, not the company's actual revenue.
2.  **Dataset Size**: The provided `questions.json` contains 12 questions. Statistical significance requires hundreds of queries.
3.  **Generative Evaluation**: We are evaluating retrieval, not generation. We do not currently evaluate if the LLM hallucinated despite getting the right context.

## Adding Questions
Edit `evaluation/questions.json` to add queries tailored to your specific documents. Ensure `expected_section_keywords` contains the exact terminology you expect the system to find.

## Future Evaluation Improvements

*   **Precision @ K**: Measuring how many of the retrieved chunks were actually relevant (requires human labeling or an LLM-as-a-judge).
*   **MRR (Mean Reciprocal Rank)**: Measures how high up the list the *first* relevant chunk appears.
*   **LLM-as-a-Judge**: Using GPT-4 to read the LLM's answer and the source document to evaluate "Faithfulness" (Did the answer contradict the document?) and "Answer Relevance" (Did it actually answer the user's prompt?).
