"""
User schemas — Request/Response for profile management (v1.2).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: str
    email: str
    username: str | None
    full_name: str | None
    avatar_url: str | None
    email_verified: bool
    is_active: bool
    preferences: dict
    last_login_at: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    full_name: str | None = Field(None, max_length=255)
    avatar_url: str | None = Field(None, max_length=512)
    preferences: dict | None = None
