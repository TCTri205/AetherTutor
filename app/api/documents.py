from fastapi import APIRouter, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from ..database import get_db
from ..schemas.lightrag import (
    DocumentDetail,
)
from ..services.document_service import DocumentService
from ..constants import RATE_LIMIT_DOCUMENT_UPLOAD, RATE_LIMIT_DOCUMENT_DELETE
from .limiter import limiter
from .dependencies import get_current_user_id

router = APIRouter(prefix="/documents", tags=["documents"])


def get_doc_service(db: AsyncSession = Depends(get_db), request: Request = None, user_id: uuid.UUID = Depends(get_current_user_id)) -> DocumentService:
    arq_pool = request.app.state.arq_pool if request else None
    return DocumentService(db, arq_pool, user_id=user_id)


@router.post("/upload")
@limiter.limit(RATE_LIMIT_DOCUMENT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_doc_service)
):
    """
    Tải lên file PDF và bắt đầu luồng xử lý tự động (Async).
    Trả về 202 Accepted cho file mới.
    Trả về 409 Conflict nếu file đã tồn tại (BR-017).
    """
    doc = await service.upload_document(file)

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
    """Liệt kê danh sách tài liệu và trạng thái xử lý."""
    docs_data = await service.list_documents(skip, limit)
    return [DocumentDetail(**d) for d in docs_data]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document_status(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_doc_service)
):
    """Lấy thông tin chi tiết và trạng thái của một tài liệu cụ thể."""
    doc_data = await service.get_document_status(document_id)
    return DocumentDetail(**doc_data)


@router.delete("/{document_id}")
@limiter.limit(RATE_LIMIT_DOCUMENT_DELETE)
async def delete_document(
    request: Request,
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_doc_service)
):
    """
    Xóa tài liệu và toàn bộ dữ liệu đồ thị liên quan (SQL + Chroma + File).

    ⚠️ UF-010: Atomic delete — nếu ChromaDB fail thì rollback.
    """
    result = await service.delete_document(document_id)
    return result
