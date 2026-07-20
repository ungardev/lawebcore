# La Web Core

> Plataforma interna de **La Web Figital Agency** para gestión integral de campañas de marketing, KPIs, operaciones de marca y producto, e Inteligencia Artificial.
>
> **El corazón y núcleo operativo de la agencia, todo en un solo producto.**
>
> **El Ojo que Todo lo Ve** — el módulo de discovery más potente de Venezuela, con pipeline de 4 capas Apify y LWFA Scoring propietario.

---

## El Ojo que Todo lo Ve

Sistema de descubrimiento de influencers que cambia las reglas del juego en Venezuela y LATAM.

| Competidor | Qué hacen | Qué hacemos nosotros |
|---|---|---|
| HypeAuditor | Filtros estáticos + datos genéricos | **Pipeline 4 capas + data local VE + scoring LWFA en tiempo real** |
| Modash | Dashboard de métricas | **Cerebro conversacional con contexto de campaña + Apify real** |
| Metricool | Analytics de cuentas propias | **Discovery de cuentas nuevas + datos oficiales de Instagram** |
| Apify (standalone) | Scraping puro | **Scraping + LWFA scoring + razonamiento IA** |

---

## Estado actual (Sprint 1 — Julio 2026)

- ✅ Pipeline de 4 capas Apify deployed en Railway
- ✅ LWFA Scoring (4 KPIs exclusivos + composite 0-100)
- ✅ Discovery conversacional con DeepSeek-V3
- ✅ 28 keywords estratégicas Gemini organizadas por categoría
- ✅ Railway deploy: `https://lawebcore-production.up.railway.app`
- ✅ 7 funciones ARQ worker cargadas

---

## Stack

- **Frontend:** React 19 + Vite + TypeScript + shadcn/ui + Tailwind + TanStack Query + Zustand
- **Backend:** FastAPI (Python 3.12 async) + SQLAlchemy 2.0 + Pydantic v2
- **DB / Auth / Storage:** Supabase (Postgres 16 + Auth + Storage + Realtime + pgvector)
- **Jobs async:** ARQ sobre Redis
- **IA:** DeepSeek-V3 (LLM) + fastembed (embeddings) via pgvector
- **Discovery:** Apify (3 actores: search-scraper, hashtag-scraper, profile-scraper, engagement-analytics)
- **Hosting:** Vercel (FE) + Railway (API + workers + Redis) + Supabase Cloud (DB)
- **Monorepo:** pnpm workspaces

---

## Arquitectura del Pipeline de Discovery

```
[BRIEF: "Mascotas/Perros en VE para Purina Dog Chow"]
                ↓
══════════════════════════════════════════════════════════
STEP 1: KEYWORD DISCOVERY
  Actor: apify/instagram-search-scraper
  Method: search_users_by_multiple_keywords()
  Input:  28 keywords Gemini (brand/lifecycle/personas/trends/nicho)
  Output: hasta 250 handles únicos con bio + followers
══════════════════════════════════════════════════════════
                ↓
══════════════════════════════════════════════════════════
STEP 2: HASHTAG DEEP DIVE
  Actor: apify/instagram-hashtag-scraper
  Method: scrape_hashtags_batch()
  Input:  22 hashtags estratégicos
  Output: ~660 posts con geotags + likes + comments + ownerUsername
══════════════════════════════════════════════════════════
                ↓
══════════════════════════════════════════════════════════
STEP 3: PROFILE ENRICHMENT
  Actor: apify/instagram-profile-scraper
  Method: search_instagram_profiles_batch()
  Input:  top 80 handles (STEP1 + STEP2 deduplicados)
  Output: followers + latestPosts + country (from about section)
══════════════════════════════════════════════════════════
                ↓
══════════════════════════════════════════════════════════
STEP 4: ENGAGEMENT ANALYTICS
  Actor: easy_scraper/instagram-profile-engagement-analytics
  Method: analyze_profile_engagement()
  Input:  top 20 handles × 30 posts cada uno
  Output: velocity, consistency_score, content_mix, comment_rate
══════════════════════════════════════════════════════════
                ↓
══════════════════════════════════════════════════════════
STEP 5: LWFA SCORING (4 KPIs exclusivos)
  1. ICA — Index de Conversión Aparentada
  2. Geo-Foco Real — geotags × idioma captions
  3. Engagement Velocity — interacciones/día
  4. Business Intent — multilink + fb page + business account
  Output: Composite score 0-100 por candidato
══════════════════════════════════════════════════════════
```

