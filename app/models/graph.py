import uuid
from typing import Optional
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import (
    String, Text, Integer, Float, ForeignKey, UniqueConstraint, Index, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
    )


class GraphEntity(Base, TimestampMixin):
    __tablename__ = "graph_entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # document_id kept for backward compatibility but NULLABLE now
    # Use entity_documents junction table for many-to-many
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    canonical_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Obsidian Integration columns
    source: Mapped[str] = mapped_column(String(50), default="ai_extracted", index=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=[], server_default="{}")
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default={}, server_default="{}")

    # Optimistic Concurrency Control
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    __table_args__ = (
        Index("idx_graph_entities_user_id", "user_id"),
        Index("idx_graph_entities_tags", "tags", postgresql_using="gin"),
        Index("idx_graph_entities_version", "version"),
        Index("idx_graph_entities_document_id", "document_id"),
    )

    # Relationships
    document_links = relationship("EntityDocument", back_populates="entity", cascade="all, delete-orphan")
    note_links = relationship("NoteEntityLink", back_populates="entity", cascade="all, delete-orphan")


class GraphRelation(Base, TimestampMixin):
    __tablename__ = "graph_relations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Confidence & Evidence (for quality filtering and explainability)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Confidence score from LLM extraction (0.0 - 1.0)",
    )
    evidence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Source text or reasoning for this relation",
    )

    # Obsidian Integration columns
    source: Mapped[str] = mapped_column(String(50), default="ai_extracted", index=True)
    is_backlink: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default={}, server_default="{}")

    # Optimistic Concurrency Control
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    __table_args__ = (
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_graph_relations_confidence_range",
        ),
        Index("idx_graph_relations_user_id", "user_id"),
        Index("idx_graph_relations_version", "version"),
        Index("idx_graph_relations_document_id", "document_id"),
    )

    # Relationships
    source_entity = relationship("GraphEntity", foreign_keys=[source_entity_id])
    target_entity = relationship("GraphEntity", foreign_keys=[target_entity_id])


class EntityAlias(Base, TimestampMixin):
    """
    Entity alias for cross-document resolution.
    
    Maps alternative names (aliases) to canonical entity names.
    Example: "AI" → "Artificial Intelligence"
    """
    __tablename__ = "entity_aliases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual, ai_suggested, auto

    __table_args__ = (
        UniqueConstraint("user_id", "alias_name", name="uq_entity_aliases_user_alias"),
        Index("idx_entity_aliases_canonical", "canonical_name"),
    )

    # Relationships
    user = relationship("User", back_populates="entity_aliases")


class GraphEditLog(Base):
    """
    Audit log for graph edits (create/update/delete operations).
    Provides traceability and debugging for graph modifications.
    """
    __tablename__ = "graph_edit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_entities.id", ondelete="SET NULL"), nullable=True
    )
    relation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_relations.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # CREATE, UPDATE, DELETE
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # entity, relation
    old_value: Mapped[Optional[dict]] = mapped_column("old_value", JSONB, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column("new_value", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.current_timestamp(), nullable=False
    )

    __table_args__ = (
        Index("idx_graph_edit_log_user_id", "user_id"),
        Index("idx_graph_edit_log_document_id", "document_id"),
        Index("idx_graph_edit_log_created_at", "created_at"),
    )
