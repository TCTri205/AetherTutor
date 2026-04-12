# Stage 4 Plan: Interactive UX, Collaboration & Ecosystem

> **Date:** 2026-04-12
> **Author:** AetherTutor Team
> **Status:** DRAFT — Pending approval
> **Parent:** [Product Roadmap](./2026-04-07_product_roadmap.md)
> **Previous:** [Stage 3 Final Summary](./reports/2026-04-12_stage3_final_summary.md)
> **Last Revised:** 2026-04-12 (v1.3 — Final polish: Sprint 14 estimate fix, Sprint 15 email fallback, Sprint 18 dependency clar, +2 risks)

---

## Bối cảnh

### Hiện trạng (Post-Stage 3) — Đã xác thực codebase

| Hạng mục | Đã có | Đã kiểm chứng | Ghi chú |
|----------|-------|--------------|---------|
| **Backend** | 87 API endpoints ✅ | `grep @router` → 87 matches | 11 router files: auth, chat, documents, flashcards, graph, notes, quiz, topics, users |
| **Frontend** | 9 pages ✅ | `pages/*.tsx` → 9 files | Dashboard, Vault, Chat, GraphExplorer, GlobalGraphExplorer, Zettelkasten, Flashcards, Quiz |
| **Tests** | 289 tests | `pytest --collect-only` → 289 | +1 so với báo cáo 288 (chấp nhận được) |
| **Agents** | 2 agents ✅ | `examiner_agent.py`, `visualizer_agent.py` | Chưa có base agent framework |
| **Auth** | JWT + sessions ✅ | `auth.py`: register, login, Refresh, Logout, Logout-all | Chưa có email verification, password reset |
| **WebSocket** | ❌ Chưa có | Không tìm thấy file nào | Cần build from scratch |
| **MCP** | Skeleton ✅ | `mcp/skeleton.py`: 3 methods cơ bản | Cần extend cho Specialized Agents |
| **Models** | 13 model files ✅ | base, conversation, document, document_topic, flashcard, graph, note, note_topic, quiz, study_session_group, topic, user, user_session | Chưa có team, shared_resource |
| **TODOs** | 4 trong backend | quiz.py:333, quiz.py:627, graph.py:939, flashcard_generation_service.py:108 | Cần scan thêm frontend TODOs |

### Sprint tồn đọng từ Stage 3 (Deferred)

| Sprint | Status | Sẽ làm ở Stage 4? |
|--------|--------|-------------------|
| Sprint 10: Source Code Visualizer | ⏸️ Deferred | ✅ Yes — P1 |
| Sprint 11: Media Microlearning | ⏸️ Deferred | ✅ Yes — P2 |
| Sprint 12: UI Polish | ⏸️ Deferred | ✅ Yes — P0 (nền tảng cho Sprint 15-17) |

---

## Kiến trúc Stage 4

```
Stage 4: Interactive UX, Collaboration & Ecosystem
├── Sprint 13: Source Code Visualizer (8 tasks)         [P1]
├── Sprint 14: UI Polish & Dark Mode (12 tasks)         [P0]
├── Sprint 15: Real-time Collaboration (15 tasks)       [P0]
├── Sprint 16: Specialized Agents (12 tasks)            [P1]
├── Sprint 17: Media Microlearning (11 tasks)           [P2]
├── Sprint 18: PWA & Mobile (10 tasks)                  [P1]
└── Sprint 19: Security & Observability (12 tasks)      [P0/P1]
```

**Tổng:** 7 Sprints, **80 tasks** (~138h)

---

## Sprint 13: Source Code Visualizer

> **Priority:** P1 | **Dependency:** Stage 3 (Graph CRUD) | **Estimate:** ~17 giờ

Xử lý file source code (Python, JavaScript) → extract entities → hiển thị trên Graph Explorer.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Python AST Parser Service** | Backend | `app/services/code_parser.py` — Parse `.py` files bằng `ast` module, extract: classes, functions, imports, decorators, docstrings | 3h |
| 2 | **JavaScript/TS Parser** | Backend | `app/services/code_parser.py` — Dùng `tree-sitter` + `tree-sitter-javascript` + `tree-sitter-typescript` (pip packages) parse `.js`/`.ts`, extract: functions, classes, exports, imports. **Lưu ý:** Không dùng `esprima` — không có pip package ổn định cho Python | 2h |
| 3 | **Code → Graph Entity Mapper** | Backend | Map AST nodes → GraphEntity: `Class:Foo`, `Function:bar`, `Module:baz`. Relations: `CONTAINS`, `IMPORTS`, `CALLS`, `INHERITS` | 2h |
| 4 | **Extend Document Pipeline** | Backend | `app/worker/tasks.py` — Detect file type (`.py`, `.js`, `.ts`) → route đến code parser thay vì text ingest | 2h |
| 5 | **Code Snippet Storage** | Backend | Thêm cột `code_snippet TEXT` vào `graph_entities` để lưu source code gốc. **Performance guardrail:** Giới hạn 2000 lines/file, reject files >500KB | 1.5h |
| 6 | **Code Block Renderer** | Frontend | `CodeEntityNode.tsx` — Custom ReactFlow node hiển thị code snippet với syntax highlighting (prism.js). **Lazy-load:** Chỉ load code khi user click node | 3.5h |
| 7 | **File Upload for Source Code** | Frontend | Accept `.py`, `.js`, `.ts` trong Upload UI, hiển thị file type badge + size validation | 1h |
| 8 | **Tests** | Testing | 15 unit tests: AST parsing, entity mapping, code renderer, file size limits | 2h |

