# Worker Runbook — Background Job System

> **Document Owner:** AetherTutor Team
> **Created:** April 12, 2026
> **Version:** 1.0
> **Status:** Active
> **Framework:** ARQ (Asynchronous Redis Queue)

---

## 1. Tổng Quan Kiến Trúc

AetherTutor sử dụng **ARQ (Async Redis Queue)** để xử lý background jobs, giúp API không bị block bởi các tác vụ nặng như document processing, entity extraction, hay notification dispatch.

```
┌─────────────┐     Enqueue      ┌──────────────┐
│  FastAPI    │ ──────────────>  │   Redis      │
│  Gateway    │                  │   Queue      │
└─────────────┘                  └──────┬───────┘
                                        │
                                        │ Dequeue
                                        ▼
                               ┌─────────────────┐
                               │  ARQ Worker     │
                               │  (Python)       │
                               └────────┬────────┘
                                        │
                   ┌────────────────────┼────────────────────┐
                   ▼                    ▼                    ▼
            PostgreSQL            ChromaDB            NetworkX Graph
            (update status)       (embeddings)        (graph data)
```

### 1.1 File Structure

| File | Purpose |
|------|---------|
| `app/worker/tasks.py` | Task definitions + WorkerSettings configuration |
| `app/worker/queue.py` | Redis connection pool factory |
| `app/worker/__init__.py` | Module exports (currently empty) |
| `app/constants.py` | Worker-related constants (timeout, retries, etc.) |

### 1.2 Command Reference

```bash
# Khởi chạy ARQ Worker
arq app.worker.tasks.WorkerSettings

# Verbose mode (detailed logging)
arq app.worker.tasks.WorkerSettings --verbose
```

> [!WARNING]
> Worker PHẢI chạy song song với API server. Nếu không có worker, document uploads sẽ bị treo ở trạng thái `PENDING` vĩnh viễn.

---

## 2. Configuration

### 2.1 WorkerSettings

```python
class WorkerSettings:
    functions = [
        cleanup_expired_sessions_task,
        process_document_task,
        sm2_daily_digest_task,
        quiz_feedback_analysis_task,
        import_obsidian_vault_task,
    ]
    cron_jobs = [session_cleanup_cron, sm2_daily_digest_cron]
    redis_settings = redis_settings
    job_timeout = 1800      # 30 phút
    max_retries = 3         # Retry 3 lần trước khi fail
```

### 2.2 Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `WORKER_JOB_TIMEOUT_SECONDS` | 1800 (30 phút) | Timeout tối đa cho mỗi job |
| `WORKER_MAX_RETRIES` | 3 | Số lần thử lại tối đa |
| `REDIS_DISTRIBUTED_LOCK_TTL` | 60 (giây) | TTL cho distributed lock |
| `QUIZ_FEEDBACK_FLAG_THRESHOLD` | 2 | Ngưỡng rating để flag quiz kém chất lượng |

### 2.3 Redis Connection

```python
# app/worker/queue.py
from arq import create_pool
from arq.connections import RedisSettings
from ..config import settings

redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
# Default: redis://localhost:6379/0

async def get_redis_pool():
    pool = await create_pool(redis_settings)
    return pool
```

> [!NOTE]
> Pool được tạo mới mỗi lần gọi `get_redis_pool()` (KHÔNG phải singleton). Trong production, nên cân nhắc dùng connection pool singleton để giảm overhead.

---

## 3. Task Registry

### 3.1 Overview

| Task | Type | Trigger | Max Tries | Timeout |
|------|------|---------|-----------|---------|
| `process_document_task` | Manual | Document upload API | 3 | 30 min |
| `sm2_dispatcher_task` | Cron | Daily 8:00 AM | 1 | 30 min |
| `sm2_daily_digest_task` | Manual | Dispatched bởi dispatcher | 3 | 30 min |
| `quiz_feedback_analysis_task` | Manual | Low quiz rating (≤2) | 3 | 30 min |
| `import_obsidian_vault_task` | Manual | Obsidian import API | 3 | 30 min |
| `cleanup_expired_sessions_task` | Cron | Daily 2:00 AM | 1 | 30 min |

