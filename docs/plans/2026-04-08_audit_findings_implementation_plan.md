# Audit Findings & Implementation Plan - AetherTutor Final Polish (Revised v3 - Deep Audit)

> **⚠️ Cập nhật sau khi Deep Audit toàn bộ codebase:**  
> Sau khi đọc kỹ lưỡng toàn bộ source code liên quan (`chat_service.py`, `chat_repo.py`, `llm_service.py`, `chat.py` API routes, tests, mocks, database config, Dockerfile), tôi đã phát hiện các vấn đề **THỰC TẾ** cần khắc phục.
> 
> **Lỗi Critical trước đó (missing commit):** Code đã đúng tại `chat_service.py:177`. Không cần sửa.

---

## Findings Summary

### ✅ Đã xác nhận ổn định (No Action Required)

| Hạng mục | Trạng thái | Bằng chứng |
|----------|------------|-----------|
| **Chat Persistence Commit** | ✅ Ổn | `chat_service.py:172-177` có commit sau update COMPLETED |
| **OLLAMA_BASE_URL Env** | ✅ Đã xử lý | `docker-compose.yml:83,106` dùng `${OLLAMA_BASE_URL:-...}` |
| **Test Commit Count** | ✅ Đúng | Test assertion `commit_count == 3` khớp code thực tế |
| **Session Lifecycle** | ✅ Ổn | Mỗi stream tạo `AsyncSessionLocal()` riêng, scope đúng |
| **Database config** | ✅ Ổn | `expire_on_commit=False` tránh stale object issues |

---

### 🔴 Vấn đề cần khắc phục (Action Required)

#### 1. Stream Disconnect Handling - KHÔNG GUARANTEE Execute [MEDIUM-HIGH]

- **File:** `app/services/chat_service.py` (dòng 180-188)
- **Root cause:** 
  - Khi client disconnect, StreamingResponse gọi `aclose()` trên async generator → raise `GeneratorExit`
  - `GeneratorExit` là **sync exception** đặc biệt, Python dùng để đóng generators
  - **Trong async context**, khi generator đang closing, các `await` calls trong except block **có thể không execute** được
  - Tương tự với `asyncio.CancelledError`: Khi task bị cancel, execution dừng **ngay lập tức**, code sau cancel point có thể không chạy
- **Impact thực tế:**
  - Assistant message **vẫn ở trạng thái PENDING** với `content=""` trong DB
  - Orphan records tích tụ theo thời gian → database clutter
  - User thấy tin nhắn "pending" vĩnh viễn trong UI nếu query lại history
- **Bằng chứng:** Không có test nào verify thực tế disconnect behavior với real async session
- **Mức ưu tiên:** 🔴 **P0 - HIGH** (ảnh hưởng data integrity)

**🔧 Solution đề xuất:**

Có 2 approaches:

**Option A - Defensive commit trước khi await (Recommended):**
```python
# Trước khi bắt đầu stream, set FAILED default
# Nếu stream thành công → override thành COMPLETED
# Nếu disconnect → vẫn còn FAILED từ trước
```

**Option B - Dùng asyncio.shield() để bảo vệ commit:**
```python
import asyncio

except (asyncio.CancelledError, GeneratorExit):
    logger.warning(f"Stream disconnected for message {assistant_msg.id}")
    # Shield để đảm bảo commit chạy dù task bị cancel
    await asyncio.shield(
        chat_repo.update_message(
            assistant_msg.id,
            content=full_content,
            status=MessageStatus.FAILED
        )
    )
    await asyncio.shield(chat_repo.session.commit())
    raise
```

**Recommendation: Option A** vì:
- Đơn giản hơn, không cần shield phức tạp
- Không race condition risk
- Performance tốt hơn (không tạo thêm task overhead)

---

#### 2. Test Disconnect KHÔNG Chính Xác [MEDIUM]

- **File:** `tests/unit/test_chat_hardened.py` (dòng 107-142)
- **Vấn đề:**
  ```python
  async def infinite_gen():
      yield MagicMock()
      raise GeneratorExit()  # ← KHÔNG ĐÚNG CÁCH
  ```
  - `GeneratorExit` không nên self-raise trong generator
  - Đây không phải cách Python handle generator cleanup thực tế
  - Test có thể pass nhưng **không verify được behavior thực tế**