---

## LWFA Scoring — Los 4 KPIs Exclusivos de La Web

### 1. ICA — Index de Conversión Aparentada
```python
# = (comentarios con keywords de compra / total comentarios) * 100
BUY_INTENT_KEYWORDS = ["precio", "donde", "link", "comprar", "tienda", "oferta", ...]
```

### 2. Geo-Foco Real
```python
# Cruza geotags VE (caracas, vzla, maracaibo...) + idioma captions
# Penaltiza perfiles con captions en inglés puro sin geotag VE
```

### 3. Engagement Velocity
```python
# = (likes + comments) / num_posts / días_desde_primera_publicacion
# Detecta perfiles que mantienen engagement constante vs. spikes
```

### 4. Business Intent Score
```python
# = 0.4*has_multilink + 0.4*has_facebook_page + 0.2*is_business_account
# Perfiles con intención comercial verificable
```

---

## Estructura del monorepo

```
lawebcore/
├── apps/
│   ├── web/              # React + Vite SPA (shadcn/ui) — Vercel
│   ├── api/              # FastAPI backend — Railway
│   └── workers/          # ARQ workers (discovery_run_task, etc.) — Railway
├── packages/
│   ├── shared-core/      # Config, DB, Supabase REST client
│   ├── shared-ai/        # DeepSeek client, embeddings
│   ├── discovery/         # ★ El Ojo que Todo lo Ve
│   │   └── discovery/
│   │       ├── __init__.py
│   │       ├── brief_parser.py     # DeepSeek brief parser
│   │       ├── orchestrator.py     # LangGraph state machine
│   │       ├── query_builder.py    # Gemini keywords → DiscoveryPlan
│   │       ├── result_ranker.py    # LWFA scoring (4 KPIs + composite)
│   │       ├── schemas.py          # BriefStructured, DiscoveryPlan
│   │       └── tools/
│   │           ├── apify_client.py  # 3 actores Apify + 6 métodos nuevos
│   │           ├── meta_client.py
│   │           ├── tiktok_client.py
│   │           ├── youtube_client.py
│   │           └── metricool_client.py
│   └── ui/               # Componentes compartidos
├── supabase/
│   ├── migrations/       # SQL migrations (1-11)
│   ├── functions/        # Edge Functions (Deno)
│   ├── seed.sql          # Roles, permisos, BUs, KPIs
│   └── seed_excel_data.sql
├── docs/                 # Documentación (ARCHITECTURE, DISCOVERY, etc.)
└── scripts/
    └── etl_excel.py
```

---

## Quickstart (desarrollo local)

### 1. Prerrequisitos
- Node >= 20, pnpm >= 9
- Python >= 3.12
- Docker (para Postgres + Redis locales)

### 2. Levantar servicios locales
```bash
docker compose up -d
```

### 3. Aplicar migraciones y seed
```bash
psql "postgresql://postgres:postgres@localhost:5432/lawebcore" -f supabase/migrations/00000000000001_extensions.sql
psql "postgresql://postgres:postgres@localhost:5432/lawebcore" -f supabase/seed.sql
```

### 4. Backend (FastAPI)
```bash
cd apps/api
pip install -e ".[dev]"
cp ../../.env.example .env
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/api/docs
```

