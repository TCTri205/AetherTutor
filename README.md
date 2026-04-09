# AetherTutor: AI-Powered Learning OS

AetherTutor là một hệ thống học tập thông minh dựa trên AI, sử dụng mã nguồn **LightRAG** để xây dựng Knowledge Graph từ tài liệu của bạn, giúp bạn học tập sâu hơn thông qua phương pháp Socratic phản biện.

---

## 🚀 Quick Start (Production/Docker)

Cách nhanh nhất để khởi chạy toàn bộ hệ thống AetherTutor:

```bash
# 1. Clone repository và cấu hình env
cp .env.example .env

# 2. Khởi chạy toàn bộ stack với Docker Compose
docker compose up --build -d
```

Sau khi hoàn tất, bạn có thể truy cập:
- **Frontend UI:** `http://localhost` (Port 80)
- **API Health:** `http://localhost/health`
- **Swagger Docs:** `http://localhost/docs`

---

## 🛠️ Local Development (Hybrid Mode)

**Khuyến nghị:** Chạy Backend + Frontend trực tiếp trên host (hot-reload), chỉ dùng Docker cho Database services.

### 1. Khởi động Data Layer (Docker)
```bash
# Chỉ chạy 3 services: PostgreSQL, Redis, ChromaDB
docker compose -f docker-compose.data.yml up -d

# Kiểm tra status
docker compose -f docker-compose.data.yml ps

# Xem logs
docker compose -f docker-compose.data.yml logs -f
```

### 2. Backend Setup (Host)
```bash
# Tạo và kích hoạt venv
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate     # macOS/Linux

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy migration
alembic upgrade head

# Chạy Worker (background jobs - terminal 1)
arq app.worker.tasks.WorkerSettings

# Chạy API (hot-reload - terminal 2)
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup (Host)
```bash
cd frontend
npm install
npm run dev
```

### 4. Truy cập
- **Frontend (Vite):** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Swagger Docs:** `http://localhost:8000/docs`
- **API Health:** `http://localhost:8000/health`

### 5. Dừng Data Layer
```bash
docker compose -f docker-compose.data.yml down
```

---

## 🐳 Full Docker Stack (Production)

Để chạy toàn bộ hệ thống trong Docker (không hot-reload):

```bash
# Khởi chạy toàn bộ stack
docker compose up --build -d

# Truy cập
# - Frontend: http://localhost:3000
# - API: http://localhost:8001
# - Docs: http://localhost:8001/docs
```

---

## 📂 Documentation Hub

Tài liệu chi tiết được tổ chức trong thư mục `docs/`:

- [**Kiến trúc hệ thống**](docs/core/Architecture.md)
- [**Cấu hình API**](docs/core/API_Specifications.md)
- [**Hướng dẫn kiểm thử E2E**](docs/testing/E2E_INTEGRATION_TESTS.md)
- [**Lộ trình phát triển**](docs/reports/Roadmap.md)
- [**Launch Checklist**](docs/reports/LAUNCH_CHECKLIST.md)
- [**📚 Documentation Hub**](docs/README.md) — Xem toàn bộ tài liệu

---

## 📊 Current Status: v0.1 (MVP) - LAUNCHED ✅

Phase 6 (Integration & Launch) đã hoàn tất:
- **Backend:** 18+ Unit tests, 20+ Integration tests (passing).
- **Hardening:** CORS production-ready, Rate Limmiting tích hợp.
- **Docker:** Multi-stage build cho cả Frontend và Backend.
- **CI/CD:** GitHub Actions workflow được cấu hình.

---
© 2026 AetherTutor Team.
