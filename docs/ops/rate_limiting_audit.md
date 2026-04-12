# Rate Limiting Audit Report

**Date:** 2026-04-12
**Auditor:** AetherTutor QA
**Scope:** All API endpoints in `app/api/*.py`

---

## 1. Current Rate Limits per Endpoint

Rate limiting is implemented via **slowapi** (`Limiter`) with a shared instance in `app/api/limiter.py`. The key function extracts the real client IP from the `X-Forwarded-For` header (for reverse proxy support).

### 1.1 Auth Endpoints (`app/api/auth.py`)

| Endpoint | Method | Rate Limit | Constant | Status |
|----------|--------|------------|----------|--------|
| `/auth/register` | POST | 3/minute | `RATE_LIMIT_REGISTER` | Protected |
| `/auth/login` | POST | 5/minute | `RATE_LIMIT_LOGIN` | Protected |
| `/auth/refresh` | POST | 10/minute | `RATE_LIMIT_REFRESH` | Protected |
| `/auth/logout` | POST | 10/minute | `RATE_LIMIT_LOGOUT` | Protected |
| `/auth/forgot-password` | POST | 10/minute | `RATE_LIMIT_AUTH_EMAIL` (inline) | Protected |
| `/auth/reset-password` | POST | 10/minute | `RATE_LIMIT_AUTH_EMAIL` (inline) | Protected |
| `/auth/verify-email` | POST | 10/minute | `RATE_LIMIT_AUTH_EMAIL` (inline) | Protected |
| `/auth/resend-verification` | POST | 10/minute | `RATE_LIMIT_AUTH_EMAIL` (inline) | Protected |
| `/auth/logout-all` | POST | **NONE** | - | **MISSING** |
| `/auth/sessions` | GET | **NONE** | - | **MISSING** |

### 1.2 Document Endpoints (`app/api/documents.py`)

| Endpoint | Method | Rate Limit | Constant | Status |
|----------|--------|------------|----------|--------|
| `/documents/upload` | POST | 5/minute | `RATE_LIMIT_DOCUMENT_UPLOAD` | Protected |
| `/documents/{id}` | DELETE | 20/minute | `RATE_LIMIT_DOCUMENT_DELETE` | Protected |
| `/documents/test-ingest` | POST | **NONE** | - | **MISSING** (debug-only, but still) |
| `/documents/` | GET | **NONE** | - | **MISSING** |
| `/documents/{id}` | GET | **NONE** | - | **MISSING** |

### 1.3 Chat Endpoints (`app/api/chat.py`)

| Endpoint | Method | Rate Limit | Constant | Status |
|----------|--------|------------|----------|--------|
| `/chat/conversations/{doc_id}` | POST | 20/minute | `RATE_LIMIT_CONVERSATION_CREATE` | Protected |
| `/chat/stream` | POST | 60/minute | `RATE_LIMIT_CHAT_STREAM` | Protected |
| `/chat/conversations/{doc_id}` | GET | **NONE** | - | **MISSING** |
| `/chat/history/{conv_id}` | GET | **NONE** | - | **MISSING** |
| `/chat/conversations/{conv_id}` | DELETE | **NONE** | - | **MISSING** |
| `/chat/socratic` | POST | **NONE** | - | **MISSING** (legacy) |
| `/chat/multi-doc` | POST | **NONE** | - | **MISSING** |

### 1.4 Graph Endpoints (`app/api/graph.py`)

| Endpoint Category | Count | Rate Limit | Status |
|-------------------|-------|------------|--------|
| All POST endpoints | ~15 | **NONE** | **MISSING** |
| All GET endpoints | ~15 | **NONE** | **MISSING** |
| All DELETE/PATCH endpoints | 1 | **NONE** | **MISSING** |

