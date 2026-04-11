"""
Topic model — Organize documents and notes into topics (v1.2).

Mỗi user có thể tạo nhiều topics. Topic được liên kết với documents
và notes thông qua junction tables (document_topics, note_topics).
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import TimestampMixin
from ..database import Base


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(
        String(7), nullable=False, server_default="#3B82F6"
    )
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="topics")
    document_associations = relationship(
        "DocumentTopic", back_populates="topic", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", secondary="document_topics", back_populates="topics"
    )
    note_associations = relationship(
        "NoteTopic", back_populates="topic", cascade="all, delete-orphan"
    )
    notes = relationship(
        "Note", secondary="note_topics", back_populates="topics"
    )

    __table_args__ = (
        Index("idx_topics_user", "user_id"),
        Index("idx_topics_user_slug", "user_id", "slug", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Topic {self.name} (user={self.user_id})>"
