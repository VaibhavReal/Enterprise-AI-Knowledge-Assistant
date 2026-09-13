# Future Scope and Roadmap

This document outlines potential future enhancements for the Financial Research Assistant, categorized by implementation complexity.

## Phase 1: Easy Wins (Immediate Enhancements)

*   **Expanded File Format Support**: Add native parsing for `.xlsx` (Excel), `.csv`, and `.html` files, which are heavily used in finance.
*   **Improved PDF Table Extraction**: Integrate `pdfplumber` or `Camelot` to specifically identify and extract tabular data more cleanly than standard text extractors.
*   **Document Preview in UI**: Add a PDF viewer component in the React frontend so users can click a citation and immediately see the highlighted paragraph in the original document.
*   **Enhanced Metadata**: Automatically extract document creation dates and entity names using Named Entity Recognition (NER) during ingestion to enable better filtering (e.g., "Search only documents from 2023").

## Phase 2: Intermediate Architectural Upgrades

*   **Asynchronous Ingestion (Celery)**: Currently, uploading large documents can block API responses. Implementing a message broker (RabbitMQ/Redis) and Celery workers will allow ingestion to happen in the background, updating the UI via polling or WebSockets.
*   **Redis Query Caching**: Implement semantic caching. If User B asks a question semantically identical to User A's recent question, return the cached LLM response instantly instead of rerunning the pipeline.
*   **Document Versioning**: Allow updating a document (e.g., Draft v1 to v2) without losing the chat history associated with it.
*   **Conversation Summarization**: For long chat sessions, implement an automatic summarization step that compresses older messages, preserving the context window limit and reducing API costs.
*   **Robust Evaluation**: Build an "LLM-as-a-judge" evaluation pipeline using a stronger model to grade the RAG outputs on Faithfulness and Answer Relevance.

## Phase 3: Advanced Capabilities

*   **Direct SEC EDGAR Integration**: Build a data pipeline that automatically ingests 10-K and 10-Q filings directly from the SEC APIs using ticker symbols, eliminating the need for manual PDF uploads.
*   **Real-time Financial Data**: Integrate APIs like Alpha Vantage or Yahoo Finance. If a user asks about current stock price or market cap, the system routes the query to an API instead of the document database (Agentic Tool Calling).
*   **Multimodal RAG**: Upgrade the pipeline to process charts and graphs. Use models like GPT-4V to analyze images extracted from PDFs and generate text descriptions for the vector database.
*   **Local LLM Deployment**: Replace OpenAI with a self-hosted, quantized local LLM (like Llama 3 via Ollama) to ensure 100% data privacy for enterprise deployment.
*   **Multi-tenant Architecture & RBAC**: Implement strict data isolation so different corporate departments can use the system without seeing each other's proprietary documents. Add Role-Based Access Control (Admin vs. Viewer).

## Note on Integration with Quantitative Platforms (FUTURE ONLY)

This project is specifically designed for analyzing **unstructured financial text** (reports, filings, transcripts). 

In the future, this system could serve as an "Analyst Agent" alongside a distinct **Quantitative Portfolio Platform** that handles structured market data, backtesting, and portfolio optimization. 
*   **The Bridge**: The RAG system could identify qualitative risks in a 10-K (e.g., "Supply chain issues in Asia"), which a human portfolio manager then uses to adjust parameters in the quantitative platform.
*   **Architecture Rule**: Do NOT merge the codebases. They serve fundamentally different purposes. Maintain them as separate microservices that communicate via APIs.
