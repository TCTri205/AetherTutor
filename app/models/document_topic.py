"""
DocumentTopic junction table — Many-to-many between Topic and Document.

ON DELETE CASCADE trên cả 2 FKs → xóa topic/document chỉ xóa junction row,
KHÔNG xóa target data.
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import TimestampMixin
from ..database import Base


class DocumentTopic(Base, TimestampMixin):
    __tablename__ = "document_topics"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    topic = relationship("Topic", back_populates="document_associations")
    document = relationship("Document", back_populates="document_associations")

    __table_args__ = (
        Index("idx_document_topics_topic", "topic_id"),
        Index("idx_document_topics_document", "document_id"),
    )