- **Impact:** False confidence - test pass nhưng production vẫn có issue
- **Mức ưu tiên:** 🟡 **P1 - MEDIUM** (cần test đúng để catch regression)

**🔧 Solution đề xuất:**

```python
@pytest.mark.asyncio
async def test_chat_stream_disconnect_marks_failed(chat_service, mock_repo, mock_retriever):
    """Test disconnect handling thực tế."""
    # Setup...
    
    # Mock LLM stream raises CancelledError (cách đúng để simulate disconnect)
    mock_stream = AsyncMock()
    async def stream_that_gets_cancelled():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="partial"))])
        raise asyncio.CancelledError()  #← Đúng cách simulate
    
    mock_stream.__aiter__ = stream_that_gets_cancelled
    
    with patch("app.services.chat_service.llm_service") as mock_llm:
        mock_llm.stream_chat_completion.return_value = mock_stream
        
        gen = chat_service._stream_logic(...)
        with pytest.raises(asyncio.CancelledError):
            async for _ in gen:
                pass
    
    # Verify message được update thành FAILED
    mock_repo.update_message.assert_called_with(
        mock_assistant_msg.id,
        content="partial",  # ← Verify partial content được giữ lại
        status=MessageStatus.FAILED
    )
```

---

#### 3. Background Title Generation - Race Condition Risk [LOW-MEDIUM]

- **File:** `app/services/chat_service.py` (dòng 200-202, 235-262)
- **Vấn đề kép:**
  1. **Timing issue:** `background_tasks.add_task()` gọi trong `finally` block của async generator. Khi generator đóng, request context có thể đã cleanup → background task có thể không execute hoặc execute với stale context
  2. **Fail silent:** Nếu LLM error/timeout trong title generation → `logger.error()` rồi swallow. Không retry.
  3. **No timeout:** `llm_service.get_chat_completion()` không có timeout → có thể hang indefinitely nếu LLM không response
- **Impact:**
  - Conversations giữ title mặc định "Cuộc hội thoại mới" → UX giảm
  - Không ảnh hưởng core functionality
- **Mức ưu tiên:** 🟡 **P2 - LOW-MEDIUM**

**🔧 Solution đề xuất:**

```python
async def generate_conversation_title(self, conversation_id: uuid.UUID, first_query: str, max_retries: int = 2):
    """Background task với retry và timeout cho resilience."""
    from ..database import AsyncSessionLocal
    import asyncio
    
    for attempt in range(max_retries):
        try:
            async with AsyncSessionLocal() as session:
                chat_repo = ChatRepository(session)
                
                prompt = f"Generate a very short title (max 5 words) for a conversation that starts with: '{first_query}'"
                
                # Thêm timeout để tránh hang
                response = await asyncio.wait_for(
                    llm_service.get_chat_completion([
                        {"role": "user", "content": prompt}
                    ], max_tokens=LLM_MAX_TOKENS_TITLE_GENERATION),
                    timeout=30  # 30 seconds max cho title generation
                )
                
                title = response.choices[0].message.content.strip().strip('"')
                await chat_repo.session.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(title=title)
                )
                await chat_repo.session.commit()
                logger.info(f"Generated title for {conversation_id}: {title}")
                return  # Success
                
        except asyncio.TimeoutError:
            logger.warning(f"Title generation timed out on attempt {attempt + 1}")
        except Exception as e:
            logger.warning(f"Title generation attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        else:
            logger.error(f"Failed to generate title after {max_retries} attempts for {conversation_id}")
```

---

### 🟡 Observations (Nice-to-Have Improvements)

#### 4. Worker Healthcheck [LOW]
- **File:** `docker-compose.yml` (dòng 117-122)
- **Current:** Chỉ check Redis connectivity
- **Risk:** Worker container "healthy" nhưng arq process crash → jobs không consume
- **Mitigation hiện tại:** `depends_on: api` đảm bảo start order đúng
- **Recommend:** Giữ nguyên. Upgrade nếu có issue thực tế.

#### 5. Integration Tests Thiếu [MEDIUM]
- **File:** `tests/unit/test_chat_hardened.py`
- **Vấn đề:** Chỉ dùng MagicMock, không test với real async session + database
- **Risk:** Miss issues liên quan đến session lifecycle, transaction isolation, flush behavior thực tế
- **Recommend:** Thêm integration test ở phase sau

