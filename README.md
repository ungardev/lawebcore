# La Web Core

> Plataforma interna de **La Web Figital Agency** para gestión integral de campañas de marketing, KPIs, operaciones de marca y producto, e Inteligencia Artificial.
>
> **El corazón y núcleo operativo de la agencia, todo en un solo producto.**

---

## LENS

**LENS** — *El sistema de discovery de influencers más inteligente de Venezuela.*

Con LENS, describe tu brief en lenguaje natural y recibe los mejores perfiles de Instagram verificados con scoring LWFA propietario — todo en minutos, no en días.

| Lo que hacían antes | Con LENS ahora |
|---|---|
| Búsqueda manual de 200+ perfiles en Instagram | Pipeline automatizado de 4 capas en segundos |
| Scoring genérico (followers/ER) | **4 KPIs LWFA exclusivos**: ICA, Geo-Foco Real, Engagement Velocity, Business Intent |
| Sin contexto VE | **Inteligencia local**: slang, hashtags reales, benchmarks VE |
| Sin filtro anti-bot | **Anti-bot filter**: descarta cuentas fake antes del enrichment |
| Sin inteligencia de nicho | **Sistema ELITE**: genera hashtags/keywords/geo adaptados a VE automáticamente |
| Apify directo ($$$) | **Cache inteligente Redis** → $0.30 por campaign vs $3.30 |

---

## Estado actual (Sprint 2 — Agosto 2026)

- ✅ Pipeline de 4 capas Apify deployed en Railway
- ✅ LWFA Scoring (4 KPIs exclusivos + composite 0-100)
- ✅ Sistema **ELITE** — generación automática de queries con inteligencia VE
- ✅ **Anti-bot filter** — descarta cuentas fake antes del enrichment
- ✅ **Redis cache layer** — $0.30 por campaign vs $3.30
- ✅ Discovery conversacional con DeepSeek-V3
- ✅ Chat conversacional + Brief Wizard + Búsqueda directa
- ✅ AI scoring: content_quality, audience_quality, brand_fit
- ✅ Propuesta CSV con top candidatos
- ✅ Railway deploy: `https://lawebcore-production.up.railway.app`
- ✅ 5 funciones ARQ worker activas

---

## Stack

- **Frontend:** React 19 + Vite + TypeScript + shadcn/ui + Tailwind + TanStack Query + Zustand
- **Backend:** FastAPI (Python 3.12 async) + SQLAlchemy 2.0 + Pydantic v2
- **DB / Auth / Storage:** Supabase (Postgres 16 + Auth + Storage + Realtime + pgvector)
- **Jobs async:** ARQ sobre Redis (Railway)
- **IA:** DeepSeek-V3 (LLM) + fastembed (embeddings) via pgvector
- **Discovery:** Apify (4 actores: search-scraper, hashtag-scraper, profile-scraper, engagement-analytics)
- **Hosting:** Vercel (FE) + Railway (API + workers + Redis) + Supabase Cloud (DB)
- **Monorepo:** pnpm workspaces

---

## Arquitectura del Pipeline de Discovery

```
[BRIEF: "Mascotas/Perros en VE para Purina Dog Chow, mujeres 25-45, tono aspiracional"]
                    ↓
╔═══════════════════════════════════════════════════════════════════╗
║  BRIEF PARSER (DeepSeek)                                          ║
║  Texto libre → BriefStructured (industry, niches, audience...)     ║
╚═══════════════════════════════════════════════════════════════════╝
                    ↓
╔═══════════════════════════════════════════════════════════════════╗
║  PROFILE GENERATOR (DeepSeek) — Sistema ELITE                    ║
║  BriefStructured → DiscoveryProfile con elite_data                 ║
║  Genera: hashtags, keywords, geo_indicators, buy_intent_keywords ║
║  + elite_data: content_themes, local_slang, credibility_signals,  ║
║    anti_bot_signals, niche_benchmarks, competitor_intel,           ║
║    geo_local_signals, query_variations                            ║
╚═══════════════════════════════════════════════════════════════════╝
                    ↓
╔═══════════════════════════════════════════════════════════════════╗
║  WORKER (ARQ)                                                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  STEP 1: KEYWORD DISCOVERY (Apify)                               ║
║    Method: search_users_by_multiple_keywords()                    ║
║    Output: handles únicos de keyword search                        ║
╠═══════════════════════════════════════════════════════════════════╣
║  STEP 2: HASHTAG DEEP DIVE (Apify)                              ║
║    Method: scrape_hashtags_batch()                                ║
║    Output: posts con geotags + engagement data                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  STEP 3: PRE-FILTER + ENRICHMENT (Apify)                        ║
║    Pre-filter: geo_score + niche_relevance + anti_bot_signals     ║
║    Enrich: top 25 handles con datos oficiales IG                   ║
╠═══════════════════════════════════════════════════════════════════╣
║  STEP 4: SCORING                                                  ║
║    geo_score (≥0.85 threshold)                                   ║
║    lens_score (0-100): tier_norm_er + geo + niche + business     ║
║    cross-reference bonus (STEP1 + STEP2)                          ║
╠═══════════════════════════════════════════════════════════════════╣
║  STEP 5: AI ANALYSIS (DeepSeek)                                  ║
║    content_quality, audience_quality, brand_fit (0-100)         ║
║    Usa elite_data para scoring contextualizado                     ║
╚═══════════════════════════════════════════════════════════════════╝
                    ↓
[TOP CANDIDATES → discovery_candidates DB]
```

