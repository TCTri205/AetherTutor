# Security & Privacy Policy

> **Document Owner:** AetherTutor Team
> **Created:** April 12, 2026
> **Version:** 2.0
> **Status:** Active
> **Parent:** [Contributing.md](../Contributing.md)

---

## 1. Tổng Quan

AetherTutor được thiết kế với **nguyên tắc bảo mật từ gốc** (security by design). Tài liệu này mô tả các biện pháp bảo mật đã được implement và roadmap cho các tính năng tương lai.

**Triết lý cốt lõi:**
> **Local-First Privacy** — User có thể chạy toàn bộ hệ thống cục bộ (Ollama + local DB), KHÔNG dữ liệu nào rời khỏi máy.

---

## 2. Data Encryption

### 2.1 At Rest (Đã Implement)

| Component | Method | Status |
|-----------|--------|--------|
| **Passwords** | `bcrypt` với configurable rounds (default: 12) | ✅ Implemented |
| **JWT Tokens** | HMAC-SHA256 (HS256) với secret key | ✅ Implemented |
| **Device Info** | SHA-256 hash trước khi lưu (tránh lưu raw PII) | ✅ Implemented |
| **Database** | PostgreSQL native encryption (tùy OS/file system) | ⚠️ OS-level |
| **File Uploads** | Local filesystem (chưa encrypt) | ❌ Not implemented |
| **ChromaDB** | Local storage (chưa encrypt) | ❌ Not implemented |

**Implementation:**
```python
# app/services/security.py
import bcrypt
import hashlib

def hash_password(password: str) -> str:
    """Hash password với bcrypt, rounds từ settings."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)  # Default: 12
    ).decode("utf-8")

def hash_device_info(user_agent: str | None, ip_address: str | None) -> str:
    """SHA-256 hash device info để tránh lưu raw PII."""
    raw = f"{user_agent or ''}|{ip_address or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

### 2.2 In Transit (Production Required)

| Component | Method | Status |
|-----------|--------|--------|
| **API (HTTP)** | TLS 1.3 (qua reverse proxy: Nginx/Traefik) | ✅ Production-ready |
| **WebSocket** | WSS (WebSocket Secure) | ✅ Production-ready |
| **PostgreSQL** | SSL mode (sslmode=require) | ⚠️ Configurable |
| **Redis** | TLS (arq redis_settings support SSL) | ⚠️ Configurable |
| **OpenAI API** | HTTPS (built-in) | ✅ Always encrypted |
| **Ollama** | HTTP local only (127.0.0.1) | ✅ Local-only, no TLS needed |

> [!WARNING]
> **Development mode** chạy HTTP plain-text. CHỈ dùng cho local development.
> Production BẮT BUỘC phải có TLS termination qua reverse proxy.

---

## 3. Authentication & Authorization

### 3.1 Authentication (✅ Implemented)

| Feature | Status | Details |
|---------|--------|---------|
| **Email/Password Login** | ✅ | Bcrypt hashed passwords |
| **JWT Access Token** | ✅ | 30 phút expiry, HS256 signed |
| **JWT Refresh Token** | ✅ | 7 ngày expiry, token rotation |
| **Multi-Device Sessions** | ✅ | Mỗi device có refresh_token riêng |
| **Token Rotation** | ✅ | Refresh → revoke old, create new |
| **Logout (Single Device)** | ✅ | Soft delete session (giữ audit trail) |
| **Logout All Devices** | ✅ | Revoke tất cả sessions |
| **Email Verification** | ✅ | JWT token, 24h expiry |
| **Password Reset** | ✅ | JWT token, 1h expiry, single-use |
| **Session Cleanup** | ✅ | Cron job daily 2AM, xóa sessions >30 ngày |

**Authentication Flow:**
```
┌──────────┐     POST /auth/login      ┌──────────┐
│  Client  │ ───────────────────────>  │   API    │
│          │                           │          │
│          │  ← access_token (30min)   │          │
│          │  ← refresh_token (7 days) │          │
│          │  ← session_id             │          │
└──────────┘                           └──────────┘
     │                                       │
     │  POST /auth/refresh                   │
     │  (rotation: revoke old → new)         │
     │ ──────────────────────────────────>   │
     │                                       │
     │  POST /auth/logout                    │
     │  (soft delete: is_revoked = true)     │
     │ ──────────────────────────────────>   │
