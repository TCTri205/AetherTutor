"""
Team and TeamMember models for real-time collaboration.

Teams allow users to share graphs, notes, and other resources with role-based access control.
"""
import uuid
from enum import Enum as PyEnum
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Index, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TeamRole(PyEnum):
    """Team member roles."""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Team(Base, TimestampMixin):
    """A collaboration team (organization)."""
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    max_members: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Relationships
    owner = relationship("User", backref="owned_teams")
    members = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )
    shared_resources = relationship(
        "SharedResource", back_populates="team", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_teams_owner_id", "owner_id"),
        Index("idx_teams_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Team {self.name} (owner={self.owner_id})>"


class TeamMember(Base, TimestampMixin):
    """Association between users and teams with role-based access."""
    __tablename__ = "team_members"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[TeamRole] = mapped_column(
        SAEnum(TeamRole, name="team_role_enum", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=TeamRole.VIEWER,
        nullable=False,
    )
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, nullable=False, server_default="true"
    )

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], backref="team_memberships")
    inviter = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        Index("idx_team_members_team_id", "team_id"),
        Index("idx_team_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<TeamMember user={self.user_id} team={self.team_id} role={self.role.value}>"
