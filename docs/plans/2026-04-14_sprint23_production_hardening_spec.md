# Sprint 23: Production Hardening & GDPR Compliance — Detailed Specification

> **Priority:** 🔴 P0 | **Sprint:** 23 | **Dependency:** Sprint 22 (tests passing)
> **Estimate:** ~48 giờ (~1.5 tuần)
> **Goal:** Bảo mật, compliance, monitoring — required cho production launch

---

## 📋 Tổng quan

Sprint 23 tập trung vào việc hardening hệ thống cho production, bao gồm:
1. **Rate Limiting** — Upgrade từ 12% → 100% coverage, Redis-backed
2. **Security Audit** — IDOR, XSS, CSRF, penetration testing
3. **GDPR/CCPA Compliance** — Data export, account deletion, anonymization
4. **Backup & Recovery** — Database backup scripts, restore procedures
5. **Monitoring & Health Checks** — Prometheus metrics, Kubernetes probes

---

## 🗺️ Tasks Chi Tiết

### Part A: Rate Limiting & Security (7 tasks, ~24 giờ)

> **Estimate:** ~24 giờ

#### Task 23.1.1: Upgrade Rate Limiting to Redis Backend

**Vấn đề hiện tại:**

File `app/api/limiter.py` đang dùng **in-memory storage** (slowapi default):

```python
# CURRENT (IN-MEMORY — KHÔNG HOẠT ĐỘNG VỚI MULTI-WORKER)
from slowapi import Limiter

limiter = Limiter(key_func=get_client_ip)
```

**Giải pháp:** Upgrade lên `RedisStorage` để sync rate limits across workers.

**Implementation:**

```python
# app/api/limiter.py — UPDATED

from slowapi import Limiter
from slowapi.storage import RedisStorage
from app.config import settings

def get_client_ip(request) -> str:
    """Extract real client IP from X-Forwarded-For header."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host or "unknown"

# Redis-backed rate limiter (syncs across workers)
redis_storage = RedisStorage(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=1,  # Separate DB from cache/queue
    password=settings.REDIS_PASSWORD or None,
)

limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
)
```

**Dependencies:**

```txt
# requirements.txt (nếu chưa có)
slowapi[redis]>=0.5.0
```

**Testing:**

- Deploy 2+ workers, verify rate limit sync across workers
- Test rate limit consistency: 10 requests from IP → all workers count toward same limit

#### Task 23.1.2: Apply 23 Rate Limit Recommendations

Dựa theo `docs/ops/rate_limiting_audit.md`, áp dụng rate limits cho 90+ unprotected endpoints.

**Phase 1: Critical Security Fixes (8 endpoints)**

| Endpoint | Rate Limit | Constant | Lý do |
|----------|-----------|----------|-------|
| `/auth/logout-all` | 10/min | `RATE_LIMIT_LOGOUT_ALL` | Brute-force risk |
| `/auth/sessions` | 30/min | `RATE_LIMIT_SESSIONS` | Session enumeration |
| `/chat/multi-doc` | 30/min | `RATE_LIMIT_CHAT_MULTI_DOC` | LLM-intensive |
| `/chat/socratic` | 30/min | `RATE_LIMIT_SOCRATIC` | Legacy LLM |
| `/quiz/generate` | 10/min | `RATE_LIMIT_QUIZ_GENERATE` | LLM-intensive |
| `/flashcards/generate` | 20/min | `RATE_LIMIT_FLASHCARD_GENERATE` | LLM-intensive |
| `/notes/suggest-backlinks` | 15/min | `RATE_LIMIT_NOTE_SUGGEST` | LLM-intensive |
| `/graph/query-multi` | 30/min | `RATE_LIMIT_GRAPH_MULTI` | LLM-intensive |

**Phase 2: Full Coverage (82 endpoints)**

Xem `rate_limiting_audit.md` Section 3.1 cho đầy đủ limits theo category.

**Implementation Pattern:**

```python
# app/constants.py — Thêm constants mới

RATE_LIMIT_LOGOUT_ALL = "10/minute"
RATE_LIMIT_SESSIONS = "30/minute"
RATE_LIMIT_CHAT_MULTI_DOC = "30/minute"
RATE_LIMIT_QUIZ_GENERATE = "10/minute"
RATE_LIMIT_FLASHCARD_GENERATE = "20/minute"
# ... (xem Section 3.3 trong audit doc)

# app/api/quiz.py — Apply decorator
from app.constants import RATE_LIMIT_QUIZ_GENERATE

@router.post("/generate/{document_id}")
@limiter.limit(RATE_LIMIT_QUIZ_GENERATE)
async def generate_quiz(...):
    pass
```

