FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install workers runtime dependencies (arq, redis, pydantic, langchain, etc.)
COPY apps/workers/pyproject.toml ./pyproject.toml
RUN pip install --upgrade pip && pip install -e .

# Layer 1: Workers' own code (provides /app/app/worker.py and /app/app/__init__.py)
COPY apps/workers/app /app/app

# Layer 2: API modules overlay onto /app/app/
# Docker COPY does NOT delete files only present in destination, so
# /app/app/worker.py (from layer 1) is preserved even though apps/api/app/ has no worker.py
# apps/api/app/ has no worker.py (verified), so COPY cannot overwrite it
# Result: single unified /app/app/ tree, no namespace collisions
COPY apps/api/app /app/app

CMD ["arq", "app.worker.WorkerSettings"]
