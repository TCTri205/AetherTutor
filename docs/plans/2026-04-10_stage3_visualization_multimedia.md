# Kế hoạch Triển khai Giai đoạn 3: Visualization & Multimedia

> **Document Owner:** AetherTutor Team
> **Status:** Draft (Planning for Stage 3)
> **Timeline:** Dự kiến 10 tuần (Quý 3 - 2026)
> **Phiên bản:** 1.4 — **Fix: Layer architecture, GraphBuilder reload spec, DuplicateResourceError, graph_relations user_id**
> **Parent:** [Roadmap.md#3-stage-3-visualization-trực-quan-hóa--multimedia](../reports/2026-04-07_product_roadmap.md)

**Changelog v1.3 → v1.4:**
- 🔴 **Fix G1:** Thay `ConflictError` → `DuplicateResourceError` (đã có sẵn HTTP 409 trong `exceptions.py`)
- 🔴 **Fix G2:** Bổ sung `GraphBuilder.build_from_db()` method spec — build NetworkX từ PostgreSQL entities/relations
- 🔴 **Fix G3:** Chuyển CRUD từ `app/core/graph_builder.py` → `app/repositories/graph_repo.py` (đúng layer repository)
- 🔴 **Fix G4:** Thêm migration `ADD COLUMN user_id` vào `graph_relations` trước khi create index

---

## 1. Hiện trạng hệ thống (Current State Audit)

Trước khi bắt đầu Stage 3, cần xác định rõ các thành phần đã có vs. các khoảng trống kỹ thuật (Gaps):

| Thành phần | Đã có (Current State) | Khoảng trống (Gaps) |
|---|---|---|
| **Database Models** | `GraphEntity` (có `user_id`), `GraphRelation` (CHƯA có `user_id`) | Thiếu cột `version` cho Concurrency, bảng `graph_edit_log`, và `user_id` cho `graph_relations` |
| **Graph Engines** | `GraphBuilder` (NetworkX) dump ra file disk (GraphML/JSON) | Thiếu cơ chế đồng bộ (sync) ngược từ DB vào NetworkX khi có edit |
| **API Layer** | Endpoint `/graph/{id}/view` (Read-only), `/graph/global` | Thiếu toàn bộ CRUD endpoints và `/mermaid` generation |
| **Frontend Store** | `document.ts`, `chat.ts`, `flashcard.ts`, `notes.ts`, `quiz.ts`, `ui.ts` | **KHÔNG CÓ `graph.ts` store**. State đang nằm cục bộ tại `GraphExplorer.tsx` component |
| **Frontend Service** | `services/graph.ts` — có `queryGraph`, `getDocumentGraph`, `getGraphStats` | **Thiếu** CRUD API calls (`createEntity`, `updateEntity`, `deleteEntity`, `createRelation`, `deleteRelation`) |
| **Visualization** | ReactFlow với Radial Layout cơ bản | Thiếu Interactive Editing (Drag/Create/Delete) và Mermaid renderer |
| **Performance** | Chưa có benchmark | Cần baseline cho graph > 500 nodes |
| **Worker Tasks** | `process_document_task`, `sm2_daily_digest_task`, `quiz_feedback_analysis_task` | **Không có** graph invalidation task (sẽ dùng Redis key thay vì Worker) |

---

## 2. Mục tiêu (Goals)

Chuyển đổi AetherTutor từ **Learning OS dạng văn bản** thành **hệ thống đa phương thức** với khả năng trực quan hóa tri thức mạnh mẽ.

**Key Outcomes:**
- ✅ Knowledge Graph → Mermaid.js diagrams (mindmap, flowchart, sequence)
- ✅ Interactive graph editing (thêm/xóa entities, relations trực tiếp trên UI)
- ✅ UI nâng cấp: Dark mode, animations, keyboard shortcuts, mobile polish
- ⏸️ Source Code Visualizer (Post-MVP nếu resource hạn chế)
- ⏸️ Media Microlearning (YouTube/Audio → transcript → graph) (Post-MVP nếu resource hạn chế)

---

## 3. Pre-requisites & Ràng buộc kỹ thuật

### 3.1 Dependencies từ Stage 1-2

| # | Dependency | Trạng thái | Ghi chú |
|---|-----------|-----------|---------|
| **D1** | LightRAG Pipeline hoàn chỉnh | ✅ Stage 1 done | Entity extraction, graph construction, dual-level retrieval |
| **D2** | NetworkX graph persistence | ✅ Stage 1 done | GraphML/JSON export đã có infrastructure |
| **D3** | ReactFlow GraphExplorer | ✅ Stage 2 done | Radial layout, custom nodes/edges, entity search |
| **D4** | Chat SSE streaming | ✅ Stage 2 done | Buffered parser, context chips, error recovery |
| **D5** | Flashcards + SM-2 | ✅ Stage 2 done | Auto-generation, review session, scheduling |
| **D6** | Quiz Generation | ✅ Stage 2 done | ExaminerAgent, multi-hop, Bloom's taxonomy |
| **D7** | Notes (Zettelkasten) | ✅ Stage 2 done | Atomic notes, backlink suggestions |
| **D8** | ARQ Workers | ✅ Stage 1 done | Background task processing |

### 3.2 Ràng buộc kỹ thuật & Performance Targets

| Ràng buộc | Giá trị | Impact |
|-----------|---------|--------|
| **RAM giới hạn** | 8GB (CPU-only) | Media pipeline phải nhẹ, không dùng whisper.cpp local |
| **User isolation** | BR-001 🔴 | Mọi graph edit PHẢI filter theo `user_id` |
| **Graph consistency** | BR-003 🔴 | NetworkX ↔ PostgreSQL sync sau mỗi edit |
| **Mermaid max nodes** | 100 nodes (default) | Warn user nếu graph quá lớn |
| **API response time** | < 500ms cho edit ops | P95 requirement từ SRS |
| **Performance Target** | Graph 500 nodes load < 3s | Baseline mục tiêu cho Sprint 12 |

---

## 4. Sprint 8: Visualizer Agent & Mermaid Integration (Tuần 1-2)

*Mục tiêu: Transform knowledge graph → Mermaid.js diagrams với nhiều format (mindmap, flowchart, sequence)*

### 4.1 Backend Tasks

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B1** | **Implement VisualizerAgent** | `app/core/visualizer_agent.py` | Medium | 4h |
|   | - `generate_mermaid(topic, max_nodes, max_depth, format)` | | | |
|   | - `_extract_subgraph(root_node, max_nodes, max_depth)` — BFS extraction | | | |
|   | - `_convert_to_mermaid(nodes, edges, format)` — support 3 formats | | | |
|   | - Formats: `graph TD` (flowchart), `mindmap`, `flowchart LR` | | | |
|   | - Metadata: `{total_nodes, total_edges, truncated}` | | | |
| **B2** | **API Endpoint** | `app/api/graph.py` | Low | 2h |
|   | - `POST /api/v1/graph/mermaid` | | | |
|   | - Request schema: `{topic, max_nodes?, max_depth?, format?}` | | | |
|   | - Response schema: `{mermaid_code, metadata}` | | | |
| **B3** | **Integration với Chat** | `app/services/chat_service.py` | Medium | 3h |
|   | - Detect intent "draw diagram" trong chat message | | | |
|   | - Gọi VisualizerAgent, trả về mermaid code trong response | | | |
|   | - **Cập nhật Socratic Tutor System Prompt** để Agent biết khả năng xuất diagram | | | |
|   | - Prompt guideline: Khi nào dùng diagram thay vì text (complex relationships, >3 entities, user yêu cầu "vẽ/minh họa") | | | |
| **B3b** | **LLM Prompting cho Mermaid** | `app/core/prompts/socratic_tutor.py` | Low | 1h |
|   | - Bổ sung section vào System Prompt: "Bạn CÓ THỂ xuất Mermaid code blocks để minh họa khái niệm phức tạp" | | | |
|   | - Rule: Dùng diagram khi giải thích quy trình (process), hệ thống (system), hoặc mối quan hệ >3 entities | | | |
|   | - Rule: KHÔNG dùng diagram cho định nghĩa đơn giản hoặc câu trả lời ngắn | | | |
|   | - Format: Luôn dùng ` ```mermaid ` code block, kèm giải thích ngắn sau diagram | | | |
| **B4** | **Unit & Integration Tests** | `tests/unit/test_visualizer_agent.py` | Medium | 3h |
|   | - Test subgraph extraction (empty, single node, multi-node) | | | |
|   | - Test Mermaid conversion (3 formats) | | | |
|   | - **Integration Test:** Mock LLM call để verify Agent sinh ra mermaid code block hợp lệ trong chat flow | | | |
|   | - Test max_nodes truncation logic | | | |

### 4.2 Frontend Tasks

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **F1** | **Install Mermaid** | `frontend/package.json` | Low | 0.5h |
|   | - `npm install mermaid@10` | | | |
|   | - Config mermaid: `{startOnLoad: false, theme: 'default'}` — Sync với system preference | | | |
| **F2** | **MermaidDiagram Component** | `frontend/src/components/shared/MermaidDiagram.tsx` | Medium | 4h |
|   | - Wrapper cho `mermaid.run()` API | | | |
|   | - Auto-render khi nhận mermaid code | | | |
|   | - Error boundary cho invalid syntax | | | |
|   | - Tooltip hiển thị metadata (nodes/edges count) | | | |
|   | - Dark mode support (theme switching qua CSS variables) | | | |
| **F3** | **Chat Integration** | `frontend/src/pages/Chat.tsx` | Low | 2h |
|   | - Detect mermaid code block trong markdown (` ```mermaid `) | | | |
|   | - Render `<MermaidDiagram>` thay vì code block | | | |
|   | - "Zoom to full screen" button for diagrams | | | |
| **F4** | **GraphExplorer Tab Diagram** | `frontend/src/pages/GraphExplorer.tsx` | Low | 2h |
|   | - Thêm tab "Diagram View" bên cạnh "Graph View" | | | |
|   | - Topic input (default: document title hoặc entity name) | | | |
|   | - "Generate" button → call API → render | | | |

