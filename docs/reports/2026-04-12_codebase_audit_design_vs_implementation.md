# Codebase Audit Report — Design vs Implementation Gap Analysis

> **Date:** 2026-04-12
> **Author:** AetherTutor Team
> **Status:** 🔴 **ACTION REQUIRED** — 7 gaps confirmed, 3 critical
> **Source:** Audit Plan from implementation_plan.md.resolved (Gemini Brain)
> **Scope:** Full codebase audit across 4 Phases: Database → Pipeline → Agent → Learning Loop

---

## Executive Summary

Báo cáo này đối chiếu **kế hoạch đặc tả** (SRS / Business Rules / Architecture docs) với **trạng thái thực tế của source code** AetherTutor. Audit Plan gồm 4 Phase, tổng cộng 12 điểm kiểm tra.

### Audit Results

| Status | Count | Details |
|--------|-------|---------|
| ✅ **ĐẠT** (Implement đúng) | 5 | P1.1, P2.1, P2.2, P3.2, P4.2 |
| ⚠️ **MỘT PHẦN** (Có nhưng chưa đủ) | 1 | P2.3 |
| ❌ **KHÔNG ĐẠT** (Thiếu hoàn toàn) | 6 | P1.2, P1.3, P1.4, P3.1, P3.3, P4.1 |

### Critical Findings (🔴 Phải sửa trước production)

1. **ChromaDB không kiểm tra `embedding_dim`** — Đổi model (OpenAI ↔ Ollama) sẽ crash vector DB
2. **Row-Level Security chưa implement** — User isolation chỉ ở SQLAlchemy level, không enforced ở DB
3. **`attempt_count` không tồn tại trong chat flow** — Socratic state tracking giao hoàn toàn cho LLM, backend không đếm

### Severity Distribution

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 Critical | 3 | P1.3 (RLS), P1.4 (ChromaDB dim), P1.2 (`attempt_count`) |
| 🟡 Medium | 3 | P3.1 (Socratic JSON), P3.3 (Structured response), P4.1 (Auto entity link) |
| 🟢 Low | 0 | — |

---

## Phase 1: Database Schema & Vector DB Enforcement

### P1.1 — `status` và `processing_step` tách bạch ✅

**Yêu cầu:** Bảng `documents` phải có 2 trường riêng: `status` (trạng thái tổng thể) và `processing_step` (bước cụ thể trong pipeline).

**Thực tế:**

| Field | Type | Values |
|-------|------|--------|
| `status` | `Enum(DocumentStatus)` | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `processing_step` | `Enum(ProcessingStep)` | `QUEUED` → `INITIAL` → `EXTRACTING` → `CHUNKING` → `EXTRACTING_ENTITIES` → `BUILDING_GRAPH` → `EMBEDDING` → `COMPLETED` |

**File:** `app/models/document.py` — Đã implement đúng từ đầu.

**Verdict:** ✅ **ĐẠT** — Không có vấn đề.

---

### P1.2 — `chat_sessions` thiếu `attempt_count` metadata ❌

**Yêu cầu (BR-006):** Backend phải tự quản lý `attempt_count` — số lần user trả lời sai trong Socratic chat. Đây là pedagogical guardrail để AI quyết định "hỏi tiếp hay giải thích".

**Thực tế:**

Bảng `conversations` và `messages` KHÔNG có trường nào liên quan đến `attempt_count`:

```python
# app/models/conversation.py
class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    # id, document_id, title, last_message_at — KHÔNG có metadata

class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    # id, conversation_id, role, content, sequence_index, status, context_used
    # KHÔNG có attempt_count
```

`attempt_count` chỉ tồn tại ở 2 nơi KHÔNG liên quan đến chat:
1. `llm_service.structured_extraction(max_retries=3)` — retry JSON parsing
2. `generate_conversation_title(max_retries=2)` — retry title generation

**Hệ quả:** Socratic AI không biết user đã sai bao nhiêu lần để điều chỉnh chiến lược (gợi ý thêm hay giải thích luôn). Logic này bị giao phó cho LLM "tự nhớ" — không reliable.

**Verdict:** ❌ **KHÔNG ĐẠT** — Cần thêm trường `metadata` (JSON) vào `conversations` hoặc `messages` để track `attempt_count` và `last_answer_correct`.