#### 6. API Route `/chat/stream` Gọi `_stream_logic` Trực Tiếp [INFO]
- **File:** `app/api/chat.py` (dòng 55-95)
- **Observation:** Route tự tạo session và gọi `_stream_logic` thay vì dùng `ChatService.chat_stream_with_conversation()`
- **Assessment:** ✅ Session lifecycle đúng, không có issue
- **Note:** Code hơi duplicate logic → có thể refactor sau (ưu tiên rất thấp)

---

## Proposed Changes

### P0: Fix Stream Disconnect Handling (Option A - Defensive)

#### [MODIFY] `app/services/chat_service.py`

**Current flow:**
```
1. Commit user message
2. Create PENDING assistant message + commit
3. Stream from LLM
4. If success → update COMPLETED + commit
5. If error/disconnect → update FAILED + commit
```

**Problem:** Step 5 may not execute if disconnect cancels task

**Proposed flow:**
```
1. Commit user message
2. Create PENDING assistant message + commit
3. **Set FAILED default** + commit (defensive)
4. Stream from LLM
5. If success → update COMPLETED + commit (override FAILED)
6. If error/disconnect → already FAILED (no action needed)
```

**Code changes:**

```python
# Trong _stream_logic, sau commit 2 (PENDING message):

# 5b. Defensive: Set FAILED default trước khi stream
# Nếu stream thành công → override thành COMPLETED
# Nếu disconnect → vẫn còn FAILED, không cần additional commit
await chat_repo.update_message(
    assistant_msg.id,
    content="",
    status=MessageStatus.FAILED
)
await chat_repo.session.commit()

# 6. Yield Meta Info
yield f"event: meta\ndata: {json.dumps({'message_id': str(assistant_msg.id), 'conversation_id': str(conversation_id)})}\n\n"

full_content = ""
try:
    # ... stream logic ...
    
    # Success: Override thành COMPLETED
    await chat_repo.update_message(
        assistant_msg.id,
        content=full_content,
        status=MessageStatus.COMPLETED
    )
    await chat_repo.session.commit()
    yield f"event: done\ndata: ...\n\n"

except (asyncio.CancelledError, GeneratorExit):
    logger.warning(f"Stream disconnected for message {assistant_msg.id}")
    # Message đã ở FAILED từ trước, chỉ cần log
    raise

except Exception as e:
    logger.error(f"Stream error: {e}")
    # Update với partial content nếu có
    await chat_repo.update_message(
        assistant_msg.id,
        content=full_content,
        status=MessageStatus.FAILED
    )
    await chat_repo.session.commit()
    yield f"event: error\ndata: {json.dumps({'detail': str(e), 'code': 'STREAM_INTERRUPTED'})}\n\n"
```

**Trade-offs:**
- ✅ **Pros:** Không cần await trong except block → guarantee data integrity
- ⚠️ **Cons:** Thêm 1 commit nữa (total: 4 thay vì 3) → minor performance hit
- ⚠️ **Cons:** Nếu stream disconnect NGAY SAU commit FAILED, user vẫn thấy empty message → acceptable trade-off

**Test impact:**
- Cần update `test_chat_stream_durability_commits` từ `commit_count == 3` → `commit_count == 4`

---

### P1: Fix Test Disconnect Handling

#### [MODIFY] `tests/unit/test_chat_hardened.py`

```python
@pytest.mark.asyncio
async def test_chat_stream_disconnect_marks_failed(chat_service, mock_repo, mock_retriever):
    """Test that CancelledError properly marks message as FAILED."""
    # Setup
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    mock_conv = MagicMock()
    mock_conv.document_id = doc_id
    mock_repo.get_conversation.return_value = mock_conv

    mock_assistant_msg = MagicMock()
    mock_assistant_msg.id = uuid.uuid4()
    mock_assistant_msg.context_used = {}
    mock_repo.add_message.return_value = mock_assistant_msg

    # Mock LLM stream that gets cancelled after first chunk
    mock_stream = AsyncMock()
    async def stream_that_gets_cancelled():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="partial"))])
        raise asyncio.CancelledError()

    mock_stream.__aiter__ = stream_that_gets_cancelled

    with patch("app.services.chat_service.llm_service") as mock_llm:
        mock_llm.stream_chat_completion.return_value = mock_stream

        gen = chat_service._stream_logic(
            chat_repo=mock_repo,
            retriever=mock_retriever,
            conversation_id=conv_id,
            document_id=doc_id,
            user_query="hello",
            background_tasks=MagicMock()
        )
        with pytest.raises(asyncio.CancelledError):
            async for _ in gen:
                pass

    # Verify: update_message called with status=FAILED và partial content
    mock_repo.update_message.assert_any_call(
        mock_assistant_msg.id,
        content="",  # Default FAILED
        status=MessageStatus.FAILED
    )
    # Should have been committed
    assert mock_repo.session.commit.call_count >= 3
```

