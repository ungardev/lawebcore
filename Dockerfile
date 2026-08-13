FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/shared-core ./packages/shared-core
COPY packages/shared-ai ./packages/shared-ai
COPY packages/discovery ./packages/discovery
COPY apps/api ./apps/api
COPY scripts/ ./scripts/

RUN pip install --upgrade pip && \
    pip install -e ./packages/shared-core \
                -e ./packages/shared-ai \
                -e ./packages/discovery \
                -e ./apps/api

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