---

## 4. Task Details

### 4.1 `process_document_task`

**Mục đích:** Xử lý document upload — extract text, extract entities, build graph, generate embeddings.

**Signature:**
```python
async def process_document_task(ctx: Any, doc_id_str: str) -> None
```

**Parameters:**
- `doc_id_str`: String UUID của document cần xử lý

**Pipeline (5 bước):**

| Step | Action | Status Update |
|------|--------|---------------|
| 0 | Idempotency: Xóa dữ liệu cũ của document (graph, chunks, ChromaDB) | — |
| 1 | Extract text: Detect file type → PDF extractor OR Code parser | `EXTRACTING` |
| 2 | Chunk text: Chia thành chunks 500 chars, 50 overlap | `CHUNKING` |
| 3 | Extract entities & relations: LLM batch processing | `EXTRACTING_ENTITIES` |
| 4 | Build graph: NetworkX graph construction | `BUILDING_GRAPH` |
| 5 | Generate embeddings: ChromaDB vector storage | `EMBEDDING` → `COMPLETED` |

**File Type Detection:**

| Extension | Processor | Notes |
|-----------|-----------|-------|
| `.pdf` | `pdf_extractor.extract_text()` | Standard PDF processing |
| `.py`, `.js`, `.ts`, etc. | `code_parser.parse_file()` | AST parsing (Python) hoặc regex (JS/TS) |
| Khác | Fallback error | `PermanentProcessingError` |

**Error Handling:**

| Error Type | Action | Retry? |
|------------|--------|--------|
| `PermanentProcessingError` | Mark FAILED, return immediately | ❌ No |
| Document not found | Mark FAILED, return immediately | ❌ No |
| Text extraction failed (empty) | Mark FAILED, return immediately | ❌ No |
| Generic Exception | Mark FAILED, raise for ARQ retry | ✅ Yes (3x) |

**Dependencies:**
- `DocumentRepository`, `ChunkRepository`, `GraphRepository`
- `EntityExtractor`, `Retriever`, `LightRAGPipeline`
- `chroma_client`, `pdf_extractor`, `code_parser`

**Idempotency Guarantee:**
```python
# Step 0: Xóa toàn bộ partial data TRƯỚC KHI processing
await graph_repo.delete_by_document_id(doc_id)
await chunk_repo.delete_by_document_id(doc_id)
await chroma_client.delete_by_document_id(doc_id_str)
```

> [!IMPORTANT]
> Tuân thủ **BR-016 (Rollback Before Retry Rule)** — KHÔNG được retry mà không rollback trước để tránh duplicate data.

---

### 4.2 `sm2_dispatcher_task` (Cron — Daily 8:00 AM)

**Mục đích:** Query users có flashcards due và dispatch digest tasks cho từng user.

**Signature:**
```python
async def sm2_dispatcher_task(ctx: Any) -> None
```

**Cron Schedule:**
```python
CronJob(
    "sm2_daily_digest",
    sm2_dispatcher_task,
    hour={2}, minute={0}, second={0}, microsecond=0,
    run_at_startup=False, unique=True, max_tries=1,
)
```

**Logic:**
1. Query: `SELECT DISTINCT user_id FROM flashcards WHERE sm2_next_review <= NOW()`
2. Nếu không có user → skip
3. Với mỗi user: Enqueue `sm2_daily_digest_task`
4. Log tổng số đã enqueue

**Error Handling:** Per-user try/except — 1 user fail KHÔNG làm dừng toàn bộ.

**Retry Policy:** `max_tries=1` (KHÔNG retry — cron sẽ chạy lại ngày hôm sau)

---

### 4.3 `sm2_daily_digest_task`

**Mục đích:** Gửi daily flashcard digest notification cho một user cụ thể.

**Signature:**
```python
async def sm2_daily_digest_task(ctx: Any, user_id_str: str) -> None
```