### 4.3 Deliverables Sprint 8

- ✅ VisualizerAgent hoạt động với 3 format Mermaid
- ✅ API endpoint `POST /api/v1/graph/mermaid` trả về valid code
- ✅ Chat render được diagrams từ graph (auto-detect intent)
- ✅ GraphExplorer có Diagram View tab
- ✅ 15+ unit tests passing
- ✅ Manual test: 5 documents khác nhau, diagrams render đúng

### 4.4 Rủi ro & Giảm thiểu

| Rủi ro | Khả năng | Impact | Giảm thiểu |
|--------|---------|--------|-----------|
| Mermaid syntax error với graph phức tạp | Trung bình | Trung bình | Try/catch, fallback về `graph TD` đơn giản |
| Render chậm (>3s) với graph >50 nodes | Cao | Thấp | Limit max_nodes=100, warn user trước |
| Dark mode mermaid không sync với UI | Trung bình | Thấp | Dùng CSS variables, test cả 2 themes |

---

## 5. Sprint 9: Interactive Graph Editing (Tuần 3-4)

*Mục tiêu: User có thể chỉnh sửa graph trực tiếp trên UI (thêm/xóa entities, tạo relations)*

### 5.1 Backend Tasks

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B1** | **Database Migration — Version Columns** | `alembic/versions/` | Medium | 2h |
|   | - Migration: Thêm cột `version INT DEFAULT 1` vào `graph_entities` và `graph_relations` | | | |
|   | - Migration: Thêm cột `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` vào `graph_entities` và `graph_relations` | | | |
|   | - Trigger: Tự động increment `version` và update `updated_at` khi có UPDATE | | | |
|   | - Migration: Tạo bảng `graph_edit_log` (id, user_id, entity_id, relation_id, action, old_value, new_value, created_at) | | | |
| **B2** | **Graph Edit Service (CRUD)** | `app/repositories/graph_repo.py` | High | 6h |
|   | - `create_entity(entity_data, user_id, document_id)` — dùng `session.add()` + `flush()` | | | |
|   | - `update_entity(entity_id, updates, expected_version, user_id)` | | | |
|   | - **Optimistic Concurrency Control:** Raw SQL `UPDATE ... WHERE id = ? AND version = ?` → 0 rows → raise `DuplicateResourceError("Edit conflict", details={"current_version": N})` (HTTP 409) | | | |
|   | - `delete_entity(entity_id, expected_version, user_id)` — cascade delete relations (DB FK handles) | | | |
|   | - `create_relation(relation_data, user_id, document_id)` | | | |
|   | - `delete_relation(relation_id, expected_version, user_id)` | | | |
| **B2b** | **Redis Cache Invalidation** | `app/core/graph_cache.py` | Medium | 3h |
|   | - **Strategy:** Set Redis key `graph_cache_invalid:{doc_id}=1` khi edit thành công | | | |
|   | - Key TTL: 30s (auto-expire, fallback an toàn) | | | |
|   | - `GraphBuilder.check_and_invalidate(doc_id)`: Check key → nếu tồn tại → clear NetworkX memory → rebuild từ DB | | | |
|   | - **Rebuild flow:** Gọi `GraphRepository.get_all_entities(doc_id)` + `get_all_relations(doc_id)` → `GraphBuilder.add_entities_and_relations()` → `self.graph` updated | | | |
|   | - Auto-clear key sau khi rebuild thành công | | | |
|   | - **Ưu điểm:** Không cần Worker subscribe, đơn giản, reliable | | | |
| **B3** | **Validation & Business Rules** | `app/core/graph_builder.py` | Medium | 3h |
|   | - Validate: entity name UNIQUE per document (BR-001) | | | |
|   | - Validate: relation source/target entities tồn tại | | | |
|   | - Validate: user_id isolation — không edit graph user khác | | | |
| **B3b** | **Audit Logging** | `app/core/graph_builder.py` | Low | 1h |
|   | - Ghi log vào `graph_edit_log` sau mỗi CRUD operation | | | |
|   | - `old_value`, `new_value` = JSONB serialization của entity/relation | | | |
|   | - Async write (fire-and-forget, không block main flow) | | | |
|   | - Nếu logging fail → log warning, KHÔNG fail operation chính | | | |
| **B4** | **API Endpoints (v1)** | `app/api/graph.py` | Medium | 4h |
|   | - `POST /api/v1/graph/entities` — Tạo entity mới | | | |
|   | - `PUT /api/v1/graph/entities/{id}` — Cập nhật có `expected_version` | | | |
|   | - `DELETE /api/v1/graph/entities/{id}` — Xóa entity | | | |
|   | - `POST /api/v1/graph/relations` — Tạo relation mới | | | |
|   | - `DELETE /api/v1/graph/relations/{id}` — Xóa relation có `expected_version` | | | |
|   | - Error 409 Conflict: `{error: "CONCURRENT_EDIT", current_version: N, message: "..."}` | | | |
| **B5** | **Unit + Integration Tests** | `tests/` | Medium | 4h |
|   | - `tests/unit/test_graph_builder_edit.py` — CRUD operations | | | |
|   | - `tests/unit/test_graph_cache.py` — Redis key set/clear/check flow | | | |
|   | - `tests/unit/test_optimistic_concurrency.py` — Version check, conflict handling | | | |
|   | - `tests/unit/test_audit_logging.py` — Verify log ghi đúng, async không block | | | |
|   | - Test cascade delete & user isolation (BR-001) | | | |

