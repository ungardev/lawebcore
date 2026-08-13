# La Web Core — Arquitectura Técnica

> **Versión:** 1.0 — Última actualización: 2026-08-13
> **Proyecto:** LENS Discovery Module — Influencer Discovery Pipeline
> **Cliente:** Nestlé Venezuela / Purina Dog Chow (demo)

---

## 1. Stack Tecnológico

### Backend
- **Framework:** FastAPI (Python 3.12 async) con Uvicorn
- **Workers:** ARQ sobre Redis para jobs asíncronos
- **ORM:** SQLAlchemy 2.0 + asyncpg
- **Validación:** Pydantic v2
- **Rate Limiting:** SlowAPI (300/min general, 30/min discovery)
- **Monitoreo:** Prometheus (`/metrics`), Sentry (producción)
- **Ubicación:** `apps/api/` — Deployado en Railway

### Frontend
- **Framework:** React 19 + TypeScript
- **Build:** Vite
- **Estilos:** Tailwind CSS + shadcn/ui
- **Estado:** TanStack Query + Zustand
- **Routing:** React Router v7
- **Gráficos:** Recharts
- **Ubicación:** `apps/web/` — Deployado en Vercel (`lawebcore.vercel.app`)

### Base de Datos
- **Motor:** PostgreSQL 16 via Supabase Cloud
- **Extensiones:** `uuid-ossp`, `pgcrypto`, `pg_trgm`, `vector` (pgvector)
- **Tablas:** 30+ incluyendo `discovery_runs`, `discovery_candidates`, `influencers`, `campaigns`
- **RLS:** Row-level security por `business_unit_id`, `client_id`, `team_id`