#### Task 23.1.3: Rate Limiting Bypass for Premium Users

**Requirement:** Premium users có rate limits cao hơn free users.

**Implementation:**

```python
# app/middleware/premium_rate_limiter.py

from fastapi import Request
from app.models.user import User
from app.services.user_service import get_user_by_id

async def get_premium_rate_limit(request: Request) -> str:
    """Return higher rate limits for premium users."""
    # Extract user_id from JWT
    token = request.query_params.get("token") or request.headers.get("Authorization", "").split(" ")[-1]
    if not token:
        return "default"  # Use default limits
    
    try:
        payload = decode_token(token)
        user = await get_user_by_id(payload["sub"])
        if user and user.is_premium:
            return "premium"  # Use premium limits
    except:
        pass
    
    return "default"

# Apply via custom decorator that checks user tier
```

**Alternative:** Use role-based rate limit keys in Redis:
- `rate_limit:default:ip:1.2.3.4`
- `rate_limit:premium:ip:1.2.3.4`

#### Task 23.1.4: Security Audit — IDOR Check

**Scope:** Audit toàn bộ endpoints để đảm bảo user chỉ truy cập resource của mình.

**Endpoints cần audit:**

| Endpoint | Risk | Test |
|----------|------|------|
| `/documents/{id}` | User A accesses User B's document | Try accessing doc with different user_id |
| `/graph/entities/{id}` | User A edits User B's entity | Try updating entity with different user_id |
| `/notes/{id}` | User A reads User B's note | Try reading note with different user_id |
| `/flashcards/{id}` | User A reviews User B's flashcard | Try reviewing with different user_id |
| `/quiz/{id}` | User A submits User B's quiz | Try submitting with different user_id |
| `/collaboration/teams/{id}` | User A accesses User B's team | Try accessing team not member of |

**Implementation:**

```python
# Test script: tests/integration/test_idor_audit.py

@pytest.mark.asyncio
async def test_idor_document_access(async_client):
    """User A cannot access User B's document."""
    # Create User A with document
    user_a_token, doc_id = create_user_and_document()
    
    # Create User B
    user_b_token = create_user()
    
    # User B tries to access User A's document
    response = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {user_b_token}"}
    )
    
    assert response.status_code == 404  # Or 403, NOT 200
```

#### Task 23.1.5: Security Audit — XSS Prevention

**Scope:** Sanitize user input trên frontend, CSP headers, DOMPurify cho Markdown.

**Tasks:**

1. **Backend: Add Content-Security-Policy headers**

```python
# app/main.py — Add security headers middleware

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: wss:; "
        "font-src 'self';"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

2. **Frontend: Add DOMPurify for Markdown rendering**

```bash
npm install dompurify
npm install --save-dev @types/dompurify
```

```typescript
// frontend/src/utils/sanitize.ts
import DOMPurify from 'dompurify';

export function sanitizeHtml(html: string): string {
    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'a', 'code', 'pre', 'ul', 'ol', 'li', 'h1', 'h2', 'h3'],
        ALLOWED_ATTR: ['href', 'target', 'rel'],
    });
}
```

3. **Frontend: Apply sanitization to all Markdown renderers**

```typescript
// In Zettelkasten.tsx, Chat.tsx, etc.
import { sanitizeHtml } from '../utils/sanitize';

// Before: <div dangerouslySetInnerHTML={{ __html: markdownHtml }} />
// After:
<div dangerouslySetInnerHTML={{ __html: sanitizeHtml(markdownHtml) }} />
```

#### Task 23.1.6: Security Audit — CSRF Protection

**Scope:** CORS production config, CSRF tokens for state-changing requests.

**Implementation:**

```python
# app/main.py — CORS config for production

from fastapi.middleware.cors import CORSMiddleware

if settings.APP_ENV == "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],  # Specific origin, NOT *
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        max_age=600,  # Cache preflight for 10 minutes
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

#### Task 23.1.7: Penetration Testing

**Tool:** OWASP ZAP hoặc manual pentest.

**Checklist:**

| Test | Tool | Expected Result |
|------|------|----------------|
| SQL Injection | OWASP ZAP | No injection possible (SQLAlchemy parameterized) |
| XSS | Manual | DOMPurify sanitizes, CSP headers block |
| CSRF | Manual | CORS restricted, SameSite cookies |
| IDOR | Manual | user_id filter on all endpoints |
| Rate Limit Bypass | Manual | Redis-backed, per-IP + per-user |
| JWT Forgery | Manual | HS256 with strong secret key |
| File Upload | Manual | Type validation, size limits, no execution |
| WebSocket Hijacking | Manual | JWT authentication required |

