# Testing Strategy

> **Document Owner:** AetherTutor Team
> **Created:** April 12, 2026
> **Version:** 2.0
> **Status:** Active
> **Parent:** [Contributing.md](../Contributing.md)

---

## 1. Tổng Quan

AetherTutor sử dụng chiến lược kiểm thử **4 lớp** (Four-Layer Testing Strategy) để đảm bảo chất lượng code, độ tin cậy của AI, và trải nghiệm người dùng.

```
┌─────────────────────────────────────────┐
│          E2E / Manual Testing           │  ← Lớp 4: User journeys
├─────────────────────────────────────────┤
│         Integration Testing             │  ← Lớp 3: API + DB + Worker
├─────────────────────────────────────────┤
│          Unit Testing                   │  ← Lớp 2: Service logic
├─────────────────────────────────────────┤
│        AI-Specific Testing              │  ← Lớp 1: LLM quality
└─────────────────────────────────────────┘
```

**Thống kê hiện tại (April 2026):**
- **39 test files** trong `tests/`
- **225+ test functions** (async def test_*)
- **2 lớp tests:** Unit + Integration
- **Framework:** pytest + pytest-asyncio + httpx

---

## 2. Cấu Trúc Thư Mục Tests

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures: test_db, async_client, mock_llm
├── test_embedding_service.py      # Embedding service unit tests
│
├── unit/                          # Unit tests (fast, isolated)
│   ├── test_cross_verification_and_alias.py   # CrossVerificationService + EntityAlias
│   ├── test_chat_title_fallback.py            # Chat service title generation
│   └── ... (more unit test files)
│
├── integration/                   # Integration tests (API + DB + Worker)
│   ├── test_worker_flow.py        # Document processing via ARQ worker
│   ├── test_ownership_validation.py  # Data isolation (BR-001) enforcement
│   └── ... (more integration test files)
│
└── mocks/                         # Mock fixtures
    ├── mock_llm.py                # Mock OpenAI/Ollama responses
    ├── mock_embedding.py          # Fixed-dimension embedding mock
    └── ... (more mock files)
```

---

## 3. Unit Testing

### 3.1 Framework & Configuration

| Setting | Value |
|---------|-------|
| **Framework** | `pytest>=7.4.0` |
| **Async Support** | `pytest-asyncio>=0.21.0` (mode: `auto`) |
| **HTTP Client** | `httpx>=0.24.0` (cho integration tests) |
| **Config File** | `pytest.ini` |

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
pythonpath = .
testpaths = tests
filterwarnings =
    ignore::pytest.PytestRemovedIn9Warning
    ignore::DeprecationWarning
```

### 3.2 Conventions

**Naming:**
```
tests/unit/test_{module_name}.py
    └── class Test{ServiceName}:
            └── async def test_{method_name}_{scenario}(self):
```

**Example:**
```python
class TestCrossVerificationService:
    """Tests for multi-document contradiction detection."""

    async def test_cross_check_single_document(self):
        """Should return empty contradictions for single doc."""
        service = CrossVerificationService()
        result = await service.cross_check(["doc_1"])
        assert result.contradictions == []
```

### 3.3 Fixtures (conftest.py)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `test_db` | Function | Isolated async DB session per test |
| `async_client` | Function | HTTPX async client với test DB |
| `mock_llm` | Function | Mock LLM service với fixed responses |
| `sample_pdf_bytes` | Session | Sample PDF file cho document processing tests |

### 3.4 Coverage Targets

| Module | Target | Current Status |
|--------|--------|----------------|
| **SM-2 Algorithm** | 100% | ✅ Covered |
| **Auth Service** | 100% | ✅ Covered |
| **Document Service** | 90%+ | ⚠️ Partial |
| **LLM Service** | 90%+ | ⚠️ Partial |
| **Graph Module** | 80%+ | ⚠️ Partial |
| **Flashcard Service** | 80%+ | ⚠️ Partial |
| **Quiz Service** | 80%+ | ⚠️ Partial |
| **Note Service** | 80%+ | ⚠️ Partial |
| **Collaboration** | 70%+ | ❌ Not covered |
| **Workers** | 70%+ | ⚠️ Partial (test_worker_flow.py) |

> [!NOTE]
> **Overall target: 80%+ coverage.** Critical modules (SM-2, Auth, Data Isolation) phải đạt 100%.

---

## 4. Integration Testing

### 4.1 Scope

Integration tests kiểm tra luồng end-to-end từ API → Service → DB → Worker → Response.

### 4.2 Test Categories

| Category | Files | What It Tests |
|----------|-------|---------------|
| **API Endpoints** | `test_*.py` trong `integration/` | HTTP request/response, status codes, validation |
| **Data Isolation** | `test_ownership_validation.py` | BR-001 enforcement — user A không thấy data user B |
| **Worker Flows** | `test_worker_flow.py` | Document processing pipeline, error recovery |
| **Database Migrations** | Manual (alembic) | Schema changes, data integrity |

