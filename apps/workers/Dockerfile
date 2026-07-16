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

# Layer 1: API code first — this is the layer that changes most often
# When apps/api/ files change, this layer is invalidated and rebuilt
COPY apps/api/app /app/app

# Layer 2: Worker code on top — this layer's files (worker.py, config, etc.)
# are copied AFTER the API layer, so they take precedence
COPY apps/workers/app /app/app

# Install workers runtime dependencies (arq, redis, pydantic, langchain, etc.)
COPY apps/workers/pyproject.toml ./pyproject.toml
RUN pip install --upgrade pip && pip install -e .

CMD ["arq", "app.worker.WorkerSettings"]