---

### P1.3 — Row-Level Security (RLS) chưa implement ❌

**Yêu cầu (BR-001):** PostgreSQL phải bật RLS để cô lập dữ liệu theo `user_id` ở cấp database, không chỉ filter bằng SQLAlchemy.

**Thực tế:**

- **25 Alembic migrations** — KHÔNG có migration nào chứa `CREATE POLICY`, `ENABLE ROW LEVEL SECURITY`, hoặc `ROW LEVEL`.
- Tất cả bảng có `user_id` với `ForeignKey('users.id', ondelete='CASCADE')` và index trên `user_id`.
- Nhưng **KHÔNG có enforcement ở database level**.

**Design doc** (`docs/core/Technical_Spec.md` mục 5.2) CÓ mô tả RLS:
```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_documents_only ON documents
    USING (user_id = current_setting('app.current_user_id')::uuid);
```

Nhưng đây chỉ là **thiết kế**, chưa được implement trong migrations.

**Hệ quả:** Nếu có bug trong SQLAlchemy filter (hoặc raw SQL query), user có thể nhìn dữ liệu của user khác. RLS là lớp bảo vệ cuối cùng.

**Verdict:** ❌ **KHÔNG ĐẠT** — Cần tạo migration bật RLS trên các bảng nhạy cảm: `documents`, `conversations`, `messages`, `flashcards`, `notes`, `quiz_results`.

---

### P1.4 — ChromaDB không kiểm tra `embedding_dim` ❌

**Yêu cầu (BR-008):** Khi đổi embedding model (ví dụ: OpenAI `text-embedding-3-small` 1536-dim → Ollama `nomic-embed-text` 768-dim), hệ thống phải tự động tạo ChromaDB collection mới để tránh xung đột dimensions.

**Thực tế:**

**Constants có định nghĩa:**
```python
# app/constants.py
EMBEDDING_DIM_OPENAI = 1536   # text-embedding-3-small
EMBEDDING_DIM_OLLAMA = 768    # nomic-embed-text
```

**Nhưng KHÔNG được sử dụng để validate:**
```python
# app/services/chroma_client.py (dòng 51-62)
collection = self.client.get_or_create_collection(
    name=name,
    metadata=metadata or {"hnsw:space": CHROMA_HNSW_SPACE}
    # ❌ KHÔNG có embedding_dim trong metadata
)
```

**Chi tiết vấn đề:**

1. **Collection tạo 1 lần, cached mãi:** `ChromaClient.__init__()` cache collections trong `_collections_cache = {}`. Sau đó `_get_collection()` gọi `get_or_create_collection()` — nếu collection đã tồn tại, trả về cái cũ.

2. **Không có dimension guard:** `_get_collection()` chỉ truyền `hnsw:space` (cosine) vào metadata, KHÔNG truyền `embedding_dim`. ChromaDB KHÔNG tự check dimension match khi `add()` vectors mới.

3. **`add_to_collection()` KHÔNG validate dimension:**
```python
# app/services/chroma_client.py (dòng 84-110)
def add_to_collection(self, collection, ids, documents, metadatas=None, embeddings=None):
    add_kwargs = {"ids": ids, "documents": documents}
    if embeddings:
        add_kwargs["embeddings"] = embeddings  # ❌ Không check dimension
    collection.add(**add_kwargs)
```

4. **Embedding service có `self.dimension` nhưng KHÔNG dùng để validate ChromaDB:**
```python
# app/services/embedding_service.py
self.dimension = (
    EMBEDDING_DIM_OPENAI      # 1536
    if self.provider == "openai"
    else EMBEDDING_DIM_OLLAMA # 768
)
# → dimension này chỉ dùng để trả về zero vectors khi fail, KHÔNG validate với ChromaDB collection
```

5. **Comment `# BR-008 Multi-Collection Delete`** trong `delete_by_document_id()` (dòng 248-250) là **KẾ HOẠCH**, không phải thực tế đã implement:
```python
"""
⚠️ BR-008 Multi-Collection Delete:
Khi user đổi embedding provider (OpenAI ↔ Ollama), collection mới được tạo.
"""
# → Đây là mô tả ý định, nhưng code bên dưới KHÔNG tạo collection mới
```

