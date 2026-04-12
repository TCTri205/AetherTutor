# Stage 5 Plan: Intelligence Maturity, Production Readiness & v1.0 Launch

> **Date:** 2026-04-12
> **Author:** AetherTutor Team
> **Status:** DRAFT — Pending approval
> **Parent:** [Product Roadmap](../reports/2026-04-07_product_roadmap.md)
> **Previous:** [Stage 4 Plan](./2026-04-12_stage4_interactive_ux_collaboration.md)
> **Version:** 1.1 — Quality checkpoints: Feedback Loop, Privacy & Compliance, Circuit Breaker

---

## Bối cảnh

### Hiện trạng (Post-Stage 4) — Đã kiểm chứng codebase thực tế

| Hạng mục | Đã có (Verified) | Ghi chú |
|----------|----------------|---------|
| **Backend API** | 115 routes ✅ | 17 router files: auth, agents, chat, collaboration, documents, flashcards, graph, notes, push, quiz, topics, users, websocket |
| **Frontend** | 13 pages ✅ | Dashboard, Vault, Chat, Quiz, GlobalGraphExplorer, GraphExplorer, Zettelkasten, Flashcards, TeamSettings, OfflinePage, LanguageChat, MathChat |
| **Tests** | 349 tests ✅ | `pytest --collect-only` → 349 |
| **Agents** | 4 agents ✅ | Examiner, Visualizer, Language, Math |
| **Models** | 18 models ✅ | +team, shared_resource, entity_document, note_entity_link |
| **WebSocket** | ✅ Có | websocket.py + websocket_handlers.py |
| **PWA** | ✅ Có | manifest.json + service-worker.js + OfflinePage |
| **Dark Mode** | ✅ Có | ThemeProvider + CSS Variables |
| **Collaboration** | ✅ Có | Teams, shared resources, presence, last-write-wins |

### Gaps tồn đọng từ Stage 4 (Deferred/Incomplete)

| # | Item | Sprint gốc | Status | Lý do deferred |
|---|------|-----------|--------|----------------|
| G1 | **Sprint 17: Media Microlearning** | Sprint 17 | ⏸️ DEFERRED | P2 optional, không blocking Stage 4 |
| G2 | **CodeEntityNode.tsx frontend** | Sprint 13 | ✅ Đã có | Audit cho thấy file đã tồn tại (8 files trong `components/graph/`) |
| G3 | **VAPID push production** | Sprint 18 | ⚠️ MOCK | `pywebpush` bị comment out, chỉ log mock |
| G4 | **Sprint 15 tests (25 tests)** | Sprint 15 | ❌ Thiếu | WebSocket load tests, E2E collaboration chưa có |
| G5 | **Sprint 13 tests (15 tests)** | Sprint 13 | ❌ Thiếu | Code parser unit tests chưa có |
| G6 | **Sprint 16 tests (15 tests)** | Sprint 16 | ❌ Thiếu | Agent unit tests chưa có |
| G7 | **Rate limiting 23 recommendations** | Sprint 19 | ⚠️ Partial | 12% coverage, 23 recommendations chưa áp dụng |
| G8 | **Lighthouse CI** | Sprint 14/18 | ❌ Chưa có | PWA score, performance audit chưa automate |
| G9 | **Bundle size audit** | Sprint 14 | ❌ Chưa có | Target <1.5MB gzipped chưa kiểm chứng |
| G10 | **Frontend TODO audit** | Sprint 19 | ⚠️ Partial | ErrorBoundary → Sentry còn TODO |
| G11 | **CRDT upgrade** | Sprint 15 | ⚠️ Last-write-wins | Cần Yjs cho conflict resolution mạnh hơn |
| G12 | **Icon generation** | Sprint 18 | ⚠️ SVG placeholders | Chưa có PNG icons 192x192, 512x512 |
| G13 | **Email templates HTML** | Sprint 19 | ⚠️ Basic | Chưa có HTML email templates đẹp |
| G14 | **Mermaid.js双向渲染** | Roadmap Stage 3 | ❌ Chưa có | VisualizerAgent chưa render Mermaid từ graph |
| G15 | **Interactive graph editing** | Roadmap Stage 3 | ❌ Chưa có | Chưa có create/delete nodes/edges trên UI |
| G16 | **Mindmap/Flowchart editing** | Roadmap Stage 3 | ❌ Chưa có | Chưa có visual editor |

### Roadmap yêu cầu còn thiếu (Stage 3 chưa hoàn thành)

| Yêu cầu | Trạng thái |
|---------|-----------|
| Visualizer Agent với Mermaid.js | ⚠️ Có VisualizerAgent nhưng chưa render Mermaid |
| Media Microlearning Pipeline | ❌ Chưa có (Sprint 17 deferred) |
| Source Code Visualizer | ✅ Backend có, frontend CodeEntityNode.tsx có |
| Interactive graph editing | ❌ Chưa có |
| Mindmap/Flowchart editing | ❌ Chưa có |

---

## Tầm nhìn Stage 5

Stage 5 là giai đoạn **hoàn thiện để phát hành v1.0 Public** — biến AetherTutor từ nền tảng học tập thông minh thành **sản phẩm production-ready hoàn chỉnh** với:

1. **Intelligence Maturity** — Media processing, advanced reasoning, multi-agent orchestration
2. **Production Readiness** — Full testing, monitoring, performance, security hardening
3. **Interactive Visualization** — Graph editing, Mermaid diagrams, mindmap/flowchart
4. **Mobile Polish** — PWA hoàn chỉnh, push notifications production, responsive design
5. **v1.0 Launch** — Documentation, onboarding, pricing, analytics

---

## Kiến trúc Stage 5

```
Stage 5: Intelligence Maturity, Production Readiness & v1.0 Launch
├── Sprint 20: Media Microlearning (Deferred Sprint 17)    [P1] — 11 tasks
├── Sprint 21: Interactive Graph Editing & Visualization   [P0] — 16 tasks (+2 Feedback Loop)
├── Sprint 22: Testing & Quality Gateway                   [P0] — 15 tasks
├── Sprint 23: Production Hardening & Observability         [P0] — 14 tasks (+2 Privacy & Compliance)
├── Sprint 24: Multi-Agent Orchestration & Advanced AI      [P1] — 10 tasks
├── Sprint 25: Mobile Polish & PWA Production               [P1] — 8 tasks
├── Sprint 26: Documentation, Onboarding & Launch Prep      [P0] — 10 tasks
└── Sprint 27: Performance & Scalability                    [P1] — 9 tasks (+1 Circuit Breaker)
```

