"""
Debug API endpoints - Only available in development/debug mode.

These endpoints bypass normal workflow for testing and debugging.
NEVER include in production.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import hashlib

from ..database import get_db
from ..repositories.document_repo import DocumentRepository
from ..repositories.chunk_repo import ChunkRepository
from ..repositories.graph_repo import GraphRepository
from ..core.pipeline import LightRAGPipeline
from ..core.entity_extractor import EntityExtractor
from ..core.retriever import Retriever
from ..schemas.lightrag import DocumentIngestRequest
from ..api.dependencies import get_current_user_id

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("/test-ingest")
async def test_ingest(
    request: DocumentIngestRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Ingest text content directly (Synchronous) for testing/debug.
    Bypasses the background worker.

    SECURITY: Chỉ hoạt động trong chế độ DEBUG hoặc development.
    """
    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)
    graph_repo = GraphRepository(db)
    extractor = EntityExtractor()
    retriever = Retriever(graph_repo)

    pipeline = LightRAGPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        graph_repo=graph_repo,
        extractor=extractor,
        retriever=retriever,
        user_id=user_id,
    )

    try:
        content_hash = hashlib.sha256(request.content.encode()).hexdigest()
        doc = await doc_repo.create(request.filename, content_hash, user_id=user_id)

        await pipeline.ingest_text(doc.id, request.content)
        await db.commit()

        return {"document_id": str(doc.id), "status": "COMPLETED"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