### Deliverables

- `app/services/code_parser.py` (~250 lines)
- `frontend/src/components/graph/CodeEntityNode.tsx` (~120 lines)
- Migration: `ADD COLUMN code_snippet TEXT`, `ADD COLUMN file_size INT`
- 15 unit tests
- Support: `.py`, `.js`, `.ts` files (max 500KB, 2000 lines)

### Acceptance Criteria

- ✅ Upload `.py` file → Graph hiển thị classes/functions với code snippets
- ✅ Relations `CALLS`, `IMPORTS`, `INHERITS` được tạo tự động
- ✅ Click node code → mở code snippet modal với syntax highlighting (lazy-load)
- ✅ File >500KB hoặc >2000 lines → reject với error message rõ ràng
- ✅ 15/15 tests passing

---

## Sprint 14: UI Polish & Dark Mode

> **Priority:** P0 | **Dependency:** None | **Estimate:** ~22 giờ

Nền tảng UI cho toàn bộ Stage 4 — dark mode, animations, keyboard shortcuts, performance.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Theme Provider** | Frontend | `frontend/src/providers/ThemeProvider.tsx` — `useTheme()` hook, detect system preference, persist to localStorage | 2h |
| 2 | **CSS Variables for Dark Mode** | Frontend | `frontend/src/styles/tokens.css` — Define CSS variables (`--bg-primary`, `--text-primary`, `--accent`, ...) cho cả light/dark | 3h |
| 3 | **Dark Mode Toggle UI** | Frontend | `ThemeToggle.tsx` component trong navbar, icon ☀️/🌙, dropdown để chọn system/light/dark | 1h |
| 4 | **Component Dark Mode** | Frontend | Update tất cả 9 pages + 20+ components dùng CSS variables thay vì hard-coded colors | 4h |
| 5 | **Global Keyboard Shortcuts** | Frontend | `frontend/src/hooks/useKeyboardShortcuts.ts` — Registry pattern, `Ctrl+K` (search), `Ctrl+/` (help), `Ctrl+Z/Y` (graph undo/redo), `Escape` (close modals), `?` (shortcuts modal) | 3h |
| 6 | **Keyboard Shortcuts Modal** | Frontend | `KeyboardShortcutsModal.tsx` — Bảng shortcuts, mở bằng `Ctrl+/` hoặc `?`, framer-motion animation | 1h |
| 7 | **Page Transition Animations** | Frontend | `RootLayout.tsx` — framer-motion `AnimatePresence` cho page transitions (fade + slide), giảm motion cho `prefers-reduced-motion` | 1h |
| 8 | **Graph Performance Optimization** | Backend + Frontend | Virtualize nodes >500, pagination cho global graph, memoization trong ReactFlow | 3h |
| 9 | **Loading Skeletons** | Frontend | Skeleton screens thay vì spinner cho Dashboard, Vault, Chat, Flashcards | 1h |
| 10 | **Toast Notification Polish** | Frontend | Sonner toast consistency: success (3s), error (5s + dismiss), warning (4s), info (3s) | 0.5h |
| 11 | **Accessibility Audit** | Frontend | ARIA labels đầy đủ, focus management, keyboard navigation, color contrast (WCAG AA) | 1h |
| 12 | **Tests** | Testing | 10 tests: theme persistence, keyboard shortcuts, reduced motion | 1.5h |

### Deliverables

- `frontend/src/providers/ThemeProvider.tsx` (~80 lines)
- `frontend/src/styles/tokens.css` (~150 lines)
- `frontend/src/components/shared/ThemeToggle.tsx` (~60 lines)
- `frontend/src/hooks/useKeyboardShortcuts.ts` (~120 lines)
- `frontend/src/components/shared/KeyboardShortcutsModal.tsx` (~100 lines)
- Dark mode cho 9 pages + 20+ components
- 10 unit tests

### Acceptance Criteria

- ✅ Toggle dark mode → toàn bộ UI đổi theme mượt mà
- ✅ Detect system preference tự động (Windows/macOS dark mode)
- ✅ `Ctrl+K` mở search, `Ctrl+/` mở shortcuts help, `Ctrl+Z` undo trên graph
- ✅ Graph render ổn với 500+ nodes (60fps)
- ✅ 10/10 tests passing
- ✅ Lighthouse accessibility score ≥ 90

---

## Sprint 15: Real-time Collaboration

> **Priority:** P0 | **Dependency:** Sprint 14 (Phase 1 ✅), Sprint 19 email service (Phase 1 ✅), Stage 3 (Graph CRUD) | **Estimate:** ~28 giờ | **Tasks:** 15

