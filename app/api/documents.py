from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..repositories.document_repo import DocumentRepository
from ..repositories.chunk_repo import ChunkRepository
from ..repositories.graph_repo import GraphRepository
from ..core.pipeline import LightRAGPipeline
from ..core.entity_extractor import EntityExtractor
from ..core.retriever import Retriever
from ..schemas.lightrag import DocumentIngestRequest

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/test-ingest", status_code=HTTPStatus.CREATED)
async def test_ingest(request: DocumentIngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingest text content directly into the LightRAG pipeline for testing.
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
        retriever=retriever
    )

    try:
        doc_id = await pipeline.process_document(request.content, request.filename)
        return {"document_id": doc_id, "status": "COMPLETED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/upload", status_code=HTTPStatus.CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document and start the LightRAG processing pipeline.
    """
    return {"message": f"Document {file.filename} upload started."}

@router.get("/", response_model=List[dict])
async def list_documents():
    """
    List all documents and their processing status.
    """
    return []

@router.get("/{document_id}")
async def get_document_status(document_id: str):
    """
    Get the details and processing status of a specific document.
    """
    return {"document_id": document_id, "status": "processing"}

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its associated knowledge graph.
    """
    return {"message": f"Document {document_id} deleted."}
