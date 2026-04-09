# AetherTutor - Project Context

## Project Overview

**AetherTutor** là một hệ thống học tập thông minh dựa trên AI (AI-Powered Learning OS), sử dụng mã nguồn **LightRAG** để xây dựng Knowledge Graph từ tài liệu người dùng, hỗ trợ học tập sâu thông qua phương pháp Socratic phản biện.

### Core Features
- **Document Processing**: Upload và xử lý tài liệu PDF
- **Knowledge Graph**: Xây dựng đồ thị tri thức từ tài liệu
- **Socratic Chat**: Chat AI với phương pháp phản biện Socratic
- **Flashcards**: Tạo flashcards thông minh với thuật toán SM-2
- **Quiz Generation**: Tạo bài kiểm tra tự động
- **Note Taking**: Hệ thống ghi chú tích hợp

### Tech Stack
| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Database** | PostgreSQL 16 (asyncpg), SQLAlchemy 2.0 |
| **Vector DB** | ChromaDB 0.5.0 |
| **Cache/Queue** | Redis 7, ARQ (async task queue) |
| **LLM** | OpenAI API / Ollama (local) |
| **Graph** | NetworkX |
| **Frontend** | React/Vite (trong thư mục `frontend/`) |
| **Migration** | Alembic |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Linting** | Ruff |
| **Containerization** | Docker, Docker Compose |

---

## Project Structure

```
AetherTutor/
├── app/                        # Backend source code
│   ├── api/                    # API routers (documents, chat, graph, flashcards, quiz, notes)
│   ├── core/                   # Core business logic
│   ├── mcp/                    # MCP (Model Context Protocol) integration
│   ├── middleware/             # Custom middleware
│   ├── models/                 # SQLAlchemy models
│   ├── repositories/           # Data access layer
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business services (LLM, embedding, etc.)
│   ├── worker/                 # ARQ background workers
│   ├── config.py               # Pydantic settings (.env)
│   ├── database.py             # Database connection
│   ├── dependencies.py         # FastAPI dependencies
│   ├── main.py                 # FastAPI app entry point
│   └── logging_config.py       # Logging configuration
├── alembic/                    # Database migrations
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── mocks/                  # Mock fixtures
├── frontend/                   # Frontend application
├── docs/                       # Documentation
├── data/                       # Data directory (uploads, graphs)
├── uploads/                    # Uploaded documents
├── docker-compose.yml          # Full stack Docker Compose
├── docker-compose.data.yml     # Data layer only (PostgreSQL, Redis, ChromaDB)
├── Dockerfile                  # Multi-stage backend build
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
├── pytest.ini                  # Pytest configuration
└── .env.example                # Environment template
```

---

## Building and Running

### Quick Start (Full Docker)
```bash
# 1. Clone và cấu hình env
cp .env.example .env

# 2. Khởi chạy toàn bộ stack
docker compose up --build -d
```

Truy cập:
- **Frontend:** `http://localhost` (Port 80)
- **API Health:** `http://localhost/health`
- **Swagger Docs:** `http://localhost/docs`

### Local Development (Hybrid Mode) - Khuyến nghị

**1. Khởi động Data Layer (Docker):**
```bash
docker compose -f docker-compose.data.yml up -d
```

**2. Backend Setup (Host):**
```bash
# Tạo và kích hoạt venv
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate     # macOS/Linux

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy migration
alembic upgrade head

# Chạy Worker - terminal 1
arq app.worker.tasks.WorkerSettings

# Chạy API - terminal 2
uvicorn app.main:app --reload --port 8000
```

**3. Frontend Setup (Host):**
```bash
cd frontend
npm install
npm run dev
```

**Truy cập Local:**
- **Frontend (Vite):** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Swagger Docs:** `http://localhost:8000/docs`

### Dừng Services
```bash
# Dừng data layer
docker compose -f docker-compose.data.yml down
```

---

## Configuration

### Environment Variables (`.env`)

File `.env.example` chứa template cấu hình. Các biến quan trọng:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production/testing) | `development` |
| `DATABASE_HOST` | PostgreSQL host | `localhost` |
| `REDIS_HOST` | Redis host | `localhost` |
| `CHROMA_HOST` | ChromaDB host | `localhost` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434/v1` |
| `DEFAULT_LLM_MODEL` | LLM model to use | Qwen2.5-1.5B |
| `EMBEDDING_PROVIDER` | Embedding provider (openai/ollama) | `openai` |
| `USE_LLM_MOCK` | Use mock LLM for testing | `false` |

---

## Testing

```bash
# Run all tests
pytest