**Tổng:** 8 Sprints, **93 tasks** (~145h) — Bao gồm 3 chốt chặn chất lượng: Feedback Loop, Privacy & Compliance, Circuit Breaker

---

## Sprint 20: Media Microlearning (Deferred Sprint 17)

> **Priority:** P1 | **Dependency:** None | **Estimate:** ~18.5 giờ

Hoàn thành Sprint 17 bị deferred từ Stage 4 — YouTube transcript, Whisper transcription, video/audio players.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **YouTube Transcript Service** | Backend | `app/services/youtube_service.py` — Dùng `youtube-transcript-api` pip package. Fetch transcript by URL hoặc video ID. Support: auto-generated subtitles, multiple languages. Handle rate limits với retry + backoff | 2h |
| 2 | **Audio Upload & Storage** | Backend | Accept `.mp3`, `.wav`, `.m4a` trong upload pipeline. Lưu `uploads/audio/`. Validate: max 50MB, correct MIME type. Generate unique filename với UUID | 1h |
| 3 | **Whisper Transcription Service** | Backend | `app/services/transcription_service.py` — Support 2 modes: (1) OpenAI Whisper API (cloud), (2) `faster-whisper` local (CPU). Chunk transcript theo timestamps. **BR-008 Compliance:** Nếu `local_mode=True` + `whisper_cpp=False` → từ chối với error message rõ ràng | 3h |
| 4 | **Transcript → Text Pipeline** | Backend | Reuse existing ingestion: transcript chunks → entity extraction → graph building. Map timestamps → entities để sync playback | 2h |
| 5 | **Video Player Component** | Frontend | `frontend/src/components/media/VideoPlayer.tsx` — Embed YouTube player (iframe API) hoặc HTML5 video. Sync transcript highlight với playback time. Controls: play/pause, seek, speed (0.5x-2x) | 4h |
| 6 | **Transcript Viewer** | Frontend | `frontend/src/components/media/TranscriptViewer.tsx` — Hiển thị transcript với timestamps. Click timestamp → seek video/audio. Highlight current line based on playback position | 2h |
| 7 | **Media Document Type** | Backend | Migration: thêm `media_type` enum (video/audio/text) vào `documents` table. Thêm `source_url` cho YouTube URLs. Validation: URL format cho YouTube | 1h |
| 8 | **Audio Player with Sync** | Frontend | `frontend/src/components/media/AudioPlayer.tsx` — Waveform visualization (wavesurfer.js hoặc custom canvas). Sync transcript với playback. Controls: play/pause, seek, speed | 2h |
| 9 | **Tests** | Testing | 10 tests: YouTube fetch, transcript parsing, audio upload validation, BR-008 compliance, timestamp sync | 1h |
| 10 | **Worker Registration** | Backend | Đăng ký `process_youtube_task` và `process_audio_transcription_task` vào `WorkerSettings.functions` trong `app/worker/tasks.py` | 0.5h |

### Deliverables

- `app/services/youtube_service.py` (~150 lines)
- `app/services/transcription_service.py` (~200 lines)
- `frontend/src/components/media/VideoPlayer.tsx` (~150 lines)
- `frontend/src/components/media/AudioPlayer.tsx` (~180 lines)
- `frontend/src/components/media/TranscriptViewer.tsx` (~120 lines)
- Migration: `media_type` enum, `source_url` column
- 10 unit tests
- Worker tasks registered

### Acceptance Criteria

- ✅ Paste YouTube URL → fetch transcript → build graph tự động
- ✅ Upload `.mp3` → transcribe → extract entities → sync transcript với audio
- ✅ Click transcript line → audio seek tới timestamp
- ✅ BR-008: Local mode + no whisper_cpp → reject với error rõ ràng
- ✅ 10/10 tests passing

---

## Sprint 21: Interactive Graph Editing & Visualization

> **Priority:** P0 | **Dependency:** Stage 3 (Graph CRUD), Stage 4 (UI Polish) | **Estimate:** ~27.5 giờ

