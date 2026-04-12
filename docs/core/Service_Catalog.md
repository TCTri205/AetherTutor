# Service Catalog — AetherTutor Backend Services

> **Document Owner:** AetherTutor Team
> **Created:** April 12, 2026
> **Version:** 1.0
> **Status:** Active
> **Purpose:** Comprehensive documentation cho tất cả backend services

---

## Tổng Quan

AetherTutor có **25 service files** chia thành 4 nhóm:

| Nhóm | Số lượng | Mô tả |
|------|----------|-------|
| **Core Services** | 5 | Document, LLM, Embedding, ChromaDB, PDF |
| **Learning Services** | 6 | Flashcard, SM-2, Quiz, Note, Backlink, Cross-Verification |
| **Auth & User Services** | 4 | Auth, User, Security, Topic |
| **Integration Services** | 6 | Notification, Email, Obsidian, Entity Resolution, Tag, Code Parser |

---

## 1. Core Services

### 1.1 DocumentService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/document_service.py` |
| **Class** | `DocumentService` |
| **Purpose** | Quản lý document lifecycle: upload, validate, enqueue processing, delete |
| **Business Rules** | BR-002 (Processing Pipeline), BR-011 (Upload Validation), BR-016 (System Resilience) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `upload_document` | `(user_id, file, filename)` | Validate file, save to storage, create DB record, enqueue worker task | `Document` |
| `get_document` | `(user_id, doc_id)` | Get document detail with user isolation | `Document \| None` |
| `list_documents` | `(user_id, skip, limit)` | List user's documents with pagination | `List[Document]` |
| `delete_document` | `(user_id, doc_id)` | Atomically delete document + graph + Chroma data (UF-010) | `bool` |

**Dependencies:**
- `DocumentRepository`, `ChunkRepository`, `GraphRepository`
- `get_redis_pool()` (worker enqueue)
- `pdf_extractor`, `code_parser` (file validation)

**Error Handling:**
- `ValueError("File type not supported")` — Invalid extension
- `ValueError("File size exceeds limit")` — > 50MB
- `ResourceNotFoundError` — Document not found
- `ValidationError` — Duplicate content hash (409 Conflict)

---

### 1.2 LLMService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/llm_service.py` |
| **Class** | `LLMService` |
| **Purpose** | Abstraction layer cho LLM providers (OpenAI/Ollama) với retry và streaming |
| **Business Rules** | BR-008 (Local Mode) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `chat_completion` | `(messages, temperature, max_tokens)` | Standard chat completion | `str` |
| `chat_stream` | `(messages, temperature, max_tokens)` | Streaming chat (SSE-compatible) | `AsyncGenerator[str]` |
| `structured_extraction` | `(prompt, response_model, max_retries)` | Extract structured JSON from LLM | `BaseModel` |
| `health_check` | `()` | Check if LLM provider is reachable | `bool` |

**Properties:**
- `is_local` → True nếu dùng Ollama
- `is_cloud` → True nếu dùng OpenAI
- `provider` → Current provider name
- `model` → Current model name

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_LLM_MODEL` | `qwen2.5-1.5b` | LLM model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API URL |
| `OPENAI_API_KEY` | — | OpenAI API key |

**Error Handling:**
- Auto-retry với exponential backoff (max 3 lần)
- Fallback: OpenAI unavailable → log error, raise
- Structured output: Retry với different prompts nếu JSON parse fail

---

### 1.3 EmbeddingService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/embedding_service.py` |
| **Class** | `EmbeddingService` |
| **Purpose** | Tạo text embeddings cho vector search, hỗ trợ multi-provider |
| **Business Rules** | BR-008 (Embedding Dimension Mismatch Prevention) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `generate_embedding` | `(text: str)` | Tạo embedding cho 1 text | `List[float]` |
| `generate_embeddings` | `(texts: List[str])` | Batch embedding generation | `List[List[float]]` |
| `health_check` | `()` | Check if embedding provider is reachable | `bool` |