WebSocket-based collaboration: shared graphs, real-time co-editing, presence indicators.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **WebSocket Infrastructure** | Backend | `app/api/websocket.py` — FastAPI WebSocket manager, connection pool, heartbeat/ping-pong, auth via JWT query param | 3h |
| 2 | **Team/Organization Model** | Backend | `app/models/team.py` — Team(id, name, owner_id, created_at), TeamMember(user_id, team_id, role: admin\|editor\|viewer) | 2h |
| 3 | **Shared Resource Model** | Backend | `app/models/shared_resource.py` — SharedResource(team_id, resource_type, resource_id, permissions) | 1h |
| 4 | **Collaboration API Endpoints** | Backend | `app/api/collaboration.py` — POST `/teams`, GET `/teams`, POST `/teams/{id}/invite`, POST `/teams/{id}/share`, GET `/teams/{id}/members` | 3h |
| 5 | **WebSocket Rooms & Events** | Backend | Room per shared resource: `graph:{graph_id}`, `chat:{conv_id}`. Events: `node_created`, `node_updated`, `node_deleted`, `cursor_move`, `presence_join`, `presence_leave` | 3h |
| 6 | **Conflict Resolution (CRDT)** | Backend | Dùng Yjs protocol hoặc operational transformation cho concurrent edits. Simplest: last-write-wins với vector clock | 3h |
| 7 | **Presence Indicator** | Frontend | `PresenceIndicator.tsx` — Hiển thị avatars của users đang online, cursor positions trên graph | 2h |
| 8 | **Real-time Graph Sync** | Frontend | `useGraphWebSocket.ts` hook — Nhận events từ WS, optimistic update, conflict resolution UI | 4h |
| 9 | **Team Management UI** | Frontend | `TeamSettings.tsx` page — Invite members, manage roles, shared resources list | 2h |
| 10 | **Shared Graph Badge** | Frontend | Hiển thị icon 👥 trên shared graphs trong GraphExplorer | 0.5h |
| 11 | **Invitation Email Flow** | Backend | Gửi email invitation (dùng email service từ Sprint 19). **Fallback:** Nếu Sprint 19 chưa xong → dùng placeholder/mock email service (log invitation link thay vì gửi thật), replace sau khi Sprint 19 hoàn thành | 1h |
| 12 | **Shared Graph Permissions UI** | Frontend | `SharedGraphModal.tsx` — Share button trong GraphExplorer, permission selector (view/edit/admin), "Shared with me" section | 1.5h |
| 13 | **WebSocket E2E Tests** | Testing | 15 integration tests: connection auth, room join/leave, event broadcast, conflict resolution | 1h |
| 14 | **WebSocket Load Tests** | Testing | 5 load tests: 100/500/1000 concurrent connections, message throughput, memory leak detection | 2h |
| 15 | **E2E Collaboration Tests** | Testing | 5 E2E tests: 2-user co-editing flow, invite-accept-access, concurrent edit conflict, leave team, shared graph visibility | 2h |

### Deliverables

- `app/api/websocket.py` (~250 lines)
- `app/models/team.py` (~80 lines)
- `app/models/shared_resource.py` (~60 lines)
- `app/api/collaboration.py` (~200 lines)
- `frontend/src/hooks/useGraphWebSocket.ts` (~150 lines)
- `frontend/src/components/shared/PresenceIndicator.tsx` (~80 lines)
- `frontend/src/components/shared/SharedGraphModal.tsx` (~100 lines)
- Migration: teams, team_members, shared_resources tables
- 25 tests (15 integration + 5 load + 5 E2E)

### Acceptance Criteria

- ✅ 2 users cùng mở shared graph → thấy cursor của nhau real-time
- ✅ User A tạo node → User B thấy node mới xuất hiện trong <500ms
- ✅ Concurrent edit → last-write-wins với notification
- ✅ Team owner mời member qua email → member accept → access shared graphs
- ✅ "Shared with me" section trong GraphExplorer hiển thị graphs được share
- ✅ Share modal: chọn user, set role (view/edit/admin), revoke access
- ✅ 25/25 tests passing (integration + load + E2E)

---

## Sprint 16: Specialized Agents

> **Priority:** P1 | **Dependency:** Sprint 14 (theme consistency), Stage 3 (VisualizerAgent pattern) | **Estimate:** ~22 giờ