Hoàn thành yêu cầu còn thiếu từ Roadmap Stage 3: interactive graph editing, Mermaid.js rendering, mindmap/flowchart.
**Bổ sung chốt chặn chất lượng:** Feedback Loop (AI response rating + entity error reporting).

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Mermaid.js Renderer Service** | Backend | `app/services/mermaid_renderer.py` — Convert NetworkX graph → Mermaid.js syntax. Support 3 diagram types: `mindmap`, `flowchart TD`, `graph TD`. Layout algorithm: group by entity type, sort by degree centrality. Handle large graphs (>200 nodes) với subgraph clustering | 3h |
| 2 | **Mermaid Diagram API Endpoint** | Backend | `GET /graph/{id}/mermaid` — Return Mermaid.js syntax + metadata (diagram_type, node_count, entity_types). Query params: `?type=mindmap|flowchart|graph`. Cache result trong Redis (5min TTL) | 1.5h |
| 3 | **MermaidDiagram Component** | Frontend | `frontend/src/components/shared/MermaidDiagram.tsx` — Render Mermaid.js syntax dùng `mermaid` npm package. Support: zoom/pan, download PNG/SVG, error boundary cho parse errors. Lazy-load mermaid library (code splitting) | 3h |
| 4 | **Graph Edit Mode Toggle** | Frontend | Thêm "Edit Mode" button trong GraphExplorer. Khi active: hiển thị toolbar (add node, add edge, delete, undo/redo). Visual indicators: dashed borders, hover highlights | 2h |
| 5 | **Create Node on Graph** | Frontend + Backend | Frontend: Click empty space → modal nhập entity name/type. Backend: `POST /graph/{id}/entities` với validation (unique name, valid type). WebSocket broadcast `node_created` cho collaborators | 3h |
| 6 | **Create Edge on Graph** | Frontend + Backend | Frontend: Drag từ node A → node B → modal nhập relation type. Backend: `POST /graph/{id}/relations` với validation (no duplicate edges, valid relation_type). WebSocket broadcast `relation_created` | 2.5h |
| 7 | **Delete Node/Edge** | Frontend + Backend | Frontend: Select node/edge → Delete key hoặc button → confirmation modal. Backend: `DELETE /graph/{id}/entities/{eid}`, `DELETE /graph/{id}/relations/{rid}`. Cascade delete: xóa node → xóa relations liên quan. WebSocket broadcast `node_deleted`/`relation_deleted` | 2.5h |
| 8 | **Undo/Redo System** | Frontend | `useGraphUndoRedo.ts` hook — Command pattern: lưu edit history (max 50 steps). `Ctrl+Z` undo, `Ctrl+Y` redo. Persist history trong sessionStorage. Sync với WebSocket cho collaborative undo | 2.5h |
| 9 | **Graph Versioning** | Backend | `app/models/graph_edit_log.py` — Log mọi edit (create/update/delete) với: user_id, timestamp, before/after state, vector clock. API: `GET /graph/{id}/history` — xem edit log, `POST /graph/{id}/revert/{log_id}` — revert to version | 2h |
| 10 | **Entity Alias System** | Frontend + Backend | `AliasManager.tsx` component — Cho phép đặt alias cho entities (ví dụ: "ML" = "Machine Learning"). Backend: `app/models/entity_alias.py` — Alias table với user_id, entity_name, alias. Resolve aliases khi chat/query | 1.5h |
| 11 | **Graph Search & Filter** | Frontend | `GraphSearchBar.tsx` — Fuzzy search entity names, filter by type (Class/Function/Concept), filter by tag. Highlight matched nodes. Keyboard: `Ctrl+F` focus search | 1h |
| 12 | **Tag System for Graph** | Backend + Frontend | Thêm `tags TEXT[]` vào `graph_entities`. `TagFilter.tsx` component — Filter by tags, create/delete tags. API: `PUT /graph/{id}/entities/{eid}/tags` | 1h |
| 13 | **Backlinks Panel** | Frontend | `BacklinksPanel.tsx` — Hiển thị entities nào link tới entity hiện tại (giống Obsidian backlinks). Panel trong sidebar, click để navigate | 1h |
| 14 | **🔒 AI Response Feedback (Like/Dislike)** | Frontend + Backend | **FEEDBACK LOOP — Chốt chặn chất lượng #1** — Thumb up/down button trên mọi AI response trong Chat. Backend: `app/models/feedback.py` — Feedback table (id, user_id, conversation_id, message_id, rating: like/dislike, reason, created_at). API: `POST /chat/{conversation_id}/messages/{message_id}/feedback`. Frontend: FeedbackButton component với quick-reason selector (👎 không chính xác, 👎 quá dài, 👎 không liên quan). Dữ liệu dùng để fine-tune prompts và huấn luyện agents Stage 6 | 2h |
| 15 | **🔒 Entity Extraction Error Report** | Frontend + Backend | **FEEDBACK LOOP — Chốt chặn chất lượng #1** — "Report Error" button trên graph entities. Backend: `POST /graph/{document_id}/entities/{entity_id}/report` — Lưu report với: user_id, entity_id, error_type (wrong_name, wrong_type, duplicate, not_relevant), description. Dashboard admin xem report trends. Analytics: entity extraction accuracy tracking | 1.5h |
| 16 | **Tests** | Testing | 17 tests: Mermaid generation, CRUD operations, undo/redo, versioning, aliases, tags, backlinks, +2 feedback loop tests | 2h |

### Deliverables

- `app/services/mermaid_renderer.py` (~200 lines)
- `app/models/graph_edit_log.py` (~80 lines)
- `app/models/entity_alias.py` (~60 lines)
- `app/models/feedback.py` (~60 lines) — NEW: Feedback model
- `frontend/src/components/shared/MermaidDiagram.tsx` (~150 lines)
- `frontend/src/components/graph/AliasManager.tsx` (~100 lines)
- `frontend/src/components/graph/BacklinksPanel.tsx` (~80 lines)
- `frontend/src/components/graph/GraphSearchBar.tsx` (~80 lines)
- `frontend/src/components/graph/TagFilter.tsx` (~70 lines)
- `frontend/src/components/shared/FeedbackButton.tsx` (~80 lines) — NEW: Feedback UI
- `frontend/src/hooks/useGraphUndoRedo.ts` (~100 lines)
- Migration: `graph_edit_log` table, `entity_alias` table, `feedback` table, `tags` column
- 17 unit tests

### Acceptance Criteria

- ✅ `GET /graph/{id}/mermaid?type=mindmap` → valid Mermaid syntax
- ✅ MermaidDiagram render mindmap, flowchart, graph diagrams
- ✅ Edit Mode: tạo/xóa nodes/edges trực tiếp trên GraphExplorer
- ✅ Undo/Redo hoạt động với `Ctrl+Z/Y`, max 50 steps
- ✅ Graph versioning: xem history, revert to previous version
- ✅ Entity aliases: "ML" resolves to "Machine Learning"
- ✅ Tags và backlinks hoạt động đúng
- ✅ WebSocket broadcast edits cho collaborators
- ✅ 🔒 Feedback: Like/Dislike button trên AI responses, lưu reason
- ✅ 🔒 Entity reports: Report error types tracked, admin dashboard hiển thị trends
- ✅ 17/17 tests passing

---

## Sprint 22: Testing & Quality Gateway

> **Priority:** P0 | **Dependency:** Sprint 20, 21 | **Estimate:** ~22 giờ