### 5.2 Frontend Tasks

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **F1** | **Tạo MỚI Zustand Graph Store** | `frontend/src/store/graph.ts` **(FILE MỚI)** | High | 5h |
|   | - **Lý do:** Hiện tại KHÔNG CÓ file này. State graph đang nằm cục bộ trong `GraphExplorer.tsx` component | | | |
|   | - Quản lý `nodes[]`, `edges[]`, `selectedId`, `documentId` | | | |
|   | - **History Stack:** `past[]`, `future[]` cho Undo/Redo (max 50 states) | | | |
|   | - **Optimistic Update:** Update store trước khi gọi API → rollback nếu fail | | | |
|   | - Actions: `setNodes`, `setEdges`, `addNode`, `updateNode`, `deleteNode`, `addEdge`, `deleteEdge` | | | |
|   | - Actions: `undo`, `redo`, `canUndo`, `canRedo` | | | |
| **F2** | **ReactFlow Editing Mode** | `frontend/src/pages/GraphExplorer.tsx` | High | 6h |
|   | - Enable `nodesDraggable`, `nodesConnectable` | | | |
|   | - Toolbar: CRUD buttons, Undo, Redo | | | |
|   | - Custom `onNodeDragStop` handler → sync position (nếu cần) | | | |
| **F2b** | **Relation Creation UX** | `frontend/src/pages/GraphExplorer.tsx` | Medium | 2h |
|   | - Click node A (select source) → drag edge handle → drop on node B (select target) | | | |
|   | - Mở modal chọn relation type dropdown: `is_a`, `part_of`, `related_to`, `causes`, `enables`, `prevents`, `depends_on` | | | |
|   | - Validation: source != target, entities tồn tại | | | |
|   | - Visual feedback: edge màu xanh khi hover valid target, màu đỏ khi invalid | | | |
|   | - Debounced API call (300ms) tránh spam khi user drag nhanh | | | |
| **F3** | **Modals & Context Menu** | `frontend/src/components/graph/` | Medium | 6h |
|   | - `AddEntityModal`: Form (name, type, description) + validation (duplicate name check) | | | |
|   | - `ConflictResolutionModal`: Hiển thị khi nhận lỗi 409 — Options: "Overwrite" hoặc "Reload" | | | |
|   | - `GraphContextMenu`: Right-click actions (Edit, Delete, Expand neighbors) | | | |
| **F4** | **API Service Extension** | `frontend/src/services/graph.ts` | Medium | 3h |
|   | - **Hiện tại:** Chỉ có `queryGraph`, `getDocumentGraph`, `getGraphStats` | | | |
|   | - **Thêm mới:** `createEntity`, `updateEntity`, `deleteEntity`, `createRelation`, `deleteRelation` | | | |
|   | - Tự động gửi `expected_version` từ store state | | | |
|   | - Rollback store state nếu API error + error toast | | | |
|   | - Handle 409 Conflict → trigger `ConflictResolutionModal` | | | |

