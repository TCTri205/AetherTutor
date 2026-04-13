# 🔍 AetherTutor - Comprehensive Code Review Report

**Ngày review:** 13/04/2026  
**Reviewer:** Qwen Code (coder-model)  
**Phạm vi:** Toàn bộ codebase trên branch `master`  
**Commit:** `9c0d2df` - feat(s17): add media microlearning platform with transcription support  
**Version:** v0.1 (MVP)

---

## 📊 Tổng quan

| Hạng mục | Kết quả |
|----------|---------|
| **Files đã review** | 75+ files |
| **Critical** | 🔴 1 |
| **Suggestion** | 🟡 22 |
| **Nice to have** | 🟢 6 |
| **Verdict** | 🟡 **Request Changes** |

### Assessment tổng thể

AetherTutor là một hệ thống học tập AI được xây dựng khá tốt với kiến trúc phân lớp rõ ràng (API → Services → Repositories → Models), sử dụng FastAPI, PostgreSQL, Redis, ChromaDB và LightRAG. Tuy nhiên, có **1 vấn đề Critical** cần sửa ngay và **nhiều vấn đề Suggestion** ảnh hưởng đến maintainability, performance và security.

---

## 🚨 Critical Findings (Must Fix)

### C-1: Dynamic class creation trong `register_agent` gây Memory Leak

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/agents.py:119-146` |
| **Source** | `[review]` |
| **Severity** | **Critical** |
| **Impact** | Memory leak, class definitions tích lũy theo thời gian |

**Mô tả:**

Endpoint `POST /agents` tạo class động (`class CustomAgent(BaseAgent)`) bên trong route handler. Mỗi khi endpoint được gọi, một class definition mới được tạo ra và đăng ký vào `agent_registry`. Python không garbage collect các class definitions này.

**Code hiện tại:**

```python
@router.post("", status_code=201)
async def register_agent(request: AgentCreateRequest, ...):
    try:
        from app.core.agents.base_agent import BaseAgent

        class CustomAgent(BaseAgent):  # ← TẠO CLASS MỚI MỖI REQUEST
            name = request.name
            version = "1.0.0"
            description = request.description
            icon = request.icon
            # ...
```

**Tại sao nghiêm trọng:**

1. **Memory leak:** Mỗi request tạo 1 class object mới + 1 instance. Các class definitions không bị GC vì được registry tham chiếu.
2. **Violation of Python best practices:** Class definitions nên ở module level.
3. **Scale issue:** 1000 registrations = 1000 class definitions trong memory.

**Đề xuất sửa:**

Sử dụng factory pattern với class định nghĩa ở module level:

```python
# app/core/agents/custom_agent.py (module level)
from app.core.agents.base_agent import BaseAgent, AgentCapabilities

