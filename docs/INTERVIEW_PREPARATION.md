# Interview Preparation & Defense Guide

This guide is designed to help a **4th-year B.Tech Mathematics & Computing student** defend the technical, mathematical, and architectural decisions of this project during senior engineering and ML interviews.

---

## 1. High-Level Elevator Pitches

### 60-Second Overview
> "I built an enterprise-grade Financial Research & Decision Support Assistant that enables analysts to query complex SEC filings (10-K, 10-Q) and earnings reports with zero hallucinated figures. The backend is built on FastAPI and PostgreSQL with `pgvector`, utilizing a multi-stage RAG pipeline: conversational query rewriting, BGE dense embeddings with BM25Plus sparse hybrid retrieval, cross-encoder reranking, and SSE token streaming directly to a React 18 interface with verifiable, database-grounded citations."

### 3-Minute Technical Deep Dive
> "Financial question answering has strict tolerance for hallucination—misreading ₹1,200 crore vs $1,200 million can alter valuation models completely. 
> To solve this, our system implements a 4-stage pipeline:
> 1. **Ingestion & Metadata Extraction**: Documents (PDF/DOCX/TXT) are parsed with PyMuPDF/python-docx, pre-cleaned, and segmented using financial paragraph-aware chunking (800 chars, 150 overlap). Embeddings are produced using `BAAI/bge-small-en-v1.5` (384 dimensions) and stored in PostgreSQL with pgvector cosine distance indices.
> 2. **Query Normalization**: A conversational query rewriter detects ambiguous multi-turn follow-ups (e.g., 'What about operating expenses?') and synthesizes self-contained retrieval queries incorporating previous chat context.
> 3. **Hybrid Search Fusion**: We perform simultaneous dense cosine similarity search in `pgvector` and sparse BM25Plus keyword matching to catch exact financial acronyms (e.g., EBITDA, EBIT, CapEx), fusing scores with min-max normalization (`0.7 * Dense + 0.3 * BM25`).
> 4. **Cross-Encoder Reranking & Constrained Generation**: Top-20 candidates are reranked using `BAAI/bge-reranker-base` down to the Top-5 most relevant passages. These are injected into a strict system prompt with temperature=0. The LLM response is streamed via Server-Sent Events (SSE) alongside verifiable citation cards."

---

## 2. Mathematical & Algorithmic Foundations

### Dense Embeddings & Vector Similarity
- **Model**: `BAAI/bge-small-en-v1.5` (BERT-based bi-encoder architecture).
- **Dimension**: $d = 384$.
- **L2 Normalization**: All vectors $\mathbf{u}, \mathbf{v}$ are $L_2$-normalized such that $\|\mathbf{u}\|_2 = 1$.
- **Cosine Distance vs Inner Product**:
  $$\text{Cosine Similarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|} = \mathbf{u} \cdot \mathbf{v}$$
  $$\text{Cosine Distance} = 1 - \text{Cosine Similarity}$$
- **pgvector `<=>` Operator**: Computes cosine distance $1 - \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$.

### BM25Plus Scoring Formulation
Standard BM25Okapi penalizes long documents heavily and can assign 0 or negative IDF scores when a term appears in more than half of the candidate chunks in small retrieval sets. We use **BM25Plus**:

$$\text{Score}(D, Q) = \sum_{q \in Q} \text{IDF}(q) \cdot \left[ \frac{f(q, D) \cdot (k_1 + 1)}{f(q, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)} + \delta \right]$$

- $f(q, D)$: Term frequency of query term $q$ in chunk $D$.
- $|D| / \text{avgdl}$: Ratio of chunk length to average corpus length.
- $k_1 = 1.5$: Term frequency saturation parameter.
- $b = 0.75$: Length normalization weight.
- $\delta = 1.0$: Lower bound floor preventing negative or zero scores on short financial passages.

### Linear Score Fusion
$$\text{Score}_{\text{hybrid}} = \alpha \cdot \widetilde{S}_{\text{dense}} + (1 - \alpha) \cdot \widetilde{S}_{\text{BM25}}$$
Where scores are min-max normalized:
$$\widetilde{S} = \frac{S - S_{\min}}{S_{\max} - S_{\min}}$$
Default weight: $\alpha = 0.7$ (Dense semantic priority with 30% keyword reinforcement).

### Bi-Encoder vs Cross-Encoder Complexity
- **Bi-Encoder ($O(1)$ search)**:
  $$\text{Score} = \phi(\text{Query}) \cdot \psi(\text{Doc})$$
  Embeddings are precomputed offline; online retrieval only requires vector dot product over index.
