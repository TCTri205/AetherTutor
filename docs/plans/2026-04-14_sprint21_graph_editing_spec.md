# Sprint 21: Interactive Graph Editing — Detailed Specification

> **Priority:** 🔴 P0 | **Sprint:** 21 | **Dependency:** Sprint 22 (tests framework sẵn sàng)
> **Estimate:** ~40-48 giờ (~1-1.5 tuần)
> **Goal:** Hoàn thiện interactive graph editing — tính năng core của Stage 3 còn thiếu

---

## 📋 Tổng quan

Sprint 21 tập trung vào việc xây dựng hệ thống interactive graph editing hoàn chỉnh, cho phép người dùng trực tiếp chỉnh sửa knowledge graph thông qua UI.

### Current Status (Đã có)

| Component | Status | Mô tả |
|-----------|--------|-------|
| **GraphEntity CRUD** | ✅ Implemented | `POST /entities`, `PUT /entities/{id}`, `DELETE /entities/{id}` |
| **GraphRelation CRUD** | ⚠️ Partial | `POST /relations`, `DELETE /relations/{id}` — THIẾU update |
| **Optimistic Concurrency** | ✅ Implemented | `version` field + `expected_version` check, 409 Conflict |
| **Audit Logging** | ✅ Implemented | `GraphEditLog` table + `log_edit()` method |
| **Entity Aliases** | ✅ Implemented | Alias resolution, merge, suggest duplicates |
| **Tags & Backlinks** | ✅ Implemented | Tag-based queries, entity backlinks |
| **Graph Visualization** | ✅ Implemented | Spring layout, community detection, centrality |
| **WebSocket Events** | ✅ Implemented | `node_create`, `node_update`, `node_delete` broadcast |

### Missing (Sprint 21 scope)

| Component | Priority | Mô tả |
|-----------|----------|-------|
| **Relation UPDATE** | P0 | Endpoint update relation type, source/target |
| **Undo/Redo API** | P0 | Endpoints `/undo`, `/redo`, `/versions` |
| **Graph Versioning** | P0 | Snapshot system, version restore |
| **Edit History API** | P0 | GET `/edit-log` để xem lịch sử chỉnh sửa |
| **Frontend Edit UI** | P0 | Create/delete nodes/edges, undo/redo toolbar |
| **Node Position Persistence** | P1 | Lưu x/y coordinates do user đặt |
| **Bulk Edit Operations** | P1 | Multi-select delete, batch create |

---

## 🗺️ Tasks Chi Tiết

### Phase 1: Backend API — Versioning & Undo/Redo (4 tasks)

> **Estimate:** ~16 giờ

#### Task 21.1.1: Graph Versioning API

**Endpoints mới:**

```
POST   /graph/{document_id}/versions          — Create snapshot
GET    /graph/{document_id}/versions          — List all versions
GET    /graph/{document_id}/versions/{version_id} — Get version details
POST   /graph/{document_id}/versions/{version_id}/restore — Restore to version
DELETE /graph/{document_id}/versions/{version_id} — Delete old version
```

**Schema:**

```python
class GraphVersionCreate(BaseModel):
    document_id: UUID
    version_number: Optional[int] = None  # Auto-increment if None
    description: Optional[str] = None  # User note about this version

class GraphVersionResponse(BaseModel):
    id: UUID
    document_id: UUID
    version_number: int
    description: Optional[str]
    snapshot: dict  # JSONB: {entities: [...], relations: [...]}
    created_at: datetime
    created_by: UUID  # user_id
    entity_count: int
    relation_count: int
```

**Implementation:**

