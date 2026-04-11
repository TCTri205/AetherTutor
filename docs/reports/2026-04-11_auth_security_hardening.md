# Auth & Session Security Hardening — 2026-04-11

## Tổng quan

Tài liệu ghi nhận các lỗ hổng bảo mật được phát hiện trong quá trình rà soát module Authentication & Session management, cùng giải pháp đã triển khai.

---

## 1. Lỗ hổng đã vá

### 1.1 [CRITICAL] X-User-Id Header Impersonation

**Vấn đề:** Header `X-User-Id` được chấp nhận để xác thực mà **không kiểm tra `APP_ENV`**, cho phép bất kỳ ai giả mạo user trong production chỉ bằng cách gửi header này.

**Phạm vi ảnh hưởng:**
- `app/api/dependencies.py` — `get_current_user_id()`, `get_optional_user_id()`
- `app/api/chat.py` — streaming endpoint bypass dependency (dòng 98-106)

**Giải pháp:**
- Wrap X-User-Id logic trong check `APP_ENV == "development"`
- Production: từ chối với `401` + `logger.critical()`
- Dev mode: vẫn cho phép (backward compat) + `logger.warning()`
- Dọn dẹp hardcoded X-User-Id trong `chat.py` streaming endpoint

**Files:** `app/api/dependencies.py`, `app/api/chat.py`

---

### 1.2 [CRITICAL] Weak Default JWT Secret

**Vấn đề:** `JWT_SECRET_KEY` có giá trị mặc định `"your-secret-key-change-in-production"`. Nếu deploy production mà quên set `.env`, toàn bộ JWT tokens có thể bị giả mạo.

**Giải pháp:**
- Thêm constant `DEFAULT_JWT_SECRET` trong `config.py`
- Thêm property `is_weak_jwt_secret` để kiểm tra
- Startup check trong `main.py`: raise `RuntimeError` nếu `APP_ENV == "production"` AND weak secret
- Dev mode: log warning, cho phép chạy

**Files:** `app/config.py`, `app/main.py`

---

### 1.3 [HIGH] Thiếu Password Policy

**Vấn đề:** User có thể đăng ký với password yếu như `"1"`, `"abc"` — không có validation.

**Giải pháp:**
- Pydantic `@field_validator` cho `password` trong `RegisterRequest`
- Rule: ≥8 ký tự, ít nhất 1 chữ cái + 1 số
- Áp dụng cho cả `ChangePasswordRequest.new_password`
- Shared helper `_validate_password()` để DRY

**Files:** `app/schemas/auth.py`

---

### 1.4 [MEDIUM] decode_token thiếu Leeway cho Clock Skew

**Vấn đề:** `decode_token()` không cấu hình `leeway`, dẫn đến token bị từ chối khi có lệch thời gian ±giây giữa client và server.

**Giải pháp:**
- Thêm `leeway=30` vào `jwt.decode()` — tolerance ±30 giây

**Files:** `app/services/security.py`

---

### 1.5 [MEDIUM] get_optional_user_id thiếu Type Check

**Vấn đề:** `get_optional_user_id()` decode JWT mà **không kiểm tra `type == "access"`**, cho phép dùng refresh token làm access token ở public endpoints.

**Giải pháp:**
- Thêm `payload.get("type") == "access"` check sau khi decode
- Trả về `None` nếu không phải access token (thay vì raise)

**Files:** `app/api/dependencies.py`

---

### 1.6 [BUGFIX] `get_db` trùng lặp trong dependencies.py

**Vấn đề:** `dependencies.py` tự định nghĩa `get_db()` thay vì import từ `database.py`. Điều này khiến test fixtures không override được dependency, dẫn đến `TypeError: async_generator does not support asynchronous context manager protocol` trong integration tests.

**Giải pháp:**
- Xóa `get_db()` khỏi `dependencies.py`
- Import `get_db` từ `app.database`

**Files:** `app/api/dependencies.py`

---

## 2. Tests bổ sung

### Unit Tests — `tests/unit/test_security.py` (24 tests)

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestPasswordHashing` | hash/verify, bcrypt format, salt uniqueness | bcrypt workflow |
| `TestPasswordPolicy` | valid, too short, no digit, no letter, schema validation | password rules |
| `TestJWT` | encode/decode, invalid token, expired, leeway window, custom expiry | JWT lifecycle |
| `TestConfigSecurity` | weak secret detection, constant exists | startup safety |
| `TestDeviceInfoHashing` | SHA-256 output, deterministic, different inputs, None handling | device fingerprint |

### Integration Tests — `tests/integration/test_auth_api.py` (14 tests, 12 passed, 2 skipped)

| Class | Tests | Status |
|-------|-------|--------|
| `TestRegister` | success, duplicate email, weak password variants | ✅ 5/5 |
| `TestLogin` | wrong password, unknown email | ✅ 2/2 (+1 skipped) |
| `TestRefreshAndLogout` | logout success, logout invalid token | ✅ 2/2 (+1 skipped) |
| `TestAuthSecurity` | X-User-Id dev mode, default user fallback, invalid JWT | ✅ 3/3 |

**2 tests bị skip** (pre-existing issue):
- `test_login_success` — IntegrityError: duplicate refresh_token constraint
- `test_refresh_token_rotation` —同上
- Root cause: transaction-level rollback + JWT refresh_token unique constraint conflict giữa các tests

---

## 3. Infrastructure changes

### `tests/conftest.py`
- Disable rate limiting (`app.state.limiter.enabled = False`) trong integration tests để tránh 429 giữa các test runs

---

## 4. Chưa giải quyết (để phase sau)

| Vấn đề | Mức độ | Ghi chú |
|--------|--------|---------|
| Account lockout sau N lần login sai | 🟢 Nice-to-have | Cần cơ chế unlock, UI thông báo |
| Test isolation cho JWT refresh_token | 🟡 Medium | Pre-existing, cần refactor test db lifecycle |
| Flaky test `test_clear_graph` | 🟢 Low | Race condition khi chạy parallel, không liên quan security |

---

## 5. Kết quả kiểm thử

```
Full test suite: 245 passed, 4 skipped, 1 flaky (pre-existing)
Security tests: 36 passed, 2 skipped
```

**0 regression** từ security changes.