```

**Token Payload:**
```python
# Access Token
{
    "sub": "user-uuid",
    "type": "access",
    "exp": 1712934000  # 30 minutes
}

# Refresh Token
{
    "sub": "user-uuid",
    "type": "refresh",
    "exp": 1713538800  # 7 days
}

# Clock Skew Tolerance: ±30 giây
jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"], leeway=30)
```

### 3.2 Authorization (✅ MVP — Data Isolation)

| Feature | Status | Implementation |
|---------|--------|----------------|
| **User Data Isolation (BR-001)** | ✅ | Mọi query filter `WHERE user_id = :current_user_id` |
| **JWT Middleware** | ✅ | `get_current_user_id()` dependency injection |
| **Row-Level Security** | ⚠️ Prepared | SQL policies defined but not enforced in MVP |
| **Role-Based Access Control (RBAC)** | ❌ Post-MVP | Admin/Enterprise roles planned |

**Dependency Injection Pattern:**
```python
# app/api/dependencies.py
async def get_current_user_id(
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, deprecated=True)
) -> uuid.UUID:
    """
    Extract user_id từ JWT Bearer token.

    Priority:
    1. JWT Bearer token (production)
    2. X-User-Id header (dev only — deprecated)
    3. Default user (dev fallback)
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        payload = decode_token(token)
        return uuid.UUID(payload["sub"])

    # Dev fallback (remove in production)
    if x_user_id:
        return uuid.UUID(x_user_id)

    return DEFAULT_USER_ID  # 00000000-0000-0000-0000-000000000001
```

### 3.3 Rate Limiting (✅ Implemented)

| Endpoint | Limit | Window | Implementation |
|----------|-------|--------|----------------|
| Document Upload | 5 requests | 24h rolling | `slowapi` với Redis backend |
| Chat (SSE Stream) | 10 requests | 60s sliding | Per-IP rate limiting |
| Graph Queries | 30 requests | 60s sliding | Per-IP rate limiting |
| Flashcard Generation | 10 requests | 24h rolling | Per-user rate limiting |
| Quiz Generation | 5 requests | 24h rolling | Per-user rate limiting |
| Auth (Login/Register) | 10 requests | 60s sliding | Anti-brute-force |
| Password Reset | 10 requests | 60s sliding | Anti-enumeration |

**Implementation:**
```python
# app/api/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_client_ip(request: Request) -> str:
    """Lấy IP thực từ X-Forwarded-For (qua reverse proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

limiter = Limiter(key_func=get_client_ip)
```

---

## 4. Input Validation & Injection Prevention

### 4.1 SQL Injection (✅ Protected)

- **SQLAlchemy 2.0** với parameterized queries — KHÔNG có string concatenation
- **Type-safe queries:** `select(User).where(User.email == email)`

```python
# ✅ SAFE — Parameterized query
result = await session.execute(
    select(User).where(User.email == email)
)

# ❌ DANGEROUS — Never do this
result = await session.execute(
    text(f"SELECT * FROM users WHERE email = '{email}'")
)
```

### 4.2 Prompt Injection (⚠️ Partial)

| Measure | Status | Description |
|---------|--------|-------------|
| **System Prompt Hardening** | ✅ | System prompt luôn đứng đầu trong messages list |
| **User Input Sanitization** | ❌ Not implemented | Chưa filter special characters từ user input |
| **Context Truncation** | ✅ | Chat history bị truncate nếu vượt token limit |
| **Output Validation** | ⚠️ Partial | Structured output parsing với retry, nhưng chưa validate content |

**System Prompt Pattern:**
```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},  # LUÔN đứng đầu
    *chat_history,                                   # User messages
    {"role": "user", "content": user_input}          # Latest input
]
```

### 4.3 File Upload Validation (✅ Implemented)

| Check | Rule | Error |
|-------|------|-------|
| File Size | ≤ 50MB | 400 Bad Request |
| File Type | PDF, code extensions only | 400 Bad Request |
| Content Hash | SHA-256 duplicate check | 409 Conflict |
| Text Layer | PDF phải có text layer | 400 Bad Request |
| Concurrent Processing | Max 1 document đang processing | 409 Conflict |

---

## 5. Privacy Compliance

### 5.1 Data Erasure (✅ Implemented)

| Feature | Status | Implementation |
|---------|--------|----------------|
| **Document Deletion** | ✅ | Cascade delete: doc → chunks → entities → relations → ChromaDB |
| **Account Deletion** | ⚠️ Partial | CASCADE trên FKs, nhưng chưa có dedicated endpoint |
| **Session Revocation** | ✅ | Soft delete (giữ audit trail) |
| **Chat History Deletion** | ✅ | Delete conversation → cascade messages |

**Atomic Document Deletion (UF-010):**
```python
async def delete_document(user_id: uuid.UUID, doc_id: uuid.UUID) -> bool:
    """Xóa document + toàn bộ dữ liệu liên quan."""
    # 1. Delete from graph repository
    await graph_repo.delete_by_document_id(doc_id)

    # 2. Delete from ChromaDB (all collections — BR-008)
    await chroma_client.delete_by_document_id(str(doc_id))

    # 3. Delete from PostgreSQL (cascade handles chunks, entities, relations)
    doc = await doc_repo.get_by_id_with_user_check(doc_id, user_id)
    if not doc:
        return False
    await doc_repo.delete(doc_id)

    return True
