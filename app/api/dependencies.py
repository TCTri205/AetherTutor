"""
API Dependencies - Authentication & Authorization

HỖ TRỢ CẢ HAI mechanisms trong giai đoạn transition:
1. JWT Bearer token (production-ready)
2. X-User-Id header (backward compat cho development)

Priority: JWT > Header > Default fallback
"""

from __future__ import annotations

import uuid
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.security import decode_token
from app.config import settings
from app.database import get_db

# Default user UUID (khớp với migration 1)
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

security = HTTPBearer(auto_error=False)  # auto_error=False để optional


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_user_id: str | None = Header(default=None),
) -> uuid.UUID:
    """
    Xác thực JWT token hoặc header X-User-Id và trả về user_id.

    Priority:
    1. JWT Bearer token (nếu có)
    2. X-User-Id header (backward compat)
    3. Default user (development fallback)

    Args:
        credentials: JWT token từ Authorization header
        x_user_id: Giá trị của header X-User-Id

    Returns:
        UUID của user hiện tại

    Raises:
        HTTPException: Nếu authentication fail
    """
    # Priority 1: JWT Bearer token
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )
            user_id = uuid.UUID(payload["sub"])
            logger.debug(f"Authenticated via JWT: {user_id}")
            return user_id
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid JWT token: {e}",
            )

    # Priority 2: X-User-Id header (development ONLY — deprecated)
    if x_user_id:
        if settings.APP_ENV != "development":
            logger.critical(
                f"SECURITY: X-User-Id header rejected in {settings.APP_ENV} mode. "
                f"Impersonation attempt from IP. Header value: {x_user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-User-Id header is only allowed in development mode",
            )
        try:
            user_id = uuid.UUID(x_user_id)
            logger.warning(
                f"Authenticated via X-User-Id header (dev-only, deprecated): {user_id}"
            )
            return user_id
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid X-User-Id header: {x_user_id}",
            )

    # Priority 3: Default user (development only)
    if settings.APP_ENV == "development":
        logger.debug("No auth provided, using default user (dev mode)")
        return DEFAULT_USER_ID

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_user_id: str | None = Header(default=None),
) -> uuid.UUID | None:
    """
    Lấy user_id từ header hoặc JWT (optional).

    Trả về None nếu không có auth, không fallback.
    Phù hợp cho endpoints công khai nhưng có thể có auth.

    Security: Chỉ chấp nhận X-User-Id ở dev mode, và kiểm tra token type "access".
    """
    # Try JWT first
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.get("type") != "access":
                logger.debug("Optional auth: rejected non-access token type")
                return None
            return uuid.UUID(payload["sub"])
        except ValueError:
            pass

    # Try header (dev only)
    if x_user_id:
        if settings.APP_ENV != "development":
            logger.critical(
                f"SECURITY: X-User-Id header rejected in {settings.APP_ENV} mode (optional auth)"
            )
            return None
        try:
            return uuid.UUID(x_user_id)
        except ValueError:
            pass

    return None