**Properties:**
- `is_local`, `is_cloud`, `provider`, `dimension`

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_PROVIDER` | `openai` | Provider selector |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI model |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model |
| `EMBEDDING_DIM_OPENAI` | 1536 | OpenAI embedding dimension |
| `EMBEDDING_DIM_OLLAMA` | 768 | Ollama embedding dimension |
| `EMBEDDING_BATCH_SIZE` | 100 | Max texts per batch |

**Auto-Fallback Logic:**
```
IF OpenAI API key invalid (starts with "your_")
THEN auto-switch to Ollama provider
```

---

### 1.4 ChromaClient

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/chroma_client.py` |
| **Class** | `ChromaClient` |
| **Purpose** | Enhanced ChromaDB client với collection caching và BR-002/BR-008 compliance |
| **Business Rules** | BR-002 (Content Type Enforcement), BR-008 (Multi-Collection Delete) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `add_chunks` | `(ids, documents, metadatas, embeddings)` | Add document chunks với auto `content_type="chunk"` | `None` |
| `add_entities` | `(ids, documents, metadatas, embeddings)` | Add entities với auto `content_type="entity"` | `None` |
| `query_chunks` | `(query_texts, query_embeddings, n_results, where)` | Query chunks collection | ChromaDB result |
| `query_entities` | `(query_texts, query_embeddings, n_results, where)` | Query entities collection | ChromaDB result |
| `delete_by_document_id` | `(document_id: str)` | Xóa chunks/entities từ MỌI collections | `None` |
| `reset_cache` | `()` | Reset collection cache | `None` |

**Properties:**
- `client` → Lazy-init ChromaDB HttpClient (cached)
- `chunks_collection` → Cached chunks collection
- `entities_collection` → Cached entities collection

**Key Design Decisions:**
1. **Collection caching:** Tránh repeated `get_or_create` calls
2. **Explicit embeddings:** Ưu tiên explicit embeddings nếu có, fallback auto-generate
3. **Multi-collection delete (BR-008):** Quét TẤT CẢ collections khi xóa document để tránh orphan vectors

---

### 1.5 PDFExtractor

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/pdf_extractor.py` |
| **Class** | `PDFExtractor` |
| **Purpose** | Extract text từ PDF files, handle encrypted/corrupt files |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `extract_text` | `(file_path: str)` | Extract text từ PDF file | `str` |

**Error Handling:**
- `ValueError("PDF is encrypted")` — Encrypted PDF không hỗ trợ
- `ValueError("No text layer found")` — Scan image-only PDF
- `ValueError("Empty PDF")` — File rỗng
- `pypdf.errors.PdfReadError` — Corrupt PDF

**Dependencies:**
- `pypdf` — PDF parsing library

---

## 2. Learning Services

### 2.1 FlashcardGenerationService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/flashcard_generation_service.py` |
| **Class** | `FlashcardGenerationService` |
| **Purpose** | Auto-generate flashcards từ graph entities, quiz wrong answers, custom data |
| **Business Rules** | BR-004 (Flashcard Generation Rule), BR-015 (Flashcard Quality Threshold) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `generate_from_document` | `(user_id, doc_id, max_cards)` | Generate flashcards từ document's graph entities | `List[Flashcard]` |
| `generate_from_quiz` | `(user_id, quiz_result_id)` | Generate flashcards từ quiz wrong answers | `List[Flashcard]` |
| `generate_from_custom` | `(user_id, front_back_pairs)` | Generate flashcards từ custom data | `List[Flashcard]` |

**Validation (BR-004):**
- Document status PHẢI là "completed"
- Entity confidence >= 0.7
- Max 50 flashcards per request
- Entity degree (connections) >= 1

---