# Run with verbose
pytest -v

# Run specific test file
pytest tests/unit/test_something.py

# Run integration tests
pytest tests/integration/
```

**Test Structure:**
- `tests/unit/` - Unit tests cho services, models, utilities
- `tests/integration/` - Integration tests cho API endpoints
- `tests/mocks/` - Mock fixtures cho LLM và external services
- `tests/conftest.py` - Shared fixtures và configuration

---

## Database Migrations

```bash
# Tạo migration mới
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback 1 migration
alembic downgrade -1

# Xem migration history
alembic history
```

---

## Code Quality & Conventions

### Linting
```bash
ruff check .
```

### Testing Conventions
- Sử dụng `pytest-asyncio` cho async tests
- `asyncio_mode = auto` trong `pytest.ini`
- Fixtures được định nghĩa trong `conftest.py`
- Mock LLM service trong `tests/mocks/` cho CI/CD

### Architecture Patterns
- **Repository Pattern**: `app/repositories/` - Data access layer
- **Service Layer**: `app/services/` - Business logic
- **Schema Layer**: `app/schemas/` - Pydantic models cho request/response
- **API Layer**: `app/api/` - FastAPI routers
- **Dependency Injection**: FastAPI `Depends()` pattern

---

## Key Services

### LLM Service
- Hỗ trợ cả **OpenAI** (cloud) và **Ollama** (local)
- Configurable qua `EMBEDDING_PROVIDER` và `DEFAULT_LLM_MODEL`
- Health check qua `/api/v1/health`

### Worker (ARQ)
- Background job processing qua Redis
- Xử lý document ingestion, graph building, flashcard generation
- Command: `arq app.worker.tasks.WorkerSettings`

### Vector Database (ChromaDB)
- Lưu trữ embeddings cho retrieval
- HTTP client mode kết nối tới ChromaDB container

### Knowledge Graph (NetworkX)
- Xây dựng đồ thị tri thức từ tài liệu
- Lưu trữ local hoặc S3 (configurable)

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/health` | Health check (PostgreSQL, Redis, ChromaDB, LLM) |
| `/api/v1/documents` | Document upload & processing |
| `/api/v1/chat` | Socratic chat with AI |
| `/api/v1/graph` | Knowledge graph operations |
| `/api/v1/flashcards` | Flashcard generation & review |
| `/api/v1/quiz` | Quiz generation |
| `/api/v1/notes` | Note management |
| `/docs` | Swagger UI (auto-generated) |

---

## Current Status

**Version:** v0.1 (MVP) - LAUNCHED ✅

- **Backend:** 18+ Unit tests, 20+ Integration tests (passing)
- **Hardening:** CORS production-ready, Rate Limiting tích hợp
- **Docker:** Multi-stage build cho Frontend và Backend
- **CI/CD:** GitHub Actions workflow được cấu hình

---

## Useful Commands Reference

```bash
# Docker
docker compose up --build -d                    # Full stack
docker compose -f docker-compose.data.yml up -d # Data layer only
docker compose down                             # Stop all
docker compose -f docker-compose.data.yml logs -f  # View logs

# Backend
pip install -r requirements.txt                 # Install dependencies
alembic upgrade head                            # Run migrations
uvicorn app.main:app --reload --port 8000       # Dev server
arq app.worker.tasks.WorkerSettings             # Worker

# Testing & Linting
pytest                                          # Run tests
ruff check .                                    # Lint code

# Frontend
cd frontend && npm install && npm run dev       # Dev server
```

---

## Troubleshooting

### Database Connection Issues
- Kiểm tra `DATABASE_HOST` trong `.env`: `localhost` cho local, `db` cho Docker
- Đảm bảo PostgreSQL container đang chạy: `docker compose -f docker-compose.data.yml ps`

### LLM Connection Issues
- **OpenAI:** Kiểm tra `OPENAI_API_KEY` hợp lệ
- **Ollama:** Đảm bảo Ollama đang chạy trên host, dùng `host.docker.internal` trong Docker

### Redis/Worker Issues
- Restart Redis: `docker compose -f docker-compose.data.yml restart redis`
- Kiểm tra worker logs: `arq app.worker.tasks.WorkerSettings --verbose`

---

© 2026 AetherTutor Team.