**Kịch bản crash thực tế:**
1. User chạy hệ thống với `EMBEDDING_PROVIDER=openai` → tạo collection `aethertutor_chunks` với vectors 1536-dim
2. User đổi `.env` → `EMBEDDING_PROVIDER=ollama`
3. Pipeline gọi `chroma_client.add_chunks()` với vectors 768-dim
4. ChromaDB nhận vectors dimension khác vào cùng collection → **crash hoặc silent corruption** (search trả kết quả sai)

**Design doc** (`docs/core/Technical_Spec.md` mục 5.3) MÔ TẢ logic "Embedding Dimension Isolation":
> 1. Kiểm tra `embedding_dim` khác nhau → tạo ChromaDB collection mới
> 2. KHÔNG xóa collection cũ — giữ để cross-collection query

Nhưng logic này **CHƯA ĐƯỢC IMPLEMENT**.

**Verdict:** ❌ **KHÔNG ĐẠT** — Bug nghiêm trọng. Cần:
1. Thêm `embedding_dim` vào collection metadata khi `get_or_create_collection`
2. Kiểm tra dimension match trước khi `add` vectors
3. Auto-create collection mới nếu dimension khác (ví dụ: `aethertutor_chunks_ollama`)
4. Lưu `embedding_model_name` trong DB để track model hiện tại

---

## Phase 2: Pipeline Xử Lý Tài Liệu & Background Workers

### P2.1 — Validation 409 khi document đang PENDING/PROCESSING ✅

**Yêu cầu (BR-011):** API Upload phải trả `409 Conflict` khi user đang có document ở trạng thái `PENDING` hoặc `PROCESSING`.

**Thực tế:** `document_service.py` implement ĐÚNG và ĐẦY ĐỦ:

```python
# BR-011: Check concurrent processing
processing_count = await self.repo.count_processing_documents(self.user_id)
if processing_count > 0:
    raise HTTPException(status_code=409, detail="Document khác đang được xử lý...")
```

Cũng check duplicate hash → 409 (BR-017).

**Verdict:** ✅ **ĐẠT** — Audit plan flag để kiểm tra, thực tế đã implement tốt.

---

### P2.2 — Embedding cho cả Document Chunks VÀ Graph Entities ✅

**Yêu cầu:** LightRAG pipeline phải sinh vector cho cả chunks (đoạn văn bản) và entities (đỉnh graph).

**Thực tế:** `pipeline.py` có 2 collection ChromaDB riêng biệt:
- `aethertutor_chunks` — vectors cho document chunks
- `aethertutor_entities` — vectors cho graph entities

Cả `ingest_text()` và `ingest_code_entities()` đều gọi embedding cho cả hai.

**Verdict:** ✅ **ĐẠT** — Implement đúng thiết kế LightRAG.

---

### P2.3 — Rollback before Retry ⚠️

**Yêu cầu (BR-016):** Trước khi Worker retry một task lỗi, phải dọn partial data trong PostgreSQL và ChromaDB.

**Thực tế:** KHÔNG có hàm riêng tên `cleanup_partial_document_data()`, NHƯNG logic cleanup đã được **inline** trực tiếp trong `process_document_task` — và implement **TỐT HƠN kỳ vọng**:

```python
# app/worker/tasks.py — process_document_task (dòng ~115-125)
# Bước 0: Idempotency Sweep - Xóa sạch dấu vết cũ nếu đây là chạy lại
await graph_repo.delete_by_document_id(doc_id)
await chunk_repo.delete_by_document_id(doc_id)
chroma_client.delete_by_document_id(doc_id)
await session.commit()
```

**Điểm mạnh:**
- Cleanup chạy **NGAY ĐẦU** task, trước khi ingest → đảm bảo idempotency
- Cover cả 3 lớp lưu trữ: PostgreSQL (graph + chunks) + ChromaDB
- `commit()` ngay sau cleanup → đảm bảo sạch sẽ trước khi bắt đầu ingest mới

