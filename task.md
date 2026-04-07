# Task: Phase 6 - Integration & Launch

> **Updated:** April 7, 2026 — Version 1.5 với Codebase Audit Complete
> **Status:** Draft — Chờ triển khai

---

## Changelog v1.4 → v1.5

- **Loại bỏ S1.5** (WorkerSettings) — vì đã tồn tại trong `app/worker/tasks.py`.
- **Sửa worker path:** `app.worker.main.WorkerSettings` → `app.worker.tasks.WorkerSettings` ở mọi nơi.
- **Bổ sung findings:**
  - `.github/workflows/` không tồn tại — phải tạo CI workflow từ scratch.
  - `WorkerSettings` đã có sẵn trong `app/worker/tasks.py`.
  - `tests/mocks/llm_mock.py` đã có — không cần tạo mới.
- **Điều chỉnh priority:** Đề xuất nâng Docker full-stack lên P1 (từ P2).
- **Thêm task S0.7:** Kiểm tra worker path trước khi bắt đầu Sprint 1.

---

## Entry Criteria từ Phase 5 (PHẢI ĐẠT TRƯỚC KHI BẮT ĐẦU)
- [x] **EC1:** Frontend build `npm run build` — 0 errors, JS bundle < 2MB, CSS < 200KB
- [x] **EC2:** Frontend unit tests — 46/46 passing (`phase5.test.ts`)
- [x] **EC3:** E2E test documentation — `docs/E2E_INTEGRATION_TESTS.md` hoàn chỉnh
- [x] **EC4:** Backend CORS middleware đã thêm vào `app/main.py`
- [x] **EC5:** Backend `/health` endpoint trả về LLM metadata
- [x] **EC6:** Backend SSE `done` event có `found_entities` field
- [x] **EC7:** Upload endpoint phân biệt 200 (duplicate) vs 202 (new file)
- [x] **EC8:** ProcessingStep enum + column đã migrate vào DB
- [ ] **EC9:** Tất cả 4 routes hoạt động: `/`, `/vault`, `/chat/:docId`, `/graph/:docId` — Cần manual verify
- [ ] **EC10:** Mobile sidebar toggle hoạt động (framer-motion drawer) — Cần manual verify

> **⚠️ Nếu bất kỳ EC nào chưa đạt → Fix Phase 5 trước, không bắt đầu Phase 6.**

---

## Sprint 0: Pre-Phase 6 Setup (Làm TRƯỚC) [Pre-work]
- [x] **S0.5** Setup Vitest Config — Tạo `frontend/vitest.config.ts`, `frontend/src/setupTests.ts` và thêm `"test": "vitest run"` vào `package.json`
- [x] **S0.6** Verify EC9/EC10 — Manual check 4 routes hoạt động và mobile sidebar toggle dùng browser tool
- [x] **S0.7** Verify Worker Path — Chạy `arq app.worker.tasks.WorkerSettings --check` để đảm bảo worker path đúng

---

## Sprint 1: Test Infrastructure & Integration (Day 1-2) [P0]
- [x] **S1.1** Setup Integration Fixtures — Tạo `tests/conftest.py` với core fixtures (`async_client`, `test_db`, `sample_pdf_bytes`, `processed_document`)
- [x] **S1.1b** LLM Mocking — `tests/mocks/llm_mock.py` đã có, tích hợp vào `conftest.py` với `USE_LLM_MOCK` flag, pytest fixtures
- [x] **S1.2a** API Integration Tests — Documents API (`test_documents_api.py`: upload, duplicate, oversized, status, delete, pagination)
- [x] **S1.2b** API Integration Tests — Chat API (`test_chat_api.py`: create/list/delete conversation, SSE stream với LLM mock, found_entities, invalid doc)
- [x] **S1.2c** API Integration Tests — Graph API (`test_graph_api.py`: nodes, edges, stats, empty doc, nonexistent doc)
- [x] **S1.3a** Worker Integration — `test_worker_flow.py` (upload enqueues job, worker processes, handles failure, idempotent) — dùng `arq app.worker.tasks.WorkerSettings`
- [x] **S1.4** Integration Test Execution — Chạy `pytest tests/integration/ -v` với LLM mock, target > 95% pass

> ~~**S1.5: Worker Settings File**~~ → **ĐÃ CÓ** trong `app/worker/tasks.py`. Không cần tạo file mới.

