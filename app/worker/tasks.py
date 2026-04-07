import asyncio
import uuid
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_factory
from ..models.document import DocumentStatus, ProcessingStep
from ..repositories.document_repo import DocumentRepository
from ..repositories.chunk_repo import ChunkRepository
from ..repositories.graph_repo import GraphRepository
from ..services.chroma_client import chroma_client
from ..services.pdf_extractor import pdf_extractor
from ..services.llm_service import llm_service
from ..core.entity_extractor import EntityExtractor
from ..core.retriever import Retriever
from ..core.pipeline import LightRAGPipeline
from ..core.exceptions import PermanentProcessingError
from .queue import redis_settings
from ..constants import WORKER_JOB_TIMEOUT_SECONDS, WORKER_MAX_RETRIES

logger = logging.getLogger(__name__)

async def process_document_task(ctx: Any, doc_id_str: str):
    """
    Background Task xử lý tài liệu:
    1. Dọn dẹp dữ liệu cũ (Idempotency).
    2. Trích xuất Text từ PDF.
    3. Chạy Pipeline xử lý ngôn ngữ.
    """
    doc_id = uuid.UUID(doc_id_str)
    
    async with async_session_factory() as session:
        # Khởi tạo các repository
        doc_repo = DocumentRepository(session)
        chunk_repo = ChunkRepository(session)
        graph_repo = GraphRepository(session)

        # Khởi tạo pipeline components
        extractor = EntityExtractor()
        retriever = Retriever(graph_repo)
        pipeline = LightRAGPipeline(doc_repo, chunk_repo, graph_repo, extractor, retriever)
        
        # Lấy thông tin tài liệu
        doc = await doc_repo.get_by_id(doc_id)
        if not doc:
            logger.error(f"Không tìm thấy tài liệu {doc_id} trong database.")
            return

        try:
            # Bước 0: Idempotency Sweep - Xóa sạch dấu vết cũ nếu đây là chạy lại
            logger.info(f"Đang dọn dẹp dữ liệu cũ cho tài liệu: {doc.filename} ({doc_id})")
            await graph_repo.delete_by_document_id(doc_id)
            await chunk_repo.delete_by_document_id(doc_id)
            chroma_client.delete_by_document_id(doc_id)
            await session.commit()

            # Bước 1: Extract PDF
            if not doc.file_path:
                raise PermanentProcessingError("Tài liệu không có đường dẫn file vật lý.")
            
            await doc_repo.update_processing_step(doc_id, ProcessingStep.EXTRACTING)
            logger.info(f"Đang trích xuất văn bản từ PDF: {doc.file_path}")
            text = pdf_extractor.extract_text(doc.file_path)
            
            if not text:
                raise PermanentProcessingError("Không thể trích xuất văn bản có nghĩa từ file PDF.")

            # Bước 2: Ingest vào Pipeline
            logger.info(f"Đang bắt đầu Ingestion Pipeline cho {doc.filename}")
            await pipeline.ingest_text(doc_id, text)
            
            # Commit session cuối cùng
            await session.commit()
            logger.info(f"Hoàn tất xử lý tài liệu: {doc.filename}")

        except PermanentProcessingError as e:
            # Lỗi không thể cứu vãn -> Mark FAILED và dừng lại
            logger.error(f"Lỗi xử lý vĩnh viễn cho {doc_id}: {e.message}")
            await doc_repo.update_status(doc_id, DocumentStatus.FAILED, e.message)
            await session.commit()
            return
            
        except Exception as e:
            # Lỗi tạm thời (Network, LLM Timeout...) -> Mark FAILED và để ARQ Retry
            logger.exception(f"Lỗi hệ thống khi xử lý tài liệu {doc_id}: {str(e)}")
            await doc_repo.update_status(doc_id, DocumentStatus.FAILED, f"Lỗi hệ thống: {str(e)}")
            await session.commit()
            raise e

# Cấu hình ARQ Worker
class WorkerSettings:
    functions = [process_document_task]
    redis_settings = redis_settings
    job_timeout = WORKER_JOB_TIMEOUT_SECONDS
    max_retries = WORKER_MAX_RETRIES
