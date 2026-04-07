# Task: Phase 5 - Frontend Interface Implementation

> **Updated:** April 7, 2026 — Dựa trên kiểm tra thực tế backend code + deep review chi tiết

## Sprint 0: Backend Readiness (P0)
- [x] **S0.1** Thêm `ProcessingStep` Enum vào `app/models/document.py` (7 steps) + cập nhật `pipeline.py` (5 step updates), `tasks.py` (EXTRACTING step), `document_repo.py` (thêm method `update_processing_step`)
- [x] **S0.2** Tạo Alembic Migration cho ProcessingStep enum + column
- [x] **S0.3** Bổ sung 5 fields mới vào `DocumentDetail` schema + cập nhật endpoints `list_documents`, `get_document_status` để query `count_entities`/`count_relations` từ `graph_repo`
- [x] **S0.4** Upload endpoint phân biệt 200/202: `document_service.py` trả tuple `(doc, is_duplicate)` → endpoint **BỎ CẢ `response_model` LẪN `status_code`**, dùng `JSONResponse` trực tiếp — 200 cho trùng hash, 202 cho file mới
- [x] **S0.5** Sửa `retriever.retrieve()` trả về tuple `(context, entity_names)` thay vì chỉ `context` → cập nhật `chat_service.py`, `graph.py/query_graph`, `chat.py/socratic` để unpack tuple → gửi `found_entities` trong SSE `done` event (dùng `json.dumps(..., default=str)` để handle UUID/datetime)
- [x] **S0.6** Cập nhật `/health` endpoint: thêm LLM metadata (model, embedding_model, provider, mode, healthy) + `health_check()` method trong `llm_service.py`
- [x] **S0.7** ⚠️ **CRITICAL** — Thêm `CORSMiddleware` vào `main.py`: `allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`

## Sprint 1: Bootstrap & Design System (P1)
- [x] **S1.1** Scaffold Vite + React + TS project
- [x] **S1.2** Cài đặt dependencies (Core, Markdown, MSW, Vitest)
- [x] **S1.3** Thiết lập `src/index.css` (Design System Tokens)
- [x] **S1.4** Khởi tạo Router & Base Layout Shell

## Sprint 2: Data Layer (P0)
- [x] **S2.1** Axios client + Response Interceptor: check content-type (phát hiện HTML error page từ backend — backend không có global error handler), custom `ApiError` class, retry 1 lần 502/503 (GET only)
- [x] **S2.2** Triển khai API services (Documents, Chat, Graph)
- [x] **S2.3** Thiết lập Zustand Stores (Document, Chat, UI)
- [x] **S2.4** Triển khai `useChat` SSE hook (Buffered Parser, AbortController)
- [x] **S2.5** SSE Retry Logic — chỉ retry trước khi nhận `meta` event, max 3 lần, exponential backoff. Sau `meta` → error state, user tự retry
- [x] **S2.6** Triển khai `usePolling` hook — poll mỗi 3s, auto-stop khi COMPLETED/FAILED, Document Deletion Guard (404 → redirect), Conversation Title Sync (poll 5 lần sau khi COMPLETED)
- [x] **S2.7** Router Guards — kiểm tra document status trước khi vào `/chat`, `/graph`

## Sprint 3: Base UI Components (P1)
- [x] **S3.1** Xây dựng Buttons, Badges, Cards
- [x] **S3.2** Hoàn thiện Modals, Toasts, Skeletons, Tooltips, Spinners, Progress Bars

## Sprint 4: App Layout (P1)
- [x] **S4.1** Sidebar + Navigation: Responsive, Active States (Lucide)
- [x] **S4.2** LLM Mode Badge (🔒 Local / 🌐 Cloud) — connect `/health` để detect backend mode
- [x] **S4.3** Mobile Responsive adjustments & Glassmorphism Header — Mobile sidebar toggle với framer-motion drawer

## Sprint 5: Document Management (P1)
- [x] **S5.1** Dashboard (Recent docs, Quick Actions, Empty state)
- [x] **S5.2** Document Library (List, Filter, Sort, **"Load more" pagination** — skip/limit)
- [x] **S5.3** Upload Flow với Processing Progress UI (granular steps: EXTRACTING → CHUNKING → EXTRACTING_ENTITIES → BUILDING_GRAPH → EMBEDDING)