---

## Sistema ELITE — Inteligencia Automática por Brief

El `profile_generator.py` analiza cada brief y genera automáticamente:

### Datos estándar
- **hashtags** — 20-30 hashtags que la gente USA realmente en el país
- **keywords** — 15-25 frases de búsqueda reales
- **niche_keywords** — términos del nicho en español
- **geo_indicators** — capitales, ciudades, gentilicios, abreviaturas, emoji bandera
- **buy_intent_keywords** — en idioma y moneda local (bs, $, pesos)

### elite_data (JSONB) — Generado por DeepSeek por cada brief
| Campo | Descripción |
|-------|-------------|
| `content_themes` | Tipos de contenido winners para el nicho en IG VE |
| `audience_behavior` | posting_hours, best_days, content_formats, engagement_pattern |
| `competitor_intel` | brands, hashtags, strategies de competidores en VE |
| `local_slang` | Slang VE: panas, jeva, chamo, fulete, peluche... |
| `credibility_signals` | Señales de perfil real: external_url, email in bio... |
| `niche_benchmarks` | min_followers, min_er, target_er, ideal_range |
| `anti_bot_signals` | Patrones de cuentas fake/bot específicos del nicho |
| `geo_local_signals` | Neighborhoods por ciudad, wealth_areas, trending_areas |
| `query_variations` | hashtag_stacking, keyword_combinations efectivos |

---

## LWFA Scoring — Los 4 KPIs Exclusivos

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

### Benchmarks LWFA (9 tiers)

| Tier | Followers | ER Range |
|------|-----------|----------|
| NANO_BAJO | 500–2K | 8–15% |
| NANO_ALTO | 2K–10K | 6–12% |
| MICRO_BAJO | 10K–30K | 4–10% |
| MICRO_MEDIO | 30K–100K | 3–8% |
| MICRO_ALTO | 100K–500K | 2–6% |
| MID_BAJO | 500K–1M | 1.5–5% |
| MID_ALTO | 1M–5M | 1–4% |
| MACRO_BAJO | 5M–10M | 0.5–2% |
| MACRO_ALTO | 10M+ | 0.3–1% |

---

## Estructura del monorepo

```
lawebcore/
├── apps/
│   ├── web/              # React 19 + Vite + shadcn/ui — Vercel
│   │   └── src/
│   │       ├── features/ # auth, campaigns, clients, lens, influencers...
│   │       ├── components/ # Shared UI
│   │       └── lib/ # API clients, utils
│   └── api/              # FastAPI backend — Railway
│       └── app/
│           ├── api/v1/   # 40+ endpoints
│           ├── core/     # security, metrics, rate_limiter
│           ├── models/   # SQLAlchemy ORM
│           ├── services/ # AI service, proposal generator
│           └── workers/  # ARQ worker (discovery_run_task, cron)
├── packages/
│   ├── discovery/         # ★ LENS Discovery Module
│   │   └── discovery/
│   │       ├── orchestrator.py     # State machine (START→BRIEF→SEARCHING→DONE)
│   │       ├── brief_parser.py     # Brief → BriefStructured (DeepSeek)
│   │       ├── profile_generator.py # ELITE system (DeepSeek)
│   │       ├── candidate_analyzer.py # AI scoring (DeepSeek)
│   │       ├── query_builder.py    # Brief → DiscoveryPlan
│   │       ├── memory.py          # Conversation persistence
│   │       ├── scoring/
│   │       │   ├── lens_score.py  # Unified 0-100 score
│   │       │   └── niche.py       # Niche relevance
│   │       └── tools/
│   │           ├── apify_client.py     # 4 actores + Redis cache
│   │           ├── geo_boost.py        # Geographic + tier scoring
│   │           └── multi_actor_instagram.py # Fallback chain
│   ├── shared-core/      # Config, DB, Supabase REST
│   └── shared-ai/        # DeepSeek client, fastembed embeddings
├── supabase/
│   ├── migrations/       # 30+ SQL migrations
│   ├── schema.sql        # Schema consolidado
│   └── seed*.sql         # Seed data
└── docs/                 # LAWEBCORE_PROYECTO_COMPLETO.md, MASTER_PROMPT_CLAUDE_CODE_FABLE_5.md
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

### 3. Backend (FastAPI)
```bash
cd apps/api
pip install -e ".[dev]"
cp ../../.env.example .env
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/api/docs
```

### 4. Frontend (React)
```bash
cd apps/web
pnpm install
pnpm dev
```

---

## Variables de entorno

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Connection string asyncpg (Railway Postgres) |
| `ARQ_REDIS_URL` | Redis para ARQ workers |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Supabase |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` | DeepSeek-V3 |
| `APIFY_API_KEY` | Source principal de datos |
| `ENABLE_AI_ANALYZER` | Flag para activar scoring AI |
| `METRICOOL_ACCESS_TOKEN` | Métricas de redes propias |
| `ADMIN_TOKEN` | JWT secret |