---

### P2: Cải thiện Background Title Generation

*(Như đã đề xuất ở phần Finding #3 ở trên)*

---

## Open Questions

1. **Timeout handling:** Khi LLM stream timeout sau X giây với partial content, có nên:
   - **A:** Giữ partial content với status=COMPLETED? (User thấy ít nhấtsomething)
   - **B:** Giữ nguyên status=FAILED? (Nhất quán với error handling)
   - **Current code:** Option B → **Recommend giữ nguyên**

2. **Worker Healthcheck:** Giữ nguyên (Redis check) hay nâng cấp (process check)?
   - **Recommend:** Giữ nguyên. Stack ổn định 6/6 healthy.

3. **Integration Tests:** Ưu tiên viết ngay hay defer?
   - **Recommend:** Defer. Unit tests coverage đủ cho regression prevention.

---

## Implementation Priority & Order

| Priority | Item | Effort | Risk if skipped | Impact |
|----------|------|--------|-----------------|--------|
| 🥇 **P0** | Fix stream disconnect handling | ~30 min | **HIGH** - Orphan PENDING messages | Data integrity |
| 🥈 **P1** | Fix test disconnect handling | ~15 min | Medium - False confidence | Test reliability |
| 🥉 **P2** | Title generation retry + timeout | ~20 min | Low - UX minor | Better UX |
| ⏸️ **Future** | Integration tests | 1-2 hrs | Medium | Higher confidence |
| ⏸️ **Future** | Worker healthcheck upgrade | 10 min | Low | Operational visibility |

---

## Verification Plan

### Automated Tests
```bash
# Unit tests - sau khi update
pytest tests/unit/test_chat_hardened.py -v

# Verify commit counts
# P0 sau khi implement: commit_count == 4

# Full test suite
pytest tests/ -v --tb=short
```

### Manual Verification
- **Test stream disconnect:**
  1. Start app, chat qua API/frontend
  2. Giữa chừng cancel request (Ctrl+C hoặc close connection)
  3. Query DB:
     ```sql
     SELECT id, role, status, content, created_at 
     FROM messages 
     WHERE status = 'PENDING'
     ORDER BY created_at DESC;
     ```
     → **Expect:** Empty result (không còn orphan PENDING messages)

- **Test title generation:**
  1. Tạo conversation mới
  2. Check logs: Should see retry attempts nếu LLM fail
  3. Query DB: `SELECT id, title FROM conversations ORDER BY created_at DESC LIMIT 5;`

- **Verify no regression:**
  ```bash
  docker compose ps  # All healthy
  pytest tests/ -v   # All pass
  ```

---

## Success Criteria

- [ ] P0: Stream disconnect test pass → không còn orphan PENDING messages
- [ ] P1: Test dùng `CancelledError` thay vì `GeneratorExit`, verify đúng behavior
- [ ] P2: Title generation có retry (2 attempts) và timeout (30s)
- [ ] All existing tests pass với updated assertions
- [ ] Manual test: Chat stream hoạt động bình thường, disconnect xử lý đúng

---

## Risk Assessment

| Change | Risk Level | Mitigation |
|--------|------------|------------|
| P0: Defensive commit | Low | Thêm commit, không thay đổi logic hiện tại |
| P1: Test fix | None | Chỉ sửa test, không đụng production code |
| P2: Title retry | Low | Pattern đã có trong `structured_extraction` |

---

> **✅ Kết luận cuối cùng (v3 - Deep Audit):**  
> Codebase ổn định, nhưng có **1 issue thực sự cần fix** (P0: stream disconnect handling).  
> Đây là problem affects **data integrity** - orphan PENDING messages tích tụ theo thời gian.  
> **Ready to implement?** → Start với P0, sau đó P1, rồi P2. Total effort: ~1 giờ.