### 2.2 SM2Service

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/sm2_service.py` |
| **Class** | `SM2Service` |
| **Purpose** | Spaced Repetition SM-2 algorithm, review scheduling, due cards retrieval |
| **Business Rules** | BR-005 (SM-2 Scheduling Rule) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `update_sm2_params` | `(card_id, quality)` | Update SM-2 parameters sau review | `Flashcard` |
| `get_due_cards` | `(user_id, limit)` | Get flashcards due for review | `List[Flashcard]` |
| `get_due_cards_count` | `(user_id)` | Count due flashcards | `int` |
| `get_review_stats` | `(user_id, days)` | Get review stats for period | `Dict` |

**SM-2 Algorithm:**
```python
if quality >= 3:  # Successful recall
    if repetitions == 0: interval = 1
    elif repetitions == 1: interval = 6
    else: interval = round(interval * ease_factor)
    repetitions += 1
else:  # Failed recall
    repetitions = 0
    interval = 0  # Review immediately
ease_factor = max(1.3, ease_factor + (0.1 - (5-quality) * (0.08 + (5-quality)*0.02)))
```

> [!WARNING]
> **Divergence CR-001:** Code dùng `interval = 1` thay vì `0` trong spec. Recommendation: Fix code → `interval = 0`.

---

### 2.3 QuizAnalysisService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/quiz_analysis_service.py` |
| **Class** | `QuizAnalysisService` |
| **Purpose** | Analyze quiz results, identify weak areas, generate AI study recommendations |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `analyze_weak_areas` | `(user_id, quiz_id)` | Identify entities user struggled with | `List[WeakArea]` |
| `get_study_recommendations` | `(user_id)` | Generate AI-powered study plan | `List[Recommendation]` |
| `get_bloom_breakdown` | `(user_id)` | Performance by Bloom's taxonomy level | `Dict[str, float]` |

---

### 2.4 NoteService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/note_service.py` |
| **Class** | `NoteService` |
| **Purpose** | Zettelkasten note CRUD, backlink management, note graph generation |
| **Business Rules** | BR-009 (Note Backlink Rule) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `create_note` | `(user_id, title, content, note_type, tags)` | Create atomic note | `Note` |
| `update_note` | `(user_id, note_id, updates)` | Update note fields | `Note` |
| `delete_note` | `(user_id, note_id)` | Delete note + cascading links | `bool` |
| `get_note` | `(user_id, note_id)` | Get note with backlinks | `Note` |
| `list_notes` | `(user_id, skip, limit, note_type, tags)` | List notes with filters | `List[Note]` |
| `search_notes` | `(user_id, query)` | ILIKE search title/content/tags | `List[Note]` |
| `get_note_graph` | `(user_id)` | Get note graph for visualization | `NoteGraphResponse` |
| `create_link` | `(user_id, source_id, target_id, context)` | Create manual note link | `NoteLink` |
| `get_backlinks` | `(user_id, note_id)` | Get incoming links | `List[NoteLink]` |
| `suggest_backlinks` | `(user_id, note_id)` | AI-suggest backlinks (threshold 0.75) | `BacklinkSuggestionsResponse` |

---

### 2.5 BacklinkService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/backlink_service.py` |
| **Class** | `BacklinkService` |
| **Purpose** | Compute/fetch incoming relations (backlinks) cho graph entities |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `get_entity_backlinks` | `(entity_id, user_id)` | Get incoming relations cho entity | `List[Backlink]` |

**Implementation:**
- Query `graph_relations` table WHERE `target_entity_id = entity_id`
- Filter by `user_id` cho data isolation (BR-001)
- Include source entity details cho context

---

### 2.6 BacklinkAIService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/backlink_ai_service.py` |
| **Class** | `BacklinkAIService` |
| **Purpose** | AI-powered backlink suggestions giữa notes và graph entities |
| **Business Rules** | BR-009 (Note Backlink Rule) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `suggest_backlinks` | `(note_id, user_id, threshold)` | AI-suggest backlinks (threshold 0.75) | `List[BacklinkSuggestion]` |

