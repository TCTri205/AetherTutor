"""
Transcript model for Sprint 17 - Media Microlearning

Stores transcriptions for audio/video documents with timestamped segments.
"""

import uuid
from sqlalchemy import (
    String, Text, ForeignKey, Index, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Transcript(Base, TimestampMixin):
    """Transcription for a media document (audio/video)."""
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en", server_default="en"
    )
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Duration in seconds
    segments: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    # Array of {text, start, end, speaker?}
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    # pending | processing | completed | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="transcripts")
    document = relationship("Document", back_populates="transcripts")

    __table_args__ = (
        Index("idx_transcripts_user_id", "user_id"),
        Index("idx_transcripts_document_id", "document_id"),
        Index("idx_transcripts_status", "status"),
        Index("uq_transcripts_document", "document_id", unique=True),
    )

    def __repr__(self):
        return f"<Transcript(id={self.id}, doc={self.document_id}, status={self.status})>"