**Error handling cũng đầy đủ:**
```python
except PermanentProcessingError:
    await session.rollback()
    await doc_repo.update_status(doc_id, DocumentStatus.FAILED, e.message)
    await session.commit()
    return  # ❌ Không raise → ARQ KHÔNG retry

except Exception:
    await session.rollback()
    await doc_repo.update_status(doc_id, DocumentStatus.FAILED, ...)
    await session.commit()
    raise e  # ✅ ARQ sẽ retry (max 3 lần theo WORKER_MAX_RETRIES)
```

**Lưu ý quan trọng:** `PermanentProcessingError` (file không tồn tại, PDF không đọc được) → KHÔNG retry. Chỉ lỗi runtime (network, LLM timeout) mới retry. Đây là **thiết kế đúng**.

**Điểm cần cải thiện:**
- Logic inline thay vì hàm riêng → khó test unit, khó tái sử dụng
- `delete_by_document_id()` trên ChromaDB có thể fail silently (log error nhưng không raise) → nếu cleanup fail, task vẫn tiếp tục ingest → data rác

**Verdict:** ⚠️ **MỘT PHẦN** — Về cốt lõi ĐẠT TỐT (có idempotency sweep + rollback). Nhưng:
- Nên refactor thành `cleanup_partial_document_data(doc_id, session)` để testable
- Cần thêm validation: nếu ChromaDB cleanup fail → raise thay vì continue

---

## Phase 3: Agent Orchestrator & Logic Truy Xuất

### P3.1 — `attempt_count` trong Socratic chat ❌

**Yêu cầu (BR-006):** Backend phải tự đếm số lần user trả lời sai (`attempt_count`), KHÔNG giao cho LLM tự nhớ. Đây là pedagogical guardrail để backend quyết định khi nào AI nên "giải thích luôn" thay vì "hỏi tiếp".

**Thực tế:** KHÔNG có `attempt_count` trong bất kỳ model, schema, hay service nào liên quan đến chat.

**Phân tích chi tiết `_stream_logic` (`chat_service.py`):**

```python
# Quy trình stream hiện tại:
# 0. Context validation → 1. Save user message
# 2. Get recent history (last 10) → 3. Retrieve context
# 4. Construct Socratic prompt → 5. Create PENDING message
# 6. Stream LLM → 7. Update to COMPLETED
```

**KHÔNG có bước nào đếm `attempt_count` hay đánh giá `correctness`.** Toàn bộ "Socratic logic" nằm trong system prompt — LLM tự quyết định hỏi hay giải thích dựa trên conversation history (last 10 messages). Backend chỉ đóng vai trò **pipe**: retrieve → stream → save.

**Hệ quả:**
1. LLM "nhớ" attempt count qua history → unreliable, mất khi context window đầy
2. Không có guardrail: AI có thể hỏi mãi không giải thích, hoặc giải thích quá sớm
3. Không thể implement pedagogical analytics

**Verdict:** ❌ **KHÔNG ĐẠT** — Cần:
1. Thêm `metadata` JSON field vào `conversations` để track `{attempt_count, last_topics, hint_level}`
2. Backend parse user query → so khớp topics → increment attempt_count nếu cùng concept
3. Truyền state vào system prompt: `"Student asked about X 3 times. Level 4: provide explanation."`

---

### P3.2 — Dual Retrieval có thực sự dùng Graph ✅

**Yêu cầu:** Retrieval phải quét cả Graph (NetworkX) chứ không chỉ vector search.

**Thực tế:** Retriever implement **Triple Retrieval**, không phải Dual:

| Bước | Công nghệ | Mục đích |
|------|-----------|----------|
| 1. Vector Search: Chunks | ChromaDB | Tìm top-k đoạn văn liên quan |
| 2. Vector Search: Entities | ChromaDB | Tìm top-k entities trong query |
| 3. Graph Traversal: Neighbors | **PostgreSQL** (`GraphRepository.get_entity_neighbors()`) | Lấy relations của entities tìm được |

**Lưu ý quan trọng:** Retrieval KHÔNG dùng NetworkX trực tiếp. NetworkX chỉ dùng trong `GraphBuilder` (ingestion phase). Retrieval query SQL qua `GraphRepository`.

```python
# app/core/retriever.py
entities_res = chroma_client.query_entities(...)
found_entity_names = [m['entity_name'] for m in entities_res['metadatas'][0]]

if found_entity_names:
    relations = await self.graph_repo.get_entity_neighbors(doc_uuid, found_entity_names)
```

