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

**Mô tả:** Document PHẢI trải qua đúng 7 bước tuần tự theo State Machine. Không được bỏ qua bước nào.

**7 bước BẮT BUỘC (khớp Data_Model State Machine):**
```
Upload → pending → processing → chunking → entity_extraction → graph_construction → embedding_generation → completed
  (1)      (2)         (3)         (4)           (5)                 (6)                    (7)                  (8)
```

**Chi tiết từng bước:**

| Bước | State | Tên | Input | Output | Điều kiện thành công |
|---|---|---|---|---|---|
| 1 | `pending` | Upload | File PDF/URL | Document record (status: pending) | File hợp lệ, size < 50MB |
| 2 | `processing` | Start Processing | Document pending | Worker picks up task | Worker available |
| 3 | `chunking` | Extract & Chunk | Raw text | Chunks (500 chars, 50 overlap) | Ít nhất 100 chars extracted, ≥1 chunk |
| 4 | `entity_extraction` | Entity/Relation Extraction | Chunks | Entities + Relations từ spaCy + LLM (hybrid) | Có ít nhất 1 entity (spaCy hoặc LLM) |
| 5 | `graph_construction` | Graph Construction | Entities + Relations | NetworkX graph | Graph có nodes và edges |
| 6 | `embedding_generation` | Embedding Generation | Chunks | Vector embeddings | Tất cả chunks được embed |
| 7 | `completed` | All Storage Success | Embeddings + Graph | Document ready (PostgreSQL + ChromaDB + Graph) | Cả 3 storage layers thành công |

**State Machine (khớp Data_Model.md Section 4):**
```
pending → processing → chunking → entity_extraction → graph_construction → embedding_generation → completed
                ↓            ↓              ↓                    ↓                       ↓
              failed       failed         failed               failed                 failed

partial_failure → retry (max 3) → embedding_generation
                                → failed (retry exhausted)
```

**Logic:**
```
IF bất kỳ bước nào FAIL
THEN:
    - Update document status = "failed"
    - Lưu error_message vào document record
    - Retry tối đa 3 lần với exponential backoff (30s, 60s, 120s)
    - Sau 3 lần vẫn fail → Notify user
```

**State Transition Rules (khớp Data_Model):**

| From State | To State | Trigger | Conditions |
|---|---|---|---|
| `pending` | `processing` | Background worker picks up | File size < max, valid format |
| `processing` | `chunking` | Text extraction success | Min 100 chars extracted |
| `chunking` | `entity_extraction` | Chunking complete | At least 1 chunk created |
| `entity_extraction` | `graph_construction` | Entities extracted | Min 1 entity (spaCy or LLM) |
| `graph_construction` | `embedding_generation` | Graph saved | NetworkX graph has nodes |
| `embedding_generation` | `completed` | All storage success | PostgreSQL + ChromaDB + Graph |
| Any state | `failed` | Error with no retry | Timeout, invalid data, API error |
| `partial_failure` | `retry` | Some embeddings failed | Retry count < 3 |

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
        card.sm2_interval = 0

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

FORMAT PHẢN HỒI:
- Câu hỏi gợi mở (bắt buộc)
- Gợi ý nhỏ (nếu user đã thử 1 lần)
- Giải thích Feynman (nếu user đã thử >= 2 lần)
- Follow-up question (luôn có)
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

**Configuration:**
| Setting | Local Mode | Cloud Mode |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | N/A |
| `OPENAI_API_KEY` | NOT USED | Required |
| `DEFAULT_LLM_MODEL` | `llama3`, `mistral`, etc. | `gpt-4`, `claude-3.5`, etc. |
| `EMBEDDING_PROVIDER` | `ollama` | `openai` |

**Violation Impact:** 🔴 **Data privacy breach** — Dữ liệu gửi lên cloud khi user không muốn

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

**Mô tả:** Background task thất bại PHẢI retry 3 lần với exponential backoff.

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
| Rule | Condition | Error Message |
|---|---|---|
| File size | <= 50MB | "File vượt giới hạn 50MB. Vui lòng nén file." |
| File type | PDF, URL, YouTube | "Chỉ hỗ trợ PDF, URL, hoặc YouTube links." |
| PDF text layer | Must have text layer | "Không đọc được text. Cần PDF có text layer." |
| URL accessible | HTTP 200 response | "Không truy cập được URL này." |
| User quota | Daily limit not exceeded | "Vượt giới hạn upload trong ngày. Nâng cấp để thêm." |

**Violation Impact:** 🟡 **Wasted processing** hoặc **storage waste**

---

## BR-012: Rate Limiting & Quota 🟡

**Mô tả:** API calls PHẢI được giới hạn theo subscription tier.

**MVP Limits (single-user):**
| Endpoint | Limit | Window |
|---|---|---|
| Document upload | 5 per day | 24h rolling |
| Chat requests | 10 per minute | 60s sliding |
| Graph queries | 30 per minute | 60s sliding |
| Flashcard generation | 10 per day | 24h rolling |
| Quiz generation | 5 per day | 24h rolling |

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

## Business Rules Checklist (Cho Code Review)

Trước khi merge code, check list sau:

- [ ] **BR-001:** Mọi query có `WHERE user_id = :current_user_id`?
- [ ] **BR-002:** Document pipeline đủ 7 bước?
- [ ] **BR-003:** Có ít nhất 1 entity trước khi build graph?
- [ ] **BR-004:** Flashcard chỉ sinh từ completed documents?
- [ ] **BR-005:** SM-2 algorithm đúng công thức?
- [ ] **BR-006:** Socratic Tutor hỏi trước, trả lời sau?
- [ ] **BR-007:** Quiz có explanation cho mỗi câu?
- [ ] **BR-008:** Local Mode không gọi Cloud API?
- [ ] **BR-009:** Note mới có backlink suggestion?
- [ ] **BR-010:** Retry logic đúng 3 lần + backoff?

---

> [!IMPORTANT]
> **Các rule 🔴 BẤT BIẾN là hợp đồng (contract).** Vi phạm = bug nghiêm trọng.
> Cập nhật tài liệu này khi thêm rule mới hoặc thay đổi rule cũ.

---
© 2026 AetherTutor Team. Created: April 10, 2026
