# Báo cáo Triển khai Stage 3: Sprint 9 — Interactive Graph Editing

> **Date:** 2026-04-12
> **Author:** AetherTutor Team
> **Status:** ✅ COMPLETE
> **Parent:** [Stage 3 Plan](../plans/2026-04-10_stage3_visualization_multimedia.md)

---

## Tổng quan

Sprint 9 triển khai khả năng chỉnh sửa Knowledge Graph trực tiếp trên UI với cơ chế optimistic concurrency control, audit logging, và Redis cache invalidation.

---

## Chi tiết triển khai

### 1. Database Migration

**File mới:** `alembic/versions/s9a1b2c3d4e5_stage3_graph_editing_version_audit.py`

**Thay đổi schema:**

| Bảng | Cột thêm | Mục đích |
|------|----------|----------|
| `graph_entities` | `version INT DEFAULT 1 NOT NULL` | Optimistic concurrency control |
| `graph_entities` | `updated_at TIMESTAMP` | Audit trail |
| `graph_relations` | `user_id UUID NOT NULL` | User isolation (BR-001) |
| `graph_relations` | `version INT DEFAULT 1 NOT NULL` | Optimistic concurrency control |
| `graph_relations` | `updated_at TIMESTAMP` | Audit trail |
| *(mới)* `graph_edit_log` | Toàn bộ | Audit log table |

**Indexes mới:**
- `idx_graph_entities_version`
- `idx_graph_relations_version`
- `idx_graph_relations_user_id`
- `idx_graph_edit_log_user_id`, `idx_graph_edit_log_document_id`, `idx_graph_edit_log_created_at`

**Migration strategy:**
- `user_id` trên `graph_relations` được backfill từ `documents.user_id` trước khi set NOT NULL

---

### 2. Model Updates

**File:** `app/models/graph.py`

- Thêm `version: Mapped[int]` vào `GraphEntity` và `GraphRelation`
- Thêm `user_id: Mapped[uuid.UUID]` vào `GraphRelation`
- Tạo model `GraphEditLog` cho audit trail

---

### 3. Repository Extensions

**File:** `app/repositories/graph_repo.py` (+250 dòng)

| Method | Chức năng |
|--------|-----------|
| `create_entity()` | Tạo entity mới, validate uniqueness (document_id, canonical_name) |
| `update_entity()` | Cập nhật với optimistic concurrency (`WHERE version = expected_version`) |
| `delete_entity()` | Xóa entity với version check, cascade delete relations |
| `create_relation()` | Tạo relation, validate source/target entities tồn tại, chống self-reference |
| `delete_relation()` | Xóa relation với version check |
| `log_edit()` | Async audit logging (fire-and-forget, không block main operation) |

**Optimistic Concurrency Control:**
```sql
UPDATE graph_entities SET ..., version = version + 1
WHERE id = ? AND user_id = ? AND version = ?
```
- Nếu 0 rows affected → `DuplicateResourceError(409)` với `current_version`

---

### 4. Redis Cache Invalidation

**File mới:** `app/core/graph_cache.py` (95 dòng)

**Strategy:**
1. Khi edit thành công → set Redis key `graph_cache_invalid:{doc_id}=1` (TTL=30s)
2. `GraphBuilder` check key trước khi serve cached data
3. Nếu key tồn tại → clear in-memory NetworkX → rebuild từ DB
4. Sau khi rebuild → clear key

**API:**
- `invalidate(document_id)` → set invalidation key
- `is_invalid(document_id)` → check if key exists
- `clear_invalid(document_id)` → remove key after rebuild

---

### 5. API Endpoints

**File:** `app/api/graph.py` (+360 dòng)

| Method | Endpoint | Status | Mô tả |
|--------|----------|--------|-------|
| POST | `/api/v1/graph/entities` | 201 | Tạo entity mới |
| PUT | `/api/v1/graph/entities/{id}` | 200 | Cập nhật entity (có version check) |
| DELETE | `/api/v1/graph/entities/{id}` | 204 | Xóa entity (cascade relations) |
| POST | `/api/v1/graph/relations` | 201 | Tạo relation mới |
| DELETE | `/api/v1/graph/relations/{id}` | 204 | Xóa relation |

**Error handling:**
- `409 Conflict`: `{error: "CONCURRENT_EDIT", current_version: N}`
- `404 Not Found`: Entity/relation không tồn tại
- `400 Bad Request`: Self-reference, no update fields

---

### 6. Schemas

**File:** `app/schemas/lightrag.py` (+75 dòng)

