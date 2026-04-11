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

## 🔧 Docker Maintenance & Cleanup

### Log Rotation
Tất cả service đều được giới hạn log để tránh phình dung lượng:

| Mode | Max Size | Max Files | Total/Service |
|------|----------|-----------|---------------|
| **Production** (`docker-compose.yml`) | 50MB | 5 | ~250MB |
| **Development** (override tự động merge) | 100MB | 10 | ~1GB |

### WSL2 .vhdx Cleanup (Windows)
Docker Desktop trên Windows dùng file `.vhdx` — tự mở rộng nhưng KHÔNG tự thu nhỏ.
Để giảm dung lượng sau khi xóa dữ liệu bên trong:

```powershell
# 1. Dừng Docker Desktop hoàn toàn
# 2. Compact file vhdx (đường dẫn có thể khác tùy version)
Optimize-VHD -Path "$env:LOCALAPPDATA\Docker\wsl\data\ext4.vhdx" -Mode Full
# Hoặc dùng diskpart (built-in Windows):
diskpart
  select vdisk file="%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"
  attach vdisk readonly
  compact vdisk
  detach vdisk
  exit
```

### Dọn dẹp Docker định kỳ
```bash
# Xóa dangling images (image cũ không còn dùng)
docker image prune -f

# Xóa unused images, containers, volumes, networks
docker system prune -f

# Xóa TẤT CẢ (kể cả volumes — CẢ THẬN: mất data DB)
docker system prune --volumes -f
```

### Khi nào cần cleanup?
- Sau nhiều lần `docker compose up --build` (tích tụ image layers)
- Khi Docker Desktop báo "Disk image is using X GB"
- Khi container không khởi động được do hết dung lượng

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