---

### Part B: GDPR/CCPA Compliance (5 tasks, ~16 giờ)

> **Estimate:** ~16 giờ

#### Task 23.2.1: PII Anonymization Middleware

**Requirement:** Mask PII (email, name, IP) trong logs, hash user_id trong analytics.

**Implementation:**

```python
# app/middleware/pii_anonymizer.py

import re
from loguru import logger

class PIIAnonymizer:
    """Anonymize PII in log messages."""
    
    EMAIL_PATTERN = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    
    @staticmethod
    def anonymize_email(text: str) -> str:
        """Replace emails with ***@***.***"""
        return PIIAnonymizer.EMAIL_PATTERN.sub('***@***.***', text)
    
    @staticmethod
    def anonymize_ip(text: str) -> str:
        """Replace IPs with ***.***.***.***"""
        return PIIAnonymizer.IP_PATTERN.sub('***.***.***.***', text)
    
    @staticmethod
    def anonymize(text: str) -> str:
        """Anonymize all PII in text."""
        text = PIIAnonymizer.anonymize_email(text)
        text = PIIAnonymizer.anonymize_ip(text)
        return text

# Usage in logging:
# logger.info(f"User login: {PIIAnonymizer.anonymize(email)}")
```

**Analytics Hashing:**

```python
# app/services/analytics.py

import hashlib

def hash_user_id(user_id: str) -> str:
    """Hash user_id for analytics (one-way, non-reversible)."""
    return hashlib.sha256(f"{user_id}:{settings.ANALYTICS_SALT}").hexdigest()[:16]
```

#### Task 23.2.2: Data Export (ZIP Download)

**Endpoint:** `POST /api/v1/users/export`

**Implementation:**

```python
# app/services/gdpr_export.py

import zipfile
import io
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Document, Note, Flashcard, Quiz, Conversation, GraphEntity

async def export_user_data(user_id: str, db: AsyncSession) -> bytes:
    """Export all user data as ZIP file."""
    
    # Fetch all user data
    documents = await get_user_documents(user_id, db)
    notes = await get_user_notes(user_id, db)
    flashcards = await get_user_flashcards(user_id, db)
    quizzes = await get_user_quizzes(user_id, db)
    conversations = await get_user_conversations(user_id, db)
    graph_entities = await get_user_graph_entities(user_id, db)
    
    # Create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('documents.json', json.dumps([doc.to_dict() for doc in documents], indent=2))
        zf.writestr('notes.json', json.dumps([note.to_dict() for note in notes], indent=2))
        zf.writestr('flashcards.json', json.dumps([fc.to_dict() for fc in flashcards], indent=2))
        zf.writestr('quizzes.json', json.dumps([q.to_dict() for q in quizzes], indent=2))
        zf.writestr('conversations.json', json.dumps([conv.to_dict() for conv in conversations], indent=2))
        zf.writestr('graph_entities.json', json.dumps([e.to_dict() for e in graph_entities], indent=2))
        zf.writestr('README.txt', 'AetherTutor Data Export\nGenerated on: {date}\nTotal files: 6')
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
```

**API Endpoint:**

```python
# app/api/users.py

from fastapi.responses import StreamingResponse

@router.post("/users/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data as ZIP file (GDPR Article 20)."""
    zip_bytes = await export_user_data(str(current_user.id), db)
    
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=aethertutor_export_{datetime.now().strftime('%Y%m%d')}.zip"
        }
    )
```

#### Task 23.2.3: Account Deletion Flow

**Requirement:** 2-step verification, soft delete 30 ngày → hard delete.

**Implementation:**

