# Kịch Bản Sử Dụng Hệ Thống (System Use Cases) - Learning OS

Tài liệu này chi tiết hóa cách thức hệ thống **AetherTutor** vận hành để hỗ trợ từng phương pháp học tập cụ thể, dựa trên kiến trúc **Agentic Learning Ecosystem**. Các kịch bản được thiết kế để tối ưu hóa luồng tư duy và giảm tải nhận thức cho người học.

---

## 1. Nhóm Kỹ Thuật Học Tập Thực Chiến (Interactive Techniques)

### 1.1. Kỹ thuật Feynman & Socratic Dialogue
*   **Người dùng:** Chọn tính năng "Giảng giải", chọn một chủ đề (vd: Quantum Computing) và bắt đầu viết hoặc nói lời giải thích.
*   **Hệ thống (Socratic Tutor Agent):**
    *   Lắng nghe/Đọc nội dung của người dùng, đối chiếu với kiến thức chuẩn trong **Vector Database**.
    *   **Phản hồi:** *"Bạn giải thích về Qubit khá tốt, nhưng đoạn về 'Sự rối rắm lượng tử' (Entanglement) còn hơi mơ hồ. Bạn có thể giải thích nó như một ví dụ trong đời thực không?"*
*   **Giá trị:** Phát hiện lỗ hổng kiến thức thông qua phản diện và gợi mở thay vì đưa ra đáp án trực tiếp.

### 1.2. Active Recall & Spaced Repetition (Ghi nhớ dài hạn)
*   **Người dùng:** Bôi đen một định luật quan trọng khi đang nghiên cứu tài liệu.
*   **Hệ thống (Examiner Agent):**
    *   Tự động biến đoạn bôi đen thành câu hỏi Flashcard (Cloze deletion/Q&A).
    *   Lên lịch ôn tập theo thuật toán **SM-2**.
    *   **Thông báo:** *"Đã đến lúc ôn tập lại Định luật Ohm để giữ vững kiến thức trong trí nhớ dài hạn."*
*   **Giá trị:** Tự động hóa hoàn toàn việc tạo học liệu ghi nhớ.

### 1.3. Tư duy First Principles (Tầng sâu bản chất)
*   **Người dùng:** Gửi một vấn đề phức tạp (vd: "Tối ưu hóa chi phí logistics toàn cầu").
*   **Hệ thống (Researcher Agent):**
    *   Phân rã vấn đề thành các nguyên tử kiến thức cơ bản (năng lượng, không gian, lực cản, nhân lực).
    *   Yêu cầu người dùng đặt nghi vấn cho từng phần tử: *"Nếu biến phí vận chuyển thành 0, cấu trúc kinh tế của bạn sẽ thay đổi thế nào?"*
*   **Giá trị:** Loại bỏ định kiến, tìm kiếm giải pháp đột phá từ gốc rễ.

---

## 2. Quản trị Tri thức & Trực quan hóa (Interactive KM)

### 2.1. Zettelkasten & Liên kết mạng lưới (Second Brain)
*   **Người dùng:** Tạo ghi chú mới về "Tâm lý học hành vi".
*   **Hệ thống (Researcher Agent):** Quét kho dữ liệu cá nhân, gợi ý liên kết: *"Ghi chú này liên quan 85% đến thẻ 'Cơ chế kích thích' bạn tạo tháng trước. Bạn có muốn tạo Backlink?"*
*   **Hệ thống (Visualizer Agent):** Cập nhật **Graph View** theo thời gian thực.

### 2.2. Trực quan hóa song hướng (Bidirectional Dual Coding)
*   **Người dùng:** Tải lên văn bản quy trình hoặc mô tả hệ thống.
*   **Hệ thống (Visualizer Agent):** Tự động render sơ đồ **Mermaid.js** (Flowchart/Mindmap) bên cạnh text.
*   **Tính năng nâng cao:** Người dùng có thể click trực tiếp vào một "node" trên sơ đồ để sửa text. Ngay lập tức, đoạn Markdown gốc được cập nhật tương ứng và ngược lại.
*   **Giá trị:** Duy trì luồng tư duy liền mạch giữa ngôn ngữ và hình ảnh.

---

## 3. Định dạng Học tập Hiện đại (Automated Pipelines)