## Sprint 6: Chat Interface (P0 - Core)
- [x] **S6.1** MessageBubble (Markdown rendering + streaming cursor)
- [x] **S6.2** MessageList (Virtualization, Auto-scroll, Loading skeleton)
- [x] **S6.3** Chat Input & Streaming Cursor
- [x] **S6.4** Mode Indicator & Context Chips (từ `found_entities` trong SSE `done` event)
- [x] **S6.5** MVP Scope: Chỉ kích hoạt Feynman Test — Diagram/Quiz disabled (tooltip: "Coming soon")
- [x] **S6.6** ConversationList — Data từ `ConversationRead[]` (không có messages), Fallback title "Hội thoại #N" nếu title = "Cuộc hội thoại mới", auto-update khi backend generate title xong (poll max 5 lần, 15s timeout)
- [x] **S6.7** ChatPage — Document Deletion Guard (404 → redirect), Orphaned Conversation Guard

## Sprint 7: Knowledge Graph (P1) — MVP Basic
- [x] **S7.1** GraphNode — Custom EntityNode với color theo type (concept/term/process/theory)
- [x] **S7.2** GraphEdge — Custom edge với label relation_type
- [x] **S7.3** Simple Layout — Radial layout từ tâm (thay vì random)
- [x] **S7.4** GraphControls — Search filtering logic (highlight matching, dim others)
- [x] **S7.5** GraphSidebar — Entity detail panel khi click node (name, type, description, neighbors, degree, "Chat về entity" button)
- [x] **S7.6** GraphPage — Document Deletion Guard + Empty state

## Sprint 8: Polish & Testing (P2)
- [x] **S8.1** Empty States (Dashboard, Library, Chat, Graph) — Graph có empty state mới
- [x] **S8.1a** Error State: LLM Timeout (Retry / Switch Local Mode)
- [x] **S8.1b** Error State: File >50MB (Dismiss only)
- [x] **S8.1c** Error State: PDF Scan/no text layer (Dismiss only)
- [x] **S8.1d** Error State: Invalid API Key (Go to Settings)
- [x] **S8.1e** Error State: Network Failure (Retry / Switch Local Mode)
- [x] **S8.1f** Error State: Chat AI không phản hồi (Retry / Check Settings) — trigger: không nhận chunk nào sau 30s
- [x] **S8.2** Global Error Boundary (Route-level wrapping với `react-error-boundary`)
- [x] **S8.3** Micro-animations & Transitions (Framer Motion) — Page transitions, modal scales, entity chips animations
- [x] **S8.4** Responsive Layout (Mobile/Tablet) — Mobile sidebar toggle với drawer animation
- [x] **S8.5** Unit Testing — 46 tests passing (Error types, Stores, SSE parser, ApiError)
- [x] **S8.6** End-to-End Integration Test — Manual test guide created (4 flows + error recovery)
- [x] **S8.7** README & Build Optimization — `npm run build` SUCCESS (0 errors, 1.2MB JS, 95KB CSS)
- [x] **S8.8** Accessibility & ARIA labels — Chat log/aria-live, input aria-labels, nav role, button labels, LLM badge role=status

---

## Ghi chú quan trọng từ Deep Review

### Backend Gaps đã phát hiện
| Gap | Mức độ | Sprint xử lý |
|-----|--------|-------------|
| Không có CORS middleware | 🔴 Critical | S0.7 |
| `retriever.retrieve()` không trả entity names | 🔴 Critical | S0.5 |
| Upload endpoint hard-coded status 202 | 🟡 Important | S0.4 |
| Backend không có global error handler (trả HTML 500) | 🟡 Important | Frontend S2.1 handle |
| `context_used` có thể chứa non-serializable data | 🟡 Important | S0.5 (`default=str`) |
| Conversation title gen bất đồng bộ (5-10s delay) | 🟠 Note | Frontend S6.6 poll |

### Files backend bị ảnh hưởng
| File | Thay đổi |
|------|---------|
| `app/main.py` | Thêm CORS middleware + LLM metadata vào `/health` |
| `app/models/document.py` | Thêm ProcessingStep enum + column |
| `app/schemas/lightrag.py` | Thêm 5 fields vào DocumentDetail |
| `app/services/document_service.py` | Trả tuple `(doc, is_duplicate)` |
| `app/api/documents.py` | Dùng JSONResponse, phân biệt 200/202, map fields mới |
| `app/repositories/document_repo.py` | Thêm `update_processing_step()` |
| `app/core/pipeline.py` | 5 calls `update_processing_step()` |
| `app/worker/tasks.py` | 1 call `update_processing_step(EXTRACTING)` |
| `app/core/retriever.py` | Trả tuple `(context, entity_names)` |
| `app/services/chat_service.py` | Unpack tuple, thêm `found_entities` vào `done` event |
| `app/api/graph.py` | Unpack tuple trong `query_graph()` |
| `app/api/chat.py` | Unpack tuple trong `socratic_chat_legacy()` |
| `app/services/llm_service.py` | Thêm `health_check()` method |
| `alembic/versions/` | Migration mới cho ProcessingStep |
