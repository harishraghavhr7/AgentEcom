# AgentEcom: High-Throughput, Low-Latency Commerce Engine for AI Agents

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Tests: 12 Passed](https://img.shields.io/badge/tests-12%20passed-brightgreen.svg)]()
[![Hybrid Search Recall@1: 100%](https://img.shields.io/badge/Recall%401-100%25-success.svg)]()

**AgentEcom** is a high-throughput, low-latency e-commerce backend and commerce tool suite engineered specifically for **AI Agent workflows** (autonomous purchasing agents, shopping assistants, and multi-agent systems).

---

## 📌 Project Status: Ready & Verified

- **Virtual Environment & Dependencies**: Fully configured with local PyTorch, Sentence-Transformers, Rank-BM25, FastAPI, SQLAlchemy, and Pytest.
- **Aggressive Caching**: Sub-millisecond reads (**0.031 ms**, 227.2x speedup) with precise tag-based reverse indexing.
- **Webhook-Based Invalidation**: Zero-polling, real-time cache invalidation triggered on merchant DB updates.
- **Hybrid Search Engine**: BM25 Sparse Lexical + Dense Vector Embeddings + Reciprocal Rank Fusion (RRF). **100% Recall@1, 100% Recall@3, 100% Recall@5, and 1.0 MRR** on golden agent evaluation queries.
- **Decoupled Ingestion**: Background worker generates embeddings off-request-thread without stalling agent search or checkout.
- **Isolated Idempotent Checkout**: Short-TTL (15 min) transient checkout sessions segregated from core `orders` table; guarantees zero duplicate orders or double charges on agent retries.
- **Automated Tests**: 12/12 integration and unit tests passing.

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    Agent[AI Agent / LLM Tool Calling] -->|Stateless Commerce Tools| API[FastAPI Gateway /tools]
    
    subgraph 1. Aggressive Caching & Invalidation Layer
        API -->|1. Check Cache <0.1ms| Cache[(In-Memory / Redis Cache)]
        MerchantDB[Merchant DB / Webhook Source] -->|2. Webhook: product.updated| InvalidationHook[Webhook Endpoint]
        InvalidationHook -->|3. Surgical Invalidation by SKU/Category| Cache
        InvalidationHook -->|4. Enqueue Async Reindex| AsyncQueue[Async Index Worker]
    end
    
    subgraph 2. Hybrid Search Engine (BM25 + Dense RRF)
        API -->|Search Query| HybridEngine[Hybrid Search Engine]
        HybridEngine -->|Sparse BM25| BM25Index[Tokenized Lexical Index]
        HybridEngine -->|Dense Cosine| DenseIndex[all-MiniLM-L6-v2 Vectors]
        HybridEngine -->|Reciprocal Rank Fusion| RRFMerge[RRF Score Aggregator]
        AsyncQueue -->|Decoupled Batch Embeddings| DenseIndex
        AsyncQueue -->|Update Document Tokens| BM25Index
    end
    
    subgraph 3. Isolated Checkout Sessions & Idempotency
        API -->|Create Session with Idempotency-Key| CheckoutMgr[Checkout Session Manager]
        CheckoutMgr -->|Short-TTL 15m Session| SessionStore[(Isolated Checkout Sessions)]
        CheckoutMgr -->|Confirm with Idempotency-Key| CoreOrderDB[(Core Orders Table)]
    end
```

---

## ⚡ Key Architectural Pillars

### 1. Catalog API — Cache Aggressively, Invalidate Precisely
- In-memory / Redis cache sits in front of the database, keyed by SKU, Category, and Query hash.
- **Webhook-driven Invalidation**: When merchant DB updates price or stock, targeted webhooks invalidate only the affected SKU/category keys. Eliminates TTL polling, stale pricing, and database thrashing.
- Achieves **0.031 ms** read latency (compared to 7.043 ms on direct DB queries).

### 2. Search Engine — Hybrid Search (Don't Reach for a Separate Vector DB by Default)
- **Why Hybrid**: BM25 excels at exact matches (SKU codes like `SKU-4471`, brand models like `SONY-WH1000XM5`), while dense vector retrieval catches semantic / paraphrased queries (`"cozy oversized sweater for winter"`).
- **Reciprocal Rank Fusion (RRF)**:
  $$\text{Score}_{\text{RRF}}(d) = \sum_{m \in \{\text{bm25}, \text{dense}\}} \frac{w_m}{k + \text{rank}_m(d)}$$
- **Decoupled Ingestion**: Product embedding generation runs asynchronously in background queues — never blocking the agent search request path or merchant DB writes.

### 3. Commerce Tools — Stateless and Fast
- Thin, idempotent commerce tools (`search_products`, `get_product`, `check_inventory`, `create_checkout_session`, `confirm_checkout`).
- Standard OpenAPI / JSON tool calling schema exportable for OpenAI, Anthropic, Gemini, LangChain, or Model Context Protocol (MCP) agents.

### 4. Checkout Sessions — Short-Lived, Idempotent, Isolated
- Short-TTL checkout sessions (15 minutes) stored in a dedicated table isolated from the core `orders` table.
- Prevents abandoned or exploratory agent sessions from polluting production sales analytics.
- Enforces `Idempotency-Key` headers on creation and confirmation to prevent double-charging and duplicate order placement during agent retries.

---

## 📊 Retrieval Quality & Latency Benchmark Results

Evaluated against the golden agent query dataset (`python -m agentecom.eval.eval_retrieval`):

| Retrieval Mode | Recall@1 (%) | Recall@3 (%) | Recall@5 (%) | MRR (Mean Reciprocal Rank) | Avg Latency (ms) | P50 Latency (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Sparse BM25 (Lexical Only)** | 100.0% | 100.0% | 100.0% | 1.0000 | 0.189 ms | 0.177 ms |
| **2. Dense Vector (Semantic Only)** | 87.5% | 93.75% | 93.75% | 0.9062 | 16.226 ms | 16.044 ms |
| **3. Hybrid RRF (BM25 + Dense)** | **100.0%** | **100.0%** | **100.0%** | **1.0000** | **15.265 ms** | **15.292 ms** |

---

## 📁 Repository Structure

```
AgentEcom/
├── agentecom/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── catalog.py      # Cached product & stock endpoints
│   │   │   ├── search.py       # Hybrid search endpoint
│   │   │   ├── checkout.py     # Isolated session & idempotent order endpoints
│   │   │   ├── webhooks.py     # Merchant DB sync webhook receiver
│   │   │   └── tools.py        # LLM tool execution & JSON schema endpoints
│   │   └── main.py             # FastAPI app with lifespan manager
│   ├── core/
│   │   ├── cache.py            # Aggressive cache with reverse tag indexing
│   │   └── checkout.py         # Checkout session isolation & idempotency logic
│   ├── db/
│   │   ├── database.py         # SQLAlchemy async engine
│   │   ├── models.py           # Product, Inventory, CheckoutSession, Order models
│   │   └── seed.py             # Curated product catalog dataset
│   ├── eval/
│   │   ├── dataset.py          # Golden agent query evaluation dataset
│   │   └── eval_retrieval.py   # Automated Recall@k & MRR benchmark script
│   ├── search/
│   │   ├── bm25_retriever.py   # Tokenized lexical BM25 engine
│   │   ├── dense_retriever.py  # Local sentence-transformers vector retriever
│   │   ├── hybrid.py           # Reciprocal Rank Fusion hybrid search engine
│   │   └── worker.py           # Decoupled async indexing worker
│   ├── tools/
│   │   └── commerce.py         # Stateless agent tools implementation
│   ├── config.py               # Application settings
│   └── demo.py                 # Interactive live demonstration script
├── tests/
│   ├── conftest.py             # Pytest fixtures and shared DB setup
│   ├── test_catalog_cache.py   # Cache hits, misses, latency tests
│   ├── test_webhook_invalidation.py # Surgical invalidation tests
│   ├── test_hybrid_search.py   # BM25, Dense, RRF tests
│   ├── test_checkout_idempotency.py # Session isolation & idempotency tests
│   └── test_commerce_tools.py  # Agent tool execution tests
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Project dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

---

## 🚀 Quickstart Guide

### 1. Set Up Virtual Environment
```powershell
# Create venv
python -m venv .venv

# Activate venv (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Interactive Live Demonstration
```powershell
python -m agentecom.demo
```

### 3. Run Retrieval Evaluation Suite
```powershell
python -m agentecom.eval.eval_retrieval
```

### 4. Run Automated Test Suite
```powershell
pytest tests/ -v
```

### 5. Launch FastAPI Server
```powershell
uvicorn agentecom.api.main:app --reload --port 8000
```
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`
- **Agent Tool Schemas (OpenAI/MCP)**: `http://localhost:8000/api/v1/tools/schema`