### 5.3 Deliverables Sprint 9

- ✅ Drag & drop nodes trong GraphExplorer
- ✅ Tạo entity mới qua UI (modal + validation)
- ✅ Tạo relation mới (click source → drag edge → drop target → select type)
- ✅ Xóa entity/relation (context menu + confirmation)
- ✅ Undo/redo hoạt động (Ctrl+Z, Ctrl+Y)
- ✅ Backend API validate và persist edits
- ✅ NetworkX ↔ PostgreSQL sync qua Redis cache invalidation
- ✅ Audit logging hoạt động (ghi vào `graph_edit_log`)
- ✅ 20+ integration tests passing
- ✅ User isolation verified (không thể edit graph user khác)
- ✅ Concurrent edit conflict handled gracefully (409 → user resolution modal)

### 5.4 Rủi ro & Giảm thiểu

| Rủi ro | Khả năng | Impact | Giảm thiểu |
|--------|---------|--------|-----------|
| **Editing conflict (2 tabs cùng edit)** | Trung bình | Cao | **Optimistic Concurrency Control:** `version` column + `WHERE version = expected_version` → 409 Conflict, user resolve manually |
| NetworkX out-of-sync với PostgreSQL | Thấp | Cao | **Redis Cache Invalidation:** Set key `graph_cache_invalid:{doc_id}=1` khi edit. `GraphBuilder` check key → reload từ DB. Fallback: TTL 30s tự expire |
| User tạo relation circular (A→B→A) | Cao | Thấp | Validation: allow circular (valid trong graph theory) |
| Undo history memory leak | Thấp | Trung bình | Limit history stack max 50 states |
| Redis down → cache invalidation fail | Thấp | Trung bình | Fallback: edit vẫn thành công trong DB. Graph sẽ stale tối đa 30s (TTL). Next request sẽ reload từ DB |
| Audit logging làm chậm edit ops | Thấp | Thấp | Async fire-and-forget. Nếu fail → log warning, không block operation chính |

---

## 6. Sprint 10: Source Code Visualizer (Tuần 5-6) [OPTIONAL]

> [!NOTE]
> **Delay sang Stage 4 nếu resource hạn chế.** Sprint 8 + 9 là core của Stage 3. Sprint này là nice-to-have.

*Mục tiêu: Upload source code files → tự động parse thành graph (functions, classes, dependencies)*

### 6.1 Tasks

| # | Task | File(s) | Ghi chú |
|---|------|---------|---------|
| **C1** | **Code Parser Service** | `app/services/code_parser.py` | Python: `ast` module, JS/TS: `tree-sitter` (MVP chỉ support Python) |
| **C2** | **Code → Graph Entities** | `app/core/code_graph_builder.py` | Classes → entities, Functions → entities, Imports → relations, Inheritance → relations |
| **C3** | **Document Pipeline Extension** | `app/core/pipeline.py` | Support `source_type: code` |
| **C4** | **API Endpoint** | `app/api/documents.py` | `POST /api/v1/documents/process/code` — accept `.py` files |
| **C5** | **Frontend Upload** | `frontend/src/pages/Vault.tsx` | Accept `.py`, `.js`, `.ts` files (MVP: `.py` only) |
| **C6** | **Code Graph Visualization** | `frontend/src/pages/GraphExplorer.tsx` | Syntax highlighting trong node labels, color by type (class=function, func=blue, import=green) |
| **C7** | **Tests** | `tests/unit/test_code_parser.py` | Parse 3 Python files khác nhau, verify graph entities correct |

### 6.2 Scope MVP (Minimum)

- ✅ Support Python `.py` files only
- ✅ Extract: classes, functions, imports
- ✅ Graph: nodes = classes/functions, edges = imports/calls
- ❌ Multi-file projects (Post-MVP)
- ❌ JS/TS support (Post-MVP)

### 6.3 Rủi ro

| Rủi ro | Impact | Giảm thiểu |
|--------|--------|-----------|
| `ast` module không parse được syntax mới | Thấp | MVP chỉ support Python 3.10+ syntax |
| Graph quá lớn với project nhiều files | Cao | Limit 1 file/document, multi-file là Post-MVP |

---

## 7. Sprint 11: Media Microlearning Pipeline (Tuần 7-8) [OPTIONAL]