- **Cross-Encoder ($O(N)$ forward passes)**:
  $$\text{Score} = \text{Transformer}(\text{Query} \oplus \text{Doc})$$
  Allows all-to-all cross-attention between every query token and document token. Too expensive for corpus search ($N=100,000$), but optimal for reranking the top $K=20$ candidates (~50-100ms on CPU).

---

## 3. Systems Architecture & Trade-Offs

### Why PostgreSQL + pgvector over Pinecone / Qdrant?
1. **Single Source of Truth**: User authentication (`users`), document metadata (`documents`), chat threads (`chats`), and vectors (`document_chunks`) reside in a single ACID-compliant database.
2. **Relational Security Filtering**: Enforces strict document ownership with standard relational joins (`WHERE d.user_id = :user_id`) *before* or *during* nearest-neighbor scan, preventing multi-tenant data leaks.
3. **No External Network Latency**: Zero API roundtrips to third-party vector SaaS.

### Indexing: HNSW vs IVFFlat
- **HNSW (Hierarchical Navigable Small World)**: Multi-layer graph index. Fast queries ($O(\log N)$), high recall (>95%), slightly higher memory footprint. Best for production low-latency serving.
- **IVFFlat (Inverted File Flat)**: Clusters vectors into Voronoi cells. Requires initial training; faster build times but lower recall on dynamic updates.

### Server-Sent Events (SSE) vs WebSockets
| Attribute | Server-Sent Events (SSE) | WebSockets |
|---|---|---|
| **Direction** | Server $\to$ Client (Unidirectional) | Bidirectional full-duplex |
| **Protocol** | Plain HTTP/1.1 or HTTP/2 | `ws://` TCP upgrade handshake |
| **Authentication** | Standard `Authorization: Bearer <JWT>` header | Subprotocol or initial ticket |
| **Browser Reconnection** | Automatic with event IDs | Manual client-side reconnection loop |
| **Proxy / Nginx Buffering** | Simple: `X-Accel-Buffering: no` | Requires `Upgrade` & `Connection` proxy headers |
| **Suitability** | **Optimal** for LLM token streaming | Overkill for request-response chat |

---

## 4. Financial Domain Edge Cases & Defenses

### 1. Hallucination Mitigation
- System prompt uses strict exclusionary constraints: *"ONLY use information from the provided excerpts. If not present, state 'I could not find information about this in the retrieved document sections.'"*
- `temperature = 0.0`: Maximizes token determinism and greedy decoding.
- Separation of source citation metadata from LLM output: chunk page numbers and section headers are stamped directly from the database, not generated by the model.

### 2. Units & Scale Modifiers
- In corporate finance, balance sheet tables frequently note: *"Amounts in millions"* or *"₹ in Crores"*.
- The prompt instructs the LLM to retain the exact scale and currency notation as written rather than converting or truncating decimals.

### 3. Multi-turn Follow-up Disambiguation
- When an analyst asks: *"What about their operating expenses?"*, naive semantic search fails because the company name and fiscal period are missing from the raw query.
- The `QueryRewriter` checks recent chat history to rewrite the search query to: *"What were [Company]'s operating expenses in [Period]?"* while preserving the original user prompt for display.

---

## 5. Typical Interview Q&A Cheatsheet

**Q: How do you evaluate the RAG pipeline?**
> "We measure quantitative retrieval metrics using our [`evaluation/evaluate_retrieval.py`](file:///C:/Users/Harsh%20Aggarwal/Desktop/Enterprise%20AI%20Assistant/evaluation/evaluate_retrieval.py) harness over [`evaluation/questions.json`](file:///C:/Users/Harsh%20Aggarwal/Desktop/Enterprise%20AI%20Assistant/evaluation/questions.json):
> - **Hit Rate @ K**: Proportion of queries where at least one retrieved chunk contains the ground-truth target section keywords.
> - **Recall @ K**: Proportion of relevant chunks retrieved within the Top-K slots.
> - **Retrieval Latency**: End-to-end timing across query embedding, dense search, BM25 scoring, and cross-encoder reranking."

**Q: How would you scale this system to 10,000 concurrent users?**
> "1. **Asynchronous Ingestion**: Move PDF parsing and chunk embedding off the HTTP loop to Celery / Redis workers with a job status queue.
> 2. **Embedding Cache**: Cache query embeddings for identical or near-duplicate queries using Redis vector similarity.
> 3. **Read Replicas**: Distribute pgvector read traffic across PostgreSQL read replicas.
> 4. **Model Serving**: Host the BGE embedding and reranker models on dedicated Triton Inference Servers with ONNX Runtime or TensorRT acceleration."
