# Technical Specifications

> **Document Owner:** AetherTutor Team
> **Created:** April 12, 2026
> **Version:** 1.0
> **Status:** Active
> **Parent:** [core/README.md](README.md)

---

Tài liệu này định nghĩa **Tech Stack MVP**, **AI Pipeline logic**, **Rate Limiting**, **Token Management** và **Data Isolation** — các quy định kỹ thuật cốt lõi cho AetherTutor.

---

## 1. Tech Stack MVP

### 1.1 Backend

| Component | Technology | Version | Ghi chú |
|---|---|---|---|
| **Framework** | FastAPI + Uvicorn | 0.115+ / 0.29+ | Async-first, auto OpenAPI docs |
| **Language** | Python | 3.11+ | Type hints bắt buộc |
| **ORM** | SQLAlchemy 2.0 (async) | 2.0+ | AsyncSession, select() syntax |
| **Migration** | Alembic | Latest | Auto-generate từ model changes |
| **Database** | PostgreSQL | 16 (Alpine) | asyncpg driver, connection pooling |
| **Vector DB** | ChromaDB | 0.5.0 (HTTP mode) | Embeddings cho chunks + entities |
| **Cache/Queue** | Redis + ARQ | Redis 7 / ARQ 0.25+ | Background task processing |
| **Graph Storage** | NetworkX (in-memory) + PostgreSQL (persistent) | Latest | NetworkX cho query, SQL cho persistence |
| **LLM** | OpenAI API / Ollama | Configurable | Switch được qua Settings |
| **Embedding** | text-embedding-3-small (OpenAI) / nomic-embed-text (Ollama) | 1536d / 768d | Dimension tracking bắt buộc (BR-008) |
| **Testing** | pytest + pytest-asyncio + httpx | Latest | asyncio_mode = auto |
| **Linting** | Ruff | Latest | Pre-commit hook |

### 1.2 Frontend

| Component | Technology | Version | Ghi chú |
|---|---|---|---|
| **Framework** | React + TypeScript | 18+ / 5+ | Vite build tool |
| **Styling** | Tailwind CSS | v4 | Utility-first, CSS variables cho theme |
| **State Management** | Zustand | 4+ | Lightweight, 3 stores (chat, graph, theme) |
| **HTTP Client** | Axios | Latest | Interceptors cho auth + error handling |
| **Graph Viewer** | React Flow | v11 | Custom nodes/edges, radial layout |
| **Animation** | Framer Motion | Latest | Page transitions, mobile drawer |
| **Markdown** | react-markdown + KaTeX | Latest | Math rendering |
| **Notifications** | Sonner | Latest | Toast notifications |
| **Icons** | Lucide React | Latest | Consistent icon set |

### 1.3 Infrastructure

| Component | Technology | Version | Ghi chú |
|---|---|---|---|
| **Containerization** | Docker + Docker Compose | Latest | Multi-stage builds |
| **CI/CD** | GitHub Actions | Latest | ci.yml: lint, test, build |
| **Reverse Proxy** | Nginx | Alpine | Production frontend serving |
| **Monitoring** | Sentry SDK | Latest | Backend + frontend error tracking |

---

## 2. AI Pipeline Logic

### 2.1 Document Processing Pipeline

```
Upload PDF → Validate (size, type) → Queue (ARQ) → Worker picks up
    → Extract Text (PyPDF) → Chunk (500 chars, 50 overlap)
    → Extract Entities + Relations (LLM batch / spaCy hybrid)
    → Build Knowledge Graph (NetworkX)
    → Generate Embeddings (chunks + entities)
    → Store (PostgreSQL + ChromaDB + NetworkX persist)
    → Mark COMPLETED
```

**State Machine (Dual-Field — BR-002):**

| Field | Values | Purpose |
|---|---|---|
| `status` | PENDING → PROCESSING → COMPLETED / FAILED | User-facing macro state |
| `processing_step` | QUEUED → INITIAL → EXTRACTING → CHUNKING → EXTRACTING_ENTITIES → BUILDING_GRAPH → EMBEDDING → COMPLETED | Internal micro state |

**Critical Rules:**
- Entity extraction PHẢI có ít nhất 1 entity (BR-003)
- Embeddings phải cho CẢ chunks VÀ entities (dual-level retrieval)
- ChromaDB metadata phải có `content_type: "chunk" | "entity"`
- Concurrent processing: CHỈ 1 document/user tại 1 thời điểm (BR-011)

### 2.2 Hybrid Entity Extraction

| Method | When | Pros | Cons |
|---|---|---|---|
| **spaCy** | LUÔN chạy trước (nhanh, ~50MB RAM) | Fast, deterministic | Limited to NER types |
| **LLM Batch #1** | Chạy sau spaCy, lấy relations | Semantic understanding | Slow, costs tokens |
| **LLM Fallback** | CHỈ chạy nếu < 30 entities | Đảm bảo quality | Extra cost |

