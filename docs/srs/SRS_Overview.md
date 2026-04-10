# Software Requirements Specification (SRS) — Tổng Quan

> **Document Owner:** AetherTutor Team
> **Created:** April 10, 2026
> **Version:** 1.0
> **Status:** Active (MVP Phase)
> **Source of Truth:** Đây là tài liệu SRS CHÍNH, đóng vai trò "Context Anchor" cho mọi yêu cầu AI code.

---

## 0. Hướng Dẫn Sử Dụng SRS Này (Cho Vibe Coding)

### Mục Đích
Bộ SRS này được thiết kế tối ưu cho **AI-assisted development**, tập trung vào 3 trụ cột:
1. **Business Rules** — Luật chơi bất biến
2. **User Flows** — Luồng dữ liệu end-to-end
3. **Module Contracts** — Interface definitions

### Cách Dùng Khi Prompt AI
```
Trước khi yêu cầu AI code cho Module X:
1. AI đọc file này (SRS_Overview.md) để nắm context tổng thể
2. AI đọc Business_Rules.md để nắm luật bất biến
3. AI đọc Module_Contracts.md để nắm input/output của module cần code
4. AI đọc User_Flows.md để nắm luồng người dùng liên quan
```

### Quan Hệ Với Tài Liệu Hiện Có
| Tài liệu SRS | Tài liệu hiện có trong docs/ | Quan hệ |
|---|---|---|
| `SRS_Overview.md` (file này) | `core/Architecture.md`, `core/Features.md` | Tổng hợp + bổ sung Business Rules |
| `Business_Rules.md` | **KHÔNG CÓ** — hoàn toàn mới | Định nghĩa luật chơi bất biến |
| `User_Flows.md` | `design/User_Scenarios.md` | Chi tiết hóa thành flowchart/data flow |
| `Module_Contracts.md` | `core/API_Specifications.md` | Mở rộng sang internal service contracts |

---

## 1. Giới Thiệu

### 1.1 Mục Đích Hệ Thống
**AetherTutor** là AI-Powered Learning OS giúp người học đạt **"Hiểu Đầy Đủ"** thông qua:
- Xây dựng **Knowledge Graph** từ tài liệu cá nhân (PDF, Web, YouTube)
- Tương tác **Socratic** với 4 Agent chuyên biệt
- Ôn tập thông minh với thuật toán **SM-2 Spaced Repetition**
- Quản lý tri thức theo phương pháp **Zettelkasten**

### 1.2 Đối Tượng Người Dùng
| Persona | Mô tả | Use Case Chính |
|---|---|---|
| **Student** | Sinh viên, người tự học | Upload tài liệu → Chat Socratic → Ôn tập Flashcard |
| **Researcher** | Nghiên cứu sinh, chuyên gia | Xây dựng Knowledge Graph → Multi-hop Query → Visualize |
| **Professional** | Chuyên gia phân tích | Local Mode (Ollama) → Private Knowledge OS |

### 1.3 Phạm Vi MVP

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Document Upload (PDF) | ✅ Trong scope | Processing qua background worker |
| LightRAG Knowledge Graph | ✅ Trong scope | Entity extraction, dual-level retrieval |
| Socratic Chat | ✅ Trong scope | Feynman technique, graph-aware |
| Flashcard + SM-2 | ✅ Trong scope | Auto-generate từ graph entities |
| Quiz Generation | ✅ Trong scope | Multi-hop questions từ graph |
| Note Taking (Zettelkasten) | ✅ Trong scope | Atomic notes + backlinks |
| Knowledge Graph View | ✅ Trong scope | React Flow visualization |
| Authentication / JWT | ❌ Post-MVP | MVP: single-user local |
| Multi-user / Multi-tenancy | ❌ Post-MVP | MVP: single-user |
| OAuth / Social Login | ❌ Post-MVP | Post-MVP Phase |
| Payment / Subscription | ❌ Post-MVP | Post-MVP Phase |
| Video/Audio Processing | ❌ Post-MVP | Post-MVP Phase |
| Mobile App | ❌ Post-MVP | Responsive web only (MVP) |

---

## 2. Tổng Quan Kiến Trúc