```python
# app/api/graph.py

@router.post("/graph/{document_id}/versions")
async def create_graph_version(
    document_id: UUID,
    body: GraphVersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a snapshot of current graph state."""
    # 1. Verify document ownership
    # 2. Fetch all entities and relations for document
    # 3. Create snapshot JSON: {entities: [...dicts], relations: [...dicts]}
    # 4. Get max version_number, increment
    # 5. Insert into graph_versions table
    # 6. Return version response
    pass

@router.get("/graph/{document_id}/versions")
async def list_graph_versions(...):
    """List all versions for a document, ordered by created_at DESC."""
    pass

@router.post("/graph/{document_id}/versions/{version_id}/restore")
async def restore_graph_version(...):
    """Restore graph to a previous version.
    
    This creates NEW edit log entries (not destructive):
    - DELETE all current entities/relations
    - CREATE entities/relations from snapshot
    Each action is logged to edit_log for undo capability.
    """
    pass
```

**Database Migration:**

```sql
-- Already exists from Stage 3 migration? Need to verify
-- If not exists:

CREATE TABLE graph_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    description TEXT,
    snapshot JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, version_number)
);

CREATE INDEX idx_graph_versions_document ON graph_versions(document_id, version_number DESC);
```

#### Task 21.1.2: Undo/Redo API

**Endpoints mới:**

```
POST   /graph/{document_id}/undo      — Undo last action
POST   /graph/{document_id}/redo      — Redo last undone action
GET    /graph/{document_id}/edit-log  — Get edit history
```

**Schema:**

```python
class UndoResponse(BaseModel):
    success: bool
    action_undone: str  # "CREATE", "UPDATE", "DELETE"
    entity_type: str    # "entity" or "relation"
    entity_id: UUID
    old_value: Optional[dict]  # What was restored
    new_value: Optional[dict]  # What was removed
    can_undo_more: bool  # False if no more actions in log
```

**Implementation:**

```python
@router.post("/graph/{document_id}/undo")
async def undo_last_action(...):
    """Undo the last edit from graph_edit_log.
    
    Logic:
    1. Get last edit_log entry for document/user
    2. Reverse the action:
       - CREATE → DELETE the entity/relation
       - DELETE → RECREATE from old_value
       - UPDATE → RESTORE old_value (using optimistic concurrency)
    3. Mark edit_log entry as 'undone'
    4. Return what was undone
    """
    pass

@router.post("/graph/{document_id}/redo")
async def redo_last_undone(...):
    """Redo the last undone action.
    
    Logic:
    1. Get last 'undone' edit_log entry
    2. Re-apply the new_value:
       - CREATE → recreate entity/relation
       - DELETE → delete again
       - UPDATE → apply new_value again
    3. Mark edit_log entry as 'redone' (undo undone)
    4. Return what was redone
    """
    pass

@router.get("/graph/{document_id}/edit-log")
async def get_edit_history(...):
    """Get edit history for a document.
    
    Query params:
    - limit: int (default 50)
    - offset: int (default 0)
    - user_id: Optional[UUID] (filter by user)
    - action: Optional[str] (CREATE/UPDATE/DELETE)
    
    Returns paginated list of GraphEditLog entries.
    """
    pass
```

#### Task 21.1.3: Relation UPDATE Endpoint

**Endpoint mới:**

```
PUT    /graph/relations/{relation_id}  — Update relation
```

**Schema:**

```python
class RelationUpdateRequest(BaseModel):
    relation_type: Optional[str] = None
    description: Optional[str] = None
    source_entity_id: Optional[UUID] = None
    target_entity_id: Optional[UUID] = None
    expected_version: int  # Required for optimistic concurrency
```

**Implementation:**

```python
@router.put("/graph/relations/{relation_id}")
async def update_relation(
    relation_id: UUID,
    body: RelationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: GraphCacheService = Depends(get_graph_cache),
):
    """Update a relation with optimistic concurrency control.
    
    1. Fetch relation by ID, verify user_id matches
    2. Check version matches expected_version
    3. If mismatch → 409 Conflict with current_version
    4. If match → update fields, increment version
    5. Log to edit_log
    6. Invalidate cache
    7. Broadcast node_update via WebSocket
    """
    pass
```

