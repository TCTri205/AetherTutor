from fastapi import APIRouter, Body
from typing import Optional

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/socratic")
async def socratic_chat(
    document_id: str,
    message: str = Body(..., embed=True),
    mode: str = "feynman"
):
    """
    Start or continue a Socratic dialogue based on a specific document's knowledge graph.
    """
    return {
        "response": "Explain this naturally as if I'm 5 years old.",
        "context_used": ["entity1", "relation1"]
    }

@router.get("/history/{document_id}")
async def get_chat_history(document_id: str):
    """
    Get the chat history for a specific document.
    """
    return []