### 3.1. Microlearning Pipeline cho Media
*   **Người dùng:** Cung cấp link Video/Audio dài (vd: Podcast công nghệ).
*   **Hệ thống (Researcher Agent):**
    *   Trích xuất Audio -> Speech-to-Text (khử nhiễu) -> Chia nhỏ thành Chunks 3-5 phút.
    *   Sinh kịch bản tóm tắt (Text script) song song với từng đoạn video.
*   **Hệ thống (Examiner Agent):** Bắt "key terms" để tạo Quiz tương tác ngay sau mỗi Chunk.
*   **Giá trị:** Biến nội dung dài thành lộ trình học tập vi mô đa phương thức chỉ với 1 click.

---

## 4. Kịch bản Chuyên sâu cho Kỹ thuật & Công nghệ (Combo D)

### 4.1. Đọc hiểu Mã nguồn & Phân tích Hệ thống (Source Code Reading)
*   **Ngữ cảnh:** Đọc hiểu Framework mới hoặc debug hệ thống phức tạp.
*   **Hệ thống (Researcher + Socratic Tutor):**
    *   **Researcher:** RAG quét codebase để nắm bắt kiến trúc tổng thể.
    *   **Socratic Tutor:** Giải thích luồng thực thi (execution flow) và hỏi ngược: *"Nếu tham số input ở hàm X thay đổi, bạn nghĩ memory sẽ bị ảnh hưởng thế nào?"*
    *   **Visualizer:** Tự động sinh **Sequence Diagram** cho đoạn code đang đọc.
*   **Giá trị:** Biến việc đọc code thụ động thành buổi Pair-programming chủ động.

### 4.2. Luồng Điều Phối Đa Nhiệm (Orchestrator Handoff)
*   **Ngữ cảnh:** Yêu cầu phức hợp từ người dùng.
*   **Người dùng:** *"Giải thích cấu trúc dữ liệu Graph, vẽ minh họa và tạo bài kiểm tra."*
*   **Hệ thống (Parent Orchestrator):**
    *   Phân rã thành 3 sub-tasks: (1) Tutor giải thích -> (2) Visualizer vẽ sơ đồ thông qua context từ Tutor -> (3) Examiner tạo Quiz từ context tổng hợp.
    *   Sử dụng **MCP Protocol** để đồng bộ ngữ cảnh giữa các Agent.
    *   Render kết quả đồng thời trên UI.
*   **Giá trị:** Trải nghiệm "One-stop shop" mượt mà, không gián đoạn.

---

## 5. Bảng Tổng Hợp Vai Trò & Công Nghệ Key

| Agent | Use Case Tiêu Biểu | Chuẩn Đầu Ra (Output) | Công Nghệ Key |
| :--- | :--- | :--- | :--- |
| **Parent Orchestrator** | Task routing, Context Handoff | JSON payload phân rã tác vụ | MCP Protocol, LLM Function Calling |
| **Socratic Tutor** | Feynman, Code Review, Tranh biện | Text giải thích, Câu hỏi gợi mở | System Prompt chuyên sâu sư phạm |
| **Researcher Agent** | Pipeline Media, Zettelkasten, RAG | Text chunks, Metadata, Vector Link | RAG, Vector DB, Audio/Video API |
| **Visualizer Agent** | Bidirectional Edit, Dual Coding | Mã Mermaid.js, Interactive UI | LLM to Code, React/Vue Diagram Libs |
| **Examiner Agent** | Active Recall, Spaced Repetition | JSON câu hỏi, Lịch nhắc nhở (SM-2) | SM-2 Algorithm, Data Extraction |

---

## 6. Lộ trình Phát triển MVP (Roadmap)

> [!IMPORTANT]
> Ưu tiên hoàn thiện **Backend Pipeline** (Handoff & RAG) trước khi tập trung vào UI polish.

1.  **Giai đoạn 1 (Foundation):** Triển khai Orchestrator + Socratic Tutor (Sử dụng MCP đơn giản).
2.  **Giai đoạn 2 (Intelligence):** Tích hợp Researcher (RAG) và luồng xử lý Media.
3.  **Giai đoạn 3 (Visualization):** Triển khai Visualizer (One-way Mermaid) và Code Reading.
4.  **Giai đoạn 4 (Interactive UX):** Nâng cấp Visualizer lên Bidirectional và hoàn thiện UI/UX.

---
*Tài liệu này là kim chỉ nam cho việc hiện thực hóa hệ sinh thái AetherTutor.*
