import os
import uuid
import hashlib
import aiofiles
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from arq.connections import ArqRedis

from ..config import settings
from ..models.document import Document, DocumentStatus
from ..repositories.document_repo import DocumentRepository
from ..core.exceptions import PermanentProcessingError
from ..services.chroma_client import chroma_client

class DocumentService:
    def __init__(self, session: AsyncSession, arq_pool: ArqRedis):
        self.session = session
        self.arq_pool = arq_pool
        self.repo = DocumentRepository(session)

    def _calculate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def upload_document(self, file: UploadFile) -> Document:
        """
        Xử lý tải lên tài liệu:
        1. Validate (Size, Extension).
        2. Check Hash duplication.
        3. Save file to disk.
        4. Create DB record.
        5. Enqueue background task.
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
            # Nếu đã có file trùng hash, ta có thể trả về thông tin file cũ thay vì báo lỗi
            # Hoặc báo lỗi 409 Conflict tùy theo yêu cầu UI.
            # Ở đây tôi chọn trả về bản ghi cũ với thông tin đã tồn tại.
            return existing_doc

        # 3. Tạo bản ghi Document (PENDING)
        doc = await self.repo.create(file.filename, content_hash)
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
                # Để đơn giản, ta mark status FAILED ngay lập tức.
                await self.repo.update_status(doc_id, DocumentStatus.FAILED, f"Không thể kết nối hàng đợi: {str(e)}")
                await self.session.commit()
                # Có thể cân nhắc xóa file vật lý ở đây nếu muốn sạch sẽ
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

    async def get_document_status(self, doc_id: uuid.UUID) -> Document:
        doc = await self.repo.get_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
        return doc

    async def list_documents(self, skip: int = 0, limit: int = 100):
        return await self.repo.list_all(skip, limit)

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
        except:
            pass

        # 3. Xóa file vật lý
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except:
                pass
        
        await self.session.commit()
        return True
