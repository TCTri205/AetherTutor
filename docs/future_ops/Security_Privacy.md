# Security & Privacy (Future Plan)

Tài liệu này xác định các tiêu chuẩn bảo mật cho dự án AetherTutor.

---

## 1. Data Encryption

- **At Rest:** AES-256 cho lưu trữ cơ sở dữ liệu và tệp tin PDF/Media.
- **In Transit:** TLS 1.3 cho toàn bộ luồng truyền tải dữ liệu.

## 2. Authentication & Authorization

- **JWT (JSON Web Tokens):** Bảo mật cho các phiên truy cập API.
- **RBAC (Role-Based Access Control):** Kiểm soát quyền hạn truy cập tài liệu và ghi chú.

## 3. Privacy Compliance (GDPR/CCPA)

- **Data Erasure:** Hỗ trợ xóa hoàn toàn dữ liệu người dùng khi có yêu cầu.
- **Data Portability:** Xuất dữ liệu dưới định dạng chuẩn (JSON/PDF).

## 4. AI Security

- **Prompt Injection Defense:** Ngăn chặn và làm sạch các prompt lạ độc hại.
- **Data Anonymization:** Ẩn các thông tin nhạy cảm trước khi gửi đến các mô hình LLM từ xa.

---
> [!IMPORTANT]
> AetherTutor cam kết **Quyền riêng tư tuyệt đối** thông qua tùy chọn chạy toàn bộ hệ thống cục bộ (Local).
