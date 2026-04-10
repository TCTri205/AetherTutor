# Kế hoạch Triển khai Giai đoạn 2: Intelligence & Memory

> **Document Owner:** AetherTutor Team
> **Status:** Draft (Planning for Stage 2)
> **Timeline:** Dự kiến 12 tuần (Quý 2 - 2026)
> **Phiên bản:** 3.0 — Bổ sung Data Cleaning, Storage Abstraction, Quiz Feedback, Notification Strategy, Stage 3 Recommendations

---

## 1. Mục tiêu (Goals)
Chuyển đổi AetherTutor từ một công cụ tra cứu tri thức thành một **Hệ điều hành học tập (Learning OS)** thực thụ, tập trung vào việc ghi nhớ dài hạn, kết nối ý tưởng và tư duy đa chiều dựa trên nền tảng Knowledge Graph.

---

## 2. Phạm vi triển khai (Scope)
- **The Examiner Agent:** Tự động hóa việc kiểm tra kiến thức dựa trên đồ thị tri thức.
- **Spaced Repetition (SM-2):** Tối ưu hóa việc ghi nhớ thông qua lịch ôn tập thuật toán.
- **Zettelkasten Beta:** Quản lý ghi chú liên kết (Atomic notes & Backlinks).
- **LightRAG Intelligence:** Nâng cấp khả năng truy vấn đa tài liệu và xác thực thông tin (Cross-verification).

---

## 2b. Pre-requisites & Ràng buộc kỹ thuật

> [!IMPORTANT]
> Trước khi bắt đầu bất kỳ Sprint chức năng nào, các vấn đề nền tảng sau **PHẢI** được giải quyết. Đây là blocking dependencies.

### 2b.1 Các vấn đề blocking từ Stage 1

| # | Vấn đề | Trạng thái hiện tại | Tác động nếu không fix |
|---|--------|-------------------|----------------------|
| **B1** | **Bảng `documents` không có `user_id`** | Cột `user_id` không tồn tại trong model lẫn DB | Không thể phân隔离 dữ liệu per-user → Flashcards/Notes/Quizzes không hoạt động đúng |
| **B2** | **`GraphRelation` lưu entity name dạng `String`, không phải UUID FK** | `source_entity` / `target_entity` là `String(255)` | Không thể JOIN hiệu quả, multi-hop reasoning chậm, cross-document resolution sai |
| **B3** | **`GraphBuilder` là stub** | 3 methods đều `pass` | ExaminerAgent không thể tính centrality/community detection |
| **B4** | **ChromaDB collections không có `user_id` filter** | Metadata chunk/entity không chứa `user_id` | Leak context giữa users (khi có multi-user) |
| **B5** | **Chưa có Authentication layer** | Không có JWT, không có auth middleware | Không thể phân quyền API endpoints Stage 2 |
| **B6** | **API spec chưa có section cho Quiz/Flashcard/Notes** | `API_Specifications.md` chỉ có Post-MVP placeholder | Dev implement sai contract |
| **B7** | **Lỗ hổng bảo mật `/test-ingest`** | Endpoint debug lộ diện trên production | Rủi ro nạp dữ liệu trái phép, bypass worker |
| **B8** | **Mâu thuẫn Range Confidence** | Pydantic (0-100) vs DB (0-1) | Gây lỗi INSERT khi LLM trả về giá trị % |
| **B9** | **Lệch pha Embedding Function** | ChromaDB dùng default thay vì config model | Giảm độ chính xác tìm kiếm ngữ nghĩa |
| **B10** | **Enum `ProcessingStep` không đồng bộ** | Frontend có `QUEUED`, Backend thì không | Gây lỗi logic hiển thị trạng thái tài liệu |

### 2b.2 Chiến lược giải quyết

Tất cả blocking issues được gom vào **Sprint 0** (xem bên dưới). Các Sprint 1-5 chỉ bắt đầu khi Sprint 0 hoàn thành.

---

## 3. Lộ trình triển khai chi tiết (Sprints)

### Sprint 0: Foundation — Multi-tenant, Auth & Graph Hardening (Tuần 1-2)
*Mục tiêu: Giải quyết toàn bộ blocking dependencies, chuẩn bị nền tảng vững chắc cho Stage 2.*

> [!WARNING]
> **Critical Path:** Sprint 0 có 2 công việc rủi ro cao nhất toàn bộ Stage 2 — Migration 6 (String → UUID FK) và Data Cleaning. Tuyệt đối không skip manual review step.

- **Database Migrations (Alembic):**
  - Migration 1: Thêm `user_id UUID REFERENCES users(id) ON DELETE CASCADE` vào bảng `documents`
  - Migration 2: Tạo default user (`id = '00000000-0000-0000-0000-000000000001'`, email: `default@aethertutor.local`) và gán cho tất cả documents hiện tại
  - Migration 3: Thêm `user_id` vào bảng `graph_entities`
  - Migration 4: Tạo bảng `entity_aliases` (cross-document entity resolution)
  - Migration 5: Tạo staging tables Stage 2 — `flashcards`, `study_sessions`, `notes`, `note_links`, `quizzes`, `quiz_results`, `quiz_answers` (theo DDL trong `Data_Model.md §2.4-2.7, §2.9-2.10`)
  - Migration 6: **Breaking change** — Chuyển `graph_relations` từ `source_entity`/`target_entity` (String) → `source_entity_id`/`target_entity_id` (UUID FK → `graph_entities.id`). Script data migration: lookup canonical_name → entity UUID, cảnh báo nếu không khớp
  - Migration 7: Thêm index `idx_flashcards_next_review`, `idx_graph_entities_user`, `idx_graph_relations_source`, `idx_graph_relations_target`

