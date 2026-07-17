FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

ARG RAILWAY_BUILD_ID=refactor
ENV RAILWAY_BUILD_ID=${RAILWAY_BUILD_ID}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY packages/shared-core/pyproject.toml ./packages/shared-core/pyproject.toml
RUN pip install --upgrade pip && pip install packages/shared-core

COPY packages/shared-ai/pyproject.toml ./packages/shared-ai/pyproject.toml
RUN pip install packages/shared-ai

COPY packages/discovery/pyproject.toml ./packages/discovery/pyproject.toml
RUN pip install packages/discovery

COPY apps/workers/pyproject.toml ./apps/workers/pyproject.toml
RUN pip install apps/workers

COPY apps/workers/app /app/app

CMD ["arq", "app.worker.WorkerSettings"]