Hoàn thành tests còn thiếu từ Stage 4 + nâng coverage lên 80%+.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Code Parser Tests (15 tests)** | Testing | Tests cho `code_parser.py`: Python AST parsing, JS/TS regex parsing, entity mapping, file size limits, deduplication, error handling | 2h |
| 2 | **Agent Tests (15 tests)** | Testing | Tests cho `base_agent.py`, `registry.py`, `language_agent.py`, `math_agent.py`: registration, execution, system prompts, capabilities, MCP context, template export/import | 2h |
| 3 | **WebSocket Tests (15 integration)** | Testing | Tests cho websocket: connection auth (JWT invalid → reject), room join/leave, event broadcast, message ordering, heartbeat/ping-pong, disconnect cleanup | 2h |
| 4 | **WebSocket Load Tests (5 tests)** | Testing | Load test với `locust` hoặc `websockets` library: 100 concurrent, 500 concurrent, 1000 concurrent. Measure: message latency, throughput, memory usage, connection stability | 3h |
| 5 | **E2E Collaboration Tests (5 tests)** | Testing | Playwright tests: 2-user co-editing graph, invite-accept-access flow, concurrent edit conflict resolution, leave team → access revoked, shared graph visibility | 4h |
| 6 | **Media Processing Tests (10 tests)** | Testing | Tests cho Sprint 20: YouTube transcript fetch, audio upload validation, BR-008 compliance, transcript parsing, timestamp sync | 1.5h |
| 7 | **Graph Editing Tests (15 tests)** | Testing | Tests cho Sprint 21: Mermaid generation, CRUD operations, undo/redo, versioning, aliases, tags, backlinks | 2h |
| 8 | **E2E User Journeys (5 tests)** | Testing | Playwright tests: (1) Upload PDF → Chat → Graph, (2) Create Flashcard → Review → SM-2 schedule, (3) Create Quiz → Review → Auto-flashcards, (4) Create Team → Share Graph → Collaborate, (5) YouTube → Transcript → Graph | 3h |
| 9 | **API Contract Tests (8 tests)** | Testing | OpenAPI spec validation: tất cả 115 endpoints return đúng schema, status codes, error format. Dùng `schemathesis` hoặc `pytest-openapi` | 1.5h |
| 10 | **Frontend Component Tests (10 tests)** | Testing | Tests cho ThemeProvider, KeyboardShortcuts, AgentSelector, MermaidDiagram, VideoPlayer, AudioPlayer | 1h |
| 11 | **Integration Test Suite** | Testing | `tests/integration/test_full_pipeline.py` — End-to-end: register user → upload doc → process → chat → graph → flashcards → quiz | 1h |
| 12 | **Test Infrastructure** | DevOps | `pytest.ini` update, Playwright config, locust config, GitHub Actions test workflow với parallel execution, coverage report | 1h |

### Deliverables

- 15 tests: code parser
- 15 tests: agents
- 15 tests: websocket integration
- 5 tests: websocket load
- 5 tests: E2E collaboration
- 10 tests: media processing
- 15 tests: graph editing
- 5 tests: E2E user journeys
- 8 tests: API contracts
- 10 tests: frontend components
- 1 integration pipeline test
- Test infrastructure setup

### Acceptance Criteria

- ✅ **115+ tests passing** (từ 349 → 464+)
- ✅ **Test coverage ≥ 80%** (backend + frontend)
- ✅ **WebSocket load:** 1000 concurrent connections ổn định, latency <100ms
- ✅ **E2E:** 10/10 Playwright tests passing
- ✅ **API contracts:** 115/115 endpoints pass schema validation
- ✅ **CI/CD:** Tests chạy parallel trên GitHub Actions, <5min total

---

## Sprint 23: Production Hardening & Observability

> **Priority:** P0 | **Dependency:** Sprint 22 | **Estimate:** ~19 giờ

Hoàn thiện production readiness: VAPID push production, rate limiting, security audit, monitoring, error tracking.
**Bổ sung chốt chặn chất lượng:** Privacy & Compliance (GDPR/CCPA data anonymization + export/delete).

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **VAPID Push Production Setup** | Backend | Uncomment `pywebpush` trong `notification_service.py`. Config VAPID keys trong `.env`. Test push notification trên Chrome/Firefox/Safari. Handle subscription expiration, push errors | 2h |
| 2 | **Rate Limiting Full Implementation** | Backend | Áp dụng 23 recommendations từ audit. Per-endpoint limits: auth (5/min), upload (10/hour), chat (30/min), graph CRUD (60/min), collaboration (100/min). Redis-backed rate limiter, configurable per user role | 2.5h |
| 3 | **Security Audit & Penetration Testing** | Backend | Audit toàn bộ endpoints: IDOR, XSS, CSRF, SQL injection, file upload bypass, WebSocket hijacking. Fix findings. Add security headers (CSP, X-Frame-Options, HSTS) | 2.5h |
| 4 | **Sentry Production Config** | Backend + Frontend | Configure DSN production. Set up alerts (email/Slack). Release tracking. Error sampling (1000 events/day free tier). Source maps cho frontend | 1h |
| 5 | **Database Connection Pooling** | Backend | Config `asyncpg` pool size (min=5, max=20). Connection timeout (30s). Retry logic cho transient failures. Pool metrics export | 1.5h |
| 6 | **Health Check Endpoints** | Backend | `GET /health` — Database, Redis, ChromaDB, LLM. `GET /health/detailed` — thêm queue depth, disk usage, memory. Kubernetes readiness/liveness probes compatible | 1h |
| 7 | **Metrics & Monitoring** | Backend | `app/middleware/metrics.py` — Prometheus middleware: request duration, error rate, active connections, queue depth, graph size. `GET /metrics` endpoint | 2h |
| 8 | **Structured Logging** | Backend | JSON logging format. Correlation ID per request. Log levels: DEBUG (dev), INFO (prod), ERROR (always). Log rotation (daily, 7 days retention) | 1.5h |
| 9 | **Backup & Recovery** | DevOps | Database backup script (pg_dump). Redis snapshot config. ChromaDB backup. Test restore procedure. RPO < 1h, RTO < 30min | 1.5h |
| 10 | **Error Boundary Polish** | Frontend | Fix TODO `ErrorBoundary.tsx:38` → Sentry capture. Add recovery actions (retry button, clear cache, report bug). Fallback UI cho từng page | 1h |
| 11 | **API Versioning Strategy** | Backend | `/api/v1/` prefix cho tất cả routes. Deprecation headers cho old endpoints. Version negotiation header | 1h |
| 12 | **🔒 Data Anonymization for Logs (GDPR/CCPA)** | Backend | **PRIVACY & COMPLIANCE — Chốt chặn chất lượng #2** — Middleware tự động mask PII trong logs trước khi gửi Sentry/Prometheus: email → SHA256 hash, IP → mask 3 octets (192.168.x.x), user_id → pseudonymize token. Configurable per environment. `app/middleware/anonymizer.py` — Regex-based PII detection + hashing pipeline. Compliance log: audit trail cho data processing activities | 2h |
| 13 | **🔒 GDPR Data Export & Account Deletion** | Backend + Frontend | **PRIVACY & COMPLIANCE — Chốt chặn chất lượng #2** — `GET /privacy/export` → ZIP chứa toàn bộ dữ liệu cá nhân (conversations, flashcards, quizzes, notes, graph edits, feedback) theo GDPR Art. 20 (Data Portability). `DELETE /privacy/account` → Xóa vĩnh viễn account + data theo GDPR Art. 17 (Right to be Erasure): soft delete 30 days → hard delete. Confirmation flow với 2-step verification. Frontend: PrivacySettings page trong user profile với export/download/delete buttons | 2.5h |
| 14 | **Tests** | Testing | 12 tests: rate limiting, security headers, health check, metrics, backup restore, anonymization pipeline, GDPR export/delete | 1.5h |