- **Authentication (Tối thiểu cho Local/Dev):**
  - Implement middleware `get_current_user_id()` trong `app/api/dependencies.py` — đọc `X-User-Id` header (tạm thời), fallback về default user nếu không có
  - Chuẩn bị interface để sau nâng cấp lên JWT без thay đổi business logic
  - Cập nhật tất cả endpoints hiện tại để inject `user_id` vào service calls

- **GraphBuilder Implementation:**
  - **Storage Abstraction Layer** (`app/core/storage_provider.py`):
    - Định nghĩa protocol `StorageProvider`: `save(key, data)`, `load(key)`, `exists(key)`, `delete(key)`
    - Implement `LocalStorage(StorageProvider)` — lưu ra disk (dev/staging)
    - Interface sẵn cho `S3Storage(StorageProvider)` — dùng boto3/minio (production cloud)
    - Config qua env var: `GRAPH_STORAGE_BACKEND=local|s3`, `GRAPH_STORAGE_PATH=/app/uploads/graphs`
  - Implement `GraphBuilder.add_entities_and_relations()` — xây dựng `nx.MultiDiGraph` từ entities/relations
  - Implement `GraphBuilder.persist_graph(document_id)` — dùng StorageProvider export GraphML/JSON
  - Implement `GraphBuilder.load_graph(document_id)` — load từ StorageProvider
  - Thêm methods: `get_centrality_scores(document_id)` — tính `nx.degree_centrality()` và `nx.betweenness_centrality()`
  - Thêm methods: `get_multi_hop_neighbors(entity_id, max_depth=2)` — BFS traversal
  - Refactor `LightRAGPipeline` để sử dụng `GraphBuilder` thay vì bypass

- **Data Cleaning trước Migration 6 (CRITICAL):**
  - **Mục đích:** Migration 6 chuyển `source_entity`/`target_entity` từ String → UUID FK. Nếu entity name không khớp chính xác với `graph_entities.canonical_name`, migration sẽ fail hoặc tạo FK sai.
  - **Script tiền xử lý** (`scripts/clean_entity_names.py`):
    1. Quét toàn bộ `graph_relations`, thu thập tất cả `source_entity` và `target_entity` unique
    2. Fuzzy match từng entity name với `graph_entities.canonical_name` (dùng `difflib.SequenceMatcher`, threshold 0.85)
    3. Với mỗi match → gán vào `canonical_name` tương ứng
    4. Với mỗi **unresolved entity** (không match được) → log ra file `unresolved_entities.csv` với columns: `entity_name, occurrence_count, sample_relations`
    5. Báo cáo tổng quan: `Total relations: X | Resolved: Y | Unresolved: Z`
  - **Manual Review Step:** Dev/Admin review `unresolved_entities.csv`, quyết định:
    - Gán thủ công vào canonical name đúng
    - Hoặc đánh dấu `DELETE` nếu entity không còn tồn tại trong graph
  - **Migration 6 execution path:**
    1. Chạy Data Cleaning script → resolve ≥ 95% entities
    2. Backup DB: `pg_dump aethertutor > backup_pre_migration6.sql`
    3. Chạy migration 6 trên staging → verify FK integrity
    4. Chạy production với `--dry-run` flag trước (validate không raise error)
    5. Apply thật sự
  - **Rollback plan:** Giữ script đảo ngược — restore `source_entity`/`target_entity` từ `canonical_name` lookup, revert FK về String(255)

- **ChromaDB & Search Hardening:**
  - Thêm `user_id` vào metadata khi upsert chunks và entities (`pipeline.py`, `retriever.py`)
  - Cập nhật `Retriever.retrieve()` để filter `where={"user_id": user_id}` trong mọi ChromaDB query
  - **Cấu hình tường minh Embedding Function:** Cập nhật `ChromaClient` để khởi tạo collection với embedding model khớp với `settings.DEFAULT_EMBEDDING_MODEL`
  - **Nâng cấp Retriever Prompt:** Cập nhật `Retriever.generate()` để sử dụng prompt Socratic/Feynman đồng bộ với `ChatService`

- **Bug Fixes & Security [NEW ADDTIONS]:**
  - **Security:** Đóng endpoint `/api/v1/documents/test-ingest` bằng `DEBUG` guard trong `settings`.
  - **Enum Sync:** Thêm `QUEUED` vào `ProcessingStep` enum trong `app/models/document.py`.
  - **Range Fix:** Điều chỉnh `ExtractedEntity.confidence` trong `app/schemas/lightrag.py` về dải `0.0 - 1.0`.

- **API Specifications Update:**
  - Bổ sung section chính thức vào `API_Specifications.md` cho:
    - `POST /api/v1/flashcards/review`, `GET /api/v1/flashcards/due`
    - `POST /api/v1/quiz/generate`, `GET /api/v1/quiz/{id}/results`
    - `POST /api/v1/notes/zettel`, `GET /api/v1/notes/backlinks`
    - `GET /api/v1/recall/schedule`
  - Định nghĩa request/response schema chi tiết (theo pattern hiện tại)

