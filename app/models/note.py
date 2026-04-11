"""
Note & NoteLink models for Stage 2 - Zettelkasten & Bi-directional Linking
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, ForeignKey, Index, DateTime
)
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Note(Base, TimestampMixin):
    """Atomic note in Zettelkasten system."""
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="literature", server_default="literature"
    )  # fleeting | literature | permanent | project
    tags: Mapped[list] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list, server_default="{}"
    )
    note_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, server_default="{}"
    )

    # Relationships
    user = relationship("User", back_populates="notes")
    outgoing_links = relationship(
        "NoteLink",
        foreign_keys="NoteLink.source_note_id",
        back_populates="source_note",
        cascade="all, delete-orphan"
    )
    incoming_links = relationship(
        "NoteLink",
        foreign_keys="NoteLink.target_note_id",
        back_populates="target_note",
        cascade="all, delete-orphan"
    )
    topics = relationship(
        "Topic", secondary="note_topics", back_populates="notes"
    )
    note_associations = relationship(
        "NoteTopic", back_populates="note", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_notes_user_id", "user_id"),
        Index("idx_notes_tags_gin", "tags", postgresql_using="gin"),
        Index("idx_notes_created_at", "created_at"),
        Index("idx_notes_user_type", "user_id", "note_type"),
    )


class NoteLink(Base, TimestampMixin):
    """Bi-directional link between two notes (backlinks)."""
    __tablename__ = "note_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    target_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Context explaining why these notes are linked
    link_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual", server_default="manual"
    )  # manual | ai_suggested | confirmed

    # Relationships
    user = relationship("User", back_populates="note_links")
    source_note = relationship("Note", foreign_keys=[source_note_id], back_populates="outgoing_links")
    target_note = relationship("Note", foreign_keys=[target_note_id], back_populates="incoming_links")

    __table_args__ = (
        Index("idx_note_links_user_id", "user_id"),
        Index("idx_note_links_source", "source_note_id"),
        Index("idx_note_links_target", "target_note_id"),
        # Unique constraint: one link per source-target pair
        Index("uq_note_links_source_target", "source_note_id", "target_note_id", unique=True),
    )