Base Agent framework + 2 specialized agents: Language Agent, Math Agent. MCP integration for cross-agent communication.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Base Agent Class** | Backend | `app/core/agents/base_agent.py` — Abstract `Agent` class với `__init__`, `process()`, `get_system_prompt()`, `get_tools()`, `get_capabilities()`. Plugin architecture qua registry | 3h |
| 2 | **Agent Registry** | Backend | `app/core/agents/registry.py` — Register/unload agents, dynamic discovery, version compatibility check | 1h |
| 3 | **Agent Config Schema** | Backend | `app/schemas/agent.py` — AgentConfig(id, name, description, icon, system_prompt_template, tools[], capabilities[]) | 1h |
| 4 | **MCP Extension for Agents** | Backend | Extend `app/mcp/skeleton.py` → `AgentContext` class. Agents dùng MCP để share context: user progress, graph entities, session state. Standardize context format cho inter-agent communication | 2h |
| 5 | **Language Agent** | Backend | `app/core/agents/language_agent.py` — Specialized cho học ngôn ngữ: vocabulary extraction, grammar patterns, conjugation tables, translation exercises. Prompt: language learning focused | 3h |
| 6 | **Language Agent — Frontend** | Frontend | `LanguageChat.tsx` — Chat UI với vocab cards, grammar highlights, conjugation tables | 3h |
| 7 | **Math Agent** | Backend | `app/core/agents/math_agent.py` — Specialized cho toán: LaTeX rendering, step-by-step solutions, formula extraction từ documents, symbolic computation hints. Prompt: math tutor with Socratic method | 3h |
| 8 | **Math Agent — Frontend** | Frontend | `MathChat.tsx` — Chat UI với KaTeX rendering, equation editor, step-by-step reveal | 3h |
| 9 | **Agent Selector UI** | Frontend | `AgentSelector.tsx` — Dropdown/modal chọn agent khi tạo conversation mới, hiển thị icon + description | 2h |
| 10 | **Agent Management API** | Backend | `app/api/agents.py` — GET `/agents` (list available), GET `/agents/{id}` (detail), POST `/agents` (register custom) | 1h |
| 11 | **Tests** | Testing | 15 tests: base agent, registry, language agent, math agent, agent selector, MCP context | 2h |
| 12 | **Agent Marketplace Infrastructure** *(v1.0.0 prep)* | Backend | `app/schemas/agent_marketplace.py` — AgentTemplate schema (export/import agent config JSON). API: GET `/agents/templates` (list community templates). **Note:** Community sharing feature để sau, hiện tại chỉ export/import local | 2h |

### Deliverables

- `app/core/agents/base_agent.py` (~100 lines)
- `app/core/agents/registry.py` (~80 lines)
- `app/core/agents/language_agent.py` (~200 lines)
- `app/core/agents/math_agent.py` (~200 lines)
- `app/mcp/skeleton.py` (updated: +AgentContext, ~60 lines)
- `app/api/agents.py` (~100 lines)
- `app/schemas/agent_marketplace.py` (~50 lines)
- `frontend/src/pages/LanguageChat.tsx` (~150 lines)
- `frontend/src/pages/MathChat.tsx` (~150 lines)
- `frontend/src/components/shared/AgentSelector.tsx` (~100 lines)
- 17 unit tests

### Acceptance Criteria

- ✅ Register agent → xuất hiện trong Agent Selector UI
- ✅ Language Agent: upload văn bản tiếng Anh → extract vocabulary list, tạo exercises
- ✅ Math Agent: upload tài liệu toán → hiển thị công thức LaTeX, giải step-by-step
- ✅ Switch agent trong chat → system prompt thay đổi đúng
- ✅ Agents giao tiếp qua MCP: Language Agent có thể access graph entities từ session
- ✅ Export agent config → import lại được (Agent Template)
- ✅ 17/17 tests passing

---

## Sprint 17: Media Microlearning

> **Priority:** P2 | **Dependency:** None (optional) | **Estimate:** ~18.5 giờ | **Tasks:** 11

Xử lý video/audio → transcript → knowledge graph.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **YouTube Transcript Service** | Backend | `app/services/youtube_service.py` — `youtube-transcript-api` pip package, fetch transcript bằng video URL hoặc ID | 2h |
| 2 | **Audio Upload & Storage** | Backend | Accept `.mp3`, `.wav`, `.m4a` trong upload pipeline, lưu vào `uploads/audio/` | 1h |
| 3 | **Whisper Transcription** | Backend | `app/services/transcription_service.py` — OpenAI Whisper API hoặc local `faster-whisper` (CPU mode). Chunk transcript theo timestamps. **BR-008 Compliance:** Nếu `local_mode=True` + `whisper_cpp=False` → từ chối, yêu cầu user dán transcript thủ công hoặc chuyển Cloud Mode | 3h |
| 4 | **Transcript → Text Pipeline** | Backend | Reuse existing text ingestion: transcript chunks → entity extraction → graph building | 2h |
| 5 | **Video Player Component** | Frontend | `VideoPlayer.tsx` — Embed YouTube player hoặc HTML5 audio, sync transcript highlight với playback time | 4h |
| 6 | **Transcript Viewer** | Frontend | `TranscriptViewer.tsx` — Hiển thị transcript với timestamps, click timestamp → seek audio/video | 2h |
| 7 | **Media Document Type** | Backend | Thêm `media_type` enum (video/audio/text) vào `documents` table, `source_url` cho YouTube | 1h |
| 8 | **Audio Player with Sync** | Frontend | `AudioPlayer.tsx` — Waveform visualization (wavesurfer.js), sync với transcript | 2h |
| 9 | **Tests** | Testing | 10 tests: YouTube fetch, transcript parsing, audio upload, BR-008 compliance | 1h |
| 10 | **Worker Registration** | Backend | Đăng ký `process_youtube_task` và `process_audio_transcription_task` vào `WorkerSettings.functions` trong `app/worker/tasks.py` | 0.5h |

