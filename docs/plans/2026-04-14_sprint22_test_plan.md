# Sprint 22: Testing & Quality Gateway — Detailed Test Plan

> **Priority:** 🔴 P0 | **Sprint:** 22 | **Dependency:** None (có thể bắt đầu ngay)
> **Estimate:** ~40 giờ (~1 tuần)
> **Goal:** Viết 60+ tests để đạt 464+ minimum target, coverage ≥80%
> **Baseline:** 403 tests hiện tại → Target: 463+ (60+ new tests)

---

## 📋 Tổng quan

Sprint 22 tập trung vào việc xây dựng bộ tests đầy đủ cho các modules quan trọng mà hiện tại chưa có tests hoặc tests chưa đủ.

### Phases thực hiện (theo thứ tự ưu tiên)

1. **Phase 1:** WebSocket Integration Tests (15 tests) — Blocking cho collaboration
2. **Phase 2:** E2E Collaboration Tests (5 tests) — Validate real-time features
3. **Phase 3:** Code Parser Tests (15 tests) — Core functionality
4. **Phase 4:** Agent Tests (15 tests) — Core functionality
5. **Phase 5:** WebSocket Load Tests (5 tests) — Performance validation
6. **Phase 6:** E2E User Journey Tests (5 tests) — Complete workflow
7. **Phase 7:** API Contract Tests (8 tests) — Endpoint validation
8. **Phase 8:** Media API Tests (8 tests) — Media pipeline validation
9. **Phase 9:** Fix Existing Failures + Coverage Setup — CI/CD readiness

---

## Phase 1: WebSocket Integration Tests (15 tests)

> **File:** `tests/integration/test_websocket_integration.py`
> **Module:** `app/api/websocket.py`, `app/api/websocket_handlers.py`
> **Estimate:** 5 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_websocket_connect_success` | Integration | Connect to `/ws` endpoint with valid JWT token | Connection established, 101 Switching Protocols |
| 2 | `test_websocket_connect_invalid_jwt` | Integration | Connect with expired/invalid JWT | Connection rejected, 403 Forbidden |
| 3 | `test_websocket_connect_no_jwt` | Integration | Connect without token | Connection rejected, 403 Forbidden |
| 4 | `test_websocket_send_message` | Integration | Send message after connect, receive echo/ack | Message received, proper response format |
| 5 | `test_websocket_join_room` | Integration | Send `join_room` event with room_id | User added to room, presence broadcast |
| 6 | `test_websocket_leave_room` | Integration | Send `leave_room` event | User removed from room, presence update |
| 7 | `test_websocket_heartbeat` | Integration | Send heartbeat ping, receive pong | Heartbeat response, connection maintained |
| 8 | `test_websocket_broadcast_to_room` | Integration | 2 users in same room, one sends message | Both users receive message |
| 9 | `test_websocket_no_broadcast_other_room` | Integration | 2 users in different rooms, one sends | Only sender's room receives, other room doesn't |
| 10 | `test_websocket_node_create_event` | Integration | Send `node_create` event in graph room | Event broadcast to all users in room |
| 11 | `test_websocket_node_update_event` | Integration | Send `node_update` event | Event broadcast, optimistic update |
| 12 | `test_websocket_node_delete_event` | Integration | Send `node_delete` event | Event broadcast, entity removed |
| 13 | `test_websocket_disconnect` | Integration | Client disconnects, cleanup connections | User removed from active rooms, presence update |
| 14 | `test_websocket_reconnection` | Integration | Disconnect → reconnect, state restored | Rejoin rooms, sync state |
| 15 | `test_websocket_presence_sync` | Integration | 3 users connect, verify presence list | All 3 users appear in presence list |

### Implementation Notes

```python
# Use starlette.testclient.TestClient for WebSocket testing
from starlette.testclient import TestClient
from app.main import app

def test_websocket_connect_success():
    client = TestClient(app)
    with client.websocket_connect("/ws?token=valid_jwt_token") as websocket:
        # Connection should be established
        data = websocket.receive_json()
        assert data["type"] == "connection_established"