### 5. Workers (ARQ)
```bash
cd apps/workers
pip install -e ../api
arq app.workers.worker.WorkerSettings
```

### 6. Frontend (React)
```bash
cd apps/web
pnpm install
pnpm dev
```

---

## Variables de entorno

| Variable | Descripción |
|---|---|
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | Credenciales de Supabase |
| `DATABASE_URL` | Connection string asyncpg |
| `REDIS_URL` / `ARQ_REDIS_URL` | Para ARQ workers |
| `DEEPSEEK_API_KEY` | LLM conversacional + scoring (único LLM usado) |
| `APIFY_API_KEY` | Source principal de datos — 3 actores Instagram |
| `METRICOOL_ACCESS_TOKEN` | Métricas de redes propias |
| `HYPEAUDITOR_API_KEY` | (pendiente Sprint 3) |

---

## Deploy

### Railway (API + workers + Redis)
- URL: `https://lawebcore-production.up.railway.app`
- Conectar el repo en [railway.app](https://railway.app)
- Servicio `api` → `apps/api/Dockerfile`
- Servicio `workers` → comando: `arq app.workers.worker.WorkerSettings`
- Redis como add-on

### Vercel (Frontend)
- URL: `https://lawebcore.vercel.app`
- Conectar el repo en [vercel.com](https://vercel.com)
- Root directory: `apps/web`

### Supabase Cloud (DB)
- Crear proyecto en [supabase.com](https://supabase.com)
- Aplicar migraciones + seed

---

## Costos operacionales (Sprint 1)

| Proveedor | Plan | Costo/mes | Uso |
|---|---|---|---|
| Apify | Free ($5 credit) | ~$0 | ~1.5 campañas con free tier |
| Apify | CEO ($25-29) | $25-29 | 9-10 campañas/mes |
| DeepSeek-V3 | Pay-per-use | $5-15 | 50 conversaciones/mes |
| Supabase | Free tier | $0 | DB + pgvector |
| Railway | Usage-based | ~$20 | API + workers + Redis |
| **Total Sprint 1** | | **~$25-45/mes** | |

---

## Roadmap

| Sprint | Fecha | Entregable |
|---|---|---|
| **Sprint 1** ✅ | Jul 20 | Pipeline 4 capas Apify + LWFA Scoring + Gemini keywords |
| **Sprint 2** | Jul 28 | End-to-end Purina Dog Chow demo + Redis cache + Meta for Developers |
| **Sprint 3** | Ago 4 | TikTok Research API + Outreach automation |
| **Sprint 4** | Ago 11 | Multi-bu / multi-tenant prep + BI dashboard |

Ver [docs/ROADMAP.md](docs/ROADMAP.md) para detalles completos.

---

## Documentación clave

| Documento | Qué describe |
|---|---|
| [docs/DISCOVERY_ARCHITECTURE.md](docs/DISCOVERY_ARCHITECTURE.md) | Arquitectura completa del módulo Discovery v2.0 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitectura general del sistema |
| [docs/CONTEXT_FOR_FABLE5.md](docs/CONTEXT_FOR_FABLE5.md) | Contexto para agent IA Fable 5 |
| [MONOREPO.md](MONOREPO.md) | Estructura del monorepo y rules de imports |

---

## Decisiones técnicas cerradas (Sprint 1)

- **Source único de datos:** Apify (no Meta Graph API, no Excel, no mockup)
- **LLM:** DeepSeek-V3 únicamente (no OpenAI, no Anthropic)
- **Embeddings:** fastembed `all-MiniLM-L6-v2` via pgvector
- **Mockup data:** DEPRECATED — stats built from real system usage
- **Plataforma inicial:** Instagram únicamente (TikTok diferido)
- **Meta for Developers:** diferido a Sprint 2 (2-6 semanas de approval)
- **Costo por campaña:** ~$3.30 con Apify Free tier

---

## Licencia

Propietario - La Web Figital Agency. Todos los derechos reservados.
