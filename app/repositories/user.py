"""
UserRepository — CRUD operations for User model.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with auth-specific methods."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, **kwargs) -> User:
        """Create a new user."""
        user = User(**kwargs)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user_id: uuid.UUID, **kwargs) -> Optional[User]:
        """Update user fields."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.session.flush()
        return user

    async def verify_email(self, user_id: uuid.UUID) -> None:
        """Mark email as verified."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                email_verified=True,
                email_verified_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update last_login_at timestamp."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