- **Constants (`app/constants.py`):**
  ```python
  # Stage 2 Additions
  SM2_INITIAL_EASE = 2.5
  SM2_MIN_EASE = 1.3
  MAX_QUIZ_QUESTIONS = 20
  NOTE_LINK_SUGGESTION_THRESHOLD = 0.75
  SM2_DEFAULT_QUALITY = 3  # Default quality for "again" review
  QUIZ_DIFFICULTY_SCALE_MIN = 1
  QUIZ_DIFFICULTY_SCALE_MAX = 5
  BACKLINK_AI_MODEL_MAX_TOKENS = 500
  ```

- **Testing:**
  - Unit tests cho `GraphBuilder` (centrality, multi-hop, persist/load)
  - Unit tests cho `StorageProvider` (LocalStorage save/load roundtrip, S3 mock)
  - Integration test: Migration data integrity (default user assigned correctly, FK relations valid)
  - Integration test: Data Cleaning script — verify fuzzy match resolves ≥ 95% entities
  - Test ChromaDB filter: đảm bảo user A không thấy chunks của user B

- **Rủi ro & Backup:**
  - **Backup toàn bộ DB** trước khi chạy migrations (đặc biệt Migration 6 — breaking change)
  - Rollback plan: Giữ migration script đảo ngược cho Migration 6 (restore `source_entity`/`target_entity` từ canonical_name lookup)
  - Chạy migration 6 trên staging environment trước khi apply production
  - **Data Cleaning risk:** Nếu unresolved entities > 5%, DỪNG migration, manual review toàn bộ trước khi tiếp tục

---

### Sprint 1: Nền tảng Ghi nhớ & Thuật toán SM-2 (Tuần 3-4)
*Mục tiêu: Hiện thực hóa hệ thống Flashcard và thuật toán lặp lại ngắt quãng.*

- **Backend:**
  - Models: Kích hoạt `Flashcard`, `StudySession` trong `app/models/` (theo `Data_Model.md §2.5-2.6`)
  - Repositories:
    - `FlashcardRepository(BaseRepository[Flashcard])`: `bulk_create`, `get_due(user_id)`, `get_by_id`, `update_sm2_params`, `delete_by_user`
    - `StudySessionRepository(BaseRepository[StudySession])`: `create`, `get_by_user`, `get_stats`
  - Service `SM2Service`:
    - Implement thuật toán SM-2 từ `Data_Model.md §2.5` (pseudocode → Python)
    - Method `update_card(card_id, quality: int)` — cập nhật ease_factor, interval, repetitions, next_review
    - Method `get_due_cards(user_id, limit=50)` — query cards có `sm2_next_review <= NOW()`
    - Method `create_flashcard(user_id, front, back, metadata)` — tạo flashcard thủ công hoặc auto từ quiz
    - Method `generate_review_session(user_id)` — tạo StudySession và trả về danh sách cards cần ôn
    - **Idempotency:** `review(card_id, quality, idempotency_key)` — prevent duplicate review nếu client retry
  - Service `FlashcardGenerationService`:
    - Auto-generate flashcards từ graph entities: entity name → front, entity description → back
    - Batch generate từ quiz wrong answers
  - API Endpoints:
    - `GET /api/v1/flashcards/due?limit=50` → trả về danh sách cards cần ôn
    - `POST /api/v1/flashcards/review` — body: `{card_id, quality, idempotency_key}` → cập nhật SM-2
    - `POST /api/v1/flashcards` — body: `{front, back, metadata}` — tạo manual
    - `GET /api/v1/flashcards` — list user's flashcards
    - `GET /api/v1/recall/schedule` — trả về lịch ôn tập trong tuần (nhóm theo ngày)
  - Background Job (ARQ):
    - `sm2_daily_digest_task(user_id)` — chạy hàng ngày lúc 8h, quét due cards, push notification/email (nếu config)
    - Redis distributed lock: đảm bảo mỗi user chỉ có 1 job chạy tại 1 thời điểm
  - **Notification Strategy (Multi-channel):**
    - **Kênh 1 — Browser Notification (Web Push API):**
      - Frontend đăng ký Service Worker, xin permission `Notification`
      - Backend lưu `push_subscription` JSON trong Redis (key: `push:sub:{user_id}`)
      - ARQ job gửi payload: `{title: "30 flashcards đang chờ!", body: "Hãy ôn tập ngay để duy trì streak 🔥", icon: "/icon.png"}`
      - **Ưu điểm:** Miễn phí, realtime, không cần email server
      - **Nhược:** Chỉ hoạt động khi browser đang mở (hoặc background sync)
    - **Kênh 2 — Email (SMTP, optional):**
      - Nếu env có `SMTP_HOST`, `SMTP_USER` config → gửi email digest
      - Template: "Bạn có X cards cần ôn hôm nay. Streak hiện tại: Y ngày."
      - Dùng `aiosmtplib` + Jinja2 template (`app/templates/email_digest.html`)
    - **Kênh 3 — Telegram Bot (Stage 3):**
      - User link Telegram account → bot gửi message hàng ngày
      - **Không implement trong Stage 2** — để khi có demand từ users
    - **Fallback logic:** Nếu browser notification fail (permission denied) → thử email. Nếu cả 2 fail → log warning, không retry

