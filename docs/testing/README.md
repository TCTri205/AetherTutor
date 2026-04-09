# 🧪 Kiểm thử (Testing)

> Hướng dẫn kiểm thử thủ công (manual testing guides) cho E2E integration và error states.

---

## 📄 Tài liệu trong thư mục này

| Tài liệu | Mô tả |
| :--- | :--- |
| [**E2E_INTEGRATION_TESTS.md**](E2E_INTEGRATION_TESTS.md) | Hướng dẫn kiểm thử End-to-End integration — 4 flows chính + error recovery scenarios. |
| [**ERROR_STATES_TESTING.md**](ERROR_STATES_TESTING.md) | Hướng dẫn kiểm thử error states UI/UX — 7 kịch bản lỗi (S8.1a-S8.1f & S8.2). |

---

## 🎯 Kiểm tra nhanh (Quick Test Checklist)

### Upload Flow
- [ ] Upload PDF <50MB → Processing → COMPLETED
- [ ] Upload PDF >50MB → Toast error
- [ ] Upload duplicate hash → Toast error

### Chat Flow
- [ ] Send message → SSE streaming → ContextChips hiển thị
- [ ] Network disconnect → ChatErrorCard → Retry works
- [ ] AI timeout (30s) → Error card → Retry works

### Graph Flow
- [ ] Navigate to Graph → Nodes/Edges hiển thị
- [ ] Click node → GraphSidebar mở ra
- [ ] Search entity → Highlight matching nodes

### Error Recovery
- [ ] File >50MB → Toast → Retry với file hợp lệ
- [ ] Network loss → Error card → Reconnect → Retry
- [ ] Document deletion → Redirect + toast

---

## 📊 Performance Targets

| Metric | Target |
|--------|--------|
| First Meaningful Paint | < 1.5s |
| Graph render (50 nodes) | < 500ms |
| SSE first chunk | < 3s |
| Document processing (10 pages) | < 30s |
| Query response | < 3s |
| Memory usage (peak) | < 2GB |

---

## 🔗 Liên kết liên quan

- [Đặc tả Cốt lõi](../core/README.md)
- [Thiết kế & UX](../design/README.md)
- [Kế hoạch triển khai](../plans/README.md)
- [Báo cáo & Lộ trình](../reports/README.md)
- [Documentation Hub](../README.md)

---
© 2026 AetherTutor Team