Notable unprotected endpoints:
- `/graph/query` (POST) - LLM-intensive query
- `/graph/global` (POST) - Aggregated graph
- `/graph/query-multi` (POST) - Multi-doc query with cross-verification
- `/graph/mermaid` (POST) - Diagram generation
- `/graph/entities/merge` (POST) - Entity merge (destructive)
- `/graph/import/obsidian` (POST) - Vault import

### 1.5 Flashcard Endpoints (`app/api/flashcards.py`)

| Endpoint | Method | Rate Limit | Status |
|----------|--------|------------|--------|
| All endpoints (10 total) | ALL | **NONE** | **MISSING** |

Notable unprotected endpoints:
- `/flashcards/review` (POST) - SM-2 review submission
- `/flashcards/generate` (POST) - LLM-based generation
- `/flashcards` (POST) - Create flashcard

### 1.6 Quiz Endpoints (`app/api/quiz.py`)

| Endpoint | Method | Rate Limit | Status |
|----------|--------|------------|--------|
| All endpoints (12 total) | ALL | **NONE** | **MISSING** |

Notable unprotected endpoints:
- `/quiz/generate` (POST) - LLM-based quiz generation
- `/quiz/{id}/submit` (POST) - Quiz submission
- `/quiz/results/{id}/generate-flashcards` (POST) - LLM-based flashcard generation

### 1.7 Note Endpoints (`app/api/notes.py`)

| Endpoint | Method | Rate Limit | Status |
|----------|--------|------------|--------|
| All endpoints (11 total) | ALL | **NONE** | **MISSING** |

Notable unprotected endpoints:
- `/notes/{id}/suggest-backlinks` (POST) - LLM-based AI suggestions
- `/notes` (POST) - Create note

### 1.8 User Endpoints (`app/api/users.py`)

| Endpoint | Method | Rate Limit | Status |
|----------|--------|------------|--------|
| `/users/me` | GET | **NONE** | **MISSING** |
| `/users/me` | PUT | **NONE** | **MISSING** |
| `/users/me/change-password` | POST | **NONE** | **MISSING** |

### 1.9 Topic Endpoints (`app/api/topics.py`)

| Endpoint | Method | Rate Limit | Status |
|----------|--------|------------|--------|
| All endpoints (14 total) | ALL | **NONE** | **MISSING** |

Notable unprotected endpoints:
- `/topics` (POST) - Create topic
- `/topics/{id}` (PUT) - Update topic
- `/topics/{id}` (DELETE) - Delete topic

---

## 2. Summary of Gaps

| Category | Total Endpoints | Protected | Unprotected | Coverage |
|----------|----------------|-----------|-------------|----------|
| Auth | 10 | 8 | 2 | 80% |
| Documents | 5 | 2 | 3 | 40% |
| Chat | 7 | 2 | 5 | 29% |
| Graph | ~30 | 0 | ~30 | 0% |
| Flashcards | 10 | 0 | 10 | 0% |
| Quiz | 12 | 0 | 12 | 0% |
| Notes | 11 | 0 | 11 | 0% |
| Users | 3 | 0 | 3 | 0% |
| Topics | 14 | 0 | 14 | 0% |
| **TOTAL** | **~102** | **12** | **~90** | **~12%** |

### Critical Gaps (High Priority)

1. **`/auth/logout-all`** - Auth endpoint without rate limiting (brute-force risk)
2. **`/auth/sessions`** - Session enumeration without rate limiting
3. **`/chat/multi-doc`** - LLM-intensive, cross-document query without rate limiting
4. **`/chat/socratic`** - Legacy LLM endpoint without rate limiting
5. **`/quiz/generate`** - LLM-based generation without rate limiting
6. **`/flashcards/generate`** - LLM-based generation without rate limiting
7. **`/notes/{id}/suggest-backlinks`** - LLM-based AI suggestions without rate limiting
8. **`/graph/query-multi`** - LLM-based multi-doc query without rate limiting

### Moderate Gaps (Medium Priority)