**Verdict:** ✅ **ĐẠT** — Nhưng audit plan cần điều chỉnh: Graph được dùng qua SQL repository, không phải NetworkX runtime. Đây là thiết kế hợp lý (SQL nhanh hơn load whole graph vào memory).

---

### P3.3 — Socratic không trả về Structured JSON ❌

**Yêu cầu:** Socratic Tutor AI phải trả về Structured JSON để backend parse và xử lý logic (quyết định "giải thích hay hỏi tiếp").

**Thực tế:** LLM trả về **text tự do** qua SSE stream. Không có JSON schema hay function calling nào bắt buộc LLM tuân thủ.

**System prompt hiện tại (`chat_service.py` dòng 204-214):**
```python
system_role = (
    "You are a Socratic tutor. You never give direct answers. Instead, "
    "you ask guiding questions to help the student find the answer themselves..."
)
```
→ Đây là natural language instruction, KHÔNG phải structured output schema.

**SSE events chỉ wrap metadata, không parse nội dung LLM:**
```json
// meta: {message_id, conversation_id}
// chunk: {delta: "..."}
// done: {content_full, context_used, found_entities}
```
`content_full` là raw text từ LLM — không được parse thành `{pedagogical_action, hint_level, should_explain}`.

**So sánh với `structured_extraction` đã có trong codebase:**
`llm_service.structured_extraction()` (dùng trong quiz feedback analysis, contradiction detection) đã có pattern dùng Pydantic model + retry. Pattern này CÓ TÁI SỬ DỤNG được cho Socratic — nhưng hiện tại KHÔNG dùng.

**Hệ quả:**
- Backend không thể programmatically quyết định pedagogical action
- Không thể track hint progression (level 1 → level 2 → explain)
- Không thể implement adaptive tutoring (điều chỉnh chiến lược theo user)

**Verdict:** ❌ **KHÔNG ĐẠT** — Cần:
1. Định nghĩa Pydantic model: `SocraticResponse(action: str, hint_level: int, content: str, should_explain: bool)`
2. Dùng `llm_service.structured_extraction()` hoặc OpenAI function calling
3. Backend parse JSON → quyết định: stream content, update attempt_count, trigger explanation mode

---

## Phase 4: Zettelkasten & Spaced Repetition

### P4.1 — Auto entity matching khi tạo Note ❌

**Yêu cầu:** Khi tạo Note, API phải tự động gọi `extract_and_match_entities()` để tạo liên kết ngược (backlinks) vào Graph Entities.

**Thực tế:** `note_service.py` có `BacklinkAIService` nhưng chỉ hoạt động khi **user manual gọi** `POST /notes/{id}/suggest-backlinks`. KHÔNG có auto-trigger khi `POST /notes`.

**Code hiện tại (`note_service.create_note`):**
```python
async def create_note(self, user_id, title, content, note_type, tags, metadata):
    note = await self.note_repo.create(
        user_id=user_id, title=title, content=content,
        note_type=note_type, tags=tags or [], metadata=metadata or {},
    )
    return note  # ❌ Không có entity extraction, không có auto-linking
```

**`suggest_backlinks` endpoint có tồn tại nhưng là manual:**
```python
# POST /notes/{id}/suggest-backlinks → gọi backlink_ai.suggest_backlinks_for_note()
# → Quét graph entities liên quan + tìm notes khác có nội dung tương tự
# → Trả về suggestions, KHÔNG tự động tạo link
```

**Mô hình hiện tại:**
```
User tạo note → Note được lưu → KHÔNG có gì xảy ra thêm
User muốn backlinks → Manual gọi /notes/{id}/suggest-backlinks
User thấy phù hợp → Manual gọi POST /notes/{id}/links để tạo link
```

**Mô hình kỳ vọng (Zettelkasten):**
```
User tạo note → Entity extraction tự động chạy
→ Match với graph entities → Tạo note_entity_link records
→ Gợi ý backlinks tự động → Auto-create links nếu confidence cao
```

**Verdict:** ❌ **KHÔNG ĐẠT** — Cần thêm entity extraction + auto-linking trong `create_note()`. Model `note_entity_link` đã tồn tại (`app/models/note_entity_link.py`) nhưng chưa được dùng khi create.