### Deliverables

- `app/services/youtube_service.py` (~150 lines)
- `app/services/transcription_service.py` (~200 lines)
- `frontend/src/components/media/VideoPlayer.tsx` (~150 lines)
- `frontend/src/components/media/AudioPlayer.tsx` (~180 lines)
- `frontend/src/components/media/TranscriptViewer.tsx` (~120 lines)
- Migration: `media_type` enum, `source_url` column
- 11 unit tests (bao gồm BR-008 compliance test)
- Worker tasks registered trong WorkerSettings

### Acceptance Criteria

- ✅ Paste YouTube URL → fetch transcript → build graph tự động
- ✅ Upload `.mp3` → transcribe → extract entities → hiển thị transcript sync với audio
- ✅ Click transcript line → audio seek tới timestamp tương ứng
- ✅ Local mode (BR-008): Nếu `local_mode=True` + `whisper_cpp=False` → reject với error message rõ ràng
- ✅ 11/11 tests passing

---

## Sprint 18: PWA & Mobile

> **Priority:** P1 | **Dependency:** Sprint 14 (UI Polish), Sprint 19 Phase 1 (VAPID keys setup — Task 7) | **Estimate:** ~15 giờ

Biến React SPA thành Progressive Web App — installable, offline-capable, push notifications.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Vite PWA Plugin** | Frontend | `npm install vite-plugin-pwa workbox-window` — Config trong `vite.config.ts` | 1h |
| 2 | **manifest.json** | Frontend | `public/manifest.json` — name, short_name, icons, theme_color, background_color, start_url, display: standalone | 1h |
| 3 | **Service Worker** | Frontend | PWA plugin tự generate SW. Config: cache-first cho assets, network-first cho API, stale-while-revalidate cho data | 2h |
| 4 | **App Icons** | Frontend | Generate icons 192x192, 512x512 từ logo (dùng placeholder SVG nếu chưa có design) | 1h |
| 5 | **Offline Page** | Frontend | `OfflinePage.tsx` — Hiển thị khi không có mạng, list cached documents, retry button | 2h |
| 6 | **Offline Cache Strategy** | Frontend | Cache flashcards, notes, last chat conversation cho offline viewing | 2h |
| 7 | **Extend Notification Service (VAPID)** | Backend | **EXTEND** `app/services/notification_service.py` (đã tồn tại, 182 lines) — Thêm VAPID keys config, Web Push subscription endpoints (`POST/GET /push/subscription`), background push worker. **KHÔNG tạo file mới** — extend file cũ với methods mới: `subscribe_push()`, `unsubscribe_push()`, `send_push()` | 2h |
| 8 | **Push Notifications — Frontend** | Frontend | `usePushNotifications.ts` hook — Request permission, subscribe, handle push events, badge count | 2h |
| 9 | **Install Prompt** | Frontend | `InstallPrompt.tsx` — Detect `beforeinstallprompt`, show banner "Install AetherTutor", handle user choice | 1h |
| 10 | **Tests** | Testing | 8 tests: manifest validity, SW registration, offline fallback, push subscription | 1h |

### Deliverables

- `frontend/vite.config.ts` (updated with PWA plugin)
- `public/manifest.json` (~30 lines)
- `frontend/src/pages/OfflinePage.tsx` (~80 lines)
- `frontend/src/hooks/usePushNotifications.ts` (~120 lines)
- `frontend/src/components/shared/InstallPrompt.tsx` (~60 lines)
- `app/services/notification_service.py` (extended: +~80 lines VAPID methods)
- 8 unit tests

### Acceptance Criteria

- ✅ Lighthouse PWA score ≥ 90
- ✅ Install banner xuất hiện trên Chrome mobile/desktop
- ✅ Offline mode: vẫn xem được flashcards, notes đã cache
- ✅ Push notification: review reminder, due flashcards alert
- ✅ 8/8 tests passing

---

## Sprint 19: Security, Observability & Migration Strategy

> **Priority:** P0 (Security fixes) / P1 (Observability) | **Dependency:** None (parallel được) | **Estimate:** ~15 giờ