```

### Fixtures Needed

- `websocket_client` — Async WebSocket client fixture with JWT auth
- `multi_user_websocket` — Multiple WebSocket clients for broadcast tests
- `valid_jwt_token` — Generate valid JWT token for authentication
- `test_user` — Create test user for authentication

---

## Phase 2: E2E Collaboration Tests (5 tests)

> **File:** `tests/e2e/test_collaboration_e2e.py` (new directory: `tests/e2e/`)
> **Tool:** Playwright hoặc pytest-asyncio với multiple async clients
> **Estimate:** 4 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_real_time_co_editing` | E2E | 2 users edit same graph simultaneously, changes sync | Both users see each other's changes in real-time |
| 2 | `test_conflict_resolution` | E2E | 2 users edit same node simultaneously | Conflict detected, last-write-wins or merge strategy |
| 3 | `test_presence_sync` | E2E | User A joins room, User B sees presence update | Presence list synced across all users |
| 4 | `test_share_unshare_flow` | E2E | User A shares resource with User B, then unshares | User B can access when shared, denied when unshared |
| 5 | `test_invite_accept_flow` | E2E | User A invites User B to team, User B accepts | User B becomes team member, can access shared resources |

### Implementation Notes

```python
# Example with multiple async clients
@pytest.mark.asyncio
async def test_real_time_co_editing(async_client, async_client_2):
    # User A creates graph
    # User B joins same room via WebSocket
    # User A creates node
    # User B should receive node_create event
    # User B creates node
    # User A should receive node_create event
```

### Fixtures Needed

- `async_client_2` — Second async client for multi-user testing
- `team_fixture` — Pre-created team with 2 members
- `shared_graph_fixture` — Graph shared between 2 users

---

## Phase 3: Code Parser Tests (15 tests)

> **File:** `tests/unit/test_code_parser.py`
> **Module:** `app/services/code_parser.py`
> **Estimate:** 3 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_parse_python_simple_function` | Unit | Parse Python function with docstring | Function extracted with name, params, docstring |
| 2 | `test_parse_python_class` | Unit | Parse class with methods | Class extracted with methods list |
| 3 | `test_parse_python_class_inheritance` | Unit | Parse class with inheritance | INHERITS relation extracted |
| 4 | `test_parse_python_imports` | Unit | Parse import statements | IMPORTS relations extracted |
| 5 | `test_parse_python_method_calls` | Unit | Parse method calls within functions | CALLS relations extracted |
| 6 | `test_parse_python_nested_functions` | Unit | Parse nested function definitions | Nested functions extracted with parent-child relation |
| 7 | `test_parse_python_decorators` | Unit | Parse decorated functions | Decorators extracted as metadata |
| 8 | `test_parse_python_type_hints` | Unit | Parse functions with type hints | Type hints preserved in output |
| 9 | `test_parse_js_functions` | Unit | Parse JavaScript function declarations | Functions extracted from JS code |
| 10 | `test_parse_js_classes` | Unit | Parse JS class syntax | Class and methods extracted |
| 11 | `test_parse_js_imports` | Unit | Parse ES6 import/export statements | IMPORTS relations extracted |
| 12 | `test_parse_ts_types` | Unit | Parse TypeScript interfaces/types | Type definitions extracted |
| 13 | `test_parse_file_size_limit` | Unit | Parse file exceeding size limit | Error raised, file rejected |
| 14 | `test_parse_syntax_error` | Unit | Parse code with syntax errors | Error handled gracefully, partial extraction |
| 15 | `test_parse_empty_file` | Unit | Parse empty or whitespace-only file | Empty result, no entities extracted |

### Implementation Notes

```python
from app.services.code_parser import CodeParser, CodeParseResult

def test_parse_python_simple_function():
    code = '''
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"
'''
    parser = CodeParser()
    result = parser.parse(code, language="python")
    
    assert len(result.entities) == 1
    assert result.entities[0].type == "function"
    assert result.entities[0].name == "greet"
    assert "name: str" in result.entities[0].parameters
    assert "Greet someone by name" in result.entities[0].docstring
