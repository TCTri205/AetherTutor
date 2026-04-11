"""
Auth API endpoints — Register, Login, Refresh, Logout (v1.2).

Rate limited per v1.2 plan.
Supports both JWT Bearer and X-User-Id header during transition.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user_id
from app.api.limiter import limiter
from app.constants import (
    RATE_LIMIT_REGISTER,
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_REFRESH,
    RATE_LIMIT_LOGOUT,
)
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
    UserResponse,
    SessionInfo,
    ActiveSessionsResponse,
)
from app.services.auth_service import AuthService
from app.services.security import decode_token
from app.core.exceptions import AppError

import uuid

router = APIRouter(prefix="/auth", tags=["authentication"])


def _build_auth_service(db: AsyncSession) -> AuthService:
    return AuthService(db)


def _user_response(user) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        email_verified=user.email_verified,
        is_active=user.is_active,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
@limiter.limit(RATE_LIMIT_REGISTER)
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    service = _build_auth_service(db)
    try:
        result = await service.register(
            email=body.email,
            password=body.password,
            username=body.username,
            full_name=body.full_name,
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="AUTH_REGISTER_FAILED",
        )

    return RegisterResponse(
        user=_user_response(result["user"]),
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
)
@limiter.limit(RATE_LIMIT_LOGIN)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and receive JWT access + refresh tokens."""
    # Extract device info from request headers
    device_info = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    service = _build_auth_service(db)
    try:
        result = await service.login(
            email=body.email,
            password=body.password,
            device_info=device_info,
            ip_address=ip_address,
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_LOGIN_FAILED",
        )

    return LoginResponse(
        user=_user_response(result["user"]),
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
@limiter.limit(RATE_LIMIT_REFRESH)
async def refresh_token(
    request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Implements token rotation — old session is revoked, new one created.
    """
    service = _build_auth_service(db)
    try:
        result = await service.refresh(body.refresh_token)
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_REFRESH_FAILED",
        )

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout")
@limiter.limit(RATE_LIMIT_LOGOUT)
async def logout(
    request: Request, body: LogoutRequest, db: AsyncSession = Depends(get_db)
):
    """Logout by revoking the current session."""
    service = _build_auth_service(db)
    success = await service.logout(body.refresh_token)
    if not success:
        raise AppError(
            message="Invalid refresh token",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="AUTH_LOGOUT_FAILED",
        )
    return None


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT, summary="Logout all devices")
async def logout_all(
    request: Request, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Logout from all devices simultaneously."""
    service = _build_auth_service(db)
    await service.logout_all(user_id)
    return None


@router.get(
    "/sessions",
    response_model=ActiveSessionsResponse,
    summary="List active sessions",
)
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List all active (non-revoked) sessions for current user."""
    from app.repositories.session import UserSessionRepository

    session_repo = UserSessionRepository(db)
    sessions = await session_repo.get_active_sessions(user_id)

    session_infos = []
    for s in sessions:
        session_infos.append(
            SessionInfo(
                id=str(s.id),
                device_info=s.device_info,
                ip_address=s.ip_address,
                created_at=str(s.created_at),
                expires_at=str(s.expires_at),
            )
        )

    return ActiveSessionsResponse(sessions=session_infos)