> [!NOTE]
> **Delay sang Stage 4.** Chỉ implement khi Stage 3 core (Sprint 8-9) xong và stable.
>
> **SRS Scope Note:** Phù hợp với SRS Overview Section 1.3 — `Video/Audio Processing | ❌ Post-MVP`.
> Stage 3 = Post-MVP Phase, nên Sprint 11 nằm trong scope hợp lệ.

*Mục tiêu: Upload YouTube URL hoặc audio file → transcript → process như document*

### 7.1 Tasks

| # | Task | File(s) | Ghi chú |
|---|------|---------|---------|
| **M1** | **YouTube Transcript Service** | `app/services/youtube_transcript.py` | Dùng `youtube-transcript-api` package |
| **M2** | **Audio Transcription** | `app/services/audio_transcription.py` | **MVP: OpenAI Whisper API** (cloud). Local whisper.cpp delay sang Stage 4 (tốn RAM). **Bổ sung:** Cost estimation trước khi transcribe, Local Mode compliance (BR-008) |
| **M3** | **Document Processing Extension** | `app/core/pipeline.py` | Support `source_type: youtube, audio` |
| **M4** | **Worker Task** | `app/worker/tasks.py` | `process_youtube_task(video_url, doc_id, user_id)` — đăng ký vào `WorkerSettings.functions` |
| **M5** | **Frontend Upload** | `frontend/src/pages/Vault.tsx` | Accept YouTube URLs, audio files (`.mp3`, `.wav`) |
| **M6** | **Transcript Preview** | `frontend/src/components/shared/TranscriptPreview.tsx` | Preview transcript trước khi process, allow edits |
| **M7** | **Tests** | `tests/integration/test_youtube_pipeline.py` | Test end-to-end: URL → transcript → graph → chat |

### 7.2 Scope MVP (Minimum)

- ✅ YouTube URLs (auto transcript)
- ✅ Audio files `.mp3` (OpenAI Whisper API)
- ✅ Process transcript như document thông thường (reuse pipeline)
- ✅ **Cost Estimation:** Modal xác nhận trước khi transcribe audio (hiển thị estimated duration + cost)
- ✅ **Local Mode Compliance (BR-008):** Nếu `local_mode=True` và `whisper_cpp=False` → từ chối xử lý, yêu cầu user dán transcript thủ công hoặc chuyển Cloud Mode
- ❌ Video playback trong UI (Post-MVP)
- ❌ Local whisper.cpp (Post-MVP — tốn RAM)

### 7.3 Rủi ro

| Rủi ro | Khả năng | Impact | Giảm thiểu |
|--------|---------|--------|-----------|
| YouTube API quota hết | Cao | Trung bình | Fallback: user paste transcript manual |
| Audio transcription đắt (OpenAI API: ~$0.006/phút) | Trung bình | Cao | **Cost estimation modal** trước khi xử lý. Giới hạn 5 audio/day. Warn user nếu >10 phút. |
| **Local Mode violation (BR-008)** | Thấp | 🔴 **CRITICAL** | **Check `local_mode` trước khi gọi Whisper API.** Nếu local mode ON + whispercpp OFF → từ chối, yêu cầu user dán transcript thủ công hoặc chuyển Cloud Mode. |
| Whisper API timeout (>10 min audio) | Trung bình | Trung bình | Split audio thành segments 5 min |
| Transcript language detection fail | Thấp | Thấp | Default to English, allow user override |

---

## 8. Sprint 12: UI Polish & Performance (Tuần 9-10)

*Mục tiêu: Nâng cấp trải nghiệm người dùng, tối ưu performance*

### 8.1 Tasks

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **U0** | **Performance Baseline Measurement** | Manual + React DevTools Profiler | Low | 1h |
|   | - Đo thời gian `GET /graph/{id}/view` với 50, 100, 200, 500 nodes | | | |
|   | - Đo frontend render time (React DevTools Profiler) | | | |
|   | - Đo time-to-interactive của GraphExplorer | | | |
|   | - Document kết quả làm baseline cho U3 optimization | | | |
| **U1** | **Dark Mode** | `frontend/src/` | Medium | 6h |
|   | - Tailwind dark mode config (`class` strategy) | | | |
|   | - Theme toggle trong Settings | | | |
|   | - Mermaid theme sync (light/dark qua CSS variables) | | | |
|   | - ReactFlow node colors adjust cho dark mode | | | |
| **U2** | **Advanced Animations** | `frontend/src/` | Medium | 4h |
|   | - Page transitions (framer-motion AnimatePresence) | | | |
|   | - Modal scale animations (already có, polish thêm) | | | |
|   | - Entity chip animations on hover | | | |
|   | - Graph node pulse animation khi selected | | | |
| **U3** | **Graph Performance Optimization** | `frontend/src/pages/GraphExplorer.tsx` | High | 6h |
|   | - Virtual rendering cho graphs >500 nodes (ReactFlow `defaultViewport`) | | | |
|   | - Lazy loading neighbors (click to expand thay vì load hết) | | | |
|   | - Debounce search input (300ms) | | | |
|   | - Memoize expensive computations (React.useMemo) | | | |
| **U4** | **Keyboard Shortcuts** | `frontend/src/` | Low | 3h |
|   | - Ctrl+K: Global search | | | |
|   | - Ctrl+Z: Undo (graph edit) | | | |
|   | - Ctrl+Y: Redo (graph edit) | | | |
|   | - Esc: Close modal | | | |
|   | - Enter: Send message (chat) | | | |
|   | - Display shortcuts modal (Shift+?) | | | |
| **U5** | **Loading States** | `frontend/src/` | Low | 2h |
|   | - Skeleton screens cho graph, chat, flashcard review | | | |
|   | - Progress indicators cho API calls | | | |
|   | - Empty states polish (hiện tại đã có, thêm illustrations) | | | |
| **U6** | **Mobile Polish** | `frontend/src/` | Medium | 4h |
|   | - Responsive graph view (touch zoom/pan) | | | |
|   | - Touch-friendly flashcard swipe (framer-motion gestures) | | | |
|   | - Mobile drawer navigation polish | | | |
|   | - Button sizes tăng cho touch targets (min 44x44px) | | | |

