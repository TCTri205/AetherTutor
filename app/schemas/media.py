"""
Pydantic schemas for Media APIs (Sprint 17 - Media Microlearning).
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


# --- Transcript Segment ---

class TranscriptSegment(BaseModel):
    """A single segment of transcribed audio/video."""
    text: str = Field(..., description="Transcribed text")
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    speaker: Optional[str] = Field(None, description="Speaker identifier (optional)")


# --- Transcript Schemas ---

class TranscriptBase(BaseModel):
    """Base schema for transcript."""
    document_id: uuid.UUID = Field(..., description="ID của document được transcribe")
    language: str = Field(default="en", max_length=10, description="Ngôn ngữ (e.g., 'en', 'vi')")


class TranscriptCreate(TranscriptBase):
    """Schema để tạo transcription request."""
    pass


class TranscriptUpdate(BaseModel):
    """Schema để cập nhật transcript (manual correction)."""
    full_text: Optional[str] = None
    segments: Optional[List[TranscriptSegment]] = None
    language: Optional[str] = Field(None, max_length=10)


class TranscriptInfo(BaseModel):
    """Full transcript info for response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    full_text: str
    language: str
    duration: float
    segments: List[dict]  # JSON segments
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TranscriptStatus(BaseModel):
    """Transcript processing status."""
    document_id: uuid.UUID
    status: str  # pending | processing | completed | failed
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")


# --- Media Upload Schemas ---

class MediaUploadRequest(BaseModel):
    """Request to register a media document (video/audio)."""
    source_url: Optional[str] = Field(None, max_length=1024, description="URL YouTube/Vimeo/direct link")
    media_type: str = Field(..., description="Loại media: video, audio")
    title: str = Field(..., min_length=1, max_length=500, description="Tiêu đề media")
    auto_transcribe: bool = Field(
        default=False,
        description="Tự động transcribe sau khi upload"
    )


class MediaUploadResponse(BaseModel):
    """Response after media upload/registration."""
    document_id: uuid.UUID
    filename: str
    media_type: str
    source_url: Optional[str] = None
    status: str  # PENDING | PROCESSING | COMPLETED
    transcript_status: Optional[str] = None  # null | pending | processing | completed


# --- Generic Response ---

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None