```python
# app/services/account_deletion.py

from datetime import datetime, timedelta
from app.models.user import User, AccountStatus

async def request_deletion(user_id: str, db: AsyncSession) -> dict:
    """Step 1: Request account deletion (sends confirmation email)."""
    user = await get_user_by_id(user_id, db)
    if not user:
        raise ValueError("User not found")
    
    # Generate deletion token (valid 24h)
    token = generate_deletion_token(user_id)
    
    # Send confirmation email
    await send_deletion_confirmation_email(user.email, token)
    
    return {"message": "Confirmation email sent. Check your inbox."}

async def confirm_deletion(user_id: str, token: str, password: str, db: AsyncSession) -> dict:
    """Step 2: Confirm deletion with password verification."""
    # Verify token
    if not verify_deletion_token(token, user_id):
        raise ValueError("Invalid or expired token")
    
    # Verify password
    user = await get_user_by_id(user_id, db)
    if not verify_password(password, user.hashed_password):
        raise ValueError("Incorrect password")
    
    # Soft delete: mark as pending_deletion
    user.status = AccountStatus.PENDING_DELETION
    user.deletion_requested_at = datetime.utcnow()
    user.deletion_scheduled_at = datetime.utcnow() + timedelta(days=30)
    await db.commit()
    
    return {"message": "Account scheduled for deletion in 30 days. You can cancel anytime."}

async def hard_delete_user(user_id: str, db: AsyncSession):
    """Background task: Hard delete users past 30-day window."""
    user = await get_user_by_id(user_id, db)
    if not user or user.status != AccountStatus.PENDING_DELETION:
        return
    
    if user.deletion_scheduled_at > datetime.utcnow():
        return  # Not yet time
    
    # Delete all user data (cascade)
    await delete_user_documents(user_id, db)
    await delete_user_notes(user_id, db)
    await delete_user_flashcards(user_id, db)
    await delete_user_quizzes(user_id, db)
    await delete_user_conversations(user_id, db)
    await delete_user_graph_entities(user_id, db)
    await delete_user_teams(user_id, db)
    
    # Delete user
    await db.delete(user)
    await db.commit()
```

**API Endpoints:**

```python
# app/api/users.py

@router.post("/users/delete-request")
async def request_account_deletion(...):
    """Step 1: Request deletion (sends email)."""
    pass

@router.post("/users/delete-confirm")
async def confirm_account_deletion(
    token: str,
    password: str,
    ...
):
    """Step 2: Confirm deletion with password."""
    pass

@router.post("/users/delete-cancel")
async def cancel_account_deletion(...):
    """Cancel pending deletion (within 30 days)."""
    pass
```

#### Task 23.2.4: Cookie Consent Banner

**Frontend Component:** `CookieConsent.tsx`

```typescript
// frontend/src/components/CookieConsent.tsx

import { useState, useEffect } from 'react';

export function CookieConsent() {
    const [show, setShow] = useState(false);
    
    useEffect(() => {
        const consent = localStorage.getItem('cookie_consent');
        if (!consent) {
            setShow(true);
        }
    }, []);
    
    const accept = () => {
        localStorage.setItem('cookie_consent', 'accepted');
        setShow(false);
        // Enable analytics
    };
    
    const decline = () => {
        localStorage.setItem('cookie_consent', 'declined');
        setShow(false);
        // Disable analytics
    };
    
    if (!show) return null;
    
    return (
        <div className="fixed bottom-0 left-0 right-0 bg-gray-800 text-white p-4">
            <p>We use cookies to improve your experience. <a href="/privacy">Learn more</a></p>
            <button onClick={accept}>Accept</button>
            <button onClick={decline}>Decline</button>
        </div>
    );
}
```

#### Task 23.2.5: Privacy Policy Page

**Frontend Page:** `PrivacyPolicy.tsx`

- Data collection: What we collect (email, usage, documents)
- Usage: How we use data (learning, graph building, flashcards)
- Retention: How long we keep data (until deletion)
- User rights: Access, export, delete, rectify
- Contact: Privacy officer email

---

### Part C: Backup & Monitoring (4 tasks, ~8 giờ)

> **Estimate:** ~8 giờ

#### Task 23.3.1: Backup Scripts

**Location:** `scripts/backup/`

**PostgreSQL Backup:**

```bash
#!/bin/bash
# scripts/backup/postgres_backup.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=${DB_NAME:-aethertutor}
DB_USER=${DB_USER:-postgres}
DB_HOST=${DB_HOST:-localhost}

mkdir -p $BACKUP_DIR

pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f "$BACKUP_DIR/db_$DATE.dump"

# Retention: keep last 30 days
find $BACKUP_DIR -name "db_*.dump" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/db_$DATE.dump"
```

**ChromaDB Backup:**

```bash
#!/bin/bash
# scripts/backup/chromadb_backup.sh

BACKUP_DIR="/backups/chromadb"
CHROMA_DATA="/var/lib/chroma"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

tar -czf "$BACKUP_DIR/chroma_$DATE.tar.gz" -C $CHROMA_DATA .

# Retention: keep last 7 days
find $BACKUP_DIR -name "chroma_*.tar.gz" -mtime +7 -delete

echo "ChromaDB backup completed: $BACKUP_DIR/chroma_$DATE.tar.gz"
```

**Redis Backup:**

```bash
#!/bin/bash
# scripts/backup/redis_backup.sh

BACKUP_DIR="/backups/redis"
REDIS_DATA="/var/lib/redis"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Trigger RDB save
redis-cli BGSAVE
sleep 5

cp "$REDIS_DATA/dump.rdb" "$BACKUP_DIR/redis_$DATE.rdb"

# Retention: keep last 7 days
find $BACKUP_DIR -name "redis_*.rdb" -mtime +7 -delete

echo "Redis backup completed: $BACKUP_DIR/redis_$DATE.rdb"
```