### 8.2 Deliverables Sprint 12

- ✅ Performance baseline documented
- ✅ Dark mode hoạt động toàn bộ UI
- ✅ Animations mượt mà (60fps)
- ✅ Graph 500 nodes load trong < 3s (verified against baseline)
- ✅ Keyboard shortcuts hoạt động
- ✅ Mobile responsive hoàn thiện
- ✅ Lighthouse score > 90 (Performance, Accessibility, Best Practices)

---

## 9. Alembic Migration Checklist & Workflow

Trước khi triển khai Code Stage 3, cần hoàn thành chu trình Migration sau:

### 9.1 Chuẩn bị

1. **Backup Database:** `docker exec -t pg_db pg_dump -U user aether > backup_stage2.sql`
2. **Verify migration history:** `alembic history` — đảm bảo không có gaps
3. **Test trên local DB trước** — không chạy trực tiếp production

### 9.2 Schema Update

Tạo Alembic revision mới:
```bash
alembic revision --autogenerate -m "stage3_graph_editing_version_audit"
```

Migration script sẽ bao gồm:
- Thêm cột `version INT DEFAULT 1 NOT NULL` vào `graph_entities` và `graph_relations`
- Thêm cột `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` vào `graph_entities` và `graph_relations`
- 🔴 Thêm cột `user_id UUID REFERENCES users(id)` vào `graph_relations` (hiện tại chưa có)
- 🔴 Populate `user_id` từ `documents.user_id` → set NOT NULL
- Tạo bảng `graph_edit_log`
- Tạo trigger function `increment_version_and_timestamp()`
- Apply triggers lên 2 bảng

### 9.3 Trigger SQL (tham chiếu — sẽ do Alembic generate)

```sql
CREATE OR REPLACE FUNCTION increment_version_and_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version := OLD.version + 1;
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to entities and relations
CREATE TRIGGER trg_graph_entities_version
    BEFORE UPDATE ON graph_entities
    FOR EACH ROW
    EXECUTE FUNCTION increment_version_and_timestamp();

CREATE TRIGGER trg_graph_relations_version
    BEFORE UPDATE ON graph_relations
    FOR EACH ROW
    EXECUTE FUNCTION increment_version_and_timestamp();
```

### 9.4 Rollback Plan

Nếu migration có vấn đề:
```bash
# Rollback 1 migration
alembic downgrade -1

# Rollback về điểm cụ thể
alembic downgrade <revision_id>

# Nếu cần revert thủ công (emergency):
# 1. DROP TRIGGER trg_graph_entities_version;
# 2. DROP TRIGGER trg_graph_relations_version;
# 3. DROP FUNCTION increment_version_and_timestamp();
# 4. ALTER TABLE graph_entities DROP COLUMN version, DROP COLUMN updated_at;
# 5. ALTER TABLE graph_relations DROP COLUMN version, DROP COLUMN updated_at;
# 6. DROP TABLE graph_edit_log;
```

### 9.5 Verify sau migration

- [ ] `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'graph_entities' AND column_name IN ('version', 'updated_at');` — có 2 rows
- [ ] `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'graph_relations' AND column_name IN ('version', 'updated_at', 'user_id');` — có 3 rows
- [ ] `SELECT COUNT(*) FROM graph_relations WHERE user_id IS NULL;` — = 0 (đã populate hết)
- [ ] `SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_graph_%';` — có 2 triggers
- [ ] `SELECT COUNT(*) FROM graph_edit_log;` — table tồn tại (0 rows)
- [ ] Index `idx_graph_entities_user_id` đã tồn tại (không cần tạo lại)
- [ ] Index `idx_graph_relations_user_id` đã được tạo thành công
- [ ] Test update entity → verify `version` tự động increment
- [ ] Test create relation → verify `user_id` được set đúng

### 9.6 Update SQLAlchemy Model

Sau khi migration chạy thành công, cập nhật `app/models/graph.py`:

```python
class GraphRelation(Base, TimestampMixin):
    __tablename__ = "graph_relations"

    # ... existing fields ...
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(...)

    __table_args__ = (
        # ... existing constraints ...
        Index("idx_graph_relations_user_id", "user_id"),  # Thêm index mới
    )
```

---

## 10. Database Schema Bổ sung

### 10.1 graph_edit_log Table (Sprint 9)

```sql
CREATE TABLE graph_edit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES graph_entities(id) ON DELETE SET NULL,
    relation_id UUID REFERENCES graph_relations(id) ON DELETE SET NULL,
    action VARCHAR(20) CHECK (action IN ('create_entity', 'update_entity', 'delete_entity',
                                          'create_relation', 'update_relation', 'delete_relation')),
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_graph_edit_log_user ON graph_edit_log(user_id);
CREATE INDEX idx_graph_edit_log_entity ON graph_edit_log(entity_id);
```

### 10.2 Version Columns cho Optimistic Concurrency (Sprint 9)

> **Note:** Trigger function `increment_version_and_timestamp()` được define ở Section 9.3 (Alembic Migration).

```sql
-- Thêm version tracking để tránh "lost update" khi concurrent edits
ALTER TABLE graph_entities
    ADD COLUMN version INT DEFAULT 1 NOT NULL,
    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE graph_relations
    ADD COLUMN version INT DEFAULT 1 NOT NULL,
    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Trigger đã được tạo ở Section 9.3 (increment_version_and_timestamp)
-- Không cần định nghĩa lại ở đây để tránh duplicate.
```

