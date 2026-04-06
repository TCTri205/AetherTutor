from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from ..database import get_db
from ..repositories.graph_repo import GraphRepository
from ..core.retriever import Retriever
from ..schemas.lightrag import QueryRequest, QueryResponse

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
        context = await retriever.retrieve(request.query, request.document_id)
        response_text = await retriever.generate(request.query, context)
        
        return QueryResponse(
            query=request.query,
            response=response_text,
            context_used=context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/subgraph")
async def get_document_subgraph(
    document_id: str,
    depth: int = 2
):
    """
    Get the localized knowledge subgraph for a document to be visualized.
    """
    return {
        "nodes": [{"id": "E1", "label": "Concept A"}, {"id": "E2", "label": "Concept B"}],
        "edges": [{"source": "E1", "target": "E2", "label": "explains"}]
    }

@router.get("/{document_id}/stats")
async def get_graph_stats(document_id: str):
    """
    Get statistics about the knowledge graph (number of entities, relations).
    """
    return {
        "entity_count": 42,
        "relation_count": 68
    }