### Infraestructura
- **Backend:** Railway (`lawebcore-production.up.railway.app`)
- **Frontend:** Vercel (`lawebcore.vercel.app`)
- **Cache/Queue:** Redis via Railway
- **Container:** Docker (Python 3.12-slim)

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Vercel)                         │
│   React 19 + TypeScript + TanStack Query + Tailwind + shadcn/ui    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ HTTPS
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND API (Railway)                          │
│                   FastAPI + Uvicorn + ARQ Workers                   │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  /api/v1/*  │  │   /health    │  │   /metrics (Prometheus)  │  │
│  │  (40+ ep)   │  │   /ready     │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    ARQ WORKER (Redis)                         │  │
│  │   discovery_run_task() ← Pipeline principal de LENS          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  HikerAPI   │    │   DeepSeek-V3   │    │   Supabase DB   │
│ (Instagram) │    │   (AI/LLM)      │    │  (PostgreSQL)   │
└─────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│     Redis       │
│  (Cache/Queue)  │
└─────────────────┘
```

---

## 3. Módulos Principales

### 3.1 LENS Discovery Module (`packages/discovery/`)

Pipeline de descubrimiento de influencers para campañas de marketing.

```
[BRIEF INPUT]
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 0: Location Search (Opcional)                         │
│  - search_location() por ciudad                             │
│  - location_medias_top() + location_medias_recent()        │
│  - Output: perfiles geolocalizados                         │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Hashtag Search                                    │
│  - search_hashtag() → top posts por hashtag               │
│  - search_hashtag_recent() → nano/micro creators          │
│  - Fuente: HikerAPI                                        │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Keyword Search                                    │
│  - search_keyword() con sufijos geo ("perros vzla")       │
│  - search_top_accounts() → cuentas trending               │
│  - search_reels_by_keyword() → creadores de Reels        │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2.5: Network Expansion                               │
│  - suggested_profiles() → algoritmo de IG                 │
│  - search_followers_of() → red de seguidores             │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Profile Enrichment  ★ COSTO PRINCIPAL            │
│  - enrich_profile() por handle (followers, bio, etc.)     │
│  - get_user_about() → país, account_age, former_usernames│
│  - Anti-bot: ff_ratio > 10, bajo posts, señales commerce  │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Scoring (LWFA KPIs)                              │
│  - geo_score: geotags × idioma del caption               │
│  - ica: buy intent en comentarios                         │
│  - velocity: (likes + comments) / posts / días           │
│  - business_intent: multilink + fb page + business       │
│  - Bot filter: ER > 30% = bot                            │
│  - Country mismatch: .rd, .do, .mx TLDs descartados     │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: AI Analysis (DeepSeek) [OPCIONAL]                │
│  - content_quality, audience_quality, brand_fit (0-100)  │
│  - elite_data para scoring contextual                     │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
[TOP CANDIDATES] → discovery_candidates (DB)
```

### 3.2 Paquetes del Monorepo

| Paquete | Descripción |
|---------|-------------|
| `packages/discovery/` | LENS Discovery Module (pipeline de influencers) |
| `packages/shared-core/` | Configuración, DB, REST de Supabase |
| `packages/shared-ai/` | Cliente DeepSeek, embeddings |

---

## 4. APIs y Servicios Conectados

### 4.1 HikerAPI (Primary — Instagram Data)

```
Uso: Búsqueda de perfiles, enrichment, hashtags, keywords
Costo: ~$0.0006 USD por request
Documentación: https://api.hikerapi.com/docs
```

**Endpoints principales:**
| Método | Endpoint | Uso |
|--------|----------|-----|
| `search_hashtag()` | `/v2/hashtag/medias/top` | Top posts por hashtag |
| `search_hashtag_recent()` | `/v2/hashtag/medias/recent` | Posts recientes |
| `search_keyword()` | `/v2/fbsearch/accounts` | Cuentas por keyword |
| `search_top_accounts()` | `/v3/fbsearch/topsearch` | Cuentas trending |
| `enrich_profile()` | `/v1/user/by/username` | Datos completos de perfil |
| `get_user_about()` | `/v1/user/about` | País, account_age, former_usernames |
| `suggested_profiles()` | `/v2/user/suggested/profiles` | Cuentas sugeridas por IG |
| `search_location()` | `/v1/fbsearch/places` | Búsqueda de ubicaciones |
| `location_medias_top()` | `/v1/location/medias/top` | Posts top por ubicación |
| `location_medias_recent()` | `/v1/location/medias/recent/chunk` | Posts recientes por ubicación |

**Parámetros críticos:**
- ❌ `safe_int` causa 422 en `/gql/user/about`, `/v1/location/search`
- ✅ `/v1/user/about` usa `id` (no `user_id`)
- ✅ `/v1/location/medias/top` usa `location_pk` (no `id`)
- ✅ `/v1/fbsearch/places` usa `query` (búsqueda por texto)

### 4.2 Apify (Fallback/Legacy — DESHABILITADO)

```
Estado: CONFIGURED BUT DISABLED
Nota: Retorna 404 — actors no disponibles o deshabilitados
```

**Actors configurados pero no funcionales:**
- `apify/instagram-search-scraper` → busca por hashtag/keyword
- `apify/instagram-hashtag-scraper` → posts por hashtag
- `apify/instagram-profile-scraper` → datos de perfil
- `apify/instagram-engagement-analytics` → métricas de engagement

### 4.3 DeepSeek-V3 (AI/LLM)

```
Uso: Parsing de brief, generación de perfiles, scoring AI
Modelo: deepseek-chat
Costo: ~$0.001 USD por 1K tokens (cache habilitado)
```

### 4.4 Supabase (Database + Auth + Storage)

```
Uso: Datos persistentes, autenticación, вектор embeddings
Ubicación: postgres.railway.internal:5432/railway
```

---

## 5. Modelo de Datos — Discovery

### Tablas Principales

```
discovery_runs
├── id (UUID)
├── brief (JSON) — brief estructurado
├── status — pending | running | completed | failed
├── total_candidates — conteo final
├── actual_cost_usd — costo en USD
├── created_at, updated_at
└── business_unit_id (FK)

discovery_candidates
├── id (UUID)
├── run_id (FK → discovery_runs)
├── handle — @username
├── match_score — score 0-100
├── tier — nano | micro | mid | macro
├── followers, following, posts
├── engagement_rate
├── geo_relevance, niche_relevance
├── enriched_data (JSON) — datos de HikerAPI
├── ai_analysis (JSON) — scoring de DeepSeek
└── created_at

discovery_conversations
├── id (UUID)
├── run_id (FK, nullable)
├── brief (JSON) — brief acumulado
├── messages (JSON) — conversación
└── accumulated_brief, parsed_brief_json

discovery_profiles
├── id (UUID)
├── brief_id — fingerprint del brief
├── profile_data (JSON) — datos del perfil generado
└── cached_at
```

---

## 6. Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:***@postgres.railway.internal:5432/railway

# Redis (ARQ Workers)
ARQ_REDIS_URL=redis://default:***@hopper.proxy.rlwy.net:34537

# APIs
HIKERAPI_API_KEY=***          # Instagram data (PRIMARY)
APIFY_API_KEY=apify_api_***   # Instagram data (FALLBACK/DISABLED)
DEEPSEEK_API_KEY=sk-***       # AI/LLM

# Config
INSTAGRAM_SOURCE=hikerapi      # hikerapi | apify | hybrid
ENABLE_AI_ANALYZER=false      # Toggle AI scoring
API_ENV=production
ADMIN_TOKEN=***
```

---

## 7. Costos del Pipeline

### Desglose por Step (1 run completa)

| Step | Método | Llamadas máx | Costo aprox |
|------|--------|--------------|-------------|
| STEP 0 | Location search | 42 | $0.025 |
| STEP 1 | Hashtags | 33 | $0.020 |
| STEP 2 | Keywords | 24 | $0.014 |
| STEP 2.5 | Reels + Expansion | 6 | $0.004 |
| STEP 3 | Top Search | 2 | $0.001 |
| STEP 4 | Suggested | 4 | $0.002 |
| **STEP 3 Enrich** | **enrich_profile** | **50** | **$0.030** |
| **STEP 3 About** | **get_user_about** | **50** | **$0.030** |
| **TOTAL** | | **~211** | **~$0.13** |

### Configuración ULTRA-ECONÓMICA (testing)

| Step | Original | Optimizado | Reducción |
|------|----------|------------|-----------|
| `MAX_HANDLES_TO_ENRICH` | 500 | **50** | -90% |
| `get_user_about` | Enabled | **Disabled** | -50 calls |
| Hashtags (top) | 6 | **3** | -50% |
| Hashtags (recent) | 3 | **2** | -33% |
| Keywords | 8 | **3** | -63% |
| STEP 0 (Location) | Enabled | **Disabled** | -42 calls |
| Follower expansion | 2 seeds | **Disabled** | -4 calls |
| Top Search | 2 | **Disabled** | -2 calls |

**Resultado: ~60 calls/run = ~$0.04 USD/run**

---

## 8. Flujo de Desarrollo Local

```bash
# 1. Levantar servicios (Postgres + Redis)
docker-compose up -d

# 2. Instalar dependencias
npm install

# 3. Configurar env
cp apps/api/.env.example apps/api/.env
# Editar HIKERAPI_API_KEY

# 4. Correr migraciones
cd apps/api && npm run db:migrate

# 5. Iniciar backend (dev)
npm run dev:api

# 6. Iniciar frontend (dev)
npm run dev:web

# 7. Test discovery (desde Railway shell)
cd /app/apps/api && python3 scripts/test_purina_dogchow.py
```

---

## 9. Railway Deployment

```toml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers'"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
healthcheckPath = "/api/v1/health"
```

**Variables de entorno en Railway:**
- `HIKERAPI_API_KEY` — API key de HikerAPI
- `DATABASE_URL` — PostgreSQL (auto-provisioned)
- `ARQ_REDIS_URL` — Redis (auto-provisioned)
- `DEEPSEEK_API_KEY` — DeepSeek API key

---

## 10. Arquitectura de la UI — LENS Discovery

```
/lens/discovery
├── Conversational interface (chat-style)
├── Brief input (product, industry, audience)
├── Hashtag suggestions
├── Results display (cards con score)
└── Candidate export

/features/lens/
├── DiscoveryChat.tsx       — Chat principal
├── BriefForm.tsx           — Formulario de brief
├── CandidateCard.tsx       — Tarjeta de candidato
├── CandidateList.tsx      — Lista de resultados
└── useDiscovery.ts        — TanStack Query hooks
```

---

## 11. Issues Conocidos y Fixes Aplicados

### Bugs Arreglados (2026-08-13)

| Bug | Síntoma | Fix |
|-----|---------|-----|
| `get_user_about()` 422 | enrichment retornaba country vacío | `/gql/user/about?user_id` → `/v1/user/about?id` |
| `search_location()` fail | STEP 0 no encontraba perfiles | `/v1/location/search?query` → `/v1/fbsearch/places?query` |
| `location_medias_top/recent` fail | posts de location no cargaban | param `id` → `location_pk` |
| Costo excesivo | $50 en 2 días | `MAX_HANDLES_TO_ENRICH` 500→50, disables varios |

### Issues Abiertos

| Issue | Prioridad | Estado |
|-------|-----------|--------|
| Balance HikerAPI agotado | CRÍTICA | Necesita top-up |
| Hashtags B2B no retornan creators | ALTA | HashTags actualizados a creator-focused |
| Modo ultra-económico no persiste en deploy | MEDIA | Config hardcodeada en worker.py |

---

## 12. Próximos Pasos

### Inmediato (hoy)
- [ ] Fix `MAX_HANDLES_TO_ENRICH` → 50 en worker.py
- [ ] Disable `get_user_about` por default
- [ ] Disable STEP 0 location search
- [ ] Reducir hashtags y keywords
- [ ] Test con modo ultra-económico
- [ ] Top-up HikerAPI ($20-30 USD)

### Esta semana
- [ ] Validar pipeline completo con candidatos reales
- [ ] Documentar costos por run
- [ ] Presentar demo al CEO

### Largo plazo
- [ ] Re-habilitar Apify como fallback
- [ ] Implementar modo "dry run" (sin costo)
- [ ] Dashboard de costos por campaña

---

## 13. Contactos y Recursos

| Recurso | URL |
|---------|-----|
| API Docs | `https://lawebcore-production.up.railway.app/api/docs` |
| HikerAPI Dashboard | `https://hikerapi.com/billing` |
| Railway Dashboard | `https://railway.app/project/lawebcore` |
| Vercel Dashboard | `https://vercel.com/lawebcore` |

---

*Documento generado: 2026-08-13*
*Última actualización: Commit `98978b5` — fix: HikerAPI endpoints*
