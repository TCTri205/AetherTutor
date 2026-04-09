"""
Flashcard & StudySession models for Stage 2 - Spaced Repetition System
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, Float, ForeignKey, Index, DateTime
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Flashcard(Base, TimestampMixin):
    __tablename__ = "flashcards"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    card_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, server_default="{}"
    )
    
    # SM-2 Algorithm parameters
    sm2_ease_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5, server_default="2.5"
    )
    sm2_interval: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    sm2_repetitions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    sm2_next_review: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default="NOW()"
    )
    
    # Source: manual, quiz_wrong_answer, auto_generated
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual", server_default="manual"
    )
    
    # Relationships
    user = relationship("User", back_populates="flashcards")
    study_sessions = relationship(
        "StudySession", back_populates="flashcard", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_flashcards_user_id", "user_id"),
        Index("idx_flashcards_next_review", "sm2_next_review"),
        Index("idx_flashcards_user_due", "user_id", "sm2_next_review"),
        Index("idx_flashcards_user_source", "user_id", "source"),
    )


class StudySession(Base, TimestampMixin):
    __tablename__ = "study_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    flashcard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)  # SM-2 quality: 0-5
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default="NOW()"
    )
    
    # Relationships
    user = relationship("User", back_populates="study_sessions")
    flashcard = relationship("Flashcard", back_populates="study_sessions")
    
    __table_args__ = (
        Index("idx_study_sessions_user_id", "user_id"),
        Index("idx_study_sessions_flashcard_id", "flashcard_id"),
        Index("idx_study_sessions_reviewed_at", "reviewed_at"),
    )