#### Task 21.1.4: Node Position Persistence

**Endpoints mới:**

```
PUT    /graph/entities/{entity_id}/position  — Update entity position
```

**Schema:**

```python
class EntityPositionUpdate(BaseModel):
    x: float
    y: float
    expected_version: int
```

**Implementation:**

- Add `position_x` and `position_y` columns to `graph_entities` table
- Or store in `metadata_` JSONB field as `{position: {x: float, y: float}}`
- Endpoint updates position without affecting other entity data
- Broadcast via WebSocket for real-time sync

---

### Phase 2: Frontend Edit UI (11 tasks)

> **Estimate:** ~24-32 giờ

#### Task 21.2.1: Graph Edit Mode Toggle

**Component:** `GraphEditToolbar.tsx`

- Toggle button: View Mode ↔ Edit Mode
- Visual indicator (cursor change, highlights) when in edit mode
- Lock/unlock icon
- Keyboard shortcut: `Ctrl+E` to toggle

#### Task 21.2.2: Create Node Dialog

**Component:** `CreateNodeDialog.tsx`

- Modal dialog with form fields:
  - Name (required, unique check)
  - Type (dropdown: concept, person, place, event, other)
  - Description (textarea)
  - Tags (multi-select)
- Validation: Check for duplicate names before submit
- API call: `POST /graph/entities`
- On success: Add node to graph, broadcast via WebSocket

#### Task 21.2.3: Create Edge Dialog

**Component:** `CreateEdgeDialog.tsx`

- Modal dialog:
  - Source entity (dropdown/search)
  - Target entity (dropdown/search)
  - Relation type (dropdown: RELATED_TO, PART_OF, CAUSES, etc.)
  - Description (optional)
- Validation: Prevent duplicate edges, self-references
- API call: `POST /graph/relations`
- On success: Add edge to graph, broadcast via WebSocket

#### Task 21.2.4: Delete Node/Edge (Right-Click Menu)

**Component:** `NodeContextMenu.tsx`, `EdgeContextMenu.tsx`

- Right-click context menu on nodes/edges
- Options: Delete, Edit, View Details
- Delete confirmation dialog
- Optimistic update (remove from UI immediately)
- API call: `DELETE /graph/entities/{id}` or `DELETE /graph/relations/{id}`
- On failure: Rollback optimistic update

#### Task 21.2.5: Undo/Redo System (Frontend)

**Service:** `UndoRedoService.ts`

- Command pattern: Store action stack (max 50 actions)
- Actions: CREATE_NODE, DELETE_NODE, CREATE_EDGE, DELETE_EDGE, UPDATE_NODE, UPDATE_EDGE
- Keyboard shortcuts: `Ctrl+Z` undo, `Ctrl+Y` redo
- Clear stack on page refresh
- Sync with backend undo API for persistence across sessions

#### Task 21.2.6: Entity Alias Panel

**Component:** `EntityAliasPanel.tsx`

- Sidebar panel showing aliases for selected entity
- Add new alias button
- Delete alias button
- Duplicate alias suggestions (from API)
- Click alias to highlight all matching entities on graph
- API calls: `GET /graph/entities/aliases`, `POST /graph/entities/create-alias`

#### Task 21.2.7: Tags Panel

**Component:** `TagsPanel.tsx`

- Sidebar panel showing all tags for document
- Click tag to filter graph (highlight matching entities)
- Add/remove tags from selected entity
- Color-coded tags
- API calls: `GET /graph/tags`, `PUT /graph/entities/{id}` (update tags)

#### Task 21.2.8: Backlinks Panel

**Component:** `BacklinksPanel.tsx`

- Sidebar panel showing incoming relations to selected entity
- List of entities that link TO selected entity
- Click backlink to navigate to source entity on graph
- API call: `GET /graph/entities/{entity_id}/backlinks`

#### Task 21.2.9: Graph Search & Filter

**Component:** `GraphSearchFilter.tsx`

