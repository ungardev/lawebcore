# La Web Core — Monorepo Architecture

## Overview

La Web Core es un monorepo Python con arquitectura de packages compartidos. Contiene dos servicios desplegados en Railway: **API** (FastAPI) y **Workers** (ARQ).

## Structure

```
lawebcore/
├── packages/                      # Shared packages (editable installs)
│   ├── shared-core/              # Config, DB, Supabase REST client
│   │   ├── pyproject.toml
│   │   └── shared_core/
│   │       ├── __init__.py       # Exports: settings, db_session, get_db, supabase_rest, etc.
│   │       ├── config.py         # Pydantic Settings (env vars)
│   │       ├── db.py             # SQLAlchemy async session + init_db
│   │       └── supabase_rest.py  # Supabase REST client wrapper
│   │
│   ├── shared-ai/                # AI clients (DeepSeek, OpenAI, embeddings)
│   │   ├── pyproject.toml
│   │   └── shared_ai/
│   │       ├── __init__.py       # Exports: embed_text, embed_texts, deepseek_client, etc.
│   │       ├── deepseek_client.py
│   │       └── embeddings.py
│   │
│   └── discovery/                 # Discovery orchestrator, ranker, tools
│       ├── pyproject.toml
│       └── discovery/
│           ├── __init__.py
│           ├── brief_parser.py
│           ├── memory.py
│           ├── orchestrator.py
│           ├── query_builder.py
│           ├── result_ranker.py
│           ├── schemas.py
│           └── tools/            # Platform API clients (Apify, Meta, TikTok, YouTube, Metricool)
│
├── apps/
│   ├── api/                      # FastAPI application
│   │   ├── Dockerfile
│   │   ├── railway.toml         # Root Directory = /apps/api
│   │   ├── pyproject.toml
│   │   └── app/
│   │       ├── main.py          # Entry point (uvicorn)
│   │       ├── api/v1/          # Route modules
│   │       │   ├── discovery.py # Imports from packages/discovery/
│   │       │   └── ...
│   │       ├── core/            # App-specific: security, logging, piar_*, etc.
│   │       ├── ai/              # Hybrid: wrappers around shared_ai + app-specific
│   │       ├── models/
│   │       └── schemas/
│   │
│   └── workers/                  # ARQ async workers
│       ├── Dockerfile
│       ├── railway.toml         # Root Directory = /
│       ├── pyproject.toml
│       └── app/
│           ├── worker.py        # Entry point (arq)
│           └── core/
│               └── config.py    # Workers-specific config
│
└── railway.toml                  # Root: workers service build config
```

## Deployment

| Service | Root Directory | Dockerfile | Deploy |
|---------|---------------|------------|--------|
| Workers | `/` (repo root) | `apps/workers/Dockerfile` | `railway.toml` at root |
| API | `/apps/api` | `apps/api/Dockerfile` | `apps/api/railway.toml` |

### Railway Variables (both services)
```env
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
REDIS_URL=redis://...                    # Workers only
ARQ_REDIS_URL=redis://...                 # Workers only
SUPABASE_SERVICE_ROLE_KEY=...            # API + Workers
OPENAI_API_KEY=...                       # API + Workers
DEEPSEEK_API_KEY=...                      # API + Workers
ANTHROPIC_API_KEY=...                    # API + Workers
API_ENV=production                       # Both
```

## Development

### Local Setup

```bash
# Install all packages in editable mode
pip install -e ./packages/shared-core
pip install -e ./packages/shared-ai
pip install -e ./packages/discovery
pip install -e ./apps/workers
pip install -e ./apps/api

# Or use the Dockerfiles for a clean environment
docker build -f apps/workers/Dockerfile .
docker build -f apps/api/Dockerfile .
```

### Python Path

Both Dockerfiles set `PYTHONPATH=/app`. The `PYTHONPATH` ensures that when the code does `from shared_core import settings`, Python can find `shared_core` at `/app/packages/shared_core`.

## Import Rules

### Packages (`packages/*/`)
- **Never** declare `file:///...` URL dependencies on other local packages in `pyproject.toml`
- Install order in Dockerfile creates the effective dependency contract
- All packages are installed editable (`-e ./packages/X`) before any app

### Applications (`apps/*/`)
- Apps **do not** declare local package deps in `pyproject.toml` (no `shared-core @ file:///...`)
- Apps import from packages using standard Python imports: `from shared_core import settings`
- App-specific modules (`app.core`, `app.api`, etc.) are NOT shared; they live in the app

### Legacy Code Cleanup
The following directories were deleted (legacy duplicates replaced by packages):
- `apps/api/app/discovery/` — replaced by `packages/discovery/`
- `apps/api/app/integrations/` — empty directory, removed
- `apps/api/app/utils/` — empty directory, removed
- `test_apify_local.py` — dev script, removed

### Why `shared_core` lives in the API but Workers uses it too
- `shared_core` contains `settings`, `db_session`, `get_db`, `supabase_rest`
- The API imports from `shared_core` directly
- Workers import from `shared_core` directly
- Both get `shared_core` via `pip install -e ./packages/shared-core`
- The local `apps/api/app/core/{config,db,supabase_rest}.py` were **deleted** (consolidated into `shared_core`)
- `app.core` in the API still contains app-specific modules: `security.py`, `logging.py`, `piar_*.py`, `worker_enqueuer.py`, `cost_tracker.py`

## Packages vs App Code

| Import | Source | Notes |
|--------|--------|-------|
| `from shared_core import settings` | `packages/shared-core/shared_core/` | ✅ Canonical |
| `from app.core.config import settings` | ❌ Deleted — use `shared_core` | |
| `from app.core.db import get_db` | ❌ Deleted — use `shared_core` | |
| `from app.core.supabase_rest import supabase_rest` | ❌ Deleted — use `shared_core` | |
| `from shared_ai import embed_text` | `packages/shared-ai/shared_ai/` | ✅ Canonical |
| `from discovery import orchestrator` | `packages/discovery/discovery/` | ✅ Canonical |
| `from app.core.security import CurrentUserDep` | `apps/api/app/core/security.py` | App-specific |
| `from app.core.logging import configure_logging` | `apps/api/app/core/logging.py` | App-specific |
| `from app.ai.indexer import ...` | `apps/api/app/ai/indexer.py` | Hybrid (still in app) |
