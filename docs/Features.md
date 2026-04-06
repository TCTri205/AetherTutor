# Danh Sách Tính Năng (Features)

AetherTutor cung cấp một bộ tính năng toàn diện để hỗ trợ quá trình nghiên cứu và học tập thông minh, tập trung vào 3 trụ cột chính.

---

## 1. Trụ cột Tương tác (Interactive Learning)

- **Feynman Chat (Socratic Tutor):** AI đóng vai người học/người mới bắt đầu để yêu cầu người dùng giải thích lại kiến thức. Giúp phát hiện "ảo tưởng về tri thức".
- **AI-Augmented Reading:** Hỗ trợ đọc tài liệu thông minh:
  - Giải thích thuật ngữ theo ngữ cảnh.
  - Phân rã khái niệm phức tạp thành các thành phần nguyên tử (Atomic components).
- **Adaptive Quiz:** Tự động tạo câu hỏi trắc nghiệm/tự luận từ tài liệu nghiên cứu để kiểm tra mức độ hiểu bài ngay lập tức.

## 2. Trụ cột Kiến trúc Tri thức (Knowledge Architecture)

- **LightRAG Knowledge Graph Base:** Hệ thống quản lý tài liệu (PDF, Web, YouTube) được chuyển đổi thành knowledge graph với entities và relations, cho phép AI trích xuất chính xác nguồn gốc tri thức và hiểu mối liên hệ giữa các concepts.
- **Bi-directional Zettelkasten:**
  - Ghi chú dạng thẻ (Atomic notes).
  - Tự động gợi ý liên kết (Backlinks) giữa các ghi chú dựa trên sự trùng lặp khái niệm.
- **Knowledge Graph View:** Trực quan hóa mạng lưới liên kết giữa các ý tưởng và tài liệu.

## 3. Trụ cột Hiệu suất Học tập (Efficiency & Memory)

- **Dual-Coding Visualization:** Tự động sinh sơ đồ (Flowchart/Mindmap) từ văn bản nghiên cứu để hỗ trợ kênh xử lý hình ảnh của não bộ.
- **Smart Spaced Repetition (SM-2):** Tích hợp thuật toán lặp lại ngắt quãng để đẩy kiến thức từ trí nhớ ngắn hạn sang dài hạn.
- **Media Ingestion Pipeline:** Chuyển đổi video bài giảng dài thành các đoạn "Micro-learning" kèm tóm tắt và câu hỏi ôn tập.

---

## Lộ trình Phát triển (MVP Roadmap)

| Tính năng | Giai đoạn | Mục tiêu |
| :--- | :--- | :--- |
| **LightRAG Core & Ingestion** | **Móng (v0.1)** | Tải tài liệu, xây dựng knowledge graph và "hỏi-đáp" cơ bản. |
| **Socratic/Feynman Chat** | **Lõi (v0.2)** | Triển khai logic hội thoại sư phạm. |
| **Basic Visualization** | **Lõi (v0.2)** | Tự động sinh sơ đồ Mermaid đơn giản. |
| **Zettelkasten & SM-2** | **Trí tuệ (v0.3)** | Quản lý ghi chú liên kết và lịch ôn tập. |
| **Media Pipeline** | **Mở rộng (v0.4)** | Xử lý video/audio phức tạp. |

---
> [!TIP]
> Các tính năng được thiết kế để hoạt động hiệp đồng. Ví dụ: Từ một tài liệu (Research), hệ thống sinh sơ đồ (Visualization), sau đó tạo ghi chú (Zettelkasten) và lên lịch ôn tập (SM-2).