### 4.3 API Testing Pattern

```python
async def test_get_documents_list_default_user(async_client: AsyncClient, test_db: AsyncSession):
    """Should return 200 with user's documents."""
    # Arrange: Create test document
    doc = Document(user_id=TEST_USER_ID, filename="test.pdf", status="COMPLETED")
    test_db.add(doc)
    await test_db.commit()

    # Act: GET /documents/
    response = await async_client.get("/api/v1/documents/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "test.pdf"
```

### 4.4 Data Isolation Testing (BR-001)

```python
async def test_repository_get_by_id_with_user_denied(test_db: AsyncSession):
    """User A cannot access User B's document."""
    # Arrange: Doc belongs to User B
    doc = Document(user_id=USER_B, filename="secret.pdf")
    test_db.add(doc)
    await test_db.commit()

    # Act: User A tries to access
    repo = DocumentRepository(test_db)
    result = await repo.get_by_id_with_user_check(doc.id, USER_A)

    # Assert
    assert result is None  # Denied
```

### 4.5 Worker Integration Testing

```python
async def test_worker_process_document_success(test_db: AsyncSession, sample_pdf_bytes: bytes):
    """Should process document through full pipeline."""
    # Arrange
    doc = await create_document(test_db, sample_pdf_bytes)

    # Act: Enqueue worker task
    await process_document_task({"job_try": 1}, str(doc.id))

    # Assert
    doc = await test_db.get(Document, doc.id)
    assert doc.status == "COMPLETED"

    # Verify graph was built
    entities = await test_db.execute(
        select(GraphEntity).where(GraphEntity.document_id == doc.id)
    )
    assert entities.scalars().all() != []
```

---

## 5. End-to-End (E2E) Testing

### 5.1 Current Status: Manual Testing

Hiện tại, E2E testing được thực hiện **thủ công** thông qua các guides:

| Guide | Location | Description |
|-------|----------|-------------|
| **E2E Integration Tests** | `testing/E2E_INTEGRATION_TESTS.md` | 4 flows: Upload → Graph → Chat → Flashcard |
| **Error States Testing** | `testing/ERROR_STATES_TESTING.md` | UI error states: S8.1a-S8.1f & S8.2 |

### 5.2 E2E Test Flows (Manual)

| Flow # | Name | Steps | Expected Result |
|--------|------|-------|-----------------|
| **E2E-001** | Document Upload & Processing | Upload PDF → Wait → Check status | Status = COMPLETED, graph built |
| **E2E-002** | Graph Query & Visualization | Query graph → View stats → Export | Entities returned, graph renders |
| **E2E-003** | Socratic Chat | Start chat → Ask question → Get Socratic response | Response is question, not answer |
| **E2E-004** | Flashcard Review | Generate cards → Review → Check SM-2 | Interval updated, next review set |
| **E2E-005** | Quiz Generation | Generate quiz → Submit → Check results | Score calculated, weak areas identified |
| **E2E-006** | Note Creation with Backlinks | Create note → Check backlink suggestions | Related notes suggested |

### 5.3 Future: Automated E2E (Post-MVP)

**Target Framework:** Playwright (Python)

```python
# tests/e2e/test_learning_flow.py (planned)
async def test_full_learning_flow(page: Page):
    """Upload doc → build graph → chat → generate flashcards → review."""
    # 1. Login
    await page.goto("http://localhost:5173")
    await page.fill("[name=email]", "test@example.com")
    await page.fill("[name=password]", "password123")
    await page.click("button[type=submit]")

    # 2. Upload document
    await page.click("text=Upload Document")
    await page.set_input_files("input[type=file]", "test.pdf")
    await page.click("button:has-text('Upload')")

    # 3. Wait for processing
    await page.wait_for_selector("text=Processing completed")

    # 4. Chat with AI
    await page.click("text=Chat")
    await page.fill("textarea", "Explain quantum entanglement")
    await page.click("button:has-text('Send')")
    response = await page.wait_for_selector(".chat-response")
    assert "What do you think" in await response.inner_text()

    # 5. Generate flashcards
    await page.click("text=Generate Flashcards")
    await page.wait_for_selector(".flashcard")
    cards = await page.query_selector_all(".flashcard")
    assert len(cards) >= 5
```

---

## 6. AI-Specific Testing

### 6.1 Mock Strategy

Vì LLM calls không deterministic, tests sử dụng **mock responses** cho consistency:

```python
# tests/mocks/mock_llm.py
class MockLLMService:
    """Mock LLM service với fixed responses cho testing."""

    async def chat_completion(self, messages, **kwargs):
        return "This is a mock Socratic response: What do you think happens when...?"

    async def structured_extraction(self, prompt, model, **kwargs):
        return model(
            entities=[{"name": "Test Entity", "type": "concept"}],
            relations=[]
        )
```

### 6.2 Test Categories

| Category | Method | Purpose | Status |
|----------|--------|---------|--------|
| **Deterministic Logic** | Mock LLM | Test service logic không phụ thuộc LLM output | ✅ Implemented |
| **Prompt Validation** | Unit tests | Ensure prompts follow format rules | ⚠️ Partial |
| **Response Parsing** | Unit tests | Test JSON extraction từ LLM responses | ⚠️ Partial |
| **Golden Sets** | Manual review | Bộ câu hỏi/trả lời mẫu để đánh giá chất lượng | ❌ Not implemented |
| **Hallucination Detection** | Manual review | Kiểm tra AI có bịa kiến thức không | ❌ Not implemented |

### 6.3 Chat Service Testing

```python
async def test_generate_conversation_title_fallback():
    """Should generate title from first user message if LLM fails."""
    service = ChatService()
    title = service._generate_title_from_fallback([
        {"role": "user", "content": "Explain quantum mechanics"}
    ])
    assert "quantum" in title.lower()
```

---

## 7. Running Tests

### 7.1 Commands

```bash
# Chạy TẤT CẢ tests
pytest

# Verbose output
pytest -v

# Chạy specific test file
pytest tests/unit/test_cross_verification_and_alias.py -v

# Chạy tests matching keyword
pytest -k "flashcard" -v

# Chạy integration tests
pytest tests/integration/ -v

# Chạy unit tests
pytest tests/unit/ -v

# Stop on first failure
pytest -x

# Coverage report (cần pytest-cov)
pytest --cov=app --cov-report=html --cov-report=term-missing

# Coverage cho specific module
pytest --cov=app/services/sm2_service.py -v
```

### 7.2 Pre-Commit Checklist

Trước khi push code:

```bash
# 1. Lint
ruff check .

# 2. Run tests
pytest tests/unit/ tests/integration/ -v

# 3. (Optional) Coverage
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

### 7.3 CI/CD Integration

GitHub Actions workflow (` .github/workflows/ci.yml`):

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:16 }
      redis: { image: redis:7 }
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=app
```

---

## 8. Test Data Management

### 8.1 Fixtures

| Fixture Type | Location | Purpose |
|-------------|----------|---------|
| `conftest.py` | `tests/conftest.py` | Shared fixtures: DB, client, mocks |
| `mocks/` | `tests/mocks/` | Mock LLM, embedding, external services |
| `test_files/` | (planned) | Sample PDFs, code files, images |

### 8.2 Database Isolation

Mỗi test có **DB session riêng** với auto-rollback:

```python
@pytest.fixture
async def test_db():
    """Isolated DB session per test."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()  # Auto-cleanup
```

### 8.3 User Isolation

Tests sử dụng **default user ID** cho MVP:

```python
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
```

---

## 9. Testing Anti-Patterns (Avoid These!)

| Anti-Pattern | Why Bad | Fix |
|-------------|---------|-----|
| Testing với real LLM | Không deterministic, tốn chi phí | Dùng mock responses |
| Shared DB state giữa tests | Tests ảnh hưởng lẫn nhau | Fixture-per-test với rollback |
| No assertions | Test luôn pass mà không check gì | Luôn có `assert` statements |
| Testing implementation details | Refactor làm break tests | Test behavior, not implementation |
| Ignoring edge cases | Bugs trong production | Test error paths, empty inputs |

---

## 10. Future Improvements

| Improvement | Priority | Effort | Description |
|------------|----------|--------|-------------|
| **pytest-cov integration** | High | Low | Auto-generate coverage reports |
| **E2E with Playwright** | Medium | Medium | Automated browser-based E2E tests |
| **Golden set evaluation** | Medium | Medium | Fixed Q&A sets để đánh giá LLM quality |
| **Load testing** | Low | Medium | Test API performance dưới load |
| **Mutation testing** | Low | High | Test quality của chính tests |
| **Visual regression testing** | Low | Medium | Detect UI changes tự động |

---

## 11. Quick Reference

| Resource | Link |
|----------|------|
| pytest Documentation | https://docs.pytest.org/ |
| pytest-asyncio | https://pytest-asyncio.readthedocs.io/ |
| httpx Testing | https://www.python-httpx.org/async/ |
| E2E Manual Guide | `testing/E2E_INTEGRATION_TESTS.md` |
| Error States Guide | `testing/ERROR_STATES_TESTING.md` |
| Mock Fixtures | `tests/mocks/` |
| Conftest | `tests/conftest.py` |

---
© 2026 AetherTutor Team. Last updated: April 12, 2026