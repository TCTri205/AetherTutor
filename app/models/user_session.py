"""
UserSession model — Multi-device session management (v1.2).

Mỗi device/browser có 1 session riêng với refresh_token độc lập.
Khi logout → soft delete (is_revoked=True) để giữ audit trail.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import TimestampMixin
from ..database import Base


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token: Mapped[str] = mapped_column(
        Text, unique=True, index=True, nullable=False
    )
    device_info: Mapped[str | None] = mapped_column(String(255))  # SHA-256 hash
    ip_address: Mapped[str | None] = mapped_column(String(45))     # IPv4/IPv6 max
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_user_sessions_user", "user_id"),
        Index("idx_user_sessions_expires", "expires_at"),
        Index("idx_user_sessions_active", "user_id", "is_revoked"),
    )

    def __repr__(self) -> str:
        return f"<UserSession user_id={self.user_id} revoked={self.is_revoked}>"
