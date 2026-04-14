import uuid
import logging
import asyncio
from pathlib import Path
from typing import Any
from sqlalchemy import select, func
from arq.cron import CronJob

from ..database import async_session_factory
from ..models.document import DocumentStatus, ProcessingStep, Document
from ..models.user import User
from ..models.transcript import Transcript
from ..repositories.document_repo import DocumentRepository
from ..repositories.chunk_repo import ChunkRepository
from ..repositories.graph_repo import GraphRepository
from ..repositories.flashcard_repo import FlashcardRepository
from ..repositories.study_session_repo import StudySessionRepository
from ..repositories.quiz_repo import QuizResultRepository
from ..services.chroma_client import chroma_client
from ..services.pdf_extractor import pdf_extractor
from ..services.code_parser import code_parser, CodeParserError, CODE_EXTENSIONS
from ..services.llm_service import llm_service
from ..services.notification_service import get_notification_service
from ..services.transcription_service import transcription_service
from ..config import settings
from ..core.entity_extractor import EntityExtractor

from ..core.retriever import Retriever
from ..core.pipeline import LightRAGPipeline
from ..core.exceptions import PermanentProcessingError
from .queue import redis_settings, get_redis_pool
from ..constants import WORKER_JOB_TIMEOUT_SECONDS, WORKER_MAX_RETRIES, REDIS_DISTRIBUTED_LOCK_TTL, QUIZ_FEEDBACK_FLAG_THRESHOLD

logger = logging.getLogger(__name__)

# =============================================
# P2-1: Cleanup helper function (refactored from inline code)
# =============================================

async def cleanup_partial_document_data(
    doc_id: uuid.UUID,
    graph_repo,
    chunk_repo,
    session,
    user_id: uuid.UUID | None = None,
) -> None:
    """
    P2-1: Xóa sạch dấu vết của document trong PostgreSQL và ChromaDB.
    Dùng cho idempotency sweep trước khi xử lý lại document.

    Args:
        doc_id: Document UUID
        graph_repo: GraphRepository instance
        chunk_repo: ChunkRepository instance
        session: AsyncSession để commit
        user_id: User UUID cho RLS context (optional)

    Raises:
        Exception: Nếu ChromaDB cleanup fail (để caller có thể handle)
    """
    from app.database import set_current_user_id

    logger.info(f"Running idempotency sweep for document {doc_id}")

    # Set RLS context if user_id is provided
    if user_id:
        await set_current_user_id(session, str(user_id))

    # Bước 1: Xóa graph và chunks trong PostgreSQL
    await graph_repo.delete_by_document_id(doc_id)
    await chunk_repo.delete_by_document_id(doc_id)

    # Bước 2: Xóa embeddings trong ChromaDB
    # Nếu fail, raise exception để caller biết (không silent như trước)
    try:
        await asyncio.to_thread(chroma_client.delete_by_document_id, doc_id)
    except Exception as e:
        logger.error(f"ChromaDB cleanup failed for document {doc_id}: {e}")
        # Rollback session on ChromaDB failure to avoid half-committed state
        await session.rollback()
        raise

    # Bước 3: Commit PostgreSQL changes
    await session.commit()

    logger.info(f"Idempotency sweep completed for document {doc_id}")


# =============================================
# Cron Dispatcher Task
# =============================================

async def cleanup_expired_sessions_task(ctx: Any):
    """
    Cron job: Dọn dẹp user sessions đã hết hạn và bị revoke > 30 ngày.
    Chạy hàng ngày lúc 2 AM.
    """
    from ..repositories.session import UserSessionRepository

    logger.info("Session cleanup: Starting")
    try:
        async with async_session_factory() as session:
            session_repo = UserSessionRepository(session)
            deleted = await session_repo.cleanup_expired_sessions(older_than_days=30)
            await session.commit()
        logger.info(f"Session cleanup: Deleted {deleted} expired sessions")
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")


