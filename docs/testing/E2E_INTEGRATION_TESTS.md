# E2E Integration Test Guide — AetherTutor Sprint 5

> **Created:** April 7, 2026
> **Type:** Manual End-to-End Testing
> **Prerequisites:** Backend running on `localhost:8000`, Frontend on `localhost:5173`

---

## Flow 1: Upload PDF → Processing → Completed

### Steps
1. **Mở ứng dụng**
   - Truy cập `http://localhost:5173`
   - ✅ Verify: Dashboard hiển thị với welcome message
   - ✅ Verify: LLM Mode Badge hiển thị (🔒 Local hoặc 🌐 Cloud)

2. **Navigate đến Knowledge Vault**
   - Click "Knowledge Vault" trong sidebar
   - ✅ Verify: Document list hiển thị (có thể trống)
   - ✅ Verify: Upload button available

3. **Upload PDF**
   - Click "Upload PDF" → Chọn file PDF hợp lệ (<50MB)
   - ✅ Verify: Modal đóng, document xuất hiện với status "PROCESSING"
   - ✅ Verify: Progress bar hiển thị
   - ✅ Verify: Polling tự động cập nhật status mỗi 3s

4. **Wait for Processing**
   - Quan sát processing step changes: EXTRACTING → CHUNKING → EXTRACTING_ENTITIES → BUILDING_GRAPH → EMBEDDING → COMPLETED
   - ✅ Verify: Status chuyển sang "COMPLETED" khi xong
   - ✅ Verify: Toast "Xử lý hoàn tất" hiển thị
   - ✅ Verify: entity_count và relation_count > 0

5. **Navigate to Chat**
   - Click nút "Chat" trên document
   - ✅ Verify: Redirect đến `/chat/{documentId}`
   - ✅ Verify: DocumentGuard check status = COMPLETED
   - ✅ Verify: Chat welcome screen hiển thị với filename
   - ✅ Verify: Feynman mode được chọn mặc định
   - ✅ Verify: Socratic mode disabled với "Coming soon in v2" tooltip

### Error Scenarios
- [ ] **Upload file >50MB** → Toast "File quá lớn (giới hạn 50MB)"
- [ ] **Upload file trùng hash** → Toast "Tài liệu này đã tồn tại"
- [ ] **Upload PDF scan (no text)** → Toast "PDF này là ảnh scan"

---

## Flow 2: Chat → SSE Streaming → Context Chips

### Steps
1. **Bắt đầu cuộc hội thoại**
   - Từ Chat page, nhập câu hỏi vào textarea
   - Click Send (hoặc Enter)
   - ✅ Verify: User message hiển thị ngay lập tức (optimistic update)
   - ✅ Verify: Assistant placeholder "PENDING" hiển thị
   - ✅ Verify: Input disabled khi đang streaming
   - ✅ Verify: Loading indicator trong send button

2. **SSE Streaming**
   - ✅ Verify: Assistant message bắt đầu stream từng chunk
   - ✅ Verify: Streaming cursor (blinking) ở cuối message
   - ✅ Verify: Markdown rendering đúng (code blocks, bold, lists)
   - ✅ Verify: Auto-scroll xuống khi có content mới

3. **Message Completed**
   - ✅ Verify: Message status → "COMPLETED"
   - ✅ Verify: ContextChips hiển thị entity pills dưới message (từ `found_entities`)
   - ✅ Verify: ContextChips clickable → navigate sang Graph với highlight

4. **Conversation Management**
   - ✅ Verify: Conversation sidebar (trái) hiển thị list conversations
   - ✅ Verify: Click conversation khác → load history
   - ✅ Verify: "New conversation" button → tạo conversation mới
   - ✅ Verify: Delete conversation → toast + auto-switch

5. **Mode Switching**
   - ✅ Verify: Feynman mode active (amber highlight)
   - ✅ Verify: Socratic mode disabled (greyed out + cursor-not-allowed)
   - ✅ Verify: Hover Socratic → tooltip "Coming soon in v2"

### Error Scenarios
- [ ] **Network disconnect trong streaming** → ChatErrorCard "Mất kết nối mạng" + [Retry]
- [ ] **AI không phản hồi sau 30s** → ChatErrorCard "⚠️ AI không phản hồi" + [Retry]
- [ ] **Invalid API Key (504/401)** → ChatErrorCard "API Key không hợp lệ" + [Go to Settings]
- [ ] **Retry từ error card** → Gửi lại message cuối, stream lại

---

## Flow 3: Graph Viewer → Node Click → Entity Details

