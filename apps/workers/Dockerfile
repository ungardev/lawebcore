FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

ARG RAILWAY_BUILD_ID=refactor
ENV RAILWAY_BUILD_ID=${RAILWAY_BUILD_ID}

WORKDIR /app

COPY packages/shared-core/pyproject.toml ./packages/shared-core/pyproject.toml
COPY packages/shared-ai/pyproject.toml ./packages/shared-ai/pyproject.toml
COPY packages/discovery/pyproject.toml ./packages/discovery/pyproject.toml
COPY apps/workers/pyproject.toml ./apps/workers/pyproject.toml

RUN pip install --upgrade pip && \
    pip install -e ./packages/shared-core \
                -e ./packages/shared-ai \
                -e ./packages/discovery \
                -e ./apps/workers

COPY apps/workers/app /app/app

CMD ["arq", "app.worker.WorkerSettings"]
