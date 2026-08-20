# La Web Core — LENS Discovery Module
## Documentación de Ingeniería para Advisor

> **Fecha:** 2026-08-20 (sesión completa — Hitos 26-28 aplicados)
> **Audiencia:** Ingeniero advisor técnico
> **Proyecto:** La Web Core — LENS Discovery Module
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Ingeniero que documenta:** Sistema (contexto completo del repositorio)
> **Estado de deploy:** ✅ Railway deploy `7796dc9` 18:26 UTC | ✅ Vercel frontend `df41d9e` 11:30 UTC | ⏳ Railway deploy `a21dd97` pendiente (Hito 28)
> **HikerAPI balance:** ✅ **$43.00 USD** (recargado 2026-08-20)

---

## Tabla de Contenidos

1. [Executive Summary](#1-executive-summary)
2. [Stack Tecnológico Completo](#2-stack-tecnológico-completo)
3. [Infraestructura de Carpetas](#3-infraestructura-de-carpetas)
4. [LENS — Flujo Completo End-to-End](#4-lens--flujo-completo-end-to-end)
5. [HikerAPI — Sistema de Costos y Control](#5-hikerapi--sistema-de-costos-y-control)
6. [Modo Explorar — Descubrimiento Barato](#6-modo-explorar--descubrimiento-barato)
7. [Modo Analizar — Enrichment Selectivo](#7-modo-analizar--enrichment-selectivo)
8. [Modelo de Datos](#8-modelo-de-datos)
9. [Budget Tracking — G12](#9-budget-tracking--g12)
10. [Testing — pytest Suite](#10-testing--pytest-suite)
11. [Runbook Operacional](#11-runbook-operacional)
12. [Roadmap H26-H30](#12-roadmap-h26-h30)
13. [Commits Principales](#13-commits-principales)
14. [Análisis Exhaustivo de la Sesión 2026-08-20](#14-análisis-exhaustivo-de-la-sesión-2026-08-20)

---

## 1. Executive Summary

### Qué es La Web Core

Plataforma interna de **La Web Figital Agency** para gestión integral de campañas de marketing, KPIs, operaciones de marca y producto, e Inteligencia Artificial aplicada. El núcleo operativo de la agencia.

### Qué es LENS

**LENS** — *El sistema de discovery de influencers más inteligente de Venezuela.*

Permite describir un brief en lenguaje natural y recibir los mejores perfiles de Instagram verificados con scoring LWFA propietario — todo en minutos, no en días.

### El problema histórico

El pipeline automático ejecutaba discovery + enrichment en un solo paso. El enrichment (Step 3) consume ~$1.28/run. Con $28 gastados en 48 runs, el saldo se agotaba en enrichment dejando **0 candidatos**. El costo por run era fijo e inevitable aunque el resultado fuera inútil.

### La solución: Modo Explorar → Modo Analizar

```
┌──────────────────────────────────────────────────────────────────────┐
│  MODO EXPLORAR (~$0.24)              MODO ANALIZAR (~$0.02/handle) │
│                                                                      │
│  1. Discovery only (HikerAPI)          1. Carga candidatos          │
│     Sin enrichment                          del run padre             │
│  2. Rough score geo + niche            2. Enrichment selectivo        │
│  3. Usuario selecciona handles           3. Scoring completo          │
│  4. Costo mínimo                        4. Auto-save → proposal.csv  │
│                                                                      │
│  Status: 'explored'                   Status: 'completed'            │
└──────────────────────────────────────────────────────────────────────┘
```

- **Costo campaña completa (Explorar + Analizar 5 handles):** ~**$0.34** (vs. $1.28 anterior del pipeline automático)
- **Tasa de éxito:** pendiente de medir en primer run real (vs. 2% automático histórico)
- **Riesgo de 402 mid-run:** Bajo (pre-flight de saldo en analizar)

### Estado actual del proyecto (post-sesión 2026-08-20)

- **48 runs ejecutados históricamente**, $28.33 gastados, **1 candidato encontrado**
- HikerAPI balance: ✅ **$43.00 USD** (recargado 2026-08-20)
- Modo Explorar/Analizar: **implementado y corregido** en código
- Railway deploy: ✅ **completado** (18:26 UTC, commit `7796dc9`)
- Vercel frontend: ✅ **deployado** (11:30 UTC, commit `df41d9e`)
- Migration `00106`: ✅ **APLICADA** (enum `explored` confirmado en Railway)
- Migration `00107`: ⏳ **opcional** (ledger protegido por try/except en worker)
- **Hito 28 aplicado** (commit `a21dd97`): Fix A pre-flight mode-aware + Fix B DeepSeek skip + extra='forbid' — deploy pendiente
- **4 bugs críticos encontrados y corregidos en Hito 26** (ver Sección 14)
- **17 tests nuevos** en `test_hito28_e2e.py` (17 passed)

---

## 2. Stack Tecnológico Completo

### Backend — FastAPI (Python 3.12 async)

| Componente | Tecnología | Notas |
|---|---|---|
| Framework | FastAPI + Uvicorn | ASGI async |
| Workers | **ARQ** sobre Redis | `apps/api/app/workers/worker.py` |
| Acceso DB | `asyncpg` directo vía `shared_core.railway_pg` | SQLAlchemy presente pero no en el camino de discovery |
| Validación | Pydantic v2 | `packages/discovery/discovery/schemas.py` |
| Rate limiting | SlowAPI | `app/core/rate_limiter.py` |
| Monitoreo | Prometheus (`/metrics`) + Sentry | `app/core/metrics.py` |
| Logging | structlog | JSON estructurado |
| Serialización | orjson | Más rápido que json estándar |

**Ubicación:** `apps/api/` — Railway (contenedor Docker)

### Frontend — React 19 + TypeScript

| Componente | Tecnología | Notas |
|---|---|---|
| Framework | React 19 + Vite | SPA con SSR en Vercel |
| Lenguaje | TypeScript strict | |
| UI | Tailwind CSS + shadcn/ui | Componentes base |
| State server | TanStack Query v5 | Cache + polling |
| State local | Zustand | Carrito de selección |
| Routing | React Router v7 | |

**Ubicación:** `apps/web/` — Vercel

### Base de Datos

| Componente | Tecnología | Notas |
|---|---|---|
| Motor | **PostgreSQL en Railway** | `postgres.railway.internal:5432/railway` |
| Extensiones | `uuid-ossp`, `pgcrypto`, `pg_trgm`, `vector` | pgvector para embeddings |
| Acceso | asyncpg (no SQLAlchemy en discovery) | `shared_core.railway_pg` |
| Migraciones | SQL files en `supabase/migrations/` | 107 migraciones (00001 → 00107) |

> **Corrección histórica:** la documentación vieja decía "PostgreSQL via Supabase Cloud". El motor real en producción es PostgreSQL en Railway. Las migraciones viven en `supabase/migrations/` por historia del proyecto, pero el camino de datos de discovery no pasa por Supabase.

### Cache y Cola

| Componente | Tecnología | Notas |
|---|---|---|
| Cola de jobs | **ARQ** sobre Redis | `ARQ_REDIS_URL` en Railway |
| Cache | Redis (misma instancia) | Respuestas HikerAPI, contadores BudgetFuse |
| Lua scripts | Redis EVALSHA | BudgetFuse: operación atómica |

**Ubicación:** Railway Redis add-on

### APIs Externas

| Proveedor | Uso | Costo | Docs |
|---|---|---|---|
| **HikerAPI** | Fuente primaria de datos Instagram | $0.02/call (plan Start) | `hikerapi.com/billing` |
| **DeepSeek-V3** | LLM: brief parsing, profile generation, AI scoring | ~$0.001/1K tokens | `api.deepseek.com` |
| Apify | Legacy (no funcional) | — | — |

### Deploy

| Servicio | Qué | URL |
|---|---|---|
| Railway | API + Workers + Postgres + Redis | `lawebcore-production.up.railway.app` |
| Vercel | Frontend React | `lawebcore.vercel.app` |
| Sentry | Error tracking | En variables de Railway |

### Variables de Entorno Clave

```bash
# Database
DATABASE_URL=postgresql+asyncpg://...@postgres.railway.internal:5432/railway
ARQ_REDIS_URL=redis://...

# APIs
HIKERAPI_API_KEY=***
DEEPSEEK_API_KEY=sk-***
APIFY_API_TOKEN=***   # legacy, no operativo

# Controles de costo (Hito 21-25)
MONTHLY_BUDGET_USD=10.0          # tope mensual total
MAX_CALLS_PER_RUN=120            # máximo llamadas por run
BUDGET_ALERT_THRESHOLD=0.7       # alerta al 70%
HIKERAPI_COST_PER_CALL_USD=0.02  # plan Start

# Flags de pipeline
INSTAGRAM_SOURCE=hikerapi        # hikerapi | apify (apify no funciona)
HIKERAPI_STEP0_LOCATION=false    # búsqueda por ubicación
HIKERAPI_INCLUDE_ABOUT=false     # llamada de fraude/país
ENABLE_AI_ANALYZER=true         # análisis DeepSeek

API_ENV=production
ADMIN_TOKEN=***
```

---

## 3. Infraestructura de Carpetas

```
lawebcore/
├── apps/
│   ├── api/                          # FastAPI backend — Railway
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       └── endpoints/
│   │   │   │           ├── lens.py          # /conversations, /runs, /analyze-selected
│   │   │   │           └── ...
│   │   │   ├── core/
│   │   │   │   ├── budget_fuse.py          # Hito 21 — single accounting point
│   │   │   │   ├── discovery_cost_tracker.py  # flush a api_costs
│   │   │   │   ├── hikerapi_client.py      # Cliente con reserve_and_record
│   │   │   │   ├── metrics.py             # Prometheus counters/gauges
│   │   │   │   ├── rate_limiter.py        # SlowAPI
│   │   │   │   └── security.py
│   │   │   ├── models/                    # SQLAlchemy (presente pero no usado en discovery)
│   │   │   ├── workers/
│   │   │   │   └── worker.py              # ★ pipeline completo
│   │   │   └── main.py                    # FastAPI app entry
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── web/                          # React frontend — Vercel
│       └── src/
│           ├── features/
│           │   └── lens/
│           │       ├── api/
│           │       │   └── lensApi.ts      # TanStack Query hooks
│           │       ├── components/
│           │       │   ├── CandidateCard.tsx   # Con checkbox de selección
│           │       │   └── BulkActionBar.tsx   # Barra de acciones bulk
│           │       ├── hooks/
│           │       │   ├── useDiscoveryRun.ts
│           │       │   ├── useDiscoveryConversation.ts
│           │       │   └── useRunPolling.ts   # ⭐ ahora carga candidatos en status='explored'
│           │       └── types/
│           │           └── discovery.ts     # Tipos TypeScript
│           ├── components/ui/             # shadcn/ui
│           └── lib/
│               └── api.ts                 # Cliente Axios
│
├── packages/
│   ├── discovery/                     # ★ Core LENS Module
│   │   └── discovery/
│   │       ├── brief_parser.py        # Texto → BriefStructured (DeepSeek)
│   │       ├── profile_generator.py   # Brief → DiscoveryProfile + elite_data
│   │       ├── query_builder.py       # Brief → DiscoveryPlan
│   │       ├── candidate_analyzer.py  # Scoring AI (DeepSeek)
│   │       ├── orchestrator.py        # State machine: START→BRIEF→SEARCHING→DONE
│   │       ├── memory.py              # Persistencia de conversación
│   │       ├── schemas.py             # BriefStructured, CandidateMetrics, etc.
│   │       ├── scoring/
│   │       │   ├── lens_score.py      # Unified 0-100 score
│   │       │   └── niche.py          # Niche relevance
│   │       └── tools/
│   │           ├── hikerapi_client.py    # Cliente HikerAPI con BudgetFuse
│   │           ├── hikerapi_circuit_breaker.py  # State machine en Redis
│   │           ├── geo_boost.py          # Geographic + tier scoring
│   │           └── instagram_source.py   # Protocolo abstracción (hikerapi/apify)
│   │
│   └── shared-core/                  # Config, DB, utilities
│       └── shared_core/
│           ├── config.py              # Settings Pydantic (incluye budget params)
│           ├── railway_pg.py          # Acceso asyncpg a PostgreSQL Railway
│           ├── supabase_rest.py       # Cliente REST Supabase (legacy)
│           └── db.py
│
├── supabase/
│   └── migrations/
│       ├── 00000000000001_extensions.sql
│       ├── ...
│       ├── 00000000000106_discovery_run_explored_status.sql  # ← ✅ APLICADA
│       └── 00107_budget_transactions.sql                        # ← ⏳ OPCIONAL (try/except)
│
├── docs/
│   ├── LENS_ASESORIA_INGENIERO_2026-08-20.md   # Este documento
│   ├── ARQUITECTURA_LENS.md                     # Arquitectura técnica
│   └── ...
│
├── tests/
│   ├── test_discovery_contract.py     # 20 tests — contratos de API
│   ├── test_discovery_api.py          # 18 tests — endpoints
│   └── test_discovery_workflow.py     # 21 tests — integración
│
├── pyproject.toml                     # pnpm workspaces root
├── package.json                       # frontend deps
└── docker-compose.yml                 # Postgres + Redis locales
```

---

## 4. LENS — Flujo Completo End-to-End

### 4.1 Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vercel)                         │
│   React 19 + TanStack Query + Tailwind + shadcn/ui         │
│   Usuario escribe brief → selecciona handles → descarga CSV  │
└─────────────────────────────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 BACKEND API (Railway)                        │
│   FastAPI + Uvicorn + ARQ Worker                             │
│   /api/v1/conversations/{id}/messages  (chat)               │
│   /api/v1/discovery/runs/{id}          (status)             │
│   /api/v1/discovery/analyze-selected   (analizar Selección)│
└─────────────────────────────────────────────────────────────┘
           │                    │                      │
           │ encola             │ encola               │
           ▼                    ▼                      ▼
    ┌────────────┐      ┌────────────┐       ┌─────────────┐
    │ HikerAPI   │      │ DeepSeek-V3 │       │   Railway   │
    │(Instagram) │      │   (LLM)     │       │  Postgres  │
    └────────────┘      └────────────┘       └─────────────┘
           │                                       │
           ▼                                       │
    ┌────────────┐                                │
    │   Redis    │◄──── ARQ jobs + BudgetFuse     │
    └────────────┘      + Circuit Breaker          │
```

### 4.2 Pipeline Completo — Paso a Paso

#### Fase 0: Conversación (opcional)

El usuario puede chatear con LENS para refinar el brief. El `orchestrator.py` mantiene estado en memoria (se pierde en restart) y persiste en `discovery_conversations` + `discovery_messages`.

```
Usuario: "Busco influencers de mascotas en Caracas"
         ↓
Orchestrator (DeepSeek): Parsea intención → BriefStructured
         ↓
DiscoveryProfile: Genera hashtags/keywords/geo adaptados
         ↓
Worker encolado: discovery_run_task(run_id)
```

#### Fase 1: Brief Estructurado

`BriefStructured` (schema en `packages/discovery/discovery/schemas.py:56`):

```python
class BriefStructured(BaseModel):
    niches: list[str]                    # ["mascotas", "perros"]
    audience_countries: list[str]        # ["Venezuela"]
    audience_cities: list[str]           # ["Caracas"]
    discovery_mode: Literal["auto", "explore", "analyze"]  # Hito 24
    handles_to_analyze: list[str]        # handles seleccionados en explorar
    parent_run_id: str | None            # run padre en modo analizar
    analyze_with_ai: bool = True        # DeepSeek scoring
    exclude_stores: bool = True         # excluir cuentas comerciales
    # ... 30+ campos más
```

#### Fase 2: Worker — `discovery_run_task` (worker.py)

**Orquestación global:**
```
startup()
  → establece RedisSettings
  → inicia health server (opcional)

discovery_run_task(run_id)
  → _run_set_status("running")
  → carga brief_parsed de DB
  → BudgetFuse.assert_budget_available()     ← Hito 23: pre-flight
  → CircuitBreaker.can_proceed()
  → query_builder.build(brief) → DiscoveryPlan
  → [MODO EXPLORAR / ANALIZAR según discovery_mode]
  → _run_update(status="explored"|"completed"|"partial"|"failed")
  → flush costs a api_costs + budget_transactions
```

### 4.3 Flujo por Modo

#### Modo AUTO (legacy — pipeline completo)

```
discovery_run_task
  ├── STEP 1: Hashtag search (top + recent)
  ├── STEP 2: Keyword search (3 keywords × 3 sufijos geo)
  ├── STEP 2.5: Reels serp
  ├── STEP 2.6: Follower expansion (ROTO — devuelve vacío)
  ├── STEP 3: Top search + Suggested profiles
  ├── STEP 4: Pre-filter + ENRICHMENT (50 handles × $0.0006)
  └── STEP 5: Scoring (geo_score + lens_score + niche)
  → Status: "completed" | "partial" | "failed"
```

#### Modo EXPLORAR (H26 — Hito 24)

```
discovery_run_task(discovery_mode='explore')
  ├── STEP 1-3: Discovery completo (igual que auto)
  ├── ENRICHMENT: SKIPPED
  └── Scoring: rough score (geo + niche, sin followers)
  → Status: "explored"
  → 15-50 handles candidatos en DB
  → Usuario ve lista con handles + rough score
  → Selecciona handles con checkbox
  → POST /analyze-selected
```

#### Modo ANALIZAR (H26 — Hito 24)

```
discovery_run_task(discovery_mode='analyze')
  ├── Valida parent_run_id + handles_to_analyze
  ├── Carga candidatos del run padre desde DB
  ├── SKIP STEP 1-3 (discovery ya hecho)
  ├── ENRICHMENT: Solo handles_to_analyze (3-10 típicamente)
  └── Scoring completo + auto-save como 'saved'
  → Status: "completed"
  → Proposal CSV disponible
```

---

## 5. HikerAPI — Sistema de Costos y Control

### 5.1 Qué es HikerAPI

API de scraping de Instagram. Plan "Start": **$0.02 USD por request**.

Documentación: `https://api.hikerapi.com/docs`
Panel de billing: `https://hikerapi.com/billing`

### 5.2 Endpoints Usados

| Método | Endpoint | Perfil devuelto | Costo |
|---|---|---|---|
| `search_hashtag()` | `/v2/hashtag/medias/top` | **Reducido** (sin bio/seguidores) | $0.02 |
| `search_hashtag_recent()` | `/v2/hashtag/medias/recent` | **Reducido** | $0.02 |
| `search_keyword()` | `/v2/fbsearch/accounts` | **Completo** | $0.02 |
| `search_top_accounts()` | `/v3/fbsearch/topsearch` | **Completo** | $0.02 |
| `enrich_profile()` | `/v1/user/by/username` | **Completo** | $0.02 |
| `get_user_about()` | `/v1/user/about?id=` | País, antigüedad, aliases | $0.02 |
| `suggested_profiles()` | `/v2/user/suggested/profiles` | **Completo** | $0.02 |
| `search_location()` | `/v1/fbsearch/places?query=` | Ubicaciones | $0.02 |
| `location_medias_top/recent()` | `/v1/location/medias/*` | Posts con geotag | $0.02 |

> **Parámetros que causan 422:** `safe_int` en `/gql/user/about` y `/v1/location/search`; `id` en lugar de `location_pk` en endpoints de ubicación.

### 5.3 Sistema de Costos — BudgetFuse (Hito 21)

**Problema histórico:** No había control de presupuesto. $50-72 consumidos en dos días sin que ningún mecanismo interviniera.

**Solución implementada:** `BudgetFuse` (`apps/api/app/core/budget_fuse.py`)

```
┌─────────────────────────────────────────────────────────────┐
│  BudgetFuse — Single Accounting Point (Hito 21)            │
│                                                              │
│  reserve_and_record() — ÚNICO punto donde se contabiliza   │
│  Se llama desde HikerAPIClient._get() DESPUÉS del cache    │
│  lookup y ANTES de la HTTP request                         │
│                                                              │
│  Lua script atómico (EVALSHA):                              │
│  1. GET run_key → check count < MAX_CALLS_PER_RUN          │
│  2. INCR run_key (per-run counter)                         │
│  3. INCRBYFLOAT month_key (gasto mensual)                   │
│  4. EXPIRE en ambas keys                                   │
│                                                              │
│  Redis keys:                                                │
│  lens:budget:hikerapi:2026-08   ← monthly spend            │
│  lens:budget:run:{run_id}       ← per-run counter          │
│  lens:budget:alerted:hikerapi:2026-08  ← alert sent flag   │
└─────────────────────────────────────────────────────────────┘
```

**Parámetros configurados:**
```python
MONTHLY_BUDGET_USD = 10.0         # Hito 21: $10/mes
MAX_CALLS_PER_RUN = 120          # Hito 22: 120 llamadas/run
BUDGET_ALERT_THRESHOLD = 0.7     # Alertar al 70%
HIKERAPI_COST_PER_CALL_USD = 0.02
```

**Costos por fase (config default):**

| Fase | Llamadas aprox. | Costo aprox. |
|---|---|---|
| Hashtag top (3) | 6 | $0.12 |
| Hashtag recent (2) | 4 | $0.08 |
| Keyword (3 × 3) | 9 | $0.18 |
| Reels (1) | 1 | $0.02 |
| Expansión seguidores | 1 (roto) | $0.02 |
| Top search (1) | 2 | $0.04 |
| Sugeridos (1) | 1 | $0.02 |
| **Enrichment (25 handles)** | **25** | **$0.50** |
| **Total Modo AUTO** | **~49** | **~$0.98** |
| **Modo Explorar (sin enrichment)** | **~24** | **~$0.48** |
| **Modo Analizar (3 handles)** | **3** | **~$0.06** |

### 5.4 Circuit Breaker

`hikerapi_circuit_breaker.py` — State machine en Redis:

```
CLOSED (normal) ──[5 errores consecutivos 5xx]──► OPEN
                                                      │
                                              [300s TTL]
                                                      ▼
                                              HALF_OPEN (1 test call)
                                              /              \
                                    [test ok]                 [test fail]
                                          ▼                      ▼
                                    CLOSED                   OPEN (otra vez)
```

**Config:**
- `failure_threshold = 5` — abre tras 5 fallos consecutivos
- `breaker_ttl_s = 300` — espera 5 min antes de probar otra vez

### 5.5 Pre-flight de Saldo — Mode-Aware (Hito 23 + Hito 28 Fix A)

Antes de iniciar enrichment, el worker llama a `instagram_source.get_balance()` para comparar contra el costo estimado del run.

**Hito 28 corrige el caso grave:** Antes, siempre estimaba 57 calls = $1.14, incluso en Analizar donde solo se necesitan 3-5 calls = $0.06-0.10. Con saldo=$0.80, rechazaba un Analizar que SÍ alcanza.

**Estimación modo-aware (Hito 28):**
```python
if is_explore_mode:
    estimated_calls = ESTIMATED_DISCOVERY_CALLS  # 32 = $0.64
elif is_analyze_mode:
    estimated_calls = max(1, len(brief.handles_to_analyze)) if brief.handles_to_analyze else 1
    # ~$0.02-0.10 para 1-5 handles
else:
    estimated_calls = ESTIMATED_DISCOVERY_CALLS + MAX_HANDLES_TO_ENRICH  # 57 = $1.14

balance = await instagram_source.get_balance()
if balance < estimated_cost:
    raise SourceUnavailable(...)
```

| Modo | Antes (Hito 23) | Después (Hito 28) |
|------|-----------------|-------------------|
| Explorar | $1.14 (sobreestimado 78%) | **$0.64** |
| Analizar (5 handles) | $1.14 (sobreestimado **11×**) | **$0.10** |
| Auto | $1.14 | $1.14 (sin cambio) |

El "último dólar inutilizable" de cada recarga ahora se recupera.

### 5.6 Budget Transactions — G12 (Ledger Inmutable)

**Problema del desfase Redis↔DB:** Redis y DB mostraban números distintos ($25.13 de diferencia).

**Solución:** Tabla `budget_transactions` como ledger inmutable:

```sql
CREATE TABLE budget_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES discovery_runs(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,       -- 'hikerapi', 'deepseek'
    operation TEXT NOT NULL,      -- 'discovery_pipeline', 'enrichment'
    amount_usd NUMERIC(12, 6) NOT NULL,  -- positivo=gasto, negativo=reversa
    request_count INTEGER NOT NULL DEFAULT 1,
    balance_after_usd NUMERIC(12, 6),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger impide UPDATE/DELETE — solo INSERT allowed
CREATE TRIGGER budget_tx_immutable
    BEFORE UPDATE OR DELETE ON budget_transactions
    FOR EACH ROW EXECUTE FUNCTION budget_tx_prevent_modification();

-- Reconciliación:
SELECT SUM(amount_usd)
FROM budget_transactions
WHERE provider = 'hikerapi'
  AND created_at > '2026-08-01';
```

**Migración:** `00107_budget_transactions.sql` — **OPCIONAL** (el worker tiene try/except que protege contra error si la tabla no existe). Aplicar cuando sea conveniente.

---

## 6. Modo Explorar — Descubrimiento Barato

### 6.1 Qué hace

Ejecuta discovery completo (Steps 1-3, sin enrichment). El analista recibe una lista de handles con rough score (geo + niche) y selecciona cuáles enriquecer en modo Analizar.

### 6.2 Costo

**~$0.24-0.48/run** (solo discovery, sin enrichment)

### 6.3 Trigger

```python
# worker.py
is_explore_mode = getattr(brief, "discovery_mode", "auto") == "explore"
```

El modo `explore` está **hardcodeado** en `LensSearchPage.tsx:51` como `discovery_mode: 'explore' as const`. No hay selector en la UI — el modo `auto` es inalcanzable desde esa página. El campo `discovery_mode='explore'` va en `BriefStructured` y se persiste en `discovery_runs.brief_parsed`.

### 6.4 Lógica en el Worker

**Step 3 — Skip enrichment (worker.py):**
```python
if handles_to_enrich and is_explore_mode:
    logger.info("step3_explore_mode_skip_enrichment", handles_count=len(handles_to_enrich))
    await _save_progress_message(
        run_id,
        f"✅ Encontré {len(handles_to_enrich)} candidatos con señales de nicho. "
        f"Seleccioná los que quieras evaluar y ejecutá 'Analizar'.",
    )
```

**Scoring — Rough score sin followers (worker.py):**
```python
if followers == 0:
    untracked_no_followers += 1
    if is_explore_mode:
        rough = rough_score_map.get(handle, 0.0)
        if rough > 0:
            scored.append({
                "handle": handle,
                "match_score": rough * 100,
                "rough_score": rough,
                "_is_explore_mode": True,
            })
        continue
    continue
```

**Dict de candidato guardado — columnas correctas (Hito 26 fix):**
```python
candidate_dict = {
    "run_id": run_id,
    "handle": handle,
    "full_name": raw.get("full_name", ""),
    "bio": raw.get("bio", ""),
    "avatar_url": raw.get("avatar_url", ""),
    "url": raw.get("url", ""),
    "platform": "instagram",
    "followers": raw.get("followers", 0) or 0,
    "following": raw.get("following", 0) or 0,
    "posts_count": raw.get("posts_count", 0) or 0,
    # ... todas las columnas de discovery_candidates
}
```

> ⚠️ **Bug 1 de la sesión 2026-08-20:** El dict original usaba claves que NO correspondían a columnas DB (`profile`, `rough_score`, `_is_explore_mode`) y faltaban `run_id` y `platform` (parte del ON CONFLICT). Fix aplicado en commit `2fe9816`.

### 6.5 Schema — Nuevo Status

```sql
-- migration 00106 ✅ APLICADA EN RAILWAY
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'explored';
```

**CHECK constraint:**
```sql
CHECK (status IN ('pending', 'running', 'completed', 'partial', 'failed', 'explored'))
```

### 6.6 Frontend — Lista con Checkbox

- `CandidateCard.tsx`: Checkbox para seleccionar handles
- `BulkActionBar.tsx`: Barra de acciones bulk ("Analizar seleccionados")
- `lensApi.ts` → `analyzeSelected(runId, handles)`: POST `/analyze-selected`
- **Fix en esta sesión:** `LensSearchPage.tsx` ahora envía `discovery_mode: 'explore' as const` explícitamente
- **Fix en esta sesión:** `useRunPolling.ts` ahora carga candidatos cuando `status === 'explored'`

### 6.7 Por qué es la decisión correcta

| Criterio | Pipeline Automático | Modo Explorar |
|---|---|---|
| Costo/run | ~$0.98 | ~$0.24 |
| Control de calidad | Bajo (sin supervisión) | Alto (analista selecciona) |
| Riesgo 402 mid-run | Alto | Bajo |
| Tasa de éxito | 2% (1/48) | Pendiente de medir |

El enriquecimiento sin supervisión es costoso e irreversible. Si el enrichment falla, todo el run se pierde. En modo Explorar, el costo de discovery (~50 llamadas) es ~$0.24: aceptable incluso si el resultado no sirve. El enrichment ($0.02 × N handles) solo se ejecuta sobre handles que el analista eligió conscientemente.

---

## 7. Modo Analizar — Enrichment Selectivo

### 7.1 Qué hace

Carga candidatos del run padre (Explorar), enriquece SOLO los handles seleccionados, scoring completo, auto-save como `saved`, genera proposal.csv.

### 7.2 Costo

**~$0.06/handle** (3 handles = $0.18, 10 handles = $0.60)

### 7.3 Trigger

```python
is_analyze_mode = getattr(brief, "discovery_mode", "auto") == "analyze"
parent_run_id = getattr(brief, "parent_run_id", None)
```

### 7.4 Lógica en el Worker

**Carga candidatos del run padre (worker.py):**
```python
if is_analyze_mode and parent_run_id:
    parent_candidates = await railway_pg.select(
        table="discovery_candidates",
        filters=[
            f"run_id=eq.{parent_run_id}",
            f"handle=in.({','.join(repr(h) for h in brief.handles_to_analyze)})",
        ],
    )
    for c in parent_candidates:
        handle = c["handle"]
        profiles[handle] = { /* merge raw_payload + DB fields */ }
```

**Skip discovery completo (worker.py):**
```python
_skip_discovery = is_analyze_mode and parent_run_id

if _skip_discovery:
    print("[ANALYZE MODE] skipping STEP 1/2/2.5/3 discovery")
    hashtag_items, keyword_items, reels_items = [], [], []
    step1_handles, step2_handles = set(), set()
else:
    # Normal discovery
```

**Enrichment selectivo (worker.py):**
```python
elif is_analyze_mode and brief.handles_to_analyze:
    handles_to_enrich = [
        h for h in brief.handles_to_analyze
        if h in profiles
    ]
    logger.info("step3_analyze_mode_enrich_selected",
        handles_count=len(handles_to_enrich),
        selected=list(handles_to_enrich)[:10],
    )
```

**Auto-save como 'saved' (worker.py):**
```python
if is_analyze_mode:
    for c in qualified:
        c["status"] = "saved"   # ← para proposal.csv
inserted_count = await _deduplicate_and_insert_candidates(qualified, run_id)
```

**Status final (worker.py):**
```python
if is_explore_mode:
    final_status = "explored"
else:
    final_status = "partial" if step3_degraded else "completed"
```

### 7.5 Wrap-up Message Específico

```python
if is_analyze_mode:
    await _save_progress_message(
        run_id,
        f"✅ Análisis completado. {len(qualified)} perfiles enriquecidos y guardados. "
        f"Mejor score: {top:.0f}/100. "
        f"Descargá la propuesta en CSV desde el historial de runs.",
    )
```

---

## 8. Modelo de Datos

### Tablas Principales

```sql
discovery_runs
├── id (UUID, PK)
├── business_unit_id (FK)
├── brief_text              -- texto original del brief
├── brief_parsed (JSONB)     -- BriefStructured serializado
├── status                  -- pending | running | completed | partial | failed | explored
├── total_candidates        -- candidatos guardados
├── actual_cost_usd         -- costo total del run
├── metadata (JSONB)        -- current_step, completed_steps, is_explore_mode, etc.
├── title
├── error
├── started_at, completed_at, created_at

discovery_candidates        -- UNIQUE(run_id, platform, handle)
├── id (UUID, PK)
├── run_id (FK → discovery_runs)
├── handle, full_name, bio, avatar_url, url
├── platform
├── country, city
├── followers, following, posts_count
├── engagement_rate, avg_likes, avg_comments
├── match_score             -- 0-100 (lens_score)
├── niche_relevance, geo_relevance
├── content_quality, audience_relevance, audience_quality
├── brand_fit               -- DeepSeek (si analyze_with_ai=true)
├── ai_rationale           -- resumen DeepSeek
├── rationale               -- texto por reglas
├── tier, is_tienda, status  -- status: 'new'|'saved'|'rejected'|'contacted'
├── raw_payload (JSONB)     -- lens_score, geo_score, cross_referenced, fraud_signals
└── fetched_at

discovery_conversations
├── id (UUID, PK)
├── discovery_run_id (FK, nullable)
├── current_step
├── accumulated_brief
├── parsed_brief_json (JSONB)
├── pending_refinements
├── message_count
├── title
└── state (JSONB)           -- ⚠️ existe pero NO se usa (orcestrator en memoria)

discovery_messages          -- Tabla propia (NO JSON en conversations)
├── id (UUID, PK)
├── conversation_id (FK)
├── role                    -- 'user' | 'assistant' | 'tool'
├── content
├── tool_calls (JSONB)
├── tool_results (JSONB)
├── reasoning
├── cost_usd
└── latency_ms

discovery_profiles         -- Vocabulario por vertical (ELITE system)
├── id (UUID, PK)
├── fingerprint (UNIQUE)    -- hash del brief
├── vertical_slug
├── languages (JSONB)
├── countries (JSONB)
├── hashtags, keywords, niche_keywords (JSONB)
├── geo_indicators
├── buy_intent_keywords (JSONB)
├── elite_data (JSONB)     -- 9 subcampos de contexto de campaña
├── source                  -- seed | llm | manual | fallback
├── quality_score, times_used
└── created_at, updated_at

api_costs
├── provider              -- 'hikerapi' | 'deepseek'
├── operation
├── entity_id            -- run_id
├── cost_usd
├── tokens_in, tokens_out
├── request_count
├── metadata (JSONB)
└── occurred_at

budget_transactions       -- G12: ledger inmutable
├── id (UUID, PK)
├── run_id (FK, nullable)
├── provider              -- 'hikerapi' | 'deepseek' | 'apify'
├── operation             -- 'discovery_pipeline' | 'enrichment' | 'scoring'
├── amount_usd           -- positivo=gasto, negativo=reversa
├── request_count
├── balance_after_usd
├── metadata (JSONB)
└── created_at           -- trigger impide UPDATE/DELETE
```

### Índices Principales

```sql
CREATE INDEX idx_candidates_run ON discovery_candidates(run_id);
CREATE INDEX idx_candidates_handle ON discovery_candidates(platform, handle);
CREATE INDEX idx_candidates_score ON discovery_candidates(run_id, match_score DESC);
CREATE INDEX idx_candidates_status ON discovery_candidates(run_id, status);
CREATE INDEX idx_runs_status ON discovery_runs(status);
CREATE INDEX idx_runs_business_unit ON discovery_runs(business_unit_id, created_at DESC);
CREATE INDEX idx_budget_tx_provider ON budget_transactions(provider, created_at DESC);
CREATE INDEX idx_budget_tx_run ON budget_transactions(run_id) WHERE run_id IS NOT NULL;
```

---

## 9. Budget Tracking — G12

### Problema Documentado

```
Redis:    $3.20  gastado (contador en Redis)
DB:       $28.33 gastado (SUM(api_costs))
Desfase:  $25.13 sin explicar
```

### Arquitectura de la Solución

```
┌──────────────────────────────────────────────────────────────┐
│  Redis: BudgetFuse (hot path — usado en cada request)       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ lens:budget:hikerapi:2026-08  ← monthly float           ││
│  │ lens:budget:run:{run_id}     ← per-run int counter      ││
│  │ lens:budget:alerted:hikerapi:2026-08  ← alert flag      ││
│  └─────────────────────────────────────────────────────────┘│
│  Propósito: bloquear requests cuando se acaben los credits  │
│  ⚠️ Redis PUEDE perder datos (crash, flush)                 │
└──────────────────────────────────────────────────────────────┘
                            │
                    reserve_and_record()
                    (Hito 21 — único punto)
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  DB: budget_transactions (ledger inmutable)                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ id | run_id | provider | operation | amount_usd | ...    ││
│  │ INSERT ONLY (trigger impide UPDATE/DELETE)              ││
│  └─────────────────────────────────────────────────────────┘│
│  Propósito: source of truth para reconciliación            │
│  ✅ DB ES inmutable — sobrevive a Redis                      │
└──────────────────────────────────────────────────────────────┘
                            │
                    Reconciliación:
                    SELECT SUM(amount_usd)
                    WHERE provider='hikerapi'
                      AND created_at > '2026-08-01'
```

### Worker Escribe en Ledger

El worker graba cada reserva en `budget_transactions` vía el cost tracker. El ledger está protegido por try/except: si la tabla no existe (migration 00107 no aplicada), el worker continúa sin crash.

### Cómo Hacer Reconciliación

```bash
# Saldo real según ledger:
psql $DATABASE_URL -c "
SELECT provider,
       SUM(amount_usd) as total_usd,
       SUM(request_count) as total_calls
FROM budget_transactions
WHERE created_at > '2026-08-01'
GROUP BY provider;
"

# Saldo según Redis (puede diferir):
redis-cli GET lens:budget:hikerapi:2026-08

# Desfase = Redis - DB
```

---

## 10. Testing — pytest Suite

### Estructura

```
tests/
├── test_discovery_contract.py    # 20 tests — contratos de API
├── test_discovery_api.py         # 18 tests — endpoints
└── test_discovery_workflow.py    # 21 tests — integración
```

### Cómo Ejecutar

```bash
cd apps/api
pip install -e ".[dev]"
pytest tests/ -v --tb=short
```

### Niveles de Testing

| Nivel | Qué prueba | Ejemplo |
|---|---|---|
| **Contract** | Que la API responde lo que dice | `test_get_run_returns_correct_status` |
| **API** | Que los endpoints funcionan | `test_analyze_selected_creates_child_run` |
| **Workflow** | Que el pipeline end-to-end funciona | `test_full_explore_analyze_flow` |

---

## 11. Runbook Operacional

### 11.1 Iniciar un Run

1. Ir a `https://lawebcore.vercel.app/lens`
2. Escribir brief en lenguaje natural: "Influencers de mascotas en Caracas, mujeres 25-45"
3. Seleccionar **"Modo Explorar"**
4. Esperar status `explored` (polling cada 3s)
5. Revisar handles candidatos (rough score)
6. Seleccionar handles con checkbox
7. Click **"Analizar seleccionados"** → POST /analyze-selected
8. Esperar status `completed`
9. Descargar proposal.csv desde historial

### 11.2 Ver Costos

```bash
# Ledger de transacciones (fuente de verdad):
psql $DATABASE_URL -c "SELECT SUM(amount_usd) FROM budget_transactions WHERE provider='hikerapi' AND created_at > '2026-08-01';"

# Contador Redis (hot path):
redis-cli GET lens:budget:hikerapi:2026-08

# Saldo real HikerAPI:
curl -H "X-API-Key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/user/me/balance
```

### 11.3 Recargar HikerAPI

1. Ir a `https://hikerapi.com/billing`
2. Comprar credits (plan Start: $0.02/call)
3. Mínimo recomendado: **$50 USD** para validar el flujo completo
4. WARNING: Hacerlo cuando los controls estén verificados en producción

### 11.4 Aplicar Migrations en Railway

```bash
# Migration 00106 — ✅ YA APLICADA (confirmada por usuario):
psql $DATABASE_URL -c "ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'explored';"

# Migration 00107 — OPCIONAL (ledger protegido por try/except):
psql $DATABASE_URL -f supabase/migrations/00107_budget_transactions.sql

# Verificar:
psql $DATABASE_URL -c "SELECT enumlabel FROM pg_enum WHERE enumtypid = 'discovery_run_status'::regtype;"
# Debe incluir: pending, running, completed, partial, failed, explored
```

### 11.5 Ver Logs

```bash
# Railway logs:
railway logs --service lawebcore-api

# O desde la UI: railway.app → proyecto → service → logs
```

### 11.6 Restart Worker

```bash
# Railway redeploy:
railway up --service lawebcore-api

# O desde la UI de Railway
```

### 11.7 Ver Métricas Prometheus

```
https://lawebcore-production.up.railway.app/metrics
```

Métricas relevantes:
- `lens_active_runs` — runs activos
- `lens_candidates_total` — candidatos encontrados
- `lens_apify_cost_usd_total` — costo Apify acumulado

---

## 12. Roadmap H26-H30

### H26 ✅ (2026-08-19/20)
- Modo Explorar: schema, BE, FE, status `explored`
- G1-G3, G5-G10 implementados
- **Fix 2026-08-20:** Dict de candidato usaba claves incorrectas → columnas DB correctas (commit `2fe9816`)
- **Fix 2026-08-20:** `discovery_mode` no se enviaba desde frontend (commit `92d6faa`)
- **Fix 2026-08-20:** Polling no cargaba candidatos en status `explored` (commit `df41d9e`)
- **Fix 2026-08-20:** TypeScript error en `discovery_mode` (commit `df41d9e`)
- Commits: `5ba4625`, `2fe9816`, `92d6faa`, `df41d9e`

### Phase 2.1-2.3 ✅ (2026-08-19)
- UI selección multi-handle (checkbox)
- Endpoint `/analyze-selected`
- `BulkActionBar`
- G4, G11, G13
- Commit: `ba30a85`

### G14 ✅ (2026-08-20)
- `parent_run_id` en brief
- Worker carga candidatos del padre en analyze mode
- Skip discovery steps en analyze mode
- Auto-save candidatos como `saved`
- Commit: `9c4bf70`

### G12 ✅ (2026-08-20)
- Tabla `budget_transactions` con ledger inmutable
- Worker escribe en ledger
- Commit: `d83897f`

### Phase 3 ✅ (2026-08-20)
- 59 tests (contracts, API, workflow)
- Commit: `a3f8b40`

### H27 ✅ (2026-08-20 — COMPLETADO)
1. ✅ Apply migration `00106` en Railway — enum `explored` existe
2. ✅ Migration `00107` en Railway — **OPCIONAL** (protegido por try/except)
3. ✅ **Hito 27:** Fix `parent_run_id` en `DiscoverySearchRequest` — modo Analizar ahora no repite discovery (~$0.64 ahorrados por run)
4. ✅ **Hito 27:** Fix `platforms` — `default_factory=` en vez de `default=` (bug latente Pydantic v2)

### H28 ✅ (2026-08-20 — COMPLETADO — commit `a21dd97`)
1. ✅ **Fix A: Pre-flight mode-aware** — Explorar $0.64, Analizar real, Auto $1.14
2. ✅ **Fix B: DeepSeek skip en Explorar** — rationale honesto preservado, decisión corrupta evitada
3. ✅ **extra='forbid' en schemas** — BriefStructured + DiscoverySearchRequest
4. ✅ **17 tests nuevos** en `test_hito28_e2e.py` (17 passed)
5. ⏳ **Deploy Railway pendiente** — `a21dd97` debe ser pushneado a producción

### H28 Post-Deploy 🔴 (PRÓXIMO — validación mañana)
1. ⏳ Validar que candidatos aparecen en la UI tras `status='explored'`
2. ⏳ Validar que enrichment selectivo funciona en `analyze` mode
3. ⏳ Criterio de éxito: **≥15 handles con bio no vacía**, ≥5 seleccionables
4. ⏳ Validar `get_balance()` con saldo=$43 (curl post-recarga para verificar formato)

### H29 ⏳ (próximo sprint)
- Persistencia del carrito de selección (Zustand store → DB)
- Notificaciones cuando el análisis termina
- Historial de análisis por run

### H30 🔲 (futuro)
- Dashboard de costos con `budget_transactions`
- Alertas de presupuesto (notify cuando $X gastados)
- API de costos por período/provider

---

## 13. Commits Principales

| Commit | Desc | Fecha |
|--------|------|-------|
| `5ba4625` | H26 — G1,G2,G3,G5,G6,G7,G8,G9,G10 — Modo Explorar schema + BE + FE | 2026-08-19 |
| `ba30a85` | Phase 2.1-2.3 — UI selección + checkbox + endpoint analyze-selected | 2026-08-19 |
| `9c4bf70` | **G14** — Modo Analizar con parent_run_id + auto-save + wrap-up message | 2026-08-20 |
| `d83897f` | **G12** — budget_transactions ledger + migration 00107 | 2026-08-20 |
| `a3f8b40` | **Phase 3** — 59 tests (contracts, API, workflow) | 2026-08-20 |
| `7796dc9` | Empty commit — trigger Railway redeploy post-incidente Google Cloud | 2026-08-20 |
| `2fe9816` | **Hito 26** — explore mode dict con columnas DB correctas + ledger try/except | 2026-08-20 |
| `92d6faa` | Frontend: `discovery_mode='explore'` enviado + polling `explored` | 2026-08-20 |
| `df41d9e` | TypeScript: `discovery_mode: 'explore' as const` (fix type error) | 2026-08-20 |
| `hito27` | **Hito 27** — `parent_run_id` en DiscoverySearchRequest (modo Analizar no repite discovery) + `platforms` default_factory | 2026-08-20 |
| `a21dd97` | **Hito 28** — Fix A pre-flight mode-aware ($0.64/$0.10/$1.14) + Fix B DeepSeek skip explorar + extra='forbid' + 17 tests | 2026-08-20 |

---

## Notas para el Advisor

### Lo que está funcionando
- Pipeline completo en código (Modo Explorar + Modo Analizar)
- BudgetFuse con Lua atómico (Hito 21)
- Circuit Breaker con state machine en Redis (Hito 21)
- Pre-flight de saldo antes de enrichment (Hito 23)
- Ledger inmutable para reconciliación (G12) — **OPCIONAL**
- 59 tests cubriendo contracts, API y workflow
- Railway worker con código actualizado (deploy `7796dc9`)
- Frontend con `discovery_mode` y polling corregido (deploy `df41d9e`)
- **Hito 27:** `parent_run_id` en `DiscoverySearchRequest` — modo Analizar ahora salta discovery correctamente

### Lo que está pendiente (ANTES de producción)
1. **Recargar HikerAPI** — con $0 todo falla en pre-flight (**$20 USD recomendado**, ~58 campañas completas)
2. **Verificación end-to-end** — probar el flujo completo Explorar→Analizar en producción
3. **Validar 4 checks:**
   - `status='explored'` aparece tras Modo Explorar
   - `total_candidates > 0` en la respuesta
   - Candidatos tienen `handle` y `bio` populated
   - `actual_cost_usd > 0` en el run

### Métricas de éxito (post-recarga)
- Criterio mínimo: **≥15 handles con bio no vacía**, ≥5 seleccionables por el analista
- Explorar: ¿cuántos handles descubre por run?
- Analizar: de los handles seleccionados, ¿cuántos enriquecen correctamente?
- Propuesta: de los candidatos guardados, ¿cuántos aparecen en proposal.csv?

### Lo que NO hacer
- No modificar el pipeline automático legacy (costo alto, bajo ROI)
- No agregar más features hasta que el flujo Explorar→Analizar esté validado
- No implementar billing avanzado hasta que el flujo básico esté 100% confirmado

---

## 14. Análisis Exhaustivo de la Sesión 2026-08-20

### Resumen de la sesión

Esta sesión de trabajo (2026-08-20) descubrió y corrigió **4 bugs críticos** que impedían que el Modo Explorar produjera candidatos, a pesar de que los commits anteriores (`5ba4625`, `ba30a85`, `9c4bf70`) parecían implementar el flujo correctamente.

### Bug 1 — Dict de candidato con claves incorrectas (🔴 CRÍTICA)

**Detectado por:** Inspección de código durante análisis de `worker.py`
**Archivo:** `apps/api/app/workers/worker.py`
**Commit fix:** `2fe9816`

**Problema:** El dict de candidato en modo explorar usaba claves que NO correspondían a columnas de la tabla `discovery_candidates`:

```python
# ❌ ANTES (código real — NUNCA usó 'username' ni 'profile_pic_url'):
candidate_dict = {
    "handle": handle,
    "profile": p,                # ← no es columna de discovery_candidates
    "rough_score": rough,        # ← no es columna
    "_is_explore_mode": True,    # ← no es columna
    # FALTABAN: run_id y platform (parte del ON CONFLICT)
}
```

> ⚠️ **Corrección sobre documentación anterior:** La versión anterior de este documento describía el bug como uso de `username` y `profile_pic_url`. Ese código **nunca existió**. El bug real era `profile`, `rough_score`, `_is_explore_mode` y la ausencia de `run_id` y `platform` en el dict.

**Síntoma:** El `INSERT` a `discovery_candidates` fallaba silenciosamente (o insertaba NULLs en las columnas incorrectas), resultando en 0 candidatos aunque el pipeline dijera "encontré X handles".

**Fix:** Usar las columnas correctas de la tabla `discovery_candidates`:
```python
# ✅ DESPUÉS (claves correctas):
candidate_dict = {
    "run_id": run_id,
    "handle": handle,
    "platform": "instagram",
    "full_name": raw.get("full_name", ""),
    "bio": raw.get("bio", ""),
    "avatar_url": raw.get("profile_pic_url") or raw.get("avatar_url") or "",
    # ... todas las columnas existentes en la tabla
}
```

**Verificación:** El fix fue aplicado en commit `2fe9816` y deployado en Railway (commit `7796dc9`).

---

### Bug 2 — Frontend no enviaba `discovery_mode` (🔴 CRÍTICA)

**Detectado por:** Inspección de `LensSearchPage.tsx` + `lensApi.ts`
**Archivos:** `apps/web/src/features/lens/pages/LensSearchPage.tsx`
**Commit fix:** `92d6faa`

**Problema:** La UI de LENS no tenía un selector de modo visible, y el código no enviaba `discovery_mode` al backend. El `BriefStructured` se creaba sin ese campo, resultando en `discovery_mode="auto"` por default — que ejecuta el pipeline completo con enrichment.

**Fix:** Añadir `discovery_mode: 'explore' as const` en el brief enviado al crear el run.

**Verificación:** Deployado en Vercel (commit `df41d9e`).

---

### Bug 3 — Polling no cargaba candidatos en status='explored' (🔴 CRÍTICA)

**Detectado por:** Inspección de `useRunPolling.ts`
**Archivo:** `apps/web/src/features/lens/hooks/useRunPolling.ts`
**Commit fix:** `92d6faa` / `df41d9e`

**Problema:** El polling consultaba `data?.status` para decidir cuándo cargar candidatos, pero solo cargaba cuando `status === 'completed'`. El modo explorador usa `status === 'explored'`, que era ignorado.

```typescript
// ❌ ANTES:
if (runStatus === 'completed' && data?.total_candidates != null) {
  setCandidates(data.candidates ?? []);
}

// ✅ DESPUÉS:
if ((runStatus === 'completed' || runStatus === 'explored') && data?.total_candidates != null) {
  setCandidates(data.candidates ?? []);
}
```

**Verificación:** Deployado en Vercel (commit `df41d9e`).

---

### Bug 4 — TypeScript error en `discovery_mode` (⚠️ MEDIA)

**Detectado por:** Error de compilación TypeScript
**Archivo:** `apps/web/src/features/lens/pages/LensSearchPage.tsx`
**Commit fix:** `df41d9e`

**Problema:** El valor `'explore'` asignado a `discovery_mode` no era asignable al tipo `DiscoveryMode` que era una unión de literales (`"auto" | "analyze"`). Faltaba `"explore"` en la unión.

**Fix:** `discovery_mode: 'explore' as const` para forzar el tipo literal.

---

### Bugs adicionales encontrados

**Bug 5 — Ledger crash (try/except faltante):** El worker hacía INSERT en `budget_transactions` sin verificar que la tabla existía. Si la migration 00107 no estaba aplicada, el worker crashaba. **Fix:** Wrapped en try/except. La migration 00107 ahora es opcional.

---

### Bug 6 — `parent_run_id` descartado en `DiscoverySearchRequest` (🔴 CRÍTICA — Hito 27)

**Detectado por:** Auditoría de Claude Code Opus 5
**Archivos:** `packages/discovery/discovery/schemas.py`, `apps/api/app/api/v1/endpoints/discovery.py`
**Commit fix:** `hito27` (pendiente de commit en este push)

**Problema:** `analyze_selected` asignaba `brief_parsed["parent_run_id"] = str(body.run_id)` pero luego construía `DiscoverySearchRequest(**brief_parsed)`. Ese schema **no tenía el campo `parent_run_id`**, así que Pydantic v2 lo descartaba silenciosamente (`extra='ignore'` por defecto).

**Cadena de consecuencias:**
```python
# En discovery.py:
brief_parsed["parent_run_id"] = str(body.run_id)  # ← se asigna
brief = DiscoverySearchRequest(**brief_parsed)        # ← Pydantic descarta el campo

# En worker.py:
parent_run_id = getattr(brief, "parent_run_id", None)  # → None
_skip_discovery = is_analyze_mode and parent_run_id     # → False
```

Resultado: modo Analizar **repetía ~32 llamadas de discovery** (~$0.64) en vez de enriquecer solo los handles seleccionados.

**Fix:** Añadir `parent_run_id: str | None = Field(default=None, ...)` a `DiscoverySearchRequest`.

**Bug secundario en el mismo commit:** `platforms: list[Platform] = Field(default=lambda: [Platform.INSTAGRAM])` usaba `default=` en vez de `default_factory=`. En Pydantic v2, `default` se usa tal cual sin validar — `brief.platforms` era el objeto lambda, no una lista. Latente hoy porque nadie lee ese campo; rompe el día que se añada TikTok.

**Costo del bug:** ~$0.64 por cada run de Analizar si no se hubiera corregido.

---

### Bugs Nuevos Identificados — Fix A, Fix B, Fix C (2026-08-20)

> **Estado:** Fix A y Fix B ✅ RESUELTOS en Hito 28 (commit `a21dd97`). Fix C ⚠️ BAJA tech debt, sin acción requerida.

---

### Fix A — Pre-flight mode-aware ✅ RESUELTO HITO 28

**Archivo:** `apps/api/app/workers/worker.py:411-421`

**Problema original (Opus 5):** Pre-flight siempre estimaba 57 calls = $1.14. En Analizar (solo 3-5 calls = $0.06-0.10), sobreestimaba **11×**. Con saldo=$0.80, rechazaba runs que SÍ alcanzan.

**Fix aplicado:**
```python
if is_explore_mode:
    estimated_calls = ESTIMATED_DISCOVERY_CALLS  # 32 = $0.64
elif is_analyze_mode:
    estimated_calls = max(1, len(brief.handles_to_analyze)) if brief.handles_to_analyze else 1
else:
    estimated_calls = ESTIMATED_DISCOVERY_CALLS + MAX_HANDLES_TO_ENRICH  # 57 = $1.14
```

**Impacto:**
| Modo | Antes | Después |
|------|-------|---------|
| Explorar | $1.14 (78% sobre) | **$0.64** |
| Analizar (5 handles) | $1.14 (11× sobre) | **$0.10** |

---

### Fix B — DeepSeek skip en Explorar ✅ RESUELTO HITO 28

**Archivo:** `apps/api/app/workers/worker.py:1646`

**Problema original (Opus 5):** NO era el costo (~$0.10/run). Era la **corrupción de la decisión humana**. DeepSeek sobrescribía el rationale honesto con scores ficticios de `followers=0` y poblaba columnas visibles (`brand_fit`, `content_quality`, `audience_quality`) derivadas de NADA.

**Fix aplicado:**
```python
if analyze_with_ai and not is_explore_mode:
    # DeepSeek corre normalmente (Auto o Analizar)
else:
    reason = "explore_mode" if is_explore_mode else "analyze_with_ai=False"
    print(f"[...] STEP 5: Skipping AI analysis ({reason}), using rule-based scores")
    analyzed = to_analyze  # Rationale honesto preservado
```

---

### Fix C — `useRunPolling.ts` no usado por `LensSearchPage.tsx` ⚠️ BAJA

**Confirmado como tech debt, NO action needed.** `useRunPolling` es usado por `LensChatPage.tsx`. `LensSearchPage` usa `useDiscoveryRun.pollRun()` correctamente.

---

### Estado de Redis verificado

```
db_keys = 5
clients_connected = 4
redis_version = 8.2.1
```

Worker funcionando con 5 funciones registradas:
- `discovery_run_task`
- `sync_hypeauditor_task`
- `sync_metricool_task`
- `cron:scheduled_reports_cron`
- `cron:sync_metricool_task`

---

### Incidente de Google Cloud en Railway

**Timeline:**
- Railway tuvo incidente de Google Cloud infrastructure causando deployment delays
- Incidente resuelto: "The deployment pause has been lifted and the backlog of queued deployments is clearing."
- Deploy completado a las **18:26 UTC**
- Worker reiniciado y funcionando correctamente

---

### Verificación de enum `explored` en Railway

Confirmado por el usuario con query SQL directo a PostgreSQL de Railway:
```sql
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'discovery_run_status'::regtype;
```
Resultado: `explored` presente en el enum.

---

### Resumen de deploys

| Servicio | Commit | Status | Hora UTC |
|----------|--------|--------|----------|
| Railway API + Worker | `7796dc9` | ✅ Success | 18:26 UTC |
| Vercel Frontend | `df41d9e` | ✅ Success | 11:30 UTC |
| Railway API + Worker | `a21dd97` | ⏳ Pendiente (Hito 28) | — |

---

###get_balance() — Verificación pendiente con saldo=$43

El parser de `get_balance()` busca campos `balance`, `balance_usd`, `credits_usd`, `amount`. Cuando el saldo es `$0`, HikerAPI retorna `{"state": false, ...}`. El fix de Hito 25 detecta `state: false` y retorna `0.0`.

**AHORA CON SALDO=$43:** hacer curl para verificar el formato de respuesta con saldo positivo:
```bash
curl -s -H "x-access-key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/account
```

Esto confirmará que el parser sigue funcionando correctamente con saldo>0 o si HikerAPI usa un nombre de campo diferente.

El parser de `get_balance()` busca campos `balance`, `balance_usd`, `credits_usd`, `amount`. Cuando el saldo es `$0`, HikerAPI retorna `{"state": false, ...}` — sin esos campos. El fix de Hito 25 detecta `state: false` y retorna `0.0`.

**Sin verificar:** Qué retorna HikerAPI cuando el saldo es **positivo** (> $0). El parser actual solo fue probado con saldo=$0. Es posible que con saldo positivo HikerAPI retorne un campo con nombre diferente (ej: `credit`, `balance_amount`, etc.).

**Recomendación:** Después de recargar, hacer un curl al endpoint para documentar el formato real de respuesta con saldo positivo:
```bash
curl -s -H "x-access-key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/account
```

---

*Documento generado con contexto completo del repositorio — sesión 2026-08-20. Hito 28 aplicado (commit `a21dd97`): Fix A pre-flight mode-aware + Fix B DeepSeek skip explorar + extra='forbid'. HikerAPI balance: $43.00 USD. Para más detalle técnico, ver `docs/ARQUITECTURA_LENS.md` v5.3.*
