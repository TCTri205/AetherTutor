# API Specifications

> [!WARNING]
> **Tài liệu này cần được cập nhật cho LightRAG!**
> Đây là tài liệu future_ops được viết trước khi tích hợp LightRAG. 
> Các endpoints trong tài liệu này dựa trên kiến trúc RAG truyền thống (Vector DB).
> Vui lòng tham khảo [`../API_Specifications.md`](../API_Specifications.md) để xem các LightRAG endpoints đã được cập nhật.
> 
> **Cần cập nhật:** Thêm các endpoints cho LightRAG graph querying, entity management, và relation endpoints.

Tài liệu này định nghĩa chi tiết tất cả API endpoints của AetherTutor theo chuẩn OpenAPI 3.0.

---

## 1. Base Information

```yaml
openapi: 3.0.3
info:
  title: AetherTutor API
  description: Learning OS API for intelligent learning management
  version: 1.0.0
  contact:
    name: AetherTutor Team
    email: api@aethertutor.com
  license:
    name: MIT

servers:
  - url: https://api.aethertutor.com/v1
    description: Production
  - url: https://staging-api.aethertutor.com/v1
    description: Staging
  - url: http://localhost:8000/v1
    description: Development
```

**Base URL:** `https://api.aethertutor.com/api/v1`

**Authentication:** Bearer Token (JWT)
```http
Authorization: Bearer <access_token>
```

---

## 2. Common Response Format

### 2.1 Success Response

```json
{
  "success": true,
  "data": {
    // Response payload
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-04-05T10:00:00Z"
  }
}
```

### 2.2 Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

### 2.3 Error Codes

| Code | HTTP Status | Description |
|---|---|---|
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid token |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource doesn't exist |
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Temporary service unavailable |

---

## 3. Pagination

All list endpoints support cursor-based pagination:

```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "cursor": "eyJpZCI6MTAwfQ==",
      "has_more": true,
      "total_count": 1234
    }
  }
}
```

**Query Parameters:**
- `limit`: Items per page (default: 20, max: 100)
- `cursor`: Pagination cursor from previous response

---

## 4. Authentication Endpoints

### 4.1 Register User

```http
POST /auth/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe",
  "accept_terms": true
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_abc123",
      "email": "user@example.com",
      "name": "John Doe",
      "subscription_tier": "free",
      "created_at": "2026-04-05T10:00:00Z"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJSUzI1NiIs...",
      "refresh_token": "dGhpcyBpcyBhIHRva2Vu...",
      "expires_in": 900
    }
  }
}
```

### 4.2 Login

```http
POST /auth/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_abc123",
      "email": "user@example.com",
      "name": "John Doe"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJSUzI1NiIs...",
      "refresh_token": "dGhpcyBpcyBhIHRva2Vu...",
      "expires_in": 900
    }
  }
}
```

### 4.3 Refresh Token

```http
POST /auth/refresh
Content-Type: application/json
```

**Request Body:**
```json
{
  "refresh_token": "dGhpcyBpcyBhIHRva2Vu..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "refresh_token": "bmV3IHRva2Vu...",
    "expires_in": 900
  }
}
```

### 4.4 OAuth Login

```http
GET /auth/oauth/{provider}
```

**Path Parameters:**
- `provider`: `google`, `github`, `microsoft`

**Response:** 302 Redirect to OAuth provider

**Callback:** `GET /auth/oauth/{provider}/callback?code=...`

---

## 5. User Endpoints

### 5.1 Get User Profile

```http
GET /users/me
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "usr_abc123",
    "email": "user@example.com",
    "name": "John Doe",
    "avatar_url": "https://...",
    "subscription_tier": "pro",
    "privacy_settings": {
      "data_collection": true,
      "ai_training": false,
      "telemetry": true,
      "history_retention_days": 365
    },
    "usage_stats": {
      "documents_count": 45,
      "notes_count": 123,
      "flashcards_count": 456,
      "study_hours_this_month": 28.5
    },
    "created_at": "2026-01-15T08:30:00Z",
    "updated_at": "2026-04-05T10:00:00Z"
  }
}
```

### 5.2 Update User Profile