```

### Fixtures Needed

- `python_sample_code` — Various Python code snippets
- `js_sample_code` — Various JavaScript/TypeScript code snippets
- `invalid_code_sample` — Code with syntax errors

---

## Phase 4: Agent Tests (15 tests)

> **File:** `tests/unit/test_agents_comprehensive.py`
> **Module:** `app/core/agents/` (ExaminerAgent, VisualizerAgent, LanguageAgent, MathAgent)
> **Estimate:** 4 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_examiner_agent_prompt_generation` | Unit | ExaminerAgent generates Socratic questions | Prompt contains Socratic elements (hint, question, feedback) |
| 2 | `test_examiner_agent_hints` | Unit | ExaminerAgent provides hints when user stuck | Hint level increases progressively |
| 3 | `test_examiner_agent_feedback` | Unit | ExaminerAgent evaluates user answers | Feedback includes correctness, explanation, next step |
| 4 | `test_examiner_agent_error_handling` | Unit | ExaminerAgent handles invalid input | Graceful error message, prompt retry |
| 5 | `test_examiner_agent_health_check` | Unit | ExaminerAgent health check endpoint | Returns healthy status |
| 6 | `test_visualizer_agent_mindmap` | Unit | VisualizerAgent generates mindmap Mermaid | Valid Mermaid syntax, mindmap format |
| 7 | `test_visualizer_agent_flowchart` | Unit | VisualizerAgent generates flowchart Mermaid | Valid Mermaid syntax, flowchart TD/LR |
| 8 | `test_visualizer_agent_error_handling` | Unit | VisualizerAgent handles empty graph | Error message, fallback visualization |
| 9 | `test_visualizer_agent_health_check` | Unit | VisualizerAgent health check | Returns healthy status |
| 10 | `test_language_agent_vocab_cards` | Unit | LanguageAgent generates vocabulary flashcards | Flashcards with word, definition, example |
| 11 | `test_language_agent_grammar` | Unit | LanguageAgent explains grammar rules | Grammar explanation with examples |
| 12 | `test_language_agent_conjugation` | Unit | LanguageAgent conjugates verbs | Conjugation table generated |
| 13 | `test_math_agent_latex` | Unit | MathAgent generates LaTeX rendering | Valid LaTeX syntax in response |
| 14 | `test_math_agent_step_by_step` | Unit | MathAgent solves problem step-by-step | Multiple steps, logical progression |
| 15 | `test_agent_registry_list` | Unit | AgentRegistry lists all available agents | Returns 4 core agents + custom agents |

### Implementation Notes

```python
from app.core.agents import ExaminerAgent, VisualizerAgent

@pytest.mark.asyncio
async def test_examiner_agent_prompt_generation():
    agent = ExaminerAgent()
    prompt = agent.generate_prompt(
        question="What is the time complexity of binary search?",
        context="Binary search algorithm divides array in half each iteration",
        user_level="beginner"
    )
    
    assert "hint" in prompt or "question" in prompt
    assert "binary search" in prompt
    # Should not give away answer directly
    assert "O(log n)" not in prompt
```

### Fixtures Needed

- `agent_config` — Agent configuration fixtures
- `sample_graph_context` — Knowledge graph context for agents
- `sample_user_question` — Example user questions

---

## Phase 5: WebSocket Load Tests (5 tests)

> **File:** `tests/load/test_websocket_load.py` (new directory: `tests/load/`)
> **Module:** `app/api/websocket.py`
> **Estimate:** 4 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_100_concurrent_connections` | Load | 100 WebSocket connections simultaneously | All connections established, no errors |
| 2 | `test_500_concurrent_connections` | Load | 500 WebSocket connections simultaneously | All connections established, <1% failure |
| 3 | `test_1000_concurrent_connections` | Load | 1000 WebSocket connections simultaneously | All connections established, <5% failure |
| 4 | `test_broadcast_latency` | Load | 100 users, broadcast message to room | p95 latency <200ms, no message loss |
| 5 | `test_memory_leak_detection` | Load | 1000 connections, hold 5min, disconnect | Memory usage stable, no growth >10% |

### Implementation Notes

```python
# Use asyncio.gather for concurrent connections
import asyncio
from websockets import connect