**Cron Jobs:**

```cron
# Daily backups at 2 AM
0 2 * * * /scripts/backup/postgres_backup.sh >> /var/log/backup.log 2>&1
0 2 * * * /scripts/backup/chromadb_backup.sh >> /var/log/backup.log 2>&1
0 2 * * * /scripts/backup/redis_backup.sh >> /var/log/backup.log 2>&1
```

#### Task 23.3.2: Recovery Scripts

**PostgreSQL Restore:**

```bash
#!/bin/bash
# scripts/restore/postgres_restore.sh

BACKUP_FILE=$1
DB_NAME=${DB_NAME:-aethertutor}

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "Restoring from $BACKUP_FILE..."
pg_restore -d $DB_NAME -c --if-exists $BACKUP_FILE
echo "Restore completed"
```

#### Task 23.3.3: Prometheus Metrics

**Endpoint:** `/metrics`

**Implementation:**

```python
# app/middleware/prometheus_middleware.py

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
WS_CONNECTIONS = Gauge('websocket_connections', 'Active WebSocket connections')

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_LATENCY.observe(duration)
        
        return response

# Metrics endpoint
from fastapi import APIRouter
from prometheus_client import generate_latest

router = APIRouter()

@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

#### Task 23.3.4: Kubernetes Health Checks

**Endpoints:**

```python
# app/api/health.py

from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()

@router.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe: DB connected, migrations applied."""
    try:
        from app.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}, 503

@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe: Process alive, no deadlock."""
    return {"status": "alive"}
```

**Kubernetes Config:**

```yaml
# k8s/deployment.yaml

livenessProbe:
  httpGet:
    path: /health/liveness
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/readiness
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## 📊 Deliverables

### Backend

| File | Description |
|------|-------------|
| `app/api/limiter.py` | Upgraded to RedisStorage |
| `app/constants.py` | 23 new rate limit constants |
| `app/middleware/pii_anonymizer.py` | PII masking in logs |
| `app/middleware/prometheus_middleware.py` | Metrics collection |
| `app/services/gdpr_export.py` | Data export service |
| `app/services/account_deletion.py` | Deletion flow |
| `app/api/health.py` | Health check endpoints |
| All API routers | Rate limit decorators applied |
| `scripts/backup/` | Backup scripts (3 files) |
| `scripts/restore/` | Restore scripts (1 file) |

### Frontend

| File | Description |
|------|-------------|
| `frontend/src/components/CookieConsent.tsx` | Cookie consent banner |
| `frontend/src/pages/PrivacyPolicy.tsx` | Privacy policy page |
| `frontend/src/utils/sanitize.ts` | DOMPurify sanitization |
| All Markdown renderers | Sanitized with DOMPurify |

### Tests

| File | Description |
|------|-------------|
| `tests/integration/test_idor_audit.py` | IDOR audit tests (6 tests) |
| `tests/integration/test_rate_limiting.py` | Rate limiting tests (10 tests) |
| `tests/integration/test_gdpr_export.py` | GDPR export test (1 test) |
| `tests/integration/test_account_deletion.py` | Account deletion tests (3 tests) |

---

## ✅ Acceptance Criteria

- [ ] 100% rate limiting coverage (121/121 endpoints)
- [ ] Redis-backed rate limiting syncs across workers
- [ ] IDOR audit: 0 critical findings (all endpoints properly scoped)
- [ ] XSS prevention: DOMPurify + CSP headers active
- [ ] GDPR export: ZIP download working
- [ ] Account deletion: 2-step flow working, soft delete 30 days
- [ ] Backup scripts: PostgreSQL, ChromaDB, Redis all backing up
- [ ] Recovery scripts: Restore from backup working
- [ ] Prometheus metrics: `/metrics` endpoint active
- [ ] Kubernetes health checks: `/health/readiness`, `/health/liveness` working

---

## ⚠️ Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Redis storage upgrade breaks existing rate limits | Low | High | Test in staging first, rollback plan ready |
| Rate limit too restrictive blocks legitimate users | Medium | Medium | Monitor logs, adjust limits post-launch |
| GDPR export times out for large users | Medium | Low | Use background job, notify when ready |
| Backup scripts fail silently | Medium | High | Add monitoring/alerting on backup failures |

---

© 2026 AetherTutor Team
*Sprint 23 Production Hardening Spec — Generated 2026-04-14*
*Status: READY FOR EXECUTION*