- Search bar: Search entities by name, type, tag
- Filter dropdown: Filter by relation type
- Highlight matching entities on graph
- Keyboard shortcut: `Ctrl+F` to focus search
- Real-time filtering as user types

#### Task 21.2.10: Graph Stats Widget

**Component:** `GraphStatsWidget.tsx`

- Display in corner of graph:
  - Total nodes, edges
  - Graph density
  - Average degree
  - Top 3 most central entities (from centrality API)
- Auto-refresh every 30s or after edits
- API calls: `GET /graph/{document_id}/stats`, `GET /graph/{document_id}/centrality`

#### Task 21.2.11: Duplicate Detection & Merge UI

**Component:** `DuplicateDetectionPanel.tsx`, `EntityMergeDialog.tsx`

- Panel suggesting potential duplicates (similarity >0.8)
- Click suggestion to view both entities side-by-side
- Merge button → dialog to select canonical entity
- Transfer relations from merged entities
- API calls: `GET /graph/duplicates`, `POST /graph/entities/merge`

---

### Phase 3: Tests (23 tests)

> **Estimate:** ~8 giờ

#### Backend API Tests (15 tests)

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | `test_create_graph_version` | Create version snapshot, verify entity/relation counts |
| 2 | `test_list_graph_versions` | Create 3 versions, list returns 3 in DESC order |
| 3 | `test_restore_graph_version` | Create version, edit graph, restore, verify state |
| 4 | `test_restore_creates_edit_log` | Restore creates new CREATE/DELETE entries in edit_log |
| 5 | `test_undo_create` | Create entity, undo → entity deleted |
| 6 | `test_undo_delete` | Delete entity, undo → entity recreated |
| 7 | `test_undo_update` | Update entity, undo → old values restored |
| 8 | `test_redo_undo` | Undo then redo → state same as before undo |
| 9 | `test_edit_history_pagination` | Create 100 edits, fetch with limit=10, verify pagination |
| 10 | `test_edit_history_filter_by_user` | Create edits by 2 users, filter by user_id |
| 11 | `test_edit_history_filter_by_action` | Filter by CREATE/UPDATE/DELETE |
| 12 | `test_update_relation` | Update relation type, verify old_value logged |
| 13 | `test_update_relation_version_mismatch` | Update with wrong expected_version → 409 |
| 14 | `test_update_entity_position` | Update x/y position, verify persisted |
| 15 | `test_concurrent_edits` | 2 users edit same entity simultaneously → one gets 409 |

#### Frontend Component Tests (8 tests)

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | `test_create_node_dialog_validation` | Submit empty name → validation error |
| 2 | `test_create_node_duplicate_name` | Create node with existing name → API error shown |
| 3 | `test_create_edge_self_reference` | Select same source/target → validation error |
| 4 | `test_undo_redo_stack` | Create 3 nodes, undo 2, redo 1, verify stack state |
| 5 | `test_optimistic_update_rollback` | Delete node, API fails → node reappears |
| 6 | `test_websocket_node_broadcast` | User A creates node, User B receives node_created |
| 7 | `test_tags_panel_filter` | Click tag → only tagged entities highlighted |
| 8 | `test_merge_dialog` | Select 2 entities, merge, verify relations transferred |

---

## 📊 Deliverables

### Backend

| File | Description |
|------|-------------|
| `app/api/graph.py` | New endpoints: `/versions`, `/undo`, `/redo`, `/edit-log`, `/relations/{id}` PUT |
| `app/schemas/lightrag.py` | New schemas: `GraphVersionCreate`, `GraphVersionResponse`, `UndoResponse`, `RelationUpdateRequest` |
| `app/models/graph.py` | (Nếu cần) Add `GraphVersion` model nếu migration chưa có |
| `app/repositories/graph_repo.py` | New methods: `create_version()`, `list_versions()`, `get_version()`, `restore_version()`, `get_edit_log()`, `undo_action()`, `redo_action()` |
| `alembic/versions/` | Migration: `CREATE TABLE graph_versions` (nếu chưa có), `ALTER TABLE graph_entities ADD COLUMN position_x, position_y` |

