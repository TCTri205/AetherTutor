import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import TimestampMixin
from ..database import Base


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata for custom learning persona or settings
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    # Enhancements (v1.2)
    username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    documents = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )
    flashcards = relationship(
        "Flashcard", back_populates="user", cascade="all, delete-orphan"
    )
    study_sessions = relationship(
        "StudySession", back_populates="user", cascade="all, delete-orphan"
    )
    quizzes = relationship("Quiz", back_populates="user", cascade="all, delete-orphan")
    quiz_results = relationship(
        "QuizResult", back_populates="user", cascade="all, delete-orphan"
    )
    quiz_answers = relationship(
        "QuizAnswer", back_populates="user", cascade="all, delete-orphan"
    )
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    note_links = relationship(
        "NoteLink", back_populates="user", cascade="all, delete-orphan"
    )
    entity_aliases = relationship(
        "EntityAlias", back_populates="user", cascade="all, delete-orphan"
    )

    # New relationships (v1.2)
    topics = relationship(
        "Topic", back_populates="user", cascade="all, delete-orphan"
    )
    study_session_groups = relationship(
        "StudySessionGroup", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
