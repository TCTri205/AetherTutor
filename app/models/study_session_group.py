"""
StudySessionGroup model — Group multiple study sessions together (v1.2).

Cho phép gom nhóm các review sessions thành 1 group để analytics.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import TimestampMixin
from ..database import Base


class StudySessionGroup(Base, TimestampMixin):
    __tablename__ = "study_session_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_cards_reviewed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    avg_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="study_session_groups")
    sessions = relationship(
        "StudySession", back_populates="group", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_session_groups_user", "user_id"),
        Index("idx_session_groups_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<StudySessionGroup {self.session_type} cards={self.total_cards_reviewed}>"
