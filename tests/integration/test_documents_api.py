import pytest
import io
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_upload_valid_pdf(async_client: AsyncClient, sample_pdf_bytes: bytes):
    """Test upload file PDF hợp lệ -> 202 Accepted"""
    files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    
    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "test.pdf"
    assert data["status"] == "PENDING"

@pytest.mark.asyncio
async def test_upload_duplicate(async_client: AsyncClient, sample_pdf_bytes: bytes):
    """Test upload file đã tồn tại -> 409 Conflict (BR-017)"""
    # Lần 1: Upload mới
    files = {"file": ("test_dup.pdf", sample_pdf_bytes, "application/pdf")}
    response1 = await async_client.post("/api/v1/documents/upload", files=files)
    assert response1.status_code == 202

    # Lần 2: Upload lại chính file đó -> 409 theo BR-017
    # Lưu ý: Document đầu tiên có thể còn PENDING/PROCESSING → BR-011 trigger trước
    response2 = await async_client.post("/api/v1/documents/upload", files=files)

    assert response2.status_code == 409
    data = response2.json()
    # Có thể là "đang được xử lý" (BR-011) hoặc "đã được upload" (BR-017)
    assert any(msg in data["detail"] for msg in [
        "đã được upload trước đó",
        "đang được xử lý"
    ])

@pytest.mark.asyncio
async def test_list_documents(async_client: AsyncClient, processed_document):
    """Test liệt kê danh sách tài liệu"""
    response = await async_client.get("/api/v1/documents/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(d["id"] == str(processed_document.id) for d in data)

@pytest.mark.asyncio
async def test_get_document_status(async_client: AsyncClient, processed_document):
    """Test lấy trạng thái tài liệu cụ thể"""
    doc_id = str(processed_document.id)
    response = await async_client.get(f"/api/v1/documents/{doc_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["status"] == "COMPLETED"
    assert data["entity_count"] == 1

@pytest.mark.asyncio
async def test_delete_document(async_client: AsyncClient, processed_document):
    """Test xóa tài liệu"""
    doc_id = str(processed_document.id)
    response = await async_client.delete(f"/api/v1/documents/{doc_id}")
    
    assert response.status_code == 200
    assert "đã được xóa" in response.json()["message"]
    
    # Kiểm tra lại xem còn tồn tại không
    check_response = await async_client.get(f"/api/v1/documents/{doc_id}")
    assert check_response.status_code == 404

@pytest.mark.asyncio
async def test_get_nonexistent_document(async_client: AsyncClient):
    """Test lấy tài liệu không tồn tại -> 404"""
    random_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/documents/{random_id}")
    assert response.status_code == 404