- **Frontend:**
  - Zustand store: `useFlashcardStore` — `dueCards[]`, `currentCard`, `reviewStats`, `streak`
  - API service: `flashcardService.ts` — `getDue()`, `review()`, `create()`
  - Trang `FlashcardReview.tsx`:
    - Interactive Flip Card (framer-motion 3D flip)
    - Quality rating buttons: 0-5 (SM-2 scale với labels: "Again", "Hard", "Good", "Easy")
    - Progress bar: số cards còn lại trong session
    - Session summary khi hoàn thành
  - Dashboard Widget:
    - Hiển thị Streak (số ngày liên tiếp ôn tập)
    - Số cards cần ôn hôm nay
    - Mini calendar heatmap (như GitHub contributions)
  - Micro-interactions: âm thanh flip card, confetti khi hoàn thành session

---

### Sprint 2: The Examiner Agent & Quiz Generation (Tuần 5-6)
*Mục tiêu: AI chủ động kiểm tra kiến thức dựa trên Graph.*

- **AI Logic — ExaminerAgent (`app/core/examiner_agent.py`):**
  - Method `generate_quiz(document_id, user_id, topic=None, num_questions=10, question_types=["multiple_choice", "true_false"])`:
    - **Entity Selection:** Lấy entities từ document, rank theo centrality score (từ `GraphBuilder.get_centrality_scores()`)
    - **Question Generation:** Với mỗi entity → prompt LLM tạo câu hỏi theo Bloom's Taxonomy (remember → analyze)
      - Multiple choice: 1 correct + 3 distractors (distractors lấy từ entities cùng loại trong graph)
      - True/False: Statement về entity, 50% true, 50% false
    - **Cross-verification:** Dùng graph relations để validate distractors — distractor phải là entity thật nhưng không phải answer đúng cho context này
    - **Difficulty balancing:** Phân bố difficulty 1-5 dựa trên entity confidence + centrality
  - Method `evaluate_quiz(quiz_id, user_answers)` → trả về score, weak_areas (entities có score thấp)
  - Method `convert_wrong_answers_to_flashcards(quiz_result_id)` → auto-generate flashcards từ câu sai

- **Backend:**
  - Models: `Quiz`, `QuizResult`, `QuizAnswer` (theo `Data_Model.md §2.7, §2.10`)
  - **Bổ sung:** Thêm cột `quality_rating` (SMALLINT 1-5) và `quality_feedback` (TEXT) vào `quiz_results` — cho phép user đánh giá chất lượng câu hỏi
  - Repositories:
    - `QuizRepository`: `create`, `get_by_id`, `get_by_user`
    - `QuizResultRepository`: `create`, `get_by_user`, `get_stats`, `get_weak_areas`, `update_quality_feedback`
  - API Endpoints:
    - `POST /api/v1/quiz/generate` — body: `{document_id?, topic?, num_questions, question_types}` → tạo quiz từ graph
    - `POST /api/v1/quiz/{quiz_id}/submit` — body: `{answers: [{question_id, answer}]}` → chấm điểm, lưu result
    - `GET /api/v1/quiz/{quiz_id}/results` → chi tiết kết quả, giải thích, weak areas
    - `POST /api/v1/quiz/{result_id}/convert-to-flashcards` → tạo flashcards từ câu sai
    - **`POST /api/v1/quiz/{result_id}/feedback`** — body: `{quality_rating: 1-5, quality_feedback?: "Câu hỏi sai kiến thức" | "Đáp án không hợp lý" | "Quá dễ" | "Quá khó" | "Khác"}` → lưu feedback để fine-tune prompt
  - Service `QuizAnalysisService`:
    - `analyze_weak_areas(quiz_result_id)` — xác định entities/concepts user yếu nhất
    - `generate_study_recommendation(user_id)` — gợi ý topics cần ôn dựa trên quiz history
  - **Quiz Quality Feedback Loop:**
    - Feedback được lưu vào `quiz_results.quality_rating` và `quality_feedback`
    - ARQ job `quiz_feedback_analysis_task(result_id)`:
      - Nếu `quality_rating <= 2` → flag quiz để admin review
      - Phân loại feedback bằng LLM (prompt: "Classify this feedback into: factual_error, poor_distractor, too_easy, too_hard, other")
      - Aggregate stats: `% quizzes rated >= 4`, `top feedback categories`
    - **Prompt tuning:** Hàng tuần, export feedback data → điều chỉnh ExaminerAgent prompt:
      - Nếu nhiều "poor_distractor" → tăng số lượng entity candidates cho distractors
      - Nếu nhiều "factual_error" → thêm verification step trước khi generate
    - **Dashboard metric:** Hiển thị `% quizzes có rating >= 4` trong admin dashboard

- **Frontend:**
  - Zustand store: `useQuizStore` — `currentQuiz`, `answers`, `score`, `weakAreas`
  - API service: `quizService.ts`
  - Trang `Quiz.tsx`:
    - Timer đếm ngược (optional, configurable)
    - Progress bar
    - Multiple choice UI với radio buttons
    - True/False toggle
    - Submit & Review mode
  - Trang `QuizResults.tsx`:
    - Score breakdown theo taxonomy level
    - Weak areas visualization (bar chart)
    - Nút "Thêm vào Flashcard" cho câu sai
    - Nút "Làm lại" với câu hỏi mới
    - **Star Rating component** (1-5 stars) cho chất lượng quiz
    - **Feedback modal:** Chọn lý do từ dropdown + optional text input
    - Nút "Báo cáo câu hỏi sai" cho từng câu specific
  - Tích hợp vào Chat: Nút "Tạo Quiz từ tài liệu này" trong Chat page

---

### Sprint 3: Zettelkasten & Bi-directional Linking (Tuần 7-8)
*Mục tiêu: Kết nối ghi chú cá nhân vào mạng lưới tri thức.*

