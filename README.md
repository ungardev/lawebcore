# La Web Core

> El núcleo operativo de **La Web Figital Agency** — gestión integral de campañas de influencer marketing, discovery con IA propietario y scoring LWFA.

[![CI](https://github.com/ungardev/lawebcore/actions/workflows/ci.yml/badge.svg)](https://github.com/ungardev/lawebcore/actions)
[![Railway](https://img.shields.io/badge/Railway-Production-00d4aa?logo=railway)](https://railway.app)
[![Vercel](https://img.shields.io/badge/Vercel-Frontend-000000?logo=vercel)](https://vercel.com)

**Producción:** [API](https://lawebcore-production.up.railway.app) · [Frontend](https://lawebcore.vercel.app) · [Health](https://lawebcore-production.up.railway.app/api/v1/health)

---

## Qué es LaWebCore

Plataforma interna con 3 módulos核心:

| Módulo | Descripción |
|--------|-------------|
| **LENS** | Discovery de influencers — pipeline automatizado 4 capas con IA (HikerAPI + DeepSeek-V3) |
| **PIAR** | Scoring y benchmarking de publicaciones con KPIs propietarios LWFA |
| **Core** | Campañas, clientes, operaciones, KPIs y métricas |

---

## LENS — Discovery de Influencers

Describe tu brief en lenguaje natural y recibe los mejores perfiles verificados con scoring LWFA — todo en minutos, no en días.

### Pain points antes / después

| Antes | Con LENS |
|-------|---------|
| Búsqueda manual de 200+ perfiles | Pipeline automatizado de 4 capas en segundos |
| Scoring genérico (followers/ER) | **4 KPIs LWFA exclusivos**: ICA, Geo-Foco, Engagement Velocity, Business Intent |
| Sin contexto VE | **Inteligencia local**: slang VE, hashtags reales, benchmarks VE |
| Sin filtro anti-bot | Filtro anti-bot: descarta cuentas fake antes del enrichment |
| Sin inteligencia de nicho | **Sistema ELITE**: hashtags/keywords/geo adaptados a VE automáticamente |
| HikerAPI directo ($$$) | **Cache Redis** → ~$0.30 por campaign |

### Arquitectura del Pipeline

```
[BRIEF: "Mascotas/Perros en VE, mujeres 25-45"]
                    ↓
╔══════════════════════════════════════════╗
║  BRIEF PARSER (DeepSeek-V3)             ║
║  Texto libre → BriefStructured          ║
╚══════════════════════════════════════════╝
                    ↓
╔══════════════════════════════════════════╗
║  PROFILE GENERATOR — Sistema ELITE      ║
║  BriefStructured → elite_data JSONB     ║
║  hashtags · keywords · geo_indicators   ║
║  · local_slang · credibility_signals   ║
╚══════════════════════════════════════════╝
                    ↓
╔══════════════════════════════════════════╗
║  WORKER (ARQ — Railway)                ║
╠══════════════════════════════════════════╣
║  STEP 1: Hashtag Search (HikerAPI)     ║
║  STEP 2: Keyword Search (HikerAPI)      ║
║  STEP 3: Profile Enrichment (HikerAPI)  ║
║  STEP 4: Scoring (LWFA + DeepSeek)     ║
╚══════════════════════════════════════════╝
                    ↓
[CANDIDATES → discovery_candidates DB]
```

### Sistema ELITE — Inteligencia Automática por Brief

Generado por DeepSeek-V3 para cada brief:

| Campo | Descripción |
|-------|-------------|
| `hashtags` | 20-30 hashtags reales usados en el país |
| `keywords` | 15-25 frases de búsqueda reales |
| `local_slang` | Slang VE: panas, jeva, chamo, fulete... |
| `content_themes` | Tipos de contenido winners para el nicho en IG VE |
| `credibility_signals` | Señales de perfil real: external_url, email in bio... |
| `anti_bot_signals` | Patrones de cuentas fake específicas del nicho |
| `niche_benchmarks` | min_followers, min_ER, target_ER, ideal_range |

### 9 Sub-Tiers LWFA

| Sub-Tier | Followers | Sub-Tier | Followers |
|----------|-----------|----------|-----------|
| `NANO_BAJO` | 500–2K | `MID_BAJO` | 500K–1M |
| `NANO_ALTO` | 2K–10K | `MID_ALTO` | 1M–5M |
| `MICRO_BAJO` | 10K–30K | `MACRO_BAJO` | 5M–10M |
| `MICRO_MEDIO` | 30K–100K | `MACRO_ALTO` | 10M+ |
| `MICRO_ALTO` | 100K–500K | | |

### 13 Estados de Run (RunStatus)

```
pending → queued → running → delivered  (éxito completo)
                           → degraded   (parcial + warnings)
                           → empty      (0 candidatos)
                           → inconsistent (datos corruptos)
                           → aborted_budget (saldo agotado)
                    → partial   (resultados mixtos)
                    → explored  (modo explorar sin enrichment)
              → completed  (legado)
              → failed     (error)
              → cancelled  (usuario canceló)
```

### KPIs Exclusivos LWFA

| KPI | Fórmula | Qué mide |
|-----|---------|---------|
| **ICA** | `(comentarios con keywords de compra / total comentarios) * 100` | Intención de compra real |
| **Geo-Foco Real** | Geotags VE + idioma captions | Perfiles con audiencia VE verificable |
| **Engagement Velocity** | `(likes + comments) / posts / días` | Engagement constante vs. spikes |
| **Business Intent** | `0.4*multilink + 0.4*facebook_page + 0.2*business_account` | Señales comerciales verificables |

---

## Stack de Tecnología

```
Frontend   React 19 + Vite 6 + TypeScript 5.7 + Tailwind CSS
           shadcn/ui + Radix UI + Zustand + TanStack Query + Sonner
           Vitest 2.1 (testing)

Backend    FastAPI (Python 3.12 async) + SQLAlchemy 2.0 + Pydantic v2
           ARQ (Redis) + Uvicorn

DB / Cache PostgreSQL 16 (Railway) + Redis 8.2 (Railway)

AI         DeepSeek-V3 (LLM) + fastembed all-MiniLM-L6-v2 (embeddings)

Discovery  HikerAPI (hashtag/keyword/enrichment — 4 endpoints)

Infra      Vercel (Frontend) + Railway (API + workers) + Supabase Cloud
```

### Monorepo Structure

```
lawebcore/
├── apps/
│   ├── web/                   # React 19 — Vercel
│   │   └── src/features/     # auth, campaigns, clients, lens, influencers...
│   └── api/                  # FastAPI — Railway
│       └── app/
│           ├── api/v1/       # 40+ endpoints
│           ├── core/         # security, metrics, rate_limiter, budget_fuse
│           ├── models/       # SQLAlchemy ORM
│           ├── workers/       # ARQ worker
│           └── tests/         # pytest (139 tests passing)
├── packages/
│   ├── discovery/            # ★ LENS module
│   │   └── discovery/
│   │       ├── orchestrator.py    # State machine
│   │       ├── brief_parser.py    # DeepSeek brief parsing
│   │       ├── profile_generator.py # ELITE system
│   │       ├── candidate_analyzer.py # AI scoring
│   │       └── tools/hikerapi_client.py
│   ├── shared-core/          # Config, DB, Supabase REST
│   └── shared-ai/            # DeepSeek client, fastembed
└── supabase/
    ├── migrations/           # 110+ migraciones SQL
    └── seed*.sql             # Seed data
```

---

## Quickstart — Desarrollo Local

### Prerrequisitos
- Node >= 20, pnpm >= 9
- Python >= 3.12
- Docker

### 1. Instalar y levantar servicios
```bash
git clone https://github.com/ungardev/lawebcore.git && cd lawebcore
pnpm install
docker compose up -d
```

### 2. Backend
```bash
cd apps/api
pip install -e ".[dev]"
cp ../../.env.example .env   # configurar DATABASE_URL y API keys
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/api/docs
```

### 3. Frontend
```bash
cd apps/web
pnpm dev
# http://localhost:5173
```

### 4. Verificar
```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","service":"lawebcore-api","version":"0.1.0"}
```

### 5. Tests
```bash
# Backend
cd apps/api && pytest --ignore=tests/test_budget_fuse.py

# Frontend
cd apps/web && pnpm test --passWithNoTests
```

---

## Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Connection string asyncpg (Railway Postgres) |
| `ARQ_REDIS_URL` | Redis para ARQ workers |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Supabase |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` | DeepSeek-V3 |
| `HIKERAPI_API_KEY` | Source de datos (discovery/enrichment) |
| `ADMIN_TOKEN` | JWT secret |
| `API_ENV` | `development` / `production` |

> Ver `.env.example` en `apps/api/` para la configuración completa.

---

## Sistema de Migraciones

Railway tiene **DOS mecanismos** que NO deben confundirse:

| Mecanismo | Ejecuta | Se ejecuta automáticamente? |
|-----------|---------|------------------------------|
| `apply_migrations.py` | Solo `schema.sql` | ✅ Solo al primer deploy |
| `memory.py::migrate_*()` | `ALTER TABLE ADD COLUMN` | ✅ Cada startup de Railway |
| **`supabase/migrations/*.sql`** | Migraciones numeradas | ❌ **Manual — vía SQL Editor Railway** |

**Importante:** Cada vez que se agregue una tabla o ENUM, ejecutar la migración manualmente contra Railway PostgreSQL.

---

## Documentación Clave

| Documento | Qué describe |
|-----------|-------------|
| [docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md](docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md) | Estado completo LENS — Hitos 30-35 |
| [docs/PROMPT_CLAUDE_CODE_ANALYSIS.md](docs/PROMPT_CLAUDE_CODE_ANALYSIS.md) | Índice de auditorías y análisis |
| [docs/FIXES_FRONTEND_LENS_C0-C2_27-08-26.md](docs/FIXES_FRONTEND_LENS_C0-C2_27-08-26.md) | Fixes de acoplamiento frontend |
| [docs/DISCOVERY_ARCHITECTURE.md](docs/DISCOVERY_ARCHITECTURE.md) | Arquitectura del módulo Discovery |
| [docs/13a_data_contract_discovery.md](docs/13a_data_contract_discovery.md) | Contrato de datos entre componentes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitectura general del sistema |

---

## Hitos Completados (LENS — Hitos 30-35)

| Hito | Descripción | Fecha |
|------|-------------|-------|
| **Hito 30** | Observabilidad: RunEvent, DropLedger, FunnelTracker, 6 statuses nuevos | Ago 2026 |
| **Hito 31** | Normalización datos, dual-name elimination, zero patterns | Ago 2026 |
| **Hito 32** | 9 sub-tiers LWFA, deduplicación handle, UPSERT social accounts | Ago 2026 |
| **Hito 33** | Config constants centralizadas | Ago 2026 |
| **Hito 34** | JSON object response_format, regex extraction eliminada, DeepSeek-v3 | Ago 2026 |
| **Hito 35** | 8 fixes regresión backend + frontend C-0/C-1/C-2 coupling | Ago 2026 |

---

## Deploy

### Railway (API + workers)
URL: `https://lawebcore-production.up.railway.app`
- Auto-deploys on push to `main`
- Dockerfile: `apps/api/Dockerfile`
- Redis como add-on

### Vercel (Frontend)
URL: `https://lawebcore.vercel.app`
- Auto-deploys on push to `main`
- Root directory: `apps/web`

---

## Licencia

Propietario — La Web Figital Agency. Todos los derechos reservados.