### 2.1 High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend (React/Vite)"
        UI[User Interface]
        GraphView[Graph Viewer]
        ChatUI[Chat Interface]
        FlashcardUI[Flashcard Review]
    end

    subgraph "Backend (FastAPI)"
        API[API Gateway / Routers]
        Auth[Auth Middleware]
        Orchestrator[Parent Orchestrator]
        Workers[Background Workers ARQ]
    end

    subgraph "Services Layer"
        LLM[LLM Service]
        Embedding[Embedding Service]
        GraphService[Graph Service]
        SM2[SM-2 Service]
    end

    subgraph "Agents"
        Researcher[Researcher Agent]
        Socratic[Socratic Tutor Agent]
        Visualizer[Visualizer Agent]
        Examiner[Examiner Agent]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        Chroma[(ChromaDB)]
        Redis[(Redis)]
        NetX[NetworkX Graph]
    end

    UI --> API
    GraphView --> API
    ChatUI --> API
    FlashcardUI --> API

    API --> Auth
    API --> Orchestrator
    API --> Workers

    Orchestrator --> Researcher
    Orchestrator --> Socratic
    Orchestrator --> Visualizer
    Orchestrator --> Examiner

    Researcher --> GraphService
    Socratic --> LLM
    Visualizer --> GraphService
    Examiner --> SM2

    Workers --> LLM
    Workers --> Embedding
    Workers --> GraphService

    LLM --> PG
    Embedding --> Chroma
    GraphService --> NetX
    SM2 --> PG
```

### 2.2 Tech Stack Summary

| Layer | Technology | Version |
|---|---|---|
| Backend | Python + FastAPI | Python 3.11, FastAPI 0.115+ |
| Frontend | React + TypeScript + Vite | React 18+ |
| Database | PostgreSQL + asyncpg | PostgreSQL 16 |
| Vector DB | ChromaDB (HTTP mode) | ChromaDB 0.5.0 |
| Cache/Queue | Redis + ARQ | Redis 7 |
| Graph | NetworkX (in-memory) | Latest |
| LLM | OpenAI API / Ollama | Configurable |
| ORM | SQLAlchemy 2.0 (async) | 2.0+ |
| Migration | Alembic | Latest |
| Testing | pytest + pytest-asyncio | Latest |

---

## 3. Business Rules — Tổng Quan Cốt Lõi

> [!IMPORTANT]
> Đây là danh sách rút gọn. Chi tiết đầy đủ tại **`Business_Rules.md`**.

### BR-001: User Data Isolation (BẤT BIẾN)
**MỌI dữ liệu phải được隔离 (isolate) theo `user_id`. Dữ liệu User A KHÔNG BAO GIỜ hiển thị cho User B.**

### BR-002: Document Processing Pipeline (BẤT BIẾN)
**Document PHẢI trải qua đủ 7 bước tuần tự theo State Machine.** Bỏ bước = FAIL.

**7 bước BẮT BUỘC (khớp Data_Model State Machine):**

| Bước | State | Input | Output |
|---|---|---|---|
| 1 | `pending` | File PDF/URL upload | Document record created |
| 2 | `processing` | Worker picks up task | Status update |
| 3 | `chunking` | Raw text extracted | Chunks (500 chars, 50 overlap) |
| 4 | `entity_extraction` | Chunks | JSON entities + relations từ spaCy + LLM (hybrid) |
| 5 | `graph_construction` | Entities + Relations | NetworkX graph built |
| 6 | `embedding_generation` | Chunks | Vector embeddings từ LLM |
| 7 | `completed` | All storage success | Document ready (PostgreSQL + ChromaDB + Graph) |

**Failure Path:** Bất kỳ bước nào fail → `failed` state với error_message.

**Chi tiết đầy đủ tại:** [Business_Rules.md#br-002](Business_Rules.md#br-002-document-processing-pipeline)

### BR-003: Graph Construction Requires LLM (BẤT BIẾN)
**Knowledge Graph KHÔNG được xây dựng nếu LLM service không phản hồi hoặc trả về lỗi.**

### BR-004: Flashcard Generation Rule (BẤT BIẾN)
**Flashcard chỉ được sinh từ graph entities/relations đã được người dùng xác nhận hoặc đã hoàn thành processing.**

### BR-005: SM-2 Scheduling Rule (BẤT BIẾN)
**Flashcard chỉ xuất hiện để ôn tập khi `sm2_next_review <= NOW()`. Không cho phép override thủ công trừ khi user explicitly yêu cầu.**

### BR-006: Socratic Response Rule (BẤT BIẾN)
**Socratic Tutor KHÔNG được đưa ra câu trả lời trực tiếp. PHẢI đặt câu hỏi gợi mở trước, chỉ giải thích khi user đã cố gắng trả lời ít nhất 1 lần.**

### BR-007: Quiz Generation Rule (BẤT BIẾN)
**Quiz PHẢI bao phủ ít nhất 80% các entities có `degree > 3` trong graph. Câu hỏi PHẢI có explanation cho đáp án đúng.**

### BR-008: Local Mode Rule (BẤT BIẾN)
**Khi user kích hoạt Local Mode, KHÔNG dữ liệu nào được gửi đến Cloud LLM. Mọi request PHẢI route sang Ollama endpoint.**

### BR-009: Note Backlink Rule (BẤT BIẾN)
**Khi tạo note mới, hệ thống PHẢI quét nội dung để tìm khái niệm trùng với entities trong graph và gợi ý backlinks.**

### BR-010: Error Recovery Rule (BẤT BIẾN)
**Mọi background task thất bại PHẢI được retry tối đa 3 lần với exponential backoff. Sau 3 lần vẫn fail → lưu error message và notify user.**

---

## 4. Module Dependencies Map

```mermaid
graph LR
    subgraph "Core Modules"
        DOC[Document Module]
        GRAPH[Graph Module]
        CHAT[Chat Module]
    end

    subgraph "Learning Modules"
        FLASH[Flashcard Module]
        QUIZ[Quiz Module]
        NOTE[Note Module]
    end

    subgraph "Infrastructure"
        LLM[LLM Service]
        EMB[Embedding Service]
        WORKER[Background Worker]
    end

    DOC -->|depends on| LLM
    DOC -->|depends on| EMB
    DOC -->|depends on| WORKER
    DOC -->|produces| GRAPH

    GRAPH -->|depends on| LLM
    GRAPH -->|feeds| CHAT
    GRAPH -->|feeds| FLASH
    GRAPH -->|feeds| QUIZ
    GRAPH -->|feeds| NOTE

    CHAT -->|depends on| LLM
    FLASH -->|depends on| SM2
    QUIZ -->|depends on| LLM
    NOTE -->|depends on| GRAPH