- **Backend:**
  - Models: `Note`, `NoteLink` (theo `Data_Model.md §2.4`)
  - Repositories:
    - `NoteRepository(BaseRepository[Note])`: `create`, `get_by_user`, `get_with_backlinks`, `search_by_tags`
    - `NoteLinkRepository`: `create_link`, `get_backlinks(note_id)`, `get_outgoing_links(note_id)`
  - Service `NoteService`:
    - `create_note(user_id, title, content, note_type, tags)` — tạo atomic note
    - `suggest_backlinks(note_id)` — AI scan content, đối chiếu với Knowledge Graph → gợi ý links tới entities/notes khác
      - Dùng embedding similarity giữa note content và entity descriptions
      - Threshold: `NOTE_LINK_SUGGESTION_THRESHOLD = 0.75`
    - `update_note(note_id, title?, content?, tags?)` — cập nhật, trigger re-suggest backlinks
    - `get_note_graph(user_id)` — trả về network của notes + backlinks (cho visualization)
  - Service `BacklinkAIService`:
    - Method `find_related_entities(note_content, user_id, top_k=5)` — embedding-based retrieval
    - Method `find_related_notes(note_content, user_id, top_k=3)` — semantic similarity giữa notes
    - Cache kết quả trong Redis (TTL 1h) để tránh gọi LLM liên tục
  - API Endpoints:
    - `POST /api/v1/notes` — body: `{title, content, note_type, tags}` → tạo note
    - `GET /api/v1/notes` — list user's notes (paginate, filter by tags)
    - `GET /api/v1/notes/{id}` — note detail + backlinks + related entities
    - `POST /api/v1/notes/{id}/links` — body: `{target_note_id, context}` — tạo link thủ công
    - `GET /api/v1/notes/{id}/backlinks` — danh sách backlinks gợi ý
    - `GET /api/v1/notes/graph` — trả về nodes/edges cho Zettelkasten Graph View

- **Frontend:**
  - Zustand store: `useNoteStore` — `notes[]`, `currentNote`, `backlinks[]`, `relatedEntities[]`
  - API service: `noteService.ts`
  - Trang `Zettelkasten.tsx`:
    - Markdown Editor (dùng `react-markdown` + KaTeX như project đã có)
    - Atomic note view/edit toggle
    - Tag input với autocomplete
    - Sidebar: Related Entities (context chips từ Knowledge Graph)
    - Sidebar: Suggested Backlinks (click để tạo link)
  - **Zettelkasten Graph View:**
    - Dùng React Flow (như GraphExplorer hiện tại)
    - Nodes = Notes, Edges = NoteLinks
    - Color coding theo note_type (fleeting/literature/permanent/project)
    - Click node → mở note detail panel
  - Tích hợp vào Chat: Nút "Tạo Note từ câu trả lời AI"

---

### Sprint 4: LightRAG Intelligence & Multi-doc Reasoning (Tuần 9-10)
*Mục tiêu: Xóa bỏ ranh giới giữa các tài liệu đơn lẻ.*

- **AI Core:**
  - Nâng cấp `Retriever.retrieve()` → `retrieve_multi(document_ids: list[str] | None = None, user_id: UUID)`:
    - Nếu `document_ids=None` → Global search toàn bộ user's documents
    - Nếu `document_ids=[...]` → Scoped search trong danh sách documents
    - Kết hợp: vector search entities (global) + vector search chunks (scoped) + graph neighbors
  - Service `CrossVerificationService`:
    - Method `cross_check(query, document_ids)` → LLM so sánh thông tin giữa các documents
    - Phát hiện mâu thuẫn: "Document A nói X, nhưng Document B nói Y"
    - Phát hiện bổ sung: "Document A đề cập P, Document B mở rộng thêm Q"
    - Output: consolidated context với source attribution per claim
  - Entity Alias Resolution:
    - Method `resolve_entity_alias(entity_name, user_id)` → lookup `entity_aliases` table
    - Ví dụ: "AI" → "Artificial Intelligence", "ML" → "Machine Learning"
    - Auto-create alias khi user confirm LLM suggestion

- **API:**
  - Nâng cấp `POST /api/v1/graph/query`:
    - Thêm field `document_ids: list[str] | null` trong request body
    - Thêm field `scope: "document" | "user_global"` trong request body
    - Response thêm `cross_verification_summary` (nếu multi-doc)
  - API mới:
    - `POST /api/v1/entities/resolve-alias` — body: `{alias_name, suggested_canonical}` → user confirm tạo alias
    - `GET /api/v1/entities/aliases?user_id=...` — list user's entity aliases

- **Frontend:**
  - **Global Graph Explorer:**
    - Mở rộng `GraphExplorer.tsx` để hỗ trợ toggle: "Document Graph" ↔ "Global Graph"
    - Global Graph: aggregate entities theo `canonical_name` across documents
    - Node size ∝ centrality, Edge thickness ∝ frequency across docs
  - Multi-document selector trong Chat page — chọn documents để chat cùng lúc
  - Cross-verification display: AI response với inline source attribution (highlight claim → show source doc)
  - Entity alias management UI: suggestion popup khi phát hiện alias tiềm năng

---

### Sprint 5: Tối ưu hóa & Đóng gói (Tuần 11-12)
*Mục tiêu: Kiểm thử hệ thống và tinh chỉnh UX.*

