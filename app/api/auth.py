"""
Auth API endpoints — Register, Login, Refresh, Logout (v1.2).

Rate limited per v1.2 plan.
Supports both JWT Bearer and X-User-Id header during transition.
"""
from __future__ import annotations

import uuid

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
from app.core.exceptions import AppError
from app.repositories.user import UserRepository
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
from app.schemas.auth_extended import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    MessageResponse,
    PasswordResetResponse,
    EmailVerificationResponse,
)
from app.services.auth_service import AuthService
from app.services.security import hash_password
from app.services.email_service import (
    generate_verification_token,
    generate_password_reset_token,
    decode_email_token,
    VERIFICATION_TOKEN_TYPE,
    PASSWORD_RESET_TOKEN_TYPE,
    send_verification_email,
    send_password_reset_email,
)

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


# ---------------------------------------------------------------------------
# Email Verification & Password Reset Endpoints
# ---------------------------------------------------------------------------

# Rate limit constant for auth email endpoints (not in constants.py yet, use inline)
RATE_LIMIT_AUTH_EMAIL = "10/minute"


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset email",
)
@limiter.limit(RATE_LIMIT_AUTH_EMAIL)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a password reset token and send email to the user.

    Always returns 200 even if email doesn't exist (security: prevents email enumeration).
    Token expires in 1 hour.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(body.email)

    if user:
        try:
            token = generate_password_reset_token(str(user.id), user.email)
            await send_password_reset_email(user.email, token)
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            raise AppError(
                message="Failed to send password reset email. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="EMAIL_SEND_FAILED",
            )

    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
    summary="Reset password with token",
)
@limiter.limit(RATE_LIMIT_AUTH_EMAIL)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate the password reset token and update the password.

    Token expires in 1 hour and is single-use.
    """
    try:
        payload = decode_email_token(body.token, PASSWORD_RESET_TOKEN_TYPE)
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_RESET_TOKEN",
        )

    user_id = uuid.UUID(payload["sub"])
    token_email = payload["email"]

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.email != token_email:
        raise AppError(
            message="Invalid reset token.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_RESET_TOKEN",
        )

    if not user.is_active:
        raise AppError(
            message="Account is deactivated.",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ACCOUNT_DEACTIVATED",
        )

    # Hash and update password
    hashed = hash_password(body.new_password)
    await user_repo.update(user_id, hashed_password=hashed)
    await db.commit()

    logger.info(f"Password reset successfully for user {user_id}")

    return PasswordResetResponse(
        message="Password has been reset successfully.",
        user_id=str(user_id),
    )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
    summary="Verify email with token",
)
@limiter.limit(RATE_LIMIT_AUTH_EMAIL)
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate the email verification token and mark the user as verified.

    Token expires in 24 hours.
    """
    try:
        payload = decode_email_token(body.token, VERIFICATION_TOKEN_TYPE)
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_VERIFICATION_TOKEN",
        )

    user_id = uuid.UUID(payload["sub"])
    token_email = payload["email"]

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.email != token_email:
        raise AppError(
            message="Invalid verification token.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_VERIFICATION_TOKEN",
        )

    if user.email_verified:
        return EmailVerificationResponse(
            message="Email is already verified.",
            email_verified=True,
            user_id=str(user_id),
        )

    # Mark as verified
    await user_repo.verify_email(user_id)
    await db.commit()

    logger.info(f"Email verified for user {user_id}")

    return EmailVerificationResponse(
        message="Email verified successfully.",
        email_verified=True,
        user_id=str(user_id),
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
)
@limiter.limit(RATE_LIMIT_AUTH_EMAIL)
async def resend_verification(
    request: Request,
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Resend the email verification link.

    Only sends if the user exists and is not yet verified.
    Always returns 200 to prevent email enumeration.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(body.email)

    if user and not user.email_verified:
        try:
            token = generate_verification_token(str(user.id), user.email)
            await send_verification_email(user.email, token)
            logger.info(f"Verification email resent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to resend verification email: {e}")
            raise AppError(
                message="Failed to send verification email. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="EMAIL_SEND_FAILED",
            )

    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If an account with that email exists and is not verified, "
                "a verification link has been sent."
    )
