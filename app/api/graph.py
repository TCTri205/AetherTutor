from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(prefix="/graph", tags=["graph"])

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