**Matching Algorithm:**
| Method | Priority | Description |
|--------|----------|-------------|
| Exact match | Cao nhất | Entity name xuất hiện chính xác trong note |
| Fuzzy match (>= 0.8) | Cao | Entity name gần giống text trong note |
| Semantic similarity | Trung bình | Embedding similarity cao |

---

### 2.7 CrossVerificationService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/cross_verification_service.py` |
| **Class** | `CrossVerificationService` |
| **Purpose** | Multi-document contradiction detection, complementary info identification, consolidated answer generation |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `detect_contradictions` | `(user_id, doc_ids)` | Find contradictions giữa documents | `List[Contradiction]` |
| `find_complementary_info` | `(user_id, doc_ids, topic)` | Find complementary info across docs | `ConsolidatedAnswer` |
| `generate_consolidated_answer` | `(user_id, query, doc_ids)` | Synthesize answer từ multiple docs | `str` |

**Documentation:** Extensively documented trong [LLM_WIKI_DEEP_DIVE.md](../LLM_WIKI_DEEP_DIVE.md)

---

## 3. Auth & User Services

### 3.1 AuthService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/auth_service.py` |
| **Class** | `AuthService` |
| **Purpose** | Multi-device authentication với session management |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `register` | `(email, password, username?, full_name?)` | Register new user, create user + tokens + session | `dict` (user, access_token, refresh_token) |
| `login` | `(email, password, device_info?, ip_address?)` | Login, create new session for device | `dict` (user, access_token, refresh_token, session) |
| `refresh` | `(refresh_token)` | Refresh access token với token rotation | `dict` (access_token, refresh_token, session) |
| `logout` | `(refresh_token)` | Revoke session (soft delete) | `bool` |
| `logout_all` | `(user_id)` | Revoke all sessions cho user | `int` (sessions revoked) |

**Key Features:**
- **Multi-device:** Mỗi device có refresh_token riêng
- **Token rotation:** Refresh → revoke old session, create new
- **Soft delete logout:** Giữ audit trail
- **Device hashing:** SHA-256 hash device info trước khi lưu

**Dependencies:**
- `UserRepository`, `UserSessionRepository`
- `security.py`: `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`

---

### 3.2 UserService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/user_service.py` |
| **Class** | `UserService` |
| **Purpose** | User profile management, change password |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `get_profile` | `(user_id)` | Get user profile | `UserProfile` |
| `update_profile` | `(user_id, updates)` | Update profile fields (name, avatar, preferences) | `UserProfile` |
| `change_password` | `(user_id, old_password, new_password)` | Change password với validation | `bool` |

---

### 3.3 Security Module

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/security.py` |
| **Type** | Module-level functions (không có class) |
| **Purpose** | Password hashing, JWT operations, device hashing |

**Public Functions:**

| Function | Signature | Description | Returns |
|----------|-----------|-------------|---------|
| `hash_password` | `(password: str)` | Hash password bằng bcrypt | `str` |
| `verify_password` | `(plain_password, hashed_password)` | Verify password match hash | `bool` |
| `create_access_token` | `(user_id, expires_delta?)` | Create JWT access token | `str` |
| `create_refresh_token` | `(user_id, expires_delta)` | Create JWT refresh token | `str` |
| `decode_token` | `(token: str)` | Decode và validate JWT | `dict` |
| `hash_device_info` | `(user_agent?, ip_address?)` | SHA-256 hash device info | `str` (64-char hex) |

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `BCRYPT_ROUNDS` | 12 | bcrypt cost factor |
| `JWT_SECRET_KEY` | — | Secret cho token signing |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token TTL |
| JWT algorithm | HS256 | — |
| Clock skew leeway | 30 giây | Tolerance khi decode |

---

### 3.4 TopicService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/topic_service.py` |
| **Class** | `TopicService` |
| **Purpose** | Topic CRUD, assign documents/notes to topics |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `create_topic` | `(user_id, name, description?, color?, icon?)` | Create topic | `Topic` |
| `update_topic` | `(user_id, topic_id, updates)` | Update topic fields | `Topic` |
| `archive_topic` | `(user_id, topic_id)` | Soft delete topic | `Topic` |
| `delete_topic` | `(user_id, topic_id)` | Delete topic (cascade junctions) | `bool` |
| `list_topics` | `(user_id, skip, limit)` | List user's topics | `List[Topic]` |
| `get_topic` | `(user_id, topic_id)` | Get topic detail | `Topic` |
| `add_document` | `(user_id, topic_id, doc_id)` | Add document to topic | `DocumentTopic` |
| `remove_document` | `(user_id, topic_id, doc_id)` | Remove document from topic | `bool` |
| `add_note` | `(user_id, topic_id, note_id)` | Add note to topic | `NoteTopic` |
| `remove_note` | `(user_id, topic_id, note_id)` | Remove note from topic | `bool` |

