# 🛠️ Implementation Guide — Step by Step

> **Purpose:** Hướng dẫn chi tiết từng bước để fix các issues found trong SRS analysis  
> **Created:** April 11, 2026  
> **Estimated Total Time:** ~5 giờ (Pre-Launch)

---

## Step 1: Fix SM-2 Interval Bug (5 phút) 🔴

### File: `app/services/sm2_service.py`

**Line 77** — Change:
```python
# Before
if quality < 3:
    new_repetitions = 0
    new_interval = 1  # Review lại sau 1 ngày

# After
if quality < 3:
    new_repetitions = 0
    new_interval = 0  # SM-2 standard: review immediately
```

### Test:
```bash
pytest tests/unit/test_sm2_algorithm.py -v -k "failed"
```

### Commit:
```bash
git add app/services/sm2_service.py
git commit -m "fix: SM-2 interval=0 on failed recall (spec compliance)"
```

---

## Step 2: Add Document Status Check (15 phút) 🟡

### File: `app/services/flashcard_generation_service.py`

**Add at start of `generate_from_document()`:**
```python
from app.models.document import Document
from sqlalchemy import select

async def generate_from_document(
    self,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    source: str = "auto_generated",
    max_cards: int = 50,
    min_confidence: float = 0.7,
    db_session: Optional[AsyncSession] = None
):
    # ✅ NEW: Check document status
    if db_session:
        doc_result = await db_session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        
        if doc.status != "COMPLETED":
            raise ValueError(
                f"Document must be completed before generating flashcards. "
                f"Current status: {doc.status}"
            )
    
    # Continue with existing logic...
    entities = await self.graph_repo.get_entities_by_document(...)
```

### Test:
```bash
# Create test with pending document
pytest tests/unit/test_flashcard_generation.py -v -k "status"
```

### Commit:
```bash
git add app/services/flashcard_generation_service.py
git commit -m "feat: add document status validation before flashcard generation"
```

---

## Step 3: Add attempt_count Column (30 phút) 🟡

### 3.1 Create Migration

```bash
# Alembic migration
alembic revision --autogenerate -m "add attempt_count to conversations"
```

**Migration file:**
```python
def upgrade():
    op.add_column('conversations', sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('conversations', sa.Column('current_concept', sa.String(length=500), nullable=True))

def downgrade():
    op.drop_column('conversations', 'current_concept')
    op.drop_column('conversations', 'attempt_count')
```

**Run:**
```bash
alembic upgrade head
```

### 3.2 Update Model

**File: `app/models/conversation.py`**
```python
from sqlalchemy import Integer, String

class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    
    # ... existing columns ...
    
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    current_concept: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
```

### 3.3 Update Chat Service

**File: `app/services/chat_service.py`**
```python
async def chat_stream(self, conversation_id: uuid.UUID, document_id: uuid.UUID, message: str):
    conv = await self.chat_repo.get(conversation_id)
    
    # Increment attempt count
    conv.attempt_count = (conv.attempt_count or 0) + 1
    
    # Detect concept change
    if self._detect_concept_change(message, conv.current_concept):
        conv.attempt_count = 0
        conv.current_concept = self._extract_concept(message)
    
    # Build prompt based on attempts
    system_prompt = self._build_socratic_prompt(conv.attempt_count)
    
    await self.chat_repo.session.commit()
    
    # Continue with streaming...
```

### Commit:
```bash
git add alembic/versions/xxx_add_attempt_count.py
git add app/models/conversation.py
git add app/services/chat_service.py
git commit -m "feat: add attempt_count tracking for Socratic pedagogy"
```

---

## Step 4: Auto-Call Backlinks (1 giờ) 🟡

### File: `app/services/note_service.py`

**Update `create_note()`:**
```python
async def create_note(
    self,
    user_id: uuid.UUID,
    title: str,
    content: str,
    note_type: str = "literature",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    note = await self.note_repo.create(
        user_id=user_id,
        title=title,
        content=content,
        note_type=note_type,
        tags=tags or [],
        metadata=metadata or {},
    )
    
    # ✅ Auto-suggest backlinks (non-blocking)
    try:
        backlinks = await self.suggest_backlinks(note.id, user_id)
        return {"note": note, "backlink_suggestions": backlinks}
    except Exception as e:
        logger.warning(f"Backlink suggestion failed for note {note.id}: {e}")
        return {"note": note, "backlink_suggestions": []}
```

