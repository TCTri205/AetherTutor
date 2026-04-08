# ==========================================
# Stage 1: Builder — Cài đặt dependencies
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài đặt system dependencies cần thiết để compile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==========================================
# Stage 2: Runtime — Chỉ copy những gì cần thiết
# ==========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy dependencies từ builder stage
COPY --from=builder /install /usr/local

# Copy source code (không include những file trong .dockerignore)
COPY alembic/ alembic/
COPY alembic.ini .
COPY app/ app/

# Tạo non-root user để chạy ứng dụng
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --uid 1001 --gid appuser --shell /bin/bash appuser && \
    mkdir -p /app/uploads && \
    chown -R appuser:appuser /app
USER appuser

# Biến môi trường
ENV PYTHONPATH=/app
ENV APP_ENV=production

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# CMD mặc định
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