### Deliverables

- `app/services/notification_service.py` (VAPID uncommented + tested)
- `app/middleware/metrics.py` (~120 lines)
- `app/middleware/anonymizer.py` (~150 lines) — NEW: PII anonymization pipeline
- `app/api/privacy.py` (~150 lines) — NEW: GDPR export/delete endpoints
- `frontend/src/pages/PrivacySettings.tsx` (~100 lines) — NEW: Privacy settings UI
- Rate limiting applied to all 115+ endpoints
- Security audit report
- Sentry production config
- Backup scripts
- Structured logging with PII masking
- 12 tests

### Acceptance Criteria

- ✅ VAPID push hoạt động production (Chrome/Firefox/Safari)
- ✅ Rate limiting: 23/23 recommendations áp dụng
- ✅ Security audit: 0 critical/high findings
- ✅ Sentry: errors được capture với source maps
- ✅ Health checks: Kubernetes compatible
- ✅ Metrics: Prometheus endpoint hoạt động
- ✅ Backup: restore test thành công
- ✅ 🔒 Anonymization: 0 PII leaks trong Sentry/Prometheus logs (email hashed, IP masked)
- ✅ 🔒 GDPR export: ZIP download chứa đầy đủ dữ liệu cá nhân
- ✅ 🔒 GDPR delete: Account deletion flow 2-step, soft delete 30 ngày → hard delete
- ✅ 12/12 tests passing

---

## Sprint 24: Multi-Agent Orchestration & Advanced AI

> **Priority:** P1 | **Dependency:** Sprint 22 (testing), Stage 4 (agents) | **Estimate:** ~16 giờ

Nâng cấp từ single-agent sang multi-agent orchestration. Parent Orchestrator điều phối nhiều agents cho complex learning tasks.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Parent Orchestrator Service** | Backend | `app/core/orchestrator.py` — Orchestrate multiple agents: route user intent → best agent, chain agents (Language → Examiner → Flashcard), parallel execution. Support: fallback to default agent, timeout handling | 3h |
| 2 | **Intent Classification** | Backend | `app/services/intent_classifier.py` — Classify user intent: learning_language, math_problem, quiz_request, flashcard_review, graph_query, general_chat. Prompt-based classification (fast LLM call) | 2h |
| 3 | **Agent Chaining API** | Backend | `POST /chat/orchestrate` — Accept message → classify intent → route to agent(s) → aggregate response. Support multi-step: e.g., "tạo quiz từ document này rồi tạo flashcard từ câu sai" → Examiner → Flashcard | 2.5h |
| 4 | **Agent Tool Calling** | Backend | Extend `base_agent.py` với tool calling pattern. Agents có thể call tools: search_graph, create_flashcard, generate_quiz, create_note. OpenAI function calling compatible | 2h |
| 5 | **Learning Path Generator** | Backend | `app/services/learning_path.py` — Generate personalized learning path từ graph entities + user progress. Output: sequence of topics, estimated time, prerequisites, milestones | 2h |
| 6 | **Progress Analytics Dashboard** | Backend + Frontend | `GET /analytics/progress` — Stats: study time, entities mastered, weak areas, streak, SM-2 performance. Frontend: `AnalyticsPage.tsx` với charts (recharts) | 2.5h |
| 7 | **Adaptive Difficulty** | Backend | Adjust quiz/flashcard difficulty based on user performance. Nếu đúng >80% → tăng bloom level. Nếu sai >50% → giảm difficulty + gợi ý ôn tập | 1.5h |
| 8 | **Tests** | Testing | 10 tests: orchestrator routing, intent classification, agent chaining, tool calling, learning path, adaptive difficulty | 1.5h |

### Deliverables

- `app/core/orchestrator.py` (~250 lines)
- `app/services/intent_classifier.py` (~120 lines)
- `app/services/learning_path.py` (~150 lines)
- `frontend/src/pages/AnalyticsPage.tsx` (~200 lines)
- 10 tests

### Acceptance Criteria

- ✅ Orchestrator routing: classify intent → đúng agent (>85% accuracy)
- ✅ Agent chaining: Examiner → Flashcard chain hoạt động
- ✅ Tool calling: agents có thể call search_graph, create_flashcard, generate_quiz
- ✅ Learning path: generate personalized sequence
- ✅ Adaptive difficulty: quiz difficulty điều chỉnh theo performance
- ✅ Analytics dashboard: charts hiển thị progress
- ✅ 10/10 tests passing

---

## Sprint 25: Mobile Polish & PWA Production

> **Priority:** P1 | **Dependency:** Sprint 23 (VAPID production) | **Estimate:** ~12 giờ

Hoàn thiện PWA cho production: responsive design, offline sync, push notifications, install prompt.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Responsive Design Audit** | Frontend | Test tất cả pages trên mobile (375px), tablet (768px), desktop (1440px). Fix layout issues. Touch-friendly: button size ≥44px, swipe gestures | 2h |
| 2 | **Offline Sync Queue** | Frontend | `useOfflineQueue.ts` hook — Queue mutations khi offline (create note, edit graph), sync khi online. IndexedDB storage. Conflict resolution: server wins | 2.5h |
| 3 | **Push Notification Production** | Frontend + Backend | Test VAPID push production. Handle notification click → navigate đúng page. Badge count update. Notification categories: review reminder, due flashcards, collaboration invites | 2h |
| 4 | **Install Prompt Polish** | Frontend | `InstallPrompt.tsx` — Better UX: show after 30s engagement, dismissible, re-show sau 7 ngày. Custom install page với feature list | 1h |
| 5 | **Icon Generation** | Frontend | Replace SVG placeholders với PNG icons: 192x192, 512x512, maskable icons. Generate với `pwa-asset-generator` hoặc manual design | 1.5h |
| 6 | **PWA Lighthouse Audit** | Testing | Run Lighthouse CI: PWA score ≥90, Performance ≥90, Accessibility ≥90, Best Practices ≥90. Fix findings | 1h |
| 7 | **Service Worker Update** | Frontend | Handle service worker updates gracefully (skipWaiting, clientsClaim). Notify user "Update available, refresh?". Fallback cho browsers không support SW | 1.5h |
| 8 | **Tests** | Testing | 8 tests: manifest validity, SW registration, offline queue, push subscription, responsive breakpoints | 1h |

