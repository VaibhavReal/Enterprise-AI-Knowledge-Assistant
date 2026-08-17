# System Limitations and Tradeoffs

While this Retrieval-Augmented Generation (RAG) system demonstrates significant capability for financial research, it is essential to acknowledge its architectural and operational limitations. Honest assessment of these constraints is critical for real-world deployment.

## 1. Document Extraction and Parsing

*   **Complex PDF Layouts**: The system currently uses standard libraries (like PyMuPDF) to extract text. It struggles with complex multi-column layouts, sidebars, and embedded charts. 
*   **Table Structure Loss**: Financial documents rely heavily on tabular data (e.g., Balance Sheets). While the raw text in the tables is extracted, the structural relationship (rows and columns) is often lost. An LLM might confuse a number from 2023 with a label for 2024 because the spatial alignment was destroyed during extraction.
*   **Scanned Documents (No OCR)**: The default ingestion pipeline expects native digital PDFs. It does not perform Optical Character Recognition (OCR). Scanned images of documents will result in empty or garbled text extraction.

## 2. Retrieval Constraints

*   **Embedding Model Nuances**: The `BAAI/bge-small-en-v1.5` model is highly efficient, but it is a general-purpose text embedding model. It may miss highly specific, nuanced financial context that a specially trained domain-specific model (like FinBERT embeddings) might catch.
*   **Hybrid Search Imperfections**: While combining dense and sparse search improves results, it is not foolproof. A search for "Apple" (the company) might still retrieve a chunk discussing agricultural commodities if the BM25 weighting is not perfectly tuned.
*   **Terminology Ambiguity**: Financial terms can be ambiguous. If a user asks for "revenue," and the document only lists "income from operations," the system relies entirely on the dense embedding's ability to link those concepts. If it fails, the answer fails.

## 3. Large Language Model (LLM) Risks

*   **Hallucinations Are Never Zero**: Despite strict system prompts and grounding via context, LLMs can still hallucinate. They might combine a revenue figure from one chunk with a date from another chunk, creating a plausible but entirely fabricated fact.
*   **Conflicting Values**: If a company's earnings release highlights an "Adjusted Revenue" on page 1, and GAAP Revenue on page 10, the RAG system might retrieve both. The LLM has to decide which one to present to the user, potentially causing confusion if not explained clearly.
*   **Latency**: The pipeline involves multiple stages: query rewriting (LLM), dense/sparse search (DB), cross-encoder reranking (Model), and generation (LLM). Relying on external APIs like GPT-4.1 adds 2-10 seconds of latency, which can feel slow in a chat interface.
*   **Cost**: Operating GPT-4.1 or Claude Sonnet at scale incurs significant API costs. Every retrieved chunk adds to the token count of the prompt.

## 4. Evaluation and Metrics

*   **Proxy Evaluation**: Our evaluation framework uses keyword matching as a proxy for relevance (e.g., assuming a chunk is relevant if it contains the word "EBITDA"). This is a necessary shortcut for automated testing but does not represent true human judgment.
*   **Limited Dataset**: The system requires rigorous testing against hundreds of complex financial queries across varied document structures before being considered reliable.

## Conclusion and Disclaimer

This project is an advanced proof-of-concept demonstrating modern AI engineering patterns. **It is NOT institutional-grade financial infrastructure.** Real-world financial systems require human-in-the-loop verification, much more advanced table extraction (like OCR + LayoutLM), and extensive red-teaming.

**This system does not constitute investment advice.** Users must always verify AI-generated figures against the cited original documents.