## Sprint 2: Hardening & Production Ready (Day 3) [P1]
- [x] **S2.1a** CORS & Docker Networking Hardening — Cập nhật `app/config.py` với ALLOWED_ORIGINS, APP_URL, FRONTEND_URL, APP_ENV + `DATABASE_HOST`, `REDIS_HOST`, `CHROMADB_HOST` động
- [x] **S2.1b** CORS Hardening — Cập nhật `app/main.py` dùng `settings.allowed_origins_list` thay vì hard-coded
- [x] **S2.1c** CORS & Env Hardening — Cập nhật `.env.example` với vars mới + hướng dẫn switch Local/Docker (`*_HOST` vars)
- [x] **S2.2a** Unit Tests Expansion — `test_document_service.py` (FIXED)
- [x] **S2.2b** Unit Tests Expansion — `test_retriever.py` (FIXED)
- [x] **S2.2c** Unit Tests Expansion — `test_pipeline.py` (FIXED)
- [x] **S2.2d** Unit Tests Expansion — `test_worker_tasks.py` (FIXED)
- [x] **S2.3a** Security Audit — Rate Limiting (SlowAPI integrated cho upload/chat)
- [ ] **S2.3b** Security Audit — Input Validation (file content-type, chat input sanitize, UUID validation)
- [ ] **S2.3c** Security Audit — Dependency Scan (`pip audit`, `npm audit`, fix CVE > 8.0)
- [ ] **S2.3d** Security Audit — SQL Injection Review (codebase uses parameterized queries via SQLAlchemy)
- [x] **S2.3e** Security Audit — Secrets Management (không hard-code API keys, `.env` trong `.gitignore`)
- [ ] **S2.4** Bug Triage Process — Thiết lập Issue Template, Priority Definitions (P1/P2/P3), Daily triage meeting 15-min

## Sprint 3: E2E Validation & Performance (Day 4-5) [P0/P1]
- [ ] **S3.1a** Manual E2E — Flow 1: Upload → EXTRACTING → CHUNKING → ... → COMPLETED
- [ ] **S3.1b** Manual E2E — Flow 2: Chat → SSE stream → ContextChips hiển thị
- [ ] **S3.1c** Manual E2E — Flow 3: Graph → Node click → GraphSidebar
- [ ] **S3.1d** Manual E2E — Flow 4a-4d: Error Recovery scenarios
- [ ] **S3.2a** Performance Benchmarking — First Meaningful Paint < 1.5s (Lighthouse)
- [ ] **S3.2b** Performance Benchmarking — Graph render (50 nodes) < 500ms (DevTools Performance)
- [ ] **S3.2c** Performance Benchmarking — SSE first chunk < 3s (Network TTFB)
- [ ] **S3.2d** Performance Benchmarking — Document processing (10 trang) < 30s
- [ ] **S3.2e** Performance Benchmarking — Query response < 3s
- [ ] **S3.2f** Performance Benchmarking — Memory usage (peak) < 2GB
- [ ] **S3.3a** Accessibility — Keyboard Navigation Testing (tab order, focus visible, Enter/Space, ESC)
- [ ] **S3.3b** Accessibility — Screen Reader Testing (NVDA: ARIA labels, aria-live, heading hierarchy)
- [ ] **S3.3c** Accessibility — Color Contrast Validation (WCAG AA: text ≥ 4.5:1, large text ≥ 3:1)

## Sprint 4: Full Stack Docker & Optimization (Day 5-6) [P2]
- [x] **S4.1a** Multi-stage Dockerfiles — Backend (`python:3.11-slim` với build deps cho asyncpg/tiktoken)
- [x] **S4.1b** Multi-stage Dockerfiles — Frontend (`node:20-alpine` builder + `nginx:alpine`)
- [x] **S4.2** Nginx Configuration — SPA routing + `/health` proxy cho LLM Mode Badge
- [x] **S4.3** Docker Compose Full Stack — Thêm `api`, `worker`, `frontend` services vào `docker-compose.yml` với `environment: DATABASE_HOST=db, REDIS_HOST=redis, CHROMADB_HOST=chromadb`
- [x] **S4.4** CI/CD Pipeline — Tạo `.github/workflows/ci.yml` TỪ SCRATCH với `USE_LLM_MOCK=true` cho backend tests
  - **S4.4a:** Setup workflow structure (postgres, redis, chromadb services)
  - **S4.4b:** Thêm backend tests step với `USE_LLM_MOCK=true`
  - **S4.4c:** Thêm frontend tests + build check
- [ ] **S4.5a** Frontend Optimization — Code Splitting (lazy load routes: Vault, Chat, Graph)
- [ ] **S4.5b** Frontend Optimization — Lazy load heavy components (ReactFlow, react-markdown + KaTeX)
- [ ] **S4.5c** Frontend Optimization — Tree shaking (`npx knip` phát hiện unused files/exports)
- [ ] **S4.6** Docker Validation — `docker compose up --build`, verify 6 checklist items

> **⚠️ Lưu ý:** `.github/workflows/` chưa tồn tại trong repo — phải tạo từ đầu.