### Deliverables

- `frontend/src/hooks/useOfflineQueue.ts` (~150 lines)
- `InstallPrompt.tsx` (updated)
- PNG icons (192x192, 512x512, maskable)
- Lighthouse CI config
- 8 tests

### Acceptance Criteria

- ✅ Lighthouse PWA score ≥ 90
- ✅ Responsive design: mobile/tablet/desktop ổn
- ✅ Offline queue: tạo note/graph khi offline → sync khi online
- ✅ Push notifications: hoạt động production, click → navigate đúng
- ✅ Install prompt: show/dismiss/re-show hoạt động đúng
- ✅ Service worker update: graceful update flow
- ✅ 8/8 tests passing

---

## Sprint 26: Documentation, Onboarding & Launch Prep

> **Priority:** P0 | **Dependency:** Sprint 22, 23, 24, 25 | **Estimate:** ~16 giờ

Chuẩn bị cho v1.0 public launch: documentation, onboarding flow, pricing, analytics, marketing.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **API Documentation (OpenAPI/Swagger)** | Backend | Polish `/docs` Swagger UI: tags, descriptions, examples. Generate static docs cho `docs/api/`. Postman collection export | 2h |
| 2 | **User Documentation** | Docs | `docs/user/` — Getting Started, Upload Documents, Chat with AI, Flashcards, Quiz, Graph Editing, Team Collaboration, PWA Install. Screenshots + GIFs | 3h |
| 3 | **Developer Documentation** | Docs | `docs/dev/` — Architecture, Setup Guide, Contributing, Code Style, Testing, Deployment, Troubleshooting. Update README.md | 2h |
| 4 | **Onboarding Flow** | Frontend | `OnboardingTour.tsx` — Interactive tour cho new users: highlight features, step-by-step guide. First-run wizard (opt-out). Progress tracking | 2h |
| 5 | **Landing Page** | Frontend | `LandingPage.tsx` — Public page (no auth): features, testimonials, pricing, CTA. SEO optimized (meta tags, OpenGraph). Responsive | 3h |
| 6 | **Pricing & Subscription** | Backend + Frontend | `app/models/subscription.py` — Plan model (free, pro, team). `GET /pricing`, `POST /subscribe`. Frontend: Pricing page với feature comparison table | 1.5h |
| 7 | **Analytics Integration** | Frontend | `app/services/analytics.ts` — PostHog hoặc Plausible (privacy-focused). Track: page views, feature usage, user retention, conversion funnel. Dashboard | 1.5h |
| 8 | **Changelog System** | Backend + Frontend | `app/models/changelog.py` — Changelog entries. `GET /changelog`. Frontend: Changelog page. In-app notification cho new features | 1h |
| 9 | **Release Script** | DevOps | `scripts/release.sh` — Tag git, update version, build production, deploy. Semantic versioning (v1.0.0) | 1h |
| 10 | **Tests** | Testing | 5 tests: onboarding flow, landing page SEO, pricing API, changelog CRUD | 1h |

### Deliverables

- `docs/user/` — User guide (6+ pages)
- `docs/dev/` — Developer guide (6+ pages)
- `frontend/src/components/onboarding/OnboardingTour.tsx` (~200 lines)
- `frontend/src/pages/LandingPage.tsx` (~250 lines)
- `app/models/subscription.py` (~80 lines)
- `frontend/src/pages/PricingPage.tsx` (~150 lines)
- Analytics integration
- Changelog system
- Release script
- 5 tests

### Acceptance Criteria

- ✅ Swagger UI: tất cả endpoints có description, examples, schemas
- ✅ User docs: 6+ guides với screenshots
- ✅ Developer docs: architecture, setup, contributing
- ✅ Onboarding tour: interactive guide cho new users
- ✅ Landing page: SEO optimized, responsive, CTA
- ✅ Pricing: feature comparison, subscription flow
- ✅ Analytics: track page views, feature usage, retention
- ✅ Changelog: in-app notifications cho new features
- ✅ Release script: tag, build, deploy tự động
- ✅ 5/5 tests passing

---

## Sprint 27: Performance & Scalability

> **Priority:** P1 | **Dependency:** Sprint 23 (metrics), Sprint 22 (load tests) | **Estimate:** ~14 giờ

Tối ưu performance và scalability cho production load.
**Bổ sung chốt chặn chất lượng:** Circuit Breaker pattern cho hạ tầng tự phục hồi.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Database Query Optimization** | Backend | Audit N+1 queries. Add indexes cho frequently queried columns. Use `selectinload` thay vì `joinedload` cho relationships. Query plan analysis | 2h |
| 2 | **Caching Strategy** | Backend | Redis cache cho: graph data (5min), agent responses (10min), mermaid diagrams (5min), analytics (15min). Cache invalidation on write. Hit rate monitoring | 2h |
| 3 | **API Response Optimization** | Backend | Pagination cho large datasets (cursor-based). Field selection (`?fields=name,type`). Compression (gzip/brotli middleware). ETag support | 1.5h |
| 4 | **Frontend Bundle Optimization** | Frontend | Code splitting per route. Lazy load heavy components (ReactFlow, Mermaid, wavesurfer). Tree shaking audit. Target: <1MB initial bundle, <3MB total | 2h |
| 5 | **Image & Asset Optimization** | Frontend | Compress images (WebP format). SVG icons thay vì PNG. Font subloading optimization. Preload critical assets | 1h |
| 6 | **WebSocket Scaling** | Backend | Redis pub/sub cho multi-instance WebSocket. Connection pooling. Message batching. Graceful degradation khi overload | 2h |
| 7 | **🔒 Circuit Breaker Pattern** | Backend | **SELF-HEALING INFRASTRUCTURE — Chốt chặn chất lượng #3** — `app/core/circuit_breaker.py` — Circuit breaker cho agent calls + external services (LLM, Whisper, ChromaDB). 3 states: CLOSED (normal) → OPEN (error rate >50% trong 60s) → HALF_OPEN (retry sau 30s, 1 test request). Khi OPEN: trả về graceful degradation response thay vì timeout/hang. Configurable per service: threshold, timeout, recovery time. Metrics: circuit state transitions, failure rates exported to Prometheus. Fallback examples: Math Agent lỗi → fallback sang default chat với "Tôi đang tạm dừng, thử lại sau"; Whisper API lỗi → suggest manual transcript upload | 2.5h |
| 8 | **Load Testing Suite** | Testing | Locust scripts: 100/500/1000/5000 concurrent users. Measure: RPS, latency, error rate, resource usage. Generate report. Include circuit breaker trigger test | 1.5h |
| 9 | **Performance Budget & CI Gate** | DevOps | Set performance budgets: API p95 <500ms, frontend FCP <1.5s, TTI <3s. GitHub Actions check: fail if budget exceeded | 1.5h |

