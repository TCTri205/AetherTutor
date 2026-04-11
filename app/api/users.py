"""
Users API endpoints — Profile management (v1.2).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user_id
from app.schemas.auth import ChangePasswordRequest
from app.schemas.user import UserProfileResponse, UserProfileUpdateRequest
from app.services.user_service import UserService
from app.core.exceptions import AppError

router = APIRouter(prefix="/users", tags=["users"])


def _user_response(user) -> UserProfileResponse:
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        email_verified=user.email_verified,
        is_active=user.is_active,
        preferences=user.preferences,
        last_login_at=str(user.last_login_at) if user.last_login_at else None,
        created_at=str(user.created_at),
        updated_at=str(user.updated_at),
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get the current authenticated user's profile."""
    service = UserService(db)
    user = await service.get_profile(user_id)
    if not user:
        raise AppError(
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="USER_NOT_FOUND",
        )
    return _user_response(user)


@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
)
async def update_me(
    request: Request,
    body: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update the current user's profile fields."""
    service = UserService(db)
    try:
        user = await service.update_profile(
            user_id,
            **body.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="USER_UPDATE_FAILED",
        )

    if not user:
        raise AppError(
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="USER_NOT_FOUND",
        )

    return _user_response(user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Change the current user's password."""
    service = UserService(db)
    try:
        await service.change_password(
            user_id, body.old_password, body.new_password
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="USER_PASSWORD_CHANGE_FAILED",
        )
    return None
