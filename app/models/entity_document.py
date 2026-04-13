"""
EntityDocument Junction Model.

Many-to-many relationship between GraphEntity and Document.
Allows entities to be associated with multiple documents,
supporting cross-document entity resolution and merging.
"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class EntityDocument(Base, TimestampMixin):
    """
    Junction table linking GraphEntity to Documents.

    Purpose:
    - Track which documents contributed to each entity
    - Support entity merging across documents
    - Enable cross-document entity lookup
    - Prevent data loss when deleting documents (entities can survive if linked to other docs)

    Example:
        Entity "Python" might be extracted from both:
        - Document A: "Python Programming Guide"
        - Document B: "Data Science with Python"

        Both documents link to the SAME entity via this table.
    """

    __tablename__ = "entity_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Metadata
    first_seen_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.current_timestamp(),
        nullable=False,
        comment="When this entity was first linked to this document",
    )
    confidence: Mapped[float] = mapped_column(
        nullable=True,
        comment="Confidence of entity extraction from this document",
    )

    __table_args__ = (
        Index("idx_entity_documents_entity_id", "entity_id"),
        Index("idx_entity_documents_document_id", "document_id"),
        # Prevent duplicate entity-document links
        sa.UniqueConstraint(
            "entity_id",
            "document_id",
            name="uq_entity_documents_entity_document",
        ),
    )

    # Relationships
    entity = relationship("GraphEntity", back_populates="document_links")
    document = relationship("Document", back_populates="entity_links")

    def __repr__(self):
        return f"<EntityDocument(entity_id={self.entity_id}, doc_id={self.document_id})>"