---

### P4.2 — SM-2 Algorithm ép cận ease_factor ✅

**Yêu cầu:** Thuật toán SM-2 phải ép cận `ease_factor >= 1.3` để không rớt quá thấp khi user quên nhiều.

**Thực tế:** `sm2_service.py` implement ĐÚNG:

```python
new_ease = current_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
new_ease = max(SM2_MIN_EASE, new_ease)  # SM2_MIN_EASE = 1.3 từ constants
```

Cũng có đầy đủ:
- Quality clamping: `max(0, min(5, quality))`
- Reset khi `quality < 3`: `repetitions = 0, interval = 1`
- Interval progression: 1 → 6 → `interval * ease_factor`
- Idempotency key chống duplicate review

**Verdict:** ✅ **ĐẠT** — SM-2 implement đúng chuẩn SuperMemo 2.

---

## Tổng hợp: Audit Scorecard

| Phase | Check | Yêu cầu | Thực tế | Status | Severity |
|-------|-------|---------|---------|--------|----------|
| **P1.1** | `status`/`processing_step` tách bạch | BR-002 | ✅ Enum riêng, 8 bước | ✅ ĐẠT | — |
| **P1.2** | `conversations` có `attempt_count` | BR-006 | ❌ Không có field | ❌ KHÔNG ĐẠT | 🔴 Critical |
| **P1.3** | Row-Level Security trên PostgreSQL | BR-001 | ❌ 25 migrations, 0 RLS | ❌ KHÔNG ĐẠT | 🔴 Critical |
| **P1.4** | ChromaDB check `embedding_dim` | BR-008 | ❌ Không validate | ❌ KHÔNG ĐẠT | 🔴 Critical |
| **P2.1** | Validation 409 khi doc processing | BR-011 | ✅ count_processing + hash dedup | ✅ ĐẠT | — |
| **P2.2** | Embedding cả chunks + entities | LightRAG | ✅ 2 collections riêng | ✅ ĐẠT | — |
| **P2.3** | Rollback before Retry | BR-016 | ⚠️ Idempotency sweep inline | ⚠️ ĐẠT (refactor) | 🟢 Low |
| **P3.1** | Backend track `attempt_count` | BR-006 | ❌ LLM tự nhớ qua history | ❌ KHÔNG ĐẠT | 🟡 Medium |
| **P3.2** | Dual retrieval dùng Graph | LightRAG | ✅ SQL-based (3 bước) | ✅ ĐẠT | — |
| **P3.3** | Socratic Structured JSON | BR-006 | ❌ Text tự do qua SSE | ❌ KHÔNG ĐẠT | 🟡 Medium |
| **P4.1** | Auto entity link khi tạo note | Zettelkasten | ❌ Manual suggest only | ❌ KHÔNG ĐẠT | 🟡 Medium |
| **P4.2** | SM-2 ép cận ease_factor | SM-2 spec | ✅ `max(1.3, ...)` | ✅ ĐẠT | — |

### Score

| Metric | Value |
|--------|-------|
| **✅ ĐẠT** | 5/12 (41.7%) |
| **⚠️ ĐẠT (cần refactor)** | 1/12 (8.3%) |
| **❌ KHÔNG ĐẠT** | 6/12 (50%) |
| **🔴 Critical** | 3 |
| **🟡 Medium** | 3 |
| **🟢 Low** | 0 |

---

## Đánh giá Audit Plan

### Audit Plan làm đúng

1. **Phát hiện chính xác 6/6 vấn đề thực sự tồn tại** trong codebase
2. **Ưu tiên đúng mức độ** — Infrastructure (Phase 1) là nền tảng, cần sửa trước
3. **Tập trung vào logic integrity** chứ không chỉ syntax — đây là cách tiếp cận đúng

### Audit Plan chưa chính xác

1. **P2.3 quá conservative** — Thực tế đã implement rollback/retry tốt hơn kỳ vọng (idempotency sweep + session rollback)
2. **P3.2 hiểu nhầm về NetworkX** — Retrieval dùng SQL `GraphRepository`, không phải NetworkX runtime. Đây là thiết kế hợp lý, không phải bug
3. **P2.1, P2.2, P4.2 flag để kiểm tra nhưng thực tế đã ĐẠT** — Audit plan nên phân biệt "need to verify" vs "likely missing"