9. **All Graph CRUD endpoints** - Read-heavy, could be rate-limited for abuse prevention
10. **All Flashcard CRUD endpoints** - Write endpoints need abuse prevention
11. **All Quiz endpoints** - Write endpoints need abuse prevention
12. **All Note endpoints** - Write endpoints need abuse prevention
13. **All Topic endpoints** - Write endpoints need abuse prevention
14. **`/users/me/change-password`** - Security-sensitive without rate limiting

---

## 3. Recommendations

### 3.1 Suggested Rate Limits by Category

| Category | Recommended Limit | Rationale |
|----------|------------------|-----------|
| **Auth (register/login)** | 10/minute | Prevent brute-force, allow legitimate login attempts |
| **Auth (email operations)** | 10/minute | Prevent email flooding, already set correctly |
| **Auth (session management)** | 30/minute | Read-heavy, low risk |
| **Upload** | 5/minute | Already set correctly, prevents resource abuse |
| **Chat (stream)** | 30/minute | LLM-intensive, currently 60/min (too high) |
| **Chat (conversation CRUD)** | 30/minute | Moderate usage expected |
| **Graph CRUD (write)** | 30/minute | Destructive operations need tighter limits |
| **Graph (read/query)** | 60/minute | Read-heavy with LLM cost |
| **Flashcard (review/read)** | 120/minute | High-frequency spaced repetition usage |
| **Flashcard (generate/write)** | 20/minute | LLM-intensive generation |
| **Quiz (generate/submit)** | 10/minute | LLM-intensive, expensive operations |
| **Quiz (read/stats)** | 60/minute | Read-heavy |
| **Notes (CRUD)** | 60/minute | Moderate write frequency |
| **Notes (AI suggest)** | 15/minute | LLM-intensive |
| **Topics (CRUD)** | 60/minute | Moderate write frequency |
| **Users (profile)** | 30/minute | Moderate usage |
| **Users (change-password)** | 10/minute | Security-sensitive |

### 3.2 Implementation Plan

#### Phase 1: Critical Security Fixes (Immediate)

Add rate limiting to unprotected auth endpoints and LLM-intensive endpoints:

```python
# app/api/auth.py - Add to logout-all and sessions
from app.constants import RATE_LIMIT_LOGOUT, RATE_LIMIT_REFRESH
@limiter.limit(RATE_LIMIT_LOGOUT)  # or new constant
async def logout_all(...)

@limiter.limit(RATE_LIMIT_REFRESH)
async def list_sessions(...)

# app/constants.py - Add new constants
RATE_LIMIT_LOGOUT_ALL = "10/minute"
RATE_LIMIT_SESSIONS = "30/minute"
RATE_LIMIT_CHAT_MULTI_DOC = "30/minute"
RATE_LIMIT_QUIZ_GENERATE = "10/minute"
RATE_LIMIT_FLASHCARD_GENERATE = "20/minute"
RATE_LIMIT_NOTE_SUGGEST_BACKLINKS = "15/minute"
RATE_LIMIT_GRAPH_MULTI_QUERY = "30/minute"
RATE_LIMIT_CHANGE_PASSWORD = "10/minute"
```

#### Phase 2: LLM-Intensive Endpoints (Short-term)

Protect all endpoints that trigger LLM calls:
- `/quiz/generate` - 10/minute
- `/quiz/{id}/submit` - 20/minute
- `/flashcards/generate` - 20/minute
- `/notes/{id}/suggest-backlinks` - 15/minute
- `/graph/query-multi` - 30/minute
- `/graph/mermaid` - 30/minute
- `/chat/multi-doc` - 30/minute
- `/chat/socratic` - 30/minute

#### Phase 3: Full Coverage (Medium-term)

Apply consistent rate limiting across all remaining endpoints:
- Graph read endpoints: 60/minute
- Graph write endpoints: 30/minute
- Flashcard CRUD: 60/minute (read), 20/minute (write)
- Quiz CRUD: 60/minute (read), 10/minute (write)
- Note CRUD: 60/minute
- Topic CRUD: 60/minute
- User profile: 30/minute