---

## 4. Integration Services

### 4.1 NotificationService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/notification_service.py` |
| **Class** | `NotificationService` |
| **Purpose** | Multi-channel notifications (Browser Push, Email, VAPID Web Push) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `send_browser_notification` | `(user_id, title, body, icon, data)` | Browser push via Web Push API | `bool` |
| `send_email_notification` | `(user_email, subject, html_content)` | Email via SMTP | `bool` |
| `send_flashcard_digest` | `(user_id, user_email, due_count, streak)` | Daily digest (browser > email fallback) | `bool` |
| `subscribe_push` | `(user_id, subscription)` | Register Web Push subscription | `bool` |
| `unsubscribe_push` | `(user_id, endpoint)` | Unregister push subscription | `bool` |
| `send_push_notification` | `(user_id, title, body, icon, badge, data, tag)` | VAPID push notification (có mock mode) | `bool` |

**Multi-Channel Fallback:**
```
Browser Push (VAPID) → Email (SMTP) → Log fallback
```

**External Integrations:**
- **SMTP** — Email sending (aiosmtplib)
- **VAPID** — Web Push API (pywebpush — currently comment out, needs uncomment for production)
- **Redis** — Push subscription storage

---

### 4.2 EmailService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/email_service.py` |
| **Type** | Module-level functions (không có class) |
| **Purpose** | SMTP email sending với HTML templates và JWT token generation |

**Public Functions:**

| Function | Signature | Description | Returns |
|----------|-----------|-------------|---------|
| `generate_verification_token` | `(user_id, email)` | Create JWT email verification token (24h expiry) | `str` |
| `generate_password_reset_token` | `(user_id, email)` | Create JWT password reset token (1h expiry) | `str` |
| `decode_email_token` | `(token, expected_type)` | Decode và validate email token | `dict` (payload) |
| `send_verification_email` | `(to_email, token)` | Send email verification với HTML template | `bool` |
| `send_password_reset_email` | `(to_email, token)` | Send password reset với HTML template | `bool` |

**Token Configuration:**
| Token Type | Expiry | Algorithm | Secret |
|------------|--------|-----------|--------|
| Email Verification | 24 hours | HS256 | `_get_email_jwt_secret()` |
| Password Reset | 1 hour | HS256 | `_get_email_jwt_secret()` |

**Features:**
- Token single-use với `jti` (unique token ID)
- Token type validation
- HTML email templates với responsive design
- Auto-dispatch: SMTP (nếu đủ config) hoặc mock mode

---

