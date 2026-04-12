# AetherTutor: Hệ Điều Hành Học Tập (Learning OS)

Chào mừng bạn đến với **AetherTutor**, một hệ sinh thái học tập dựa trên AI được thiết kế để biến tri thức từ lý thuyết thành khả năng ứng dụng thực tế thông qua các kỹ thuật sư phạm tiên tiến và kiến trúc Agent thông minh.

---

## 1. Tầm nhìn dự án

AetherTutor không chỉ là một ứng dụng ghi chú hay học tập thông thường. Đây là một **Hệ điều hành học tập (Learning OS)** nhằm giải quyết các bài toán:

- **Quá tải thông tin:** Giúp người học chắt lọc và "tiêu hóa" tri thức một cách khoa học.
- **Lỗ hổng kiến thức:** Phát hiện những điểm chưa hiểu rõ thông qua phản biện Socratic.
- **Ghi nhớ kém:** Tự động hóa việc ôn tập dựa trên các thuật toán ghi nhớ lâu dài.
- **Thiếu trực quan:** Chuyển đổi linh hoạt giữa ngôn ngữ và hình ảnh để tăng hiệu quả xử lý của não bộ.

## 2. Triết lý cốt lõi

Hệ thống vận hành dựa trên sự kết hợp giữa các thuyết học tập hiện đại và công nghệ AI Agentic:

- **Active Learning (Học tập chủ động):** Không chỉ đọc thụ động mà phải tương tác, giải thích và thực hành.
- **Atomic Knowledge (Kiến thức nguyên tử):** Chia nhỏ thông tin để tối ưu hóa tải nhận thức.
- **Agentic Ecosystem:** Điều phối các chuyên gia AI (Socratic Tutor, Researcher, Visualizer) để hỗ trợ từng khâu.

---

## 3. Hệ thống Tài liệu (Documentation Hub)

AetherTutor sử dụng **Ma trận Trách nhiệm Tài liệu** để đảm bảo tính nhất quán và loại bỏ sự chồng chéo thông tin. Tài liệu được tổ chức theo cấu trúc phân loại rõ ràng:

### 📖 Đặc tả Cốt lõi (`core/`)

> Single Source of Truth cho kiến trúc, kỹ thuật và dữ liệu.

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**Architecture.md**](core/Architecture.md) | Sơ đồ luồng, Agent orchestration và giao thức MCP. |
| [**Technical_Spec.md**](core/Technical_Spec.md) | Tech Stack, kiến trúc tổng thể và các AI Pipeline logic cốt lõi. |
| [**Service_Catalog.md**](core/Service_Catalog.md) | 🆕 **25 backend services** — Methods, dependencies, business rules, error handling. |
| [**API_Specifications.md**](core/API_Specifications.md) | Đặc tả chi tiết 115 REST Endpoints. |
| [**Data_Model.md**](core/Data_Model.md) | Thiết kế Schema DB (26 tables), Vector Store và Graph Storage. |
| [**Database.md**](core/Database.md) | Hạ tầng cơ sở dữ liệu (Docker, Resource Optimization, Connection). |
| [**Features.md**](core/Features.md) | Danh sách tính năng và trụ cột chức năng. |

### 🎨 Thiết kế & Trải nghiệm (`design/`)

> Tài liệu về UI/UX, kịch bản người dùng và phương pháp sư phạm.

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**UI_UX_Design_Spec.md**](design/UI_UX_Design_Spec.md) | Thiết kế giao diện, Design System, trải nghiệm người dùng. |
| [**User_Scenarios.md**](design/User_Scenarios.md) | Kịch bản sử dụng thực tế và luồng tương tác của Agent. |
| [**Methodology.md**](design/Methodology.md) | Phương pháp học tập và combo công cụ theo lĩnh vực. |

### 📋 Software Requirements Specification (`srs/`)