@pytest.mark.asyncio
async def test_100_concurrent_connections():
    async def connect_and_ping(uri):
        async with connect(uri) as ws:
            await ws.send('{"type": "ping"}')
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            return response
    
    uris = [f"ws://localhost:8000/ws?token=token_{i}" for i in range(100)]
    tasks = [connect_and_ping(uri) for uri in uris]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    assert success_count >= 95  # 95% success rate
```

### Fixtures Needed

- `load_test_jwt_tokens` — Generate N JWT tokens for load testing
- `websocket_server_uri` — WebSocket server URI fixture

---

## Phase 6: E2E User Journey Tests (5 tests)

> **File:** `tests/e2e/test_user_journeys.py`
> **Tool:** Playwright hoặc pytest-asyncio
> **Estimate:** 4 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_complete_learning_journey` | E2E | Register → upload doc → process → chat → flashcards → quiz → review | Complete workflow succeeds |
| 2 | `test_flashcard_review_sm2` | E2E | Review 10 flashcards with SM-2 ratings | Due count decreases, intervals updated |
| 3 | `test_quiz_take_and_submit` | E2E | Generate quiz, answer questions, submit, view results | Score calculated, weak areas identified |
| 4 | `test_zettelkasten_note_creation` | E2E | Create note → add backlink → view graph | Note created, backlinks synced, graph updated |
| 5 | `test_graph_exploration_journey` | E2E | Upload doc → view graph → explore entities → view Mermaid | Graph rendered, entities clickable, Mermaid tabs work |

### Implementation Notes

```python
@pytest.mark.asyncio
async def test_complete_learning_journey(async_client):
    # Step 1: Register
    response = await async_client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    
    # Step 2: Login
    response = await async_client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = response.json()["access_token"]
    
    # Step 3: Upload document
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.post(
        "/api/v1/documents",
        files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        headers=headers
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]
    
    # Step 4: Wait for processing
    # Poll until status = "completed"
    
    # Step 5: Start chat
    response = await async_client.post(
        "/api/v1/chat/conversations",
        json={"document_id": doc_id},
        headers=headers
    )
    conversation_id = response.json()["id"]
    
    # Step 6: Generate flashcards
    response = await async_client.post(
        f"/api/v1/flashcards/generate/{doc_id}",
        headers=headers
    )
    assert response.status_code == 200
    
    # Step 7: Generate quiz
    response = await async_client.post(
        f"/api/v1/quiz/generate/{doc_id}",
        headers=headers
    )
    assert response.status_code == 200
```

### Fixtures Needed

- `journey_user` — User fixture for complete journey
- `journey_document` — Pre-processed document fixture

---

## Phase 7: API Contract Tests (8 tests)

> **File:** `tests/integration/test_api_contracts.py`
> **Module:** All API routers
> **Estimate:** 3 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_response_schema_auth` | Contract | Auth endpoints return correct schema | All required fields present, correct types |
| 2 | `test_response_schema_documents` | Contract | Document endpoints return correct schema | id, filename, status, created_at present |
| 3 | `test_response_schema_graph` | Contract | Graph endpoints return correct schema | entities, relations arrays, stats object |
| 4 | `test_response_schema_flashcards` | Contract | Flashcard endpoints return correct schema | cards array, due_count, stats |
| 5 | `test_response_schema_quiz` | Contract | Quiz endpoints return correct schema | quiz_id, questions array, timer |
| 6 | `test_pagination_format` | Contract | Paginated endpoints return correct format | items, total, page, page_size, has_next |
| 7 | `test_error_response_format` | Contract | Error responses follow standard format | error, message, status_code fields |
| 8 | `test_status_codes_consistency` | Contract | Similar operations use same status codes | 200 success, 201 created, 404 not found, 422 validation |

### Implementation Notes

```python
from pydantic import ValidationError

