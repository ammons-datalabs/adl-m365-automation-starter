# Slim, fast, production-friendly
FROM python:3.11-slim

# System deps (if you use psycopg2, tesseract, etc. add here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Leverage layer caching for deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . /app

# FastAPI app is in src.api.main:app
ENV MODULE_PATH=src.api.main:app
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Use Uvicorn in production mode
CMD ["sh", "-c", "uvicorn $MODULE_PATH --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'"]
