import pytest
import uuid
import tempfile
import os
import sys
from app.worker.tasks import process_document_task
from app.models.document import DocumentStatus, Document
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform == "win32", reason="asyncpg Proactor event loop incompatibility on Windows")
async def test_worker_process_document_success(test_db: AsyncSession, sample_pdf_bytes: bytes):
    """
    Test worker xử lý tài liệu thành công.
    Dùng Mock LLM (auto-patched via conftest).
    """
    from app.repositories.document_repo import DocumentRepository

    # 1. Tạo document PENDING trong DB
    doc_repo = DocumentRepository(test_db)
    doc = await doc_repo.create("worker_test.pdf", "somehash")
    doc_id = doc.id

    # Giả lập file vật lý tồn tại - sử dụng temp dir cross-platform
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"{doc_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(sample_pdf_bytes)
    
    await doc_repo.update_file_path(doc_id, file_path)
    await test_db.commit()

    # 2. Chạy worker task trực tiếp
    # ctx giả lập arq context
    ctx = {}
    await process_document_task(ctx, str(doc_id))
    
    # 3. Kiểm tra kết quả trong DB
    # Refresh session hoặc query lại
    result = await test_db.execute(select(Document).where(Document.id == doc_id))
    updated_doc = result.scalar_one()
    
    assert updated_doc.status == DocumentStatus.COMPLETED
    assert updated_doc.entity_count > 0
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform == "win32", reason="asyncpg Proactor event loop incompatibility on Windows")
async def test_worker_process_nonexistent_document(test_db: AsyncSession):
    """Test worker xử lý document không tồn tại -> Log error và thoát êm"""
    random_id = str(uuid.uuid4())
    # Không nên raise exception làm treo worker
    await process_document_task({}, random_id)
    # Nếu không crash là đạt