Fix TODOs, security gaps, monitoring, error tracking, migration strategy.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Email Verification Flow** | Backend | Generate verification token, send email, verify endpoint, resend logic | 2h |
| 2 | **Password Reset** | Backend | POST `/auth/forgot-password` (send reset link), POST `/auth/reset-password` (validate token + update) | 2h |
| 3 | **Document Ownership Validation** | Backend | Fix TODO `graph.py:939`: validate user owns document before entity CRUD. Audit ALL graph/document endpoints for ownership checks | 1.5h |
| 4 | **Quiz Bloom Level Persistence** | Backend | Fix TODO `quiz.py:333`: store `bloom_level` trong quiz answer model thay vì hardcode "remember" | 0.5h |
| 5 | **Quiz Entity Type Enrichment** | Backend | Fix TODO `quiz.py:627`: fetch entity type từ graph cho weak areas endpoint | 0.5h |
| 6 | **Sentry Integration** | Backend + Frontend | Backend: `sentry-sdk` FastAPI integration. Frontend: `@sentry/react` + `@sentry/tracing`. Error boundary gửi Sentry. Fix TODO `ErrorBoundary.tsx:38` | 2h |
| 7 | **Flashcard Quiz Wrong Answers** | Backend | Fix TODO `flashcard_generation_service.py:108`: implement `generate_from_quiz_wrong_answers()` — quiz sai → auto tạo flashcard | 1h |
| 8 | **Context Chips → Graph Navigation** | Frontend | Fix TODO `ContextChips.tsx:24`: click entity chip → navigate Graph page với entity selected/highlighted | 1h |
| 9 | **Rate Limiting Audit** | Backend | Review rate limits trên tất cả endpoints, log violations, add exponential backoff | 1h |
| 10 | **Database Migration Strategy** | DevOps | Backward-compatible migrations cho Stage 4 schema changes (teams, shared_resources, media_type, code_snippet). Test zero-downtime migration trên staging. Blueprint: chạy migration → deploy code → verify | 2h |
| 11 | **Frontend TODOs Audit** | Frontend | Scan toàn bộ `frontend/src/` cho TODO comments, fix hoặc create tickets cho Stage 5 | 1h |
| 12 | **Tests** | Testing | 12 tests: email verification, password reset, ownership validation, Sentry capture, migration rollback | 1.5h |

### Deliverables

- `app/api/auth.py` (updated: forgot/reset password endpoints)
- `app/services/notification_service.py` (extended: +~60 lines email verification + password reset methods)
- Sentry integration (backend + frontend config)
- Fix 5 TODOs trong codebase (4 backend + 1 frontend — ContextChips đã fix)
- Migration strategy doc: `docs/ops/migration_strategy.md`
- 12 unit + integration tests

### Acceptance Criteria

- ✅ Register → nhận email verification → click link → verified
- ✅ Forgot password → nhận email reset link → đặt password mới
- ✅ Entity CRUD chỉ thành công nếu user sở hữu document (tất cả endpoints được audit)
- ✅ Quiz wrong answers → auto-generate flashcards hoạt động
- ✅ Click context chip → Graph page highlight entity tương ứng
- ✅ Errors được gửi đến Sentry
- ✅ Migration test: rollback được, zero-downtime trên staging
- ✅ Frontend TODO audit: danh sách TODOs được document hóa
- ✅ 12/12 tests passing

---

## Tổng kết Stage 4

### Metrics tổng thể (Đã xác thực codebase)

| Metric | Stage 3 End (Verified) | Stage 4 Target | Delta |
|--------|----------------------|---------------|-------|
| **API Endpoints** | 87 (grep confirmed) | ~110 | +23 |
| **Frontend Pages** | 9 (files confirmed) | ~15 | +6 |
| **Tests** | 289 (pytest confirmed) | ~400 | +111 |
| **Agents** | 2 (Examiner, Visualizer) | 4 (+ Language, Math) | +2 |
| **Models** | 13 files | 16 (+ team, shared_resource, agent_config) | +3 |
| **Lines of Code** | ~2,200 (Stage 3) | ~5,000 (est.) | +2,800 |
| **Test Pass Rate** | 100% | 100% | Maintain |
| **Test Types** | Unit + Integration | Unit + Integration + E2E + Load + Lighthouse CI | +3 types |

### Sprint Breakdown (Revised)

| Sprint | Tasks | Priority | Est. Hours | Dependencies |
|--------|-------|----------|-----------|-------------|
| **13**: Source Code Visualizer | 8 | P1 | ~17h | Stage 3 Graph CRUD |
| **14**: UI Polish & Dark Mode | 12 | P0 | ~22h | None |
| **15**: Real-time Collaboration | 15 | P0 | ~28h | Sprint 14 (Phase 1 ✅), Sprint 19 (Phase 1 ✅), Stage 3 |
| **16**: Specialized Agents | 12 | P1 | ~22h | Sprint 14 (theme), Stage 3 VisualizerAgent |
| **17**: Media Microlearning | 11 | P2 | ~18.5h | None |
| **18**: PWA & Mobile | 10 | P1 | ~15h | Sprint 14, Sprint 19 (push notifications) |
| **19**: Security & Observability | 12 | P0/P1 | ~15h | None |
| **TOTAL** | **80** | — | **~138h** | — |

### Đề xuất thứ tự triển khai (Revised — v1.3)

```
Phase 1 (Critical Foundation): Sprint 14 + Sprint 19 (song song)
Phase 2 (Core Features):        Sprint 13 + Sprint 16 (song song)
Phase 3 (Advanced):             Sprint 15 → Sprint 18 → Sprint 17 (optional)
```

**Lý do điều chỉnh:**