**Entity Resolution:**
- Canonical name matching (lowercase, underscore)
- Similarity score >= 0.8 → merge
- Store aliases in `entity_aliases` table

### 2.3 LightRAG Dual-Level Retrieval

```
Level 1 (Entity-level): Vector similarity query → top_k entities
Level 2 (Concept-level): Graph traversal from Level 1 results → related concepts
Combine: Entities + Concepts + Relations → assembled context → LLM response
```

**Embedding Requirements:**
- OpenAI text-embedding-3-small: **1536 dimensions**
- Ollama nomic-embed-text: **768 dimensions**
- ⚠️ KHÔNG được trộn embeddings khác dimension vào cùng collection (BR-008)

---

## 3. Rate Limiting & Quota Management

### 3.1 Implementation

| Component | Library | Strategy |
|---|---|---|
| **Rate Limiter** | SlowAPI | Per-IP (MVP), per-user (Post-MVP) |
| **Key Function** | `get_remote_address()` | MVP single-user |
| **Storage** | In-memory (MVP) → Redis (Post-MVP) | |

### 3.2 MVP Limits

| Endpoint | Limit | Window | HTTP Code khi vượt |
|---|---|---|---|
| Document upload | 5 / day | 24h rolling | 429 |
| Chat requests | 10 / minute | 60s sliding | 429 |
| Graph queries | 30 / minute | 60s sliding | 429 |
| Flashcard generation | 10 / day | 24h rolling | 429 |
| Quiz generation | 5 / day | 24h rolling | 429 |

### 3.3 Post-MVP (per subscription tier)

| Tier | Daily Upload | Daily API Calls | Daily Tokens | Max File Size |
|---|---|---|---|---|
| Free | 5 | 1,000 | 50,000 | 50MB |
| Pro | 50 | 10,000 | 500,000 | 200MB |
| Enterprise | Unlimited | Unlimited | Unlimited | 1GB |

**Tracking:** `api_usage_logs` table (Post-MVP) — hiện chưa implement.

---

## 4. Token Management

### 4.1 Token Budgeting

| Operation | Est. Tokens (OpenAI) | Ghi chú |
|---|---|---|
| Entity extraction (1 chunk) | ~500 input + ~300 output | Per 500-char chunk |
| Embedding generation (batch) | ~100 per 10 chunks | Very cheap |
| Socratic chat response | ~2,000 input + ~500 output | Includes graph context |
| Flashcard generation (20 cards) | ~3,000 input + ~2,000 output | From graph entities |
| Quiz generation (10 questions) | ~4,000 input + ~3,000 output | Multi-hop questions |

### 4.2 Cost Optimization

- **Batch processing:** Entity extraction gộp nhiều chunks/LLM call
- **Caching:** Graph context cached cho cùng query
- **Local mode:** Ollama miễn phí, nhưng chậm hơn và embedding dimension khác
- **Token tracking:** `token_count` field trong `chat_messages` (Post-MVP)

---

## 5. Data Isolation & Multi-Tenancy

### 5.1 User Data Isolation (BR-001)

**MVP:** Single-user local với `DEFAULT_USER_ID = 00000000-0000-0000-0000-000000000000`

**Implementation per layer:**

| Layer | Isolation Mechanism |
|---|---|
| **PostgreSQL** | `WHERE user_id = :current_user_id` mọi query + RLS policies |
| **ChromaDB** | `where={"user_id": str(user_id)}` mọi query |
| **NetworkX Graph** | Node/edge attribute `user_id`, filter khi query |
| **API Layer** | Auth middleware inject `user_id` vào request context |

### 5.2 Row-Level Security (PostgreSQL)

```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users only see own data
CREATE POLICY user_documents_only ON documents
    USING (user_id = current_setting('app.current_user_id')::uuid);
```

### 5.3 Embedding Dimension Isolation (BR-008)

Khi user switch provider (OpenAI ↔ Ollama):
1. Kiểm tra `embedding_dim` khác nhau → tạo ChromaDB collection mới
2. KHÔNG xóa collection cũ — giữ để cross-collection query
3. Metadata tracking: `embedding_model`, `embedding_dim`, `created_at`
4. Query: CHỈ collections cùng `embedding_dim` với current model

---

## 6. Background Worker Architecture

### 6.1 Worker Types & Configuration

| Worker Type | Task | Priority | Timeout | Retry |
|---|---|---|---|---|
| Document Processing | PDF text extraction | High | 2 min | 3 retries, exponential backoff |
| Entity Extraction | LLM/spaCy extraction | High | 5 min | 3 retries, exponential backoff |
| Embedding Generation | ChromaDB storage | Medium | 10 min | 3 retries, exponential backoff |
| Graph Construction | NetworkX building | Medium | 3 min | 3 retries, exponential backoff |

### 6.2 Retry Policy (BR-010)

