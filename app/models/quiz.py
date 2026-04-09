"""
Quiz, QuizResult, QuizAnswer models for Stage 2 - Examiner & Quiz System
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, ForeignKey, Index, SmallInteger, DateTime
)
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Quiz(Base, TimestampMixin):
    """Quiz generated from knowledge graph entities."""
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    num_questions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, server_default="10"
    )
    question_types: Mapped[list] = mapped_column(
        ARRAY(String(50)), nullable=False, default=["multiple_choice"],
        server_default="'{multiple_choice}'"
    )
    difficulty: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )  # 1-5 scale
    quiz_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, server_default="{}"
    )

    # Questions stored as JSON in metadata for simplicity
    # Format: [{"question_id", "question_text", "options", "correct_answer", ...}]

    # Relationships
    user = relationship("User", back_populates="quizzes")
    document = relationship("Document", back_populates="quizzes")
    results = relationship(
        "QuizResult", back_populates="quiz", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_quizzes_user_id", "user_id"),
        Index("idx_quizzes_document_id", "document_id"),
    )


class QuizResult(Base, TimestampMixin):
    """Result of a user completing a quiz."""
    __tablename__ = "quiz_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0.0"
    )  # Percentage 0-100
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False)
    weak_areas: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]")
    # List of entity names user struggled with

    # Quality feedback for quiz (1-5 rating)
    quality_rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    quality_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Feedback analysis results (populated by quiz_feedback_analysis_task)
    feedback_category: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # factual_error, poor_distractor, too_easy, too_hard, other
    feedback_severity: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # low, medium, high
    feedback_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)

    completed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default="NOW()"
    )

    # Relationships
    user = relationship("User", back_populates="quiz_results")
    quiz = relationship("Quiz", back_populates="results")
    answers = relationship(
        "QuizAnswer", back_populates="quiz_result", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_quiz_results_user_id", "user_id"),
        Index("idx_quiz_results_quiz_id", "quiz_id"),
        Index("idx_quiz_results_completed_at", "completed_at"),
    )


class QuizAnswer(Base, TimestampMixin):
    """Individual answer to a quiz question."""
    __tablename__ = "quiz_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quiz_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_results.id", ondelete="CASCADE"), nullable=False
    )
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # multiple_choice | true_false
    user_answer: Mapped[dict] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Entity liên quan để tính weak areas
    difficulty: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )

    # Relationships
    user = relationship("User", back_populates="quiz_answers")
    quiz_result = relationship("QuizResult", back_populates="answers")

    __table_args__ = (
        Index("idx_quiz_answers_result_id", "quiz_result_id"),
        Index("idx_quiz_answers_user_id", "user_id"),
        Index("idx_quiz_answers_correct", "is_correct"),
    )
