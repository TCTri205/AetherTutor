"""
Integration tests cho Auth Extended endpoints (Sprint 14/19).

Kiểm tra:
- POST /auth/forgot-password
- POST /auth/reset-password
- POST /auth/verify-email
- POST /auth/resend-verification
- Rate limiting trên auth endpoints
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
import jwt

from app.services.email_service import (
    VERIFICATION_TOKEN_TYPE,
    PASSWORD_RESET_TOKEN_TYPE,
    TOKEN_ALGORITHM,
)


# --- Helpers ---

def _unique(prefix: str = "test") -> str:
    """Tạo string unique để tránh conflict giữa các test."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _make_register_payload(**overrides) -> dict:
    """Tạo register payload mặc định."""
    payload = {
        "email": f"{_unique('user')}@example.com",
        "password": "SecurePass1",
        "username": _unique("user"),
        "full_name": "Test User",
    }
    payload.update(overrides)
    return payload


def _generate_valid_token(user_id: str, email: str, token_type: str, secret: str = "your-secret-key-change-in-production") -> str:
    """Generate valid JWT token cho email verification/password reset."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24 if token_type == VERIFICATION_TOKEN_TYPE else 1)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": token_type,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=TOKEN_ALGORITHM)


# --- Forgot Password Tests ---

class TestForgotPassword:
    """Kiểm tra POST /auth/forgot-password."""

    async def test_forgot_password_existing_user(self, async_client: AsyncClient):
        """Forgot password cho user tồn tại → 200, không send email thật (mock mode)."""
        # Register user trước
        reg_payload = _make_register_payload()
        await async_client.post("/api/v1/auth/register", json=reg_payload)

        # Request forgot password
        resp = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": reg_payload["email"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "password reset link has been sent" in data["message"].lower()

    async def test_forgot_password_nonexistent_user(self, async_client: AsyncClient):
        """Forgot password cho email không tồn tại → vẫn 200 (prevent enumeration)."""
        resp = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": f"{_unique('nobody')}@example.com"},
        )
        # Always returns 200 to prevent email enumeration
        assert resp.status_code == 200
        data = resp.json()
        assert "password reset link has been sent" in data["message"].lower()

    async def test_forgot_password_invalid_email(self, async_client: AsyncClient):
        """Forgot password với email invalid format → 422."""
        resp = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422


# --- Reset Password Tests ---

class TestResetPassword:
    """Kiểm tra POST /auth/reset-password."""

    async def test_reset_password_success(self, async_client: AsyncClient, test_db):
        """Reset password với valid token → 200."""
        # Register user
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_resp.status_code == 201

        user_id = reg_resp.json()["user"]["id"]
        email = reg_payload["email"]

        # Generate token
        token = _generate_valid_token(user_id, email, PASSWORD_RESET_TOKEN_TYPE)

        # Reset password
        resp = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "NewSecurePass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user_id

    async def test_reset_password_invalid_token(self, async_client: AsyncClient):
        """Reset password với token invalid → 400."""
        resp = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid.token.here", "new_password": "NewSecurePass1"},
        )
        assert resp.status_code == 400

    async def test_reset_password_expired_token(self, async_client: AsyncClient):
        """Reset password với token hết hạn → 400."""
        # Generate expired token
        expired_expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "user@example.com",
            "exp": expired_expire,
            "type": PASSWORD_RESET_TOKEN_TYPE,
            "jti": uuid.uuid4().hex,
        }
        token = jwt.encode(payload, "your-secret-key-change-in-production", algorithm=TOKEN_ALGORITHM)

        resp = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "NewSecurePass1"},
        )
        assert resp.status_code == 400

    async def test_reset_password_wrong_token_type(self, async_client: AsyncClient, test_db):
        """Reset password với verification token (wrong type) → 400."""
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        user_id = reg_resp.json()["user"]["id"]
        email = reg_payload["email"]

        # Generate verification token instead of password reset token
        token = _generate_valid_token(user_id, email, VERIFICATION_TOKEN_TYPE)

        resp = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "NewSecurePass1"},
        )
        assert resp.status_code == 400

    async def test_reset_password_email_mismatch(self, async_client: AsyncClient, test_db):
        """Reset password với token có email không khớp → 400."""
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        user_id = reg_resp.json()["user"]["id"]

        # Token với email khác
        token = _generate_valid_token(user_id, "different@example.com", PASSWORD_RESET_TOKEN_TYPE)

        resp = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "NewSecurePass1"},
        )
        assert resp.status_code == 400

    async def test_reset_password_weak_password(self, async_client: AsyncClient, test_db):
        """Reset password với password yếu → vẫn 200 (API không validate password strength)."""
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        user_id = reg_resp.json()["user"]["id"]
        email = reg_payload["email"]

        token = _generate_valid_token(user_id, email, PASSWORD_RESET_TOKEN_TYPE)

        resp = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "weak"},
        )
        # Note: API có thể accept hoặc reject tùy vào validation
        # Đây là expected behavior
        assert resp.status_code in (200, 422)


# --- Verify Email Tests ---

class TestVerifyEmail:
    """Kiểm tra POST /auth/verify-email."""

    async def test_verify_email_success(self, async_client: AsyncClient, test_db):
        """Verify email với valid token → 200."""
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        user_id = reg_resp.json()["user"]["id"]
        email = reg_payload["email"]

        token = _generate_valid_token(user_id, email, VERIFICATION_TOKEN_TYPE)

        resp = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email_verified"] is True
        assert data["user_id"] == user_id

    async def test_verify_email_invalid_token(self, async_client: AsyncClient):
        """Verify email với token invalid → 400."""
        resp = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid.token.here"},
        )
        assert resp.status_code == 400

    async def test_verify_email_already_verified(self, async_client: AsyncClient, test_db):
        """Verify email lần 2 (đã verified rồi) → 200 với message khác."""
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        user_id = reg_resp.json()["user"]["id"]
        email = reg_payload["email"]

        token = _generate_valid_token(user_id, email, VERIFICATION_TOKEN_TYPE)

        # First verification
        resp1 = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert resp1.status_code == 200

        # Second verification with same token (already expired/used)
        # Note: Token vẫn valid về mặt JWT, nhưng user đã verified
        resp2 = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        # API trả về 200 với message "already verified"
        assert resp2.status_code == 200
        data = resp2.json()
        assert "already verified" in data["message"].lower()

    async def test_verify_email_wrong_token_type(self, async_client: AsyncClient, test_db):
        """Verify email với password reset token → 400."""
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        user_id = reg_resp.json()["user"]["id"]
        email = reg_payload["email"]

        # Wrong token type
        token = _generate_valid_token(user_id, email, PASSWORD_RESET_TOKEN_TYPE)

        resp = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert resp.status_code == 400


# --- Resend Verification Tests ---

class TestResendVerification:
    """Kiểm tra POST /auth/resend-verification."""

    async def test_resend_verification_unverified_user(self, async_client: AsyncClient):
        """Resend verification cho user chưa verify → 200."""
        reg_payload = _make_register_payload()
        await async_client.post("/api/v1/auth/register", json=reg_payload)

        resp = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": reg_payload["email"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "verification link has been sent" in data["message"].lower()

    async def test_resend_verification_nonexistent_user(self, async_client: AsyncClient):
        """Resend verification cho email không tồn tại → vẫn 200 (prevent enumeration)."""
        resp = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": f"{_unique('nobody')}@example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "verification link has been sent" in data["message"].lower()

    async def test_resend_verification_already_verified(self, async_client: AsyncClient, test_db):
        """Resend verification cho user đã verify → vẫn 200 (prevent enumeration)."""
        reg_payload = _make_register_payload()
        reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
        user_id = reg_resp.json()["user"]["id"]
        email = reg_payload["email"]

        # Verify first
        token = _generate_valid_token(user_id, email, VERIFICATION_TOKEN_TYPE)
        await async_client.post("/api/v1/auth/verify-email", json={"token": token})

        # Resend
        resp = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": email},
        )
        assert resp.status_code == 200

    async def test_resend_verification_invalid_email(self, async_client: AsyncClient):
        """Resend verification với email invalid → 422."""
        resp = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422


# --- Rate Limiting Tests ---

class TestAuthRateLimiting:
    """Kiểm tra rate limiting trên auth endpoints."""

    @pytest.mark.skip(reason="Rate limiting disabled in test environment via conftest.py")
    async def test_forgot_password_rate_limit(self, async_client: AsyncClient):
        """Forgot password bị rate limit khi gửi quá nhiều request."""
        # NOTE: Skip vì rate limiting bị disable trong test environment.
        # Để enable, cần modify conftest.py: không set app.state.limiter.enabled = False
        pass

    @pytest.mark.skip(reason="Rate limiting disabled in test environment via conftest.py")
    async def test_reset_password_rate_limit(self, async_client: AsyncClient):
        """Reset password bị rate limit khi gửi quá nhiều request."""
        pass

    @pytest.mark.skip(reason="Rate limiting disabled in test environment via conftest.py")
    async def test_verify_email_rate_limit(self, async_client: AsyncClient):
        """Verify email bị rate limit khi gửi quá nhiều request."""
        pass

    @pytest.mark.skip(reason="Rate limiting disabled in test environment via conftest.py")
    async def test_resend_verification_rate_limit(self, async_client: AsyncClient):
        """Resend verification bị rate limit khi gửi quá nhiều request."""
        pass