async def sm2_dispatcher_task(ctx: Any):
    """
    Cron job: Chạy hàng ngày theo SM2_DAILY_DIGEST_CRON.
    Quét tất cả users có flashcard đến hạn và enqueue sm2_daily_digest_task cho từng user.
    """
    logger.info("SM2 dispatcher: Starting daily digest dispatch")

    async with async_session_factory() as session:
        # Query tất cả users có due flashcards
        from ..models.flashcard import Flashcard

        result = await session.execute(
            select(Flashcard.user_id)
            .where(Flashcard.sm2_next_review <= func.now())
            .distinct()
        )
        user_ids = [row[0] for row in result.all()]
    
    if not user_ids:
        logger.info("SM2 dispatcher: No users with due cards, skipping")
        return
    
    logger.info(f"SM2 dispatcher: Found {len(user_ids)} users with due cards")
    
    # Enqueue digest task cho mỗi user
    redis_pool = await get_redis_pool()
    
    enqueued = 0
    for uid in user_ids:
        try:
            await redis_pool.enqueue_job(
                "sm2_daily_digest_task",
                str(uid),
                _job_id=f"sm2_digest:{uid}:{ctx['job_try']}",
            )
            enqueued += 1
        except Exception as e:
            logger.warning(f"SM2 dispatcher: Failed to enqueue for user {uid}: {e}")
    
    logger.info(f"SM2 dispatcher: Enqueued {enqueued}/{len(user_ids)} digest tasks")


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

        # Lấy thông tin tài liệu
        doc = await doc_repo.get_by_id(doc_id)
        if not doc:
            logger.error(f"Không tìm thấy tài liệu {doc_id} trong database.")
            raise PermanentProcessingError(f"Tài liệu {doc_id} không tồn tại trong database.")

        # Khởi tạo pipeline components (truyền user_id để ChromaDB metadata có user isolation)
        extractor = EntityExtractor(config=settings)

        retriever = Retriever(graph_repo)
        pipeline = LightRAGPipeline(doc_repo, chunk_repo, graph_repo, extractor, retriever, user_id=doc.user_id)

        try:
            # Bước 0: Idempotency Sweep - Dùng helper function (P2-1 refactored)
            await cleanup_partial_document_data(doc_id, graph_repo, chunk_repo, session, user_id=doc.user_id)

            # Bước 1: Extract text from file
            if not doc.file_path:
                raise PermanentProcessingError("Tài liệu không có đường dẫn file vật lý.")

            await doc_repo.update_processing_step(doc_id, ProcessingStep.EXTRACTING)
            
            # Detect file type and route to appropriate parser
            file_ext = Path(doc.file_path).suffix.lower()
            
            if file_ext in CODE_EXTENSIONS:
                # Code file: use CodeParser
                logger.info(f"Đang phân tích mã nguồn: {doc.file_path}")
                try:
                    extraction_result = code_parser.parse_file(Path(doc.file_path))
                    text = code_parser.get_code_snippet(Path(doc.file_path))
                    
                    # Store code snippet in metadata for graph entities
                    logger.info(f"Extracted {len(extraction_result.entities)} entities, {len(extraction_result.relations)} relations from code")
                except CodeParserError as e:
                    raise PermanentProcessingError(f"Lỗi phân tích mã nguồn: {str(e)}")
            else:
                # Document file: use PDF extractor
                logger.info(f"Đang trích xuất văn bản từ PDF: {doc.file_path}")
                text = await asyncio.to_thread(pdf_extractor.extract_text, doc.file_path)
                
                if not text:
                    raise PermanentProcessingError("Không thể trích xuất văn bản có nghĩa từ file PDF.")
                
                logger.info(f"Extracted {len(text)} characters ({len(text)//1000}KB) from document")

            # Bước 2: Ingest vào Pipeline
            logger.info(f"Đang bắt đầu Ingestion Pipeline cho {doc.filename}")
            
            if file_ext in CODE_EXTENSIONS and 'extraction_result' in locals():
                # For code files: directly use extracted entities/relations
                await pipeline.ingest_code_entities(
                    doc_id, 
                    extraction_result.entities, 
                    extraction_result.relations,
                    code_snippet=text
                )
            else:
                # For documents: use text ingestion
                await pipeline.ingest_text(doc_id, text)
            
            # Commit session cuối cùng
            await session.commit()
            logger.info(f"Hoàn tất xử lý tài liệu: {doc.filename}")

        except PermanentProcessingError as e:
            # Lỗi không thể cứu vãn -> Mark FAILED và dừng lại
            logger.error(f"Lỗi xử lý vĩnh viễn cho {doc_id}: {e.message}")
            await session.rollback()
            await doc_repo.update_status(doc_id, DocumentStatus.FAILED, e.message)
            await session.commit()
            return
            
        except Exception as e:
            # Lỗi tạm thời (Network, LLM Timeout...) -> Mark FAILED và để ARQ Retry
            logger.exception(f"Lỗi hệ thống khi xử lý tài liệu {doc_id}: {str(e)}")
            await session.rollback()
            try:
                await doc_repo.update_status(doc_id, DocumentStatus.FAILED, f"Lỗi hệ thống: {str(e)}")
                await session.commit()
            except Exception as update_err:
                logger.error(f"Không thể cập nhật trạng thái lỗi trong task: {update_err}")
            raise e