- **Testing:**
  - **Unit Tests:**
    - `test_sm2_algorithm.py` — test mọi branch của SM-2: quality 0-5, edge cases (first review, reset, overflow)
    - `test_examiner_agent.py` — test quiz generation với mock graph, test cross-verification
    - `test_note_service.py` — test backlink suggestion, test note CRUD
    - `test_cross_verification.py` — test矛盾 detection, test consolidation
    - `test_entity_alias_resolution.py` — test alias creation, test lookup
  - **Integration Tests:**
    - Full flow: `Upload Document → Graph Build → Generate Quiz → Submit Quiz → Wrong Answers → Create Flashcards → SM-2 Review`
    - Multi-doc: `Upload 2 Docs → Multi-doc Query → Cross-verification → Response`
    - Zettelkasten: `Create Note → AI Suggest Backlinks → Create Link → Graph View`
  - **Benchmark:**
    - Graph query performance: >1000 nodes, response time < 5s
    - Flashcard due query: >10K cards, response time < 200ms
    - ChromaDB multi-user isolation: verify 0 leak giữa users

- **Polish:**
  - Mobile responsive layout cho Flashcard review, Quiz, Note editor
  - Lazy loading cho Global Graph (>500 nodes → virtual rendering)
  - Optimistic updates cho flashcard review (UI update trước khi API respond)
  - Error handling chi tiết:
    - SM-2 review fail → retry với warning
    - Quiz generation timeout → partial quiz delivery
    - Backlink AI service down → fallback keyword matching
  - LLM Mode Badge enhancement: hiển thị Agent hiện tại (Socratic / Examiner / Backlink AI)

- **Documentation:**
  - Cập nhật `README.md` với Stage 2 features
  - User guide: "Cách sử dụng Flashcards + SM-2", "Cách tạo Quiz", "Zettelkasten basics"
  - API documentation update (OpenAPI spec)

---

## 4. Đặc tả kỹ thuật bổ sung (Technical Requirements)

### 4.1 Cập nhật Database Schema
- **Sprint 0:** Kích hoạt toàn bộ bảng Stage 2 theo DDL trong `Data_Model.md`
  - `notes`, `note_links`, `flashcards`, `study_sessions`, `quizzes`, `quiz_results`, `quiz_answers`, `entity_aliases`
- **Indexing strategy:**
  - `idx_flashcards_next_review` — Partial index: `WHERE sm2_next_review <= NOW()`
  - `idx_flashcards_user_due` — Composite: `(user_id, sm2_next_review)`
  - `idx_notes_tags_gin` — GIN index cho tags array
  - `idx_graph_relations_entity_fk_source` / `_target` — FK indexes sau khi migration sang UUID
  - `idx_entity_aliases_canonical` / `_alias` — B-tree indexes

### 4.2 Cấu hình Constants (`app/constants.py`)
```python
# Stage 2 Additions
SM2_INITIAL_EASE = 2.5
SM2_MIN_EASE = 1.3
MAX_QUIZ_QUESTIONS = 20
NOTE_LINK_SUGGESTION_THRESHOLD = 0.75
SM2_DEFAULT_QUALITY = 3
QUIZ_DIFFICULTY_SCALE_MIN = 1
QUIZ_DIFFICULTY_SCALE_MAX = 5
BACKLINK_AI_MODEL_MAX_TOKENS = 500
ENTITY_ALIAS_SIMILARITY_THRESHOLD = 0.8
CROSS_VERIFICATION_CONFLICT_THRESHOLD = 0.6
SM2_DAILY_DIGEST_CRON = "0 8 * * *"  # 8:00 AM daily
REDIS_DISTRIBUTED_LOCK_TTL = 60  # seconds

# Data Cleaning (Sprint 0)
ENTITY_NAME_FUZZY_THRESHOLD = 0.85
MAX_UNRESOLVED_ENTITY_PERCENTAGE = 5  # Dừng migration nếu > 5%

# Storage Abstraction (Sprint 0)
GRAPH_STORAGE_BACKEND = "local"  # "local" | "s3"
GRAPH_STORAGE_PATH = "/app/uploads/graphs"

# Quiz Feedback Loop (Sprint 2)
QUIZ_QUALITY_RATING_MIN = 1
QUIZ_QUALITY_RATING_MAX = 5
QUIZ_FEEDBACK_FLAG_THRESHOLD = 2  # Flag quiz nếu rating <= 2
QUIZ_FEEDBACK_ANALYSIS_CRON = "0 3 * * 0"  # Sunday 3 AM

# Notification Strategy (Sprint 1)
NOTIFICATION_BROWSER_ENABLED = True
NOTIFICATION_EMAIL_ENABLED = True  # Requires SMTP_HOST, SMTP_USER
NOTIFICATION_TELEGRAM_ENABLED = False  # Stage 3
```

### 4.3 Idempotency Design
- **Flashcard review endpoint:** Client gửi `X-Idempotency-Key` header (UUID)
- Server lưu key → result mapping trong Redis (TTL 24h)
- Nếu key tồn tại → trả về cached result, không cập nhật SM-2 lần nữa
- **Quiz submit:** Tương tự, prevent double-submit

### 4.4 Background Jobs (ARQ) Schedule
| Job | Schedule | Purpose | Lock |
|---|---|---|---|
| `sm2_daily_digest_task` | Cron: 8:00 AM | Quét due cards, notify user | Per-user lock (TTL 60s) |
| `backlink_suggestion_task` | On note create/update | AI gợi ý backlinks | Per-note lock (TTL 30s) |
| `entity_alias_suggestion_task` | Weekly (Sunday 3 AM) | Gợi ý entity aliases mới | Global lock (TTL 300s) |