### Steps
1. **Navigate đến Graph**
   - Từ Chat page, click icon "View Graph" trong header
   - Hoặc từ Vault, click "Graph" trên document
   - ✅ Verify: Redirect đến `/graph/{documentId}`
   - ✅ Verify: ReactFlow hiển thị nodes và edges
   - ✅ Verify: Nodes xếp theo radial layout (vòng tròn)
   - ✅ Verify: Stats hiển thị (X Nút • Y Cạnh)

2. **Node Interaction**
   - Click vào một entity node
   - ✅ Verify: GraphSidebar mở ra từ bên phải (animation)
   - ✅ Verify: Entity name, type badge, description hiển thị
   - ✅ Verify: Neighbors list với relation_type labels
   - ✅ Verify: Degree count chính xác
   - ✅ Verify: "Chat về entity này" button available

3. **Chat about Entity**
   - Click "Chat về entity này"
   - ✅ Verify: Navigate sang `/chat/{documentId}`
   - ✅ Verify: (Optional) Pre-filled query với entity name

4. **Search Filtering**
   - Click nút Search trong toolbox
   - ✅ Verify: Search input hiển thị
   - Nhập tên entity
   - ✅ Verify: Matching nodes highlight, others dimmed
   - Xóa search → tất cả nodes bình thường

5. **Edge Labels**
   - ✅ Verify: Edges có label relation_type (hiển thị trên edge)
   - ✅ Verify: Edges animated (dashed line)

### Error Scenarios
- [ ] **Document chưa xử lý xong** → DocumentGuard redirect về Vault
- [ ] **Document bị xóa (404)** → Redirect + toast "Tài liệu này đã bị xóa"
- [ ] **Graph trống (no nodes)** → Empty state "Chưa có Knowledge Graph"
- [ ] **Backend error** → Toast "Lỗi tải đồ thị"

---

## Flow 4: Error Recovery — Full Scenarios

### 4a: Upload Error Recovery
1. Upload file >50MB
2. ✅ Verify: Toast "File quá lớn (giới hạn 50MB)" với icon cảnh báo
3. ✅ Verify: Modal vẫn mở, user có thể chọn file khác
4. ✅ Verify: Dismiss → modal đóng
5. Upload file hợp lệ
6. ✅ Verify: Upload thành công bình thường

### 4b: Chat Error Recovery
1. Ngắt mạng (disable network trong DevTools)
2. Gửi message trong Chat
3. ✅ Verify: Sau 30s → ChatErrorCard "⚠️ AI không phản hồi"
4. ✅ Verify: Buttons: [Retry] [Check Settings]
5. Bật lại mạng
6. Click Retry
7. ✅ Verify: Gửi lại message, stream hoạt động bình thường

### 4c: Network Failure in Graph
1. Mở Graph page
2. Ngắt mạng
3. Click Refresh
4. ✅ Verify: Toast "Lỗi tải đồ thị: Mất kết nối mạng"
5. Bật lại mạng
6. Click Refresh
7. ✅ Verify: Graph tải lại thành công

### 4d: Document Deletion Guard
1. Mở Chat page với document A
2. Navigate sang Vault, xóa document A
3. ✅ Verify: Polling phát hiện 404
4. ✅ Verify: Redirect về `/vault`
5. ✅ Verify: Toast "Tài liệu này đã bị xóa."

---

## Performance Targets

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| First meaningful paint | < 1.5s | TBD | ⏳ |
| Graph render (50 nodes) | < 500ms | TBD | ⏳ |
| SSE first chunk | < 3s | TBD | ⏳ |
| Build size (JS bundle) | < 2MB | 1.2MB | ✅ |
| Build size (CSS) | < 200KB | 95KB | ✅ |
| Unit tests | 46 passing | 46/46 | ✅ |

---

## Browser Compatibility

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | Latest | ⏳ TBD |
| Firefox | Latest | ⏳ TBD |
| Edge | Latest | ⏳ TBD |
| Safari | Latest | ⏳ TBD |

---

## Checklist tổng thể

- [ ] Flow 1: Upload → Processing → Completed ✅
- [ ] Flow 2: Chat → SSE Streaming → Context Chips ✅
- [ ] Flow 3: Graph Viewer → Node Click → Details ✅
- [ ] Flow 4a: Upload Error Recovery ✅
- [ ] Flow 4b: Chat Error Recovery ✅
- [ ] Flow 4c: Network Failure in Graph ✅
- [ ] Flow 4d: Document Deletion Guard ✅
- [ ] LLM Mode Badge hiển thị đúng ✅
- [ ] Mobile sidebar toggle hoạt động ✅
- [ ] Conversation sidebar hoạt động ✅
- [ ] Build `npm run build` — 0 errors ✅

---

> **Note:** Đây là manual test guide. Automation testing (Playwright/Cypress) có thể được setup trong tương lai.