**Logic:**
1. Parse `user_id` từ string
2. **Acquire Redis distributed lock** (key: `lock:sm2_digest:{user_id}`, TTL: 60s)
3. Query: `get_due_cards_count(user_id)` và `get_stats(user_id, days=7)`
4. Nếu `due_count == 0` → skip
5. Lấy user email từ DB
6. `notification_service.send_flashcard_digest(user_id, email, due_count, streak)`
7. Release lock trong `finally` block

**Distributed Lock Pattern:**
```python
lock_acquired = False
try:
    lock_acquired = await lock.acquire(blocking=False)
    if not lock_acquired:
        return  # Job đang chạy ở nơi khác
    # ... process
finally:
    if lock_acquired:
        await lock.release()
```

> [!WARNING]
> Distributed lock ngăn chặn duplicate notifications khi có nhiều workers chạy cùng lúc.

---

### 4.4 `quiz_feedback_analysis_task`

**Mục đích:** Phân tích feedback chất lượng quiz bằng LLM khi user rating thấp.

**Signature:**
```python
async def quiz_feedback_analysis_task(ctx: Any, result_id_str: str) -> None
```

**Trigger:** User submit feedback với rating ≤ 2 (xem `QUIZ_FEEDBACK_FLAG_THRESHOLD`)

**Logic:**
1. Lấy quiz result kèm answers: `get_by_id_with_answers(result_id)`
2. Check: Nếu `quality_rating > 2` hoặc `None` → return (không phân tích)
3. **LLM Analysis** (nếu có feedback text):
   - Tạo prompt phân loại
   - `llm_service.structured_extraction(prompt, FeedbackClassification, max_retries=2)`
4. Persist: `update_feedback_analysis(result_id, category, severity, suggestion)`

**FeedbackClassification Model:**
```python
class FeedbackClassification(BaseModel):
    category: str       # factual_error, poor_distractor, too_easy, too_hard, other
    severity: str       # low, medium, high
    suggestion: str     # LLM-generated suggestion
```

**Error Handling:** LLM failure → log warning, vẫn commit (KHÔNG raise)

---

### 4.5 `import_obsidian_vault_task`

**Mục đích:** Import Obsidian Vault (markdown files, wiki-links) vào Knowledge Graph.

**Signature:**
```python
async def import_obsidian_vault_task(
    ctx: Any,
    vault_path: str,
    user_id_str: str,
    job_id: str
) -> None
```

**Logic:**
1. Parse `user_id`
2. Setup Redis progress tracking (key: `import:{job_id}:progress`, TTL: 3600s)
3. `ObsidianVaultImporter.import_vault(vault_path, user_id, import_id=job_id)`

**Progress Tracking (4 giai đoạn):**

| Stage | Progress | Action |
|-------|----------|--------|
| Parsing markdown files | 0-30% | Scan vault, parse `.md` files |
| Upserting entities | 30-70% | Create/update graph entities |
| Building relations | 70-90% | Create wiki-link relations |
| Import completed | 100% | Persist graph, save result |

**API Integration:**
```python
# Check progress từ API
GET /graph/import/obsidian/status/{job_id}
# Response: {"status": "processing", "progress": 45} hoặc {"status": "completed", "result": {...}}
```

**Error Handling:**
- Per-file error: Log và continue (không abort toàn bộ)
- Task-level exception: Raise để ARQ retry, lưu error vào Redis

---

### 4.6 `cleanup_expired_sessions_task` (Cron — Daily 2:00 AM)

**Mục đích:** Xóa user sessions đã expire và revoked quá 30 ngày.

**Signature:**
```python
async def cleanup_expired_sessions_task(ctx: Any) -> None
```

**Cron Schedule:**
```python
CronJob(
    "session_cleanup",
    cleanup_expired_sessions_task,
    hour={2}, minute={0}, second={0}, microsecond=0,
    run_at_startup=False, unique=True, max_tries=1,
)
```

**Logic:**
1. Tạo `async_session_factory()`
2. Khởi tạo `UserSessionRepository`
3. `cleanup_expired_sessions(older_than_days=30)`
4. Commit session
5. Log số lượng đã xóa

