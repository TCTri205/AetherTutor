# Hướng dẫn Manual Test - Error States (S8.1a-S8.1f & S8.2)

> **Ngày tạo:** April 7, 2026
> **Người test:** AetherTutor Team
> **Mục đích:** Kiểm tra tất cả error states UI/UX sau khi implement

---

## Chuẩn bị

1. **Start Backend:**
   ```bash
   cd D:\Projects_IT\AetherTutor
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start Frontend:**
   ```bash
   cd D:\Projects_IT\AetherTutor\frontend
   npm run dev
   ```

3. **Mở browser:** `http://localhost:5173`

---

## KỊCH BẢN TEST

### **S8.1a - LLM Timeout (504 Gateway)**

**Mục tiêu:** Kiểm tra UI khi backend trả về 504 (LLM timeout)

**Cách test:**
1. Start frontend
2. **TẮT backend** (để giả lập server quá tải)
3. Upload 1 file PDF nhỏ
4. Vào Chat, gửi tin nhắn
5. Backend sẽ không phản hồi → nên thấy lỗi

**Kỳ vọng:**
- ✅ Sau 30s: Hiển thị ChatErrorCard với icon ⏰
- ✅ Title: "AI đang bận xử lý"
- ✅ Message: "AI đang bận xử lý câu hỏi của bạn — thử lại nhé."
- ✅ Button [Thử lại] hoạt động
- ✅ Button [Dùng Local Mode] disabled với tooltip "Coming soon in v2"

---

### **S8.1b - File >50MB**

**Mục tiêu:** Kiểm tra validation file size khi upload

**Cách test:**
1. Tạo file PDF giả >50MB:
   ```bash
   # Windows PowerShell
   fsutil file createnew D:\Projects_IT\AetherTutor\large_test.pdf 52428800
   ```
   (52,428,800 bytes = 50MB)

2. Mở frontend → Dashboard/Vault
3. Click "Tải lên PDF"
4. Chọn file `large_test.pdf`

**Kỳ vọng:**
- ✅ Toast error ngay lập tức: "File quá lớn (50.0MB). Giới hạn tối đa 50MB."
- ✅ File KHÔNG được thêm vào danh sách chọn
- ✅ Nếu bypass được client validation → backend trả 413 → toast: "File quá lớn (giới hạn 50MB). Hãy chọn file nhỏ hơn."

---

### **S8.1c - Scanned PDF (No Text Layer)**

**Mục tiêu:** Kiểm tra UI khi upload file PDF là ảnh scan

**Cách test:**
1. Tạo PDF từ ảnh (không có text):
   - Chụp màn hình → lưu thành ảnh PNG
   - Dùng công cụ online (như ilovepdf.com) để convert ảnh → PDF
   - HOẶC dùng file PDF scan có sẵn

2. Upload file PDF đó lên

**Kỳ vọng:**
- ✅ Backend detect scanned PDF → trả về error
- ✅ Toast error: "PDF này là ảnh scan — hệ thống không đọc được text. Hãy dùng file PDF có text layer."
- ✅ DocumentGuard hiển thị icon Scan + message phù hợp
- ✅ Document status = FAILED

---

### **S8.1d - Invalid API Key**

**Mục tiêu:** Kiểm tra UI khi API key không hợp lệ

**Cách test:**
1. Sửa file `.env` backend:
   ```
   OPENAI_API_KEY=sk-invalid-key-12345
   ```
2. Restart backend
3. Upload file PDF → Vào Chat → Gửi tin nhắn

**Kỳ vọng:**
- ✅ Backend trả về 401 Unauthorized
- ✅ ChatErrorCard hiển thị với icon 🔑
- ✅ Title: "API Key không hợp lệ"
- ✅ Message: "API Key không hợp lệ. Vui lòng kiểm tra cài đặt."
- ✅ Button [Đi đến Settings] hiển thị toast "Settings page coming soon in v2"

---

### **S8.1e - Network Failure**

**Mục tiêu:** Kiểm tra UI khi mất kết nối mạng

**Cách test Method 1 (DevTools):**
1. Mở DevTools (F12) → Network tab
2. Chọn "Offline" từ dropdown "No throttling"
3. Thử gửi tin nhắn trong Chat HOẶC reload trang

**Kỳ vọng:**
- ✅ ChatErrorCard hiển thị với icon 📡
- ✅ Title: "Mất kết nối mạng"
- ✅ Message: "Không thể kết nối đến server. Kiểm tra internet hoặc dùng Local Mode."
- ✅ Button [Thử lại] hoạt động
- ✅ Button [Dùng Local Mode] disabled

**Cách test Method 2 (Tắt WiFi):**
1. Tắt WiFi/Ethernet
2. Reload trang

