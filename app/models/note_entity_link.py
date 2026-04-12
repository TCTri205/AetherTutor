"""
NoteEntityLink - Junction table linking notes to graph entities.

This model implements BR-009 (Note Backlink Rule):
Khi tạo note mới, hệ thống quét nội dung để tìm khái niệm trùng với
entities trong graph và lưu liên kết vào bảng này.
"""

import uuid
from sqlalchemy import (
    String, Text, ForeignKey, Index, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class NoteEntityLink(Base, TimestampMixin):
    """
    Junction table linking a Note to a GraphEntity.

    Enables BR-009: Note backlink suggestions based on entity matching.
    Also enables AI retrieval of notes by entity (via ChromaDB embeddings).
    """
    __tablename__ = "note_entity_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False
    )
    match_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="exact", server_default="exact"
    )  # exact | fuzzy | semantic | ai_suggested
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0-1, match confidence
    context: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Text snippet showing where entity was found

    # Relationships
    user = relationship("User", back_populates="note_entity_links")
    note = relationship("Note", back_populates="entity_links")
    entity = relationship("GraphEntity", back_populates="note_links")

    __table_args__ = (
        Index("idx_note_entity_links_user_id", "user_id"),
        Index("idx_note_entity_links_note_id", "note_id"),
        Index("idx_note_entity_links_entity_id", "entity_id"),
        # Unique constraint: one link per note-entity pair
        Index("uq_note_entity_links_note_entity", "note_id", "entity_id", unique=True),
    )
