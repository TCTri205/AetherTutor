# Lộ Trình Phát Triển (Roadmap)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 12, 2026
> **Status:** Stage 4 Phase 1 Complete — UI Polish + Security Foundation

---

Tài liệu này theo dõi lộ trình phát triển của AetherTutor từ giai đoạn R&D đến khi ra mắt MVP và các tính năng mở rộng.

---

## 1. Stage 1 (Foundation): Thiết lập nền tảng

> Thời điểm dự kiến: Quý 1 - 2026 | Mục tiêu: Xây dựng hạ tầng **LightRAG** và hệ thống Agent điều phối cơ bản.

- [x] Thiết kế kiến trúc **Agentic Learning Ecosystem**.
- [x] Triển khai **Parent Orchestrator** với giao thức **MCP**.
- [x] Xây dựng **LightRAG Pipeline**: Entity Extraction → Graph Construction → Dual-Level Retrieval.
- [x] Hoàn thiện **Socratic Tutor Agent** (Chế độ Feynman Chat cơ bản với graph-aware context).
- [x] Implement document upload & processing (Text Ingestion logic).
- [x] Implement PDF text extraction.
- [x] Basic graph viewer để visualize knowledge graph.

**MVP Scope:** Upload PDF → LightRAG Processing → Chat với AI

## 2. Stage 2 (Intelligence): Thông minh hóa & Ghi nhớ

> Thời điểm dự kiến: Quý 2 - 2026 | Mục tiêu: Tăng cường khả năng trích xuất tri thức và cá nhân hóa việc học.

- [x] Tích hợp **The Examiner Agent** để tự động tạo Quiz và Flashcard từ **graph entities**.
- [x] Triển khai thuật toán **Spaced Repetition (SM-2)** cho lịch ôn tập.
- [x] Ra mắt tính năng **Zettelkasten Graph View** (Bản beta).
- [x] Cải thiện kỹ năng RAG bằng cách giảm thiểu ảo giác của AI qua **LightRAG cross-verification**.
- [x] Multi-document reasoning (trả lời queries cần nhiều documents).
- [x] Testing & Polish (Sprint 5 — 90 unit tests passing).

## 3. Stage 3 (Visualization): Trực quan hóa & Multimedia

> Thời điểm dự kiến: Quý 3 - 2026 | Mục tiêu: Mở rộng khả năng xử lý hình ảnh và video.
> **Trạng thái:** ✅ **CORE COMPLETE** (Sprint 8 + Sprint 9 — 20/20 tasks, 38 tests passing)

- [x] Hoàn thiện **Visualizer Agent** với khả năng render **Mermaid.js** từ LightRAG graph (Sprint 8).
- [ ] Triển khai **Media Microlearning Pipeline** (Xử lý Video/Audio tự động) — **DEFERRED → Stage 5**.
- [x] Tích hợp MermaidDiagram component vào Chat (Sprint 8).
- [x] Topic/Session organization (Sprint 9 — Migration, Redis cache, API endpoints).
- [ ] Interactive graph editing capabilities — **DEFERRED → Stage 5 Sprint 21**.
- [ ] Source Code Visualizer — **DEFERRED → Stage 4 Sprint 13**.

## 4. Stage 4 (Interactive UX): Nâng cấp trải nghiệm & Cộng đồng

> Thời điểm dự kiến: Quý 4 - 2026 | Mục tiêu: Tối ưu hóa trải nghiệm người dùng và hỗ trợ làm việc nhóm.
> **Trạng thái:** 🟡 **PHASE 1 COMPLETE** (Sprint 14 + Sprint 19 — 24/80 tasks). Phase 2-3 pending.

- [x] **Phase 1 Complete:** UI Polish (Dark Mode, Keyboard Shortcuts, Loading Skeletons) + Security (Email Verification, Password Reset, Sentry) — Sprint 14 + 19.
- [ ] Source Code Visualizer — Sprint 13 (Backend done, Frontend pending).
- [ ] Hỗ trợ làm việc chung (Collaborative Learning) qua WebSockets — Sprint 15 (pending).
- [ ] Specialized Agents (Language, Math) — Sprint 16 (pending).
- [ ] PWA & Mobile — Sprint 18 (pending).
- [ ] Media Microlearning — Sprint 17 (DEFERRED → Stage 5).

---

## Bảng theo dõi cột mốc (Milestones)

| Cột mốc | Mô tả | Trạng thái |
| :--- | :--- | :--- |
| **Pioneering** | Hoàn tất thiết kế và Research | 100% ✅ |
| **v0.1 (MVP)** | LightRAG core + Chat đa luồng/Streaming + Full Frontend UI | 100% ✅ |
| **v0.1.1 (Refactoring)** | Code quality, performance, testing (+155% tests), production-ready | 100% ✅ |
| **v0.2 (Pro)** | Intelligence + SM-2 + Flashcards + Zettelkasten | 100% ✅ |
| **v0.3 (Visualization)** | Visualizer Agent + Mermaid + Topic organization | 100% ✅ (Core) |
| **v0.4 (Interactive UX)** | Dark Mode + Security + Collaboration + PWA | 30% 🔄 (Phase 1 done) |
| **v1.0 (Public)** | Full feature set + Media + Launch ready | 0% |

---

## Mapping: Stage → Version