### 4.3 ObsidianVaultImporter

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/obsidian_vault_importer.py` |
| **Class** | `ObsidianVaultImporter` |
| **Purpose** | Import Obsidian Vault (.md files, wiki-links) vào Knowledge Graph |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `import_vault` | `(vault_path, user_id, import_id?)` | Scan, parse, upsert entities/relations, persist graph | `Dict` (entities_imported, relations_imported, errors) |

**Import Pipeline:**
1. **Scan** — Find all `.md` files (exclude `.*` directories)
2. **Parse** — `MarkdownParser.parse_file()` → title, content, tags, links, frontmatter
3. **Entity Resolution** — `EntityResolutionService.resolve_and_merge()` (dual mapping: filename + title)
4. **Relations** — Wiki-links `[[target]]` → `links_to` relations
5. **GraphBuilder** — `add_entities_and_relations()` + `persist_graph("obsidian_global")`

**Progress Tracking (Redis):**
| Stage | Progress | Action |
|-------|----------|--------|
| Parsing markdown files | 0-30% | Scan vault, parse `.md` files |
| Upserting entities | 30-70% | Create/update graph entities |
| Building relations | 70-90% | Create wiki-link relations |
| Import completed | 100% | Persist graph, save result |

---

### 4.4 EntityResolutionService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/entity_resolution_service.py` |
| **Class** | `EntityResolutionService` |
| **Purpose** | Resolve và merge duplicate entities từ different sources (AI/Obsidian/manual) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `resolve_and_merge` | `(user_id, name, source, confidence, metadata)` | Resolve entity (fuzzy match + LLM verification) | `GraphEntity` |

**Source Priority:**
```
Manual > Obsidian > AI Extracted
```

**Matching Strategy:**
1. Exact name match → Merge
2. Fuzzy match (>= 0.85) → LLM verification → Merge if confirmed
3. No match → Create new entity

---

### 4.5 EntityAliasResolutionService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/entity_alias_service.py` |
| **Class** | `EntityAliasResolutionService` |
| **Purpose** | Cross-document entity alias resolution (AI/ML → Artificial Intelligence/Machine Learning) |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `resolve_alias` | `(user_id, alias_name)` | Resolve alias → canonical name (optional LLM verification) | `Dict` (alias_name, canonical_name, resolved) |
| `suggest_aliases` | `(user_id, entity_names)` | AI-suggest aliases cho review | `List[Suggestion]` |
| `create_alias` | `(user_id, alias_name, canonical_name, confidence, source)` | Manually create alias | `EntityAlias` |

---

### 4.6 TagService

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/tag_service.py` |
| **Class** | `TagService` |
| **Purpose** | Tag management, search entities by tag, add tags to entities |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `get_all_tags` | `(user_id)` | Get all unique tags in user's knowledge graph | `List[str]` |
| `get_entities_by_tag` | `(user_id, tag)` | Get entities filtered by tag | `List[GraphEntity]` |
| `add_tags_to_entity` | `(user_id, entity_id, tags)` | Add tags to entity | `GraphEntity` |

**Implementation:**
- PostgreSQL ARRAY column + GIN index cho fast tag queries
- Query: `WHERE tags @> ARRAY['tag_name']`

---

### 4.7 CodeParser

| Thuộc tính | Giá trị |
|------------|---------|
| **File** | `app/services/code_parser.py` |
| **Class** | `CodeParser` |
| **Purpose** | Parse source code files (Python, JS, TS) qua AST + regex để extract entities, relations |

**Public Methods:**

| Method | Signature | Description | Returns |
|--------|-----------|-------------|---------|
| `parse_file` | `(file_path: str)` | Parse code file → entities + relations | `ParsedCodeResult` |

**Supported Languages:**

| Language | Method | Entities Extracted | Relations Detected |
|----------|--------|-------------------|-------------------|
| **Python** | AST parsing | Classes, functions, methods, imports, decorators, inheritance, docstrings | Inheritance, function calls, import dependencies, class composition |
| **JavaScript** | Regex parsing | Exports, modules, classes, functions, imports, React components | Import dependencies, function calls, module exports |
| **TypeScript** | Regex parsing | Interfaces, types, classes, functions, imports, React components | Import dependencies, type inheritance, function calls |

**Error Handling:**
- `SyntaxError` → Graceful fallback (regex instead of AST)
- Empty file → Empty result (KHÔNG raise)
- Large file (>1MB) → Truncate warning trong metadata

**Integration:**
- Called bởi `DocumentService` khi `source_type = "code"`
- Output → `LightRAGPipeline.ingest_code_entities()`

---

## 5. Service Dependency Map

```
┌──────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                       │
└───────────────────────────┬──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ DocumentService│  │ AuthService   │  │ NoteService   │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ LLMService    │  │ Security      │  │ BacklinkAI    │
│ EmbeddingSvc  │  │ UserService   │  │ Service       │
│ ChromaClient  │  │ TopicService  │  └───────┬───────┘
│ PDFExtractor  │  └───────────────┘          │
│ CodeParser    │                              │
└───────┬───────┘                              │
        │                                      │
        ▼                                      ▼
