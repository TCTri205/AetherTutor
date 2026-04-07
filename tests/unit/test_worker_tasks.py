import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.worker.tasks import process_document_task
from app.models.document import DocumentStatus, ProcessingStep
from app.core.exceptions import PermanentProcessingError

@pytest.mark.asyncio
async def test_process_document_task_flow():
    doc_id = uuid.uuid4()
    ctx = MagicMock()

    # Mock Document data
    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.filename = "test.pdf"
    mock_doc.file_path = "/tmp/test.pdf"

    with patch("app.worker.tasks.async_session_factory") as mock_session_factory, \
         patch("app.worker.tasks.DocumentRepository") as MockDocRepo, \
         patch("app.worker.tasks.ChunkRepository") as MockChunkRepo, \
         patch("app.worker.tasks.GraphRepository") as MockGraphRepo, \
         patch("app.worker.tasks.pdf_extractor") as mock_pdf_extractor, \
         patch("app.worker.tasks.LightRAGPipeline") as MockPipeline, \
         patch("app.worker.tasks.chroma_client") as mock_chroma, \
         patch("app.worker.tasks.EntityExtractor") as MockEntityExtractor, \
         patch("app.worker.tasks.Retriever") as MockRetriever:

        # Setup session mock
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        # Setup repo mock
        doc_repo = MockDocRepo.return_value
        doc_repo.get_by_id = AsyncMock(return_value=mock_doc)
        doc_repo.update_processing_step = AsyncMock()
        doc_repo.update_status = AsyncMock()
        doc_repo.update_file_path = AsyncMock()

        chunk_repo = MockChunkRepo.return_value
        chunk_repo.delete_by_document_id = AsyncMock()

        graph_repo = MockGraphRepo.return_value
        graph_repo.delete_by_document_id = AsyncMock()

        # Setup pipeline mock
        pipeline = MockPipeline.return_value
        pipeline.ingest_text = AsyncMock()

        # Setup extractor mock
        mock_pdf_extractor.extract_text.return_value = "Extracted text content"

        await process_document_task(ctx, str(doc_id))

        # Verify flow
        mock_pdf_extractor.extract_text.assert_called_once_with("/tmp/test.pdf")
        pipeline.ingest_text.assert_called_once_with(doc_id, "Extracted text content")
        mock_session.commit.assert_called()

@pytest.mark.asyncio
async def test_process_permanent_error():
    doc_id = uuid.uuid4()
    ctx = MagicMock()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.filename = "test.pdf"
    mock_doc.file_path = None  # Will cause PermanentProcessingError

    with patch("app.worker.tasks.async_session_factory") as mock_session_factory, \
         patch("app.worker.tasks.DocumentRepository") as MockDocRepo, \
         patch("app.worker.tasks.ChunkRepository") as MockChunkRepo, \
         patch("app.worker.tasks.GraphRepository") as MockGraphRepo, \
         patch("app.worker.tasks.LightRAGPipeline") as MockPipeline, \
         patch("app.worker.tasks.EntityExtractor") as MockEntityExtractor, \
         patch("app.worker.tasks.Retriever") as MockRetriever, \
         patch("app.worker.tasks.chroma_client") as mock_chroma:

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        doc_repo = MockDocRepo.return_value
        doc_repo.get_by_id = AsyncMock(return_value=mock_doc)
        doc_repo.update_status = AsyncMock()

        chunk_repo = MockChunkRepo.return_value
        chunk_repo.delete_by_document_id = AsyncMock()

        graph_repo = MockGraphRepo.return_value
        graph_repo.delete_by_document_id = AsyncMock()

        await process_document_task(ctx, str(doc_id))

        # Should catch PermanentProcessingError and update status to FAILED
        # and NOT re-raise
        doc_repo.update_status.assert_called_once_with(
            doc_id, DocumentStatus.FAILED, "Tài liệu không có đường dẫn file vật lý."
        )

@pytest.mark.asyncio
async def test_process_transient_error_retry():
    doc_id = uuid.uuid4()
    ctx = MagicMock()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.filename = "test.pdf"
    mock_doc.file_path = "/tmp/test.pdf"

    with patch("app.worker.tasks.async_session_factory") as mock_session_factory, \
         patch("app.worker.tasks.DocumentRepository") as MockDocRepo, \
         patch("app.worker.tasks.ChunkRepository") as MockChunkRepo, \
         patch("app.worker.tasks.GraphRepository") as MockGraphRepo, \
         patch("app.worker.tasks.LightRAGPipeline") as MockPipeline, \
         patch("app.worker.tasks.EntityExtractor") as MockEntityExtractor, \
         patch("app.worker.tasks.Retriever") as MockRetriever, \
         patch("app.worker.tasks.chroma_client") as mock_chroma, \
         patch("app.worker.tasks.pdf_extractor") as mock_pdf_extractor:

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        doc_repo = MockDocRepo.return_value
        doc_repo.get_by_id = AsyncMock(return_value=mock_doc)
        doc_repo.update_status = AsyncMock()
        doc_repo.update_processing_step = AsyncMock()
        doc_repo.update_file_path = AsyncMock()

        chunk_repo = MockChunkRepo.return_value
        chunk_repo.delete_by_document_id = AsyncMock()

        graph_repo = MockGraphRepo.return_value
        graph_repo.delete_by_document_id = AsyncMock()

        # Simulate transient error (Network, etc)
        mock_pdf_extractor.extract_text.side_effect = Exception("Temporary Connection Error")

        with pytest.raises(Exception) as excinfo:
            await process_document_task(ctx, str(doc_id))

        assert "Temporary Connection Error" in str(excinfo.value)
        # Should have tried to mark as FAILED before re-raising
        doc_repo.update_status.assert_called_with(
            doc_id, DocumentStatus.FAILED, "Lỗi hệ thống: Temporary Connection Error"
        )