### Deliverables

- Database index migrations
- Redis cache implementation
- API pagination + compression
- Frontend bundle optimization
- `app/core/circuit_breaker.py` (~180 lines) — NEW: Circuit breaker pattern
- Circuit breaker dashboard (Prometheus metrics + health check integration)
- Load testing suite (Locust) với circuit breaker trigger test
- Performance budget CI gate

### Acceptance Criteria

- ✅ Database: 0 N+1 queries, p95 <500ms
- ✅ Cache hit rate ≥ 70%
- ✅ API: cursor pagination, gzip compression
- ✅ Frontend bundle: <1MB initial, <3MB total
- ✅ WebSocket: 5000 concurrent ổn định
- ✅ Load test: 1000 users, error rate <1%
- ✅ Performance budgets enforced trong CI
- ✅ 🔒 Circuit breaker: OPEN khi error rate >50%/60s, HALF_OPEN retry sau 30s
- ✅ 🔒 Graceful degradation: Agent lỗi → fallback message, không treo app
- ✅ 🔒 Circuit state metrics export ra Prometheus

---

## Tổng kết Stage 5

### Metrics tổng thể

| Metric | Stage 4 End | Stage 5 Target | Delta | % Growth |
|--------|------------|---------------|-------|----------|
| **API Endpoints** | 115 | ~140 | +25 | +22% |
| **Frontend Pages** | 13 | ~18 | +5 | +38% |
| **Tests** | 349 | ~570 | +221 | +63% |
| **Agents** | 4 | 4 (+ orchestrator) | +1 module | +25% |
| **Models** | 18 | ~24 | +6 | +33% |
| **Test Coverage** | ~60% (est.) | ≥80% | +20% | +33% |
| **Lighthouse PWA** | N/A | ≥90 | — | — |
| **Lighthouse Performance** | N/A | ≥90 | — | — |
| **GDPR Compliance** | N/A | ✅ Full | — | — |
| **Self-Healing** | N/A | ✅ Circuit Breaker | — | — |
| **Feedback Loop** | N/A | ✅ Like/Dislike + Entity Reports | — | — |
| **Lines of Code** | ~14,750 | ~23,000 | +8,250 | +56% |

### Sprint Breakdown

| Sprint | Tasks | Priority | Est. Hours | Dependencies |
|--------|-------|----------|-----------|-------------|
| **20**: Media Microlearning | 11 | P1 | ~18.5h | None |
| **21**: Interactive Graph Editing (+ Feedback Loop) | 16 | P0 | ~27.5h | Stage 3 Graph CRUD |
| **22**: Testing & Quality | 15 | P0 | ~22h | Sprint 20, 21 |
| **23**: Production Hardening (+ Privacy & Compliance) | 14 | P0 | ~19h | Sprint 22 |
| **24**: Multi-Agent Orchestration | 10 | P1 | ~16h | Sprint 22, Stage 4 agents |
| **25**: Mobile Polish & PWA | 8 | P1 | ~12h | Sprint 23 (VAPID) |
| **26**: Documentation & Launch | 10 | P0 | ~16h | Sprint 22-25 |
| **27**: Performance & Scalability (+ Circuit Breaker) | 9 | P1 | ~14h | Sprint 22, 23 |
| **TOTAL** | **93** | — | **~145h** | — |

### Đề xuất thứ tự triển khai

```
Phase 1 (Deferred + Foundation): Sprint 20 + Sprint 21 (song song)
Phase 2 (Quality Gateway):        Sprint 22
Phase 3 (Production Ready):       Sprint 23 + Sprint 27 (song song)
Phase 4 (Advanced AI):            Sprint 24
Phase 5 (Mobile & Launch):        Sprint 25 → Sprint 26
```

**Lý do:**

1. **Sprint 20 + 21 song song** — Không dependency lẫn nhau (media processing vs graph editing) → tiết kiệm calendar time.
2. **Sprint 22 sau Phase 1** — Cần code từ Sprint 20, 21 để viết tests đầy đủ.
3. **Sprint 23 + 27 song song** — Production hardening và performance optimization có thể chạy song song vì tập trung vào lớp infrastructure, không conflict code.
4. **Sprint 24 sau Sprint 22** — Multi-agent orchestration cần agents đã được test kỹ.
5. **Sprint 25 sau Sprint 23** — PWA production cần VAPID production setup.
6. **Sprint 26 cuối cùng** — Documentation và launch prep cần tất cả features hoàn thành.

### Resource & Capacity Planning

| Phase | Sprints | Est. Hours | Parallelizable? | Est. Calendar (1 dev) | Est. Calendar (2 devs) |
|-------|---------|-----------|----------------|----------------------|----------------------|
| Phase 1 | 20 + 21 | 46h | ✅ Yes | ~3 tuần | ~1.5 tuần |
| Phase 2 | 22 | 22h | ❌ Sequential | ~1.5 tuần | ~1 tuần |
| Phase 3 | 23 + 27 | 33h | ✅ Yes | ~2.5 tuần | ~1.5 tuần |
| Phase 4 | 24 | 16h | ❌ Sequential | ~1 tuần | ~1 tuần |
| Phase 5 | 25 + 26 | 28h | ❌ Sequential | ~2 tuần | ~1.5 tuần |
| **TOTAL** | 8 sprints | **~145h** | — | **~10 tuần** | **~6.5 tuần** |

---

## Rủi ro & Giảm thiểu