async def sm2_daily_digest_task(ctx: Any, user_id_str: str):
    """
    ARQ Job: Gửi daily digest notification cho flashcard review.
    Chạy hàng ngày lúc 8h (theo SM2_DAILY_DIGEST_CRON).

    Sử dụng Redis distributed lock để đảm bảo mỗi user chỉ có 1 job chạy tại 1 thời điểm.
    """
    user_id = uuid.UUID(user_id_str)
    redis_client = await get_redis_pool()

    # Redis distributed lock
    lock_key = f"lock:sm2_digest:{user_id}"
    lock = redis_client.lock(lock_key, timeout=REDIS_DISTRIBUTED_LOCK_TTL)

    lock_acquired = False
    try:
        lock_acquired = await lock.acquire(blocking=False)
        if not lock_acquired:
            logger.info(f"Digest job already running for user {user_id}, skipping")
            return

        async with async_session_factory() as session:
            # Set RLS context for background task
            from app.database import set_current_user_id
            await set_current_user_id(session, user_id_str)

            flashcard_repo = FlashcardRepository(session)
            session_repo = StudySessionRepository(session)

            # Lấy thống kê
            due_count = await flashcard_repo.get_due_cards_count(user_id)
            stats = await session_repo.get_stats(user_id, days=7)

            if due_count == 0:
                logger.info(f"No due cards for user {user_id}, skipping notification")
                return

            # Gửi notification
            notification_service = get_notification_service(redis_client)

            # Lấy user email từ DB
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            user_email = user.email if user else None

            await notification_service.send_flashcard_digest(
                user_id=user_id,
                user_email=user_email,
                due_cards_count=due_count,
                streak_days=stats.get("streak_days", 0)
            )

            logger.info(f"Daily digest sent to user {user_id}: {due_count} cards due")

    finally:
        if lock_acquired:
            await lock.release()


async def quiz_feedback_analysis_task(ctx: Any, result_id_str: str):
    """
    ARQ Job: Analyze quiz feedback and flag low-quality quizzes.

    Chạy khi user submit quality rating <= QUIZ_FEEDBACK_FLAG_THRESHOLD.
    Phân loại feedback bằng LLM và flag để admin review.
    """
    result_id = uuid.UUID(result_id_str)

    async with async_session_factory() as session:
        result_repo = QuizResultRepository(session)
        result = await result_repo.get_by_id_with_answers(result_id)

        if not result:
            logger.error(f"Quiz result {result_id} not found")
            return

        # Check if quality rating is low
        if result.quality_rating is None or result.quality_rating > QUIZ_FEEDBACK_FLAG_THRESHOLD:
            logger.info(f"Quiz result {result_id} has acceptable rating ({result.quality_rating})")
            return

        # Analyze feedback using LLM
        if result.quality_feedback:
            from pydantic import BaseModel

            class FeedbackClassification(BaseModel):
                category: str  # factual_error, poor_distractor, too_easy, too_hard, other
                severity: str  # low, medium, high
                suggestion: str

            prompt = f"""Phân loại feedback sau về chất lượng quiz:

Feedback: "{result.quality_feedback}"
Rating: {result.quality_rating}/5

Phân loại vào một trong các category:
- factual_error: Sai kiến thức, thông tin không chính xác
- poor_distractor: Đáp án nhiễu kém hợp lý
- too_easy: Câu hỏi quá dễ
- too_hard: Câu hỏi quá khó
- other: Lý do khác

Trả về JSON:
{{
  "category": "category_name",
  "severity": "low|medium|high",
  "suggestion": "Gợi ý cải thiện"
}}
"""

            try:
                classification = await llm_service.structured_extraction(
                    prompt=prompt,
                    response_model=FeedbackClassification,
                    max_retries=2,
                )

                if classification:
                    # Persist classification to database
                    await result_repo.update_feedback_analysis(
                        result_id,
                        feedback_category=classification.category,
                        feedback_severity=classification.severity,
                        feedback_suggestion=classification.suggestion,
                    )
                    await session.commit()

                    logger.warning(
                        f"Quiz {result_id} flagged: "
                        f"category={classification.category}, "
                        f"severity={classification.severity}"
                    )
                    return

            except Exception as e:
                logger.error(f"Failed to classify feedback for {result_id}: {e}")

        # Fallback: log warning
        logger.warning(
            f"Quiz result {result_id} has low rating ({result.quality_rating}/5). "
            f"Feedback: {result.quality_feedback or 'None'}"
        )


