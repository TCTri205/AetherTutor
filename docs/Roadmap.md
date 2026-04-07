# Lộ Trình Phát Triển (Roadmap)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 7, 2026
> **Status:** LAUNCHED (MVP Phase 6 Complete — Ready for Production deployment)

---

Tài liệu này theo dõi lộ trình phát triển của AetherTutor từ giai đoạn R&D đến khi ra mắt MVP và các tính năng mở rộng.

---

## 1. Giai đoạn 1 (Foundation): Thiết lập nền tảng

> Thời điểm dự kiến: Quý 1 - 2026 | Mục tiêu: Xây dựng hạ tầng **LightRAG** và hệ thống Agent điều phối cơ bản.

- [x] Thiết kế kiến trúc **Agentic Learning Ecosystem**.
- [x] Triển khai **Parent Orchestrator** với giao thức **MCP**.
- [x] Xây dựng **LightRAG Pipeline**: Entity Extraction → Graph Construction → Dual-Level Retrieval.
- [x] Hoàn thiện **Socratic Tutor Agent** (Chế độ Feynman Chat cơ bản với graph-aware context).
- [x] Implement document upload & processing (Text Ingestion logic).
- [x] Implement PDF text extraction.
- [x] Basic graph viewer để visualize knowledge graph.

**MVP Scope:** Upload PDF → LightRAG Processing → Chat với AI

## 2. Giai đoạn 2 (Intelligence): Thông minh hóa & Ghi nhớ

> Thời điểm dự kiến: Quý 2 - 2026 | Mục tiêu: Tăng cường khả năng trích xuất tri thức và cá nhân hóa việc học.

- [ ] Tích hợp **The Examiner Agent** để tự động tạo Quiz và Flashcard từ **graph entities**.
- [ ] Triển khai thuật toán **Spaced Repetition (SM-2)** cho lịch ôn tập.
- [ ] Ra mắt tính năng **Zettelkasten Graph View** (Bản beta).
- [ ] Cải thiện kỹ năng RAG bằng cách giảm thiểu ảo giác của AI qua **LightRAG cross-verification**.
- [ ] Multi-document reasoning (trả lời queries cần nhiều documents).

## 3. Giai đoạn 3 (Visualization): Trực quan hóa & Multimedia

> Thời điểm dự kiến: Quý 3 - 2026 | Mục tiêu: Mở rộng khả năng xử lý hình ảnh và video.

- [ ] Hoàn thiện **Visualizer Agent** với khả năng render **Mermaid.js** song hướng từ LightRAG graph.
- [ ] Triển khai **Media Microlearning Pipeline** (Xử lý Video/Audio tự động).
- [ ] Ra mắt tính năng **Source Code Visualizer** dành riêng cho lập trình viên.
- [ ] Tích hợp chỉnh sửa Mindmap/Flowchart trực tiếp trên UI.
- [ ] Interactive graph editing capabilities.

## 4. Giai đoạn 4 (Interactive UX): Nâng cấp trải nghiệm & Cộng đồng

> Thời điểm dự kiến: Quý 4 - 2026 | Mục tiêu: Tối ưu hóa trải nghiệm người dùng và hỗ trợ làm việc nhóm.

- [ ] Nâng cấp UI toàn diện (Rich Aesthetics) với các hiệu ứng tương tác cao cấp.
- [ ] Hỗ trợ làm việc chung (Collaborative Learning) qua WebSockets.
- [ ] Mở rộng hệ sinh thái các Agent chuyên biệt theo yêu cầu người dùng (Language Agent, Math Agent).
- [ ] Ra mắt ứng dụng Mobile (PWA/Native) để học tập mọi lúc mọi nơi.
- [ ] Shared knowledge graphs cho team learning.

---

## Bảng theo dõi cột mốc (Milestones)

| Cột mốc | Mô tả | Trạng thái |
| :--- | :--- | :--- |
| **Pioneering** | Hoàn tất thiết kế và Research | 100% |
| **v0.1 (MVP)** | LightRAG core + Chat đa luồng/Streaming + Full Frontend UI | 100% ✅ |
| **v0.1.1 (Refactoring)** | Code quality, performance, testing (+155% tests), production-ready | 100% ✅ |
| **v0.2 (Pro)** | Visualization + SM-2 + Flashcards | 0% |
| **v0.3 (Ecosystem)** | Multi-document + Collaborative graphs | 0% |
| **v1.0 (Public)** | Full feature set + Mobile app | 0% |

---

## LightRAG Integration Timeline

### Phase 1: Core Infrastructure & Local Setup (Week 1–2)

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

### Phase 2: LightRAG Pipeline & Validation (Week 3–4)

- [x] Entity extraction từ documents.
- [x] Graph construction với hỗ trợ persistence (SQL & ChromaDB).
- [x] Dual-level retrieval implementation.
- [x] **Connectivity Validation**: Hoàn thiện bộ script kiểm thử kết nối (`scripts/validate_pipeline.py`).
- [x] Context assembly cho LLM với tối ưu hóa prompt (Socratic mode).

### Phase 3: Document Processing (Week 5) - COMPLETED

- [x] PDF upload & text extraction
- [x] Chunking strategy implementation
- [x] Batch entity processing
- [x] Graph persistence (save/load)

### Phase 4: Chat Integration (Week 6–7) - COMPLETED

- [x] Chat endpoint với LightRAG context
- [x] Socratic mode với graph-aware prompts
- [x] Response streaming (SSE)
- [x] Error handling & Durability (Hardened)

### Phase 5: Frontend (Week 8–9) — COMPLETED ✅

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