> **Context Anchors** cho AI-assisted development. Đọc trước khi code.

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**SRS_Overview.md**](srs/SRS_Overview.md) | Tổng quan hệ thống, scope MVP, business rules summary, module dependencies map. |
| [**Business_Rules.md**](srs/Business_Rules.md) | **17 luật chơi bất biến** (🔴 BẤT BIẾN, 🟡 CỐ ĐỊNH, 🟢 KHUYẾN NGHỊ). |
| [**User_Flows.md**](srs/User_Flows.md) | **8 end-to-end user flows** với mermaid diagrams, input/output, error handling. |
| [**Module_Contracts.md**](srs/Module_Contracts.md) | **10 module contracts** — interface definitions, input/output contracts, error contracts. |

### 📋 Kế hoạch Triển khai (`plans/`)

> Implementation plans, sprint checklists và audit findings.

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**MVP_Implementation_Plan.md**](plans/2026-04-08_mvp_implementation_lightrag.md) | Checklist thực thi Stage 1 (MVP), các Sprint 1-6 và Timeline chi tiết. |
| [**Stage2_Implementation_Plan.md**](plans/2026-04-08_stage2_intelligence_memory.md) | Kế hoạch Stage 2 — Intelligence & Memory (10 tuần). |
| [**Stage3_Implementation_Plan.md**](plans/2026-04-10_hybrid_entity_extraction.md) | Hybrid Entity Extraction + Obsidian Integration. |
| [**Stage4_Implementation_Plan.md**](plans/2026-04-12_stage4_interactive_ux_collaboration.md) | Interactive UX, Collaboration, PWA, Security (Phase 1 done). |
| [**Stage5_Implementation_Plan.md**](plans/2026-04-12_stage5_intelligence_maturity_launch.md) | Intelligence Maturity & Launch Prep (Draft). |
| [**Audit_Findings_Plan.md**](plans/2026-04-08_audit_findings_implementation_plan.md) | Audit findings & polish plan cho Final Polish. |

### 📊 Báo cáo & Lộ trình (`reports/`)

> Báo cáo hoàn thành, checklist launch và roadmap theo dõi milestones.

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**Roadmap.md**](2026-04-07_product_roadmap.md) | Tầm nhìn dài hạn, cột mốc quan trọng (Milestones) và Success Criteria. |
| [**Stage2_Completion.md**](2026-04-09_stage2_completion.md) | Báo cáo hoàn thành Sprint 5 — Frontend Interface. |
| [**Refactoring_Log.md**](2026-04-08_refactoring_log.md) | Báo cáo refactoring v0.1.1 — Code quality, performance, testing. |
| [**Stage3_Final_Summary.md**](2026-04-12_stage3_final_summary.md) | Stage 3 Core Complete (Sprint 8+9). |
| [**Stage4_Phase1_Report.md**](2026-04-12_stage4_phase1_implementation_report.md) | Stage 4 Phase 1 Complete (Sprint 14+19). |
| [**LAUNCH_CHECKLIST.md**](2026-04-07_mvp_launch_checklist.md) | Checklist kiểm tra trước khi launch MVP v0.1. |

### 🧪 Kiểm thử (`testing/`)

> Hướng dẫn kiểm thử thủ công (manual testing guides).

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**E2E_INTEGRATION_TESTS.md**](testing/E2E_INTEGRATION_TESTS.md) | Hướng dẫn kiểm thử E2E integration (4 flows + error recovery). |
| [**ERROR_STATES_TESTING.md**](testing/ERROR_STATES_TESTING.md) | Hướng dẫn kiểm thử error states UI/UX (S8.1a-S8.1f & S8.2). |

### 🔮 Hạ tầng & Tương lai (`future_ops/`)