```http
PATCH /users/me
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "John Updated",
  "avatar_url": "https://new-avatar.com/...",
  "privacy_settings": {
    "data_collection": false
  }
}
```

### 5.3 Export User Data (GDPR)

```http
POST /users/me/export
Authorization: Bearer <token>
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "export_id": "exp_abc123",
    "status": "processing",
    "estimated_completion": "2026-04-05T10:05:00Z"
  }
}
```

**Check Status:**
```http
GET /users/me/export/{export_id}
```

**Response (when complete):**
```json
{
  "success": true,
  "data": {
    "export_id": "exp_abc123",
    "status": "completed",
    "download_url": "https://exports.aethertutor.com/exp_abc123.zip",
    "expires_at": "2026-04-12T10:00:00Z"
  }
}
```

### 5.4 Delete User Account (GDPR)

```http
DELETE /users/me
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Account deletion scheduled",
    "grace_period_ends_at": "2026-05-05T10:00:00Z"
  }
}
```

---

## 6. Document Endpoints

### 6.1 Upload Document

```http
POST /documents
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Request Body:**
```
file: <PDF/Word/text file>
title: "My Document" (optional)
tags: ["machine-learning", "notes"] (optional)
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "document_id": "doc_abc123",
    "title": "My Document",
    "status": "processing",
    "source_type": "pdf",
    "file_size": 1234567,
    "created_at": "2026-04-05T10:00:00Z"
  }
}
```

### 6.2 Ingest from URL

```http
POST /documents/ingest-url
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "source_type": "web",
  "tags": ["research"]
}
```

### 6.3 List Documents

```http
GET /documents?limit=20&cursor=&status=completed&sort=-created_at
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit`: Number of results (default: 20, max: 100)
- `cursor`: Pagination cursor
- `status`: Filter by status (`pending`, `processing`, `completed`, `failed`)
- `sort`: Sort field (`created_at`, `title`, `file_size`), prefix with `-` for descending
- `search`: Full-text search in title/content

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "doc_abc123",
        "title": "My Document",
        "source_type": "pdf",
        "status": "completed",
        "file_size": 1234567,
        "total_pages": 45,
        "tags": ["machine-learning"],
        "created_at": "2026-04-05T10:00:00Z",
        "updated_at": "2026-04-05T10:01:30Z"
      }
    ],
    "pagination": {
      "cursor": "eyJpZCI6MTAwfQ==",
      "has_more": true,
      "total_count": 45
    }
  }
}
```

### 6.4 Get Document Details

```http
GET /documents/{document_id}
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "doc_abc123",
    "title": "My Document",
    "source_type": "pdf",
    "source_url": null,
    "file_path": "s3://bucket/doc_abc123.pdf",
    "mime_type": "application/pdf",
    "file_size": 1234567,
    "total_pages": 45,
    "total_chunks": 234,
    "status": "completed",
    "tags": ["machine-learning"],
    "metadata": {
      "author": "John Smith",
      "creation_date": "2026-01-01"
    },
    "created_at": "2026-04-05T10:00:00Z",
    "updated_at": "2026-04-05T10:01:30Z"
  }
}
```

### 6.5 Delete Document

```http
DELETE /documents/{document_id}
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Document deleted successfully"
  }
}
```

---

## 7. Chat Endpoints

### 7.1 Send Chat Message

```http
POST /chat/feynman
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "Explain quantum computing",
  "context": {
    "document_ids": ["doc_abc123"],
    "mode": "socratic",
    "max_response_length": 500
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "response": "What do you already know about quantum mechanics? Let's start from your current understanding.",
    "metadata": {
      "mode": "socratic",
      "tokens_used": 150,
      "model": "gpt-4o-mini",
      "response_time_ms": 1234,
      "context_documents": ["doc_abc123"]
    },
    "session_id": "sess_xyz789"
  }
}
```

### 7.2 Streaming Chat (WebSocket)

```http
WS /ws/chat
Authorization: Bearer <token>
```

**Client Message:**
```json
{
  "action": "send_message",
  "data": {
    "message": "Explain quantum computing",
    "context": {
      "document_ids": ["doc_abc123"],
      "mode": "socratic"
    }
  }
}
```

