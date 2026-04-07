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

AetherTutor sử dụng **Ma trận Trách nhiệm Tài liệu** để đảm bảo tính nhất quán và loại bỏ sự chồng chéo thông tin. Mỗi tài liệu đóng vai trò là "Single Source of Truth" cho một lĩnh vực cụ thể.

| Tài liệu | Trách nhiệm chính (Single Source of Truth) |
| :--- | :--- |
| [**UI_UX_Design_Spec.md**](UI_UX_Design_Spec.md) | Thiết kế giao diện, Design System, trải nghiệm người dùng. |
| [**Technical_Spec.md**](Technical_Spec.md) | Tech Stack, kiến trúc tổng thể và các AI Pipeline logic cốt lõi. |
| [**Architecture.md**](Architecture.md) | Sơ đồ luồng, Agent orchestration và giao thức MCP. |
| [**API_Specifications.md**](API_Specifications.md) | Đặc tả chi tiết các REST Endpoints (không để ở file khác). |
| [**LightRAG_Implementation.md**](LightRAG_Implementation.md) | **Tất cả mã nguồn ví dụ**, thuật toán và logic Graph/RAG chuyên sâu. |
| [**MVP_Implementation_Plan.md**](MVP_Implementation_Plan.md) | Checklist thực thi, các Phase triển khai và Timeline chi tiết. |
| [**Data_Model.md**](Data_Model.md) | Thiết kế Schema DB, Vector Store và Graph Storage. |
| [**Database.md**](Database.md) | Hạ tầng cơ sở dữ liệu (Docker, Resource Optimization, Connection). |
| [**Roadmap.md**](Roadmap.md) | Tầm nhìn dài hạn và các cột mốc quan trọng (Milestones). |
| [**REFACTORING.md**](REFACTORING.md) | Chi tiết cải tiến code quality, performance, testing (v0.1.1). |

---

### 📂 Lộ trình & Kịch bản

- [**Lộ trình Phát triển (Roadmap.md)**](Roadmap.md): Quản lý toàn bộ Timeline (Quý/Tuần) và Chỉ số thành công (Success Criteria).
- [**Kịch bản sử dụng (User_Scenarios.md)**](User_Scenarios.md): Các câu chuyện sử dụng thực tế và luồng tương tác của Agent.

### 📂 Đặc tả Kỹ thuật & Thực thi

- [**Đặc tả Kỹ thuật (Technical_Spec.md)**](Technical_Spec.md): Chi tiết Tech Stack MVP, AI Pipeline và chiến lược Prompt Engineering.
- [**Kiến trúc hệ thống (Architecture.md)**](Architecture.md): Sơ đồ điều phối Agentic Workflow và giao thức MCP.
- [**Cấu hình Hạ tầng DB (Database.md)**](Database.md): Cách thiết lập PostgreSQL trên Docker tối ưu tài nguyên.
- [**Kế hoạch thực thi (MVP_Implementation_Plan.md)**](MVP_Implementation_Plan.md): Danh sách các đầu việc (Checklist) chi tiết cho đội ngũ phát triển.
- [**LightRAG Implementation (LightRAG_Implementation.md)**](LightRAG_Implementation.md): Deep-dive thuật toán, cấu trúc Graph và **Mã nguồn ví dụ chi tiết**.

### 📂 Dữ liệu & Quy chuẩn

- [**API Specifications (API_Specifications.md)**](API_Specifications.md): Đặc tả các Endpoints, tham số và ví dụ JSON (MVP Core).
- [**Data Model & Schema (Data_Model.md)**](Data_Model.md): Thiết kế DB, Vector Store và Graph Storage.
- [**Hướng dẫn đóng góp (Contributing.md)**](Contributing.md): Quy chuẩn mã nguồn và quy trình làm việc.
- [**Tài liệu Refactoring (REFACTORING.md)**](REFACTORING.md): Chi tiết các cải tiến code quality, performance và testing (v0.1.1).

### 📂 Hạ tầng & Tương lai (Future Ops)
*(Nằm trong thư mục `future_ops/`)*
- [API Full Specification](future_ops/API_Full_Spec.md), [Deployment](future_ops/Deployment_Architecture.md), [Monitoring](future_ops/Monitoring_Observability.md), v.v.

---
© 2026 AetherTutor Team. Dự án đang trong giai đoạn R&D tập trung vào lõi Algorithm và UX.
