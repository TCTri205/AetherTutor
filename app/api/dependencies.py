"""
API Dependencies - Authentication & Authorization

Middleware lấy user_id từ request header (tạm thời X-User-Id).
Fallback về default user nếu không có header (cho development).

Sau này có thể nâng cấp lên JWT mà không cần thay đổi business logic.
"""

import uuid
from fastapi import Header, HTTPException, status
from loguru import logger

# Default user UUID (khớp với migration 1)
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user_id(
    x_user_id: str | None = Header(default=None),
) -> uuid.UUID:
    """
    Lấy user_id từ header X-User-Id.
    
    Nếu không có header, fallback về default user (cho development).
    
    Args:
        x_user_id: Giá trị của header X-User-Id
        
    Returns:
        UUID của user hiện tại
        
    Raises:
        HTTPException: Nếu user_id không hợp lệ
    """
    if x_user_id:
        try:
            user_id = uuid.UUID(x_user_id)
            logger.debug(f"Authenticated user: {user_id}")
            return user_id
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid X-User-Id header: {x_user_id}",
            )
    
    # Fallback về default user cho development
    logger.debug("No X-User-Id header, using default user")
    return DEFAULT_USER_ID


async def get_optional_user_id(
    x_user_id: str | None = Header(default=None),
) -> uuid.UUID | None:
    """
    Lấy user_id từ header (optional).
    
    Trả về None nếu không có header, không fallback.
    Phù hợp cho endpoints công khai nhưng có thể có auth.
    """
    if x_user_id:
        try:
            return uuid.UUID(x_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid X-User-Id header: {x_user_id}",
            )
    
    return None
