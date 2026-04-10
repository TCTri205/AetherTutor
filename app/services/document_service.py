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

    async def upload_document(self, file: UploadFile) -> tuple[Document, bool]:
        """
        Xử lý tải lên tài liệu:
        1. Validate (Size, Extension).
        2. Check Hash duplication.
        3. Save file to disk.
        4. Create DB record.
        5. Enqueue background task.
        Returns: (Document object, is_duplicate: bool)
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

        # 2. Check trùng lặp theo Hash
        existing_doc = await self.repo.get_by_hash(content_hash)
        if existing_doc:
            # Nếu đã có file trùng hash, trả về kèm flag is_duplicate = True
            return existing_doc, True

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
            return existing_doc, True

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

            # Trả về đối tượng Document đã cập nhật kèm flag is_duplicate = False
            await self.session.refresh(doc)
            return doc, False

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
        """
        rows = await self.repo.list_with_counts(skip, limit)
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
        """ Xóa tài liệu khỏi hệ thống hoàn toàn. """
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

        # 1. Xóa trong DB (SQL CASCADE sẽ lo phần Graph Entities/Relations)
        await self.repo.delete(doc_id)
        
        # 2. Xóa trong ChromaDB
        try:
            chroma_client.delete_by_document_id(doc_id)
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB data for document {doc_id}: {e}")

        # 3. Xóa file vật lý
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                logger.error(f"Failed to delete file {doc.file_path}: {e}")
        
        await self.session.commit()
        return True