---

## 5. Risk & Mitigation

| # | Rủi ro | Mức độ | Mitigation |
|---|--------|--------|-----------|
| **R1** | Migration `graph_relations` String → UUID FK làm hỏng dữ liệu | 🔴 Cao | Backup DB trước, chạy thử trên staging, có rollback script |
| **R1.1** | **Data Cleaning không resolve được > 5% entity names** | 🔴 Cao | DỪNG migration, manual review toàn bộ unresolved entities trước khi tiếp tục. Script báo cáo chi tiết `unresolved_entities.csv` |
| **R2** | ChromaDB rebuild làm mất embeddings | 🔴 Cao | Export embeddings ra file trước khi rebuild, có script re-ingest |
| **R3** | SM-2 scheduler chạy duplicate jobs | 🟡 Trung bình | Redis distributed lock + idempotency key cho review endpoint |
| **R4** | Quiz AI sinh câu hỏi vô nghĩa / sai | 🟡 Trung bình | Human-in-the-loop: review sample 50 quizzes trước khi release, thêm user feedback "Báo cáo câu hỏi sai" |
| **R5** | Backlink AI gợi ý quá nhiều links nhiễu | 🟡 Trung bình | Threshold cao (0.75), user có thể dismiss/confirm suggestions |
| **R6** | Global Graph quá lớn (>5000 nodes) làm frontend lag | 🟡 Trung bình | Virtual rendering, pagination, level-of-detail (chỉ load nodes gần viewport) |
| **R7** | Timeline 12 tuần quá gấp | 🟡 Trung bình | Ưu tiên: Sprint 0 → Sprint 1 → Sprint 2 (core value). Sprint 3-4 có thể delay sang Stage 3 nếu cần |
| **R8** | LLM cost tăng đột biến (quiz generation + backlink AI) | 🟢 Thấp | Cache kết quả AI, rate limit per user, dùng Ollama cho tasks không cần GPT |
| **R9** | **Graph storage local disk mất dữ liệu khi container restart** | 🟡 Trung bình | Storage Abstraction layer (`LocalStorage` → `S3Storage`), config env var để switch backend |
| **R10** | **Notification delivery rate thấp (user không bật permission)** | 🟡 Trung bình | Multi-channel fallback: Browser → Email → (Stage 3: Telegram). Theo dõi metric `% users enabled notifications` |

---

## 6. Chỉ số thành công (Success Criteria)

| Metric | Target | Measurement Method |
| :--- | :--- | :--- |
| **Độ chính xác Quiz** | > 85% câu hỏi có ý nghĩa sư phạm | Manual review sample 50 quizzes bởi tutor |
| **Hiệu quả ghi nhớ** | Tăng ≥ 15% recall rate sau 1 tuần SM-2 | So sánh quiz scores trước/sau 1 tuần |
| **Tính kết nối** | Trung bình mỗi Note có ≥ 2 backlinks | Query `note_links` table avg per note |
| **Multi-doc reasoning** | Response time < 5 giây | Benchmark API `/graph/query` với 5+ documents |
| **Cross-verification accuracy** | > 80%矛盾 phát hiện đúng | Manual review sample 30 cross-doc queries |
| **User engagement** | > 60% users dùng Flashcard/Quiz ít nhất 1 lần/tuần | Analytics dashboard |
| **System reliability** | < 1% error rate cho SM-2 review endpoint | Monitor HTTP 5xx rate |

---

## 7. Phụ lục: Mapping giữa Stage 2 Plan và Codebase hiện tại

| Stage 2 Requirement | File/Module hiện tại | Trạng thái |
|---|---|---|
| Flashcard model | ❌ Chưa tồn tại | Tạo mới trong Sprint 0 migration |
| StudySession model | ❌ Chưa tồn tại | Tạo mới trong Sprint 0 migration |
| Note/NoteLink model | ❌ Chưa tồn tại | Tạo mới trong Sprint 0 migration |
| Quiz/QuizResult model | ❌ Chưa tồn tại | Tạo mới trong Sprint 0 migration |
| FlashcardRepository | ❌ Chưa tồn tại | Tạo trong Sprint 1 |
| SM2Service | ❌ Chưa tồn tại | Tạo trong Sprint 1 |
| ExaminerAgent | ❌ Chưa tồn tại | Tạo trong Sprint 2 |
| GraphBuilder | ⚠️ Stub (`app/core/graph_builder.py`) | Implement trong Sprint 0 |
| **StorageProvider** | ❌ Chưa tồn tại | Tạo `app/core/storage_provider.py` trong Sprint 0 |
| **Data Cleaning Script** | ❌ Chưa tồn tại | Tạo `scripts/clean_entity_names.py` trong Sprint 0 |
| Retriever (multi-doc) | ⚠️ Chỉ support single doc (`app/core/retriever.py`) | Nâng cấp Sprint 4 |
| entity_aliases table | ❌ Chưa tồn tại | Tạo trong Sprint 0 migration |
| ChromaDB user_id filter | ❌ Chưa có | Thêm trong Sprint 0 |
| Auth middleware | ❌ Chưa tồn tại | Tạo trong Sprint 0 |
| ARQ background jobs | ✅ Đã có infrastructure (`app/worker/`) | Mở rộng trong Sprint 1, 2, 3, 4 |
| Zustand stores | ✅ 3 stores hiện tại | Thêm 3 stores mới |
| React Flow | ✅ Đã dùng trong GraphExplorer | Reuse cho Zettelkasten Graph View |
| SSE streaming | ✅ Đã có (`chat_service.py`) | Reuse cho quiz generation streaming |
| **Quiz Feedback endpoint** | ❌ Chưa tồn tại | Tạo trong Sprint 2 |
| **Notification service** | ❌ Chưa tồn tại | Tạo `app/services/notification_service.py` Sprint 1 |

