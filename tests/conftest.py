import pytest
import asyncio
import uuid
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.database import Base, get_db
from app.config import settings
from tests.mocks.llm_mock import MockLLMService

# --- Database Setup for Testing ---
# Chúng ta sử dụng database hiện tại nhưng với cơ chế auto-rollback cho mỗi test
# Nếu muốn dùng DB riêng, hãy set DATABASE_URL trong môi trường test

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
    Fixture cho database session.
    Tự động rollback sau mỗi test để giữ database sạch.
    NOTE: Không dùng autouse=True để tránh conflict với unit tests không cần DB.
    Integration tests sẽ gọi fixture này tường minh.
    """
    async with test_engine.begin() as conn:
        # Tùy chọn: Create tables nếu chưa có (thường đã có qua alembic)
        # await conn.run_sync(Base.metadata.create_all)

        async with TestAsyncSessionLocal(bind=conn) as session:
            yield session
            await session.rollback()

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


# --- Integration Test Fixtures (cần DB thật) ---

@pytest.fixture
async def integration_test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture cho integration tests cần database thật.
    Gọi tường minh trong integration tests.
    """
    async with test_engine.begin() as conn:
        async with TestAsyncSessionLocal(bind=conn) as session:
            yield session
            await session.rollback()

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
    from app.models.graph import Entity, Relation
    
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        filename="test_manual.pdf",
        file_path="/tmp/test_manual.pdf",
        status=DocumentStatus.COMPLETED,
        processing_step=ProcessingStep.COMPLETED,
        entity_count=1,
        relation_count=0
    )
    test_db.add(doc)
    
    # Thêm entity mẫu
    entity = Entity(
        document_id=doc_id,
        canonical_name="Albert Einstein",
        entity_type="PERSON",
        description="Nhà vật lý lý thuyết người Đức."
    )
    test_db.add(entity)
    
    await test_db.commit()
    await test_db.refresh(doc)
    return doc
