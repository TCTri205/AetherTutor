import pytest
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, UploadFile
from app.services.document_service import DocumentService
from app.models.document import DocumentStatus

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def mock_arq_pool():
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock(return_value=None)
    return pool

@pytest.fixture
def doc_service(mock_session, mock_arq_pool):
    return DocumentService(mock_session, mock_arq_pool)

@pytest.mark.asyncio
async def test_upload_new_document_success(doc_service, mock_session, mock_arq_pool):
    # Mock file
    file_content = b"%PDF-test"
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.read = AsyncMock(return_value=file_content)
    
    # Mock repo & methods
    doc_id = uuid.uuid4()
    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.filename = "test.pdf"
    
    doc_service.repo.get_by_hash = AsyncMock(return_value=None)
    doc_service.repo.create = AsyncMock(return_value=mock_doc)
    doc_service.repo.update_file_path = AsyncMock()
    doc_service.repo.update_status = AsyncMock()
    
    with patch("os.makedirs"), \
         patch("aiofiles.open", MagicMock()) as mock_aio_open:
        
        # Thiết lập aiofiles mock deep
        mock_f = AsyncMock()
        mock_aio_open.return_value.__aenter__.return_value = mock_f
        
        doc, is_duplicate = await doc_service.upload_document(mock_file)
        
        assert doc.id == doc_id
        assert is_duplicate is False
        doc_service.repo.create.assert_called_once()
        mock_arq_pool.enqueue_job.assert_called_once_with("process_document_task", str(doc_id))

@pytest.mark.asyncio
async def test_upload_duplicate_document():
    # Mock file
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.read = AsyncMock(return_value=b"dup")

    # Mock existing doc
    existing_doc = MagicMock()
    
    # Mock repo với patch DocumentRepository
    with patch("app.services.document_service.DocumentRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_by_hash = AsyncMock(return_value=existing_doc)
        mock_repo_instance.create = AsyncMock(return_value=MagicMock())

        mock_session = AsyncMock()
        mock_arq_pool = AsyncMock()
        mock_arq_pool.enqueue_job = AsyncMock()
        
        service = DocumentService(mock_session, mock_arq_pool)

        doc, is_duplicate = await service.upload_document(mock_file)

        assert doc == existing_doc
        assert is_duplicate is True
        mock_repo_instance.create.assert_not_called()

@pytest.mark.asyncio
async def test_upload_invalid_extension(doc_service):
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.exe"
    
    with pytest.raises(HTTPException) as excinfo:
        await doc_service.upload_document(mock_file)
    
    assert excinfo.value.status_code == 400
    assert "không được hỗ trợ" in excinfo.value.detail

@pytest.mark.asyncio
async def test_upload_oversized_file(doc_service):
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "large.pdf"
    # Giả lập file 51MB (vượt quá 50MB mặc định)
    mock_file.read = AsyncMock(return_value=b"X" * (51 * 1024 * 1024))
    
    with pytest.raises(HTTPException) as excinfo:
        await doc_service.upload_document(mock_file)
    
    assert excinfo.value.status_code == 413
    assert "File quá lớn" in excinfo.value.detail

@pytest.mark.asyncio
async def test_delete_document_success(doc_service, mock_session):
    doc_id = uuid.uuid4()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"
    doc_service.repo.get_by_id = AsyncMock(return_value=mock_doc)
    doc_service.repo.delete = AsyncMock()
    
    with patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove, \
         patch("app.services.document_service.chroma_client") as mock_chroma:
        
        result = await doc_service.delete_document(doc_id)
        
        assert result is True
        doc_service.repo.delete.assert_called_once_with(doc_id)
        mock_remove.assert_called_once_with("/tmp/test.pdf")
        mock_chroma.delete_by_document_id.assert_called_once_with(doc_id)

@pytest.mark.asyncio
async def test_delete_document_not_found(doc_service):
    doc_id = uuid.uuid4()
    doc_service.repo.get_by_id = AsyncMock(return_value=None)
    
    with pytest.raises(HTTPException) as excinfo:
        await doc_service.delete_document(doc_id)
    
    assert excinfo.value.status_code == 404