---

## 8. Lịch trình Milestone tổng quát

| Milestone | Tuần | Deliverable |
|---|---|---|
| **Sprint 0 Complete** | 2 | Multi-tenant DB, Auth middleware, GraphBuilder, ChromaDB isolation, API spec updated |
| **Sprint 1 Complete** | 4 | Flashcard review, SM-2 algorithm, Daily digest job, Flashcard UI |
| **Sprint 2 Complete** | 6 | ExaminerAgent, Quiz generation, Quiz UI, Wrong-answer-to-flashcard |
| **Sprint 3 Complete** | 8 | Zettelkasten editor, Backlink AI, Note Graph View |
| **Sprint 4 Complete** | 10 | Multi-doc retrieval, Cross-verification, Global Graph Explorer |
| **Sprint 5 Complete** | 12 | Full test suite, Benchmark passed, Mobile responsive, Documentation |

---

## 9. Đề xuất cho Stage 3 (Post-Stage 2 Roadmap)

> Các tính năng sau được xác định là **có giá trị cao** nhưng **không urgent** cho Stage 2. Ưu tiên evalutate sau khi Stage 2 stable.

### 9.1 ModelRouter — Auto-Failover LLM (Ollama ↔ OpenAI)
- **Vấn đề:** Ollama local có thể timeout khi generate quiz 20 câu (đặc biệt với model nhỏ). OpenAI đắt nhưng nhanh và chính xác hơn.
- **Thiết kế:**
  ```python
  class ModelRouter:
      async def generate(
          self, prompt, priority: Literal["cost", "quality", "speed"] = "cost"
      ) -> str:
          if priority == "cost":
              try:
                  return await ollama_client.generate(prompt, timeout=30)
              except (TimeoutError, ConnectionError):
                  logger.warning("Ollama timeout, falling back to OpenAI")
                  return await openai_client.generate(prompt)
          elif priority == "quality":
              return await openai_client.generate(prompt, model="gpt-4")
          else:  # speed
              return await openai_client.generate(prompt, model="gpt-3.5-turbo")
  ```
- **Config:** `LLM_FAILOVER_ENABLED=true`, `LLM_DEFAULT_PRIORITY=cost`
- **Chi phí ước tính:** ~1 ngày implement, test tích hợp với `LLMService` hiện tại
- **Khi nào implement:** Khi có ≥ 10 active users và chi phí LLM tăng > $50/tháng

### 9.2 PWA (Progressive Web App) — Offline Flashcard Support
- **Vấn đề:** User muốn ôn flashcard trên mobile khi không có mạng. SM-2 vô dụng nếu không có offline mode.
- **Scope:**
  - Service Worker cache: Pre-fetch due cards khi có mạng
  - IndexedDB lưu `dueCards[]` local → review offline
  - Sync queue: Lưu review results local → sync khi có mạng
  - Manifest.json: "Add to Home Screen" support
- **Chi phí ước tính:** ~3-5 ngày
- **Khi nào implement:** Sau khi Stage 2 stable, có user feedback yêu cầu offline mode

### 9.3 Agent Memory / Shared Context (Socratic ↔ Examiner)
- **Vấn đề:** Examiner không biết user đã struggle với concepts nào khi chat với Socratic Tutor → quiz không cá nhân hóa.
- **Thiết kế:**
  - Bảng `agent_memories` (`user_id`, `agent_name`, `context_json`, `created_at`)
  - Socratic Tutor lưu: `{"topic": "Neural Networks", "struggle_points": ["backpropagation", "activation functions"], "timestamp": "..."}`
  - Examiner đọc context khi generate quiz → tăng weight cho entities trong `struggle_points`
- **Chi phí ước tính:** ~2-3 ngày
- **Khi nào implement:** Stage 3, sau khi đã có đủ user data để phân tích patterns

### 9.4 Global Graph Performance Upgrade (Sigma.js / Cytoscape.js)
- **Vấn đề:** React Flow có thể lag với > 2000 nodes dù có virtual rendering.
- **Giải pháp:**
  - **Sigma.js:** Chuyên cho graph visualization lớn (10K+ nodes), WebGL-based
  - **Cytoscape.js:** Layout algorithms mạnh hơn (force-directed, circular, hierarchical)
  - **Hybrid approach:** React Flow cho document-level graph (< 500 nodes), Sigma cho global graph
- **Khi nào evaluate:** Sprint 5 benchmark — nếu response time > 5s với 1000 nodes

### 9.5 Fine-tuning ExaminerAgent từ Feedback Data
- **Vấn đề:** Prompt hardcoded không thích nghi với user feedback.
- **Thiết kế:**
  - Export feedback data hàng tuần → analyze patterns
  - Auto-adjust prompt parameters (distractor count, difficulty distribution)
  - Long-term: Fine-tune open-source model (Qwen2.5-7B) trên quiz dataset
- **Khi nào implement:** Khi có ≥ 500 quiz feedbacks

---

© 2026 AetherTutor Team. Dự án chuyển mình sang giai đoạn thông minh hóa.
