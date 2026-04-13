"""
Media API Router - Sprint 17: Media Microlearning

Endpoints:
- POST /api/v1/media/upload - Register media document (video/audio)
- GET /api/v1/media/{document_id}/transcript - Get transcript
- POST /api/v1/media/{document_id}/transcript - Request transcription
- PUT /api/v1/media/{document_id}/transcript - Update transcript (manual correction)
- GET /api/v1/media/{document_id}/transcript/status - Check transcription status
- DELETE /api/v1/media/{document_id}/transcript - Delete transcript
"""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from arq import ArqRedis

from ..database import get_db
from ..models.document import Document, MediaType
from ..models.transcript import Transcript
from ..schemas.media import (
    MediaUploadRequest,
    MediaUploadResponse,
    TranscriptCreate,
    TranscriptUpdate,
    TranscriptInfo,
    TranscriptStatus,
    MessageResponse,
)
from .dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["media"])


def _get_arq_pool(request: Request) -> ArqRedis | None:
    """Get ARQ pool from app state."""
    return getattr(request.app.state, "arq_pool", None)


# --- Media Upload ---


@router.post("/upload", response_model=MediaUploadResponse, summary="Register media document")
async def upload_media(
    payload: MediaUploadRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Register a media document (video/audio) with optional auto-transcription.

    - **source_url**: YouTube/Vimeo URL hoặc direct link (optional cho local files)
    - **media_type**: video hoặc audio
    - **title**: Tiêu đề media
    - **auto_transcribe**: Tự động tạo transcription request
    """
    # Validate media_type
    if payload.media_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="media_type phải là 'video' hoặc 'audio'")

    # Create document record
    media_type_enum = MediaType.VIDEO if payload.media_type == "video" else MediaType.AUDIO
    filename = f"{payload.title}.mp4" if payload.media_type == "video" else f"{payload.title}.mp3"

    new_doc = Document(
        user_id=user_id,
        filename=filename,
        content_hash="",  # TODO: Generate from file or URL
        status="PENDING",
        media_type=media_type_enum,
        source_url=payload.source_url,
    )
    db.add(new_doc)
    await db.flush()

    # Auto-transcribe if requested
    transcript_status = None
    if payload.auto_transcribe:
        transcript = Transcript(
            user_id=user_id,
            document_id=new_doc.id,
            full_text="",
            language="en",
            duration=0.0,
            segments=[],
            status="pending",
        )
        db.add(transcript)
        transcript_status = "pending"
        # Transcription job will be queued via separate API call

    await db.commit()
    await db.refresh(new_doc)

    return MediaUploadResponse(
        document_id=new_doc.id,
        filename=new_doc.filename,
        media_type=payload.media_type,
        source_url=payload.source_url,
        status=new_doc.status.value if hasattr(new_doc.status, "value") else new_doc.status,
        transcript_status=transcript_status,
    )


# --- Transcript Endpoints ---


@router.get(
    "/{document_id}/transcript",
    response_model=TranscriptInfo,
    summary="Get transcript",
)
async def get_transcript(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Lấy transcript cho document."""
    # Verify ownership
    stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document không tồn hoặc bạn không có quyền")

    if doc.media_type not in (MediaType.VIDEO, MediaType.AUDIO):
        raise HTTPException(status_code=400, detail="Document này không phải media")

    # Get transcript
    transcript_stmt = select(Transcript).where(
        Transcript.document_id == document_id,
        Transcript.user_id == user_id,
    )
    transcript_result = await db.execute(transcript_stmt)
    transcript = transcript_result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript chưa tồn tại")

    return transcript


@router.post(
    "/{document_id}/transcript",
    response_model=MessageResponse,
    summary="Request transcription",
)
async def request_transcription(
    document_id: uuid.UUID,
    payload: TranscriptCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    request: Request = None,
):
    """
    Yêu cầu transcribe media document.

    - Kiểm tra ownership document
    - Tạo transcript record với status='pending'
    - Queue job vào ARQ worker (nếu có)
    """
    # Verify ownership
    stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document không tồn tại hoặc bạn không có quyền")

    if doc.media_type not in (MediaType.VIDEO, MediaType.AUDIO):
        raise HTTPException(status_code=400, detail="Document này không phải media")

    # Check if transcript already exists
    existing_stmt = select(Transcript).where(Transcript.document_id == document_id)
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Transcript đã tồn tại cho document này")

    # Create transcript record
    transcript = Transcript(
        user_id=user_id,
        document_id=document_id,
        full_text="",
        language=payload.language,
        duration=0.0,
        segments=[],
        status="pending",
    )
    db.add(transcript)
    await db.commit()

    # Queue ARQ job
    arq_pool = _get_arq_pool(request)
    if arq_pool:
        try:
            await arq_pool.enqueue_job(
                "transcribe_media_task",
                document_id_str=str(document_id),
                user_id_str=str(user_id),
                language=payload.language,
            )
            logger.info(f"Queued transcription job for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to queue transcription: {e}")
            # Update status to failed
            transcript.status = "failed"
            transcript.error_message = f"Failed to queue job: {str(e)}"
            await db.commit()
            raise HTTPException(status_code=500, detail=f"Không thể queue transcription: {str(e)}")
    else:
        logger.warning("ARQ pool not available - transcription will not be automatic")

    return MessageResponse(
        message="Transcription request đã được chấp nhận",
        detail="Job đang chờ xử lý. Kiểm tra status endpoint để theo dõi tiến trình.",
    )


@router.put(
    "/{document_id}/transcript",
    response_model=TranscriptInfo,
    summary="Update transcript (manual correction)",
)
async def update_transcript(
    document_id: uuid.UUID,
    payload: TranscriptUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Cập nhật transcript (manual correction hoặc paste transcript).

    Hữu ích khi:
    - Auto-transcription có lỗi và cần chỉnh sửa
    - User muốn dán transcript thủ công
    """
    # Verify ownership & get transcript
    stmt = select(Transcript).where(
        Transcript.document_id == document_id,
        Transcript.user_id == user_id,
    )
    result = await db.execute(stmt)
    transcript = result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript không tồn tại")

    # Update fields
    if payload.full_text is not None:
        transcript.full_text = payload.full_text
    if payload.segments is not None:
        transcript.segments = [seg.model_dump() for seg in payload.segments]
    if payload.language is not None:
        transcript.language = payload.language

    transcript.status = "completed"
    await db.commit()
    await db.refresh(transcript)

    return transcript


@router.get(
    "/{document_id}/transcript/status",
    response_model=TranscriptStatus,
    summary="Check transcription status",
)
async def get_transcription_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Kiểm tra tiến trình transcription."""
    stmt = select(Transcript).where(
        Transcript.document_id == document_id,
        Transcript.user_id == user_id,
    )
    result = await db.execute(stmt)
    transcript = result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript không tồn tại")

    # Calculate progress (mock - would be updated by worker)
    progress = None
    if transcript.status == "pending":
        progress = 10.0
    elif transcript.status == "processing":
        progress = 50.0
    elif transcript.status == "completed":
        progress = 100.0

    return TranscriptStatus(
        document_id=document_id,
        status=transcript.status,
        progress=progress,
    )


@router.delete(
    "/{document_id}/transcript",
    response_model=MessageResponse,
    summary="Delete transcript",
)
async def delete_transcript(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Xóa transcript."""
    stmt = select(Transcript).where(
        Transcript.document_id == document_id,
        Transcript.user_id == user_id,
    )
    result = await db.execute(stmt)
    transcript = result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript không tồn tại")

    await db.delete(transcript)
    await db.commit()

    return MessageResponse(message="Transcript đã được xóa")