### Kết luận về Audit Plan

**Chất lượng: CAO (8/10).** Plan phát hiện đúng các điểm mù quan trọng. Điểm trừ nhỏ vì một số flag là "false positive" (thực tế đã implement đúng).

---

## Recommended Action Plan

### Priority 1: Critical Fixes (Sprint 20)

| # | Task | Est. Effort | Files to Modify |
|---|------|-------------|-----------------|
| 1 | **ChromaDB embedding dimension guard** — Add `embedding_dim` to collection metadata, validate before add, auto-create new collection | 4h | `app/services/chroma_client.py`, `app/constants.py`, `app/core/pipeline.py` |
| 2 | **Row-Level Security migration** — Create migration enabling RLS on `documents`, `conversations`, `flashcards`, `notes`, `quiz_results` | 3h | `alembic/versions/`, `app/database.py` |
| 3 | **`attempt_count` tracking** — Add `metadata` JSON field to `conversations`, track in chat flow | 4h | `app/models/conversation.py`, `app/services/chat_service.py`, `app/api/chat.py` |

### Priority 2: Medium Fixes (Sprint 21)

| # | Task | Est. Effort | Files to Modify |
|---|------|-------------|-----------------|
| 4 | **Socratic Structured JSON** — Define Pydantic model, use `structured_extraction()` or function calling | 6h | `app/schemas/chat.py`, `app/services/chat_service.py`, `app/core/retriever.py` |
| 5 | **Auto entity linking khi tạo note** — Trigger `extract_and_match_entities()` in `create_note()` | 4h | `app/api/notes.py`, `app/services/note_service.py` |

### Priority 3: Refactoring (Sprint 22)

| # | Task | Est. Effort | Files to Modify |
|---|------|-------------|-----------------|
| 6 | **Extract `cleanup_partial_document_data()`** — Refactor inline logic trong worker thành hàm riêng | 2h | `app/worker/tasks.py` |

---

## Known Issues Not Covered by Audit Plan

Các vấn đề phát hiện thêm trong quá trình audit (ngoài scope của plan gốc):

### 1. 🔴 Document delete không hoàn toàn atomic

**Vấn đề:** `delete_document()` trong `document_service.py` xóa ChromaDB TRƯỚC, rồi mới xóa SQL. Nếu ChromaDB thành công nhưng SQL fail → **orphan embeddings đã bị xóa không thể khôi phục**.

```python
# document_service.py — delete_document()
# Bước 1: Xóa ChromaDB (KHÔNG rollback được)
chroma_client.delete_by_document_id(doc_id)

# Bước 2: Xóa SQL (có rollback)
await self.repo.delete(doc_id)
await self.session.commit()
```

**Rủi ro:** Nếu SQL fail (foreign key constraint, lock timeout), ChromaDB data đã mất vĩnh viễn. Rollback ở đây vô nghĩa vì ChromaDB không hỗ trợ transaction.

**Giải pháp:** Đổi thứ tự — xóa SQL TRƯỚC (trong transaction), nếu thành công thì xóa ChromaDB. Hoặc dùng compensating action: log lại ChromaDB IDs để re-insert nếu cần.

### 2. 🟡 Flashcard generation KHÔNG có SM-2 tuning cho auto-generated cards

**Vấn đề:** `FlashcardGenerationService` tạo cards với default params (`ease=2.5, interval=0, repetitions=0`). Cards sinh từ quiz wrong answers nên có độ khó cao hơn, nhưng KHÔNG được điều chỉnh SM-2 params phù hợp.

**Giải pháp đề xuất:** Auto-generated cards từ quiz wrong answers nên có `sm2_ease_factor = 2.3` (thấp hơn default) và `sm2_interval = 1` để review sớm hơn.

### 3. 🟡 `user_id` trong ChromaDB metadata là optional

**Vấn đề:** Trong `pipeline.py`, `user_id` chỉ được thêm vào metadata NẾU `user_id_str` tồn tại:
```python
chunk_meta = {"document_id": str(doc_id), "chunk_index": i}
if user_id_str:
    chunk_meta["user_id"] = user_id_str
```