**Retry Policy:** `max_tries=1` (KHÔNG retry — cron sẽ chạy lại ngày hôm sau)

---

## 5. Task Call Chains

### 5.1 Document Processing Flow

```
User uploads PDF
    │
    ├─> API validates & creates document (status: PENDING)
    │
    ├─> API enqueues: process_document_task(doc_id)
    │
    └─> ARQ Worker picks up task
         │
         ├─> [Step 0] Delete old data (idempotency)
         │
         ├─> [Step 1] pdf_extractor.extract_text()  OR  code_parser.parse_file()
         │
         ├─> [Step 2] ChunkRepository.save_chunks()
         │
         ├─> [Step 3] EntityExtractor.extract() → LLM calls
         │
         ├─> [Step 4] GraphRepository.save_entities_and_relations()
         │
         └─> [Step 5] ChromaClient.add_chunks() + add_entities()
              │
              └─> Document status: COMPLETED
```

### 5.2 SM2 Daily Digest Flow

```
Cron 8:00 AM
    │
    ├─> sm2_dispatcher_task()
    │    │
    │    ├─> Query: users with due flashcards
    │    │
    │    └─> For each user:
    │         │
    │         └─> Enqueue: sm2_daily_digest_task(user_id)
    │
    └─> sm2_daily_digest_task(user_id)
         │
         ├─> Acquire distributed lock
         │
         ├─> Query: due_cards_count, 7-day stats
         │
         ├─> notification_service.send_flashcard_digest()
         │    │
         │    ├─> Browser push (VAPID) — primary
         │    └─> Email (SMTP) — fallback
         │
         └─> Release lock
```

### 5.3 Quiz Feedback Analysis Flow

```
User rates quiz ≤ 2
    │
    ├─> API submits feedback
    │
    ├─> API enqueues: quiz_feedback_analysis_task(result_id)
    │
    └─> ARQ Worker picks up task
         │
         ├─> Load quiz result + answers
         │
         ├─> LLM classifies feedback → FeedbackClassification
         │
         └─> Persist: quiz_results.feedback_category, severity, suggestion
```

---

## 6. Error Handling Patterns

### 6.1 Classification

| Pattern | Use Case | Behavior |
|---------|----------|----------|
| **PermanentProcessingError** | Lỗi không thể phục hồi (file corrupt, empty text) | Mark FAILED, return, KHÔNG retry |
| **Generic Exception + raise** | Lỗi tạm thời (timeout, network error) | Mark FAILED, raise → ARQ retry |
| **Try/Except + log only** | Cron jobs, non-critical tasks | Log error, continue — KHÔNG raise |
| **Distributed Lock** | Prevent duplicate execution | Acquire → process → release |
| **Fallback logging** | LLM analysis failures | Log warning, commit partial |
| **Per-item error handling** | Batch operations | 1 item fail ≠ stop all |

### 6.2 Retry Policy Matrix

| Task | Retries | Backoff | Total Elapsed |
|------|---------|---------|---------------|
| `process_document_task` | 3 | ARQ default | ~90 phút max |
| `sm2_daily_digest_task` | 3 | ARQ default | ~90 phút max |
| `quiz_feedback_analysis_task` | 3 | ARQ default | ~90 phút max |
| `import_obsidian_vault_task` | 3 | ARQ default | ~90 phút max |
| `sm2_dispatcher_task` (cron) | 1 | N/A | 1 lần |
| `cleanup_sessions_task` (cron) | 1 | N/A | 1 lần |

> [!NOTE]
> ARQ retry backoff: 30s, 60s, 120s (exponential). Total time = sum of backoffs + job execution time.

---

## 7. Monitoring & Troubleshooting

### 7.1 Health Checks

```bash
# Kiểm tra worker có đang chạy không
ps aux | grep arq

# Kiểm tra Redis queue
redis-cli llen arq:queue:process_document_task
redis-cli llen arq:queue:sm2_daily_digest_task

# Kiểm tra Redis keys
redis-cli keys "arq:*"
```