| Schema | Mô tả |
|--------|-------|
| `EntityCreateRequest` | Request tạo entity |
| `EntityUpdateRequest` | Request update entity (có expected_version) |
| `EntityResponse` | Response entity với version |
| `RelationCreateRequest` | Request tạo relation |
| `RelationResponse` | Response relation với version |
| `ConflictErrorResponse` | Standard 409 response format |

---

### 7. Frontend

#### Zustand Graph Store
**File mới:** `frontend/src/store/graph.ts` (170 dòng)

- Quản lý `nodes[]`, `edges[]`, `selectedId`, `documentId`
- **History Stack:** `past[]`, `future[]` (max 50 states) cho Undo/Redo
- **Optimistic Update:** Update store trước khi gọi API
- Actions: `addNode`, `updateNode`, `deleteNode`, `addEdge`, `deleteEdge`, `undo`, `redo`

#### API Service Extension
**File:** `frontend/src/services/graph.ts` (+90 dòng)

- `createEntity()`, `updateEntity()`, `deleteEntity()`
- `createRelation()`, `deleteRelation()`
- `generateMermaid()` — đã có từ Sprint 8

---

### 8. Tests

**File mới:** `tests/unit/test_graph_crud.py` (360+ dòng)

| Test Suite | Tests | Coverage |
|------------|-------|----------|
| `TestCreateEntity` | 2 | Success, Duplicate raises |
| `TestUpdateEntity` | 2 | Version mismatch (409), Not found (404) |
| `TestDeleteEntity` | 2 | Success, Version mismatch (409) |
| `TestCreateRelation` | 1 | Self-reference raises |
| `TestDeleteRelation` | 1 | Success |
| `TestAuditLogging` | 2 | Success, Non-critical failure |
| `TestUserIsolation` | 1 | Cannot update other user's entity |

**File mới:** `tests/unit/test_graph_cache.py` (130+ dòng)

| Test Suite | Tests | Coverage |
|------------|-------|----------|
| `TestInvalidate` | 2 | Sets key, Returns false on error |
| `TestCheckInvalid` | 3 | True when key exists, False otherwise |
| `TestClearInvalid` | 2 | Deletes key, Returns false on error |
| `TestSingleton` | 3 | Get instance, Same instance, Reset |

**Kết quả:** ✅ **21/21 tests PASSED** (100%)

---

## Business Rules Compliance

| Rule | Status | Implementation |
|------|--------|---------------|
| **BR-001** User isolation | ✅ | `user_id` trên `graph_relations`, WHERE clause trong mọi CRUD |
| **BR-003** Graph consistency | ✅ | Redis cache invalidation triggers NetworkX rebuild |
| Optimistic Concurrency | ✅ | `version` column + `WHERE version = expected_version` |
| Audit Trail | ✅ | `graph_edit_log` table, async logging |

---

## Files Created/Modified

### Created (6 files)
| File | Lines | Description |
|------|-------|-------------|
| `alembic/versions/s9a1b2c3d4e5_...py` | 130 | Migration script |
| `app/core/graph_cache.py` | 95 | Redis cache invalidation |
| `frontend/src/store/graph.ts` | 170 | Zustand graph store |
| `tests/unit/test_graph_crud.py` | 368 | CRUD unit tests |
| `tests/unit/test_graph_cache.py` | 150 | Cache service tests |
| `docs/reports/2026-04-12_stage3_sprint9_implementation.md` | — | This report |

### Modified (4 files)
| File | Delta | Description |
|------|-------|-------------|
| `app/models/graph.py` | +40 | Added version, user_id, GraphEditLog |
| `app/repositories/graph_repo.py` | +250 | CRUD methods + audit logging |
| `app/api/graph.py` | +360 | 5 new CRUD endpoints |
| `app/schemas/lightrag.py` | +75 | 6 new schemas |
| `frontend/src/services/graph.ts` | +90 | CRUD API calls |

**Total:** ~1,400+ dòng code mới

---

## Performance Considerations

| Metric | Target | Implementation |
|--------|--------|---------------|
| API response time (edit ops) | < 500ms P95 | Single SQL statement per operation |
| Cache invalidation TTL | 30s | Fallback an toàn nếu Redis down |
| History stack limit | 50 states | Giới hạn memory usage |
| Audit logging | Non-blocking | Async fire-and-forget |

---

## Next Steps

- **Sprint 10** (Optional): Source Code Visualizer — Python AST parser
- **Sprint 11** (Optional): Media Microlearning — YouTube/Audio pipeline
- **Sprint 12**: UI Polish — Dark mode, animations, keyboard shortcuts, mobile

---

© 2026 AetherTutor Team