async def import_obsidian_vault_task(ctx: Any, vault_path: str, user_id_str: str, job_id: str):
    """
    ARQ Job: Import Obsidian vault entries into the Knowledge Graph.
    """
    user_id = uuid.UUID(user_id_str)
    
    async with async_session_factory() as session:
        from ..services.obsidian_vault_importer import ObsidianVaultImporter
        
        importer = ObsidianVaultImporter(session)
        logger.info(f"Starting Obsidian vault import for user {user_id} from {vault_path}")
        
        # Redis pools for progress tracking
        redis_pool = await get_redis_pool()
        progress_key = f"import:{job_id}:progress"
        
        try:
            # We don't have built-in progress in ObsidianVaultImporter yet, 
            # so we just mark as started and then finished.
            await redis_pool.setex(progress_key, 3600, "processing")
            
            result = await importer.import_vault(vault_path, user_id, import_id=job_id)
            
            # Save results/completion status
            import json
            await redis_pool.setex(progress_key, 3600, json.dumps({
                "status": "completed",
                "result": result
            }))
            
            logger.info(f"Finished Obsidian vault import for user {user_id}: {result}")
            
        except Exception as e:
            logger.exception(f"Failed to import Obsidian vault for user {user_id}: {e}")
            await redis_pool.setex(progress_key, 3600, json.dumps({
                "status": "failed",
                "error": str(e)
            }))
            raise e


async def transcribe_media_task(ctx: Any, document_id_str: str, user_id_str: str, language: str = "en"):
    """
    ARQ Job: Transcribe media document (audio/video) using Whisper.

    Args:
        document_id_str: UUID của document cần transcribe
        user_id_str: UUID của user (cho RLS context)
        language: Ngôn ngữ target (e.g., 'en', 'vi')
    """
    document_id = uuid.UUID(document_id_str)
    user_id = uuid.UUID(user_id_str)

    async with async_session_factory() as session:
        # Set RLS context
        from app.database import set_current_user_id
        await set_current_user_id(session, user_id_str)

        # Get transcript record
        from sqlalchemy import select
        stmt = select(Transcript).where(
            Transcript.document_id == document_id,
            Transcript.user_id == user_id,
        )
        result = await session.execute(stmt)
        transcript = result.scalars().first()

        if not transcript:
            logger.error(f"Transcript not found for document {document_id}")
            return

        # Update status to processing
        transcript.status = "processing"
        await session.commit()

        try:
            # Get file path from document
            doc_stmt = select(Document).where(Document.id == document_id)
            doc_result = await session.execute(doc_stmt)
            doc = doc_result.scalars().first()

            if not doc or not doc.file_path:
                raise PermanentProcessingError("Document không có file_path")

            file_path = Path(doc.file_path)

            # Transcribe
            transcription_result = await transcription_service.transcribe(
                file_path=file_path,
                language=language,
            )

            if not transcription_result:
                raise PermanentProcessingError("Transcription failed - no result")

            # Update transcript
            transcript.full_text = transcription_result.full_text
            transcript.language = transcription_result.language
            transcript.duration = transcription_result.duration
            transcript.segments = [
                {"text": seg.text, "start": seg.start, "end": seg.end}
                for seg in transcription_result.segments
            ]
            transcript.status = "completed"
            transcript.error_message = None
            await session.commit()

            logger.info(f"Transcription completed for document {document_id}")

        except PermanentProcessingError as e:
            logger.error(f"Permanent transcription error: {e.message}")
            transcript.status = "failed"
            transcript.error_message = e.message
            await session.commit()

        except Exception as e:
            logger.exception(f"Transcription failed for document {document_id}: {e}")
            transcript.status = "failed"
            transcript.error_message = str(e)
            await session.commit()
            raise e


# Cấu hình ARQ Worker

class WorkerSettings:
    functions = [
        cleanup_expired_sessions_task,
        process_document_task,
        sm2_daily_digest_task,
        quiz_feedback_analysis_task,
        import_obsidian_vault_task,
        transcribe_media_task,
    ]
    cron_jobs = [
        CronJob(
            "session_cleanup",  # name
            cleanup_expired_sessions_task,  # coroutine
            hour={2},  # 2 AM
            minute={0},
            second={0},
            microsecond=0,
            month=None,
            day=None,
            weekday=None,
            run_at_startup=False,
            unique=True,
            job_id=None,
            timeout_s=None,
            keep_result_s=None,
            keep_result_forever=None,
            max_tries=1,
        ),
        CronJob(
            "sm2_daily_digest",  # name
            sm2_dispatcher_task,  # coroutine
            hour={8},  # 8 AM
            minute={0},
            second={0},
            microsecond=0,
            month=None,
            day=None,
            weekday=None,
            run_at_startup=False,
            unique=True,
            job_id=None,
            timeout_s=None,
            keep_result_s=None,
            keep_result_forever=None,
            max_tries=1,
        ),
    ]
    redis_settings = redis_settings
    job_timeout = WORKER_JOB_TIMEOUT_SECONDS
    max_retries = WORKER_MAX_RETRIES