---

## Deploy

### Railway (API + workers + Redis)
- URL: `https://lawebcore-production.up.railway.app`
- Conectar el repo en [railway.app](https://railway.app)
- Servicio `api` → `apps/api/Dockerfile`
- Redis como add-on

### Vercel (Frontend)
- URL: `https://lawebcore.vercel.app`
- Conectar el repo en [vercel.com](https://vercel.com)
- Root directory: `apps/web`

---

## Costos operacionales (Optimizados Agosto 2026)

### Por campaign (sin cache): ~$3.30
| Step | Costo |
|------|-------|
| Keyword search | ~$1.30 |
| Hashtag posts | ~$1.43 |
| Profile enrichment (80) | ~$0.21 |
| Engagement analytics | ~$0.36 |

### Por campaign (con cache Redis): **~$0.30**
| Step | Costo |
|------|-------|
| Keyword search | ~$0.05 |
| Hashtag posts | ~$0.05 |
| Profile enrichment (25) | ~$0.05 |
| Engagement analytics | ~$0.15 |

### Presupuesto mensual: $250 USD ($200 APIs + $50 infra)

---

## Roadmap

| Sprint | Fecha | Entregable |
|---|---|---|
| **Sprint 1** ✅ | Jul 20 | Pipeline 4 capas Apify + LWFA Scoring |
| **Sprint 2** ✅ | Ago 4 | Sistema ELITE + Anti-bot + Redis cache + Fixes |
| **Sprint 3** | Ago 11 | TikTok Research API + Outreach automation |
| **Sprint 4** | Ago 18 | Multi-bu/multi-tenant + BI dashboard |

---

## Documentación clave

| Documento | Qué describe |
|---|---|
| [docs/LAWEBCORE_PROYECTO_COMPLETO.md](docs/LAWEBCORE_PROYECTO_COMPLETO.md) | Análisis exhaustivo del proyecto completo |
| [docs/MASTER_PROMPT_CLAUDE_CODE_FABLE_5.md](docs/MASTER_PROMPT_CLAUDE_CODE_FABLE_5.md) | Prompt para análisis de oportunidades de mejora con Fable 5 |
| [docs/DISCOVERY_ARCHITECTURE.md](docs/DISCOVERY_ARCHITECTURE.md) | Arquitectura completa del módulo Discovery |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitectura general del sistema |

---

## Decisiones técnicas

- **Source único de datos:** Apify (no Meta Graph API, no Excel, no mockup)
- **LLM:** DeepSeek-V3 únicamente (no OpenAI, no Anthropic)
- **Embeddings:** fastembed `all-MiniLM-L6-v2` via pgvector
- **Plataforma inicial:** Instagram únicamente (TikTok diferido Sprint 3)
- **Costo por campaign:** ~$0.30 con cache Redis
- **Benchmark ER VE:** 4-7% promedio (más alto que otros mercados latam)

---

## URLs de Producción

| Servicio | URL |
|----------|-----|
| API | `https://lawebcore-production.up.railway.app` |
| Frontend | `https://lawebcore.vercel.app` |
| Health | `https://lawebcore-production.up.railway.app/api/v1/health` |
| Metrics | `https://lawebcore-production.up.railway.app/metrics` |

---

## Licencia

Propietario - La Web Figital Agency. Todos los derechos reservados.