| Stage | Version | Mô tả | Trạng thái |
| :--- | :--- | :--- | :--- |
| Stage 1 | v0.1 | MVP — LightRAG Core + Chat | ✅ Complete |
| Stage 2 | v0.2 | Intelligence — SM-2 + Flashcards + Zettelkasten | ✅ Complete |
| Stage 3 | v0.3 | Visualization — Mermaid + Topics | ✅ Core Complete |
| Stage 4 | v0.4 | Interactive UX — Dark Mode + Collaboration + PWA | 🔄 Phase 1 Complete |
| Stage 5 | v1.0 | Launch Ready — Media + Testing + Polish | ⏸️ Pending |

---

## LightRAG Integration Timeline

### Sprint 1: Core Infrastructure & Local Setup (Week 1–2)

- [x] Setup FastAPI project structure.
- [x] **Local Environment Setup**:
  - Tạo Python venv: `python -m venv venv`.
  - Cài đặt dependencies (Windows Powershell): `.\venv\Scripts\Activate.ps1` -> `pip install -r requirements.txt`.
- [x] **Docker Infrastructure Readiness**:
  - Chạy các base services: `docker compose up -d db redis chromadb`.
  - Healthcheck các services từ bên ngoài container (Host).
- [x] **Database & Connectivity**:
  - Hoàn thiện `app/database.py` hỗ trợ async connection.
  - Setup Alembic: `alembic init alembic`.
  - Migration đầu tiên: `alembic revision --autogenerate -m "initial"`.
- [x] **MCP (Model Context Protocol)**:
  - Khởi tạo layer MCP cơ bản phục vụ cho việc truyền tải context giàu tri thức.
- [x] **Hybrid Model**: Mã nguồn chạy tại Local (Host) kết nối tới Hạ tầng (Database/Cache) chạy trong Docker.
- [x] NetworkX graph implementation.
- [x] LLM client setup (OpenAI + Ollama).

### Sprint 2: LightRAG Pipeline & Validation (Week 3–4)

- [x] Entity extraction từ documents.
- [x] Graph construction với hỗ trợ persistence (SQL & ChromaDB).
- [x] Dual-level retrieval implementation.
- [x] **Connectivity Validation**: Hoàn thiện bộ script kiểm thử kết nối (`scripts/validate_pipeline.py`).
- [x] Context assembly cho LLM với tối ưu hóa prompt (Socratic mode).

### Sprint 3: Document Processing (Week 5) - COMPLETED

- [x] PDF upload & text extraction
- [x] Chunking strategy implementation
- [x] Batch entity processing
- [x] Graph persistence (save/load)

### Sprint 4: Chat Integration (Week 6–7) - COMPLETED

- [x] Chat endpoint với LightRAG context
- [x] Socratic mode với graph-aware prompts
- [x] Response streaming (SSE)
- [x] Error handling & Durability (Hardened)

### Sprint 5: Frontend (Week 8–9) — COMPLETED ✅

- [x] Document upload UI (drag & drop, validation, progress tracking)
- [x] Chat interface (SSE streaming với buffered parser, retry logic, 30s timeout detection)
- [x] Graph viewer (React Flow — radial layout, custom nodes/edges với relation_type labels)
- [x] Status indicators (granular processing steps: EXTRACTING → CHUNKING → EXTRACTING_ENTITIES → BUILDING_GRAPH → EMBEDDING → COMPLETED)
- [x] **Tech Stack:** React 18 + TypeScript + Vite, Tailwind CSS v4, Zustand, Axios, Sonner (toasts), framer-motion, reactflow v11, lucide-react, react-markdown + KaTeX
- [x] **Components:** 34 files — 4 pages (Dashboard, Vault, Chat, GraphExplorer), 3 Zustand stores, 2 hooks (useChat, usePolling), 5 API services
- [x] **Features:** ContextChips (found_entities từ SSE), ConversationList sidebar, LLM Mode Badge (🔒 Local / 🌐 Cloud), mobile sidebar toggle với framer-motion drawer, error states (6 types), ARIA labels
- [x] **Testing:** 46 unit tests passing (Error types, Stores, SSE parser, ApiError) + E2E integration test guide (4 flows + error recovery)
- [x] **Build:** `npm run build` SUCCESS — 0 errors, 1.2MB JS bundle, 95KB CSS

- [x] Backend integration test — Full-stack validation: Upload → Chat → Graph (Completed với Docker)
- [x] Performance optimization — CORS hardening, Rate limiting (slowapi), Production build
- [x] CI/CD Pipeline — GitHub Actions workflow `ci.yml` setup
- [x] Full-Stack Dockerization — Multi-stage builds + Nginx configuration
- [x] MVP Launch ✅

---

## 5. Chỉ số thành công (Success Criteria)

| Metric | Target | Measurement |
| :--- | :--- | :--- |
| Document processing time | < 30s per 10 pages | Time from upload to chat-ready |
| Query response time | < 3 seconds | Time from user message to AI response |
| Entity extraction accuracy | > 80% | Manual review of extracted entities |
| Answer relevance | > 70% | User feedback rating |
| Graph construction | 20-40 entities per doc | Average entities extracted |

---

> [!IMPORTANT]
> Lộ trình trên có thể được điều chỉnh linh hoạt dựa trên phản hồi của cộng đồng người dùng và sự tiến bộ của công nghệ LLM/AI mới.
> **LightRAG** là priority số 1 cho MVP vì đây là core differentiator của AetherTutor.