1. **Sprint 19 nâng lên P0** vì chứa security fixes critical (ownership validation, password reset, email verification). Các bugs này nếu không fix sẽ tạo security debt nghiêm trọng khi mở collaboration (Sprint 15).
2. **Phase 1 chạy song song Sprint 14 + 19** vì không có dependency lẫn nhau → tiết kiệm ~5h calendar time.
3. **Sprint 15 dependency mở rộng**: Cần Sprint 19 (email service) cho invitation flow — không thể gửi invite nếu chưa có email service.
4. **Sprint 18 dependency mở rộng**: Cần Sprint 19 (push notification backend) cho VAPID keys setup.
5. **Sprint 17 (Media) vẫn optional** — có thể skip nếu resource hạn chế, không blocking các features khác.

### Resource & Capacity Planning

| Phase | Sprints | Est. Hours | Parallelizable? | Est. Calendar (1 dev) | Est. Calendar (2 devs) |
|-------|---------|-----------|----------------|----------------------|----------------------|
| Phase 1 | 14 + 19 | 37h | ✅ Yes | ~2 tuần | ~1 tuần |
| Phase 2 | 13 + 16 | 39h | ✅ Yes | ~2 tuần | ~1.5 tuần |
| Phase 3 | 15 + 18 + 17 | 61.5h | ❌ Sequential | ~3.5 tuần | ~2.5 tuần |
| **TOTAL** | 7 sprints | **~138h** | — | **~7.5 tuần** | **~5 tuần** |

> **Note:** Ước tính cho 1 full-time developer. Nếu có 2 developers (1 backend + 1 frontend), Phase 1 và Phase 2 có thể chạy song song hoàn toàn → giảm xuống ~5 tuần.

### Rủi ro & Giảm thiểu (Revised)

| Rủi ro | Impact | Xác suất | Giảm thiểu | Sprint mitigates |
|--------|--------|---------|-----------|-----------------|
| WebSocket scaling (1000+ concurrent) | Cao | Trung bình | Dùng Redis pub/sub, connection pooling, load testing (5 tests) | Sprint 15 |
| CRDT conflict complexity | Cao | Cao | Start với last-write-wins, upgrade CRDT sau | Sprint 15 |
| PWA Safari compatibility | Trung bình | Trung bình | Test iOS Safari sớm, fallback graceful | Sprint 18 |
| Whisper API cost | Trung bình | Cao | Support local `faster-whisper` làm fallback | Sprint 17 |
| Sentry rate limit (free tier) | Thấp | Thấp | Sample errors, chỉ gửi 1000 events/ngày | Sprint 19 |
| **Security: User data leak via missing ownership** | 🔴 CRITICAL | Thấp (nếu fix Sprint 19 trước) | Fix ownership validation trong Sprint 19 trước khi mở Collaboration | Sprint 19 |
| **Migration downtime** | Cao | Trung bình | Backward-compatible migrations, test zero-downtime trên staging | Sprint 19 |
| **Code parser lag (>2000 lines)** | Trung bình | Cao | Reject files >500KB, lazy-load code snippets, giới hạn 2000 lines | Sprint 13 |
| **Frontend bundle size bloat** (15+ components mới) | Trung bình | Trung bình | Code splitting per page, lazy-load ReactFlow nodes, audit bundle size mỗi Sprint, target <1.5MB | Sprint 14 + 16 + 18 |
| **Migration rollback time** (8 tables mới) | Cao | Trung bình | Test rollback trên staging trước, backup DB trước migration, estimate rollback <5 phút | Sprint 19 Task 10 |

---

## Phụ lục: TODOs cần fix (Đã xác thực codebase — 2026-04-12)

### Backend TODOs (4 confirmed)

| # | File | Line | TODO | Sprint fix | Severity |
|---|------|------|------|-----------|----------|
| 1 | `app/services/flashcard_generation_service.py` | 108 | Implement `generate_from_quiz_wrong_answers()` | Sprint 19 | Medium |
| 2 | `app/api/quiz.py` | 333 | Store bloom_level in answer model | Sprint 19 | Low |
| 3 | `app/api/quiz.py` | 627 | Fetch entity_type from graph | Sprint 19 | Low |
| 4 | `app/api/graph.py` | 939 | Validate user owns document_id | Sprint 19 | 🔴 Critical |

### Frontend TODOs (Audit result — 2026-04-12)

| # | File | Line | TODO | Sprint fix | Severity | Status |
|---|------|------|------|-----------|----------|--------|
| 5 | `frontend/src/components/shared/ErrorBoundary.tsx` | 38 | Send to Sentry | Sprint 19 | Medium | ⏳ Pending |
| 6 | `frontend/src/components/shared/ContextChips.tsx` | 24 | Pass entity name to Graph page | Sprint 19 | Medium | ✅ **ĐÃ FIX** — Đã implement navigate với highlightEntity state |

> **Note:** ContextChips.tsx đã được implement đầy đủ (navigate với highlightEntity state). Chỉ còn 1 frontend TODO cần fix (ErrorBoundary → Sentry). Danh sách đầy đủ sẽ được cập nhật sau Sprint 19 Task 11 (Frontend TODO Audit).

---

## Milestone Versions (Revised)

