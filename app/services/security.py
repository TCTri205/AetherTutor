"""
Security utilities cho authentication.
- Password hashing (bcrypt)
- JWT token generation & validation
- Device info hashing

v1.2 Fix: Sử dụng datetime.now(timezone.utc) thay vì datetime.utcnow() (deprecated Python 3.12+)
"""
from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import bcrypt
import jwt
from ..config import settings


def hash_password(password: str) -> str:
    """Hash password bằng bcrypt."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password với hashed password."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT refresh token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    """Giải mã và validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            leeway=30,  # ±30 giây clock skew tolerance
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def hash_device_info(user_agent: str | None, ip_address: str | None = None) -> str:
    """
    Hash device info từ User-Agent để tránh lưu chuỗi quá dài hoặc chứa mã độc.

    Returns:
        SHA-256 hash (64 ký tự hex) của "user_agent|ip_address"
    """
    raw = f"{user_agent or 'unknown'}|{ip_address or 'unknown'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