┌──────────────────────────────────────────────────────────┐
│              Integration Services                        │
│  NotificationService → SMTP, VAPID, Redis                │
│  EmailService → SMTP, PyJWT                              │
│  EntityResolutionService → LLM, Fuzzy matching           │
│  TagService → PostgreSQL GIN indexes                     │
│  ObsidianVaultImporter → File system, Redis              │
└──────────────────────────────────────────────────────────┘
```

---

## 6. Quick Reference

### 6.1 Services by Business Rule

| Business Rule | Services Involved |
|---------------|-------------------|
| BR-001 (Data Isolation) | **ALL** — Mọi service PHẢI filter theo user_id |
| BR-002 (Processing Pipeline) | DocumentService, LLMService, ChromaClient, CodeParser, PDFExtractor |
| BR-004 (Flashcard Generation) | FlashcardGenerationService |
| BR-005 (SM-2 Scheduling) | SM2Service |
| BR-006 (Socratic Response) | LLMService (chat_stream) |
| BR-008 (Local Mode) | LLMService, EmbeddingService, ChromaClient |
| BR-009 (Note Backlinks) | NoteService, BacklinkService, BacklinkAIService |
| BR-010 (Error Recovery) | Worker tasks (process_document_task, etc.) |
| BR-015 (Flashcard Quality) | FlashcardGenerationService |
| BR-016 (System Resilience) | DocumentService, ChromaClient, LLMService |

### 6.2 Services by Database Table

| Table | Primary Service | Secondary Services |
|-------|-----------------|-------------------|
| `users` | AuthService, UserService | TopicService, NotificationService |
| `documents` | DocumentService | FlashcardGenerationService, QuizAnalysisService |
| `graph_entities` | EntityResolutionService | BacklinkService, TagService, ObsidianVaultImporter |
| `graph_relations` | EntityResolutionService | BacklinkService, ObsidianVaultImporter |
| `flashcards` | SM2Service, FlashcardGenerationService | QuizAnalysisService |
| `notes` | NoteService | BacklinkService, BacklinkAIService, TopicService |
| `quizzes` | QuizAnalysisService | FlashcardGenerationService |
| `user_sessions` | AuthService | UserService |
| `topics` | TopicService | — |
| `entity_aliases` | EntityAliasResolutionService | EntityResolutionService |

---

## 7. Testing Guidelines

### 7.1 Unit Testing

```python
# Example: Testing SM2Service
async def test_sm2_update_first_success():
    card = await create_test_flashcard()
    updated = await sm2_service.update_sm2_params(card.id, quality=5)
    assert updated.sm2_interval == 1
    assert updated.sm2_repetitions == 1
    assert updated.sm2_ease_factor > 2.5
```

### 7.2 Integration Testing

```python
# Example: Testing DocumentService upload flow
async def test_document_upload_and_processing():
    doc = await document_service.upload_document(user_id, test_pdf)
    assert doc.status == "PENDING"

    # Wait for worker processing
    await asyncio.sleep(10)

    doc = await document_service.get_document(user_id, doc.id)
    assert doc.status == "COMPLETED"
```

### 7.3 Mock Testing

Services với external dependencies nên được mock:
- `LLMService` → Mock OpenAI/Ollama responses
- `EmbeddingService` → Return fixed dimension vectors
- `NotificationService` → Mock SMTP/VAPID calls
- `EmailService` → Mock SMTP send

---

© 2026 AetherTutor Team. Last updated: April 12, 2026