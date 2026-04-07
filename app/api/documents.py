from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from ..database import get_db
from ..repositories.document_repo import DocumentRepository
from ..repositories.chunk_repo import ChunkRepository
from ..repositories.graph_repo import GraphRepository
from ..core.pipeline import LightRAGPipeline
from ..core.entity_extractor import EntityExtractor
from ..core.retriever import Retriever
from ..schemas.lightrag import (
    DocumentIngestRequest, 
    DocumentUploadResponse, 
    DocumentDetail,
    ExtractionResult
)
from ..services.document_service import DocumentService
from ..services.llm_service import llm_service

router = APIRouter(prefix="/documents", tags=["documents"])

def get_doc_service(db: AsyncSession = Depends(get_db), request: Request = None) -> DocumentService:
    arq_pool = request.app.state.arq_pool if request else None
    return DocumentService(db, arq_pool)

@router.post("/test-ingest")
async def test_ingest(request: DocumentIngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingest text content directly (Synchronous) for testing/debug.
    Bypasses the background worker.
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
        # 1. Tạo document record
        import hashlib
        content_hash = hashlib.sha256(request.content.encode()).hexdigest()
        doc = await doc_repo.create(request.filename, content_hash)
        
        # 2. Chạy pipeline đồng bộ
        await pipeline.ingest_text(doc.id, request.content)
        await db.commit()
        
        return {"document_id": str(doc.id), "status": "COMPLETED"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import JSONResponse

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...), 
    service: DocumentService = Depends(get_doc_service)
):
    """
    Tải lên file PDF và bắt đầu luồng xử lý tự động (Async).
    Trả về 202 Accepted cho file mới, 200 OK cho file đã tồn tại.
    """
    doc, is_duplicate = await service.upload_document(file)
    
    if is_duplicate:
        # File đã tồn tại — trả về 200 OK, frontend KHÔNG cần polling
        return JSONResponse(
            status_code=200,
            content={
                "document_id": str(doc.id),
                "filename": doc.filename,
                "status": doc.status,
                "message": "Tài liệu này đã tồn tại trong hệ thống."
            }
        )
    else:
        # File mới — trả về 202 Accepted, frontend CẦN polling
        return JSONResponse(
            status_code=202,
            content={
                "document_id": str(doc.id),
                "filename": doc.filename,
                "status": doc.status,
                "message": "Yêu cầu đã được tiếp nhận và đang được xử lý trong hàng đợi."
            }
        )

@router.get("/", response_model=List[DocumentDetail])
async def list_documents(
    skip: int = 0, 
    limit: int = 100, 
    service: DocumentService = Depends(get_doc_service)
):
    """
    Liệt kê danh sách tài liệu và trạng thái xử lý.
    """
    docs_data = await service.list_documents(skip, limit)
    return [DocumentDetail(**d) for d in docs_data]

@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document_status(
    document_id: uuid.UUID, 
    service: DocumentService = Depends(get_doc_service)
):
    """
    Lấy thông tin chi tiết và trạng thái của một tài liệu cụ thể.
    """
    doc_data = await service.get_document_status(document_id)
    return DocumentDetail(**doc_data)

@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID, 
    service: DocumentService = Depends(get_doc_service)
):
    """
    Xóa tài liệu và toàn bộ dữ liệu đồ thị liên quan (SQL + Chroma + File).
    """
    await service.delete_document(document_id)
    return {"message": f"Tài liệu {document_id} đã được xóa hoàn toàn khỏi hệ thống."}