**Server Messages:**
```json
// Token stream
{
  "type": "token",
  "data": {
    "content": "What do you"
  }
}

// Complete
{
  "type": "complete",
  "data": {
    "session_id": "sess_xyz789",
    "tokens_used": 150,
    "response_time_ms": 1234
  }
}

// Error
{
  "type": "error",
  "data": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests"
  }
}
```

### 7.3 Get Chat History

```http
GET /chat/sessions/{session_id}/messages?limit=50&cursor=
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "msg_001",
        "role": "user",
        "content": "Explain quantum computing",
        "created_at": "2026-04-05T10:00:00Z"
      },
      {
        "id": "msg_002",
        "role": "assistant",
        "content": "What do you already know about quantum mechanics?",
        "metadata": {
          "tokens_used": 150,
          "model": "gpt-4o-mini"
        },
        "created_at": "2026-04-05T10:00:02Z"
      }
    ],
    "pagination": {
      "cursor": "eyJpZCI6MTAwfQ==",
      "has_more": true
    }
  }
}
```

---

## 8. Flashcard Endpoints

### 8.1 Get Due Flashcards

```http
GET /flashcards/due?limit=50
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "fc_abc123",
        "front": "What is quantum superposition?",
        "back": "A quantum system can exist in multiple states simultaneously until measured.",
        "difficulty": 0.6,
        "sm2_ease_factor": 2.5,
        "sm2_interval": 3,
        "sm2_next_review": "2026-04-05T10:00:00Z",
        "metadata": {
          "source_document_id": "doc_abc123"
        }
      }
    ],
    "pagination": {
      "cursor": "eyJpZCI6MTAwfQ==",
      "has_more": true,
      "total_count": 45
    }
  }
}
```

### 8.2 Review Flashcard

```http
POST /flashcards/{flashcard_id}/review
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "quality": 4
}
```