def test_response_schema_documents(async_client, auth_headers):
    response = await async_client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "items" in data
    for item in data["items"]:
        assert "id" in item
        assert "filename" in item
        assert "status" in item
        assert "created_at" in item
        assert isinstance(item["id"], int)
        assert isinstance(item["filename"], str)
```

### Fixtures Needed

- `auth_headers` — Authorization headers with JWT token
- `sample_document_id` — Valid document ID for testing

---

## Phase 8: Media API Tests (8 tests)

> **File:** `tests/integration/test_media_api.py`
> **Module:** `app/api/media.py`
> **Estimate:** 2 giờ

### Test Cases

| # | Test Name | Type | Description | Expected |
|---|-----------|------|-------------|----------|
| 1 | `test_media_upload_video` | Integration | Upload video file | 201 Created, media_id returned |
| 2 | `test_media_upload_audio` | Integration | Upload audio file | 201 Created, media_id returned |
| 3 | `test_media_upload_invalid_type` | Integration | Upload invalid file type (e.g., .exe) | 422 Validation Error |
| 4 | `test_transcript_get` | Integration | Get transcript for processed media | 200 OK, transcript text returned |
| 5 | `test_transcript_request` | Integration | Request transcription for media | 202 Accepted, job_id returned |
| 6 | `test_transcript_update` | Integration | Update transcript content | 200 OK, updated_at returned |
| 7 | `test_media_status` | Integration | Get processing status of media | 200 OK, status (pending/processing/completed/failed) |
| 8 | `test_media_delete` | Integration | Delete media and associated transcript | 204 No Content, resources cleaned up |

### Implementation Notes

```python
def test_media_upload_video(async_client, auth_headers):
    # Create fake video bytes (or use sample)
    video_bytes = b"fake_video_content" * 1000
    
    response = await async_client.post(
        "/api/v1/media",
        files={"file": ("test.mp4", video_bytes, "video/mp4")},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["file_type"] == "video/mp4"
```

### Fixtures Needed

- `sample_video_bytes` — Fake video file bytes
- `sample_audio_bytes` — Fake audio file bytes
- `invalid_file_bytes` — Invalid file type bytes

---

## Phase 9: Fix Existing Failures + Coverage Setup

> **Files:** Various test files + CI/CD configuration
> **Estimate:** 5 giờ

### Tasks

| # | Task | Description | Est. |
|---|------|-------------|------|
| 1 | **Audit 403 existing tests** | Run `pytest -v`, identify all failures | 1h |
| 2 | **Fix failing tests** | Update deprecated assertions, fix logic errors | 2h |
| 3 | **Update deprecated patterns** | Migrate old test patterns to current conventions | 1h |
| 4 | **Setup coverage reporting** | `pytest --cov=app --cov-report=html --cov-report=term` | 30m |
| 5 | **Configure codecov** | `.github/workflows/coverage.yml` for CI/CD | 30m |
| 6 | **Set minimum threshold** | Enforce ≥80% coverage in CI | 30m |
| 7 | **Generate coverage badge** | Add to README/docs | 30m |

### Coverage Commands

```bash
# Run tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# View coverage report
# Open htmlcov/index.html

# Minimum threshold enforcement
# Add to pytest.ini or pyproject.toml:
[tool.coverage.run]
source = ["app"]

[tool.coverage.report]
fail_under = 80
```

---

## 📊 Test Summary

| Phase | Tests Added | Cumulative Total | Est. Time |
|-------|-------------|------------------|-----------|
| **Baseline** | - | 403 | - |
| Phase 1: WebSocket Integration | +15 | 418 | 5h |
| Phase 2: E2E Collaboration | +5 | 423 | 4h |
| Phase 3: Code Parser | +15 | 438 | 3h |
| Phase 4: Agent Tests | +15 | 453 | 4h |
| Phase 5: WebSocket Load | +5 | 458 | 4h |
| Phase 6: E2E User Journey | +5 | 463 | 4h |
| Phase 7: API Contract | +8 | 471 | 3h |
| Phase 8: Media API | +8 | **479** | 2h |
| Phase 9: Fix Existing + Coverage | 0 (fix only) | **479** | 5h |
| **TOTAL** | **+76** | **479** | **34h** |

> **Note:** Total exceeds the 60+ minimum target, providing buffer for any tests that may not pass.
> **Expected final count:** 463-479 tests (depending on Phase 9 fixes)

---

## 🛠️ Implementation Guidelines

### Test Naming Convention

```python
# Pattern: test_{module}_{functionality}_{scenario}
def test_websocket_connect_success():
def test_websocket_connect_invalid_jwt():
def test_code_parser_python_function():
def test_agent_examiner_prompt_generation():
```

### Test Organization

```
tests/
├── conftest.py                  # Shared fixtures
├── integration/
│   ├── test_websocket_integration.py   # Phase 1 (15 tests)
│   ├── test_collaboration_e2e.py       # Phase 2 (5 tests) [move to e2e/]
│   ├── test_api_contracts.py           # Phase 7 (8 tests)
│   └── test_media_api.py               # Phase 8 (8 tests)
├── unit/
│   ├── test_code_parser.py             # Phase 3 (15 tests)
│   └── test_agents_comprehensive.py    # Phase 4 (15 tests)
├── e2e/                              # New directory
│   ├── test_collaboration_e2e.py       # Phase 2 (5 tests)
│   └── test_user_journeys.py           # Phase 6 (5 tests)
├── load/                             # New directory
│   └── test_websocket_load.py          # Phase 5 (5 tests)
└── mocks/
    └── llm_mock.py                   # Existing mock fixtures
```

### Fixture Strategy

```python
# In conftest.py or module-level conftest.py
@pytest.fixture
def auth_headers():
    token = create_jwt_token(user_id=1)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def websocket_client():
    client = await connect_websocket(token=valid_token)
    yield client
    await client.close()
```

---

## ✅ Deliverables Checklist

### Test Files Created

- [ ] `tests/integration/test_websocket_integration.py` (15 tests)
- [ ] `tests/e2e/test_collaboration_e2e.py` (5 tests)
- [ ] `tests/unit/test_code_parser.py` (15 tests)
- [ ] `tests/unit/test_agents_comprehensive.py` (15 tests)
- [ ] `tests/load/test_websocket_load.py` (5 tests)
- [ ] `tests/e2e/test_user_journeys.py` (5 tests)
- [ ] `tests/integration/test_api_contracts.py` (8 tests)
- [ ] `tests/integration/test_media_api.py` (8 tests)

### Configuration

- [ ] `pytest.ini` updated with coverage settings
- [ ] `.github/workflows/coverage.yml` for CI/CD
- [ ] `htmlcov/` directory in `.gitignore`
- [ ] Coverage badge in README

### Quality Gates

- [ ] All 479 tests passing
- [ ] Coverage ≥80% (verify with `pytest --cov`)
- [ ] No test warnings or deprecation notices
- [ ] CI/CD pipeline green
- [ ] Coverage report generated and reviewed

---

## 📝 Notes

### Mock Strategy

- **LLM Service:** Continue using `MockLLMService` (autouse fixture)
- **WebSocket:** Use `starlette.testclient.TestClient` for integration tests
- **Load Tests:** Use real connections, minimal mocking
- **E2E Tests:** Use real DB, real WebSocket, mock external APIs (LLM, Whisper)

### Performance Considerations

- WebSocket load tests may require increasing system resources
- Run load tests separately from unit/integration tests
- Consider adding `@pytest.mark.slow` marker for load tests

### Future Enhancements

- Add property-based testing (Hypothesis) for complex logic
- Add mutation testing to verify test effectiveness
- Add visual regression testing for frontend components

---

© 2026 AetherTutor Team
*Sprint 22 Test Plan — Generated 2026-04-14*
*Status: READY FOR EXECUTION*