### Frontend

| File | Description |
|------|-------------|
| `frontend/src/components/graph/GraphEditToolbar.tsx` | Edit mode toggle, undo/redo buttons |
| `frontend/src/components/graph/CreateNodeDialog.tsx` | Node creation form |
| `frontend/src/components/graph/CreateEdgeDialog.tsx` | Edge creation form |
| `frontend/src/components/graph/NodeContextMenu.tsx` | Right-click menu for nodes |
| `frontend/src/components/graph/EdgeContextMenu.tsx` | Right-click menu for edges |
| `frontend/src/services/UndoRedoService.ts` | Command pattern undo/redo |
| `frontend/src/components/graph/EntityAliasPanel.tsx` | Alias management panel |
| `frontend/src/components/graph/TagsPanel.tsx` | Tag management panel |
| `frontend/src/components/graph/BacklinksPanel.tsx` | Incoming relations panel |
| `frontend/src/components/graph/GraphSearchFilter.tsx` | Search and filter |
| `frontend/src/components/graph/GraphStatsWidget.tsx` | Graph statistics display |
| `frontend/src/components/graph/DuplicateDetectionPanel.tsx` | Duplicate suggestions |
| `frontend/src/components/graph/EntityMergeDialog.tsx` | Merge confirmation dialog |

### Tests

| File | Description |
|------|-------------|
| `tests/integration/test_graph_versioning.py` | Versioning API tests (5 tests) |
| `tests/integration/test_graph_undo_redo.py` | Undo/redo API tests (7 tests) |
| `tests/integration/test_graph_relation_update.py` | Relation update tests (3 tests) |
| `tests/e2e/test_graph_editing.py` | Frontend component tests (8 tests) |

---

## ✅ Acceptance Criteria

- [ ] Tất cả 23 tests mới passing
- [ ] Graph versioning API hoạt động (create, list, restore)
- [ ] Undo/redo API hoạt động (undo create, delete, update)
- [ ] Edit history API hoạt động (pagination, filters)
- [ ] Relation UPDATE endpoint hoạt động với optimistic concurrency
- [ ] Frontend edit toolbar hoạt động (create/delete nodes/edges)
- [ ] Undo/redo frontend hoạt động (Ctrl+Z/Y)
- [ ] WebSocket events broadcast realtime
- [ ] Optimistic concurrency control không bị regression
- [ ] User isolation (BR-001) không bị breach

---

## ⚠️ Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Versioning snapshot quá lớn (>10MB) | Medium | Medium | Limit max versions per document to 50, auto-delete oldest |
| Undo/redo conflict với concurrent edits | Medium | High | Use optimistic concurrency, reject undo if version mismatch |
| Frontend undo stack out of sync với backend | Low | Medium | Sync stack after each API call, reset on page refresh |
| Graph restore deletes unrelated data | Low | High | Only restore entities/relations for specific document_id |

---

## 📝 Notes

### Relationship với Sprint 22 (Tests)

Sprint 22 nên được bắt đầu TRƯỚC Sprint 21 để có test framework sẵn sàng. Khi Sprint 21 tạo code mới, tests từ Sprint 22 có thể validate ngay.

### Relationship với WebSocket Tests

WebSocket tests từ Sprint 22 Phase 1 sẽ validate rằng node_create/update/delete events được broadcast đúng cách — đây cũng là requirement cho Sprint 21.

### Database Migration Notes

Kiểm tra migration `s9a1b2c3d4e5_stage3_graph_editing_version_audit.py` đã có `graph_versions` table chưa. Nếu chưa, tạo migration mới.

---

© 2026 AetherTutor Team
*Sprint 21 Graph Editing Spec — Generated 2026-04-14*
*Status: READY FOR EXECUTION*