**Kỳ vọng:**
- ✅ Toast error: "Mất kết nối mạng — không thể tải danh sách tài liệu"
- ✅ Các page (Dashboard, Vault) vẫn hiển thị (không crash)

---

### **S8.1f - Chat AI Không Phản Hồi (Timeout 30s)**

**Mục tiêu:** Kiểm tra timeout detection khi AI không gửi chunk nào sau 30s

**Cách test:**
1. Backend CHẠY nhưng LLM service KHÔNG hoạt động (ví dụ: OpenAI API down)
2. Upload PDF → Vào Chat
3. Gửi tin nhắn
4. Đợi 30 giây

**Kỳ vọng:**
- ✅ Sau đúng 30s: ChatErrorCard xuất hiện
- ✅ Title: "⚠️ AI không phản hồi"
- ✅ Message: "Có thể do API key không hợp lệ, mạng gián đoạn, hoặc model đang quá tải."
- ✅ Suggestion: "Thử lại sau vài giây hoặc kiểm tra cài đặt."
- ✅ Button [Thử lại] gọi lại sendMessage với message cuối
- ✅ Button [Kiểm tra Settings] hoạt động
- ✅ Message assistant hiển thị: "⚠️ AI không phản hồi — thử lại nhé."

---

### **S8.2 - Global Error Boundary**

**Mục tiêu:** Kiểm tra Error Boundary catch được React crashes

**Cách test (tạo crash nhân tạo):**
1. Tạm thời sửa `Chat.tsx`:
   ```typescript
   // Thêm dòng này vào đầu component
   if (true) throw new Error("Test crash");
   ```

2. Reload trang Chat

**Kỳ vọng:**
- ✅ KHÔNG thấy "White Screen of Death"
- ✅ FallbackError component hiển thị
- ✅ Icon: ⚠️ (AlertTriangle)
- ✅ Title: "Đã xảy ra lỗi"
- ✅ Message: "Có lỗi không mong muốn xảy ra. Vui lòng thử lại hoặc quay về Dashboard."
- ✅ Button [Thử lại] → reload trang
- ✅ Button [Về Dashboard] → navigate to /dashboard
- ✅ Trong mode Development: Có `<details>` hiển thị error stack

3. **PHỤC HỒI** code sau khi test xong:
   ```typescript
   // Xóa dòng test crash
   ```

---

## CHECKLIST TỔNG QUÁT

| Test Case | Trạng thái | Ghi chú |
|-----------|-----------|---------|
| S8.1a - LLM Timeout | ⬜ Chưa test | |
| S8.1b - File >50MB | ⬜ Chưa test | |
| S8.1c - Scanned PDF | ⬜ Chưa test | Cần file PDF scan |
| S8.1d - Invalid API Key | ⬜ Chưa test | Cần sửa .env |
| S8.1e - Network Failure | ⬜ Chưa test | |
| S8.1f - AI No Response (30s) | ⬜ Chưa test | |
| S8.2 - Error Boundary | ⬜ Chưa test | |

---

## LỖI THƯỜNG GẶP & CÁCH KHẮC PHỤC

### 1. **Timeout không trigger sau 30s**
- **Nguyên nhân:** Backend vẫn trả về chunks bình thường
- **Giải pháp:** Đảm bảo LLM service thực sự không hoạt động (API key invalid, service down)

### 2. **Error Boundary không catch được lỗi**
- **Nguyên nhân:** Lỗi xảy ra trong async code (outside React render)
- **Giải pháp:** Error Boundary chỉ catch lỗi trong render phase, không catch async errors

### 3. **Toast không hiển thị**
- **Nguyên nhân:** Toaster component không được mount
- **Giải pháp:** Kiểm tra `RootLayout.tsx` có `<Toaster />` không

### 4. **File size validation không hoạt động**
- **Nguyên nhân:** File < 50MB thực sự
- **Giải pháp:** Kiểm tra `file.size` trong console

---

## KẾT QUẢ MONG ĐỢI SAU KHI TEST

✅ Tất cả error states hiển thị đúng UI với message tiếng Việt
✅ Error actions (Retry, Dismiss, Settings) hoạt động đúng
✅ Không có "White Screen of Death" khi component crash
✅ User luôn biết phải làm gì tiếp theo khi gặp lỗi
✅ Local Mode button disabled với tooltip "Coming soon"

---

## NOTES

- **Local Mode:** Hiện tại DISABLED với tooltip "Coming soon in v2" vì chưa có Ollama setup
- **Settings Page:** Chưa có trong MVP → Button hiển thị toast thông báo
- **Error Tracking:** Console.error vẫn được gọi để debug, tương lai có thể integrate Sentry
