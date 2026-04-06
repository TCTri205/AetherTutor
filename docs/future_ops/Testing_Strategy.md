# Testing Strategy (Future Plan)

Tài liệu này xác định các tiêu chuẩn kiểm thử của dự án AetherTutor.

---

## 1. Unit Testing

- **Framework:** `pytest` cho Python backend.
- **Agent Testing:** Mocking AI responses để kiểm tra logic hội thoại.

## 2. Integration Testing

- **API Testing:** Sử dụng `httpx` hoặc `Postman` để kiểm tra các luồng API.
- **RAG Consistency:** Kiểm tra kết quả truy xuất (Retrieval) có khớp với dữ liệu đầu vào.

## 3. End-to-End (E2E) Testing

- **Framework:** `Playwright` hoặc `Cypress`.
- **User Journeys:** Đảm bảo luồng học tập từ lúc nạp tài liệu đến khi nhận sơ đồ và ôn tập flashcard diễn ra trơn tru.

## 4. AI-Specific Testing

- **Golden Sets:** Bộ câu hỏi và câu trả lời mẫu để đánh giá chất lượng Agent.
- **Hallucination Detection:** Kiểm soát lỗi AI tự bịa kiến thức (Hallucination).

---
> [!NOTE]
> Giai đoạn này chỉ cần Unit tests cho logic code cơ bản và các script kiểm tra thủ công.
