# Hạ Tầng Cơ Sở Dữ Liệu (Database Infrastructure)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 5, 2026
> **Status:** Active (MVP Phase)

---

Tài liệu này quy định cấu hình hạ tầng cho các hệ thống lưu trữ của AetherTutor, tập trung vào việc tối ưu hóa tài nguyên thông qua Docker.

---

## 1. Chiến lược Lưu trữ (Storage Strategy)

AetherTutor sử dụng mô hình lưu trữ đa tầng để phục vụ kiến trúc RAG nâng cao:

| Loại dữ liệu | Công nghệ | Mục đích |
| :--- | :--- | :--- |
| **Relational (Quan hệ)** | PostgreSQL (Alpine) | Thông tin người dùng, Metadata tài liệu, Lịch sử học tập. |
| **Vector (Vectơ)** | ChromaDB | Lưu trữ embeddings và phục vụ tìm kiếm similarity. |
| **Graph (Đồ thị)** | NetworkX (In-memory) | Quản lý mối quan hệ giữa các thực thể tri thức (LightRAG). |

---

## 2. Cấu hình Docker (PostgreSQL)

Để giảm thiểu gánh nặng cho hệ thống Windows (theo yêu cầu của người dùng), PostgreSQL được triển khai với cấu hình tối thiểu nhưng vẫn đảm bảo tính ổn định cho MVP.

### Thông số kỹ thuật
- **Image:** `postgres:alpine` (Dung lượng cực nhẹ, dựa trên Alpine Linux).
- **CPU Limit:** `0.5 CPU` (Tránh tình trạng database chiếm dụng CPU khi index).
- **Memory Limit:** `512 MB` (Mức RAM tối thiểu để PostgreSQL chạy mượt mà cho các truy vấn đơn lẻ).
- **Persistence:** Volume được mapping ra thư mục `.docker-data/` để bảo toàn dữ liệu khi tắt container.

### Docker Compose Snippet
```yaml
services:
  db:
    image: postgres:alpine
    container_name: aethertutor-db
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    # Các cấu hình khác chi tiết tại file docker-compose.yml gốc
```

---

## 3. Cấu hình Kết nối (Connection)

Ứng dụng FastAPI chạy tại local sẽ kết nối vào database trong Docker thông qua các biến môi trường tại `.env`:

```env
POSTGRES_USER=aether_admin
POSTGRES_PASSWORD=... (Xem tại Secret Manager hoặc .env local)
DB_HOST=localhost
DB_PORT=5432
DATABASE_URL=postgresql://aether_admin:aether_secure_pass@localhost:5432/aethertutor
```

---

## 4. Quản lý Dữ liệu (Operations)

- **Thư mục dữ liệu:** `.docker-data/postgres` (Phải được thêm vào `.gitignore`).
- **Backup:** Sử dụng lệnh `pg_dump` từ local để sao lưu dữ liệu ra file `.sql`.
- **Migration:** Sử dụng **Alembic** để quản lý các thay đổi schema trong PostgreSQL.

---

> [!IMPORTANT]
> Toàn bộ thiết kế Schema chi tiết (Tables, Columns, Relationships) được quy định tại [Data_Model.md](Data_Model.md).
