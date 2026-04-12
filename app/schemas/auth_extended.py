"""
Auth Extended Schemas — Request/Response models for email verification
and password reset endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import PASSWORD_POLICY_MSG, _validate_password


# --- Request Schemas ---

class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset flow."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request to complete password reset with token."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_policy(cls, v: str) -> str:
        return _validate_password(v)


class VerifyEmailRequest(BaseModel):
    """Request to verify email with token."""
    token: str


class ResendVerificationRequest(BaseModel):
    """Request to resend verification email."""
    email: EmailStr


# --- Response Schemas ---

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str

    class Config:
        json_schema_extra = {
            "examples": [{"message": "Password reset email sent. Please check your inbox."}]
        }


class PasswordResetResponse(BaseModel):
    """Response after successful password reset."""
    message: str
    user_id: str

    class Config:
        json_schema_extra = {
            "examples": [{"message": "Password reset successfully.", "user_id": "abc-123"}]
        }


class EmailVerificationResponse(BaseModel):
    """Response after successful email verification."""
    message: str
    email_verified: bool
    user_id: str

    class Config:
        json_schema_extra = {
            "examples": [{
                "message": "Email verified successfully.",
                "email_verified": True,
                "user_id": "abc-123"
            }]
        }
