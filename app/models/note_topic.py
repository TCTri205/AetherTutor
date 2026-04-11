"""
NoteTopic junction table — Many-to-many between Topic and Note (v1.2).

ON DELETE CASCADE trên cả 2 FKs → xóa topic/note chỉ xóa junction row.
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import TimestampMixin
from ..database import Base


class NoteTopic(Base, TimestampMixin):
    __tablename__ = "note_topics"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    topic = relationship("Topic", back_populates="note_associations")
    note = relationship("Note", back_populates="note_associations")

    __table_args__ = (
        Index("idx_note_topics_topic", "topic_id"),
        Index("idx_note_topics_note", "note_id"),
    )