### 7.2 Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Worker không chạy | Documents stuck ở `PENDING` | Kiểm tra `arq app.worker.tasks.WorkerSettings` có đang chạy không |
| Redis down | `ConnectionRefusedError` | `docker compose -f docker-compose.data.yml restart redis` |
| Task timeout (30 min) | Document processing quá lâu | Kiểm tra file size, LLM response time, network latency |
| Duplicate notifications | User nhận nhiều digest cùng lúc | Kiểm tra distributed lock có hoạt động không |
| LLM unavailable | `quiz_feedback_analysis_task` fails | Kiểm tra `OPENAI_API_KEY` hoặc Ollama status |

### 7.3 Logging

Worker sử dụng structured logging từ `app.logging_config`:

```python
logger.info("Processing document", extra={"doc_id": "abc123"})
logger.error("Text extraction failed", exc_info=True)
```

Xem logs:
```bash
# Worker logs (nếu chạy trong terminal)
arq app.worker.tasks.WorkerSettings --verbose

# Redis logs
docker compose -f docker-compose.data.yml logs redis

# API logs (enqueue side)
docker compose logs api
```

---

## 8. Scaling Considerations

### 8.1 Current Limitations

- **Single worker instance:** MVP chạy 1 worker process
- **No concurrency control:** Nhiều workers có thể chạy cùng task (mitigated by distributed locks)
- **No priority queue:** Tất cả tasks cùng priority

### 8.2 Future Improvements (Post-MVP)

| Improvement | Description | Priority |
|-------------|-------------|----------|
| **Multiple workers** | Chạy nhiều worker processes cho throughput cao hơn | Medium |
| **Priority queues** | Document processing > Notifications > Analytics | Medium |
| **Task metrics** | Export task duration/success rate đến Prometheus | Low |
| **Dead letter queue** | Lưu tasks failed sau 3 retries để manual review | Low |
| **Horizontal scaling** | Multiple workers trên nhiều machines với shared Redis | Post-MVP |

---

## 9. Deployment Checklist

### 9.1 Pre-Deployment

- [ ] Redis đang chạy và accessible (`redis-cli ping` → PONG)
- [ ] `ARQ_REDIS_URL` trong `.env` chính xác
- [ ] Worker command được test: `arq app.worker.tasks.WorkerSettings --verbose`
- [ ] Cron jobs được verify (check logs lúc 2AM và 8AM)

### 9.2 Production Deployment

```bash
# 1. Start worker as background service
nohup arq app.worker.tasks.WorkerSettings > /var/log/aethertutor/worker.log 2>&1 &

# 2. Verify worker is running
ps aux | grep arq

# 3. Test document upload
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test.pdf"

# 4. Check task queue
redis-cli llen arq:queue:process_document_task
```

### 9.3 Monitoring (Post-Deployment)

- [ ] Set up alert cho worker process down
- [ ] Monitor Redis memory usage
- [ ] Track task success rate (target: >95%)
- [ ] Monitor cron job execution logs

---

## 10. Reference

| Resource | Link |
|----------|------|
| ARQ Documentation | https://arq-docs.helpmanual.io/ |
| Redis Documentation | https://redis.io/docs/ |
| BR-002 (Document Processing) | [docs/srs/Business_Rules.md#br-002](../srs/Business_Rules.md#br-002-document-processing-pipeline-) |
| BR-010 (Error Recovery) | [docs/srs/Business_Rules.md#br-010-error-recovery-rule-](../srs/Business_Rules.md#br-010-error-recovery-rule-) |
| BR-016 (System Resilience) | [docs/srs/Business_Rules.md#br-016-system-resilience-](../srs/Business_Rules.md#br-016-system-resilience-) |
| Worker Settings Code | [app/worker/tasks.py](../../app/worker/tasks.py) |
| Constants | [app/constants.py](../../app/constants.py) |

---
© 2026 AetherTutor Team. Last updated: April 12, 2026