> Tài liệu cho các tính năng và hạ tầng tương lai.

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**API_Full_Spec.md**](future_ops/API_Full_Spec.md) | ⚠️ **DEPRECATED** — Xem [`core/API_Specifications.md`](core/API_Specifications.md) cho LightRAG endpoints. |
| [**Deployment_Architecture.md**](future_ops/Deployment_Architecture.md) | Kiến trúc triển khai production. |
| [**Monitoring_Observability.md**](future_ops/Monitoring_Observability.md) | Chiến lược monitoring và observability. |
| [**Risk_Assessment.md**](future_ops/Risk_Assessment.md) | Đánh giá rủi ro và mitigation strategies. |
| [**Security_Privacy.md**](future_ops/Security_Privacy.md) | Chính sách bảo mật và privacy compliance. |
| [**Testing_Strategy.md**](future_ops/Testing_Strategy.md) | Chiến lược kiểm thử tổng thể. |

### ⚙️ Vận hành (`ops/`)

> Runbooks và operational guides.

| Tài liệu | Trách nhiệm chính |
| :--- | :--- |
| [**Worker_Runbook.md**](ops/Worker_Runbook.md) | 🆕 ARQ Worker configuration, task registry, error handling, monitoring, deployment. |

### 🤝 Hướng dẫn Đóng góp

- [**Contributing.md**](Contributing.md): Quy chuẩn mã nguồn, quy trình PR và code review.

### 📚 LightRAG Implementation

- [**LightRAG_Implementation.md**](LightRAG_Implementation.md): Deep-dive thuật toán, cấu trúc Graph và **Mã nguồn ví dụ chi tiết**.

---

## 4. Quick Navigation

### Bắt đầu nhanh
- 🚀 **New to AetherTutor?** → Đọc [Features.md](core/Features.md) để hiểu tính năng
- 🏗️ **Want to understand architecture?** → Đọc [Architecture.md](core/Architecture.md)
- 📝 **Ready to code with AI?** → Đọc bộ [SRS](srs/SRS_Overview.md) TRƯỚC KHI prompt AI
- 💻 **Ready to develop?** → Xem [Stage 1 Plan](plans/2026-04-08_mvp_implementation_lightrag.md) | [Stage 4 Plan](plans/2026-04-12_stage4_interactive_ux_collaboration.md)

### Dành cho Developers
- 📐 **Tech Stack** → [Technical_Spec.md](core/Technical_Spec.md) *(coming soon)*
- 📝 **SRS (AI Coding)** → [srs/](srs/) — Business Rules, User Flows, Module Contracts
- 🔌 **API Reference** → [API_Specifications.md](core/API_Specifications.md)
- 🗄️ **Database Setup** → [Database.md](core/Database.md)
- 🤝 **Contributing** → [Contributing.md](Contributing.md)

### Dành cho QA/Testing
- 🧪 **E2E Testing** → [testing/E2E_INTEGRATION_TESTS.md](testing/E2E_INTEGRATION_TESTS.md)
- ❌ **Error States** → [testing/ERROR_STATES_TESTING.md](testing/ERROR_STATES_TESTING.md)
- ✅ **Launch Checklist** → [reports/2026-04-07_mvp_launch_checklist.md](reports/2026-04-07_mvp_launch_checklist.md)

### Dành cho Project Management
- 📊 **Roadmap** → [reports/2026-04-07_product_roadmap.md](reports/2026-04-07_product_roadmap.md)
- 📋 **Sprint Plans** → [plans/](plans/)
- 📈 **Completion Reports** → [reports/](reports/)

> [!NOTE]
> **Stage Progression:** Stage 1-2 ✅ | Stage 3 Core ✅ | Stage 4 Phase 1 ✅ | Stage 4 Phase 2-3 ⏸️ | Stage 5 ⏸️
> Xem [Stage→Version Mapping](reports/2026-04-07_product_roadmap.md#mapping-stage--version) trong Roadmap.

---
© 2026 AetherTutor Team. Dự án đang trong giai đoạn R&D tập trung vào lõi Algorithm và UX.
