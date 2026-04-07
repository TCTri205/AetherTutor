FROM python:3.11-slim

WORKDIR /app

# Cài đặt system dependencies cần thiết
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Biến môi trường mặc định (có thể override trong docker-compose)
ENV PYTHONPATH=/app
ENV APP_ENV=production

# Expose port (cho API)
EXPOSE 8000

# CMD mặc định là chạy API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
