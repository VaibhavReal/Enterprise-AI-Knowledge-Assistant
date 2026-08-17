# Understanding RAG in the Financial Research Assistant

This document provides a comprehensive explanation of Retrieval-Augmented Generation (RAG) and how it is specifically tailored for financial research in this project.

## 1. What is RAG and Why Do We Need It?

Large Language Models (LLMs) like GPT-4 are incredibly capable reasoners, but they have two fundamental flaws when it comes to enterprise or domain-specific tasks:
1.  **Knowledge Cutoff**: They only know what they were trained on up to a certain date.
2.  **Hallucinations**: When asked about something they don't know, they tend to confidently invent answers.

**Retrieval-Augmented Generation (RAG)** solves this by giving the LLM an open-book test. Instead of relying on its internal memory, the system first *retrieves* relevant documents from a proprietary database, and then *augments* the prompt to the LLM with these documents, asking it to *generate* an answer based strictly on the provided context.

For financial research, this is non-negotiable. An analyst cannot rely on an LLM to "guess" a company's revenue; they need the exact figure from the latest 10-K report.

## 2. Embeddings and Cosine Similarity

To retrieve text, we need a way to mathematically compare a user's question to thousands of document paragraphs. 

**Embeddings** are lists of numbers (dense vectors) that represent the semantic meaning of text. Imagine a multi-dimensional space where concepts like "Profit," "Income," and "Revenue" are located close to each other, while "Apples" is far away. 

When a query and a document chunk are embedded into this space, we use **Cosine Similarity** to measure the angle between their vectors. A smaller angle (closer to 1.0) means the texts are semantically similar, regardless of whether they use the exact same words.

## 3. Why BGE (Bidirectional Generative Encoder)?

We use the `BAAI/bge-small-en-v1.5` model for generating embeddings.
*   **Performance**: It consistently ranks at the top of the Massive Text Embedding Benchmark (MTEB) for retrieval tasks.
*   **Efficiency**: The "small" version produces 384-dimensional vectors. Smaller vectors mean less storage space in the database, faster search times, and lower memory overhead.
*   **Local Execution**: It can run locally on standard hardware without relying on paid external APIs, ensuring data privacy for sensitive financial documents.

## 4. Chunking Financial Documents

You cannot feed a 200-page Annual Report into an embedding model; it must be broken down. This is called **chunking**.

*   **Chunk Size**: We use a chunk size of ~800 tokens. If chunks are too small, they lose context (a number without the company name). If they are too large, the embedding becomes diluted, reducing retrieval accuracy.
*   **Overlap**: We use an overlap of ~150 tokens between consecutive chunks to ensure that concepts split across chunk boundaries are not lost.
*   **Financial Challenges**: Financial documents are tough. They contain massive tables and footnotes. Standard chunking often destroys tabular data. Our chunker attempts to respect paragraph boundaries and preserve structural metadata.

## 5. Vector Search in pgvector

Once chunks are embedded, they are stored in PostgreSQL using the `pgvector` extension.
We use an **HNSW (Hierarchical Navigable Small World)** index. Instead of comparing a query vector against every single chunk in the database (which is slow), HNSW creates a graph structure that allows for rapid, approximate nearest-neighbor search, returning results in milliseconds even with millions of vectors.

## 6. BM25: The Importance of Exact Matching

While embeddings are great at semantic meaning (knowing "income" matches "revenue"), they often fail at exact keywords. If you search for "EBITDA margin Q3", a dense embedding might retrieve a chunk about "Net margin Q4" because they are semantically close.

**BM25** is a sparse retrieval algorithm based on TF-IDF (Term Frequency - Inverse Document Frequency). It looks for exact keyword matches. If a rare financial term appears in a document, BM25 scores it very highly. In finance, specific terms matter immensely.

## 7. Hybrid Retrieval: The Best of Both Worlds

To get the most accurate results, we use **Hybrid Retrieval**.
We run both Dense Retrieval (pgvector) and Sparse Retrieval (BM25) simultaneously. We then normalize their scores and combine them.
A common starting weight is **0.7 for Dense and 0.3 for BM25**. This means the system primarily relies on semantic meaning but gives a significant boost to chunks that contain the exact terminology the user asked for.

## 8. Reranking: Quality over Latency

Initial retrieval (bi-encoders) is fast but slightly imprecise. To improve accuracy, we take the top ~20 results from the hybrid search and pass them through a **Cross-Encoder Reranker** (BGE Reranker).

*   **Bi-encoder (Initial Retrieval)**: Embeds query and document separately. Fast.
*   **Cross-encoder (Reranker)**: Feeds both the query and document into the model simultaneously, allowing the attention mechanism to see how the words in the query relate to the words in the document. It is much slower, but highly accurate.

We only rerank the top 20 candidates and select the final top 5 to pass to the LLM, balancing latency and quality.

## 9. Query Rewriting

Users converse naturally:
*   User: "What was Apple's revenue?"
*   Bot: "$383 billion."
*   User: "What about their profit?"

If we search the database for "What about their profit?", we will get terrible results because it lacks the entity ("Apple"). 
The system intercepts the query, looks at the chat history, and uses a fast LLM call to rewrite it to: "What was Apple's profit?" before retrieval.

## 10. Prompt Construction and Citations

The final step is building the prompt for the main LLM.
We construct a strict system prompt instructing the model to act as a financial analyst, to rely *only* on the provided context, and to refuse to answer if the information is missing.

**Citations** are critical. We do not trust the LLM to invent citations. Instead, the backend injects the chunks into the prompt with clear IDs (e.g., `[Source: Doc1_Page5]`). The LLM is instructed to append these IDs to its claims. The frontend then maps these IDs back to the actual document metadata.

## 11. Mitigating Hallucinations

Hallucinations happen when the LLM's internal weights overpower the provided context. We mitigate this by:
1.  **Grounding**: Providing highly relevant context via RAG.
2.  **System Prompts**: Explicit instructions against fabrication.
3.  **Temperature=0**: Setting the LLM to deterministic mode to favor facts over creativity.

Despite this, the risk is never zero. The user must always verify figures against the cited sources.

## 12. Context Windows

Why not just send the entire document to the LLM?
1.  **Cost**: LLM APIs charge by the token. Sending 200 pages costs significantly more than sending 5 relevant paragraphs.
2.  **Lost in the Middle**: Studies show that when LLMs are given massive context windows, they tend to forget or ignore information located in the middle of the text. RAG ensures only dense, highly relevant information is provided.

## 13. SSE Streaming

Financial answers can be long. Instead of making the user wait 10 seconds for the entire response to generate, we use **Server-Sent Events (SSE)**.
As the LLM generates tokens, FastAPI streams them immediately to the React frontend. This provides a typewriter effect, drastically reducing perceived latency and improving the user experience.