```

### 5.2 Data Portability (❌ Post-MVP)

| Feature | Status | Notes |
|---------|--------|-------|
| **Export Documents** | ❌ | Planned: Download PDFs + metadata |
| **Export Notes** | ❌ | Planned: Markdown export (Obsidian-compatible) |
| **Export Flashcards** | ❌ | Planned: CSV/Anki export |
| **Export Quiz History** | ❌ | Planned: JSON export |
| **Export Knowledge Graph** | ✅ | GraphML/JSON export qua `GET /graph/{id}/export` |

### 5.3 Local-First Privacy (✅ Core Feature)

**Local Mode Configuration:**
```env
# .env — Local Mode (Zero Data Leakage)
OLLAMA_BASE_URL=http://localhost:11434/v1
EMBEDDING_PROVIDER=ollama
DEFAULT_LLM_MODEL=qwen2.5-1.5b
OPENAI_API_KEY=  # KHÔNG dùng

# Kết quả: KHÔNG dữ liệu nào gửi ra ngoài
```

**BR-008 Enforcement:**
```
IF local_mode = true
THEN:
    - TẤT CẢ LLM requests → Ollama (localhost)
    - KHÔNG gọi OpenAI API
    - Log warning nếu có attempt gọi Cloud API
    - Hiển thị badge "🔒 Local Mode" trên UI
```

---

## 6. Infrastructure Security

### 6.1 Environment Variables (Secrets Management)

| Variable | Sensitivity | Storage |
|----------|-------------|---------|
| `OPENAI_API_KEY` | 🔴 CRITICAL | `.env` (gitignored), Docker secrets (production) |
| `JWT_SECRET_KEY` | 🔴 CRITICAL | `.env` (gitignored), MUST be strong random string |
| `DATABASE_PASSWORD` | 🟡 HIGH | `.env` (gitignored), Docker secrets (production) |
| `SMTP_PASSWORD` | 🟡 HIGH | `.env` (gitignored) |
| `VAPID_PRIVATE_KEY` | 🟡 HIGH | `.env` (gitignored) |
| `REDIS_PASSWORD` | 🟢 LOW | `.env` (gitignored) |

**Rules:**
- ❌ KHÔNG bao giờ commit secrets vào git
- ❌ KHÔNG log API keys hoặc tokens
- ✅ Sử dụng `.env.example` làm template (không có giá trị thực)
- ✅ Production: Dùng Docker secrets hoặc vault

### 6.2 Docker Security

| Practice | Status | Description |
|----------|--------|-------------|
| **Multi-stage builds** | ✅ | Reduce image size, loại bỏ build tools |
| **Non-root user** | ✅ | Container chạy với user không root |
| **Minimal base image** | ✅ | Python slim image |
| **No secrets in image** | ✅ | Secrets inject qua `.env` hoặc Docker secrets |
| **Port exposure** | ⚠️ Partial | Chỉ expose ports cần thiết (8000 backend, 80 frontend) |

### 6.3 CORS Configuration

```python
# app/main.py — Production-ready CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Configurable qua .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Development:**
```env
CORS_ORIGINS=http://localhost:5173,http://localhost:8000
```

