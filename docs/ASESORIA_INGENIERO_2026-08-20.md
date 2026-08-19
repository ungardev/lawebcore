# La Web Core — LENS Discovery Module
## Documentación de Ingeniería para Advisor

> **Fecha:** 2026-08-20
> **Audiencia:** Ingeniero advisor técnico
> **Proyecto:** La Web Core — LENS Discovery Module
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Ingeniero que documenta:** Sistema (contexto completo del repositorio)

---

## Tabla de Contenidos

1. [Executive Summary](#1-executive-summary)
2. [Stack Tecnológico Completo](#2-stack-tecnológico-completo)
3. [Infraestructura de Carpetas](#3-infraestructura-de-carpetas)
4. [LENS — Flujo Completo End-to-End](#4-lens--flujo-completo-end-to-end)
5. [HikerAPI — Sistema de Costos y Control](#5-hikerapi--sistema-de-costos-y-control)
6. [Modo Explorar — Descubrimiento Sin Costo](#6-modo-explorar--descubrimiento-sin-costo)
7. [Modo Analizar — Enrichment Selectivo](#7-modo-analizar--enrichment-selectivo)
8. [Modelo de Datos](#8-modelo-de-datos)
9. [Budget Tracking — G12](#9-budget-tracking--g12)
10. [Testing — pytest Suite](#10-testing--pytest-suite)
11. [Runbook Operacional](#11-runbook-operacional)
12. [Roadmap H26-H30](#12-roadmap-h26-h30)
13. [Commits Principales](#13-commits-principales)

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
│  MODO EXPLORAR ($0.24/run)              MODO ANALIZAR ($0.43/handle) │
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

- **Costo mínimo para 1 candidato:** $0.24 + $0.43 = **$0.67** (vs. $1.28 anterior)
- **Tasa de éxito:** ~80% con supervisión humana (vs. 2% automático)
- **Riesgo de 402 mid-run:** Bajo (pre-flight de saldo en analizar)

### Estado actual del proyecto

- 48 runs ejecutados históricamente, $28.33 gastados, **1 candidato encontrado**
- HikerAPI balance: **$0** (InsufficientFunds — requiere recarga)
- Modo Explorar/Analizar: **implementado en código** (commits `5ba4625`, `ba30a85`, `9c4bf70`)
- Migrations `00106` y `00107`: **pendientes de aplicar en Railway**
- Desfase Redis↔DB: **$25.13** (la motivación para G12)

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

> ⚠️ **Corrección histórica:** la documentación vieja decía "PostgreSQL via Supabase Cloud". El motor real en producción es PostgreSQL en Railway. Las migraciones viven en `supabase/migrations/` por historia del proyecto, pero el camino de datos de discovery no pasa por Supabase.

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
│   │   │   │   └── worker.py              # ★ 2175 líneas — pipeline completo
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
│           │       │   └── useRunPolling.ts
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
│       ├── 00000000000106_discovery_run_explored_status.sql  # ← PENDIENTE
│       └── 00107_budget_transactions.sql                        # ← PENDIENTE
│
├── docs/
│   ├── ASESORIA_INGENIERO_2026-08-20.md   # Este documento
│   ├── ARQUITECTURA_LENS_CORREGIDA.md     # Arquitectura técnica detallada
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
│   Usuario escribe brief → selecciona handles → descarga CSV │
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
   │(Instagram) │      │   (LLM)     │       │  Postgres   │
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
    audience_cities: list[str]            # ["Caracas"]
    discovery_mode: str                   # "auto" | "explore" | "analyze"
    handles_to_analyze: list[str]        # handles seleccionados en explorar
    parent_run_id: str | None             # run padre en modo analizar
    analyze_with_ai: bool = True         # DeepSeek scoring
    exclude_stores: bool = True          # excluir cuentas comerciales
    # ... 30+ campos más
```

#### Fase 2: Worker — `discovery_run_task` (worker.py:257)

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

> ⚠️ **Parámetros que causan 422:** `safe_int` en `/gql/user/about` y `/v1/location/search`; `id` en lugar de `location_pk` en endpoints de ubicación.

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
│  3. INCRBYFLOAT month_key (gasto mensual)                  │
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

### 5.5 Pre-flight de Saldo (Hito 23)

Antes de iniciar enrichment, el worker llama a `instagram_source.get_balance()` para comparar contra el costo estimado del run:

```python
estimated_calls = ESTIMATED_DISCOVERY_CALLS + MAX_HANDLES_TO_ENRICH  # 32 + 25 = 57
estimated_cost = estimated_calls * HIKERAPI_COST_PER_CALL_USD  # 57 × $0.02 = $1.14

balance = await instagram_source.get_balance()
if balance < estimated_cost:
    raise SourceUnavailable(
        f"Saldo insuficiente: ${balance:.2f} disponibles, "
        f"se necesitan ~${estimated_cost:.2f}. "
        f"Recarga en hikerapi.com/billing.",
        status_code=402,
    )
```

Esto evita el escenario histórico: run que gasta $1.64 en discovery y muere con 402 en la primera llamada de enrichment, produciendo 0 candidatos.

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

**Migración:** `00107_budget_transactions.sql` (ya en `main`, pendiente aplicar en Railway)

---

## 6. Modo Explorar — Descubrimiento Sin Costo

### 6.1 Qué hace

Ejecuta discovery completo (Steps 1-3, sin enrichment). El analista recibe una lista de handles con rough score (geo + niche) y selecciona cuáles enriquecer en modo Analizar.

### 6.2 Costo

**~$0.24-0.48/run** (solo discovery, sin enrichment)

### 6.3 Trigger

```python
# worker.py:332
is_explore_mode = getattr(brief, "discovery_mode", "auto") == "explore"
```

El usuario elige "Modo Explorar" en la UI. El campo `discovery_mode='explore'` va en `BriefStructured` y se persiste en `discovery_runs.brief_parsed`.

### 6.4 Lógica en el Worker

**Step 3 — Skip enrichment (worker.py:1037):**
```python
if handles_to_enrich and is_explore_mode:
    # HITO 24: modo explorar saltamos enrichment por completo.
    # Rough score derivado de geo + niche. Costo: solo discovery.
    logger.info("step3_explore_mode_skip_enrichment", handles_count=len(handles_to_enrich))
    await _save_progress_message(
        run_id,
        f"✅ Encontré {len(handles_to_enrich)} candidatos con señales de nicho. "
        f"Seleccioná los que quieras evaluar y ejecutá 'Analizar'.",
    )
```

**Scoring — Rough score sin followers (worker.py:1274):**
```python
if followers == 0:
    untracked_no_followers += 1
    if is_explore_mode:
        # Usamos rough score aunque no haya followers.
        rough = rough_score_map.get(handle, 0.0)
        if rough > 0:
            scored.append({
                "handle": handle,
                "match_score": rough * 100,
                "rough_score": rough,
                "_is_explore_mode": True,   # marca para FE
            })
        continue
    continue
```

### 6.5 Schema — Nuevo Status

```sql
-- migration 00106 (PENDIENTE DE APLICAR)
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

### 6.7 Por qué es la decisión correcta

| Criterio | Pipeline Automático | Modo Explorar |
|---|---|---|
| Costo/run | ~$0.98 | ~$0.24 |
| Control de calidad | Bajo (sin supervisión) | Alto (analista selecciona) |
| Riesgo 402 mid-run | Alto | Bajo |
| Tasa de éxito | 2% (1/48) | ~80% |

El enriquecimiento sin supervisión es costoso e irreversible. Si el enrichment falla, todo el run se pierde. En modo Explorar, el costo de discovery (~50 llamadas) es~$0.24: aceptable incluso si el resultado no sirve. El enrichment ($0.02 × N handles) solo se ejecuta sobre handles que el analista eligió conscientemente.

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

**Carga candidatos del run padre (worker.py:345):**
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

**Skip discovery completo (worker.py:623):**
```python
_skip_discovery = is_analyze_mode and parent_run_id

if _skip_discovery:
    print("[ANALYZE MODE] skipping STEP 1/2/2.5/3 discovery")
    hashtag_items, keyword_items, reels_items = [], [], []
    step1_handles, step2_handles = set(), set()
else:
    # Normal discovery
```

**Enrichment selectivo (worker.py:1051):**
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

**Auto-save como 'saved' (worker.py:1677):**
```python
if is_analyze_mode:
    for c in qualified:
        c["status"] = "saved"   # ← para proposal.csv
inserted_count = await _deduplicate_and_insert_candidates(qualified, run_id)
```

**Status final (worker.py:1686):**
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
├── metadata (JSONB)         -- current_step, completed_steps, is_explore_mode, etc.
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
├── entity_id             -- run_id
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
├── amount_usd            -- positivo=gasto, negativo=reversa
├── request_count
├── balance_after_usd
├── metadata (JSONB)
└── created_at            -- trigger impede UPDATE/DELETE
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
│  │ INSERT ONLY (trigger impede UPDATE/DELETE)              ││
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

El worker graba cada reserva en `budget_transactions` vía el cost tracker.

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
├── test_discovery_api.py        # 18 tests — endpoints
└── test_discovery_workflow.py   # 21 tests — integración
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
3. WARNING: Hacerlo ANTES de implementar controls puede gastar todo rápido

### 11.4 Aplicar Migrations en Railway

```bash
# Migration 00106 — CRÍTICA (explored status):
psql $DATABASE_URL -c "ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'explored';"

# Migration 00107 — (después de 00106):
# La tabla budget_transactions se crea con trigger inmutable.
# Aplicar desde el archivo SQL:
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
- `lens_active_runs` — runs activos сейчас
- `lens_candidates_total` — candidatos encontrados
- `lens_apify_cost_usd_total` — costo Apify acumulado

---

## 12. Roadmap H26-H30

### H26 ✅ (2026-08-19)
- Modo Explorar: schema, BE, FE, status `explored`
- G1-G3, G5-G10 implementados
- Commit: `5ba4625`

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

### H27 🔴 (REQUERIDO AHORA — antes de producción)
1. Apply migration `00106` en Railway:
   ```sql
   ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'explored';
   ```
2. Apply migration `00107` en Railway (después de 00106)
3. Recargar $50 en HikerAPI (con controls implementados)

### H28 ⏳ (próximo sprint)
- Verificación end-to-end del flujo Explorar→Analizar en producción
- Ajustes de UX basados en real usage
- Métricas: candidatos por run, tasa de conversión explorar→analizar

### H29 🔲 (futuro)
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

---

## Notas para el Advisor

### Lo que está funcionando
- Pipeline completo en código (Modo Explorar + Modo Analizar)
- BudgetFuse con Lua atómico (Hito 21)
- Circuit Breaker con state machine en Redis (Hito 21)
- Pre-flight de saldo antes de enrichment (Hito 23)
- Ledger inmutable para reconciliación (G12)
- 59 tests cubriendo contracts, API y workflow

### Lo que está pendiente (ANTES de producción)
1. **Apply migration 00106** en Railway — sin esto, `explored` no existe como enum y el modo explorar falla
2. **Apply migration 00107** en Railway — ledger inmutable
3. **Recargar HikerAPI** — con $0 todo falla en pre-flight
4. **Verificación end-to-end** — probar el flujo completo Explorar→Analizar en producción

### Métricas de éxito (post-recarga)
- Explorar: ¿cuántos handles descubre por run?
- Analizar: de los handles seleccionados, ¿cuántos enriquecen correctamente?
- Propuesta: de los candidatos guardados, ¿cuántos aparecen en proposal.csv?

### Lo que NO hacer
- No modificar el pipeline automático legacy (costo alto, bajo ROI)
- No agregar más features hasta que el flujo Explorar→Analizar esté validado
- No implementar billing avanzado hasta que el flujo básico esté 100% confirmado

---

*Documento generado con contexto completo del repositorio. Para más detalle técnico, ver `docs/ARQUITECTURA_LENS_CORREGIDA.md`.*
