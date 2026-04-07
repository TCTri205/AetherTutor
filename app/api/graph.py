from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from ..database import get_db
from ..repositories.graph_repo import GraphRepository
from ..core.retriever import Retriever
from ..services.llm_service import llm_service
from ..schemas.lightrag import (
    QueryRequest,
    QueryResponse,
    GraphNodeView,
    GraphEdgeView
)
import uuid

router = APIRouter(prefix="/graph", tags=["graph"])

@router.post("/query", response_model=QueryResponse)
async def query_graph(request: QueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Query the knowledge graph for a specific document or global context.
    """
    if not request.document_id:
        raise HTTPException(status_code=400, detail="Document ID is required for now.")

    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)

    try:
        context, _ = await retriever.retrieve(request.query, request.document_id)
        response_text = await retriever.generate(request.query, context)

        return QueryResponse(
            query=request.query,
            response=response_text,
            context_used=context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/view", response_model=Dict[str, List[Any]])
async def get_document_graph(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy toàn bộ dữ liệu đồ thị của một tài liệu để hiển thị lên UI (Visualization).
    Trả về danh sách nodes và edges.
    """
    repo = GraphRepository(db)
    entities = await repo.get_all_entities(document_id)
    relations = await repo.get_all_relations(document_id)

    nodes = [
        GraphNodeView(
            id=e.canonical_name,
            label=e.canonical_name,
            type=e.entity_type,
            description=e.description
        ) for e in entities
    ]

    edges = [
        GraphEdgeView(
            id=str(r.id),
            source=r.source_entity,
            target=r.target_entity,
            label=r.relation_type,
            description=r.description
        ) for r in relations
    ]

    return {
        "nodes": nodes,
        "edges": edges
    }

@router.get("/{document_id}/stats")
async def get_graph_stats(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy thống kê về số lượng thực thể và quan hệ đã trích xuất được từ tài liệu.
    """
    repo = GraphRepository(db)
    e_count = await repo.count_entities(document_id)
    r_count = await repo.count_relations(document_id)

    return {
        "entity_count": e_count,
        "relation_count": r_count
    }
