"""
UserSessionRepository — CRUD operations for UserSession model (v1.2).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession
from app.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSession]):
    """Repository for UserSession model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, UserSession)

    async def get_by_refresh_token(self, refresh_token: str) -> Optional[UserSession]:
        """Find session by refresh token."""
        stmt = select(UserSession).where(
            UserSession.refresh_token == refresh_token
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, **kwargs) -> UserSession:
        """Create a new session."""
        session = UserSession(**kwargs)
        self.session.add(session)
        await self.session.flush()
        return session

    async def revoke(self, session_id: uuid.UUID) -> Optional[UserSession]:
        """Soft-revoke a session (keep audit trail)."""
        session = await self.get_by_id(session_id)
        if session:
            session.is_revoked = True
            session.revoked_at = datetime.now(timezone.utc)
            await self.session.flush()
        return session

    async def revoke_all_user_sessions(
        self, user_id: uuid.UUID
    ) -> int:
        """Revoke all sessions for a user."""
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_revoked == False)
            .values(is_revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def get_active_sessions(
        self, user_id: uuid.UUID, limit: int = 10, offset: int = 0
    ) -> list[UserSession]:
        """Get active (non-revoked) sessions for a user."""
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_revoked == False)
            .order_by(UserSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_expired_sessions(self, older_than_days: int = 30) -> int:
        """Delete revoked sessions that expired older_than_days ago."""
        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # We'll use raw SQL for the date arithmetic
        from sqlalchemy import text

        stmt = text(
            "DELETE FROM user_sessions "
            "WHERE is_revoked = true "
            "AND expires_at < NOW() - INTERVAL ':days days'"
        ).bindparams(days=older_than_days)
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]