| Version | Scope | Target | Delta from original |
|---------|-------|--------|-------------------|
| **v0.3.1** | Sprint 13 + 14 (Source Code + UI Polish) | Q4 2026 | +2 tasks (performance guardrails, lazy-load) |
| **v0.3.2** | Sprint 15 + 16 (Collaboration + Agents) | Q4 2026 | +7 tasks (shared graph UI, E2E tests, MCP, Agent Template) |
| **v0.4.0** | Sprint 17 + 18 (Media + PWA) | Q1 2027 | +2 tests (Lighthouse CI, load tests) |
| **v0.5.0** | Sprint 19 + Polish (Security + Observability) | Q1 2027 | +4 tasks (migration strategy, frontend audit, 2 extra tests) |
| **v1.0.0** | Stage 4 Complete — Public Release | Q1 2027 | ~400 tests, ~110 endpoints, 4 agents, PWA, Collaboration |

---

## Change Log (v1.0 → v1.3)

| # | Change | Reason | Source |
|---|--------|--------|--------|
| 1 | Sprint 19 nâng lên P0 | Security fixes critical (ownership, password reset) | Peer review |
| 2 | Phase ordering revised | Sprint 19 phải hoàn thành trước Sprint 15 để tránh security debt | Dependency analysis |
| 3 | Sprint 15: +3 tasks (Shared Graph UI, E2E tests, Load tests) | Roadmap yêu cầu "Shared knowledge graphs", thiếu E2E/load testing | Roadmap alignment + testing gap |
| 4 | Sprint 16: +2 tasks (MCP Extension, Agent Template) | Roadmap nhắc MCP, cần prep cho Agent Marketplace v1.0.0 | MCP integration + future-proofing |
| 5 | Sprint 13: +Performance guardrails (500KB/2000 lines limit, lazy-load) | Risk: large files gây lag parser | Technical feasibility |
| 6 | Sprint 19: +Migration strategy, Frontend TODO audit | Risk: downtime khi deploy, TODOs chưa được scan đầy đủ | Migration strategy + codebase audit |
| 7 | Metrics updated | Actual codebase: 87 endpoints, 289 tests, 9 pages, 13 models, 2 agents | Codebase verification |
| 8 | Resource planning table added | Capacity planning transparency | Peer review |
| 9 | Risk table: +3 risks (security leak, migration downtime, code parser lag) | New risks identified | Technical analysis |
| 10 | **🔴 C1 Fix:** Sprint 13 Task 2 — esprima → tree-sitter | esprima không có pip package ổn định cho Python | Peer review C1 |
| 11 | **🔴 C2 Fix:** Sprint 17 Task 3 — thêm BR-008 Local Mode compliance | Stage 3 plan yêu cầu rule này, bị bỏ sót | Peer review C2 |
| 12 | **🟡 H1 Fix:** Architecture block updated — 74 → 80 tasks, task counts chính xác | Task count mâu thuẫn giữa header và bảng | Peer review H1 |
| 13 | **🟡 H2 Fix:** Sprint 18 Task 7 — EXTEND notification_service.py thay vì create mới | File đã tồn tại (182 lines), tránh overwrite | Peer review H2 |
| 14 | **🟡 H3 Fix:** Sprint 15 dependency clarified — "Phase 1 ✅" cho Sprint 14 + 19 | Dependency loop không rõ | Peer review H3 |
| 15 | **🟢 M2 Fix:** Sprint 14 Task 12 estimate 0.5h → 1.5h | 10 tests async không thể viết trong 0.5h | Peer review M2 |
| 16 | **🟢 M3 Fix:** Sprint 17 +Task 10 WorkerSettings registration | Thiếu sub-task đăng ký process_youtube_task | Peer review M3 |
| 17 | **🟢 M5 Fix:** Frontend TODOs — ContextChips.tsx:24 đánh dấu ĐÃ FIX | Đã implement navigate với highlightEntity state | Codebase audit |
| 18 | **🟢 v1.3 Fix:** Sprint 14 total ~21h → ~22h | Cộng 12 tasks = 22.5h, làm tròn chính xác | Internal audit |
| 19 | **🟢 v1.3 Fix:** Sprint 15 Task 11 — thêm email fallback placeholder | Sprint 19 có thể chưa xong khi Sprint 15 chạy | Dependency resolution |
| 20 | **🟢 v1.3 Fix:** Sprint 18 dependency — thêm Sprint 19 Phase 1 (VAPID) | Push notifications cần VAPID keys từ Sprint 19 | Dependency clarification |
| 21 | **🟢 v1.3 Fix:** +2 risks — Frontend bundle size + Migration rollback time | Thiếu 2 risks quan trọng cho Stage 4 | Risk completeness |
| 22 | **🟢 v1.3 Fix:** Totals updated — 80 tasks, ~138h, Phase 1 37h | Reflect Sprint 14 estimate fix | Consistency |

---

© 2026 AetherTutor Team
*Stage 4 Plan — Revised v1.3 FINAL (2026-04-12)*
*Reviewed by: Codebase audit + Peer review integration + Final polish*
*Status: READY FOR APPROVAL*
