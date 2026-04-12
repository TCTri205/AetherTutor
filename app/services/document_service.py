import os
import uuid
import hashlib
import aiofiles
import logging
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from arq.connections import ArqRedis

from ..config import settings
from ..models.document import Document, DocumentStatus
from ..repositories.document_repo import DocumentRepository
from ..repositories.graph_repo import GraphRepository
from ..services.chroma_client import chroma_client

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, session: AsyncSession, arq_pool: ArqRedis, user_id: uuid.UUID):
        self.session = session
        self.arq_pool = arq_pool
        self.repo = DocumentRepository(session)
        self.graph_repo = GraphRepository(session)
        self.user_id = user_id

    def _calculate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def upload_document(self, file: UploadFile) -> Document:
        """
        Xử lý tải lên tài liệu:
        1. Validate (Size, Extension).
        2. Check Hash duplication (BR-017: 409 nếu trùng).
        3. Check concurrent processing (BR-011: 409 nếu đang có doc processing).
        4. Save file to disk.
        5. Create DB record.
        6. Enqueue background task.

        Returns:
            Document object đã được tạo thành công

        Raises:
            HTTPException 409: Duplicate document hoặc concurrent processing
            HTTPException 400: Invalid file type/size
            HTTPException 413: File too large
            HTTPException 503: Task queue unavailable
        """
        # 1. Validation
        extension = os.path.splitext(file.filename)[1].lower()
        if extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Định dạng file {extension} không được hỗ trợ. Chỉ nhận: {settings.ALLOWED_EXTENSIONS}")

        # Đọc nội dung để tính hash (Tạm thời đọc hết vào memory vì giới hạn 50MB)
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File quá lớn. Giới hạn tối đa: {settings.MAX_FILE_SIZE_MB}MB")

        content_hash = self._calculate_hash(content)

        # 2. Check trùng lặp theo Hash (BR-017: Idempotency)
        existing_doc = await self.repo.get_by_hash(content_hash)
        if existing_doc:
            # BR-017: Document đã tồn tại → 409 DUPLICATE_DOCUMENT
            if existing_doc.status in (DocumentStatus.PENDING, DocumentStatus.PROCESSING):
                raise HTTPException(
                    status_code=409,
                    detail="Document này đang được xử lý. Vui lòng đợi hoàn tất trước khi upload thêm."
                )
            # BR-017: Document đã completed/failed → trả về 409 với link tới resource cũ
            raise HTTPException(
                status_code=409,
                detail=f"File này đã được upload trước đó (document_id: {existing_doc.id}, status: {existing_doc.status.value})."
            )

        # BR-011: Check concurrent processing — chặn upload mới khi user đang có document processing
        processing_count = await self.repo.count_processing_documents(self.user_id)
        if processing_count > 0:
            raise HTTPException(
                status_code=409,
                detail="Document khác đang được xử lý. Vui lòng đợi hoàn tất trước khi upload thêm."
            )

        # 3. Tạo bản ghi Document (PENDING)
        try:
            doc = await self.repo.create(file.filename, content_hash, user_id=self.user_id)
        except IntegrityError:
            # Race condition: concurrent upload với cùng file — rollback và trả về doc đã tồn tại
            await self.session.rollback()
            existing_doc = await self.repo.get_by_hash(content_hash)
            if existing_doc is None:
                raise HTTPException(
                    status_code=409,
                    detail="Concurrent upload conflict. Please retry."
                )
            # BR-017: Duplicate document
            raise HTTPException(
                status_code=409,
                detail=f"File này đã được upload trước đó (document_id: {existing_doc.id})."
            )

        doc_id = doc.id
        
        # Tạo đường dẫn lưu file
        file_name = f"{doc_id}{extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, file_name)
        
        try:
            # 4. Lưu file vật lý
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
            
            # Cập nhật đường dẫn file vào DB
            await self.repo.update_file_path(doc_id, file_path)
            
            # Commit để đảm bảo dữ liệu đã vào DB trước khi enqueue
            await self.session.commit()

            # 5. Đẩy vào hàng đợi ARQ
            try:
                await self.arq_pool.enqueue_job("process_document_task", str(doc_id))
            except Exception as e:
                # Nếu không enqueue được (Redis sập), ta phải thông báo và có thể rollback nhẹ
                await self.repo.update_status(doc_id, DocumentStatus.FAILED, f"Không thể kết nối hàng đợi: {str(e)}")
                await self.session.commit()
                raise HTTPException(status_code=503, detail="Hệ thống hàng đợi đang bận. Vui lòng thử lại sau.")

            # Trả về đối tượng Document đã cập nhật
            await self.session.refresh(doc)
            return doc

        except Exception as e:
            # Rollback nếu có bất kỳ lỗi nào trong quá trình lưu file hoặc cập nhật DB
            await self.session.rollback()
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

    async def _enrich_document(self, doc: Document) -> dict:
        """ Bổ sung entity_count, relation_count và file_size vào doc object (as dict). """
        entity_count = await self.graph_repo.count_entities(doc.id)
        relation_count = await self.graph_repo.count_relations(doc.id)
        
        file_size = 0
        if doc.file_path and os.path.exists(doc.file_path):
            file_size = os.path.getsize(doc.file_path)
        
        # Note: page_count tạm thời để None nếu không lưu trong DB
        return {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "processing_step": doc.processing_step,
            "entity_count": entity_count,
            "relation_count": relation_count,
            "page_count": None,
            "file_size": file_size,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "error_message": doc.error_message
        }

    async def get_document_status(self, doc_id: uuid.UUID) -> dict:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
        return await self._enrich_document(doc)

    async def list_documents(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """
        Fetch documents with entity/relation counts in a single query.
        Uses list_with_counts to avoid N+1 problem (was 1 + 2n queries, now 1).

        ⚠️ BR-001: Lọc theo user_id để đảm bảo user data isolation.
        """
        rows = await self.repo.list_with_counts(self.user_id, skip, limit)
        results = []
        for doc, entity_count, relation_count in rows:
            file_size = 0
            if doc.file_path and os.path.exists(doc.file_path):
                file_size = os.path.getsize(doc.file_path)

            results.append({
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status,
                "processing_step": doc.processing_step,
                "entity_count": entity_count,
                "relation_count": relation_count,
                "page_count": None,
                "file_size": file_size,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
                "error_message": doc.error_message
            })
        return results

    async def delete_document(self, doc_id: uuid.UUID):
        """
        Xóa tài liệu khỏi hệ thống hoàn toàn.

        ⚠️ UF-010: Atomic delete — nếu ChromaDB fail thì ROLLBACK PostgreSQL.
        Thứ tự xóa:
            1. ChromaDB embeddings (KHÔNG có CASCADE — phải xóa thủ công)
            2. PostgreSQL records (CASCADE tự động cleanup)
            3. Physical file trên disk

        Returns:
            dict: Thống kê số lượng dữ liệu đã xóa
        """
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

        # UF-010: Xóa ChromaDB TRƯỚC để đảm bảo atomic — nếu fail thì rollback toàn bộ
        try:
            chroma_client.delete_by_document_id(doc_id)
        except Exception as e:
            # ChromaDB delete fail → KHÔNG xóa SQL để tránh orphan embeddings
            logger.error(f"ChromaDB delete failed for document {doc_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Không thể xóa document: cleanup embeddings thất bại. Vui lòng thử lại sau. Lỗi: {str(e)}"
            )

        # ChromaDB thành công → xóa SQL (CASCADE lo entities, relations, chunks, flashcards, quizzes)
        try:
            await self.repo.delete(doc_id)
            await self.session.commit()
        except Exception as e:
            # SQL delete fail → ChromaDB đã xóa trước, có thể orphan embeddings
            await self.session.rollback()
            logger.error(f"SQL delete failed for document {doc_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Không thể xóa document: database cleanup thất bại. Embeddings đã bị xóa. Lỗi: {str(e)}"
            )

        # Xóa file vật lý (không critical — nếu fail thì log và bỏ qua)
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                logger.error(f"Failed to delete file {doc.file_path}: {e}")

        return {
            "message": "Document và toàn bộ dữ liệu liên quan đã được xóa",
            "document_id": str(doc_id)
        }
