import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.pipeline import LightRAGPipeline
from app.models.document import DocumentStatus, ProcessingStep

# Tạo concrete subclass cho testing (vì LightRAGPipeline là abstract)
class ConcreteLightRAGPipeline(LightRAGPipeline):
    async def process_document(self, doc_id, text):
        """Implementation rỗng cho testing."""
        pass

@pytest.fixture
def mock_repos():
    return {
        'doc': AsyncMock(),
        'chunk': AsyncMock(),
        'graph': AsyncMock()
    }

@pytest.fixture
def mock_extractor():
    return AsyncMock()

@pytest.fixture
def mock_retriever():
    return AsyncMock()

@pytest.fixture
def pipeline(mock_repos, mock_extractor, mock_retriever):
    return ConcreteLightRAGPipeline(
        mock_repos['doc'],
        mock_repos['chunk'],
        mock_repos['graph'],
        mock_extractor,
        mock_retriever
    )

@pytest.mark.asyncio
async def test_chunking_logic(pipeline):
    text = "A" * 1000  # 1000 chars
    # chunk_size=800, overlap=150
    # Chunk 1: [0:800]
    # Chunk 2: [650:1450] -> [650:1000]
    chunks = pipeline._chunk_text(text)
    assert len(chunks) == 2
    assert chunks[0] == "A" * 800
    assert chunks[1] == "A" * 350

@pytest.mark.asyncio
async def test_ingest_text_success(pipeline, mock_repos, mock_extractor):
    doc_id = uuid.uuid4()
    text = "Relativity is a theory by Albert Einstein."

    # Mock Extractor result
    mock_entity = MagicMock()
    mock_entity.name = "Einstein"
    mock_entity.entity_type = "PERSON"
    mock_entity.description = "Physicist"
    mock_entity.confidence = 0.9

    extraction_mock = MagicMock()
    extraction_mock.entities = [mock_entity]
    extraction_mock.relations = []

    mock_extractor.extract = AsyncMock(return_value=extraction_mock)
    mock_extractor.deduplicate_entities = MagicMock(return_value=[mock_entity])

    with patch("app.core.pipeline.chroma_client") as mock_chroma:
        result = await pipeline.ingest_text(doc_id, text)

        assert result == str(doc_id)
        # Verify repo calls
        mock_repos['doc'].update_status.assert_any_call(doc_id, DocumentStatus.PROCESSING)
        mock_repos['doc'].update_status.assert_any_call(doc_id, DocumentStatus.COMPLETED)

        # Verify bulk inserts
        mock_repos['chunk'].bulk_insert.assert_called_once()
        mock_repos['graph'].bulk_upsert_entities.assert_called_once()

        # Verify chroma additions (new wrapper methods)
        assert mock_chroma.add_chunks.called
        assert mock_chroma.add_entities.called

@pytest.mark.asyncio
async def test_ingest_error_handling(pipeline, mock_repos):
    doc_id = uuid.uuid4()
    text = "Fail test"
    
    # Simulate error in chunking or first step
    mock_repos['doc'].update_status.side_effect = Exception("DB Error")
    
    with pytest.raises(Exception):
        await pipeline.ingest_text(doc_id, text)
    
    # Verification of error logging in DB
    # Note: If update_status itself fails, it might not be logged or might raise.
    # Let's test a scenario where a later step fails.
    mock_repos['doc'].update_status.side_effect = None
    pipeline._chunk_text = MagicMock(side_effect=ValueError("Chunk error"))
    
    with pytest.raises(ValueError):
        await pipeline.ingest_text(doc_id, text)
    
    # Should update status to FAILED
    mock_repos['doc'].update_status.assert_any_call(doc_id, DocumentStatus.FAILED, "Chunk error")
