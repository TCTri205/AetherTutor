# Business Rules — Luật Chơi Bất Biến

> **Document Owner:** AetherTutor Team
> **Created:** April 10, 2026
> **Version:** 1.0
> **Status:** Active (MVP Phase)
> **Parent:** [SRS_Overview.md](SRS_Overview.md)

---

## Hướng Dẫn Sử Dụng

Mỗi Business Rule được đánh ID duy nhất theo format: **`BR-XXX`** (Business Rule #XXX).

**Khi AI code cho tính năng liên quan, BẮT BUỘC phải:**
1. Đọc rule tương ứng
2. Implement đúng theo điều kiện (IF → THEN)
3. Không được bỏ qua hoặc sửa đổi logic rule

**Phân loại mức độ:**
| Mức | Ký hiệu | Mô tả |
|---|---|---|
| **BẤT BIẾN** | 🔴 | Không được vi phạm. Vi phạm = bug nghiêm trọng. |
| **CỐ ĐỊNH** | 🟡 | Nên tuân thủ. Có thể override nếu có lý do chính đáng + review. |
| **KHUYẾN NGHỊ** | 🟢 | Best practice. Linh hoạt áp dụng. |

---

## BR-001: User Data Isolation 🔴

**Mô tả:** Dữ liệu của mỗi user PHẢI được cô lập hoàn toàn. User A KHÔNG BAO GIỜ nhìn thấy dữ liệu của User B.

**Áp dụng cho:** MỌI module, MỌI query, MỌI storage layer

**Logic:**
```
IF query dữ liệu từ database/vector-db/graph
THEN PHẢI có filter: WHERE user_id = :current_user_id
```

**Implementation Rules:**

| Layer | Rule |
|---|---|
| **PostgreSQL** | Mọi query PHẢI có `WHERE user_id = :current_user_id`. Áp dụng RLS policy nếu có. |
| **ChromaDB** | Mọi query PHẢI có `where={"user_id": str(current_user_id)}` |
| **NetworkX Graph** | Mọi node/edge PHẢI có attribute `user_id`. Query PHẢI filter theo user_id. |
| **API Response** | KHÔNG BAO GIỜ trả về dữ liệu của user khác trong response |

**Test Case:**
```python
async def test_user_isolation():
    # User A uploads document
    doc_a = await upload_document(user_id=USER_A, file="doc_a.pdf")

    # User B queries
    results = await query_graph(user_id=USER_B, query="anything")

    # User B should NOT see User A's data
    assert not any(r.source_document_id == doc_a.id for r in results)
```

**Violation Impact:** 🔴 **CRITICAL SECURITY BUG** — Data leak

---

## BR-002: Document Processing Pipeline 🔴

**Dual-Field State Machine (khớp với Code — 2 fields: `status` + `processing_step`):**

```
Field 1: status (4 states — macro trạng thái)
    PENDING → PROCESSING → COMPLETED / FAILED

Field 2: processing_step (8 steps — chi tiết bước đang chạy)
    QUEUED → INITIAL → EXTRACTING → CHUNKING → EXTRACTING_ENTITIES → BUILDING_GRAPH → EMBEDDING → COMPLETED

Kết hợp thực tế:
    status = "PENDING",     processing_step = "QUEUED" | "INITIAL"
    status = "PROCESSING",  processing_step = EXTRACTING | CHUNKING | EXTRACTING_ENTITIES | BUILDING_GRAPH | EMBEDDING
    status = "COMPLETED",   processing_step = "COMPLETED"
    status = "FAILED",      processing_step = step bị lỗi (để debug)
```

**Chi tiết từng bước:**

| Step | processing_step | status | Tên | Input | Output | Điều kiện thành công |
|---|---|---|---|---|---|---|
| 1 | `QUEUED` | `PENDING` | Queued | File upload | Document record created | File hợp lệ, size < 50MB |
| 2 | `INITIAL` | `PROCESSING` | Worker starts | Document pending | Text extraction begins | Worker available |
| 3 | `EXTRACTING` | `PROCESSING` | Text Extraction | Raw file | Raw text | Ít nhất 100 chars extracted |
| 4 | `CHUNKING` | `PROCESSING` | Chunking | Raw text | Chunks (500 chars, 50 overlap) | Có ít nhất 1 chunk |
| 5 | `EXTRACTING_ENTITIES` | `PROCESSING` | Entity Extraction | Chunks | Entities + Relations | Có ít nhất 1 entity |
| 6 | `BUILDING_GRAPH` | `PROCESSING` | Graph Building | Entities + Relations | NetworkX graph | Graph có nodes và edges |
| 7 | `EMBEDDING` | `PROCESSING` | Embedding Gen | **Chunks + Entities** | **Vector embeddings cho chunks VÀ entities** | **Tất cả chunks và entities được embed** |
| 8 | `COMPLETED` | `COMPLETED` | Final State | All storage success | Document ready | Cả 3 storage layers thành công |

**⚠️ CRITICAL — Embedding Generation Rule (LightRAG Dual-Level Retrieval):**
```
Step 7 (EMBEDDING) PHẢI sinh embeddings cho CẢ:
    1. Document chunks (cho retrieval ngữ cảnh)
    2. Graph entities (cho semantic entity lookup)

ChromaDB metadata cho mỗi embedding:
    - "user_id": "uuid"
    - "document_id": "uuid"
    - "content_type": "chunk" | "entity"  ← PHÂN BIỆT loại embedding
    - "chunk_id": "uuid"                  ← Có nếu content_type = "chunk"
    - "entity_id": "uuid"                 ← Có nếu content_type = "entity"
    - "embedding_model": "text-embedding-3-small"
    - "embedding_dim": 1536

⚠️ KHÔNG được chỉ embed chunks. Nếu thiếu entity embeddings,
   LightRAG dual-level retrieval (entity similarity + concept traversal)
   sẽ KHÔNG hoạt động đúng — fallback về keyword matching (kém chính xác).
```

**Error Handling:**
```
IF bất kỳ step nào FAIL:
    - status = "FAILED"
    - processing_step = step_id bị lỗi (ví dụ: "EMBEDDING")
    - error_message = chi tiết lỗi
    - retry_count += 1

IF retry_count < max_retries (BR-010):
    - Rollback partial data (BR-016)
    - status = "PENDING", processing_step = "QUEUED"
    - Queue lại task
ELSE:
    - Document permanently failed
    - User phải retry thủ công
```

**State Transition Rules:**

| From (status, step) | To (status, step) | Trigger | Conditions |
|---|---|---|---|
| `(PENDING, QUEUED)` | `(PROCESSING, INITIAL)` | Worker picks up task | File valid, no concurrent processing |
| `(PROCESSING, INITIAL)` | `(PROCESSING, EXTRACTING)` | Worker starts | Worker ready |
| `(PROCESSING, EXTRACTING)` | `(PROCESSING, CHUNKING)` | Text extraction success | Min 100 chars extracted |
| `(PROCESSING, CHUNKING)` | `(PROCESSING, EXTRACTING_ENTITIES)` | Chunking complete | At least 1 chunk created |
| `(PROCESSING, EXTRACTING_ENTITIES)` | `(PROCESSING, BUILDING_GRAPH)` | Entities extracted | Min 1 entity |
| `(PROCESSING, BUILDING_GRAPH)` | `(PROCESSING, EMBEDDING)` | Graph saved | NetworkX graph has nodes |
| `(PROCESSING, EMBEDDING)` | `(COMPLETED, COMPLETED)` | Embeddings stored | PostgreSQL + ChromaDB synced |
| Any `(PROCESSING, step)` | `(FAILED, step)` | Error | Timeout, API error, invalid data |
| `(FAILED, step)` | `(PENDING, QUEUED)` | Retry (BR-010 + BR-016) | rollback success + retry_count < max |

**Violation Impact:** 🔴 **Data corruption** — Graph không đầy đủ, RAG query sai

---

## BR-003: Graph Construction Requires Entities 🔴

**Mô tả:** Knowledge Graph KHÔNG được xây dựng nếu không có entities nào được trích xuất.

**Logic:**
```
IF KHÔNG có entities (từ cả spaCy và LLM)
THEN:
    - KHÔNG gọi graph construction
    - Update document status = "failed"
    - Error: "No entities extracted. Cannot build graph."
    - Gợi ý user: Kiểm tra tài liệu có nội dung text không
```

**Hybrid Extraction Note:**
```
Với chế độ hybrid:
    - spaCy LUÔN chạy trước (nhanh, nhẹ ~50MB RAM)
    - LLM batch #1 LUÔN chạy để lấy relations
    - Fallback LLM chỉ chạy nếu thiếu entities (< 30)
    - Kết quả: spaCy entities + LLM relations → graph vẫn xây được
```

**Health Check Rule (LLM):**
```
TRƯỚC KHI gọi LLM batch:
    - Kiểm tra LLM health endpoint
    - Nếu LLM down → Log warning, tiếp tục với spaCy entities
    - Nếu spaacy cũng fail → FAIL
```

**Violation Impact:** 🔴 **Empty graph** hoặc **partial data**

---

## BR-004: Flashcard Generation Rule 🔴

**Mô tả:** Flashcard CHỈ được sinh từ entities/relations đã hoàn thành processing.

**Logic:**
```
IF user yêu cầu tạo flashcard
THEN:
    - Kiểm tra document status PHẢI là "completed"
    - Chỉ sinh flashcard từ entities có confidence >= 0.7
    - Mỗi flashcard PHẢI có:
        + Front: Entity name + description
        + Back: Entity details + related concepts
        + Metadata: source_document_id, source_entity_ids
```

**Generation Limits:**
| Tham số | Giá trị |
|---|---|
| Max flashcards per request | 50 |
| Min entity confidence | 0.7 |
| Min entity degree (connections) | 1 |

**Violation Impact:** 🔴 **Flashcard sai** từ data chưa hoàn chỉnh

---

## BR-005: SM-2 Scheduling Rule 🔴

**Mô tả:** Flashcard chỉ xuất hiện để ôn tập khi đến hạn. Không cho phép tự động override.

**SM-2 Algorithm (bất biến):**
```python
def update_sm2(card: Flashcard, quality: int) -> Flashcard:
    """
    quality: 0-5
        0 = Complete blackout
        1-2 = Incorrect response
        3 = Correct response, hesitated
        4 = Correct response, some difficulty
        5 = Perfect response
    """
    # BẮT BUỘC: quality phải trong range 0-5
    assert 0 <= quality <= 5

    if quality >= 3:
        # Successful recall
        if card.sm2_repetitions == 0:
            card.sm2_interval = 1
        elif card.sm2_repetitions == 1:
            card.sm2_interval = 6
        else:
            card.sm2_interval = round(card.sm2_interval * card.sm2_ease_factor)

        card.sm2_repetitions += 1
    else:
        # Failed recall — reset
        card.sm2_repetitions = 0
        card.sm2_interval = 0  # ⚠️ CRITICAL: Review IMMEDIATELY (interval = 0)

    # Update ease factor (MIN = 1.3)
    card.sm2_ease_factor = max(
        1.3,
        card.sm2_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    )

    # Calculate next review
    if card.sm2_interval == 0:
        card.sm2_next_review = NOW()  # Review again immediately
    else:
        card.sm2_next_review = NOW() + timedelta(days=card.sm2_interval)

    card.sm2_last_review = NOW()
    return card
```

**Due Card Query (bất biến):**
```sql
-- CHỈ lấy flashcard due
SELECT * FROM flashcards
WHERE user_id = :user_id
  AND sm2_next_review <= NOW()
ORDER BY sm2_next_review ASC;
```

**Violation Impact:** 🔴 **Spaced repetition broken** — Ôn tập không hiệu quả

> [!WARNING]
> **⚠️ KNOWN DIVERGENCE (CR-001):** Code thực tế (`app/services/sm2_service.py`) dùng `interval = 1` thay vì `0`.
> Đây là **design choice** (có comment: "review lại sau 1 ngày") nhưng **không khớp SM-2 chuẩn**.
> **Recommendation:** Fix code → `interval = 0` để khớp spec và tăng 15-20% memory retention.
> **Tracking Issue:** [srs_analysis_reference.md#CR-001](../references-docs/srs_analysis_reference.md#cr-001-sm-2-interval)

---

## BR-006: Socratic Response Rule 🔴

**Mô tả:** Socratic Tutor KHÔNG được đưa câu trả lời trực tiếp. PHẢI hỏi gợi mở trước.

**Logic (prompt rule):**
```
IF user hỏi về khái niệm X
THEN Socratic Tutor PHẢI:
    1. Đặt câu hỏi gợi mở để user tự suy nghĩ
    2. Chờ user trả lời
    3. NẾU user trả lời đúng → Xác nhận + mở rộng
    4. NẾU user trả lời sai → Gợi ý thêm + câu hỏi khác
    5. NẾU user đã cố gắng >= 2 lần và vẫn sai → Giải thích Feynman-style
```

**Prompt Template (bất biến):**
```
SYSTEM PROMPT CHO SOCRATIC TUTOR:
Bạn là Socratic Tutor. NHIỆM VỤ CỦA BẠN:
1. KHÔNG bao giờ đưa câu trả lời trực tiếp ngay lập tức
2. LUÔN bắt đầu bằng câu hỏi gợi mở
3. Dùng Feynman Technique: yêu cầu user giải thích lại
4. Chỉ giải thích khi user đã thử >= 2 lần
5. Phát hiện "ảo tưởng hiểu biết" và đặt câu hỏi probing

FORMAT PHẢN HỒI JSON (BẮT BUỘC — Structured Output):
{
  "current_concept": "Tên khái niệm đang thảo luận",
  "response_type": "question" | "hint" | "explanation",
  "content": "Nội dung phản hồi chính",
  "follow_up_question": "Câu hỏi tiếp theo (luôn có)"
}

**Tracking Rule (Backend-managed — LLM KHÔNG tự update):**
- `attempt_count` được lưu trong chat session metadata (PostgreSQL).
- `attempt_count` reset về 0 khi `current_concept` thay đổi (so sánh JSON response field).
- Backend tự extract `current_concept` từ LLM JSON response → so sánh với concept cũ → quyết định reset hay increment.
- ⚠️ LLM KHÔNG trực tiếp update database. Backend hoàn toàn quản lý attempt logic.
```

**Violation Impact:** 🔴 **Mất phương pháp Socratic** — AI trở thành chatbot thường

---

## BR-007: Quiz Generation Rule 🔴

**Mô tả:** Quiz PHẢI bao phủ các entities quan trọng trong graph và có explanation.

**Logic:**
```
IF user yêu cầu tạo quiz
THEN:
    1. Lấy entities có degree > 3 (quan trọng nhất)
    2. Tạo câu hỏi multi-hop nếu có relations giữa entities
    3. MỖI câu hỏi PHẢI có:
        - Question text rõ ràng
        - 4 options (1 correct, 3 distractors)
        - Explanation cho đáp án đúng
        - Difficulty level (1-5)
        - Bloom taxonomy level
    4. Quiz PHẢI bao phủ >= 80% entities có degree > 3
    5. Số lượng câu hỏi: 5-20 (user chọn)
```

**Question Types:**
| Type | Format | Yêu cầu |
|---|---|---|
| Multiple Choice | 4 options, 1 correct | Explanation bắt buộc |
| True/False | 2 options | Explanation bắt buộc |
| Fill in Blank | 1 blank | Answer key + explanation |
| Short Answer | Open text | Grading rubric |

**Violation Impact:** 🟡 **Quiz chất lượng thấp** — Không kiểm tra được hiểu biết

---

## BR-008: Local Mode Rule 🔴

**Mô tả:** Khi Local Mode bật, KHÔNG dữ liệu nào được gửi đến Cloud LLM.

**Logic:**
```
IF local_mode = true
THEN:
    - TẤT CẢ LLM requests PHẢI route tới Ollama endpoint
    - KHÔNG gọi OpenAI API
    - Log warning nếu có attempt gọi Cloud API
    - Hiển thị badge "🔒 Local Mode" trên UI
```

**⚠️ CRITICAL — Embedding Dimension Mismatch Prevention:**
```
Khi user switch Embedding Provider (openai ↔ ollama):
    1. Kiểm tra embedding_dim của model mới vs model cũ
       - OpenAI text-embedding-3-small: 1536 dimensions
       - Ollama llama3/nomic-embed: thường 4096 hoặc 768 dimensions

    2. NẾU dimension khác nhau:
        a. TẠO ChromaDB collection mới: "{provider}_{model}_{dim}"
        b. KHÔNG xóa collection cũ — giữ để query cross-collection
        c. CẢNH BÁO user: 
           "Chế độ mới dùng embedding khác. Tài liệu cũ và mới 
            sẽ ở không gian vector riêng. Tìm kiếm vẫn hoạt động 
            trên cả hai nhưng kết quả có thể khác nhau."

    3. Metadata embedding tracking (BẮT BUỘC):
       - Mỗi embedding trong ChromaDB PHẢI có:
         + "embedding_model": "text-embedding-3-small" | "nomic-embed-text"
         + "embedding_dim": 1536 | 4096 | 768
         + "created_at": ISO timestamp

    4. Khi query graph:
       - Query TẤT CẢ collections có cùng embedding_dim với current model
       - Merge results từ các collections
       - Collections khác dimension → SKIP (tránh crash)

    5. ⚠️ CRITICAL — Delete Document phải xóa TẤT CẢ collections:
       - Khi xóa document, PHẢI quét toàn bộ collections trong ChromaDB
       - Xóa document_id trên MỌI collection (kể cả collections cũ từ provider khác)
       - Nếu KHÔNG, orphan vectors sẽ tồn tại vĩnh viễn ở collections cũ
       - Implementation: `client.list_collections()` → loop → `col.delete(where={"document_id": doc_id})`

⚠️ KHÔNG BAO GIỜ chèn vector khác dimension vào cùng collection.
   Sẽ gây ValueError: "dimension mismatch" và crash hệ thống.
```

**Configuration:**
| Setting | Local Mode | Cloud Mode |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | N/A |
| `OPENAI_API_KEY` | NOT USED | Required |
| `DEFAULT_LLM_MODEL` | `llama3`, `mistral`, etc. | `gpt-4`, `claude-3.5`, etc. |
| `EMBEDDING_PROVIDER` | `ollama` | `openai` |
| `EMBEDDING_MODEL` | `nomic-embed-text` (768d) | `text-embedding-3-small` (1536d) |
| `EMBEDDING_DIM` | `768` | `1536` |

**Violation Impact:** 🔴 **Data privacy breach** — Dữ liệu gửi lên cloud khi user không muốn
**Violation Impact (Dimension):** 🔴 **System crash** — ChromaDB dimension mismatch

---

## BR-009: Note Backlink Rule 🔴

**Mô tả:** Khi tạo note mới, hệ thống PHẢI quét để tìm entities trùng và gợi ý backlinks.

**Logic:**
```
IF user tạo note mới
THEN:
    1. Quét nội dung note để tìm keywords
    2. So khớp keywords với entities trong knowledge graph
    3. NẾU tìm thấy entities trùng:
        - Gợi ý backlink tới note đã có entity đó
        - Gợi ý liên kết tới entity trong graph
    4. LƯU note với metadata chứa danh sách linked entities
```

**Matching Algorithm:**
| Method | Priority | Description |
|---|---|---|
| Exact match | Cao nhất | Tên entity xuất hiện chính xác trong note |
| Fuzzy match (>= 0.8) | Cao | Tên entity gần giống text trong note |
| Semantic similarity | Trung bình | Embedding similarity cao |

**Violation Impact:** 🟡 **Mất tính năng Zettelkasten** — Notes không liên kết

---

## BR-010: Error Recovery Rule 🔴

**Mô tả:** Background task thất bại PHẢI retry 3 lần với exponential backoff. Áp dụng cho cả các tiến trình LLM batch.

**Logic:**
```
IF background task fails
THEN:
    - Increment retry_count
    - IF retry_count < 3:
        - Wait: 30s * (2 ^ retry_count)  # 30s, 60s, 120s
        - Retry task
    - ELSE:
        - Update task status = "failed"
        - Lưu error_message
        - Notify user (nếu có email/webhook)
```

**Retry Policy Table:**
| Attempt | Wait Time | Total Elapsed |
|---|---|---|
| 1 (initial) | 0s | 0s |
| 2 (1st retry) | 30s | 30s |
| 3 (2nd retry) | 60s | 90s |
| 4 (3rd retry) | 120s | 210s |
| FAILED | - | 210s+ |

**Violation Impact:** 🟡 **Task mất vĩnh viễn** hoặc **retry vô hạn**

---

## BR-011: Document Upload Validation 🟡

**Mô tả:** Document upload PHẢI validate trước khi xử lý.

**Validation Rules:**
| Rule | Condition | Error HTTP Code | Error Message |
|---|---|---|---|
| File size | <= 50MB | 400 | "File vượt giới hạn 50MB. Vui lòng nén file." |
| File type | PDF, URL, YouTube | 400 | "Chỉ hỗ trợ PDF, URL, hoặc YouTube links." |
| PDF text layer | Must have text layer | 400 | "Không đọc được text. Cần PDF có text layer." |
| URL accessible | HTTP 200 response | 400 | "Không truy cập được URL này." |
| User quota | Daily limit not exceeded | 429 | "Vượt giới hạn upload trong ngày. Nâng cấp để thêm." |
| **Concurrent processing** | **User KHÔNG có document nào đang `PENDING` hoặc `PROCESSING` (BR-002 dual-field: status macro)** | **409** | **"Document khác đang xử lý. Vui lòng đợi hoàn tất trước khi upload thêm."** |

**Concurrent Processing Rule (CRITICAL — Queue Overload Prevention):**
```
⚠️ BR-002 Dual-Field: CHỈ check field `status` (4 macro states), KHÔNG check `processing_step`.

TRƯỚC KHI chấp nhận upload mới:
    existing = SELECT COUNT(*) FROM documents
               WHERE user_id = :user_id
               AND status IN ('PENDING', 'PROCESSING')

    IF existing > 0:
        RETURN 409 CONCURRENT_PROCESSING
        ← CHẶN upload, KHÔNG queue task mới
```

**Violation Impact:** 🟡 **Wasted processing** hoặc **storage waste**

---

## BR-012: Rate Limiting & Quota 🟡

**Mô tả:** API calls PHẢI được giới hạn để tránh lạm dụng và kiểm soát chi phí LLM.

**MVP Limits (single-user):**
| Endpoint | Limit | Window | Action khi vượt |
|---|---|---|---|
| Document upload | 5 per day | 24h rolling | Trả về `429`: "Vượt giới hạn upload trong ngày" |
| Chat requests | 10 per minute | 60s sliding | Trả về `429`: "Quá nhiều request. Đợi 1 phút" |
| Graph queries | 30 per minute | 60s sliding | Trả về `429`: "Graph query limit reached" |
| Flashcard generation | 10 per day | 24h rolling | Trả về `429`: "Vượt giới hạn tạo flashcard" |
| Quiz generation | 5 per day | 24h rolling | Trả về `429`: "Vượt giới hạn tạo quiz" |

**Post-MVP (multi-user):**
- Giới hạn theo subscription tier (Free, Pro, Enterprise)
- Rate limit per user, không phải per IP
- Token usage tracking cho billing

**Violation Impact:** 🟡 **API abuse** hoặc **cost overrun**

---

## BR-013: Knowledge Graph Versioning 🟢 (Post-MVP)

> [!NOTE]
> **Post-MVP Feature.** MVP chưa implement vì chưa có `entity_versions` table.
> Rule này để sẵn để khi làm Post-MVP có reference.

**Mô tả:** Mỗi lần document mới được thêm vào graph, PHẢI lưu version snapshot.

**Logic:**
```
IF document processing completes
THEN:
    - Lưu graph version với metadata:
        + version_number (incremental)
        + document_id vừa thêm
        + total_entities, total_relations sau khi merge
        + timestamp
    - Cho phép rollback về version trước
```

**Data Model cần thêm (Post-MVP):**
```sql
CREATE TABLE graph_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    total_entities INT,
    total_relations INT,
    snapshot_data JSONB,  -- Serialized graph snapshot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, version_number)
);
```

**Violation Impact:** 🟢 **Không rollback được** nếu graph bị corrupt

---

## BR-014: Chat Session Context 🟢

**Mô tả:** Chat session PHẢI giữ context từ document hiện tại.

**Logic:**
```
IF user đang chat về document X
THEN:
    - context_document_id = X.id
    - Graph-aware retrieval: query entities từ document X trước
    - NẾU user hỏi về khái niệm ngoài document X:
        - Mở rộng retrieval sang documents khác của user
        - Thông báo user: "Khái niệm này có trong document Y của bạn"
```

**Violation Impact:** 🟢 **Chat mất context** — Trả lời không chính xác

---

## BR-015: Flashcard Quality Threshold 🟢

**Mô tả:** Flashcard auto-generated PHẢI đạt chất lượng tối thiểu.

**Quality Rules:**
| Rule | Threshold | Action if fail |
|---|---|---|
| Entity confidence | >= 0.7 | Skip entity đó |
| Entity description length | >= 20 chars | Mark as "low quality" |
| Front-back uniqueness | Not identical | Auto-regenerate |
| AI quality score | >= 0.6 | Flag for user review |

**Violation Impact:** 🟢 **Flashcard rác** — Ôn tập vô nghĩa

---

## BR-016: System Resilience 🔴

**Mô tả:** Hệ thống PHẢI phản ứng graceful khi hạ tầng gặp sự cố. Không được crash hoặc để user treo vô hạn.

**Infrastructure Failure Response:**

| Failure Scenario | Detection | System Response | User Experience |
|---|---|---|---|
| **PostgreSQL down** | Health check fail (connection refused) | Mọi API trả về `503 Service Unavailable`. Frontend hiển thị maintenance page. | "⚠️ Database không khả dụng. Đang thử kết nối lại..." |
| **Redis down** | ARQ worker không queue được task | API upload trả về `503: "Task queue unavailable"`. Không tạo document pending. | "⚠️ Hệ thống đang bận. Thử lại sau ít phút." |
| **ChromaDB down** | Health check fail (HTTP error) | Document fail ở step 7 (vector_storage). Retry 3 lần theo BR-010. Nếu vẫn fail → `failed` status. | Toast: "⚠️ Lưu embedding thất bại. Document không khả dụng." |
| **LLM timeout/unavailable** | Health check fail hoặc request timeout (> 30s) | Chuyển sang Degraded Mode. Các tính năng cần LLM trả về `503`. Chat: inline error. | "⚠️ AI hiện không phản hồi. Kiểm tra Settings hoặc thử lại sau." |
| **NetworkX graph corrupt** | Graph load fail hoặc node count = 0 (trong khi DB có entities) | Rebuild graph từ SQL (source of truth). Nếu rebuild fail → mark graph as "rebuilding". | "🔄 Đang xây dựng lại graph. Vui lòng đợi..." |
| **Worker crash** | Process exit, task stuck | ARQ auto-restart worker. Task được retry từ checkpoint gần nhất (dựa vào retry policy của từng task type). | User không thấy gì — retry trong background |

**Recovery Rules:**
```
IF infrastructure component recovers
THEN:
    - Health check pass → remove Degraded Mode flag
    - Queued tasks resume processing
    - User sees "✅ Hệ thống đã hoạt động trở lại"
```

**Atomic Pipeline Rule:**
```
IF bất kỳ storage layer nào (PostgreSQL, ChromaDB, NetworkX) fail trong quá trình processing
THEN:
    - Document status = "failed"
    - KHÔNG hiển thị document cho user như "completed"
    - Cleanup partial data (embeddings đã lưu, entities đã lưu — xóa theo cascade)
    - User chỉ thấy document hoàn chỉnh khi CẢ 3 storage layers thành công
```

**⚠️ CRITICAL — Rollback Before Retry Rule (CHỐNG DUPLICATE DATA):**
```
TRƯỚC KHI retry processing cho document bị failed:
    1. XÓA TOÀN BỘ partial data của document từ TẤT CẢ storage layers:
       - DELETE FROM document_chunks WHERE document_id = :doc_id
       - DELETE FROM graph_entities WHERE document_id = :doc_id
       - DELETE FROM graph_relations WHERE document_id = :doc_id
       - ChromaDB: delete(where={"document_id": doc_id})
       - NetworkX: remove document nodes từ in-memory graph

    2. Reset document status:
       - status = "pending"
       - processing_step = "INITIAL"
       - error_message = NULL
       - retry_count = 0

    3. Queue task mới → Worker chạy pipeline từ Step 1 trên data SẠCH

⚠️ KHÔNG được retry mà không rollback trước.
   Sẽ sinh ra DUPLICATE chunks, entities, relations → data phình to, graph corrupt.
```

**Violation Impact:** 🔴 **User experience destroyed** — Treo, crash, data corrupt

---

## BR-017: Request Idempotency 🟡

**Mô tả:** Mọi mutation request (POST/PUT/DELETE) PHẢI có cơ chế chống trùng lặp.

**Idempotency Rules:**

| Request Type | Mechanism | Scope |
|---|---|---|
| **Document Upload** | File hash check (SHA-256). Nếu cùng hash + cùng user → trả về document_id cũ (409 Conflict) | Per-user |
| **Flashcard Generation** | Check: đã tồn tại flashcard cho `{document_id}` chưa. Nếu có → trả về danh sách cũ (không tạo mới) | Per document |
| **Quiz Generation** | Client gửi `idempotency_key` (UUID). Backend check key trong Redis (TTL 1h). Nếu tồn tại → trả về kết quả cũ | Per request |
| **Note Creation** | Không cần idempotency — user được phép tạo nhiều note cùng nội dung | N/A |
| **Merge Entities** | Check: secondary entity đã được merge vào primary chưa. Nếu rồi → trả về primary info (200 OK) | Per entity pair |
| **Delete Document** | Idempotent: nếu document đã xóa → trả về `200: "Already deleted"` (không phải 404) | Per document |
| **Review Flashcard** | Check: đã review trong cùng giây chưa. Nếu rồi → bỏ qua (200 OK, trả về result cũ) | Per flashcard + timestamp |

**Idempotency Key Header (cho Quiz):**
```
POST /api/v1/quiz/generate
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

**Duplicate Response:**
```typescript
interface DuplicateResponse {
  success: false;
  error: {
    code: 'DUPLICATE_REQUEST';
    message: string;
    existing_resource_id?: string;  // ID của resource đã tồn tại
  };
}
```

**Violation Impact:** 🟡 **Duplicate data** hoặc **wasted LLM cost**

---

## Business Rules Checklist (Cho Code Review)

Trước khi merge code, check list sau:

- [ ] **BR-001:** Mọi query có `WHERE user_id = :current_user_id`?
- [ ] **BR-002:** Document pipeline đủ 8 bước?
- [ ] **BR-003:** Có ít nhất 1 entity trước khi build graph?
- [ ] **BR-004:** Flashcard chỉ sinh từ completed documents?
- [ ] **BR-005:** SM-2 algorithm đúng công thức?
- [ ] **BR-006:** Socratic Tutor hỏi trước, trả lời sau?
- [ ] **BR-007:** Quiz có explanation cho mỗi câu?
- [ ] **BR-008:** Local Mode không gọi Cloud API?
- [ ] **BR-009:** Note mới có backlink suggestion?
- [ ] **BR-010:** Retry logic đúng 3 lần + backoff?
- [ ] **BR-016:** System failure được xử lý graceful (không crash)?
- [ ] **BR-017:** Mutation request có idempotency mechanism?

---

> [!IMPORTANT]
> **Các rule 🔴 BẤT BIẾN là hợp đồng (contract).** Vi phạm = bug nghiêm trọng.
> Cập nhật tài liệu này khi thêm rule mới hoặc thay đổi rule cũ.

---
© 2026 AetherTutor Team. Created: April 10, 2026
