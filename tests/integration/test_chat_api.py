import pytest
import uuid
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_conversation(async_client: AsyncClient, processed_document):
    """Test tạo cuộc hội thoại mới"""
    doc_id = str(processed_document.id)
    response = await async_client.post(
        f"/api/v1/chat/conversations/{doc_id}",
        json={"title": "Test Conversation"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["title"] == "Test Conversation"
    assert "id" in data

@pytest.mark.asyncio
async def test_list_conversations(async_client: AsyncClient, processed_document):
    """Test liệt kê các cuộc hội thoại của một tài liệu"""
    doc_id = str(processed_document.id)
    # Tạo sẵn 1 cái
    await async_client.post(f"/api/v1/chat/conversations/{doc_id}", json={"title": "C1"})
    
    response = await async_client.get(f"/api/v1/chat/conversations/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

@pytest.mark.asyncio
async def test_chat_stream_sse(async_client: AsyncClient, processed_document):
    """Test luồng chat streaming (SSE)"""
    doc_id = str(processed_document.id)
    payload = {
        "document_id": doc_id,
        "message": "Albert Einstein là ai?",
        "mode": "socratic"
    }
    
    # Sử dụng stream context manager của httpx
    async with async_client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        
        events = []
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                events.append(line.replace("event:", "").strip())
        
        # Verify events quan trọng
        assert "meta" in events
        assert "chunk" in events
        assert "done" in events

@pytest.mark.asyncio
async def test_get_chat_history(async_client: AsyncClient, processed_document):
    """Test lấy lịch sử hội thoại"""
    doc_id = str(processed_document.id)
    # 1. Tạo conversation
    conv_resp = await async_client.post(f"/api/v1/chat/conversations/{doc_id}", json={"title": "History Test"})
    conv_id = conv_resp.json()["id"]
    
    # 2. Lấy history
    response = await async_client.get(f"/api/v1/chat/history/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert "messages" in data

@pytest.mark.asyncio
async def test_delete_conversation(async_client: AsyncClient, processed_document):
    """Test xóa cuộc hội thoại"""
    doc_id = str(processed_document.id)
    conv_resp = await async_client.post(f"/api/v1/chat/conversations/{doc_id}")
    conv_id = conv_resp.json()["id"]
    
    response = await async_client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    
    # Kiểm tra 404
    check_resp = await async_client.get(f"/api/v1/chat/history/{conv_id}")
    assert check_resp.status_code == 404
