FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app_api:/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Build context is repo root (/)
COPY apps/workers/pyproject.toml ./pyproject.toml
RUN pip install --upgrade pip && pip install -e .

COPY apps/workers/. .

# Shared API code: bring in apps/api/app so worker.py can import app.core.*, app.discovery.*, app.ai.*
COPY apps/api/app /app_api/app

CMD ["arq", "app.worker.WorkerSettings"]
