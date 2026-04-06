# Risk Assessment (Future Plan)

Tài liệu này đánh giá các rủi ro liên quan đến sự phát triển lâu dài của AetherTutor.

---

## 1. Rủi ro Kỹ thuật (Technical Risks)

- **AI Hallucinations:** AI đưa ra các thông tin sai lệch về kiến thức chuyên môn.
- **Latency:** Thời gian phản hồi của các Agent chậm làm gián đoạn luồng học tập.
- **Scalability:** Khả năng xử lý hàng loạt tài liệu đồng thời của Vector DB.

## 2. Rủi ro Dữ liệu (Data Risks)

- **Privacy Breaches:** Rò rỉ dữ liệu học tập cá nhân.
- **Data Integrity:** Lỗi trong quá trình trích xuất kiến thức (OCR, Speech-to-Text).

## 3. Rủi ro Kinh doanh (Business Risks)

- **API Costs:** Chi phí gọi mô hình LLM từ các nhà cung cấp (OpenAI, Google) tăng cao.
- **Provider Reliability:** Sự phụ thuộc vào tính sẵn sàng của các bên thứ ba.

---
> [!TIP]
> Việc triển khai các giải pháp chạy Local LLMs được coi là bước đi chiến lược quan trọng nhất để giảm rủi ro chi phí và quyền riêng tư.