class CustomAgent(BaseAgent):
    """Generic custom agent với configurable parameters."""

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        capabilities: list[AgentCapabilities],
        custom_config: dict | None = None,
    ):
        self._name = name
        self._description = description
        self._system_prompt = system_prompt
        self._capabilities = capabilities
        self._custom_config = custom_config or {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def _default_system_prompt(self) -> str:
        return self._system_prompt

    async def execute(self, **kwargs) -> dict:
        # Implementation dựa trên custom_config
        return {"status": "success", "config": self._custom_config}

    def get_capabilities(self):
        return self._capabilities
```

```python
# app/api/agents.py (endpoint sửa đổi)
@router.post("", status_code=201)
async def register_agent(request: AgentCreateRequest, ...):
    from app.core.agents.custom_agent import CustomAgent

    # Tạo instance từ factory class — KHÔNG tạo class definition mới
    agent = CustomAgent(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt_template,
        capabilities=[
            AgentCapabilities(cap) for cap in request.capabilities
        ],
        custom_config=request.custom_config,
    )

    agent_id = agent_registry.register(
        agent,
        agent_id=request.name,
        enabled=True,
        metadata={"custom": True, "owner_id": str(user_id)},
    )
    # ...
```

---

## 🟡 Suggestion Findings

### S-1: Blocking sync calls trong async ARQ workers

| Thuộc tính | Giá trị |
|------------|---------|
| **Files** | `app/worker/tasks.py:75`, `app/worker/tasks.py:162` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** (impact cao) |

**Mô tả:**

Hai synchronous blocking calls chạy trong async ARQ worker, blocking toàn bộ event loop:

1. **ChromaDB cleanup** (line 75):
   ```python
   chroma_client.delete_by_document_id(doc_id)  # SYNC — blocks event loop
   ```

2. **PDF extraction** (line 162):
   ```python
   text = pdf_extractor.extract_text(doc.file_path)  # SYNC — blocks event loop
   ```

**Impact:** Trong khi các calls này chạy (đặc biệt với file PDF lớn hàng trăm trang), không ARQ job nào khác có thể thực thi. Gây timeout cascade và giảm worker throughput.

**Đề xuất sửa:**

```python
import asyncio

# ChromaDB cleanup
await asyncio.to_thread(chroma_client.delete_by_document_id, doc_id)

# PDF extraction
text = await asyncio.to_thread(pdf_extractor.extract_text, doc.file_path)
```

---

### S-2: Inconsistent dependency injection pattern

| Thuộc tính | Giá trị |
|------------|---------|
| **Files** | `app/api/notes.py:50-66`, `app/api/collaboration.py` (tất cả endpoints) |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Codebase sử dụng 3 patterns khác nhau để inject services:

1. **Notes API** — Tạo service thủ công trong helper function (không dùng `Depends()`):
   ```python
   def get_note_service(db: AsyncSession) -> NoteService:
       llm_service = LLMService()  # ← Tạo mới mỗi lần
       note_repo = NoteRepository(db)
       return NoteService(...)
   ```

2. **Collaboration API** — Bypasses repository pattern, dùng raw ORM trực tiếp:
   ```python
   db.add(team)
   await db.flush()
   db.add(membership)
   await db.commit()
   ```

3. **Documents API** — Correct DI pattern:
   ```python
   def get_doc_service(db: AsyncSession = Depends(get_db), ...) -> DocumentService:
       return DocumentService(db, arq_pool, user_id=user_id)
   ```

**Đề xuất:** Standardize toàn bộ codebase dùng FastAPI `Depends()` pattern như Documents API.

---

### S-3: Missing database indexes trên foreign keys

| Thuộc tính | Giá trị |
|------------|---------|
| **Files** | `app/models/conversation.py`, `app/models/document.py`, `app/models/graph.py` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Các FK columns quan trọng thiếu explicit index, dẫn đến sequential scans trên bảng lớn:

| Model | Column | Query affected |
|-------|--------|----------------|
| `Message` | `conversation_id` | `get_messages`, `get_last_n_messages` |
| `Document` | `user_id` | `get_by_user`, `list_with_counts` |
| `GraphRelation` | `document_id` | `get_all_relations`, `delete_by_document_id` |
| `GraphEntity` | `document_id` | `get_all_entities`, `count_entities` |
| `Conversation` | `document_id` | `list_conversations` |

**Đề xuất thêm vào `__table_args__`:**

```python
# Message model
__table_args__ = (
    Index("idx_messages_conversation_id", "conversation_id"),
)

# Document model
__table_args__ = (
    Index("idx_documents_user_id", "user_id"),
)

# GraphRelation model
__table_args__ = (
    Index("idx_graph_relations_document_id", "document_id"),
)

# GraphEntity model
__table_args__ = (
    Index("idx_graph_entities_document_id", "document_id"),
)

# Conversation model
__table_args__ = (
    Index("idx_conversations_document_id", "document_id"),
)
```

---

### S-4: N+1 query pattern trong `get_global_graph`

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/graph.py:275-310` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Endpoint lặp qua tất cả document IDs của user và execute 2 queries mỗi document:

```python
for doc_id in user_document_ids:
    entities = await graph_repo.get_all_entities(doc_id)     # 1 query/doc
    relations = await graph_repo.get_all_relations(doc_id)    # 1 query/doc
```

50 documents = **100 database queries** = 1-2 giây latency.

**Đề xuất:** Dùng single query với `WHERE document_id IN (...)`:

```python
# Repository method mới
async def get_entities_by_document_ids(
    self, document_ids: list[uuid.UUID]
) -> list[GraphEntity]:
    stmt = select(GraphEntity).where(
        GraphEntity.document_id.in_(document_ids)
    )
    result = await self._session.execute(stmt)
    return result.scalars().all()
```

---

### S-5: `get_note_graph` load toàn bộ graph vào memory

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/repositories/note_repo.py:181-219` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Method fetch ALL notes và ALL links cho user không có pagination hay limit. User với 5000 notes + 10000 links = 50-100MB+ RAM và several seconds để serialize.

**Đề xuất:**

```python
async def get_note_graph(
    self, user_id: uuid.UUID, limit: int = 500
) -> dict:
    # Fetch limited notes
    notes_stmt = select(Note).where(
        Note.user_id == user_id
    ).limit(limit)
    notes = (await self._session.execute(notes_stmt)).scalars().all()

    # Chỉ fetch links cho notes đã lấy
    note_ids = [n.id for n in notes]
    links_stmt = select(NoteLink).where(
        NoteLink.source_note_id.in_(note_ids) |
        NoteLink.target_note_id.in_(note_ids)
    )
    links = (await self._session.execute(links_stmt)).scalars().all()
    # ...
```

---

### S-6: Deprecated `@router.on_event("startup")`

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/agents.py:48-56` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

FastAPI 0.103+ đã deprecate `on_event` decorator. Sẽ break trong các phiên bản tương lai.

**Đề xuất:** Chuyển vào `app/main.py` lifespan:

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AetherTutor...")

    # Register agents
    from app.core.agents.registry import agent_registry
    from app.core.agents.language_agent import LanguageAgent
    from app.core.agents.math_agent import MathAgent

    agent_registry.register(LanguageAgent(), agent_id="language_agent")
    agent_registry.register(MathAgent(), agent_id="math_agent")

    app.state.arq_pool = await get_redis_pool()
    yield
    # Shutdown
    await app.state.arq_pool.close()
```

---

### S-7: Debug endpoint `/test-ingest` trong production code

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/documents.py:32-77` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Endpoint bypasses worker queue và processes documents synchronously. Dù có check `DEBUG`/`APP_ENV`, vẫn tồn tại trong production code.

**Rủi ro:** Nếu `DEBUG=true` accidentally set trong production, endpoint này cho phép direct text ingestion bỏ qua tất cả validation và queue.

**Đề xuất:** Move to separate `debug_router.py` chỉ include khi `settings.DEBUG=True`:

```python
# app/main.py
if settings.DEBUG:
    from app.api.debug_router import router as debug_router
    app.include_router(debug_router, prefix="/api/v1/debug")
```

---

### S-8: Bare `except Exception` — lộ internal details

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/flashcards.py:96-99`, `app/api/quiz.py` (nhiều nơi) |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Code hiện tại:**

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
```

**Rủi ro:** `str(e)` có thể lộ internal implementation details (paths, query strings, stack traces).

**Đề xuất:**

```python
except Exception as e:
    logger.exception(f"Flashcard review failed: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

### S-9: Unused `request: Request` parameters

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/topics.py` (12 endpoints: lines 45, 73, 91, 109, 134, 156, 177, 204, 225, 250, 275, 299) |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:** `request: Request` được declare trong signature nhưng NEVER sử dụng trong body.

**Đề xuất:** Remove parameter khỏi tất cả 12 endpoints.

---

### S-10: Schemas định nghĩa inline trong routers

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/graph.py:583-608` (`ObsidianImportRequest`), `app/api/graph.py:629-641` (`MergeEntitiesRequest`) |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:** Pydantic models định nghĩa inline trong router file thay vì trong `app/schemas/`.

**Đề xuất:** Move sang `app/schemas/lightrag.py` hoặc `app/schemas/import.py`.

---

### S-11: Mixed import styles (relative vs absolute)

| Thuộc tính | Giá trị |
|------------|---------|
| **Files** | `app/api/quiz.py` (absolute), `app/api/flashcards.py` (relative) |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:** Không nhất quán — `quiz.py` dùng `from app.database import get_db` trong khi `flashcards.py` dùng `from ..database import get_db`.

**Đề xuất:** Standardize một style. PEP 8 recommends relative imports within a package.

---

### S-12: Deprecated Pydantic v2 config pattern

| Thuộc tính | Giá trị |
|------------|---------|
| **Files** | `app/schemas/quiz.py:86,118,131,141`, `app/schemas/topic.py:31-42` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Code hiện tại:**

```python
class QuizResponse(BaseModel):
    class Config:
        from_attributes = True
```

**Đề xuất migrate sang Pydantic v2:**

```python
from pydantic import BaseModel, ConfigDict

class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

---

### S-13: Inline imports trong handler functions

| Thuộc tính | Giá trị |
|------------|---------|
| **Files** | `app/api/flashcards.py:200`, `app/api/quiz.py:413-420` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:** Imports nằm trong handler functions — tạo imports trên mỗi request, hides dependencies.

**Đề xuất:** Move imports to module level.

---

### S-14: `collaboration.py` bypasses repository pattern

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/collaboration.py:49-70` (và nhiều nơi khác) |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:** Team CRUD dùng raw SQLAlchemy ORM trực tiếp trong route handlers (`db.add(team)`, `db.commit()`) thay vì qua repository classes như các modules khác.

**Đề xuất:** Tạo `TeamRepository` và `SharedResourceRepository` classes trong `app/repositories/`.

---

### S-15: Dead code — `get_current_user`

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/dependencies.py:28-35` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Code:**

```python
async def get_current_user(db: DBDependency):
    """To be implemented: JWT Auth & User handling."""
    return None  # ← Dead code
```

**Đề xuất:** Remove hoặc implement properly.

---

### S-16: `get_doc_service` có misleading default

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/documents.py:27` |
| **Source** | `[review]` |
| **Severity** | **Nice to have** |

**Code:**

```python
def get_doc_service(..., request: Request = None, ...):
    arq_pool = request.app.state.arq_pool if request else None  # ← request luôn được FastAPI pass
```

**Đề xuất:** Remove default `= None`, make `request` required.

---

### S-17: `get_push_subscription` bypasses abstraction

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/push.py:55-62` |
| **Source** | `[review]` |
| **Severity** | **Nice to have** |

**Code:**

```python
raw_key = f"push:vapid:{user_id}"
subscription = await notification_service.redis.get(raw_key)
```

**Đề xuất:** Tạo repository method hoặc service method cho consistent data access.

---

### S-18: Redundant logger import

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/quiz.py:413-420` |
| **Source** | `[review]` |
| **Severity** | **Nice to have** |

**Code:**

```python
logger = logging.getLogger(__name__)  # ← line 30 (module level)

async def submit_feedback(...):
    import logging  # ← redundant import inside function
    logger = logging.getLogger(__name__)
```

**Đề xuất:** Remove inline import, dùng module-level logger.

---

### S-19: `get_chat_service` dead code — defined nhưng never used

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/chat.py:22-26` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Function `get_chat_service` được định nghĩa như một FastAPI dependency nhưng **không bao giờ được sử dụng** qua `Depends()`. Thay vào đó, mỗi endpoint tự tạo service instances thủ công:

```python
async def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    chat_repo = ChatRepository(db)
    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)
    return ChatService(chat_repo, retriever)  # ← Defined but NEVER called via Depends()
```

Trong khi đó, `chat_stream` endpoint imports và tạo services inline:

```python
async def chat_stream(...):
    async def stream_generator():
        async with AsyncSessionLocal() as stream_session:
            chat_repo = ChatRepository(stream_session)  # ← Manual instantiation
            # ...
```

**Impact:**
1. **Dead code** — gây nhầm lẫn về intended DI pattern
2. **Khó test** — không thể mock ChatService trong unit tests
3. **Vi phạm DRY** — repository creation bị lặp lại ở nhiều nơi

**Đề xuất:** Hoặc dùng `get_chat_service` qua `Depends()` trong endpoints, hoặc remove nó và document lý do tại sao dùng manual instantiation.

---

### S-20: `socratic_chat_legacy` — Legacy endpoint với security pattern cũ

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/chat.py:159-179` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Endpoint legacy `socratic_chat_legacy` sử dụng `get_optional_user_id` dependency (trả về None nếu không có auth) thay vì `get_current_user_id` (yêu cầu auth). Điều này có nghĩa **bất kỳ ai** có thể gọi endpoint này mà không cần authentication.

```python
@router.post("/socratic", response_model=MessageResponse)
async def socratic_chat_legacy(
    document_id: str,
    message: str = Body(..., embed=True),
    mode: str = "socratic",
    user_id: Optional[str] = Depends(get_optional_user_id),  # ← OPTIONAL AUTH!
    db: AsyncSession = Depends(get_db)
):
```

Endpoint cũng import `llm_service` trực tiếp và sử dụng raw repository construction thay vì service layer.

**Rủi ro:**
1. **Auth bypass** — anyone can call this endpoint without authentication
2. **LLM cost** — unauthenticated calls still consume LLM API tokens
3. **Maintenance burden** — legacy code có thể có outdated security patterns

**Đề xuất:** Deprecate với decorator hoặc remove nếu không còn được frontend sử dụng.

---

### S-21: `graph.py` — Single file 1238+ lines, vi phạm Single Responsibility

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/graph.py` (1238 lines) |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

File `graph.py` chứa **quá nhiều responsibilities** trong một module duy nhất:

| Responsibility | Approx lines |
|----------------|-------------|
| Graph query & retrieval | ~100 |
| Document graph view | ~100 |
| Global graph aggregation | ~100 |
| Entity CRUD | ~150 |
| Relation CRUD | ~100 |
| Entity alias resolution | ~80 |
| Obsidian import endpoint | ~80 |
| Entity merge endpoint | ~60 |
| Backlinks & tags | ~120 |
| Mermaid diagram generation | ~100 |
| Multi-document chat | ~100 |
| Community detection | ~80 |
| Cross-verification | ~70 |

**Impact:**
1. **Hard to maintain** — merge conflicts khi nhiều developers sửa cùng file
2. **Hard to test** — cần mock quá nhiều dependencies
3. **Hard to review** — PR review trở nên khó khăn
4. **Vi phạm SRP** — một module nên có một lý do để thay đổi

**Đề xuất:** Split thành nhiều routers:

```
app/api/graph/
├── __init__.py          # Mount sub-routers
├── query.py             # Graph query, retrieval
├── entities.py          # Entity CRUD, merge, alias
├── visualization.py     # Mermaid, community detection
├── import_export.py     # Obsidian import
└── multi_doc.py         # Cross-document operations
```

---

### S-22: `_topic_response` bypasses Pydantic `model_validate()`

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/api/topics.py:25-39` |
| **Source** | `[review]` |
| **Severity** | **Suggestion** |

**Mô tả:**

Helper function `_topic_response` manually constructs `TopicResponse` từ ORM objects thay vì dùng Pydantic's `model_validate()`:

```python
def _topic_response(topic) -> TopicResponse:
    return TopicResponse(
        id=str(topic.id),
        user_id=str(topic.user_id),
        name=topic.name,
        # ... manually mapping each field
        created_at=str(topic.created_at),  # ← Manual string conversion
        updated_at=str(topic.updated_at),
    )
```

Trong khi các modules khác (flashcards.py, notes.py) dùng pattern nhất quán:

```python
return NoteRead.model_validate(note)  # ← Clean, automatic
```

**Impact:**
1. **Code duplication** — 14 lines of manual mapping per response
2. **Bypasses Pydantic validation** — không tự động validate field types
3. **Manual string conversion của timestamps** — error-prone, không nhất quán với ISO format
4. **Maintenance burden** — mỗi khi schema thay đổi, phải update function thủ công

**Đề xuất:** Dùng `model_validate()` với `from_attributes=True`:

```python
# Trong schema
class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # ... fields

# Trong endpoint
return TopicResponse.model_validate(topic)  # ← One line, automatic validation
```

---

## 🟢 Nice to have Findings

### N-1: `get_flashcard_stats` makes 5+ separate DB queries

| File | `app/api/flashcards.py:127-139` |
|------|----------------------------------|
| **Issue** | Stats endpoint gọi `count_by_user`, `get_due_cards_count`, `session_repo.get_stats` (4+ queries) = 6+ round trips |
| **Fix** | Combine vào single aggregated query với SQL aggregation |

### N-2: `datetime.utcnow()` deprecated trong Python 3.12+

| File | `app/repositories/flashcard_repo.py:67-78` |
|------|---------------------------------------------|
| **Issue** | Dùng Python-side `datetime.utcnow()` thay vì DB-side `func.now()` |
| **Fix** | `.where(Flashcard.sm2_next_review <= func.now())` |

### N-3: Large PDF loaded fully vào memory

| File | `app/services/document_service.py:55-58` |
|------|-------------------------------------------|
| **Issue** | `content = await file.read()` đọc toàn bộ file vào memory |
| **Fix** | Stream file to disk using `aiofiles` in chunks |

### N-4: `_enrich_document` N+1 pattern

| File | `app/services/document_service.py:125-137` |
|------|---------------------------------------------|
| **Issue** | 2 separate SQL queries + 2 filesystem calls per document |
| **Fix** | Remove hoặc dùng single JOIN query |

### N-5: ChromaClient collection cache never invalidates

| File | `app/services/chroma_client.py:39-75` |
|------|----------------------------------------|
| **Issue** | `_collections_cache` lưu collection objects indefinitely, không có TTL |
| **Fix** | Add cache invalidation on errors hoặc TTL-based cache |

### N-6: `get_global_graph` performs N database queries trong loop

| File | `app/api/graph.py:275-310` |
|------|------------------------------|
| **Issue** | Lặp qua document IDs, execute `get_all_entities` + `get_all_relations` mỗi doc |
| **Fix** | Single query với `WHERE document_id IN (...)` |

---

## 📈 Performance & Scalability Assessment

| Area | Status | Ghi chú |
|------|--------|---------|
| **Database Indexes** | ⚠️ Needs work | Missing indexes trên 5+ critical FK columns |
| **Query Optimization** | ⚠️ Needs work | N+1 patterns trong graph/note operations |
| **Async Correctness** | 🔴 Needs work | 2 blocking sync calls trong ARQ workers |
| **Memory Management** | ⚠️ Needs work | Graph loading, PDF streaming, dynamic class creation |
| **Caching** | ✅ Good | ChromaClient cache exists (needs TTL) |
| **Connection Pools** | ✅ Good | SQLAlchemy async sessions configured correctly |
| **Background Jobs** | ✅ Good | ARQ worker với retry logic và distributed locks |

---

## 🔐 Security Assessment

| Area | Status | Ghi chú |
|------|--------|---------|
| **JWT Secret Validation** | ✅ Good | Production startup rejects weak secrets |
| **Row-Level Security** | ✅ Good | `set_config('app.current_user_id')` properly implemented |
| **CORS Configuration** | ✅ Good | Configurable via `ALLOWED_ORIGINS` env var |
| **Rate Limiting** | ✅ Good | SlowAPI với per-endpoint limits (5-60/minute) |
| **Input Validation** | ⚠️ Mixed | Một số endpoints dùng bare `except Exception` lộ details |
| **File Upload** | ✅ Good | 50MB limit, `.pdf` extension validation, SHA-256 hash |
| **SQL Injection** | ✅ Good | SQLAlchemy ORM prevents raw SQL injection |
| **Debug Endpoints** | ⚠️ Warning | `/test-ingest` exists in production code |
| **Secrets in Code** | ✅ Good | No hardcoded credentials (uses `.env`) |

---

## ✅ Strengths

1. **Kiến trúc phân lớp rõ ràng:** API → Services → Repositories → Models — đúng SOLID principles
2. **Row-Level Security:** Implement đúng với PostgreSQL `set_config()` + RLS policies
3. **Error handling:** Custom exception hierarchy (`AppError`, `ValidationError`, `ResourceNotFoundError`, `DuplicateResourceError`, `InfrastructureError`)
4. **Structured logging:** Correlation IDs qua `contextvars`, JSON formatting cho production
5. **Rate limiting:** SlowAPI integration với per-endpoint limits được định nghĩa trong `constants.py`
6. **Background jobs:** ARQ worker với retry logic, distributed locks, và cron jobs
7. **Testing foundation:** pytest-asyncio configured, 18+ unit tests, 20+ integration tests
8. **Docker Compose:** Multi-service orchestration tốt với health checks
9. **SM-2 Algorithm:** Flashcard spaced repetition được implement đúng
10. **LightRAG Integration:** Knowledge graph với vector retrieval qua ChromaDB
11. **Constants centralization:** Magic numbers được tập trung trong `constants.py`
12. **Idempotency:** Document processing có idempotency sweep trước khi xử lý lại

---

## 🎯 Recommended Action Plan

### 🔴 Immediate (Before next release)

| # | Action | File | Effort |
|---|--------|------|--------|
| 1 | **Fix dynamic class creation** — refactor to factory pattern | `app/api/agents.py` | 2h |
| 2 | **Wrap blocking calls** in `asyncio.to_thread()` | `app/worker/tasks.py` | 30m |

### 🟡 Short-term (Next sprint)

| # | Action | Files | Effort |
|---|--------|-------|--------|
| 3 | Add database indexes on FK columns | 5 model files | 1h + migration |
| 4 | Fix N+1 query patterns in graph operations | `graph.py`, `note_repo.py` | 3h |
| 5 | Standardize dependency injection | `notes.py`, `collaboration.py` | 2h |
| 6 | Migrate Pydantic v2 config patterns | `quiz.py`, `topic.py` schemas | 30m |
| 7 | Move debug endpoints to separate router | `documents.py` → `debug_router.py` | 1h |
| 8 | Fix bare exception handlers | `flashcards.py`, `quiz.py` | 30m |
| 9 | Remove unused `request: Request` params | `topics.py` (12 endpoints) | 15m |
| 10 | Move inline schemas to `app/schemas/` | `graph.py` | 30m |
| 11 | Deprecate/remove legacy chat endpoint | `chat.py:socratic_chat_legacy` | 15m |
| 12 | Remove dead `get_chat_service` DI | `chat.py:22-26` | 15m |
| 13 | Split `graph.py` thành sub-routers | `graph.py` | 4h |
| 14 | Migrate `_topic_response` to `model_validate()` | `topics.py` | 30m |

### 🟢 Medium-term (Future iterations)

| # | Action | Effort |
|---|--------|--------|
| 15 | Add pagination to `get_note_graph` | 2h |
| 16 | Implement ChromaClient cache invalidation | 1h |
| 17 | Stream PDF uploads in chunks | 2h |
| 18 | Remove dead code (`get_current_user`, redundant imports) | 30m |
| 19 | Standardize import styles (relative vs absolute) | 1h |
| 20 | Create `TeamRepository` for collaboration API | 2h |
| 21 | Combine stats queries into aggregated query | 1h |
| 22 | Replace `datetime.utcnow()` with `func.now()` | 30m |

---

## 📋 Checklist xác nhận sau khi sửa

- [ ] C-1: Dynamic class creation refactored → factory pattern
- [ ] S-1: Sync calls wrapped in `asyncio.to_thread()`
- [ ] S-3: Database indexes added + migration created
- [ ] S-4: N+1 queries fixed với batch queries
- [ ] S-2: Dependency injection standardized
- [ ] S-12: Pydantic v2 config migrated
- [ ] S-7: Debug endpoints moved to separate router
- [ ] S-8: Exception handlers không lộ internal details
- [ ] S-9: Unused request params removed
- [ ] S-10: Inline schemas moved to `app/schemas/`
- [ ] S-11: Import styles standardized
- [ ] S-13: Inline imports moved to module level
- [ ] S-14: TeamRepository created
- [ ] S-15: Dead code removed
- [ ] S-19: `get_chat_service` removed hoặc được sử dụng qua `Depends()`
- [ ] S-20: Legacy `socratic_chat_legacy` endpoint deprecated/removed
- [ ] S-21: `graph.py` split thành sub-routers
- [ ] S-22: `_topic_response` migrated to `model_validate()`
- [ ] N-2: `func.now()` thay thế `datetime.utcnow()`

---

## 📝 Phụ lục

### A. Files đã review

| Category | Files |
|----------|-------|
| **Core** | `main.py`, `config.py`, `database.py`, `dependencies.py`, `constants.py`, `logging_config.py` |
| **API (18 files)** | `documents.py`, `chat.py`, `graph.py`, `flashcards.py`, `quiz.py`, `notes.py`, `auth.py`, `users.py`, `topics.py`, `agents.py`, `collaboration.py`, `push.py`, `media.py`, `websocket_handlers.py`, `limiter.py`, `dependencies.py` |
| **Services (27 files)** | `llm_service.py`, `embedding_service.py`, `chat_service.py`, `document_service.py`, `note_service.py`, `sm2_service.py`, `flashcard_generation_service.py`, `backlink_ai_service.py`, `auth_service.py`, `security.py`, `notification_service.py`, `email_service.py`, `transcription_service.py`, `youtube_service.py`, `entity_resolution_service.py`, `entity_alias_service.py`, `cross_verification_service.py`, `quiz_analysis_service.py`, `topic_service.py`, `backlink_service.py`, `tag_service.py`, `chroma_client.py`, `pdf_extractor.py`, `code_parser.py`, `obsidian_vault_importer.py`, `user_service.py`, `backlink_ai_service.py` |
| **Repositories (15 files)** | `document_repo.py`, `chunk_repo.py`, `graph_repo.py`, `flashcard_repo.py`, `note_repo.py`, `quiz_repo.py`, `chat_repo.py`, `study_session_repo.py`, `note_entity_link_repo.py`, `base.py`, `session.py`, `topic.py`, `user.py` |
| **Models (19 files)** | `user.py`, `document.py`, `flashcard.py`, `quiz.py`, `note.py`, `topic.py`, `graph.py`, `conversation.py`, `team.py`, `shared_resource.py`, `note_entity_link.py`, `note_topic.py`, `document_topic.py`, `entity_document.py`, `transcript.py`, `study_session_group.py`, `user_session.py`, `base.py` |
| **Worker (3 files)** | `tasks.py`, `queue.py` |
| **Middleware (2 files)** | `logging.py` |
| **Core** | `exceptions.py`, `entity_extractor.py`, `retriever.py`, `pipeline.py`, `graph_builder.py`, `visualizer_agent.py`, `examiner_agent.py`, `graph_cache.py`, `agents/registry.py`, `agents/base_agent.py`, `agents/language_agent.py`, `agents/math_agent.py` |
| **Schemas** | `note.py`, `flashcard.py`, `quiz.py`, `topic.py`, `agent.py`, `lightrag.py` |

### B. Công cụ sử dụng

| Tool | Purpose |
|------|---------|
| Multi-agent review | 4 agents review song song (Security, Architecture, Services/Workers, Models/DB) |
| Performance audit | Separate agent cho N+1, blocking calls, indexes |
| Manual review | Đọc trực tiếp 20+ files quan trọng |

### C. Tài liệu tham khảo

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [ARQ Documentation](https://arq-docs.helpmanual.io/)
- [PostgreSQL Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

---

> **Generated by:** Qwen Code (coder-model) via `/review`  
> **Date:** 2026-04-13  
> **Branch:** master  
> **Commit:** `9c0d2df`