### 10.3 Indexes bổ sung

> **Note:** `idx_graph_entities_user_id` đã tồn tại trong model (`app/models/graph.py` line 43). Chỉ cần tạo thêm index cho `graph_relations`.
>
> **🔴 Quan trọng:** `graph_relations` hiện tại KHÔNG có cột `user_id` (chỉ có `document_id`). Phải thêm cột trước khi create index.

```sql
-- Bước 1: Thêm cột user_id vào graph_relations (để thỏa BR-001: user isolation)
ALTER TABLE graph_relations
    ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Bước 2: Populate user_id từ document (JOIN với documents table)
UPDATE graph_relations gr
SET user_id = d.user_id
FROM documents d
WHERE gr.document_id = d.id;

-- Bước 3: Set NOT NULL sau khi đã populate
ALTER TABLE graph_relations
    ALTER COLUMN user_id SET NOT NULL;

-- Bước 4: Tạo index
CREATE INDEX idx_graph_relations_user_id ON graph_relations(user_id);
```

---

## 11. API Endpoints Bổ sung (v1 Standard)

### 11.1 Visualizer Agent (Sprint 8)

```http
POST /api/v1/graph/mermaid
Content-Type: application/json
```

**Request:**
```json
{
  "topic": "Backpropagation",
  "max_nodes": 50,
  "max_depth": 2,
  "format": "mindmap"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "mermaid_code": "mindmap\n  root((Backpropagation))\n    Gradient Descent\n      Learning Rate\n      Loss Function\n    Chain Rule\n      Derivatives\n        Partial Derivatives",
    "metadata": {
      "total_nodes": 8,
      "total_edges": 7,
      "truncated": false,
      "format": "mindmap"
    }
  }
}
```

### 11.2 Graph Editing (Sprint 9)

**Create Entity:**
```http
POST /api/v1/graph/entities
Content-Type: application/json
```
```json
{
  "name": "Learning Rate",
  "entity_type": "term",
  "description": "Hyperparameter controlling step size in gradient descent",
  "document_id": "doc_abc123"
}
```

**Update Entity (Optimistic Concurrency):**
```http
PUT /api/v1/graph/entities/{id}
Content-Type: application/json
```
```json
{
  "name": "Learning Rate (updated)",
  "description": "Updated description",
  "expected_version": 3
}
```

**Delete Entity:**
```http
DELETE /api/v1/graph/entities/{id}?expected_version=3
```

**Conflict Response (409):**
```json
{
  "error": "CONCURRENT_EDIT",
  "message": "Entity đã được chỉnh sửa bởi user khác",
  "current_version": 4,
  "your_version": 3
}
```

---

## 12. Constants Bổ sung

```python
# app/constants.py — Stage 3 Additions

# Visualizer Agent
MERMAID_MAX_NODES = 100
MERMAID_DEFAULT_DEPTH = 2
MERMAID_SUPPORTED_FORMATS = ["graph TD", "mindmap", "flowchart LR"]

# Graph Editing
GRAPH_EDIT_HISTORY_MAX = 50
GRAPH_ENTITY_NAME_MAX_LENGTH = 500
GRAPH_RELATION_TYPES = ["is_a", "part_of", "related_to", "causes", "enables", "prevents", "depends_on"]

# Cache Invalidation (Sprint 9 — B2b)
GRAPH_CACHE_INVALID_TTL_SECONDS = 30  # Redis key TTL cho cache invalidation

# Performance
GRAPH_VIRTUAL_RENDER_THRESHOLD = 500  # nodes
GRAPH_SEARCH_DEBOUNCE_MS = 300
```

---

## 13. Testing Strategy

### 13.1 Unit Tests

| Test File | Coverage | Target |
|-----------|----------|--------|
| `tests/unit/test_visualizer_agent.py` | Subgraph extraction, Mermaid conversion (3 formats), truncation | 15 tests |
| `tests/unit/test_graph_builder_edit.py` | CRUD operations, cascade delete, NetworkX sync | 12 tests |
| `tests/unit/test_graph_cache.py` | Redis key set/clear/check, cache invalidation flow | 8 tests |
| `tests/unit/test_optimistic_concurrency.py` | Version check, conflict handling, 409 response | 6 tests |
| `tests/unit/test_audit_logging.py` | Log ghi đúng, async không block main flow | 5 tests |
| `tests/unit/test_code_parser.py` | Python AST parsing, entity extraction | 8 tests |
| `tests/unit/test_youtube_transcript.py` | Transcript fetching, error handling | 6 tests |

### 13.2 Integration Tests

| Test File | Coverage | Target |
|-----------|----------|--------|
| `tests/integration/test_graph_edit_api.py` | API endpoints, user isolation, validation, 409 conflict | 15 tests |
| `tests/integration/test_mermaid_api.py` | API endpoint, response format, error cases | 8 tests |
| `tests/integration/test_youtube_pipeline.py` | End-to-end: URL → transcript → graph → chat | 4 tests |

### 13.3 E2E Tests (Manual)

| Flow | Steps | Expected |
|------|-------|----------|
| **Generate Mermaid Diagram** | Upload PDF → Open GraphExplorer → Switch to Diagram View → Select "mindmap" → Generate | Mermaid diagram renders correctly |
| **Edit Graph via UI** | Open GraphExplorer → Right-click node → Delete → Confirm → Undo (Ctrl+Z) | Node deleted, undo restores it |
| **Create Entity** | Open GraphExplorer → Click "Add Entity" → Fill form → Submit → Refresh page | Entity persists after refresh |
| **Create Relation (Drag)** | Click node A → Drag edge → Drop on node B → Select relation type → Submit | Edge created, persists after refresh |
| **Chat with Diagram** | Chat: "Draw a diagram of backpropagation" → AI response | Mermaid diagram renders in chat |
| **Dark Mode** | Toggle dark mode → Check all pages | All components adjust to dark theme |
| **Concurrent Edit Conflict** | Tab 1: Edit entity → Tab 2: Edit same entity → Tab 1: Save → Tab 2: Save | Tab 2 gets 409 Conflict, resolution modal appears |

