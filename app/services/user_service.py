"""
UserService — Profile management (v1.2).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import UserRepository
from app.services.security import hash_password, verify_password


class UserService:
    """User profile management service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_profile(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user profile by ID."""
        return await self.user_repo.get_by_id(user_id)

    async def update_profile(
        self, user_id: uuid.UUID, **kwargs
    ) -> Optional[User]:
        """
        Update user profile fields.

        Allowed fields: username, full_name, avatar_url, preferences
        """
        allowed = {"username", "full_name", "avatar_url", "preferences"}
        filtered = {k: v for k, v in kwargs.items() if k in allowed}

        if not filtered:
            return None

        # Check username uniqueness
        if "username" in filtered:
            existing = await self.user_repo.get_by_username(filtered["username"])
            if existing and existing.id != user_id:
                raise ValueError("Username already taken")

        user = await self.user_repo.update(user_id, **filtered)
        await self.session.commit()
        if user:
            await self.session.refresh(user)

        logger.info(f"Profile updated for user {user_id}")
        return user

    async def change_password(
        self, user_id: uuid.UUID, old_password: str, new_password: str
    ) -> bool:
        """Change user password after verifying old password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if not verify_password(old_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        new_hashed = hash_password(new_password)
        await self.user_repo.update(user_id, hashed_password=new_hashed)
        await self.session.commit()

        logger.info(f"Password changed for user {user_id}")
        return True