| Attempt | Wait Time | Total Elapsed |
|---|---|---|
| 1 (initial) | 0s | 0s |
| 2 (1st retry) | 30s | 30s |
| 3 (2nd retry) | 60s | 90s |
| 4 (3rd retry) | 120s | 210s |
| FAILED | — | 210s+ |

> [!NOTE]
> **ARQ Default Behavior:** ARQ tự động retry với backoff nhanh hơn spec (~2s → 4s → 8s).
> Để khớp spec 30s/60s/120s, cần custom backoff function.
> **Tracking:** [srs_analysis_reference.md#BR-010](../references-docs/srs_analysis_reference.md#110-br-010-error-recovery-rule)

### 6.3 Rollback Before Retry (BR-016)

TRƯỚC KHI retry:
```
1. XÓA partial data từ TẤT CẢ storage layers:
   - document_chunks, graph_entities, graph_relations
   - ChromaDB embeddings
   - NetworkX in-memory nodes
2. Reset status = "pending", step = "INITIAL"
3. Queue task mới → Chạy pipeline từ Step 1 trên data SẠCH
```

---

## 7. Error Handling & Exceptions

### 7.1 Exception Hierarchy

```
AppError (base)
├── BusinessLogicError
│   ├── ValidationError (400)
│   ├── ResourceNotFoundError (404)
│   ├── DuplicateResourceError (409)
│   └── RateLimitError (429)
├── PermanentProcessingError (422)
└── InfrastructureError (503)
```

### 7.2 HTTP Status Code Mapping

| Exception | HTTP Code | Use Case |
|---|---|---|
| ValidationError | 400 | Invalid input, file type |
| ResourceNotFoundError | 404 | Document/note not found |
| DuplicateResourceError | 409 | Duplicate file hash, concurrent upload |
| RateLimitError | 429 | Quota exceeded |
| PermanentProcessingError | 422 | Unrecoverable processing error |
| InfrastructureError | 503 | Database/Redis/LLM unavailable |

---

## 8. Logging & Observability

### 8.1 Structured Logging

```python
from app.logging_config import setup_logging, get_logger

setup_logging(
    level="DEBUG" if settings.DEBUG else "INFO",
    json_format=settings.APP_ENV == "production"
)

logger = get_logger(__name__)
logger.info("Processing document", extra={"doc_id": "123"})
```

**Features:**
- JSON formatter cho production
- Correlation ID tracking per request
- Request timing và metrics

### 8.2 Monitoring (Sentry)

- Backend: `sentry-sdk[fastapi]` integration
- Frontend: `@sentry/react` + `@sentry/tracing`
- DSN từ environment variable
- Release tracking qua git commit hash

---

## 9. Configuration Reference

### 9.1 Environment Variables (.env)

| Variable | Description | Default | Required |
|---|---|---|---|
| `APP_ENV` | development/production/testing | `development` | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | — | ✅ |
| `REDIS_HOST` | Redis host | `localhost` | ✅ |
| `CHROMA_HOST` | ChromaDB host | `localhost` | ✅ |
| `OPENAI_API_KEY` | OpenAI API key | — | ☁️ Cloud mode |
| `OLLAMA_BASE_URL` | Ollama endpoint | `http://localhost:11434/v1` | 🔒 Local mode |
| `DEFAULT_LLM_MODEL` | LLM model name | `Qwen2.5-1.5B` | ✅ |
| `EMBEDDING_PROVIDER` | openai/ollama | `openai` | ✅ |
| `EMBEDDING_DIM` | Embedding dimensions | `1536` | ✅ |
| `USE_LLM_MOCK` | Mock LLM for testing | `false` | ❌ Testing only |

### 9.2 File Limits

| Limit | Value | Config Key |
|---|---|---|
| Max file size | 50MB | `MAX_FILE_SIZE_MB` |
| Allowed extensions | .pdf | `ALLOWED_EXTENSIONS` |
| Max chunks per doc | Unlimited (auto) | — |
| Concurrent uploads | 1 per user | BR-011 |

---

## 10. Related Documents

| Tài liệu | Đường dẫn | Quan hệ |
|---|---|---|
| Architecture | [Architecture.md](Architecture.md) | Tổng quan kiến trúc, Agent orchestration |
| Data Model | [Data_Model.md](Data_Model.md) | Schema database chi tiết |
| Database | [Database.md](Database.md) | Docker config, connection pooling |
| API Spec | [API_Specifications.md](API_Specifications.md) | REST endpoints |
| Features | [Features.md](Features.md) | Danh sách tính năng |
| Business Rules | [../srs/Business_Rules.md](../srs/Business_Rules.md) | Luật nghiệp vụ bất biến |
| SRS Overview | [../srs/SRS_Overview.md](../srs/SRS_Overview.md) | Context anchors cho AI coding |

---

> [!IMPORTANT]
> **LIVING DOCUMENT** — Cập nhật khi có thay đổi tech stack hoặc architecture decisions.
> Mọi thay đổi PHẢI được review trước khi merge.

---
© 2026 AetherTutor Team. Created: April 12, 2026
