"""
Auth schemas — Request/Response models for authentication endpoints (v1.2).
"""
from __future__ import annotations

import re
from pydantic import BaseModel, EmailStr, Field, field_validator


# --- Request Schemas ---

PASSWORD_POLICY_PATTERN = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d).{8,}$",
    re.ASCII,
)
PASSWORD_POLICY_MSG = (
    "Password must be at least 8 characters long and contain "
    "at least one letter and one digit."
)


def _validate_password(value: str) -> str:
    """Shared password policy validator."""
    if not PASSWORD_POLICY_PATTERN.match(value):
        raise ValueError(PASSWORD_POLICY_MSG)
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    username: str | None = Field(None, min_length=3, max_length=50)
    full_name: str | None = Field(None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        return _validate_password(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_policy(cls, v: str) -> str:
        return _validate_password(v)


# --- Response Schemas ---

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str | None
    full_name: str | None
    avatar_url: str | None
    email_verified: bool
    is_active: bool

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SessionInfo(BaseModel):
    id: str
    device_info: str | None
    ip_address: str | None
    created_at: str
    expires_at: str

    class Config:
        from_attributes = True


class ActiveSessionsResponse(BaseModel):
    sessions: list[SessionInfo]
