# ── Stage 1: build ────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System deps for OpenCV and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY data/cameras.json ./data/cameras.json

# ── Runtime ───────────────────────────────────────────────────────────────
WORKDIR /app/backend

# Env vars (all required at runtime — no defaults hardcoded here)
# DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
# Optional: MODEL_DIR (default: ../ml/weights)

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