Nếu pipeline được gọi mà không truyền `user_id`, vector sẽ KHÔNG có metadata filter → data leak risk nếu có bug ở app layer.

**Giải pháp:** Bắt buộc `user_id` khi khởi tạo pipeline. Raise error nếu None.

### 4. 🟢 `embeddings_service` fallback về zero vectors khi fail

**Vấn đề:** Khi OpenAI/Ollama fail, `generate_embeddings()` trả về zero vectors thay vì raise exception:
```python
except Exception as e:
    logger.error(f"OpenAI embedding failed: {e}")
    return [[0.0] * self.dimension] * len(texts)  # ❌ Silent fallback
```

Pipeline có validate zero vectors (`_is_valid_embedding`) và sẽ KHÔNG gửi lên ChromaDB → document được ingest mà KHÔNG có embeddings → retrieval không hoạt động.

**Đây là hành vi đúng** (không crash, vẫn ingest text), nhưng user có thể không biết rằng retrieval bị vô hiệu hóa. Cần cảnh báo rõ ràng.

---

## Conclusion

Audit plan đã **xác thực chính xác 6 khoảng trống** giữa thiết kế và implementation. Trong đó 3 vấn đề critical cần sửa ngay trước khi deploy production:

### Priority Matrix

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| 🔴 P0 | ChromaDB dimension guard | Crash/corruption khi đổi model | 4h |
| 🔴 P0 | Row-Level Security | Security gap nếu app layer bug | 3h |
| 🔴 P0 | `attempt_count` tracking | Socratic pedagogy unreliable | 4h |
| 🟡 P1 | Socratic structured JSON | Cannot implement adaptive tutoring | 6h |
| 🟡 P1 | Auto entity linking notes | Zettelkasten backlinks manual only | 4h |
| 🟢 P2 | Refactor cleanup function | Code maintainability | 2h |

### Điểm sáng đã implement tốt

| Component | Assessment | Details |
|-----------|-----------|---------|
| **Document Pipeline** | ✅ Xuất sắc | Idempotency sweep, dual embedding, graph builder integration |
| **SM-2 Algorithm** | ✅ Đúng chuẩn | Ease factor floor (1.3), interval progression, idempotency key |
| **Dual Retrieval** | ✅ Hiệu quả | Triple retrieval (ChromaDB chunks → ChromaDB entities → SQL graph neighbors) |
| **Upload Validation** | ✅ Đầy đủ | 409 conflict, hash dedup, concurrent processing check |
| **Worker Error Handling** | ✅ Đúng pattern | PermanentProcessingError không retry, runtime error có retry + rollback |

### Điểm cần cải thiện

| Component | Gap | Root Cause |
|-----------|-----|------------|
| **Socratic Chat** | Không có attempt_count, structured response | Toàn bộ pedagogy logic giao cho LLM prompt |
| **ChromaDB** | Không validate embedding_dim | Constants có định nghĩa nhưng không dùng |
| **PostgreSQL** | Không có RLS | Design có nhưng migrations chưa implement |
| **Notes** | Không auto entity link | Backlink AI có nhưng chỉ manual trigger |
| **Document Delete** | ChromaDB delete trước SQL | Thứ tự thao tác chưa tối ưu |

### Đánh giá tổng thể

**Chất lượng codebase: KHÁ (7/10)**

- **Architecture:** Đúng hướng — LightRAG pipeline, dual retrieval, SM-2, repository pattern đều implement đúng
- **Completeness:** ~58% (7/12 checks đạt hoặc gần đạt) — còn gap ở Agent orchestration và RLS
- **Robustness:** Tốt — idempotency, rollback, retry, timeout đều có
- **Security:** Cần cải thiện — RLS missing, ChromaDB user_id optional, dimension guard absent

**Khuyến nghị:** Fix 3 vấn đề P0 trước khi production. P1-P2 có thể làm trong sprint tiếp theo.

---

© 2026 AetherTutor Team
*Audit Report — Generated 2026-04-12*
*Source: implementation_plan.md.resolved (Gemini Brain) + Full codebase verification*
*Verification depth: 16 files read across models, services, APIs, workers, pipelines, migrations, constants*