## Sprint 5: Outreach & Documentation (Day 7) [P1/P2]
- [ ] **S5.1a** User Testing Plan — Tạo User Testing Script (recruiting 3-5 users, 30-45 phút/user)
- [ ] **S5.1b** User Testing Plan — Test Scenarios (upload, chat, graph, error)
- [ ] **S5.1c** User Testing Plan — Google Form Feedback template
- [ ] **S5.2a** Final Documentation — Cập nhật `docs/Roadmap.md` (Phase 6 tasks → LAUNCHED)
- [ ] **S5.2b** Final Documentation — Cập nhật `docs/MVP_Implementation_Plan.md` (Phase 6 status → COMPLETE)
- [ ] **S5.2c** Final Documentation — Cập nhật `docs/E2E_INTEGRATION_TESTS.md` (actual values, browser compatibility)
- [ ] **S5.2d** Final Documentation — Tạo `docs/LAUNCH_CHECKLIST.md`
- [ ] **S5.3a** Rollback Plan — Database Migration Rollback (alembic downgrade, pg_dump backup)
- [ ] **S5.3b** Rollback Plan — Docker Compose Rollback (down, restart infra)
- [ ] **S5.3c** Rollback Plan — Code Rollback (git revert, git reset)
- [ ] **S5.3d** Rollback Plan — Rollback Decision Criteria table
- [ ] **S5.4** MVP Launch Milestone — Final checks, Launch announcement, Post-launch monitoring

---

## Backend Tests Target

> **⚠️ Hiện tại backend chỉ có 3 unit tests** (`test_chat_hardened.py`) — quá mỏng cho production.

| Metric | Target | Hiện tại |
|--------|--------|----------|
| Unit tests | 30+ tests | 3 tests |
| Integration tests | 20+ tests | 0 tests |
| Coverage | > 80% | TBD |

---

## Ghi chú quan trọng từ Deep Review

### Backend Gaps đã phát hiện
| Gap | Mức độ | Sprint xử lý |
|-----|--------|-------------|
| Backend unit tests quá mỏng (chỉ 3 tests) | 🔴 Critical | S2.2 |
| Không có integration tests | 🔴 Critical | S1 |
| Không có CI/CD pipeline | 🟡 Important | S4.4 — Tạo từ scratch |
| Security review chưa toàn diện (chỉ CORS) | 🟡 Important | S2.3 |
| Không có rollback plan | 🟠 Note | S5.3 |
| ~~Ollama local status chưa xác nhận~~ | ✅ **Resolved** | S1.1b — LLM Mocking đã giải quyết |
| Docker networking hard-code localhost | 🟡 Important | S2.1a — `*_HOST` vars động |
| ~~Worker settings missing~~ | ✅ **ĐÃ CÓ** | `app/worker/tasks.py` — không cần tạo mới |

### Files backend bị ảnh hưởng
| File | Thay đổi |
|------|---------|
| `app/config.py` | Thêm ALLOWED_ORIGINS, APP_URL, FRONTEND_URL, APP_ENV + `DATABASE_HOST`, `REDIS_HOST`, `CHROMADB_HOST` |
| `app/main.py` | Dùng `settings.allowed_origins_list` thay vì hard-coded |
| `.env.example` | Bổ sung vars mới + hướng dẫn Local vs Docker networking |
| `tests/conftest.py` | **NEW** — Core fixtures |
| `tests/mocks/__init__.py` | **ĐÃ CÓ** — Mock package init |
| `tests/mocks/llm_mock.py` | **ĐÃ CÓ** — MockAsyncOpenAI, MockLLMService, pytest fixtures |
| `tests/integration/test_documents_api.py` | **NEW** — 6 tests |
| `tests/integration/test_chat_api.py` | **NEW** — 7 tests (dùng LLM mock) |
| `tests/integration/test_graph_api.py` | **NEW** — 5 tests |
| `tests/integration/test_worker_flow.py` | **NEW** — 4 tests |
| `tests/unit/test_document_service.py` | **NEW** — 6 tests |
| `tests/unit/test_retriever.py` | **NEW** — 4 tests |
| `tests/unit/test_pipeline.py` | **NEW** — 3 tests |
| `tests/unit/test_worker_tasks.py` | **NEW** — 3 tests |
| `Dockerfile` | Multi-stage build |
| `docker-compose.yml` | Thêm api, worker, frontend services + `*_HOST` environment vars |
| `.github/workflows/ci.yml` | **NEW** — CI/CD pipeline (chưa tồn tại) |
| `frontend/nginx.conf` | **NEW** — SPA routing + health proxy |
| `docs/LAUNCH_CHECKLIST.md` | **NEW** — Launch criteria |