### 3.3 Suggested Constants to Add to `app/constants.py`

```python
# Rate Limiting — Extended (Sprint 19)
RATE_LIMIT_LOGOUT_ALL = "10/minute"
RATE_LIMIT_SESSIONS = "30/minute"
RATE_LIMIT_CHANGE_PASSWORD = "10/minute"
RATE_LIMIT_CHAT_MULTI_DOC = "30/minute"
RATE_LIMIT_CHAT_HISTORY = "60/minute"
RATE_LIMIT_QUIZ_GENERATE = "10/minute"
RATE_LIMIT_QUIZ_SUBMIT = "20/minute"
RATE_LIMIT_QUIZ_READ = "60/minute"
RATE_LIMIT_FLASHCARD_GENERATE = "20/minute"
RATE_LIMIT_FLASHCARD_WRITE = "20/minute"
RATE_LIMIT_FLASHCARD_READ = "120/minute"
RATE_LIMIT_NOTE_CREATE = "30/minute"
RATE_LIMIT_NOTE_SUGGEST_BACKLINKS = "15/minute"
RATE_LIMIT_NOTE_READ = "60/minute"
RATE_LIMIT_TOPIC_WRITE = "30/minute"
RATE_LIMIT_TOPIC_READ = "60/minute"
RATE_LIMIT_USER_PROFILE = "30/minute"
RATE_LIMIT_GRAPH_QUERY = "60/minute"
RATE_LIMIT_GRAPH_MULTI_QUERY = "30/minute"
RATE_LIMIT_GRAPH_MERMAID = "30/minute"
RATE_LIMIT_GRAPH_WRITE = "30/minute"
RATE_LIMIT_GRAPH_READ = "60/minute"
RATE_LIMIT_DOCUMENT_LIST = "60/minute"
```

### 3.4 Current vs Recommended Comparison

| Endpoint Category | Current | Recommended | Action |
|-------------------|---------|-------------|--------|
| Auth (register) | 3/min | 10/min | Increase (too restrictive) |
| Auth (login) | 5/min | 10/min | Increase |
| Auth (refresh) | 10/min | 10/min | Keep |
| Auth (logout) | 10/min | 10/min | Keep |
| Upload | 5/min | 5/min | Keep |
| Chat (stream) | 60/min | 30/min | Decrease (LLM cost) |
| Graph CRUD | None | 30-60/min | Add |
| Flashcard CRUD | None | 20-120/min | Add |
| Quiz CRUD | None | 10-60/min | Add |
| Notes CRUD | None | 15-60/min | Add |
| Users | None | 10-30/min | Add |
| Topics | None | 30-60/min | Add |

---

## 4. Additional Recommendations

1. **Centralize all rate limit constants** - Move `RATE_LIMIT_AUTH_EMAIL` from inline (`auth.py` line 235) to `constants.py` for consistency.

2. **Consider per-user rate limits** - Current implementation is IP-based. For authenticated endpoints, consider rate limiting by user ID in addition to IP.

3. **Add rate limit headers** - Ensure `slowapi` is configured to return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers for client-side handling.

4. **Redis-backed rate limiter** - If scaling to multiple backend instances, ensure slowapi uses Redis as the backend (currently in-memory by default).

5. **Document rate limits in OpenAPI/Swagger** - Add `x-rate-limit` metadata to endpoint documentation so API consumers know their limits.

---

## 5. Conclusion

**Current coverage: ~12% (12 of ~102 endpoints protected)**

The auth and document endpoints have reasonable rate limiting, but **88% of endpoints are completely unprotected**. The highest priority is protecting LLM-intensive endpoints (quiz generation, flashcard generation, AI backlink suggestions, multi-doc queries) as these directly incur API costs and can be abused to exhaust rate limits or budgets.
