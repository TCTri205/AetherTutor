import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_document_graph(async_client: AsyncClient, processed_document):
    """Test lấy toàn bộ dữ liệu đồ thị của tài liệu"""
    doc_id = str(processed_document.id)
    response = await async_client.get(f"/api/v1/graph/{doc_id}/view")
    
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 1
    assert data["nodes"][0]["label"] == "Albert Einstein"

@pytest.mark.asyncio
async def test_get_graph_stats(async_client: AsyncClient, processed_document):
    """Test lấy thống kê đồ thị"""
    doc_id = str(processed_document.id)
    response = await async_client.get(f"/api/v1/graph/{doc_id}/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert data["entity_count"] == 1
    assert "relation_count" in data

@pytest.mark.asyncio
async def test_query_graph(async_client: AsyncClient, processed_document):
    """Test truy vấn đồ thị (Query API)"""
    doc_id = str(processed_document.id)
    payload = {
        "query": "Einstein là ai?",
        "document_id": doc_id
    }
    response = await async_client.post("/api/v1/graph/query", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "context_used" in data

@pytest.mark.asyncio
async def test_get_graph_nonexistent_doc(async_client: AsyncClient):
    """Test 404 cho tài liệu không tồn tại"""
    random_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/graph/{random_id}/view")
    assert response.status_code == 404
