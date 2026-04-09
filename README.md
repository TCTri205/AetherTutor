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

## 🛠️ Local Development (Backend & Frontend)

Nếu bạn muốn phát triển hoặc chạy local mà không dùng Docker cho toàn phần:

### 1. Infrastructure (Cần thiết)
```bash
docker compose up -d db redis chromadb
```

### 2. Backend Setup
```bash
# Tạo và kích hoạt venv
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Khởi chạy Worker & API
arq app.worker.tasks.WorkerSettings
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
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
