FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY packages/shared-core/pyproject.toml ./packages/shared-core/pyproject.toml
COPY packages/shared-ai/pyproject.toml ./packages/shared-ai/pyproject.toml
COPY packages/discovery/pyproject.toml ./packages/discovery/pyproject.toml
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml

RUN pip install --upgrade pip && \
    pip install -e ./packages/shared-core \
                -e ./packages/shared-ai \
                -e ./packages/discovery \
                -e ./apps/api

COPY apps/api/app /app/app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