**Production:**
```env
CORS_ORIGINS=https://yourdomain.com
```

---

## 7. Security Audit Checklist

### 7.1 Pre-Deployment

- [ ] `JWT_SECRET_KEY` là strong random string (≥32 chars)
- [ ] `OPENAI_API_KEY` hợp lệ (nếu dùng cloud mode)
- [ ] CORS origins cấu hình đúng domain production
- [ ] Rate limiting enabled
- [ ] Debug mode OFF (`APP_ENV=production`)
- [ ] Logging không chứa sensitive data
- [ ] Database password không phải default
- [ ] Redis password configured (nếu có)

### 7.2 Post-Deployment

- [ ] TLS certificate valid
- [ ] Security headers configured (HSTS, CSP, X-Frame-Options)
- [ ] Regular dependency audit (`pip-audit`, `npm audit`)
- [ ] Monitor failed login attempts
- [ ] Review access logs định kỳ
- [ ] Backup encryption verified

### 7.3 Ongoing

- [ ] Update dependencies monthly
- [ ] Review rate limiting thresholds
- [ ] Test data deletion flows
- [ ] Audit session cleanup cron job
- [ ] Penetration testing (quarterly)

---

## 8. Known Security Limitations (MVP)

| Issue | Risk Level | Workaround | Planned Fix |
|-------|-----------|------------|-------------|
| **Default user ID** (MVP single-user) | 🟡 Medium | Chỉ dùng cho local dev | Auth system (đã implement, chưa enforce) |
| **Dev header auth** (`X-User-Id`) | 🟡 Medium | Deprecated, chỉ dùng trong testing | Remove trong production |
| **No CSRF protection** | 🟢 Low | API-only (no browser cookies) | Add CSRF tokens nếu thêm session cookies |
| **No input sanitization** | 🟡 Medium | LLM system prompt giúp giảm risk | Implement input filtering |
| **File uploads unencrypted** | 🟢 Low | Local storage only | Encrypt at rest (Post-MVP) |

---

## 9. Incident Response Plan

### 9.1 Data Breach Response

```
1. DETECT → Monitor logs, alerts
2. CONTAIN → Revoke affected tokens, block IPs
3. ASSESS → Determine scope, affected users
4. NOTIFY → Email affected users within 72h (GDPR)
5. REMEDIATE → Patch vulnerability, rotate secrets
6. REVIEW → Post-incident analysis, update policies
```

### 9.2 Contact

| Role | Contact |
|------|---------|
| Security Team | security@aethertutor.com (planned) |
| Data Protection Officer | dpo@aethertutor.com (planned) |

---

## 10. Compliance Roadmap

| Standard | Status | Notes |
|----------|--------|-------|
| **GDPR** | ⚠️ Partial | Data erasure ✅, portability ❌, consent ❌ |
| **CCPA** | ⚠️ Partial | Data deletion ✅, opt-out ❌ |
| **SOC 2** | ❌ Not started | Post-MVP requirement |
| **ISO 27001** | ❌ Not started | Enterprise requirement |

---

## 11. Quick Reference

| Resource | Link |
|----------|------|
| Business Rules (BR-001, BR-008, BR-016) | `srs/Business_Rules.md` |
| Auth Service | `app/services/auth_service.py` |
| Security Module | `app/services/security.py` |
| Rate Limiter | `app/api/limiter.py` |
| CORS Config | `app/main.py` |
| Environment Template | `.env.example` |
| Docker Compose | `docker-compose.yml` |

---
© 2026 AetherTutor Team. Last updated: April 12, 2026