FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/shared-core/pyproject.toml ./packages/shared-core/pyproject.toml
RUN pip install --upgrade pip && pip install packages/shared-core

COPY packages/shared-ai/pyproject.toml ./packages/shared-ai/pyproject.toml
RUN pip install packages/shared-ai

COPY packages/discovery/pyproject.toml ./packages/discovery/pyproject.toml
RUN pip install packages/discovery

COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
RUN pip install apps/api

COPY apps/api/app /app/app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
