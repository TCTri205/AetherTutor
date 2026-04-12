# Stage 4 Plan: Interactive UX, Collaboration & Ecosystem

> **Date:** 2026-04-12
> **Author:** AetherTutor Team
> **Status:** DRAFT — Pending approval
> **Parent:** [Product Roadmap](./2026-04-07_product_roadmap.md)
> **Previous:** [Stage 3 Final Summary](./reports/2026-04-12_stage3_final_summary.md)

---

## Bối cảnh

### Hiện trạng (Post-Stage 3)

| Hạng mục | Đã có | Thiếu |
|----------|-------|-------|
| **Backend** | 87 API endpoints, Auth (JWT + sessions), 6 services | WebSocket, collaboration, specialized agents |
| **Frontend** | 9 pages, framer-motion, ReactFlow, Zustand | Dark mode, PWA, offline, keyboard shortcuts |
| **Tests** | 288 tests passing (100%) | Coverage còn thiếu WebSocket flows, PWA |
| **Agents** | ExaminerAgent, VisualizerAgent | Language Agent, Math Agent, base agent framework |
| **Auth** | Register/Login/Refresh/Logout, multi-device | Email verification, password reset, OAuth, 2FA |
| **Infrastructure** | PostgreSQL, Redis, ChromaDB, ARQ worker | Monitoring (Prometheus/Grafana), error tracking (Sentry) |

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
├── Sprint 13: Source Code Visualizer (8 tasks)        [P1]
├── Sprint 14: UI Polish & Dark Mode (12 tasks)        [P0]
├── Sprint 15: Real-time Collaboration (14 tasks)      [P0]
├── Sprint 16: Specialized Agents (12 tasks)           [P1]
├── Sprint 17: Media Microlearning (10 tasks)          [P2]
├── Sprint 18: PWA & Mobile (10 tasks)                 [P1]
└── Sprint 19: Security & Observability (8 tasks)      [P1]
```

**Tổng:** 7 Sprints, 74 tasks

---

## Sprint 13: Source Code Visualizer

> **Priority:** P1 | **Dependency:** Stage 3 (Graph CRUD) | **Estimate:** ~15 giờ

Xử lý file source code (Python, JavaScript) → extract entities → hiển thị trên Graph Explorer.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Python AST Parser Service** | Backend | `app/services/code_parser.py` — Parse `.py` files bằng `ast` module, extract: classes, functions, imports, decorators, docstrings | 3h |
| 2 | **JavaScript/TS Parser** | Backend | `app/services/code_parser.py` — Dùng `esprima` (pip) parse `.js`/`.ts`, extract: functions, classes, exports, imports | 2h |
| 3 | **Code → Graph Entity Mapper** | Backend | Map AST nodes → GraphEntity: `Class:Foo`, `Function:bar`, `Module:baz`. Relations: `CONTAINS`, `IMPORTS`, `CALLS`, `INHERITS` | 2h |
| 4 | **Extend Document Pipeline** | Backend | `app/worker/tasks.py` — Detect file type (`.py`, `.js`, `.ts`) → route đến code parser thay vì text ingest | 2h |
| 5 | **Code Snippet Storage** | Backend | Thêm cột `code_snippet TEXT` vào `graph_entities` để lưu source code gốc | 1h |
| 6 | **Code Block Renderer** | Frontend | `CodeEntityNode.tsx` — Custom ReactFlow node hiển thị code snippet với syntax highlighting (prism.js) | 3h |
| 7 | **File Upload for Source Code** | Frontend | Accept `.py`, `.js`, `.ts` trong Upload UI, hiển thị file type badge | 1h |
| 8 | **Tests** | Testing | 15 unit tests: AST parsing, entity mapping, code renderer | 1h |

### Deliverables

- `app/services/code_parser.py` (~250 lines)
- `frontend/src/components/graph/CodeEntityNode.tsx` (~120 lines)
- Migration: `ADD COLUMN code_snippet TEXT`
- 15 unit tests
- Support: `.py`, `.js`, `.ts` files

### Acceptance Criteria

- ✅ Upload `.py` file → Graph hiển thị classes/functions với code snippets
- ✅ Relations `CALLS`, `IMPORTS`, `INHERITS` được tạo tự động
- ✅ Click node code → mở code snippet modal với syntax highlighting
- ✅ 15/15 tests passing

---

## Sprint 14: UI Polish & Dark Mode

> **Priority:** P0 | **Dependency:** None | **Estimate:** ~20 giờ

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
| 12 | **Tests** | Testing | 10 tests: theme persistence, keyboard shortcuts, reduced motion | 0.5h |

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

> **Priority:** P0 | **Dependency:** Sprint 14 (theme), Stage 3 (Graph CRUD) | **Estimate:** ~25 giờ

WebSocket-based collaboration: shared graphs, real-time co-editing, presence indicators.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **WebSocket Infrastructure** | Backend | `app/api/websocket.py` — FastAPI WebSocket manager, connection pool, heartbeat/ping-pong, auth via JWT query param | 3h |
| 2 | **Team/Organization Model** | Backend | `app/models/team.py` — Team(id, name, owner_id, created_at), TeamMember(user_id, team_id, role: admin|editor|viewer) | 2h |
| 3 | **Shared Resource Model** | Backend | `app/models/shared_resource.py` — SharedResource(team_id, resource_type, resource_id, permissions) | 1h |
| 4 | **Collaboration API Endpoints** | Backend | `app/api/collaboration.py` — POST `/teams`, GET `/teams`, POST `/teams/{id}/invite`, POST `/teams/{id}/share`, GET `/teams/{id}/members` | 3h |
| 5 | **WebSocket Rooms & Events** | Backend | Room per shared resource: `graph:{graph_id}`, `chat:{conv_id}`. Events: `node_created`, `node_updated`, `node_deleted`, `cursor_move`, `presence_join`, `presence_leave` | 3h |
| 6 | **Conflict Resolution (CRDT)** | Backend | Dùng Yjs protocol hoặc operational transformation cho concurrent edits. Simplest: last-write-wins với vector clock | 3h |
| 7 | **Presence Indicator** | Frontend | `PresenceIndicator.tsx` — Hiển thị avatars của users đang online, cursor positions trên graph | 2h |
| 8 | **Real-time Graph Sync** | Frontend | `useGraphWebSocket.ts` hook — Nhận events từ WS, optimistic update, conflict resolution UI | 4h |
| 9 | **Team Management UI** | Frontend | `TeamSettings.tsx` page — Invite members, manage roles, shared resources list | 2h |
| 10 | **Shared Graph Badge** | Frontend | Hiển thị icon 👥 trên shared graphs trong GraphExplorer | 0.5h |
| 11 | **Invitation Email Flow** | Backend | Gửi email invitation (dùng existing email stub hoặc SMTP), accept/decline link | 1h |
| 12 | **WebSocket Tests** | Testing | 15 tests: connection auth, room join/leave, event broadcast, conflict resolution | 1h |

### Deliverables

- `app/api/websocket.py` (~250 lines)
- `app/models/team.py` (~80 lines)
- `app/models/shared_resource.py` (~60 lines)
- `app/api/collaboration.py` (~200 lines)
- `frontend/src/hooks/useGraphWebSocket.ts` (~150 lines)
- `frontend/src/components/shared/PresenceIndicator.tsx` (~80 lines)
- Migration: teams, team_members, shared_resources tables
- 15 integration tests

### Acceptance Criteria

- ✅ 2 users cùng mở shared graph → thấy cursor của nhau real-time
- ✅ User A tạo node → User B thấy node mới xuất hiện trong <500ms
- ✅ Concurrent edit → last-write-wins với notification
- ✅ Team owner mời member qua email → member accept → access shared graphs
- ✅ 15/15 tests passing

---

## Sprint 16: Specialized Agents

> **Priority:** P1 | **Dependency:** Stage 3 (VisualizerAgent pattern) | **Estimate:** ~20 giờ

Base Agent framework + 2 specialized agents: Language Agent, Math Agent.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Base Agent Class** | Backend | `app/core/agents/base_agent.py` — Abstract `Agent` class với `__init__`, `process()`, `get_system_prompt()`, `get_tools()`, `get_capabilities()`. Plugin architecture qua registry | 3h |
| 2 | **Agent Registry** | Backend | `app/core/agents/registry.py` — Register/unload agents, dynamic discovery, version compatibility check | 1h |
| 3 | **Agent Config Schema** | Backend | `app/schemas/agent.py` — AgentConfig(id, name, description, icon, system_prompt_template, tools[], capabilities[]) | 1h |
| 4 | **Language Agent** | Backend | `app/core/agents/language_agent.py` — Specialized cho học ngôn ngữ: vocabulary extraction, grammar patterns, conjugation tables, translation exercises. Prompt: language learning focused | 3h |
| 5 | **Language Agent — Frontend** | Frontend | `LanguageChat.tsx` — Chat UI với vocab cards, grammar highlights, conjugation tables | 3h |
| 6 | **Math Agent** | Backend | `app/core/agents/math_agent.py` — Specialized cho toán: LaTeX rendering, step-by-step solutions, formula extraction từ documents, symbolic computation hints. Prompt: math tutor with Socratic method | 3h |
| 7 | **Math Agent — Frontend** | Frontend | `MathChat.tsx` — Chat UI với KaTeX rendering, equation editor, step-by-step reveal | 3h |
| 8 | **Agent Selector UI** | Frontend | `AgentSelector.tsx` — Dropdown/modal chọn agent khi tạo conversation mới, hiển thị icon + description | 2h |
| 9 | **Agent Management API** | Backend | `app/api/agents.py` — GET `/agents` (list available), GET `/agents/{id}` (detail), POST `/agents` (register custom) | 1h |
| 10 | **Tests** | Testing | 15 tests: base agent, registry, language agent, math agent, agent selector | 1h |

### Deliverables

- `app/core/agents/base_agent.py` (~100 lines)
- `app/core/agents/registry.py` (~80 lines)
- `app/core/agents/language_agent.py` (~200 lines)
- `app/core/agents/math_agent.py` (~200 lines)
- `app/api/agents.py` (~100 lines)
- `frontend/src/pages/LanguageChat.tsx` (~150 lines)
- `frontend/src/pages/MathChat.tsx` (~150 lines)
- `frontend/src/components/shared/AgentSelector.tsx` (~100 lines)
- 15 unit tests

### Acceptance Criteria

- ✅ Register agent → xuất hiện trong Agent Selector UI
- ✅ Language Agent: upload văn bản tiếng Anh → extract vocabulary list, tạo exercises
- ✅ Math Agent: upload tài liệu toán → hiển thị công thức LaTeX, giải step-by-step
- ✅ Switch agent trong chat → system prompt thay đổi đúng
- ✅ 15/15 tests passing

---

## Sprint 17: Media Microlearning

> **Priority:** P2 | **Dependency:** None (optional) | **Estimate:** ~18 giờ

Xử lý video/audio → transcript → knowledge graph.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **YouTube Transcript Service** | Backend | `app/services/youtube_service.py` — `youtube-transcript-api` pip package, fetch transcript bằng video URL hoặc ID | 2h |
| 2 | **Audio Upload & Storage** | Backend | Accept `.mp3`, `.wav`, `.m4a` trong upload pipeline, lưu vào `uploads/audio/` | 1h |
| 3 | **Whisper Transcription** | Backend | `app/services/transcription_service.py` — OpenAI Whisper API hoặc local `faster-whisper` (CPU mode). Chunk transcript theo timestamps | 3h |
| 4 | **Transcript → Text Pipeline** | Backend | Reuse existing text ingestion: transcript chunks → entity extraction → graph building | 2h |
| 5 | **Video Player Component** | Frontend | `VideoPlayer.tsx` — Embed YouTube player hoặc HTML5 audio, sync transcript highlight với playback time | 4h |
| 6 | **Transcript Viewer** | Frontend | `TranscriptViewer.tsx` — Hiển thị transcript với timestamps, click timestamp → seek audio/video | 2h |
| 7 | **Media Document Type** | Backend | Thêm `media_type` enum (video/audio/text) vào `documents` table, `source_url` cho YouTube | 1h |
| 8 | **Audio Player with Sync** | Frontend | `AudioPlayer.tsx` — Waveform visualization (wavesurfer.js), sync với transcript | 2h |
| 9 | **Tests** | Testing | 10 tests: YouTube fetch, transcript parsing, audio upload | 1h |

### Deliverables

- `app/services/youtube_service.py` (~150 lines)
- `app/services/transcription_service.py` (~200 lines)
- `frontend/src/components/media/VideoPlayer.tsx` (~150 lines)
- `frontend/src/components/media/AudioPlayer.tsx` (~180 lines)
- `frontend/src/components/media/TranscriptViewer.tsx` (~120 lines)
- Migration: `media_type` enum, `source_url` column
- 10 unit tests

### Acceptance Criteria

- ✅ Paste YouTube URL → fetch transcript → build graph tự động
- ✅ Upload `.mp3` → transcribe → extract entities → hiển thị transcript sync với audio
- ✅ Click transcript line → audio seek tới timestamp tương ứng
- ✅ 10/10 tests passing

---

## Sprint 18: PWA & Mobile

> **Priority:** P1 | **Dependency:** Sprint 14 (UI Polish) | **Estimate:** ~15 giờ

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
| 7 | **Push Notifications** | Backend | `app/services/notification_service.py` — VAPID keys, subscription endpoint, send notification API | 2h |
| 8 | **Push Notifications — Frontend** | Frontend | `usePushNotifications.ts` hook — Request permission, subscribe, handle push events, badge count | 2h |
| 9 | **Install Prompt** | Frontend | `InstallPrompt.tsx` — Detect `beforeinstallprompt`, show banner "Install AetherTutor", handle user choice | 1h |
| 10 | **Tests** | Testing | 8 tests: manifest validity, SW registration, offline fallback, push subscription | 1h |

### Deliverables

- `frontend/vite.config.ts` (updated with PWA plugin)
- `public/manifest.json` (~30 lines)
- `frontend/src/pages/OfflinePage.tsx` (~80 lines)
- `frontend/src/hooks/usePushNotifications.ts` (~120 lines)
- `frontend/src/components/shared/InstallPrompt.tsx` (~60 lines)
- `app/services/notification_service.py` (~150 lines)
- 8 unit tests

### Acceptance Criteria

- ✅ Lighthouse PWA score ≥ 90
- ✅ Install banner xuất hiện trên Chrome mobile/desktop
- ✅ Offline mode: vẫn xem được flashcards, notes đã cache
- ✅ Push notification: review reminder, due flashcards alert
- ✅ 8/8 tests passing

---

## Sprint 19: Security & Observability

> **Priority:** P1 | **Dependency:** None (parallel được) | **Estimate:** ~12 giờ

Fix TODOs, security gaps, monitoring, error tracking.

### Tasks

| # | Task | Layer | Details | Est. |
|---|------|-------|---------|------|
| 1 | **Email Verification Flow** | Backend | Generate verification token, send email, verify endpoint, resend logic | 2h |
| 2 | **Password Reset** | Backend | POST `/auth/forgot-password` (send reset link), POST `/auth/reset-password` (validate token + update) | 2h |
| 3 | **Document Ownership Validation** | Backend | Fix TODO: validate user owns document before entity CRUD (entity_resolution, graph endpoints) | 1h |
| 4 | **Quiz Bloom Level Persistence** | Backend | Fix TODO: store `bloom_level` trong quiz answer model thay vì hardcode "remember" | 0.5h |
| 5 | **Quiz Entity Type Enrichment** | Backend | Fix TODO: fetch entity type từ graph cho weak areas endpoint | 0.5h |
| 6 | **Sentry Integration** | Backend + Frontend | Backend: `sentry-sdk` FastAPI integration. Frontend: `@sentry/react` + `@sentry/tracing`. Error boundary gửi Sentry | 2h |
| 7 | **Flashcard Quiz Wrong Answers** | Backend | Fix TODO: implement `generate_from_quiz_wrong_answers()` — quiz sai → auto tạo flashcard | 1h |
| 8 | **Context Chips → Graph Navigation** | Frontend | Fix TODO: click entity chip → navigate Graph page với entity selected/highlighted | 1h |
| 9 | **Rate Limiting Audit** | Backend | Review rate limits trên tất cả endpoints, log violations, add exponential backoff | 1h |
| 10 | **Tests** | Testing | 10 tests: email verification, password reset, ownership validation, Sentry capture | 1h |

### Deliverables

- `app/api/auth.py` (updated: forgot/reset password endpoints)
- `app/services/email_service.py` (~150 lines)
- Sentry integration (backend + frontend config)
- Fix 4 TODOs trong codebase
- 10 unit tests

### Acceptance Criteria

- ✅ Register → nhận email verification → click link → verified
- ✅ Forgot password → nhận email reset link → đặt password mới
- ✅ Entity CRUD chỉ thành công nếu user sở hữu document
- ✅ Quiz wrong answers → auto-generate flashcards hoạt động
- ✅ Click context chip → Graph page highlight entity tương ứng
- ✅ Errors được gửi đến Sentry
- ✅ 10/10 tests passing

---

## Tổng kết Stage 4

### Metrics tổng thể

| Metric | Stage 3 End | Stage 4 Target | Delta |
|--------|-------------|---------------|-------|
| **Sprints** | 2 (8+9) | 7 (13-19) | +5 |
| **Tasks** | 20 | 74 | +54 |
| **API Endpoints** | 87 | ~105 | +18 |
| **Frontend Pages** | 9 | ~14 | +5 |
| **Unit Tests** | 288 | ~370 | +82 |
| **Agents** | 2 | 4 | +2 |
| **Lines of Code** | ~2,200 (Stage 3) | ~4,500 (est.) | +2,300 |
| **Test Pass Rate** | 100% | 100% | Maintain |

### Sprint Breakdown

| Sprint | Tasks | Priority | Est. Hours | Dependencies |
|--------|-------|----------|-----------|-------------|
| **13**: Source Code Visualizer | 8 | P1 | ~15h | Stage 3 Graph CRUD |
| **14**: UI Polish & Dark Mode | 12 | P0 | ~20h | None |
| **15**: Real-time Collaboration | 14 | P0 | ~25h | Sprint 14, Stage 3 |
| **16**: Specialized Agents | 12 | P1 | ~20h | Stage 3 VisualizerAgent |
| **17**: Media Microlearning | 10 | P2 | ~18h | None |
| **18**: PWA & Mobile | 10 | P1 | ~15h | Sprint 14 |
| **19**: Security & Observability | 8 | P1 | ~12h | None |
| **TOTAL** | **74** | — | **~125h** | — |

### Đề xuất thứ tự triển khai

```
Phase 1 (Nền tảng): Sprint 14 → Sprint 19
Phase 2 (Features): Sprint 13 → Sprint 16
Phase 3 (Advanced): Sprint 15 → Sprint 17 → Sprint 18
```

**Lý do:**
1. **Sprint 14 trước** vì dark mode + keyboard shortcuts là nền tảng cho mọi sprint sau
2. **Sprint 19 song song** vì fix TODOs + security không blocking features khác
3. **Sprint 15 (Collaboration)** làm sau cùng vì phức tạp nhất (WebSocket, CRDT, presence)
4. **Sprint 17 (Media)** là optional — có thể skip nếu resource hạn chế

### Rủi ro & Giảm thiểu

| Rủi ro | Impact | Xác suất | Giảm thiểu |
|--------|--------|---------|-----------|
| WebSocket scaling (1000+ concurrent) | Cao | Trung bình | Dùng Redis pub/sub, connection pooling, load testing |
| CRDT conflict complexity | Cao | Cao | Start với last-write-wins, upgrade CRDT sau |
| PWA Safari compatibility | Trung bình | Trung bình | Test iOS Safari sớm, fallback graceful |
| Whisper API cost | Trung bình | Cao | Support local `faster-whisper` làm fallback |
| Sentry rate limit (free tier) | Thấp | Thấp | Sample errors, chỉ gửi 1000 events/ngày |

---

## Phụ lục: TODOs cần fix (từ Stage 3 audit)

| # | File | Line | TODO | Sprint fix |
|---|------|------|------|-----------|
| 1 | `app/services/flashcard_generation_service.py` | 108 | Implement `generate_from_quiz_wrong_answers()` | Sprint 19 |
| 2 | `app/api/quiz.py` | 333 | Store bloom_level in answer model | Sprint 19 |
| 3 | `app/api/quiz.py` | 627 | Fetch entity_type from graph | Sprint 19 |
| 4 | `app/api/graph.py` | 939 | Validate user owns document_id | Sprint 19 |
| 5 | `frontend/src/components/shared/ErrorBoundary.tsx` | 38 | Send to Sentry | Sprint 19 |
| 6 | `frontend/src/components/shared/ContextChips.tsx` | 24 | Pass entity name to Graph page | Sprint 19 |

---

## Milestone Versions

| Version | Scope | Target |
|---------|-------|--------|
| **v0.3.1** | Sprint 13 + 14 (Source Code + UI Polish) | Q4 2026 |
| **v0.3.2** | Sprint 15 + 16 (Collaboration + Agents) | Q4 2026 |
| **v0.4.0** | Sprint 17 + 18 (Media + PWA) | Q1 2027 |
| **v0.5.0** | Sprint 19 + Polish (Security + Observability) | Q1 2027 |
| **v1.0.0** | Stage 4 Complete — Public Release | Q1 2027 |

---

© 2026 AetherTutor Team
*Stage 4 Plan — Draft v1.0*
