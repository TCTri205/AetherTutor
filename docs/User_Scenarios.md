# Kịch Bản Sử Dụng (User Scenarios)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 5, 2026
> **Status:** Active (In-depth Learning Focus)

---

Tài liệu này chi tiết hóa cách thức AetherTutor hỗ trợ người dùng đạt được 3 mục tiêu: **Học Sâu**, **Học Rộng** và **Hiểu Đầy Đủ**, lấy chủ đề **"Trí tuệ nhân tạo (AI)"** làm ví dụ xuyên suốt.

---

## 0. Kịch bản Khởi đầu: "Lần đầu nạp liệu" (Onboarding)

**Người dùng:** Một sinh viên lần đầu sử dụng hệ thống để học về AI.

### Luồng tương tác (Onboarding)

1. **Ingest:** Người dùng tải lên file PDF "Lịch sử và Tổng quan về AI".
2. **Processing:** **Researcher Agent** hiển thị tiến trình: trích xuất 50 thực thể (entities) và 120 mối quan hệ (relations).
3. **Orienting:** Hệ thống gợi ý: "Chào bạn! Tôi đã xây dựng xong Knowledge Graph. Bạn muốn bắt đầu bằng việc hiểu bản chất Neural Networks hay khám phá tác động của AI tới xã hội?".

## 1. Chinh phục Bản chất: "Học Sâu" (Deep Learning Mastery)

**Mục tiêu:** Hiểu rõ cơ chế **Neural Networks** từ gốc rễ, không dừng lại ở định nghĩa khô khan.

### Luồng tương tác (Combo Hệ thống/Lý luận)

1. **Socratic Dialogue:** Người dùng yêu cầu giải thích về "Backpropagation".
2. **Mental Model:** **Socratic Tutor** không đưa ra định nghĩa ngay mà hỏi: "Bạn hãy tưởng tượng mình đang điều chỉnh các nút vặn trên một chiếc máy để output khớp với kỳ vọng. Bạn sẽ làm thế nào để biết nút nào cần vặn nhiều hơn?".
3. **Gap Detection:** Khi người dùng bối rối về "Gradient Descent", Agent nhận diện đây là lỗ hổng toán học và đề xuất: "Tôi thấy bạn gặp khó khăn với khái niệm đạo hàm. Chúng ta có nên tóm tắt nhanh phần Calculus trước khi quay lại không?".
4. **Feynman Test:** Sau khi thảo luận, Agent yêu cầu: "Bây giờ, hãy giải thích Backpropagation cho một đứa trẻ 10 tuổi". Người dùng giải thích, Agent phản hồi những điểm còn chưa chuẩn xác.

## 2. Kết nối Tri thức Đa ngành: "Học Rộng" (Broad Learning)

**Mục tiêu:** Thấy được mối liên hệ giữa kỹ thuật AI và các lĩnh vực khác như **Đạo đức & Nghệ thuật**.

### Luồng tương tác (Combo Sáng tạo/Media)

1. **Multi-hop Query:** Người dùng hỏi: "Định kiến trong dữ liệu (Data Bias) ảnh hưởng thế nào đến các tác phẩm nghệ thuật do AI tạo ra?".
2. **Cross-doc Retrieval:** **Researcher Agent** sử dụng **LightRAG** để kết nối tri thức từ tài liệu "Kỹ thuật AI" với một bài báo về "Triết học Đạo đức" trong kho dữ liệu của người dùng.
3. **Discovery:** Hệ thống chỉ ra mối liên hệ ngầm: "Thuật toán tối ưu hóa (Technical) có thể vô tình khuếch đại các khuôn mẫu xã hội (Social) vì nó luôn tìm điểm cực tiểu của hàm mất mát trên dữ liệu lịch sử".
4. **Zettelkasten:** Người dùng tạo ghi chú: "Sự nguy hiểm của hàm mục tiêu (Objective Function)". Hệ thống tự động gợi ý liên kết tới ghi chú "Chủ nghĩa Công lợi" đã có trước đó.

## 3. Hệ thống hóa & Ghi nhớ: "Hiểu Đầy Đủ" (Holistic Mastery)

**Mục tiêu:** Nắm vững toàn bộ lộ trình phát triển AI và không bỏ sót điểm mù kiến thức.

### Luồng tương tác (Combo Kỹ thuật/Logic)

1. **Panoramic View:** **Visualizer Agent** tạo một **Concept Map** (vẽ bằng Mermaid.js) hiển thị toàn bộ hệ sinh thái AI: từ Machine Learning truyền thống tới Gen-AI và AI Safety.
2. **Gap Scanning:** **Examiner Agent** quét Knowledge Graph và phát hiện: "Bạn đã nghiên cứu sâu về Transformer nhưng chưa động tới khái niệm 'AI Alignment'. Bạn có muốn làm một bài Quiz nhanh về phần này không?".
3. **Adaptive Quiz:** Hệ thống tạo một bộ câu hỏi trắc nghiệm và tự luận bao phủ 100% các thực thể then chốt trong graph.
4. **Long-term Memory:** Các câu trả lời sai được tự động chuyển thành Flashcard và lên lịch ôn tập thông qua thuật toán **SM-2**.

## 4. Bảo mật Tri thức: "Private Knowledge OS"

**Người dùng:** Một chuyên gia phân tích chiến lược doanh nghiệp đang nghiên cứu các tài liệu nội bộ về AI.

### Luồng tương tác (Bảo mật)

1. **Local Mode:** Người dùng kích hoạt chế độ "Local Only", hệ thống chuyển sang sử dụng mô hình **Ollama (Llama 3)** chạy trên máy cá nhân.
2. **Data Isolation:** Toàn bộ quá trình xây dựng Knowledge Graph và hội thoại diễn ra nội bộ, không có dữ liệu nào được gửi lên Cloud.
3. **Insight Generation:** Chuyên gia hỏi về rủi ro bảo mật của hệ thống nội bộ. AI phân tích dựa trên đặc tả kỹ thuật bí mật mà không vi phạm quy định bảo mật của công ty.

---

## 5. Vai trò của Agent trong Quy trình Học tập

| Agent | Giá trị hỗ trợ "Học sâu, rộng, đầy đủ" | Công cụ chủ chốt |
| :--- | :--- | :--- |
| **Researcher** | Kết nối tri thức đa nguồn, cung cấp ngữ cảnh chính xác. | LightRAG, Dual-level Retrieval |
| **Socratic Tutor** | Phá vỡ ảo tưởng tri thức, đào sâu bản chất vấn đề. | Feynman, Socratic Probing |
| **Visualizer** | Trực quan hóa cấu trúc, cho thấy bức tranh toàn cảnh. | Mermaid.js, Graph View |
| **Examiner** | Quét sạch điểm mù, đảm bảo ghi nhớ vĩnh viễn. | Quiz, SM-2, Flashcards |

---

> [!TIP]
> Bạn có thể chuyển đổi linh hoạt giữa các kịch bản này. Ví dụ: Sau khi "Học rộng" để thấy các mối liên hệ, bạn có thể quay lại "Học sâu" một thực thể cụ thể vừa khám phá được.