**Update `update_note()`:**
```python
async def update_note(
    self,
    note_id: uuid.UUID,
    user_id: uuid.UUID,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    note = await self.note_repo.get(note_id)
    if not note or note.user_id != user_id:
        return None
    
    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    if tags is not None:
        note.tags = tags
    
    await self.note_repo.session.commit()
    await self.note_repo.session.refresh(note)
    
    # ✅ Re-suggest backlinks after update
    try:
        backlinks = await self.suggest_backlinks(note.id, user_id)
        return {"note": note, "backlink_suggestions": backlinks}
    except Exception as e:
        logger.warning(f"Backlink suggestion failed for note {note.id}: {e}")
        return {"note": note, "backlink_suggestions": []}
```

### Commit:
```bash
git add app/services/note_service.py
git commit -m "feat: auto-call backlink suggestions on note create/update"
```

---

## Step 5: Add Tests (2 giờ) 🟡

### File: `tests/unit/test_sm2_interval_fix.py`
```python
import pytest
from app.services.sm2_service import SM2Service

class TestSM2IntervalFix:
    def test_failed_recall_immediate_review(self):
        result = SM2Service.calculate_sm2_update(
            current_ease=2.5, current_interval=6, current_repetitions=2, quality=2
        )
        assert result["interval"] == 0
        assert result["repetitions"] == 0

    def test_quality_0_1_2_all_reset(self):
        for quality in [0, 1, 2]:
            result = SM2Service.calculate_sm2_update(2.5, 6, 2, quality)
            assert result["interval"] == 0, f"quality={quality}"
            assert result["repetitions"] == 0, f"quality={quality}"
```

### File: `tests/unit/test_flashcard_validation.py`
```python
import pytest
from app.services.flashcard_generation_service import FlashcardGenerationService

@pytest.mark.asyncio
async def test_generate_requires_completed_document():
    # Setup pending document
    # Assert raises ValueError
    pass
```

### File: `tests/integration/test_chat_attempt.py`
```python
@pytest.mark.asyncio
async def test_attempt_count_increments():
    # Create conversation
    # Send messages
    # Assert attempt_count increments
    pass
```

### Run all tests:
```bash
pytest tests/ -v --tb=short
```

### Commit:
```bash
git add tests/
git commit -m "test: add tests for SM-2 fix, doc validation, attempt tracking"
```

---

## Step 6: Update Documentation (30 phút) 🟢

### File: `docs/srs/Business_Rules.md`

**BR-002 Update:**
```markdown
## BR-002: Document Processing Pipeline 🔴

**2-Level State Machine:**

1. **DocumentStatus** (User-facing):
   PENDING → PROCESSING → COMPLETED / FAILED

2. **ProcessingStep** (Internal):
   QUEUED → INITIAL → EXTRACTING → CHUNKING → EXTRACTING_ENTITIES → BUILDING_GRAPH → EMBEDDING → COMPLETED
```

**BR-005 Update:**
```markdown
## BR-005: SM-2 Scheduling Rule 🔴

**Updated:** 
- Nếu quality < 3: interval = 0 (review immediately)
- Implementation: Fixed từ interval=1 → interval=0
```

### Commit:
```bash
git add docs/srs/Business_Rules.md
git commit -m "docs: update BR-002 (2-level state), BR-005 (interval fix)"
```

---

## ✅ Final Checklist

- [ ] SM-2 interval bug fixed
- [ ] Document status check added
- [ ] attempt_count column + logic
- [ ] Auto-backlinks in create/update
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Merged to main

---

## 🚀 Deployment

```bash
# 1. Run migrations
alembic upgrade head

# 2. Restart services
docker compose restart backend worker

# 3. Verify
curl http://localhost/health
pytest tests/ -v
```

---

© 2026 AetherTutor Team
