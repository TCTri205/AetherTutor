"""
AuthService — Register, Login, Refresh, Logout (v1.2).

Sử dụng UserSession table cho multi-device support.
Mỗi device có 1 refresh_token riêng, không ghi đè lẫn nhau.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.repositories.session import UserSessionRepository
from app.services.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_device_info,
)
from app.config import settings


class AuthService:
    """Authentication service with multi-device session support."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = UserSessionRepository(session)

    async def register(
        self,
        email: str,
        password: str,
        username: str | None = None,
        full_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Register a new user.

        Returns dict with user, access_token, refresh_token.
        """
        # Check if email already exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        # Check if username already exists (if provided)
        if username:
            existing_user = await self.user_repo.get_by_username(username)
            if existing_user:
                raise ValueError("Username already taken")

        # Create user
        hashed = hash_password(password)
        user = await self.user_repo.create(
            email=email,
            hashed_password=hashed,
            username=username,
            full_name=full_name,
            is_active=True,
            is_superuser=False,
        )
        await self.session.commit()
        await self.session.refresh(user)

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Create UserSession
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.session_repo.create(
            user_id=user.id,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        await self.session.commit()

        logger.info(f"User registered: {user.email} ({user.id})")

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def login(
        self,
        email: str,
        password: str,
        device_info: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """
        Login with email + password. Creates new UserSession.

        Returns dict with user, access_token, refresh_token, session.
        """
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        # Update last login
        await self.user_repo.update_last_login(user.id)
        await self.session.commit()

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Create UserSession for this device
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Hash device info for security
        device_hash = hash_device_info(device_info, ip_address)

        session = await self.session_repo.create(
            user_id=user.id,
            refresh_token=refresh_token,
            device_info=device_hash,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        await self.session.commit()
        await self.session.refresh(session)

        logger.info(f"User logged in: {user.email} ({user.id})")

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session": session,
        }

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token.

        Implements token rotation: revoke old session, create new one.
        """
        # Find session
        session = await self.session_repo.get_by_refresh_token(refresh_token)
        if not session:
            raise ValueError("Invalid refresh token")

        if session.is_revoked:
            raise ValueError("Refresh token has been revoked")

        if session.expires_at < datetime.now(timezone.utc):
            # Token expired — revoke it
            await self.session_repo.revoke(session.id)
            await self.session.commit()
            raise ValueError("Refresh token has expired")

        # Decode to get user_id
        try:
            payload = decode_token(refresh_token)
            user_id = uuid.UUID(payload["sub"])
        except ValueError:
            raise ValueError("Invalid refresh token")

        # Verify user still exists and is active
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or deactivated")

        # Revoke old session (rotation)
        await self.session_repo.revoke(session.id)

        # Create new session
        new_refresh_token = create_refresh_token(str(user_id))
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        new_session = await self.session_repo.create(
            user_id=user_id,
            refresh_token=new_refresh_token,
            device_info=session.device_info,
            ip_address=session.ip_address,
            expires_at=expires_at,
        )

        access_token = create_access_token(str(user_id))
        await self.session.commit()
        await self.session.refresh(new_session)

        logger.debug(f"Token refreshed for user {user_id}")

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "session": new_session,
        }

    async def logout(self, refresh_token: str) -> bool:
        """
        Logout by revoking the session associated with refresh token.
        Soft delete — keeps audit trail.
        """
        session = await self.session_repo.get_by_refresh_token(refresh_token)
        if not session:
            return False

        await self.session_repo.revoke(session.id)
        await self.session.commit()

        logger.debug(f"Session revoked: {session.id}")
        return True

    async def logout_all(self, user_id: uuid.UUID) -> int:
        """Logout all sessions for a user."""
        count = await self.session_repo.revoke_all_user_sessions(user_id)
        await self.session.commit()
        logger.info(f"All sessions revoked for user {user_id}")
        return count