**Quality Scale:**
- `0`: Complete blackout
- `1`: Incorrect response
- `2`: Difficult, remembered with help
- `3`: Difficult, remembered correctly
- `4`: Correct response, some hesitation
- `5`: Perfect response, effortless

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "flashcard_id": "fc_abc123",
    "previous_interval": 3,
    "new_interval": 8,
    "next_review": "2026-04-13T10:00:00Z",
    "sm2_ease_factor": 2.6
  }
}
```

### 8.3 Generate Flashcards from Document

```http
POST /flashcards/generate
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_id": "doc_abc123",
  "num_cards": 20,
  "difficulty": "medium",
  "focus_areas": ["key concepts", "definitions"]
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "task_id": "task_xyz789",
    "status": "processing",
    "estimated_cards": 20
  }
}
```

**Check Status:**
```http
GET /flashcards/generate/{task_id}
```

---

## 9. Quiz Endpoints

### 9.1 Generate Quiz

```http
POST /quizzes/generate
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_ids": ["doc_abc123", "doc_def456"],
  "num_questions": 10,
  "question_types": ["multiple_choice", "true_false"],
  "difficulty": "medium"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "quiz": {
      "id": "quiz_abc123",
      "title": "Quiz from 2 documents",
      "questions": [
        {
          "id": "q_001",
          "type": "multiple_choice",
          "question": "What is the primary principle of quantum superposition?",
          "options": [
            "A quantum system can exist in multiple states simultaneously",
            "Particles can travel faster than light",
            "Energy is always conserved",
            "Measurement has no effect on state"
          ],
          "correct_answer": 0
        }
      ],
      "total_questions": 10
    }
  }
}
```

### 9.2 Submit Quiz Answers

```http
POST /quizzes/{quiz_id}/submit
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "answers": {
    "q_001": 0,
    "q_002": 1,
    "q_003": 2
  },
  "time_taken_seconds": 300
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "result": {
      "id": "result_xyz789",
      "score": 8,
      "total_questions": 10,
      "percentage": 80.0,
      "time_taken_seconds": 300,
      "completed_at": "2026-04-05T11:00:00Z"
    },
    "review": {
      "correct_answers": [
        {
          "question_id": "q_001",
          "your_answer": 0,
          "correct_answer": 0,
          "is_correct": true,
          "explanation": "Quantum superposition allows..."
        }
      ]
    }
  }
}
```

---

## 10. Visualization Endpoints

### 10.1 Generate Diagram

```http
POST /visualize
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "Explain the water cycle: evaporation, condensation, precipitation",
  "diagram_type": "flowchart",
  "focus": "Process flow"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "mermaid_code": "graph TD\n  A[Evaporation] --> B[Condensation]\n  B --> C[Precipitation]\n  C --> A",
    "diagram_type": "flowchart",
    "metadata": {
      "nodes_count": 3,
      "edges_count": 3,
      "generation_time_ms": 2345
    }
  }
}
```

### 10.2 Bidirectional Edit

```http
POST /visualize/edit
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "action": "text_to_diagram",
  "text": "Step 1: Upload document\nStep 2: Process chunks\nStep 3: Generate embeddings",
  "diagram_type": "flowchart"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "mermaid_code": "graph TD\n  A[Upload document] --> B[Process chunks]\n  B --> C[Generate embeddings]",
    "text_updated": "Step 1: Upload document\nStep 2: Process chunks\nStep 3: Generate embeddings"
  }
}
```

---

## 11. Notes Endpoints (Zettelkasten)

### 11.1 Create Note

```http
POST /notes
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Quantum Superposition",
  "content": "A fundamental principle where a quantum system can exist in multiple states...",
  "note_type": "permanent",
  "tags": ["quantum-physics", "fundamentals"],
  "linked_note_ids": ["note_abc123"]
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "note_xyz789",
    "title": "Quantum Superposition",
    "content": "A fundamental principle...",
    "note_type": "permanent",
    "tags": ["quantum-physics", "fundamentals"],
    "backlinks_count": 2,
    "created_at": "2026-04-05T10:00:00Z",
    "updated_at": "2026-04-05T10:00:00Z"
  }
}
```

### 11.2 Get Note Graph

```http
GET /notes/graph
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "note_abc123",
        "title": "Quantum Computing",
        "tags": ["quantum-physics"],
        "created_at": "2026-04-01T10:00:00Z"
      },
      {
        "id": "note_xyz789",
        "title": "Quantum Superposition",
        "tags": ["quantum-physics", "fundamentals"],
        "created_at": "2026-04-05T10:00:00Z"
      }
    ],
    "edges": [
      {
        "source": "note_abc123",
        "target": "note_xyz789",
        "context": "Related concept"
      }
    ]
  }
}
```

---

## 12. Agent Endpoints

### 12.1 Researcher Agent

```http
POST /agents/researcher
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "Latest advances in quantum computing 2026",
  "max_results": 10,
  "sources": ["uploaded_documents", "web"],
  "context_id": "ctx_abc123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "title": "Quantum Computing Progress 2026",
        "summary": "Recent breakthroughs include...",
        "source": "https://example.com/article",
        "relevance_score": 0.95,
        "chunk_ids": ["chk_001", "chk_002"]
      }
    ],
    "context_id": "ctx_def456",
    "metadata": {
      "total_results": 10,
      "search_time_ms": 456
    }
  }
}
```

### 12.2 Examiner Agent

```http
POST /agents/examiner
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "action": "assess_understanding",
  "topic": "quantum_superposition",
  "context_id": "ctx_abc123",
  "assessment_type": "quiz"
}
```

### 12.3 Orchestrator (Multi-Agent)

```http
POST /agents/orchestrator
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "request": "Summarize this document, create a diagram, and generate flashcards",
  "document_ids": ["doc_abc123"],
  "agents": ["researcher", "visualizer", "examiner"]
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "task_id": "task_multi123",
    "status": "processing",
    "agents_invoked": ["researcher", "visualizer", "examiner"],
    "estimated_completion": "2026-04-05T10:05:00Z"
  }
}
```

---

## 13. Study Session Endpoints

### 13.1 Start Study Session

```http
POST /sessions
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "session_type": "flashcard_review",
  "metadata": {
    "cards_count": 50,
    "document_ids": ["doc_abc123"]
  }
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "session_xyz789",
    "session_type": "flashcard_review",
    "started_at": "2026-04-05T10:00:00Z",
    "metadata": {}
  }
}
```

### 13.2 End Study Session

```http
POST /sessions/{session_id}/end
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "cards_reviewed": 45,
  "duration_seconds": 1800,
  "performance": {
    "easy": 20,
    "medium": 15,
    "hard": 10
  }
}
```

### 13.3 Get Study Statistics

```http
GET /sessions/stats
Authorization: Bearer <token>
```

**Query Parameters:**
- `period`: `week`, `month`, `year` (default: `month`)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "period": "month",
    "total_sessions": 28,
    "total_study_time_seconds": 50400,
    "total_cards_reviewed": 1234,
    "average_performance": 0.78,
    "streak_days": 15,
    "daily_breakdown": [
      {
        "date": "2026-04-01",
        "sessions": 2,
        "study_time_seconds": 1800,
        "cards_reviewed": 45
      }
    ]
  }
}
```

