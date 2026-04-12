"""
Unit tests cho EmailService (Sprint 14/19).

Test cases:
1. Token generation and validation
2. Email template rendering
3. Mock mode behavior
4. Token expiry validation
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import jwt

from app.services.email_service import (
    generate_verification_token,
    generate_password_reset_token,
    decode_email_token,
    VERIFICATION_TOKEN_TYPE,
    PASSWORD_RESET_TOKEN_TYPE,
    TOKEN_ALGORITHM,
    verification_email_template,
    password_reset_email_template,
    _send_mock,
    _send_smtp,
    _build_email_message,
)


# ─── Token Generation Tests ──────────────────────────────────────────

class TestTokenGeneration:
    """Test JWT token generation cho email."""

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_generate_verification_token(self, mock_secret):
        """Token verification được sinh đúng với user_id và email."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token = generate_verification_token(user_id, email)

        assert token is not None
        assert isinstance(token, str)

        # Decode để verify payload
        payload = jwt.decode(token, mock_secret.return_value, algorithms=[TOKEN_ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == VERIFICATION_TOKEN_TYPE
        assert "exp" in payload
        assert "jti" in payload

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_generate_password_reset_token(self, mock_secret):
        """Token password reset được sinh đúng."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token = generate_password_reset_token(user_id, email)

        assert token is not None
        assert isinstance(token, str)

        payload = jwt.decode(token, mock_secret.return_value, algorithms=[TOKEN_ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == PASSWORD_RESET_TOKEN_TYPE

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_verification_token_has_unique_jti(self, mock_secret):
        """Mỗi token có jti duy nhất (single-use)."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token1 = generate_verification_token(user_id, email)
        token2 = generate_verification_token(user_id, email)

        payload1 = jwt.decode(token1, mock_secret.return_value, algorithms=[TOKEN_ALGORITHM])
        payload2 = jwt.decode(token2, mock_secret.return_value, algorithms=[TOKEN_ALGORITHM])

        assert payload1["jti"] != payload2["jti"]

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_token_expiry_verification_is_24h(self, mock_secret):
        """Verification token expire sau 24 giờ."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token = generate_verification_token(user_id, email)
        payload = jwt.decode(token, mock_secret.return_value, algorithms=[TOKEN_ALGORITHM])

        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = exp - now

        # Allow 10s tolerance
        assert diff.total_seconds() == pytest.approx(24 * 3600, abs=10)

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_token_expiry_password_reset_is_1h(self, mock_secret):
        """Password reset token expire sau 1 giờ."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token = generate_password_reset_token(user_id, email)
        payload = jwt.decode(token, mock_secret.return_value, algorithms=[TOKEN_ALGORITHM])

        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = exp - now

        assert diff.total_seconds() == pytest.approx(3600, abs=10)


# ─── Token Validation Tests ──────────────────────────────────────────

class TestTokenValidation:
    """Test decode và validate email token."""

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_decode_verification_token_success(self, mock_secret):
        """Decode verification token thành công."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token = generate_verification_token(user_id, email)
        payload = decode_email_token(token, VERIFICATION_TOKEN_TYPE)

        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == VERIFICATION_TOKEN_TYPE

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_decode_password_reset_token_success(self, mock_secret):
        """Decode password reset token thành công."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token = generate_password_reset_token(user_id, email)
        payload = decode_email_token(token, PASSWORD_RESET_TOKEN_TYPE)

        assert payload["sub"] == user_id
        assert payload["email"] == email

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_decode_wrong_token_type_raises(self, mock_secret):
        """Decode verification token với password_reset type raises ValueError."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        token = generate_verification_token(user_id, email)

        with pytest.raises(ValueError, match="Invalid token type"):
            decode_email_token(token, PASSWORD_RESET_TOKEN_TYPE)

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_decode_expired_token_raises(self, mock_secret):
        """Decode token đã hết hạn raises ValueError."""
        mock_secret.return_value = "test-secret-key"
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "user@example.com"

        # Tạo token đã hết hạn (exp trong quá khứ)
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "type": VERIFICATION_TOKEN_TYPE,
            "jti": "expired-token-id",
        }
        token = jwt.encode(payload, mock_secret.return_value, algorithm=TOKEN_ALGORITHM)

        with pytest.raises(ValueError, match="expired"):
            decode_email_token(token, VERIFICATION_TOKEN_TYPE)

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_decode_invalid_token_raises(self, mock_secret):
        """Decode token với signature sai raises ValueError."""
        mock_secret.return_value = "test-secret-key"

        # Tạo token với secret khác
        wrong_secret = "wrong-secret"
        payload = {
            "sub": "user-id",
            "email": "user@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": VERIFICATION_TOKEN_TYPE,
            "jti": "fake-token",
        }
        token = jwt.encode(payload, wrong_secret, algorithm=TOKEN_ALGORITHM)

        with pytest.raises(ValueError, match="Invalid token"):
            decode_email_token(token, VERIFICATION_TOKEN_TYPE)

    @patch("app.services.email_service._get_email_jwt_secret")
    def test_decode_malformed_token_raises(self, mock_secret):
        """Decode string không phải JWT raises ValueError."""
        mock_secret.return_value = "test-secret-key"

        with pytest.raises(ValueError):
            decode_email_token("not-a-valid-jwt-token", VERIFICATION_TOKEN_TYPE)


# ─── Email Template Tests ────────────────────────────────────────────

class TestEmailTemplates:
    """Test rendering HTML email templates."""

    @patch("app.services.email_service.settings")
    def test_verification_email_template_contains_verify_url(self, mock_settings):
        """Template verification email chứa URL verify."""
        mock_settings.PROJECT_NAME = "AetherTutor"
        mock_settings.FRONTEND_URL = "http://localhost:5173"
        token = "test-verification-token"

        html = verification_email_template(token)

        assert "Verify Your Email" in html
        assert "http://localhost:5173/verify-email?token=test-verification-token" in html
        assert "AetherTutor" in html
        assert "24 hours" in html

    @patch("app.services.email_service.settings")
    def test_password_reset_email_template_contains_reset_url(self, mock_settings):
        """Template password reset email chứa URL reset."""
        mock_settings.PROJECT_NAME = "AetherTutor"
        mock_settings.FRONTEND_URL = "http://localhost:5173"
        token = "test-reset-token"

        html = password_reset_email_template(token)

        assert "Reset Your Password" in html
        assert "http://localhost:5173/reset-password?token=test-reset-token" in html
        assert "AetherTutor" in html
        assert "1 hour" in html

    @patch("app.services.email_service.settings")
    def test_template_contains_branded_header(self, mock_settings):
        """Template chứa header với tên project."""
        mock_settings.PROJECT_NAME = "MyApp"

        html = verification_email_template("token")

        assert "MyApp" in html
        assert "<h1>MyApp</h1>" in html

    @patch("app.services.email_service.settings")
    def test_template_contains_footer(self, mock_settings):
        """Template chứa footer với copyright."""
        mock_settings.PROJECT_NAME = "AetherTutor"

        html = verification_email_template("token")

        assert "All rights reserved" in html
        assert "automated message" in html


# ─── Mock Mode Behavior Tests ────────────────────────────────────────

class TestMockMode:
    """Test mock email sending behavior."""

    def test_send_mock_returns_true(self, caplog):
        """Mock send email luôn trả về True."""
        result = _send_mock("user@example.com", "Test Subject", "<html>body</html>")
        assert result is True

    def test_send_mock_logs_email_details(self, caplog):
        """Mock send email log thông tin email."""
        with caplog.at_level("INFO"):
            _send_mock("user@example.com", "Test Subject", "<html>Hello</html>")

        assert "MOCK EMAIL" in caplog.text
        assert "user@example.com" in caplog.text
        assert "Test Subject" in caplog.text

    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_smtp_success(self, mock_smtp, mock_settings):
        """SMTP send thành công."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user"
        mock_settings.SMTP_PASSWORD = "pass"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = _send_smtp("recipient@example.com", "Test", "<html>body</html>")

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.sendmail.assert_called_once()


# ─── Async Send Tests ────────────────────────────────────────────────

class TestAsyncSendEmail:
    """Test async email dispatch."""

    @pytest.mark.asyncio
    @patch("app.services.email_service._send_mock")
    async def test_send_verification_email_uses_mock(self, mock_send):
        """Send verification email gọi mock khi SMTP chưa config."""
        mock_send.return_value = True

        from app.services.email_service import send_verification_email

        result = await send_verification_email("user@example.com", "token-123")

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email_service._send_mock")
    async def test_send_password_reset_email_uses_mock(self, mock_send):
        """Send password reset email gọi mock khi SMTP chưa config."""
        mock_send.return_value = True

        from app.services.email_service import send_password_reset_email

        result = await send_password_reset_email("user@example.com", "reset-token")

        assert result is True
        mock_send.assert_called_once()


# ─── Build Email Message Tests ───────────────────────────────────────

class TestBuildEmailMessage:
    """Test MIME message building."""

    @patch("app.services.email_service.settings")
    def test_build_email_message_sets_subject(self, mock_settings):
        """MIME message có subject đúng."""
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"

        msg = _build_email_message("user@example.com", "Test Subject", "<html>body</html>")

        assert msg["Subject"] == "Test Subject"
        assert msg["To"] == "user@example.com"

    @patch("app.services.email_service.settings")
    def test_build_email_message_sets_from(self, mock_settings):
        """MIME message có From email đúng."""
        mock_settings.SMTP_FROM_EMAIL = "custom@example.com"

        msg = _build_email_message("user@example.com", "Subject", "<html>body</html>")

        assert msg["From"] == "custom@example.com"

    @patch("app.services.email_service.settings")
    def test_build_email_message_default_from(self, mock_settings):
        """MIME message dùng default From khi không config."""
        mock_settings.SMTP_FROM_EMAIL = None

        msg = _build_email_message("user@example.com", "Subject", "<html>body</html>")

        assert msg["From"] == "noreply@aethertutor.com"

    @patch("app.services.email_service.settings")
    def test_build_email_message_contains_html_body(self, mock_settings):
        """MIME message chứa HTML body."""
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        html_body = "<h1>Hello World</h1>"

        msg = _build_email_message("user@example.com", "Subject", html_body)

        # MIMEText với html subtype
        assert msg.is_multipart()
        payload = msg.get_payload()
        assert isinstance(payload, list)
        assert len(payload) >= 1
