"""
Unit tests cho security utilities: password hashing, JWT, config validation.
"""
from __future__ import annotations

import pytest
from datetime import timedelta, datetime, timezone

from app.services.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_device_info,
)
from app.config import settings, DEFAULT_JWT_SECRET
from app.schemas.auth import RegisterRequest, ChangePasswordRequest, _validate_password


# --- Password Hashing Tests ---

class TestPasswordHashing:
    def test_hash_and_verify(self):
        """Password hash xong thì verify đúng."""
        hashed = hash_password("MyP@ss123")
        assert verify_password("MyP@ss123", hashed)

    def test_wrong_password_fails(self):
        """Password sai thì verify fail."""
        hashed = hash_password("Correct1")
        assert not verify_password("Wrong1", hashed)

    def test_hash_is_bcrypt_format(self):
        """Hash bcrypt bắt đầu bằng $2."""
        hashed = hash_password("Test1234")
        assert hashed.startswith("$2")

    def test_different_hashes_same_password(self):
        """Cùng password nhưng hash khác nhau (do salt ngẫu nhiên)."""
        h1 = hash_password("SamePassword1")
        h2 = hash_password("SamePassword1")
        assert h1 != h2  # salt khác nhau
        # Nhưng cả hai đều verify đúng
        assert verify_password("SamePassword1", h1)
        assert verify_password("SamePassword1", h2)


# --- Password Policy Tests ---

class TestPasswordPolicy:
    def test_valid_password(self):
        """Password đủ điều kiện → không raise."""
        assert _validate_password("SecurePass1") == "SecurePass1"

    def test_too_short(self):
        """Password < 8 ký tự → raise."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            _validate_password("Ab1")

    def test_no_digit(self):
        """Password không có số → raise."""
        with pytest.raises(ValueError, match="at least one letter and one digit"):
            _validate_password("NoDigitsHere")

    def test_no_letter(self):
        """Password không có chữ → raise."""
        with pytest.raises(ValueError, match="at least one letter and one digit"):
            _validate_password("12345678")

    def test_register_request_valid(self):
        """RegisterRequest với password hợp lệ → ok."""
        req = RegisterRequest(
            email="test@example.com",
            password="ValidPass1",
            username="testuser",
        )
        assert req.password == "ValidPass1"

    def test_register_request_invalid(self):
        """RegisterRequest với password yếu → validation error."""
        with pytest.raises(ValueError):
            RegisterRequest(
                email="test@example.com",
                password="weakpass",  # không có số
                username="testuser",
            )

    def test_change_password_valid(self):
        """ChangePasswordRequest với new_password hợp lệ → ok."""
        req = ChangePasswordRequest(
            old_password="OldPass1",
            new_password="NewPass2",
        )
        assert req.new_password == "NewPass2"

    def test_change_password_invalid(self):
        """ChangePasswordRequest với new_password yếu → validation error."""
        with pytest.raises(ValueError):
            ChangePasswordRequest(
                old_password="OldPass1",
                new_password="nonumber",
            )


# --- JWT Token Tests ---

class TestJWT:
    def test_create_and_decode_access_token(self):
        """Tạo access token rồi decode thành công."""
        user_id = "00000000-0000-0000-0000-000000000001"
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        """Tạo refresh token rồi decode thành công."""
        user_id = "00000000-0000-0000-0000-000000000001"
        token = create_refresh_token(user_id)
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """Token fake → raise ValueError."""
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("fake.token.here")

    def test_decode_expired_token_with_leeway(self):
        """
        Token hết hạn nhưng trong leeway window (±30s) → vẫn decode được.
        Tạo token đã hết hạn 10 giây trước → trong leeway 30s nên vẫn hợp lệ.
        """
        user_id = "00000000-0000-0000-0000-000000000001"
        # Tạo token hết hạn 10 giây trước (trong leeway 30s)
        expire = datetime.now(timezone.utc) - timedelta(seconds=10)
        import jwt
        token = jwt.encode(
            {"sub": user_id, "exp": expire, "type": "access"},
            settings.JWT_SECRET_KEY,
            algorithm="HS256",
        )
        # Trong leeway → decode thành công
        payload = decode_token(token)
        assert payload["sub"] == user_id

    def test_decode_expired_token_outside_leeway(self):
        """Token hết hạn ngoài leeway window → raise ValueError."""
        user_id = "00000000-0000-0000-0000-000000000001"
        # Tạo token hết hạn 60 giây trước (ngoài leeway 30s)
        expire = datetime.now(timezone.utc) - timedelta(seconds=60)
        import jwt
        token = jwt.encode(
            {"sub": user_id, "exp": expire, "type": "access"},
            settings.JWT_SECRET_KEY,
            algorithm="HS256",
        )
        with pytest.raises(ValueError, match="expired"):
            decode_token(token)

    def test_custom_expiry(self):
        """Token với expiry tùy chỉnh."""
        user_id = "00000000-0000-0000-0000-000000000001"
        token = create_access_token(user_id, expires_delta=timedelta(minutes=5))
        payload = decode_token(token)
        assert payload["sub"] == user_id


# --- Config Validation Tests ---

class TestConfigSecurity:
    def test_weak_jwt_secret_detection(self):
        """Phát hiện JWT secret mặc định."""
        # Trong test env, default secret thường được dùng
        # Test này kiểm tra property hoạt động đúng
        original = settings.JWT_SECRET_KEY
        try:
            settings.JWT_SECRET_KEY = DEFAULT_JWT_SECRET
            assert settings.is_weak_jwt_secret

            settings.JWT_SECRET_KEY = "a-much-stronger-secret!"
            assert not settings.is_weak_jwt_secret
        finally:
            settings.JWT_SECRET_KEY = original

    def test_default_secret_constant_exists(self):
        """DEFAULT_JWT_SECRET phải tồn tại và không rỗng."""
        assert DEFAULT_JWT_SECRET
        assert len(DEFAULT_JWT_SECRET) > 10


# --- Device Info Hashing Tests ---

class TestDeviceInfoHashing:
    def test_hash_device_info(self):
        """Hash device info trả về SHA-256 hex string."""
        result = hash_device_info("Mozilla/5.0", "127.0.0.1")
        assert len(result) == 64  # SHA-256 = 64 hex chars
        assert all(c in "0123456789abcdef" for c in result)

    def test_device_hash_deterministic(self):
        """Cùng device info → cùng hash."""
        h1 = hash_device_info("Mozilla/5.0", "127.0.0.1")
        h2 = hash_device_info("Mozilla/5.0", "127.0.0.1")
        assert h1 == h2

    def test_device_hash_different_for_different_inputs(self):
        """Khác device info → khác hash."""
        h1 = hash_device_info("Mozilla/5.0", "127.0.0.1")
        h2 = hash_device_info("Chrome/100", "192.168.1.1")
        assert h1 != h2

    def test_device_hash_with_none_values(self):
        """None values được xử lý an toàn."""
        result = hash_device_info(None, None)
        assert len(result) == 64
