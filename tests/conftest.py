import pytest
import asyncio
import uuid
import hashlib
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.database import get_db
from app.config import settings
from tests.mocks.llm_mock import MockLLMService

# --- Database Setup for Testing ---

# Safety guard: refuse to run tests against production database
if settings.APP_ENV == "production" and "test" not in settings.DB_NAME.lower():
    raise RuntimeError(
        "Refusing to run tests against production database. "
        "Set DB_NAME to contain 'test' or APP_ENV != 'production'."
    )

test_engine = create_async_engine(settings.DATABASE_URL, future=True)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Tạo event loop cho cả session test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture cho database session với connection-level transaction isolation.
    Mỗi test nhận một connection riêng, bắt đầu transaction ở đầu test
    và rollback toàn bộ ở cuối — đảm bảo không rò rỉ dữ liệu giữa các test.
    Code trong test vẫn có thể gọi commit(), nhưng outer rollback sẽ undo tất cả.

    Trước khi yield, cleanup dữ liệu từ test trước (nếu còn sót) để
    đảm bảo test isolation.
    Sau khi teardown, dispose engine pool để giải phóng stale asyncpg
    connections trên Windows Proactor Event Loop.
    """
    from sqlalchemy import delete
    from app.models.document import Document

    # Cleanup leftover test data from previous tests (safety net).
    # FK constraints are CASCADE, so deleting documents cleans up
    # graph_entities, graph_relations, conversations, messages automatically.
    async with test_engine.connect() as conn:
        await conn.execute(delete(Document))
        await conn.commit()

    async with test_engine.begin() as conn:
        async with TestAsyncSessionLocal(bind=conn) as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await conn.rollback()
                await session.close()

    # Dispose pool sau mỗi test để tránh stale connections trên Windows.
    # Đây là trade-off: chậm hơn nhưng đảm bảo stability.
    await test_engine.dispose()

@pytest.fixture
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture cho httpx AsyncClient.
    Override dependency get_db để dùng test_db.
    Mock arq_pool để không cần Redis thật khi test API.
    """
    from unittest.mock import AsyncMock
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=None)
    app.state.arq_pool = mock_pool

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://testserver"
    ) as client:
        yield client
    
    app.dependency_overrides.clear()

# --- LLM Mocking Fixture ---

@pytest.fixture(autouse=True)
def patch_llm_service(monkeypatch):
    """
    Tự động patch LLM service nếu USE_LLM_MOCK=true.
    """
    if settings.USE_LLM_MOCK:
        mock = MockLLMService()
        monkeypatch.setattr("app.services.llm_service.llm_service", mock)
        return mock
    return None


# --- Data Fixtures ---

@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Dữ liệu PDF giả lập (minimal)."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

@pytest.fixture
async def processed_document(test_db: AsyncSession):
    """
    Fixture tạo sẵn một document đã hoàn thành (COMPLETED) kèm Graph data mẫu.
    """
    from app.models.document import Document, DocumentStatus, ProcessingStep
    from app.models.graph import GraphEntity
    from app.models.user import User

    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    # Đảm bảo user tồn tại
    user = await test_db.get(User, default_user_id)
    if not user:
        user = User(
            id=default_user_id,
            email="test@example.com",
            hashed_password="hashed",
            is_active=True
        )
        test_db.add(user)
        await test_db.flush()

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=default_user_id,
        filename="test_manual.pdf",
        file_path="/tmp/test_manual.pdf",
        content_hash=hashlib.sha256(b"test_manual").hexdigest(),
        status=DocumentStatus.COMPLETED,
        processing_step=ProcessingStep.COMPLETED,
    )
    test_db.add(doc)
    await test_db.flush()

    # Thêm entity mẫu
    entity = GraphEntity(
        document_id=doc_id,
        user_id=default_user_id,
        canonical_name="Albert Einstein",
        entity_type="PERSON",
        description="Nhà vật lý lý thuyết người Đức.",
        confidence=1.0
    )
    test_db.add(entity)

    await test_db.commit()
    await test_db.refresh(doc)
    return doc