---

## 14. Rate Limits

| Endpoint | Free Tier | Pro Tier | Enterprise |
|---|---|---|---|
| `/chat/*` | 100/hour | 500/hour | Unlimited |
| `/documents` | 50/day | Unlimited | Unlimited |
| `/agents/*` | 50/hour | 200/hour | Unlimited |
| `/flashcards/*` | 200/hour | 1000/hour | Unlimited |
| `/visualize` | 20/hour | 100/hour | Unlimited |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1617187200
```

---

## 15. Webhooks

### 15.1 Register Webhook

```http
POST /webhooks
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["document.processed", "quiz.completed"],
  "secret": "your_webhook_secret"
}
```

### 15.2 Webhook Events

| Event | Trigger | Payload |
|---|---|---|
| `document.processed` | Document ingestion complete | `{document_id, status, chunks_count}` |
| `flashcards.generated` | Flashcard generation complete | `{flashcard_count, task_id}` |
| `quiz.completed` | User submits quiz | `{quiz_id, score, percentage}` |
| `study_streak.updated` | Daily study streak changes | `{streak_days, last_session}` |

**Webhook Delivery:**
```json
{
  "id": "evt_abc123",
  "type": "document.processed",
  "timestamp": "2026-04-05T10:00:00Z",
  "data": {
    "document_id": "doc_xyz789",
    "status": "completed",
    "chunks_count": 234
  },
  "signature": "sha256=..."
}
```

---

## 16. SDK Examples

### 16.1 Python SDK

```python
from aethertutor import AetherTutorClient

client = AetherTutorClient(api_key="your_api_key")

# Upload document
doc = await client.documents.upload(
    file_path="quantum.pdf",
    tags=["physics", "quantum"]
)

# Chat with Socratic tutor
response = await client.chat.feynman(
    message="Explain quantum entanglement",
    context={"document_ids": [doc.id]}
)

# Get due flashcards
due_cards = await client.flashcards.due(limit=50)

# Review flashcard
result = await client.flashcards.review(
    flashcard_id=due_cards[0].id,
    quality=4
)

# Generate quiz
quiz = await client.quizzes.generate(
    document_ids=[doc.id],
    num_questions=10
)
```

### 16.2 JavaScript SDK

```javascript
import { AetherTutorClient } from '@aethertutor/sdk';

const client = new AetherTutorClient({
  apiKey: 'your_api_key'
});

// Upload document
const doc = await client.documents.upload({
  file: quantumPdf,
  tags: ['physics', 'quantum']
});

// Chat
const response = await client.chat.feynman({
  message: 'Explain quantum entanglement',
  context: { documentIds: [doc.id] }
});

// Get due flashcards
const dueCards = await client.flashcards.due({ limit: 50 });

// Review
const result = await client.flashcards.review({
  flashcardId: dueCards[0].id,
  quality: 4
});
```

---

> [!IMPORTANT]
> Full OpenAPI specification available tại: `https://api.aethertutor.com/openapi.json`
> Interactive documentation: `https://api.aethertutor.com/docs` (Swagger UI)

---
© 2026 AetherTutor Team. Last updated: April 5, 2026