---

## 14. Success Criteria

| Metric | Target | Cách đo |
|--------|--------|---------|
| Mermaid diagram render time | < 2s | Time from API call to UI display |
| Graph edit response time | < 500ms (P95) | Time from UI action to backend ack |
| User can create entity in < 3 clicks | ✅ | Manual testing |
| Graph with 500 nodes loads in < 3s | ✅ | Performance benchmark (so với baseline U0) |
| Stage 3 tests | 60+ tests passing | pytest + frontend tests |
| Lighthouse score | > 90 | Lighthouse CI |
| Performance improvement vs baseline | ≥ 20% faster | So sánh U0 baseline → sau U3 optimization |

> **Note:** "Dark mode adoption > 30% users" và "Diagram usage rate > 50% sessions" bị loại khỏi Stage 3 vì chưa có analytics infrastructure. Sẽ đo ở Stage 4 khi có user analytics.

---

## 15. Timeline Summary

```
Week 1-2:   Sprint 8  — Visualizer Agent & Mermaid ✅ (P0)
Week 3-4:   Sprint 9  — Interactive Graph Editing ✅ (P0)
Week 5-6:   Sprint 10 — Source Code Visualizer ⏸️ (P1 — Optional)
Week 7-8:   Sprint 11 — Media Microlearning ⏸️ (P1 — Optional)
Week 9-10:  Sprint 12 — UI Polish & Performance ✅ (P2)
            └─ U0: Perf baseline (Week 9, trước U3)
```

**Tối thiểu cho Stage 3 "done"**: Sprint 8 + 9 + 12 = **6 tuần**
**Đầy đủ (có P1 features)**: **10 tuần**
**Buffer khuyến nghị:** Thêm 1-2 tuần giữa Sprint 9 và 10 cho bug fixing

---

## 16. Rủi ro Tổng hợp

| Rủi ro | Sprint | Khả năng | Impact | Giảm thiểu |
|--------|--------|---------|--------|-----------|
| Mermaid rendering chậm với graphs lớn | 8 | Trung bình | Trung bình | Limit max_nodes=100, warn user nếu graph too large |
| **NetworkX out-of-sync với PostgreSQL** | 9 | Thấp | Cao | **Redis Cache Invalidation:** Set key `graph_cache_invalid:{doc_id}=1` khi edit. `GraphBuilder` check → reload từ DB. Fallback: TTL 30s |
| **Editing conflict (2 tabs cùng edit)** | 9 | Trung bình | Cao | **Optimistic Concurrency Control:** `version` column + `WHERE version = expected_version` → 409 Conflict, user resolve manually |
| Audit logging làm chậm edit ops | 9 | Thấp | Thấp | Async fire-and-forget. Nếu fail → log warning, không block |
| YouTube API quota hết | 11 | Cao | Trung bình | Fallback: user paste transcript manual |
| **Audio transcription đắt (OpenAI API)** | 11 | Trung bình | Cao | **Cost estimation modal** trước khi xử lý. Giới hạn 5 audio/day. Warn user nếu >10 phút. |
| **Local Mode violation (BR-008)** | 11 | Thấp | 🔴 CRITICAL | **Check `local_mode` trước khi gọi Whisper API.** Nếu local mode ON + whispercpp OFF → từ chối, yêu cầu user dán transcript thủ công. |
| Dark mode không sync mermaid | 12 | Trung bình | Thấp | Dùng CSS variables, test cả 2 themes |
| Graph >500 nodes chậm | 12 | Cao | Trung bình | Virtual rendering, lazy loading, đo baseline U0 trước |

---

## 17. Migration Checklist

Trước khi bắt đầu Stage 3:

- [ ] Stage 2 hoàn thành (Flashcards, Quiz, Notes working)
- [ ] Tất cả blocking issues từ Stage 1 resolved
- [ ] Database backup trước khi chạy migrations (`backup_stage2.sql`)
- [ ] Test migration trên local DB trước khi áp dụng
- [ ] Rollback plan đã được test (`alembic downgrade -1` hoạt động)
- [ ] Test environment sẵn sàng (PostgreSQL, Redis, ChromaDB)
- [ ] Frontend build pass (`npm run build` — 0 errors)
- [ ] Backend tests passing (`pytest` — 90+ tests)
- [ ] Performance baseline plan sẵn sàng (Sprint 12 U0)

---

## 18. Post-Stage 3 Roadmap

Sau khi Stage 3 hoàn thành, các tính năng tiếp theo:

1. **Collaborative Learning** (Stage 4 — Week 11-14)
   - Shared knowledge graphs qua WebSockets
   - Real-time co-editing notes
   - Team learning analytics

2. **Mobile App (PWA)** (Stage 4 — Week 15-16)
   - Service workers cho offline mode
   - Installable trên mobile
   - Push notifications cho flashcard reminders

3. **Authentication & Multi-tenancy** (Stage 4 — Week 17+)
   - JWT-based auth system
   - User roles & permissions
   - OAuth integration (Google, GitHub)

---

> [!IMPORTANT]
> **Stage 3 priority: Visualization trước, Multimedia sau.**
> Sprint 8-9 là core differentiator của AetherTutor so với AI chat thông thường.
> Sprint 10-11 là nice-to-have, có thể delay sang Stage 4 nếu resource hạn chế.

---

© 2026 AetherTutor Team. Created: April 10, 2026 | Last Updated: April 10, 2026 (v1.4)