| Rủi ro | Impact | Xác suất | Giảm thiểu | Sprint mitigates |
|--------|--------|---------|-----------|-----------------|
| **Whisper API cost cao** | Cao | Cao | Support `faster-whisper` local, giới hạn 10min/audio cho free tier | Sprint 20 |
| **Mermaid.js render lag (>500 nodes)** | Trung bình | Trung bình | Subgraph clustering, lazy rendering, warning cho large graphs | Sprint 21 |
| **Graph edit conflicts (collaborative)** | Cao | Trung bình | Last-write-wins + vector clock, upgrade CRDT sau nếu cần | Sprint 21 |
| **Test coverage khó đạt 80%** | Trung bình | Trung bình | Prioritize critical paths, mock external services, parallel test writing | Sprint 22 |
| **VAPID push browser compatibility** | Trung bình | Thấp | Test Chrome/Firefox/Safari, fallback graceful | Sprint 23 |
| **Multi-agent orchestration complexity** | Cao | Trung bình | Start với simple routing, chain 2 agents trước, scale sau | Sprint 24 |
| **Bundle size vượt 1.5MB** | Trung bình | Trung bình | Code splitting, lazy load, tree shaking audit mỗi sprint | Sprint 25, 27 |
| **Performance regression sau deployment** | Cao | Thấp | CI performance gate, load test trước deploy, monitoring alerts | Sprint 27 |
| **Documentation lỗi thời** | Thấp | Cao | Auto-generate API docs từ OpenAPI, update docs trong PR checklist | Sprint 26 |
| **Migration downtime khi deploy v1.0** | Cao | Thấp | Backward-compatible migrations, test rollback, blue-green deployment | Sprint 23 |
| **Feedback data bias (chỉ thu thập từ power users)** | Trung bình | Cao | Incentivize feedback qua gamification, statistical weighting | Sprint 21 |
| **GDPR compliance complexity** | Cao | Trung bình | Tư vấn legal review sớm, dùng GDPR-compliant libraries, audit trail | Sprint 23 |
| **Circuit breaker false positives (ngắt nhầm service healthy)** | Cao | Trung bình | Tune threshold conservatively, exponential backoff trong HALF_OPEN, alert khi false positive | Sprint 27 |

---

## Milestone Versions

| Version | Scope | Target |
|---------|-------|--------|
| **v0.5.0** | Sprint 20 + 21 (Media + Graph Editing) | Q1 2027 |
| **v0.6.0** | Sprint 22 + 23 (Testing + Production Hardening) | Q1 2027 |
| **v0.7.0** | Sprint 24 (Multi-Agent Orchestration) | Q2 2027 |
| **v0.8.0** | Sprint 25 + 27 (Mobile Polish + Performance) | Q2 2027 |
| **v1.0.0-rc1** | Sprint 26 (Documentation & Launch Prep) | Q2 2027 |
| **v1.0.0** | **Public Release** | Q2 2027 |

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test coverage | ≥ 80% | `pytest-cov` + `coverage.py` |
| API response time (p95) | < 500ms | Load test (Locust) |
| Frontend bundle (initial) | < 1MB | Webpack bundle analyzer |
| Lighthouse PWA score | ≥ 90 | Lighthouse CI |
| Lighthouse Performance | ≥ 90 | Lighthouse CI |
| WebSocket concurrent connections | 5000 stable | Load test |
| Cache hit rate | ≥ 70% | Prometheus metrics |
| Error rate (production) | < 1% | Sentry dashboard |
| User onboarding completion | ≥ 70% | Analytics (PostHog) |
| Documentation completeness | 100% | Doc checklist |
| 🔒 **GDPR compliance** | 100% | Audit: export + delete + anonymization |
| 🔒 **PII leak prevention** | 0 leaks | Sentry/Prometheus log audit |
| 🔒 **Feedback collection** | ≥ 5% of responses | Analytics tracking |
| 🔒 **Circuit breaker recovery** | < 30s auto-recover | Prometheus circuit state metrics |
| 🔒 **Entity extraction accuracy** | ≥ 85% (từ feedback data) | Entity report analytics |

---

## Known Deferred Items (Post-Stage 5)

| Item | Priority | Est. Effort | Notes |
|------|----------|-------------|-------|
| **CRDT upgrade (Yjs)** | P2 | ~8h | Upgrade từ last-write-wins sang Yjs/Y-webrtc |
| **Community Agent Marketplace** | P2 | ~16h | Public marketplace cho community agents |
| **Advanced analytics (ML-based)** | P3 | ~24h | Predictive learning path, knowledge gap detection |
| **Mobile native apps** | P3 | ~80h | React Native hoặc Flutter apps |
| **Enterprise SSO/SAML** | P3 | ~16h | SSO integration cho enterprise customers |

---

## Change Log

| # | Version | Entry | Reason |
|---|---------|-------|--------|
| 1 | v1.0 | Initial draft | Stage 5 planning based on Stage 4 completion audit |
| 2 | v1.0 | 8 Sprints, 88 tasks, ~137h | Comprehensive scope covering deferred items + v1.0 prep |
| 3 | v1.0 | Sprint 20 (Media) đầu tiên | Deferred từ Stage 4, dependency thấp |
| 4 | v1.0 | Sprint 22 (Testing) P0 | Quality gate trước production hardening |
| 5 | v1.0 | Sprint 23 + 27 song song | Infrastructure layer, không conflict |
| 6 | v1.0 | Sprint 26 cuối cùng | Documentation cần features hoàn thành trước |
| 7 | **v1.1** | **+5 tasks: Feedback Loop (2), Privacy & Compliance (2), Circuit Breaker (1)** | **Quality checkpoints cho commercialization** |
| 8 | **v1.1** | **93 tasks, ~145h, ~10 tuần (1 dev)** | **Updated totals reflect 3 quality checkpoints** |
| 9 | **v1.1** | **+3 risks: Feedback bias, GDPR complexity, Circuit breaker false positives** | **Risk coverage for new quality checkpoints** |
| 10 | **v1.1** | **+5 success criteria: GDPR, PII, feedback, circuit breaker, entity accuracy** | **Measurable quality targets** |

---

© 2026 AetherTutor Team
*Stage 5 Plan — v1.0 DRAFT (2026-04-12)*
*Status: PENDING APPROVAL*
*Next: Review & Approval → Implementation*
