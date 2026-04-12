"""
SharedResource model for team collaboration.

Tracks which resources (graphs, notes, flashcards, etc.) are shared with teams
and what permission level each team member has.
"""
import uuid
from enum import Enum as PyEnum
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import String, Boolean, ForeignKey, Index, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SharedResourceType(PyEnum):
    """Types of shareable resources."""
    GRAPH = "graph"
    NOTE = "note"
    FLASHCARD = "flashcard"
    QUIZ = "quiz"
    CONVERSATION = "conversation"
    DOCUMENT = "document"


class SharePermission(PyEnum):
    """Permission levels for shared resources."""
    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"


class SharedResource(Base, TimestampMixin):
    """A resource shared with a team, with permission control."""
    __tablename__ = "shared_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[SharedResourceType] = mapped_column(
        SAEnum(SharedResourceType, name="shared_resource_type_enum", create_constraint=True),
        nullable=False,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    shared_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    default_permission: Mapped[SharePermission] = mapped_column(
        SAEnum(SharePermission, name="share_permission_enum", create_constraint=True),
        default=SharePermission.VIEW,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, nullable=False, server_default="true"
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default={}, server_default="{}"
    )

    # Relationships
    team = relationship("Team", back_populates="shared_resources")
    sharer = relationship("User", backref="shared_resources")

    __table_args__ = (
        Index("idx_shared_resources_team", "team_id"),
        Index("idx_shared_resources_resource", "resource_type", "resource_id"),
        Index("idx_shared_resources_shared_by", "shared_by"),
    )

    def __repr__(self) -> str:
        return (
            f"<SharedResource team={self.team_id} "
            f"type={self.resource_type.value} resource={self.resource_id} "
            f"perm={self.default_permission.value}>"
        )