```

### Dependency Rules

| Rule | Mô tả |
|---|---|
| **DEP-001** | Document Module PHẢI hoàn thành processing trước khi Graph Module sẵn sàng |
| **DEP-002** | Graph Module PHẢI có entities trước khi Flashcard/Quiz/Note modules hoạt động |
| **DEP-003** | Chat Module CÓ THỂ hoạt động độc lập nếu không có document (general chat) |
| **DEP-004** | LLM Service là dependency của GẦN NHƯ mọi module — cần health check trước khi xử lý |
| **DEP-005** | Background Worker là async — API trả về 202 Accepted ngay, client polling status |

---

## 5. User Roles & Permissions (MVP)

> [!NOTE]
> MVP là single-user local nên chưa có phân quyền phức tạp. Bảng này cho Post-MVP reference.

| Role | Permissions | Scope |
|---|---|---|
| **Owner (MVP)** | Full access: Upload, Chat, Graph, Flashcards, Quiz, Notes, Settings | Single user |
| **User (Post-MVP)** | Upload, Chat, Graph, Flashcards, Quiz, Notes | Own data only |
| **Admin (Post-MVP)** | User management, System monitoring, Model configuration | System-wide |
| **Enterprise (Post-MVP)** | Team management, Shared knowledge graphs, Usage analytics | Team scope |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Yêu cầu | Ngưỡng | Cách đo |
|---|---|---|
| API Response Time | < 500ms (P95) cho read operations | Slow queries logging |
| Chat Response Time | < 3s cho first token (streaming) | Time to First Byte |
| Document Processing | < 5 phút cho PDF 50 trang | Worker timeout |
| Graph Query | < 2s cho graph với 10K entities | Query benchmark |
| Flashcard Review | < 200ms load time | Frontend performance |

### 6.2 Scalability

| Thành phần | Giới hạn MVP | Post-MVP Target |
|---|---|---|
| Documents per user | 100 | 10,000+ |
| Entities per graph | 5,000 | 100,000+ |
| Chat messages per session | 500 | Unlimited (archive old) |
| Concurrent users | 1 (single-user) | 1,000+ |

### 6.3 Reliability

| Yêu cầu | Target |
|---|---|
| Uptime (local dev) | Best effort |
| Data durability | 100% (PostgreSQL WAL + Volume backup) |
| Task retry success rate | > 95% (3 retries) |
| Graceful degradation | LLM down → queue requests, notify user |

### 6.4 Security (MVP)

| Yêu cầu | Implementation |
|---|---|
| API Key storage | Environment variables, NOT in code |
| Password hashing | bcrypt (Post-MVP) |
| Data encryption at rest | PostgreSQL TDE / Disk encryption |
| Row-level isolation | `WHERE user_id = :current_user_id` mọi query |
| CORS | Restrict to frontend domain (production) |
| Rate limiting | SlowAPI per IP (MVP), per user (Post-MVP) |

---

## 7. Glossary (Thuật Ngữ)

| Thuật ngữ | Định nghĩa |
|---|---|
| **Knowledge Graph** | Đồ thị tri thức với nodes (entities) và edges (relations) trích xuất từ tài liệu |
| **Entity** | Một khái niệm, thuật ngữ, người, quy trình được trích xuất từ document |
| **Relation** | Mối quan hệ có hướng giữa 2 entities (vd: "causes", "part_of") |
| **Dual-level Retrieval** | LightRAG retrieval: Level 1 (entity similarity) + Level 2 (concept traversal) |
| **Socratic Tutor** | Agent sử dụng phương pháp đặt câu hỏi gợi mở thay vì đưa câu trả lời trực tiếp |
| **Feynman Technique** | Yêu cầu user giải thích lại khái niệm bằng ngôn ngữ đơn giản để kiểm tra hiểu biết |
| **SM-2** | SuperMemo-2 algorithm tính toán thời điểm ôn tập tối ưu |
| **Zettelkasten** | Phương pháp ghi chú với atomic notes và backlinks |
| **Combo** | Bộ công cụ Agent phối hợp theo kịch bản học tập (vd: Researcher → Visualizer) |
| **Local Mode** | Chế độ sử dụng Ollama local, không gửi dữ liệu lên cloud |
| **Background Worker** | ARQ worker xử lý tác vụ nặng (entity extraction, graph building) bất đồng bộ |
| **Context Anchor** | Tài liệu SRS dùng làm "neo ngữ cảnh" cho AI khi code |

---

## 8. Tài Liệu Liên Quan

| Tài liệu | Đường dẫn | Mục đích |
|---|---|---|
| SRS Overview | `docs/srs/SRS_Overview.md` (file này) | Tổng quan + Business Rules summary |
| Business Rules | `docs/srs/Business_Rules.md` | **Chi tiết đầy đủ** mọi luật nghiệp vụ |
| User Flows | `docs/srs/User_Flows.md` | End-to-end flows với mermaid diagrams |
| Module Contracts | `docs/srs/Module_Contracts.md` | Interface definitions cho từng module |
| Architecture | `docs/core/Architecture.md` | Kiến trúc kỹ thuật chi tiết |
| Data Model | `docs/core/Data_Model.md` | Schema database chi tiết |
| API Spec | `docs/core/API_Specifications.md` | API endpoints |
| Features | `docs/core/Features.md` | Danh sách tính năng |

---

> [!IMPORTANT]
> **Tài liệu này là LIVING DOCUMENT.** Cập nhật khi có yêu cầu mới hoặc thay đổi kiến trúc.
> Mọi thay đổi PHẢI được review trước khi merge.

---
© 2026 AetherTutor Team. Created: April 10, 2026
