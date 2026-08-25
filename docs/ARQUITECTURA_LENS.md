# La Web Core — Arquitectura Técnica LENS Discovery (versión 5.5)

> **Versión:** 5.5 — 2026-08-25
> **Reemplaza a:** `docs/ARQUITECTURA_LENS.md` v5.4 (`pipeline coverage analysis`)
> **Commit de referencia:** `81db353` (Hito 29 hotfix — extra='forbid' solo en frontera de entrada)
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Auditorías previas:** Hito 26 (2026-08-20: 4 bugs críticos), Hito 27 (2026-08-20: parent_run_id + platforms), Hito 28 (2026-08-20: Fix A/B + extra='forbid'), Hito 29 (2026-08-21: HOTFIX extra='forbid'), **Santiago Lanz v1.2 (2026-08-24):** Informe de Alineación Técnica con Plan Main de 5 fases
> **HikerAPI balance actual:** **$43.00 USD** ✅ (recargado 2026-08-20)
> **Plan Lanz:** `docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md` (Fases 0-5, ~16-22h trabajo, ~$0.44 extra/run)

---

## 1. Stack Tecnológico

### Backend
- **Framework:** FastAPI (Python 3.12 async) con Uvicorn
- **Workers:** ARQ sobre Redis
- **Acceso a datos:** asyncpg directo vía `shared_core.railway_pg` (SQLAlchemy presente pero no en el camino de discovery)
- **Validación:** Pydantic v2
- **Rate limiting:** SlowAPI
- **Monitoreo:** Prometheus (`/metrics`), Sentry
- **Ubicación:** `apps/api/` — Railway

### Frontend
- React 19 + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Query + Zustand + React Router v7 — Vercel

### Base de datos
- **Motor real en producción:** PostgreSQL en **Railway** (`postgres.railway.internal:5432/railway`), accedido con asyncpg desde `railway_pg`
- **Supabase:** legado. Las migraciones viven en `supabase/migrations/` por historia del proyecto, pero el camino de datos de discovery no pasa por Supabase
- **Extensiones:** `uuid-ossp`, `pgcrypto`, `pg_trgm`, `vector` (pgvector)

⚠️ **RLS no protege el camino de datos actual:** la aplicación se conecta con la credencial propietaria de la base, y RLS no se aplica al propietario salvo `FORCE ROW LEVEL SECURITY`. **Multi-tenancy real: no implementado** — filtrado por `business_unit_id` implementado en campaigns (Hito 17), queda pendiente en endpoints de discovery.

---

## 2. Arquitectura del sistema

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND (Vercel)                     │
│      React 19 + TanStack Query + Tailwind + shadcn       │
└──────────────────────────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌──────────────────────────────────────────────────────────┐
│                  BACKEND API (Railway)                   │
│                   FastAPI + Uvicorn                      │
│   /api/v1/*  ·  /health  ·  /ready  ·  /metrics          │
│                            │                             │
│                   encola vía ARQ (_job_id=discovery:{run_id})│
│                            ▼                             │
│              ARQ WORKER  —  discovery_run_task()         │
└──────────────────────────────────────────────────────────┘
         │                  │                    │
         ▼                  ▼                    ▼
┌─────────────┐   ┌────────────────┐   ┌──────────────────┐
│  HikerAPI   │   │  DeepSeek-V3   │   │ Railway Postgres │
│ (Instagram) │   │    (LLM)       │   │   + pgvector     │
│  $0.02/req  │   │    ~0.001$/1K  │   │                   │
└─────────────┘   └────────────────┘   └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│    Redis                                │
│  • ARQ job queue                        │
│  • Response cache (TTL por endpoint)    │
│  • BudgetFuse state (lens:budget:*)     │
│  • Circuit breaker state (lens:cb:*)     │
└─────────────────────────────────────────┘
```

---

## 3. Pipeline de descubrimiento

### 3.1 Flujo completo — worker.py (~1819 líneas)

```
1.  build brief
        ↓ DeepSeek parsea brief_text → BriefStructured
2.  QueryBuilder.build() → DiscoveryPlan
        genera hashtags, keywords, reels, topsearch, suggested
3.  _fetch_step1 — Hashtag top (3 hashtags × 2 páginas)
        GET /v2/hashtag/by/name?name=X         → 1 req × 3
        GET /v2/hashtag/medias/top?page_id=Y   → 3 req × 3
        → collect up to MAX_POSTS_PER_HASHTAG=20 per hashtag
        → CACHE: TTL 12h en Redis (lens:cache:{hash})
        ⚠️ Perfil REDUCIDO — sin bio ni follower_count
4.  _fetch_step1_recent — Hashtag recent (2 hashtags)
        GET /v2/hashtag/by/name?name=X         → 1 req × 2
        GET /v2/hashtag/medias/recent?page_id=Y → 1 req × 2 × 2 páginas
        → CACHE: TTL 30 min (1800s) — Hito 6
        ⚠️ Perfil REDUCIDO
5.  _fetch_step2 — Keyword search (3 keywords × 3 variantes)
        GET /v2/fbsearch/accounts?q=X         → 9 req total
        → CACHE: TTL 30 min
        ✅ Perfil COMPLETO — con bio, followers, etc.
6.  _fetch_step2p5 — Reels serp (1 keyword)
        GET /gql/reels_serp                     → 1 req
        ⚠️ Perfil REDUCIDO
7.  _fetch_step3 — Top search (1 keyword)
        GET /gql/topsearch?q=X                 → 2 req
        ✅ Perfil COMPLETO
8.  _fetch_step4 — Suggested profiles (1 seed)
        GET /v2/user/suggested/profiles         → 1 req
        ✅ Perfil COMPLETO
9.  PREFILTRO — selecciona hasta MAX_HANDLES_TO_ENRICH=50 handles
        Scoring: 0.5·geo + 0.5·niche
        ⚠️ PROBLEMA: scoring sin bio (hashtag/reels paths)
        Commerce/creator signals applied (Hito 18 — externalizable)
        Political/exclusion keywords filter (Hito 18)
10. ENRICHMENT — enrich_profile() por handle
        GET /v1/user/by/username?username=X   → hasta 50 req
        Lua script reserve_and_record() atómico (Hito 15)
        can_make_call() checked before HTTP
        record_call() on every HTTP response (Hito 14)
        MAX_CALLS_PER_RUN=50 (soft cap via enrichment limit)
        ⚠️ CANCELADO si breaker OPEN o budget agotado
11. SCORING
        geo_score(profile, geo_indicators, target_country=brief.audience_countries[0])
        niche_relevance(profile, profile_data)
        lens_score(profile, profile_data, cross_referenced, target_country)
12. CANDIDATE_ANALYZER — DeepSeek (si analyze_with_ai=true)
        $0.001 USD/1K tokens input — típicamente ~500 tokens
        $0.002 USD/1K tokens output — típicamente ~300 tokens
        ≈ $0.001 USD por candidato × N candidatos
13. upsert_many → PostgreSQL
```

### 3.2 Constants del pipeline

```python
MAX_HANDLES_TO_ENRICH = 50       # cuántos handles se enriquecen
MAX_POSTS_PER_HASHTAG = 20      # límite por hashtag
HASHTAGS_TOP = 3                # hashtags en step1
HASHTAGS_RECENT = 2              # hashtags en step1_recent
KEYWORDS = 3                    # keywords base en step2
TOP_SEARCH = 1                  # keyword para topsearch
SUGGESTED_SEEDS = 1             # semillas para suggested
ENRICHMENT_INCLUDE_ABOUT = False  # get_user_about desactivado
```

---

## 4. Modelo de datos — Discovery

```
discovery_runs
├── id (UUID)
├── brief_text                — brief original en texto
├── brief_parsed (JSONB)       — BriefStructured serializado
├── status                    — pending | running | completed | partial | failed
├── total_candidates
├── actual_cost_usd           — costo acumulado del run (HikerAPI)
├── metadata (JSONB)           — current_step, completed_steps, replay_miss_count
├── title
├── error
├── started_at, completed_at, created_at
└── business_unit_id (FK)

discovery_candidates           — UNIQUE(run_id, platform, handle)
├── id, run_id (FK)
├── handle, full_name, bio, avatar_url, url
├── platform, country, city
├── followers, following, posts_count
├── engagement_rate, avg_likes, avg_comments
├── match_score               — 0-100 (lens_score)
├── niche_relevance, geo_relevance
├── content_quality, audience_relevance, audience_quality
├── brand_fit                 — DeepSeek (si analyze_with_ai)
├── ai_rationale              — resumen DeepSeek
├── rationale                 — texto generado por reglas
├── tier, is_tienda, status
├── raw_payload (JSONB)       — lens_score breakdown, geo_score, cross_ref
└── fetched_at

discovery_conversations
├── id, discovery_run_id (FK, nullable)
├── current_step, accumulated_brief, parsed_brief_json
├── pending_refinements, message_count, title
└── state (JSONB)             — write-through cache del orchestrator

discovery_messages
├── id, conversation_id (FK)
├── role, content
├── tool_calls (JSONB), tool_results (JSONB)
└── reasoning, cost_usd, latency_ms

discovery_profiles             — vocabulario por vertical, generado por LLM
├── id, fingerprint (UNIQUE)
├── vertical_slug, languages (JSONB), countries (JSONB)
├── hashtags, keywords, niche_keywords (JSONB)
├── geo_indicators, buy_intent_keywords (JSONB)
├── commerce_signal_keywords (JSONB)  — Hito 18
├── creator_signal_keywords (JSONB)  — Hito 18
├── exclusion_keywords (JSONB)        — Hito 18
├── elite_data (JSONB)
├── source                — seed | llm | manual | fallback
├── quality_score, times_used
└── created_at, updated_at

api_costs
└── provider, operation, entity_id, cost_usd, tokens_in/out, occurred_at
```

---

## 5. HikerAPI — Análisis de costos REAL (Plan "Start")

### 5.1 Plan de precios

```
PLAN: HikerAPI "Start"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Costo por request:     $0.02 USD
Balance mínimo:         $20 USD (~1,000 requests)
Endpoints incluidos:    Todos los de Instagram (100+)
Renovación:             Prepago — se consume del balance

⚠️ IMPORTANTE: La configuración anterior decía $0.0006 USD/call.
Este valor corresponde a un plan LEGADO. El plan ACTUAL "Start" cobra
$0.02 USD por request — 33× más caro. Esto explica el consumo
excesivo de $50-72 USD en 2 días reportado en la auditoría original.
```

### 5.2 Solicitudes por fase — DESGLOSE EXACTO

```
┌─────────────────────────────────────────────────────┬──────────┬──────────────┐
│ Fase                                                │ Requests │ Costo USD    │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ STEP 1: Hashtag Top (3 hashtags)                   │          │              │
│   /v2/hashtag/by/name?name=X                        │   3     │  $0.06       │
│   /v2/hashtag/medias/top?page_id=Y (×3 páginas)    │   9     │  $0.18       │
│   Subtotal step1                                    │  12     │  $0.24       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ STEP 1_recent: Hashtag Recent (2 hashtags)          │          │              │
│   /v2/hashtag/by/name?name=X                        │   2     │  $0.04       │
│   /v2/hashtag/medias/recent (2 páginas)            │   4     │  $0.08       │
│   Subtotal step1_recent                             │   6     │  $0.12       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ STEP 2: Keyword (3 keywords × 3 variantes geo)       │          │              │
│   /v2/fbsearch/accounts?q=X                         │   9     │  $0.18       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ STEP 2p5: Reels serp (1 keyword)                   │   1     │  $0.02       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ STEP 3: Top search (1 keyword)                      │   2     │  $0.04       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ STEP 4: Suggested (1 seed)                         │   1     │  $0.02       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ SUBTOTAL Discovery (sin enrichment)                 │  31     │  $0.62       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ STEP 10: ENRICHMENT (hasta 50 perfiles)             │          │              │
│   /v1/user/by/username?username=X (≤50)            │  50     │  $1.00       │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ TOTAL POR RUN (típico con enrichment completo)      │  81     │  $1.62 USD   │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ TOTAL POR RUN (sin enrichment, solo discovery)       │  31     │  $0.62 USD   │
├─────────────────────────────────────────────────────┼──────────┼──────────────┤
│ SI HAY CACHE HIT: enrichment completo               │  31     │  $0.62 USD   │
│ SI HAY CACHE HIT: enrichment 50% (25 calls)        │  56     │  $1.12 USD   │
└─────────────────────────────────────────────────────┴──────────┴──────────────┘
```

### 5.3 Escenarios de costo por run

```
ESCENARIO                          Requests   Costo/run   Balance $20
─────────────────────────────────────────────────────────────────────
Discovery + Enrichment 100%          81      $1.62      ~12 runs
Discovery + Enrichment 50%            56      $1.12      ~17 runs
Discovery + Enrichment 25%            44      $0.88      ~22 runs
Discovery ONLY (sin enrichment)     31      $0.62      ~32 runs
Discovery cache WARM (partial enrich) 56      $1.12      ~17 runs
```

### 5.4 Impacto del budget mensual

```
PRESUPUESTO MENSUAL:         $10.00 USD
Runs con enrichment 100%:    ~6 runs/mes  (cada $1.62)
Runs sin enrichment:         ~16 runs/mes  (cada $0.62)
Runs con enrichment 50%:      ~8 runs/mes  (cada $1.12)

CONCLUSIÓN: $10/mes permite ~6-8 runs completos con enrichment,
o ~16 runs de solo discovery (sin enriquecer perfiles).
```

### 5.4.1 Modelo de Contabilidad Único (Hito 21)

**Problema antes de Hito 21:**
- `reserve_and_record()` en worker.py incremented both run counter AND monthly spend
- `_record_if_applicable()` in hikerapi_client.py ALSO incremented monthly spend
- **Resultado:** doble conteo del gasto mensual ($0.04/call en vez de $0.02)
- Caché hit cobraba (reserve corría antes de verificar caché)
- Redis restart borraba SHA → evalsha fallaba → `return True` (fail-open silencioso)
- `MAX_CALLS_PER_RUN` solo cubría enrichment (discovery no se contaba)

**Solución (Hito 21):** `_get()` en `HikerAPIClient` es el **ÚNICO** punto de contabilidad.

```
HikerAPIClient._get():
    1. breaker.can_proceed()     ← ¿fuente disponible?
    2. ¿caché? → return (sin cobrar)
    3. ¿replay? → ReplayMiss (sin cobrar)
    4. reserve_and_record()      ← ÚNICO punto de cobro
    5. HTTP request
```

**Beneficios:**
- ✅ Sin doble conteo (un solo sitio)
- ✅ Caché no cobra (reserva después de cache check)
- ✅ Replay mode cuesta $0 de verdad
- ✅ Discovery + enrichment ambos consumen `MAX_CALLS_PER_RUN` (cap real)
- ✅ Fail closed ante error de Redis (return False, no True)
- ✅ Fallback NOSCRIPT si Redis reinicia

**Log events nuevos:**
- `budget_fuse_noscript_fallback` — Redis reinició o SCRIPT FLUSH ejecutado
- `budget_fuse_reserve_error_failing_closed` — Redis caído, fusible cerrado
- `enrichment_budget_capped` — run se marca `partial` al alcanzar tope

### 5.4.2 Test Run Hito 21 (PRE-HITO 22) — 2026-08-17 (Run ID: `1a1d6128-d1e4-4922-b7c7-1c2cb949c658`)

> ⚠️ **Este run usó worker con código PRE-Hito 21.** El ARQ worker mantenía código viejo en memoria. Railway deployó pero el worker no recargó. Hallazgos de ese run llevaron a Hito 22.

| Campo | Valor | Análisis |
|-------|-------|----------|
| `status` | `partial` | Pipeline terminó; enrichment falló |
| `total_candidates` | **0** | Todos los perfiles filtrados |
| `actual_cost_usd` | **0.0** | ❌ Cost tracking no funcionaba (código viejo) |
| `total_unique_handles` | **123** | ✅ Discovery encontró handles |
| `step3_degraded` | `true` | ✅ Flag correcto (enrichment falló) |

**Hallazgos que llevaron a Hito 22:**
1. Worker ejecutando código pre-Hito 21 (ARQ no recargó)
2. `actual_cost_usd = 0` — costo no se persistía
3. `lens:budget:run:{id}` no se creaba
4. Filtro `geo_no_signal` rejectaba perfiles sin bio

### 5.4.3 Test Run Hito 22 — 2026-08-18 (Run ID: `0c44ea23-53f6-42a8-8a9c-c6ec85359d2e`)

> ✅ **Hito 22 aplicado y verificado.** Worker recargado con código correcto. Cost tracking funcionando. Pero surfaced 3 bugs nuevos.

**Brief enviado:**
```json
{
  "product_name": "Test Hito 22",
  "industry": "belleza",
  "niches": ["makeup", "skincare", "haircare", "nails", "beauty blogger", "belleza Venezuela"],
  "platforms": ["instagram"],
  "audience_countries": ["VE"],
  "exclude_stores": true,
  "analyze_with_ai": true
}
```

**Pipeline logs (19:50:56 → 19:52:40 UTC, 110s):**

```
[discovery_run_task] START run_id=0c44ea23-53f6-42a8-8a9c-c6ec85359d2e
[STEP1] 60 posts from hashtags source=hikerapi
[STEP2] 66 users from keywords source=hikerapi
[STEP1_RECENT] 40 posts from recent hashtag search
[STEP2p5_REELS] 0 creators from reels search
[STEP3] 0 accounts from topsearch
[STEP4] 0 accounts from suggested
[DIAG] unique_handles=133
[STEP 3] Profile enrichment → HTTP 402 Payment Required (balance agotado)
[SCORING] 0 scored → 0 score≥5 → 0 qualified (tienda_excluded=True)
[discovery_run_task] DONE total_candidates=0
```

**Resultados verificados en DB:**

| Campo | Valor | Análisis |
|-------|-------|----------|
| `status` | `partial` | ✅ 200 OK en GET (no más 500) |
| `actual_cost_usd` | **`$1.64`** | ✅ Cost tracking funciona correctamente |
| `total_unique_handles` | **133** | ✅ Discovery efectivo (60 hashtag + 40 recent + 66 keyword) |
| `total_candidates` | **0** | ❌ Todos filtrados por `exclude_stores=true` |
| `step3_degraded` | `true` | ✅ 402 durante enrichment |
| `api_costs` insertado | **82 calls × $0.02** | ✅ Registro correcto en `api_costs` |
| Mensaje al usuario | "filtro geográfico" | ⚠️ **ENGANOSO** — fue filtro tiendas |

**Redis keys confirmadas:**
```
lens:budget:hikerapi:2026-08 = "1.64"  (82 calls)
lens:budget:run:0c44ea23-53f6-42a8-8a9c-c6ec85359d2e = 82
```

**3 Bugs Nuevos Descubiertos (Hito 22) — CORREGIDOS POR OPUS 5:**

| # | Bug | Severidad | Causa real (Opus 5) |
|---|-----|-----------|----------------------|
| N1 | `exclude_stores=true` filtra 100% handles VE | ❌ REFUTADO | Enrichment falló con 402 → sin followers → 0 scored |
| N2 | Mensaje fijo "filtro geográfico" misleading | ⚠️ MEDIA | Corregido en Hito 23 con `_build_zero_candidates_message` |
| N3 | Geolocalización sin validación post-enrichment | ⚠️ MEDIA | POSTERGADO hasta que haya candidatos |
| **REAL** | Run condenado sin pre-flight de saldo | 🔴 CRÍTICA | $1.64 gastados en discovery, 0 candidatos garantizados |

> ⚠️ **El Bug N1 estaba equivocado.** El log `tienda_excluded=True` es el **valor del flag de configuración**, NO un conteo. Los handles nunca fueron enriquecidos — enrichment murió con 402. Causa real: `followers=0` para todos → filtrados en scoring. Ver `LENS_AUDIT7_2026-08-18.md` §1.

**Costo Real Confirmado por Run (Hito 23 optimizado):**

| Escenario | Requests | Costo USD |
|-----------|----------|-----------|
| Discovery + Enrichment 100% (50 handles) | ~82 | **$1.64** (pre-Hito 23) |
| Discovery + Enrichment 50% (25 handles) | ~56 | **$1.12** (pre-Hito 23) |
| **Discovery + Enrichment 50%→25 (Hito 23)** | **~57** | **~$1.14** |
| Discovery ONLY (sin enrichment) | ~32 | **$0.64** |
| **Con discovery reducido + 25 handles** | **~37** | **~$0.74** |

⚠️ **Hito 23 optimiza el enrichment de 50→25 handles** ($1.00→~$0.50) y añade pre-flight de saldo para evitar runs condenados. El costo por run baja de ~$1.64 a ~$1.14. Con $10 de saldo: ~8-9 runs completos.

---

## ⚠️ ALERTA DE COSTO — HikerAPI Balance Recargado

```
╔══════════════════════════════════════════════════════════════════════╗
║  HIKERAPI BALANCE: $43.00 USD ✅ RECARGADO 2026-08-20        ║
╠══════════════════════════════════════════════════════════════════════╣
║  Costo por run confirmado (modo Explorar):  ~$0.64 USD         ║
║  Costo por run confirmado (modo Analizar 5 handles): ~$0.10 USD ║
║  Runs posibles con $43 (Explorar):           ~67 runs completos    ║
║  Runs posibles con $43 (Analizar 5 handles):  ~430 análisis       ║
╠══════════════════════════════════════════════════════════════════════╣
║  COSTOS HITO 28 (MODE-AWARE):                                   ║
║  • Explorar: 32 calls × $0.02 = $0.64                          ║
║  • Analizar: N calls × $0.02 = ~$0.02-0.20 por run            ║
║  • Auto: 57 calls × $0.02 = $1.14                              ║
║  • El 'último dólar' YA NO queda inutilizable                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Desglose de costo por fase confirmado en test run real:**

| Fase | Calls | Costo | % del total |
|------|-------|-------|-------------|
| Discovery (hashtags + keywords) | ~32 | $0.64 | 39% |
| Enrichment (50 handles) | 50 | $1.00 | 61% |
| **Total por run** | **~82** | **$1.64** | 100% |

### 5.5 Guards implementados contra sobre-costo

```
┌─────────────────────────────────────────────────────────────────┐
│ GUARD              │ VALOR    │ MECANISMO                      │
├────────────────────┼──────────┼────────────────────────────────┤
│ MAX_HANDLES_ENRICH │ 50       │ Limita enrichment a 50 calls   │
│ MAX_CALLS_PER_RUN  │ 120      │ Lua atómico — para TODAS calls │
│ MONTHLY_BUDGET_USD │ $10      │ BudgetFuse corta al 100%      │
│ Circuit Breaker    │ 5 err    │ Abre tras 5 errores 5xx       │
│ Cache TTL          │ 30m-12h  │ Reduce requests repetidos     │
│ RUN_MODE=replay    │ flag     │ $0 — usa solo cache          │
└─────────────────────────────────────────────────────────────────┘
```

### 5.6 Costos de DeepSeek (análisis IA)

```
analyze_with_ai=false (default):    $0.00 USD/run
analyze_with_ai=true:
  Input:  ~500 tokens × $0.001/1K = $0.0005
  Output: ~300 tokens × $0.002/1K = $0.0006
  Por candidato: ~$0.0011 USD
  × 50 candidatos = ~$0.055 USD/run adicional
```

### 5.7 Fórmula del costo real por run

```python
def real_cost_per_run(
    hashtag_calls: int = 12,
    keyword_calls: int = 9,
    other_discovery_calls: int = 10,
    enriched_count: int = 50,
    enriched_cached: int = 0,        # calls saved due to cache
    ai_analysis: bool = False,
) -> dict:
    discovery = hashtag_calls + keyword_calls + other_discovery_calls
    enrichment = max(0, enriched_count - enriched_cached)
    total_requests = discovery + enrichment

    cost_hikerapi = total_requests * 0.02
    cost_deepseek = (0.0011 * enriched_count) if ai_analysis else 0.0
    cost_total = cost_hikerapi + cost_deepseek

    return {
        "total_requests": total_requests,
        "hikerapi_usd": round(cost_hikerapi, 4),
        "deepseek_usd": round(cost_deepseek, 4),
        "total_usd": round(cost_total, 4),
        "runs_in_monthly_budget": int(10.0 / cost_total),
    }
```

---

## 6. Configuración del Plan HikerAPI "Start"

```
┌────────────────────────────────────────────────────────┐
│  HIKERAPI PLAN "START" — Configuración real         │
├────────────────────────────────────────────────────────┤
│  API Key:        HIKERAPI_API_KEY (env)              │
│  Costo/req:      $0.02 USD                          │
│  Balance actual: $20 prepago                        │
│  Requests límite: ~1,000 requests con $20            │
│  Billing:        https://hikerapi.com/billing         │
│  Docs:           https://api.hikerapi.com/docs       │
│                                                    │
│  ENDPOINTS USADOS POR EL PIPELINE:                 │
│  GET /v2/hashtag/by/name         (info hashtag)    │
│  GET /v2/hashtag/medias/top       (top posts)      │
│  GET /v2/hashtag/medias/recent   (recent posts)   │
│  GET /v2/fbsearch/accounts        (keyword search) │
│  GET /gql/topsearch               (top accounts)   │
│  GET /v2/user/suggested/profiles  (sugeridos)      │
│  GET /v1/user/by/username         (enriquecimiento)│
│  GET /v1/user/about               (fraude, OFF)   │
└────────────────────────────────────────────────────────┘

⚠️ NOTA: El campo HIKERAPI_COST_PER_CALL_USD=0.02 en config
refleja el plan "Start" real ($0.02/request). BudgetFuse ahora
funciona correctamente con el costo real. El modelo de contabilidad
cambió en Hito 21: un solo punto de cobro en HikerAPIClient._get().
```

---

## 7. Variables de entorno

```bash
# ===== DATOS =====
DATABASE_URL=postgresql+asyncpg://...@postgres.railway.internal:5432/railway
ARQ_REDIS_URL=redis://...

# ===== APIS =====
HIKERAPI_API_KEY=***          # Plan Start: $0.02/req
DEEPSEEK_API_KEY=sk-***      # ~$0.001/1K tokens

# ===== LENS Budget & Cost Controls =====
MONTHLY_BUDGET_USD=10.0       # Corte mensual hard
MAX_CALLS_PER_RUN=120          # Máximo de requests por run (c/limiter Lua)
BUDGET_ALERT_THRESHOLD=0.7     # Warning al 70% ($7.00)
HIKERAPI_COST_PER_CALL_USD=0.02  # Plan Start real — $0.02/req
HIKERAPI_5XX_BREAKER_THRESHOLD=5  # 5xx consecutivos → breaker abre
HIKERAPI_5XX_BREAKER_TTL_S=300    # Segundos en estado OPEN (3×TTL=900s HALF_OPEN)

# ===== Feature Flags =====
HIKERAPI_STEP0_LOCATION=false    # Búsqueda por ubicación (desactivado)
HIKERAPI_INCLUDE_ABOUT=false      # GET /v1/user/about — fraude (desactivado)
ENABLE_AI_ANALYZER=false         # Análisis DeepSeek (desactivado por defecto)

# ===== Modo Replay (testing sin costo) =====
RUN_MODE=live                    # 'live' (default) o 'replay'

# ===== Deployment =====
API_ENV=production
ADMIN_TOKEN=***
```

---

## 8. Redis — Qué se guarda y por cuánto tiempo

```
lens:cache:{hash}
  TTL: 30 min (keywords, recent) / 12h (hashtag top)
  Contenido: JSON de respuestas HikerAPI
  Uso: evita repetir requests idênticos

lens:budget:hikerapi:{YYYY-MM}
  TTL: 40 días
  Contenido: float — gasto acumulado del mes
  Uso: BudgetFuse.assert_budget_available()

lens:budget:alert:hikerapi:{YYYY-MM}
  TTL: 40 días
  Contenido: "1" (flag — alert ya enviado)
  Uso: Solo un warning por mes al threshold

lens:budget:run:{run_id}
  TTL: 24h
  Contenido: int — # requests de este run
  Uso: reserve_and_record() atómico + can_make_call()

lens:cb:hikerapi:state
  TTL: TTL del breaker × 3 (900s = 10 min en HALF_OPEN)
  Contenido: "CLOSED" | "OPEN" | "HALF_OPEN" + failure_count
  Uso: CircuitBreaker — compartido entre todos los workers

lens:profile:{fingerprint}
  TTL: 7 días
  Contenido: DiscoveryProfile serializado
  Uso: evita regenerar perfiles LLM por brief duplicado
```

---

## 9. Issues conocidos

### 9.1 Resueltos (Hitos 1-20 + Bonus 1)

| Hito | Commit | Bug/Issue | Fix |
|------|--------|-----------|-----|
| 1 | `be32a39` | Apify + source_registry + step2p6 + prefilter muertos | Eliminados |
| 2 | `835bf2a` | 4xx/5xx swallow | Excepciones propagan |
| 2 | `835bf2a` | 402 = 0 candidatos | SourceUnavailable + status=failed |
| 3+4 | `4819857` | Sin budget fuse | BudgetFuse.assert_budget_available() |
| 3+4 | `4819857` | 5xx en cascada | CircuitBreaker: 5 → OPEN |
| 3+4 | `4819857` | Sin límite per-run | BudgetFuse per-run counter |
| 5 | `766cfee` | Doble cobro por redeploy | `_job_id=discovery:{run_id}` |
| 6 | `2da78ab` | is_private perdido en merge | Añadido en update() |
| 6 | `2da78ab` | search_hashtag_recent sin cache | cache_ttl=1800 |
| 7 | `9b43316` | Docs desactualizadas | Documentación completa |
| 8 | `2f7b06b` | en_id typo | Corregido a `_job_id` |
| 9 | `390277b` | 402 no clasificaba | 402 → SourceUnavailable |
| 9 | `390277b` | asyncio.gather absorbía excepciones | 4 re-raise post-gather |
| 10 | `950d475` | apify_client zombi | Eliminado |
| 10 | `950d475` | Breaker copia divergente | Singleton unificado |
| 10 | `950d475` | HALF_OPEN TTL rota | TTL×3 (900s) |
| 10 | `950d475` | record_call() nunca llamado | Movido a `_get()` |
| 10 | `950d475` | can_make_call() nunca llamado | Check antes de HTTP |
| 10 | `950d475` | _breaker pool leak | Singleton módulo |
| 10 | `950d475` | HIKERAPI_5XX_BREAKER_* no usadas | Pasadas al constructor |
| 11 | `06a952e` | geo_score target_iso2=None siempre | target_country explícito |
| 12 | `cc3f57c` | Sin modo replay | RUN_MODE=replay + ReplayMiss |
| 13 | `a9cbb78` | enqueue_job None ignorado | Check + log dedup |
| 14 | `6fd29b1` | record_call solo 2xx | Todas las HTTP responses |
| 15 | `f3735b2` | TOCTOU en MAX_CALLS_PER_RUN | Lua atómico reserve_and_record |
| 16 | `bad1d37` | is_private ausente en search | Añadido a ambos paths |
| 17 | `a91e76d` | business_unit_id hardcoded | user.business_unit_id del JWT |
| 18 | `b5e404e` | Vocabulario hardcodeado | 3 JSONB cols + defaults |
| 19 | `a5da503` | orchestrator.state memory leak | LRU/TTL OrderedDict |
| 20 | `611d22e` | test_hashtag_cap_30 + test_result_ranker rotos | Arreglados |
| 21 | `hito21` | Doble conteo + caché cobra + fail-open | Single accounting en _get() + NOSCRIPT fallback + fail-closed |
| 22 | `7e4a99b` | actual_cost_usd=0 + partial=500 + worker old | get_run_calls() + PARTIAL enum + redeploy |
| 23 | `42b900b` | Run condenado sin pre-flight + mensaje fijo | get_balance() pre-flight + except SourceUnavailable raise + _build_zero_candidates_message + EXPLORED status |
| 24 | `hito24` | Pipeline automático decide solo — 0 candidatos tras 3 semanas | Modo Explorar + Modo Analizar — analista como prefiltro |
| 25 | `hito25` | get_balance() parser bug — InsufficientFunds sin campo balance | Detecta `state: false` → retorna 0.0 → pre-flight aborta correctamente |
| Bonus | `880da7d` | ReplayMiss invisible | Contador en metadata |

### 9.2 Abiertos (Post-Hito 28)

| Issue | Prioridad | Detalle | Estado |
|-------|-----------|---------|--------|
| HIKERAPI_COST_PER_CALL_USD legacy | ✅ RESUELTO | Cost ahora $0.02 real en config | — |
| Worker con código viejo (pre-Hito 21) | ✅ RESUELTO | Hito 22 — redeploy verificado con logs | — |
| actual_cost_usd no se persiste | ✅ RESUELTO | Hito 22 — $1.64 grabado correctamente | — |
| `lens:budget:run:{id}` no se crea | ✅ RESUELTO | Hito 22 — key creada con 82 calls | — |
| discovery_runs.metadata sin `partial` enum | ✅ RESUELTO | Hito 22 — enum actualizado | — |
| `except Exception` silencia SourceUnavailable | ✅ RESUELTO HITO 23 | 402 → degraded; ahora `raise` antes de `except Exception` | — |
| Sin pre-flight de saldo (runs condenados) | ✅ RESUELTO HITO 23+25 | get_balance() + detecta `state:false` → retorna 0.0 → aborta | — |
| `exclude_stores` filtra 100% handles VE | ❌ REFUTADO | Opus 5 probó que la causa fue enrichment 402, no tiendas | — |
| Mensaje engañoso al usuario | ✅ RESUELTO HITO 23 | `_build_zero_candidates_message` naming counter real | — |
| MAX_HANDLES_TO_ENRICH 50→25 | ✅ RESUELTO HITO 23 | Enrichment cost $1.00→~$0.50 | — |
| Migration 00106 no aplicada | ✅ RESUELTO HITO 26 | Enum `explored` confirmado en Railway DB | — |
| Modo Explorar insertaba 0 candidatos | ✅ RESUELTO HITO 26 | Dict usaba claves incorrectas → columnas DB correctas (commit `2fe9816`) | — |
| Frontend no enviaba `discovery_mode` | ✅ RESUELTO HITO 26 | `'explore' as const` añadido en LensSearchPage (commit `92d6faa`) | — |
| Polling no cargaba candidatos `explored` | ✅ RESUELTO HITO 26 | useRunPolling.ts ahora reconoce status `explored` (commit `df41d9e`) | — |
| TypeScript error `discovery_mode` | ✅ RESUELTO HITO 26 | `as const` corrige tipo literal (commit `df41d9e`) | — |
| Ledger crash sin migration 00107 | ✅ RESUELTO HITO 26 | try/except protege worker; 00107 ahora opcional | — |
| `parent_run_id` descartado en schema | ✅ RESUELTO HITO 27 | DiscoverySearchRequest ahora tiene el campo; Analizar no repite discovery | — |
| `platforms` default= en vez de default_factory= | ✅ RESUELTO HITO 27 | Pydantic v2 ahora recibe lista, no lambda | — |
| **Fix A: Pre-flight sobreestimaba costo** | ✅ RESUELTO HITO 28 | Modo-aware: Explorar $0.64, Analizar real, Auto $1.14 — commit `a21dd97` | — |
| **Fix B: DeepSeek corrompía decisión en Explorar** | ✅ RESUELTO HITO 28 | Skip DeepSeek en Explorar — rationale honesto preservado — commit `a21dd97` | — |
| **extra='forbid' en schemas** | ✅ RESUELTO HITO 28 | BriefStructured + DiscoverySearchRequest con ConfigDict(extra="forbid") — commit `a21dd97` | — |
| **Fix C: `useRunPolling.ts` no usado por LensSearchPage** | ⚠️ BAJA | Tech debt — hook usado por LensChatPage, NO por LensSearchPage — NO action needed | **PENDIENTE** |
| HikerAPI balance | ✅ RESUELTO | Balance=$43.00 USD — recargado 2026-08-20 | — |
| `accepted` nunca se actualiza | 🔴 CRÍTICA | `discovery_runs.accepted` siempre 0 | **PENDIENTE** |
| Desfase Redis↔DB ($25.13) | 🔴 CRÍTICA | Budget tracking no refleja gasto real en runs pre-Hito-21 | **PENDIENTE** |
| Geolocalización sin validación post-enrichment | ⚠️ MEDIA | POSTERGADO — no hay candidatos aún para validar | **PENDIENTE** |
| Enriquecimiento sobre muestra casi aleatoria | **Alta** | Prefiltro decide sin bio; afecta calidad | **PENDIENTE** |
| geo_no_signal filter rechaza hashtag profiles | ⚠️ MEDIA | Perfiles de hashtag sin bio → geo_score=0.0 → filtrados | **PENDIENTE** |
| Filtrado business_unit_id en endpoints discovery | **Media** | Hito 17 arregló campaigns; discovery aún no filtra | **PENDIENTE** |
| discovery_profiles sin 3 columnas nuevas | **Media** | Migration 105 creada, debe ejecutarse | **PENDIENTE** |

---

## 10. Deployment

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

**Seguridad de reintentos:** `restartPolicyMaxRetries=3` + `_job_id=discovery:{run_id}` previene doble cobro si el worker se reinicia a mitad de un run. Hito 13 añade visibilidad cuando un reintento es bloqueado por la ventana de deduplicación de arq (1h keep_result).

---

## 11. Módulos nuevos o actualizados (ciclo LENS 2026-08-14/17)

| Módulo | Ubicación | Responsabilidad |
|--------|-----------|----------------|
| `exceptions.py` | `packages/discovery/discovery/` | SourceUnavailable, TransientSourceError, BudgetExhausted, ReplayMiss |
| `hikerapi_circuit_breaker.py` | `packages/discovery/discovery/tools/` | Singleton CLOSED→OPEN→HALF_OPEN, Redis, TTL×3 |
| `budget_fuse.py` | `apps/api/app/core/` | Budget enforcement + Lua atómico + NOSCRIPT fallback + fail-closed |
| `worker_enqueuer.py` | `apps/api/app/core/` | `enqueue_job` con `_job_id` + check de dedup |
| `hikerapi_client.py` | `packages/discovery/discovery/tools/` | `_get()` con single accounting point (Hito 21), replay, breaker |
| `orchestrator.py` | `packages/discovery/discovery/` | LRU/TTL en state cache |
| `geo_boost.py` | `packages/discovery/discovery/scoring/` | geo_score con `target_country` explícito |
| `lens_score.py` | `packages/discovery/discovery/scoring/` | lens_score con `target_country` kwarg |
| `00000000000104_...sql` | `supabase/migrations/` | Enum `discovery_run_status` + `partial` |
| `00000000000105_...sql` | `supabase/migrations/` | 3 JSONB cols en `discovery_profiles` |
| `test_budget_fuse.py` | `apps/api/tests/` | Tests Hito 21: single accounting, NOSCRIPT, fail-closed, partial |

---

## 12. Bugs Críticos Detectados (Test Run Real 2026-08-17)

> Ejecutado con worker Hito 21 activo + saldo real HikerAPI. Run ID: `1a1d6128-d1e4-4922-b7c7-1c2cb949c658`

## 12. Bugs Críticos Detectados (Hito 22 Test Run — 2026-08-18)

> Run ID: `0c44ea23-53f6-42a8-8a9c-c6ec85359d2e` — Hito 22 aplicado, cost tracking funcionando, 3 bugs nuevos encontrados.

### Bug 1 — Pydantic enum sin `partial` (✅ RESUELTO en Hito 22)

**Archivo:** `packages/discovery/discovery/schemas.py`
**Fix:** `PARTIAL = "partial"` añadido al enum
**Verificación:** `GET /runs/{id}` retorna 200 OK con `status=partial` — no más 500.

---

### Bug 2 — `actual_cost_usd` siempre 0 (✅ RESUELTO en Hito 22)

**Archivo:** `apps/api/app/core/budget_fuse.py` — método `get_run_calls()`
**Fix:** Worker actualiza `actual_cost_usd` con costo real de `api_costs` al finalizar run
**Verificación:** Run `0c44ea23` — `actual_cost_usd=$1.64`, `api_costs` insertado con 82 calls

---

### Bug 3 — Balance agotado en enrichment (⚠️ PERSISTE)

**Problema:** Los ~$1.50-2.00 de discovery + enrichment agotan el saldo rápido. Con $10 de saldo: solo 5-6 runs completos.
**Solución temporal:** Recargar HikerAPI. **Solución estructural:** Reducir `MAX_HANDLES_TO_ENRICH` de 50 a 20.

---

## 13. Bugs Descubiertos — Hitos 22-23 + Auditoría Opus 5

> **Nota importante sobre Bug N1:** El Bug N1 documentado en Hito 22 fue REFUTADO por Claude Code Opus 5. El análisis original estaba equivocado — la causa real de 0 candidatos era el enrichment fallido con 402, NO el filtro `exclude_stores`. Los cambios documentados aquí reflejan los hallazgos reales de Opus 5.

### Bug Real — Run condenado sin pre-flight de saldo (🔴 CRÍTICA)

**Descubierto por:** Auditoría Opus 5 (LENS_AUDIT7_2026-08-18.md)

**Problema:** BudgetFuse valida el presupuesto INTERNO (contador en Redis), pero NO el saldo REAL del proveedor HikerAPI. El run `0c44ea23` gastó $1.64 en discovery y murió con 402 en la primera llamada de enrichment. Sin enrichment ningún perfil tiene seguidores y el resultado es 0 candidatos.

**Costo confirmado:**
| Run | Costo | Resultado | Causa |
|-----|-------|-----------|-------|
| `0c44ea23` (Hito 22) | **$1.64** | 0 candidatos | Enrichment 402 — sin pre-flight |
| `1a1d6128` (pre-Hito 22) | **~$1.64** | 0 candidatos | Misma causa (código viejo no registraba costo) |
| **Total desperdiciado** | **$3.26** | — | 2 runs condenados antes de enrichment |

**Causa raíz:** `except Exception` en el bloque de enrichment (worker.py ~línea 1035) capturaba `SourceUnavailable` (el 402) y lo convertía en `step3_degraded=True`, permitiendo que el run continuara en silencio. Esto gastar el discovery completo ($0.64) para un resultado garantizado de 0 candidatos.

**Fix aplicado (Hito 23):**
1. `except SourceUnavailable: raise` ANTES de `except Exception` — el 402 ya no se silencia
2. Pre-flight `get_balance()` antes de gastar nada — si saldo < costo estimado, se aborta con mensaje claro
3. `MAX_HANDLES_TO_ENRICH` 50→25 — reduce enrichment cost de $1.00 a ~$0.50
4. Mensaje al usuario derivado del contador dominante — ya no dice "filtro geográfico" fijo

---

### Bug N1 (REFUTADO) — `exclude_stores` como causa de 0 candidatos

**Estado: NO ES UN BUG — Diagnóstico incorrecto en Hito 22**

**Lo que decían los logs:**
```
[SCORING] 0 scored → 0 score≥5 → 0 qualified (tienda_excluded=True)
```

**Lo que esto significa:**
- `tienda_excluded=True` es el **valor del flag de configuración** (`exclude_stores` del brief), NO un conteo de tiendas excluidas
- `0 scored` significa que la lista llegó VACÍA al scoring — no que las tiendas fueran filtradas
- La causa real: enrichment falló con 402 → todos los perfiles tienen `followers=0` → todos filtrados en `worker.py:1054` (`if profile.followers < TIER_MIN_FOLLOWERS`)

**Handles "de tiendas" mencionados en ARQUITECTURA_LENS.md v3.7:**
Esos handles (`shopmarianazambrano.ve`, etc.) NUNCA fueron enriquecidos con follower count. El enrichment murió en la primera llamada con 402. Esos nombres aparecían en los logs de STEP1/STEP2 (perfiles REDUCIDOS, sin follower data).

**Fix sugerido (para cuando haya candidatos):**
POSTERGADO hasta que el pipeline produzca candidatos reales. Una vez que `total_candidates > 0`, si la mayoría son tiendas, tiene sentido abordar `exclude_stores`.

---

### Bug N2 — Mensaje engañoso al usuario (⚠️ MEDIA — CORREGIDO EN HITO 23)

**Problema original:** El mensaje decía "filtro geográfico" fijo, pero la causa real podía ser otra (enrichment fallido, filtro tiendas, etc.).

**Fix aplicado (Hito 23):** `_build_zero_candidates_message()` deriva el mensaje del contador que MÁS perfiles descarta:
- Si enrichment falló → "no pude completar la búsqueda"
- Si tiendas_excluded domina → "X cuentas son comerciales"
- Si geo mismatches → "X no son del país"
- Si sin seguidores → "X no tienen seguidores"

---

### Bug N3 — Geolocalización sin validación post-enrichment (⚠️ MEDIA — POSTERGADO)

**Problema:** Los `geo_indicators` no se validan contra la bio del perfil después del enrichment.

**Decisión:** POSTERGADO hasta que el pipeline produzca candidatos. No tiene sentido validar geo de una lista vacía.

**Fix sugerido (para cuando haya candidatos):**
Después del enrichment, verificar que el bio contiene al menos 2-3 `geo_indicators`. Si no, penalizar `geo_score`.

---

## 14. Hito 24 — Modo Explorar + Modo Analizar (Rediseño de Producto)

> **Fecha:** 2026-08-19
> **Inspirado por:** Análisis de Claude Code Opus 5 — "El problema de fondo no es técnico, es de proporción"
> **Commit:** `hito24` (próximo commit)

### 14.1 El Problema

El pipeline automático descubría 133 handles pero solo podía evaluar 25 (por presupuesto). El prefiltro decidía a ciegas cuáles 25 sobrevivían. Con $10/mes: ~13 runs, ninguno entregaba valor.

**El diagnóstico de Opus 5:**
> *"Eso no se arregla afinando el prefiltro: está mal repartido de origen."*

### 14.2 La Solución: Dos Modos

#### Modo Explorar — ~$0.24/búsqueda
- Solo discovery, **sin enrichment**
- Devuelve la lista cruda de handles con nombre, foto, bio y rough score (geo + niche)
- El analista revisa y marca cuáles quiere evaluar
- Costo: solo discovery (~32 calls = $0.64, pero con pre-flight se puede abortar antes si saldo insuficiente)

#### Modo Analizar — $0.02/perfil
- El analista seleccionó handles en modo explorar
- Lens enriquece y puntúa **solo esos** handles
- Costo: ~$0.02 × N handles seleccionados

#### Campaña Completa (Explorar + Analizar 15 handles)
- Explorar: ~$0.24
- Analizar 15: ~$0.30
- **Total: ~$0.54** vs $1.14 del pipeline automático
- Con $10: **~18 campañas completas** vs 8-9 intentos del pipeline anterior

### 14.3 Cambios en el Código

**`schemas.py` — BriefStructured:**
```python
discovery_mode: str = Field(
    default="auto",
    description="'auto' = full pipeline, 'explore' = discovery only, 'analyze' = enrich selected handles"
)
handles_to_analyze: list[str] = Field(default_factory=list)
```

**`schemas.py` — DiscoveryRunStatus:**
```python
EXPLORED = "explored"  # Hito 24 — modo explorar completado
```

**`worker.py`:**
- Si `discovery_mode == "explore"`: skip enrichment, usa rough score (geo + niche) como match_score
- Si `discovery_mode == "analyze"`: enrichment SOLO de `brief.handles_to_analyze`
- Status: `explored` en vez de `completed` para modos de dos pasos

**`migration 00106`:** Añade valor `explored` al enum `discovery_run_status`

### 14.4 Por Qué Es Mejor

1. **Elimina el problema en vez de mitigarlo**: No hay prefiltro automático — decide una persona
2. **Encaja con cómo trabaja una agencia**: Nadie acepta 15 influencers que eligió un algoritmo sin mirarlos
3. **Se puede lanzar YA**: No requiere arreglar el prefiltro, ni el geo, ni el ER
4. **La señal de cuándo parar está bien definida**: Si modo explorar no devuelve lista usable, el problema es el proveedor

### 14.5 Flujo de Usuario

```
1. Usuario crea brief → discovery_mode="explore"
2. Pipeline descubre handles → status="explored"
3. Frontend muestra lista con rough scores
4. Usuario selecciona handles → discovery_mode="analyze" + handles_to_analyze=[...]
5. Pipeline enriquece y scorea solo esos → status="completed"
6. Usuario ve candidatos finales con match_score real
```

### 14.6 Costo Comparado

| Escenario | Costo/run | Runs con $10 |
|-----------|-----------|--------------|
| Pipeline automático (Hito 23) | ~$1.14 | ~8-9 |
| Explorar + Analizar (15 handles) | ~$0.54 | ~18 |
| Solo Explorar | ~$0.24 | ~41 |

---

## 15. Verificación Empírica 2026-08-19

> **Fuente:** Railway Web Console — queries directas a PostgreSQL y Redis
> **Realizada por:** MiniMax + datos del usuario
> **Propósito:** Validar empíricamente las hipótesis de Opus 5 antes de recargar HikerAPI

### 15.1 Runs Históricos — 48 total, $28.33 gastados

```
SELECT SUM(actual_cost_usd), COUNT(*) FROM discovery_runs;
→ $28.3351 total, 48 runs
```

| Métrica | Valor |
|---------|-------|
| Total runs | 48 |
| Total gastado | **$28.33** |
| Completed | 42 |
| Partial | 2 |
| Failed | 2 |
| Candidatos producidos | **1** (solo run `03e00ee1` del 2026-08-12) |

**El sistema ha producido 1 candidato en toda su historia.**

### 15.2 Desfase Redis↔DB — $25.13 no trackeados

```
Redis: lens:budget:hikerapi:2026-08 = "3.2"
DB sum: $28.33
Diferencia: $25.13
```

**Causa probable:** Los runs de ago-12 a ago-17 (antes de Hito 21) no crearon keys en Redis porque el sistema de budget tracking no existía. Redis solo muestra lo gastado desde ago-17 en adelante.

**Implicación:** BudgetFuse no es confiable para saber cuánto queda. El pre-flight Hito 23+25 lee `lens:budget:hikerapi:2026-08` para estimar saldo, pero ese número no refleja el gasto histórico real.

### 15.3 El Bug Crítico — get_balance() Parser

**Hallazgo:** El patch de Opus 5 (Hito 23) en `get_balance()` buscaba campos `balance`, `balance_usd`, `credits_usd`, `amount` en la respuesta. Pero HikerAPI retorna:

```json
// Cuando saldo = $0:
{"state": false, "error": "Top up your account...", "exc_type": "InsufficientFunds"}

// El parser buscaba "balance" → no existe → retorna None → pre-flight SE OMITE
```

**Validación con curl en Railway:**
```bash
curl -s -H "x-access-key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/account
→ {"state":false,"error":"Top up your account at https://hikerapi.com/billing","exc_type":"InsufficientFunds"}
```

**Fix aplicado (Hito 25):**
- Detecta `state: false` → retorna `0.0` → pre-flight activa `raise SourceUnavailable(...)` correctamente
- Costo del run abortado: **$0** (en vez de $0.64 de discovery desperdiciado)

### 15.4 Endpoints de HikerAPI — Confirmados

| Endpoint | Status | Notas |
|----------|--------|-------|
| `/v1/account` | ✅ 200 OK | Auth con `x-access-key` funciona |
| `/v1/user/balance` | ✅ 200 OK | Mismo response que `/v1/account` |
| `/account` (sin v1) | ❌ 404 | Path incorrecto |
| `/balance` (sin v1) | ❌ 404 | Path incorrecto |

### 15.5下一步 — Después de esta verificación

1. ✅ Hito 25 fix aplicado (get_balance parser)
2. ✅ Migration 00106 (enum `explored`) — ejecutada y confirmada por usuario
3. ✅ Railway deploy exitoso (commit `7796dc9`, 18:26 UTC)
4. ✅ Vercel frontend deployado (commit `df41d9e`, 11:30 UTC)
5. ✅ Hito 26: 4 bugs críticos corregidos (dict columnas, frontend mode, polling, TS)
6. ✅ Hito 27: `parent_run_id` en DiscoverySearchRequest (modo Analizar no repite discovery)
7. ⏳ Recargar $20 HikerAPI (~58 campañas completas, recomendación Opus 5)
8. ⏳ Test Modo Explorar — validar `status='explored'` y candidatos en UI
9. ⏳ Test Modo Analizar — validar enrichment selectivo
10. ⏳ Demo con marca real

---

## 16. Hito 25 — Fix get_balance() Parser

> **Fecha:** 2026-08-19
> **Commit:** `hito25` (próximo commit)
> **Archivos:** `packages/discovery/discovery/tools/hikerapi_client.py`

### 16.1 El Bug

El parser original de Opus 5 buscaba `balance`, `balance_usd`, `credits_usd`, `amount` en la respuesta JSON. Pero cuando el saldo es `$0`, HikerAPI retorna:

```json
{"state": false, "error": "Top up your account...", "exc_type": "InsufficientFunds"}
```

Ningún campo coincide → `get_balance()` retornaba `None` → pre-flight se omitía → run procedía → enrichment fallaba con 402 → **$0.64 desperdiciados**.

### 16.2 El Fix

```python
async def get_balance(self) -> float | None:
    for path in ("/v1/account", "/v1/user/balance", "/account"):
        try:
            client = await self._get_client()  # Auth header ya configurado en _get_client()
            resp = await client.get(path)
            if resp.status_code != 200:
                continue
            data = resp.json()

            # HITO 25: detectar respuesta de saldo insuficiente
            if data.get("state") is False:
                logger.warning(
                    "hikerapi_balance_insufficient",
                    path=path,
                    exc_type=data.get("exc_type"),
                    error=data.get("error"),
                )
                return 0.0  # Activa pre-flight abort correctamente

            for key in ("balance", "balance_usd", "credits_usd", "amount"):
                if key in data:
                    return float(data[key])

            logger.warning("hikerapi_balance_response_unrecognized", path=path, data_keys=list(data.keys()))
        except Exception:
            continue
    return None
```

### 16.3 Cambios Respecto al Patch de Opus 5

| Cambio | Razón |
|--------|-------|
| No se añadió auth header explícito | `_get_client()` ya configura `x-access-key` en el constructor del cliente |
| Se añadió detección de `state: false` | El fix crítico — activa pre-flight cuando saldo=$0 |
| Se añadieron logs de warning | Visibilidad cuando el balance es insuficiente o el formato es inesperado |

### 16.4 Validación Post-Fix

**Caso saldo=$0 (antes de recarga):**
```
1. get_balance() → 0.0
2. balance is not None → True
3. 0.0 < estimated_cost ($0.57) → True
4. raise SourceUnavailable(...) → status=failed, costo=$0 ✅
```

**Caso saldo=$50 (post-recarga):**
```
1. get_balance() → 50.0 (asumiendo campo "balance" en respuesta)
2. 50.0 < 0.57 → False
3. Run procede normal ✅
```

---

## 17. Hito 26 — Bugs Críticos de la Sesión 2026-08-20

> **Fecha:** 2026-08-20
> **Commits:** `2fe9816`, `92d6faa`, `df41d9e`
> **Deploy:** Railway ✅ `7796dc9` (18:26 UTC) | Vercel ✅ `df41d9e` (11:30 UTC)

### 17.1 Bug 1 — Dict de candidato con claves incorrectas (🔴 CRÍTICA)

**Commit:** `2fe9816`
**Archivo:** `apps/api/app/workers/worker.py`

El dict de candidato en modo explorar usaba claves que NO correspondían a columnas de la tabla `discovery_candidates`:

```python
# ❌ ANTES (código real — NUNCA usó 'username' ni 'profile_pic_url'):
candidate_dict = {
    "handle": handle,
    "profile": p,                # ← no es columna de discovery_candidates
    "rough_score": rough,        # ← no es columna
    "_is_explore_mode": True,    # ← no es columna
    # FALTABAN: run_id y platform (parte del ON CONFLICT)
}

# ✅ DESPUÉS (claves correctas):
candidate_dict = {
    "run_id": run_id,
    "handle": handle,
    "platform": "instagram",
    "full_name": raw.get("full_name", ""),
    "bio": raw.get("bio", ""),
    "avatar_url": raw.get("profile_pic_url") or raw.get("avatar_url") or "",
    # ... todas las columnas existentes en discovery_candidates
}
```

> ⚠️ **Corrección:** La versión anterior de este documento describía el bug como uso de `username` y `profile_pic_url`. Ese código **nunca existió**. El bug real era `profile`, `rough_score`, `_is_explore_mode` y la ausencia de `run_id` y `platform`.

**Impacto:** INSERT fallaba silenciosamente → 0 candidatos aunque pipeline dijera "encontré X handles".

---

### 17.2 Bug 2 — Frontend no enviaba `discovery_mode` (🔴 CRÍTICA)

**Commit:** `92d6faa`
**Archivo:** `apps/web/src/features/lens/pages/LensSearchPage.tsx`

La UI no tenía selector de modo visible y no enviaba `discovery_mode` al backend. Brief se creaba con `discovery_mode="auto"` por default → pipeline completo con enrichment.

**Fix:** `discovery_mode: 'explore' as const` añadido en el brief.

---

### 17.3 Bug 3 — Polling no cargaba candidatos en status='explored' (🔴 CRÍTICA)

**Commit:** `92d6faa` / `df41d9e`
**Archivo:** `apps/web/src/features/lens/hooks/useRunPolling.ts`

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

---

### 17.4 Bug 4 — TypeScript error en `discovery_mode` (⚠️ MEDIA)

**Commit:** `df41d9e`
**Archivo:** `apps/web/src/features/lens/pages/LensSearchPage.tsx`

`'explore'` no asignable a la unión literal `DiscoveryMode`. Fix: `as const` fuerza el tipo literal.

---

### 17.5 Bug 5 — Ledger crash sin migration 00107 (⚠️ MEDIA)

**Commit:** `2fe9816`
**Archivo:** `apps/api/app/workers/worker.py`

Worker hacía INSERT en `budget_transactions` sin verificar que la tabla existía. Si migration 00107 no estaba aplicada → worker crashaba.

**Fix:** Wrapped en try/except. Migration 00107 ahora es **OPCIONAL**.

---

### 17.6 Bug 6 — `parent_run_id` descartado en `DiscoverySearchRequest` (🔴 CRÍTICA — Hito 27)

**Detectado por:** Auditoría de Claude Code Opus 5
**Archivos:** `packages/discovery/discovery/schemas.py`, `apps/api/app/api/v1/endpoints/discovery.py`

**Problema:** `analyze_selected` asignaba `brief_parsed["parent_run_id"]` pero `DiscoverySearchRequest` **no tenía ese campo**. Pydantic v2 descartaba el campo silenciosamente (`extra='ignore'`).

```python
# En discovery.py:
brief_parsed["parent_run_id"] = str(body.run_id)  # ← se asigna
brief = DiscoverySearchRequest(**brief_parsed)        # ← Pydantic descarta

# En worker.py:
parent_run_id = getattr(brief, "parent_run_id", None)  # → None
_skip_discovery = is_analyze_mode and parent_run_id     # → False
```

Resultado: modo Analizar **repetía ~32 llamadas de discovery** (~$0.64) en vez de enriquecer solo los handles seleccionados. Costo real: **$0.70** en vez de **$0.06**.

**Fix (commit `hito27`):**
```python
# En schemas.py — DiscoverySearchRequest:
parent_run_id: str | None = Field(
    default=None,
    description="Parent run ID for analyze mode.",
)
```

**Bug secundario en el mismo commit:** `platforms` usaba `default=` en vez de `default_factory=` — en Pydantic v2 el objeto lambda se guardaba sin validar.

---

### 17.6 Verificación de Redis

```
db_keys = 5
clients_connected = 4
redis_version = 8.2.1
```

Worker con 5 funciones registradas:
- `discovery_run_task`
- `sync_hypeauditor_task`
- `sync_metricool_task`
- `cron:scheduled_reports_cron`
- `cron:sync_metricool_task`

---

## 18. Recursos

| Recurso | URL |
|---------|-----|
| Repositorio | https://github.com/ungardev/lawebcore |
| API Docs | `https://lawebcore-production.up.railway.app/api/docs` |
| HikerAPI billing | `https://hikerapi.com/billing` |
| HikerAPI docs | `https://api.hikerapi.com/docs` |
| Railway | `https://railway.app/project/lawebcore` |
| Vercel | `https://vercel.com/lawebcore` |

---

## 19. Hito 28 — Fix A, Fix B y extra='forbid' Aplicados (2026-08-20)

> **Commit:** `a21dd97` — Railway deploy pendiente
> **Estado:** ✅ RESUELTO
> **Tests:** 17 nuevos en `test_hito28_e2e.py` (17 passed)

### 19.1 Fix A — Pre-flight Mode-Aware ✅ RESUELTO

**Archivo:** `apps/api/app/workers/worker.py:411-421`

**Problema original (Opus 5):** Pre-flight siempre estimaba 57 calls ($1.14) incluso en modo Explorar (solo necesita 32 calls = $0.64) y en Analizar (solo 1 call × N handles = ~$0.06 para 3 handles).

**Caso crítico:** Con saldo=$0.80, pre-flight rechazaba un Explorar que SÍ alcanza ($0.80 > $0.64). El "último dólar" de cada recarga quedaba inutilizable.

**Fix aplicado:**
```python
# worker.py:411-421
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
| Explorar | 57 calls = $1.14 | 32 calls = $0.64 |
| Analizar (5 handles) | 57 calls = $1.14 | 5 calls = $0.10 |
| Auto | 57 calls = $1.14 | 57 calls = $1.14 (sin cambio) |

---

### 19.2 Fix B — DeepSeek Skip en Modo Explorar ✅ RESUELTO

**Archivo:** `apps/api/app/workers/worker.py:1646`

**Problema original (Opus 5):** DeepSeek corría en modo Explorar sin enrichment → `followers=0`, bio vacía. Sobrescribía el rationale honesto con scores ficticios y poblaba columnas visibles (`brand_fit`, `content_quality`, `audience_quality`) con valores derivados de NADA. **El analista decidiría a quién enriquecer basándose en datos falsos.**

**Costo real:** $0.08-0.16 por run de Explorar (hasta 80 candidatos en lotes de 10), NO $0.02 como se creía. Pero el problema real NO es el costo — es la **corrupción de la decisión humana**.

**Fix aplicado:**
```python
# worker.py:1646
analyze_with_ai = getattr(brief, "analyze_with_ai", True)
if analyze_with_ai and not is_explore_mode:  # ← nuevo: is_explore_mode check
    # DeepSeek corre normalmente (Auto o Analizar)
else:
    reason = "explore_mode" if is_explore_mode else "analyze_with_ai=False"
    print(f"[...] STEP 5: Skipping AI analysis ({reason}), using rule-based scores")
    analyzed = to_analyze  # Rationale honesto preservado
```

---

### 19.3 extra='forbid' en Schemas ✅ RESUELTO

**Archivos:**
- `packages/discovery/discovery/schemas.py:8` — `ConfigDict` import
- `packages/discovery/discovery/schemas.py:57` — `BriefStructured`
- `packages/discovery/discovery/schemas.py:197` — `DiscoverySearchRequest`

**Problema original (Opus 5):** 8 auditorías, 8 bugs de la misma familia — ninguno falla ruidosamente, todos "afirman algo incorrecto en silencio". El bug de `parent_run_id` (Hito 27) habría sido un `ValidationError` inmediato en el primer test si el schema tuviera `extra='forbid'`.

**Fix aplicado:**
```python
from pydantic import BaseModel, ConfigDict, Field

class BriefStructured(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... todos los campos ...

class DiscoverySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... todos los campos ...
```

Ahora cualquier campo inesperado en `BriefStructured` o `DiscoverySearchRequest` genera `ValidationError` inmediato en vez de ser descartado silenciosamente.

---

### 19.4 Fix C — Tech Debt Confirmada ⚠️ BAJA (sin acción)

`useRunPolling.ts` no es usado por `LensSearchPage.tsx` — usa `useDiscoveryRun.pollRun()` directamente. El hook SÍ es usado por `LensChatPage.tsx`. **No action needed** — es tech debt para sprint futuro.

---

### 19.5 Nota para la Demo — Explorar devuelve máximo 25 candidatos

El rough_score_map viene del prefiltro limitado a `MAX_HANDLES_TO_ENRICH=25`. No es un bug, pero es importante: no prometer 133 handles y mostrar 25 en la demo.

---

*Documento generado: 2026-08-20 — Arquitectura LENS v5.4 (Hito 28 aplicado). HikerAPI balance: $43.00 USD. Fix A (pre-flight mode-aware): Explorar $0.64, Analizar real. Fix B (DeepSeek skip explorar): rationale honesto preservado. extra='forbid': clase de bug cerrada. v5.4 NUEVO: Pipeline Coverage Analysis — 8 brechas identificadas para Opus 5.*

---

## 20. Pipeline Coverage Analysis — 8 Brechas Identificadas (v5.4)

> **Fecha:** 2026-08-20
> **Auditoría:** #14 — Pipeline Coverage Analysis
> **Analista:** Opus 5 (auto-análisis)
> **Propósito:** Identificar qué NO está capturando el pipeline actual para que Opus 5 proponga patches

### 20.0 Resumen Ejecutivo

El pipeline actual de LENS captura el **~80%** de lo que HikerAPI puede ofrecer. Las 8 brechas identificadas representan el 20% restante — principalmente calidad de datos post-enrichment que no se usa para scoring.

| # | Brecha | Severidad | Esfuerzo | Costo Extra | Hito Previo |
|---|--------|-----------|----------|-------------|-------------|
| 1 | Quality Score (engagement real) | 🟡 MEDIA | 1h | +$0.10-0.20 | H31 |
| 2 | Nicho real (captions) | 🟡 MEDIA | 30min | +$0.05 | H32 |
| 3 | Geo post-enrichment | 🟢 BAJA | 30min | $0 | H29 |
| 4 | Tier enforcement (5K-50K) | 🟢 BAJA | 15min | $0 | H29 |
| 5 | Cross-reference boost | 🟡 MEDIA | 1h | $0 | H32 |
| 6 | Verified boost | 🟢 BAJA | 15min | $0 | H29 |
| 7 | Time-decay | 🟡 MEDIA | 1h | $0 | H33 |
| 8 | Bot detection avanzada | 🟡 MEDIA | 2h | $0 | H35 |

---

### 20.1 Brecha 1: Sin Quality Score de Engagement

**Archivo:** `apps/api/app/workers/worker.py:_prefilter_profiles` + `packages/discovery/discovery/candidate_analyzer.py`

**Severidad:** 🟡 MEDIA | **Esfuerzo:** 1h | **Costo:** +$0.10-0.20/run

**Problema actual:** El `rough_score` en prefilter (línea 967) se calcula como `0.5 * geo + 0.5 * niche` sin datos de engagement. El enrichment (Step 5) SÍ obtiene `avg_likes`, `avg_comments`, `followers` pero NO se usan para re-calcular el score en Modo Explorar.

```python
# ACTUAL — worker.py línea 967 (prefilter):
rough = 0.5 * geo + 0.5 * niche
# followers=0 en este punto (REDUCED profile)
# → No se puede calcular engagement rate
```

```python
# ACTUAL — candidate_analyzer.py (DeepSeek analysis):
# Solo en Modo Analizar (is_analyze_mode):
if analyze_with_ai and is_analyze_mode:
    ai_scores = await _analyze_batch(...)
```

**Impacto:** Un influencer con 50K followers y 50 likes por post (90% bots) rankea igual que uno con 50K followers y 5K likes por post.

**Código ideal:**
```python
# Post-enrichment, antes de guardar en rough_score_map:
er = (avg_likes + avg_comments) / followers if followers > 0 else 0
quality_score = min(er * 100, 100)  # 0-100

# Apply quality boost:
if quality_score > 50: rough *= 1.3
elif quality_score > 20: rough *= 1.1
elif quality_score < 5: rough *= 0.5  # Penalize very low ER
```

**Recomendación:** Implementar en Modo Explorar solo para los top 5 handles por rough_score. Sub-sample de 5 = $0.10.

---

### 20.2 Brecha 2: Sin Detección de Nicho Real via Captions

**Archivo:** `packages/discovery/discovery/candidate_analyzer.py:_build_single_prompt`

**Severidad:** 🟡 MEDIA | **Esfuerzo:** 30min | **Costo:** +$0.05 DeepSeek/run

**Problema actual:** El `niche_score` se calcula solo con `biography` y `niche_keywords` matching. Muchos perfiles de pet care NO tienen "perros" en la bio pero SÍ en los captions de sus posts.

```python
# ACTUAL — worker.py línea 1026 (niche scoring):
niche = niche_relevance_score(
    {"biography": bio, "username": username},
    brief.niche_keywords
)
```

**Impacto:** Un perfil que publicita productos para perros en sus posts pero tiene bio genérica ("lifestyle", "content creator") queda sub-rankeado.

**El endpoint `/v1/user/by/username` SÍ retorna `latest_posts` con `caption`** — pero no se usa para nicho:

```python
# candidate_analyzer.py — lo que DeepSeek recibe:
prompt = f"""Analyze creator: {username}
Bio: {biography}
Followers: {follower_count}
Latest posts: {latest_posts}"""  # latest_posts contiene captions
```

**Conflicto con Hito 28 Fix B:** Fix B dice "no DeepSeek en Explorar" para evitar scores ficticios. Pero la detección de nicho SÍ tiene datos (captions + bio). La solución es **permitir DeepSeek SOLO para niche classification** (no para brand_fit ni audience_quality que sí son ficticios en Explorar).

**Código ideal:**
```python
# En candidate_analyzer.py, modo Explorar:
# DeepSeek SOLO para nicho, NO para brand_fit/audience_quality
if is_explore_mode:
    # Solo niche classification
    prompt = f"Niche classification: {bio} + captions: {captions}"
    niche_real_score = await deepseek_classify(prompt)
    # NO brand_fit ni audience_quality
else:
    # Modo Analizar: todo habilitado
    ...
```

**Recomendación:** Implementar como H32. Fix conflictos con Fix B requiere permiso específico de usuario.

---

### 20.3 Brecha 3: Sin Validación Geo Post-Enrichment

**Archivo:** `apps/api/app/workers/worker.py:_prefilter_profiles` + `enrich_profile`

**Severidad:** 🟢 BAJA | **Esfuerzo:** 30min | **Costo:** $0

**Problema actual:** El `geo_score` se calcula en el prefilter (línea 967) sobre la bio REDUCIDA, sin `country` ni `city`. Después del enrichment (Step 5) tenemos `country`, `city`, `locationName` pero NO se re-evalúa.

```python
# ACTUAL — worker.py línea 967 (prefilter con REDUCED profile):
geo = geo_score(
    {"biography": bio, "country": "", "city": ""},  # country vacía siempre
    geo_indicators, target_country
)
```

**Después del enrichment (Step 5) — perfil completo disponible:**
```python
# enrichment retorna:
profile = {
    "username": "...",
    "biography": "...",
    "country": "VE",      # ← disponible
    "city": "Caracas",    # ← disponible
    "location_name": "...", # ← disponible
    ...
}
```

**Impacto:** Un perfil con bio en inglés que matchea "pet care" pero es de Caracas rankea igual que uno de Miami. El geo_score se calcula sin datos reales de geo.

**Código ideal:**
```python
# Post-enrichment, en _enrich_profile o después:
if profile.get("country"):
    geo_enriched = geo_score(
        {
            "biography": profile.get("biography", ""),
            "country": profile.get("country", ""),
            "city": profile.get("city", ""),
            "location_name": profile.get("location_name", "")
        },
        geo_indicators, target_country
    )
    # Reemplazar rough_score con geo enriquecido:
    rough = 0.5 * geo_enriched + 0.5 * niche
else:
    # Mantener rough original si no hay datos de geo
    pass
```

**Recomendación:** Implementar como H29 — fix trivial con alto impacto.

---

### 20.4 Brecha 4: Tier Enforcement (5K-50K) No Aplicado en Pre-Filter

**Archivo:** `apps/api/app/workers/worker.py:_prefilter_profiles` línea 952

**Severidad:** 🟢 BAJA | **Esfuerzo:** 15min | **Costo:** $0

**Problema actual:** `TIER_MIN_FOLLOWERS=5_000` y `TIER_MAX_FOLLOWERS=50_000` están definidos en `constants.py` pero NO se aplican en el prefilter. El prefilter solo usa `niche_benchmarks.min_followers`, que puede ser diferente.

```python
# ACTUAL — worker.py línea 952:
if followers > 0:
    if followers < min_followers:  # ← min_followers del brief, NO TIER_MIN
        bot_flags[handle] = bot_flags.get(handle, 0) + 1
```

**Impacto:**
- Perfiles de 1K-5K (bots micro-cuentas) compiten con el sweet spot de 5K-50K
- Perfiles de 500K+ (mega-influencers) también compiten
- El re-ranking `_rerank_diversified` SÍ aplica `TIER_DISTRIBUTION` pero DESPUÉS del prefilter — ya se invirtieron calls en perfiles fuera de tier

**Código ideal:**
```python
# En _prefilter_profiles, después del bot check:
if followers > 0:
    # Skip si fuera de tier
    if followers < TIER_MIN_FOLLOWERS or followers > TIER_MAX_FOLLOWERS:
        bot_flags[handle] = bot_flags.get(handle, 0) + 10  # Effectively skip
```

**Recomendación:** Implementar como H29 junto con Brecha 3 y 6 — 3 fixes triviales en 1 commit.

---

### 20.5 Brecha 5: Sin Cross-Reference Boost entre Steps

**Archivo:** `apps/api/app/workers/worker.py` (líneas 707-907, merge de steps)

**Severidad:** 🟡 MEDIA | **Esfuerzo:** 1h | **Costo:** $0

**Problema actual:** Steps 1-4 corren en paralelo, luego se mergean en `profiles` dict (línea 909). Si un perfil aparece en Step 1 (hashtag) Y Step 2 (keyword), el primero gana — no se weighta el cross-reference.

```python
# ACTUAL — worker.py línea 909:
for item in hashtag_items:
    handle = item.get("username")
    if handle in profiles: continue  # Skip si ya existe
    profiles[handle] = {...}  # Primer paso gana
```

**Impacto:** Un creador que aparece en #perros Y en "veterinaria" es probablemente más relevante que uno que solo aparece en #perros. No se bonusifica esto.

**Análisis:**
- Step 1: Hashtag top → handles populares del nicho
- Step 1_recent: Hashtag recent → handles frescos del nicho
- Step 2: Keyword → handles con keywords en bio/perfil
- Step 2.5: Reels serp → handles haciendo Reels del tema
- Step 3: Top search → handles top por búsqueda
- Step 4: Suggested → handles sugeridos por similitud

**Código ideal:**
```python
# En el merge, tracking de sources:
profiles[handle] = {
    ...
    "_source_count": 1,
    "_sources": ["hashtag_top"]  # Lista de sources
}

# Si aparece en otro step:
if handle in profiles:
    profiles[handle]["_source_count"] += 1
    profiles[handle]["_sources"].append("keyword")

# En prefilter scoring:
source_count = profiles[handle].get("_source_count", 1)
if source_count >= 4: rough *= 1.5   # Appears in 4+ sources
elif source_count >= 3: rough *= 1.3 # Appears in 3 sources
elif source_count >= 2: rough *= 1.15 # Appears in 2 sources
```

**Recomendación:** Implementar como H32 post-asesoría. Medium esfuerzo, $0 costo.

---

### 20.6 Brecha 6: Sin Verified Boost

**Archivo:** `apps/api/app/workers/worker.py:_prefilter_profiles`

**Severidad:** 🟢 BAJA | **Esfuerzo:** 15min | **Costo:** $0

**Problema actual:** `is_verified` se extrae del profile (línea 730) pero NO se usa en el scoring.

```python
# ACTUAL — worker.py línea 730:
"is_verified": item.get("is_verified", False),
# ... pero después no se usa en prefilter:
rough = 0.5 * geo + 0.5 * niche  # is_verified no aparece
```

**Impacto:** Un influencer verificado con 30K followers debería rankear más alto que uno no verificado con 30K. El badge azul indica cuenta validada = menos riesgo.

**Código ideal:**
```python
# En prefilter scoring, después de geo + niche:
if is_verified:
    rough *= 1.15  # 15% boost para cuentas verificadas
```

**Recomendación:** Implementar como H29 junto con Brechas 3 y 4 — 3 fixes triviales en 1 commit.

---

### 20.7 Breacha 7: Sin Time-Decay (Cuentas Activas vs Muertas)

**Archivo:** `apps/api/app/workers/worker.py` (post-enrichment)

**Severidad:** 🟡 MEDIA | **Esfuerzo:** 1h | **Costo:** $0

**Problema actual:** El pipeline NO consulta cuándo fue el último post. Una cuenta con 30K followers y último post hace 8 meses rankea igual que una activa ayer.

**El endpoint `/v1/user/by/username` retorna `latest_posts` con `taken_at`:**
```python
latest_posts = [
    {"taken_at": 1724123400, "likes": 523, "comments": 42, "caption": "..."},
    {"taken_at": 1724037000, "likes": 498, "comments": 38, "caption": "..."},
    ...
]
```

**Impacto:** Recomendamos cuentas "muertas" que no van a generar engagement. Un influencer inactivo por 90+ días es mal negocio.

**Código ideal:**
```python
# Post-enrichment:
latest_post_ts = profile.get("latest_posts", [{}])[0].get("taken_at") if profile.get("latest_posts") else None

if latest_post_ts:
    days_since = (now - datetime.fromtimestamp(latest_post_ts)).days

    if days_since > 90:
        rough *= 0.5      # Account dormant > 3 months
    elif days_since > 30:
        rough *= 0.85     # Account inactive > 1 month
    elif days_since <= 7:
        rough *= 1.1      # Active in last week
```

**Recomendación:** Implementar como H33 post-asesoría.

---

### 20.8 Brecha 8: Bot Detection Avanzada

**Archivo:** `apps/api/app/workers/worker.py:_prefilter_profiles` línea 947-983

**Severidad:** 🟡 MEDIA | **Esfuerzo:** 2h | **Costo:** $0

**Problema actual:** El bot detection básico solo cubre `ff_ratio`. Faltan señales importantes: engagement rate, ratio followers/avg_likes, posts count.

```python
# ACTUAL — worker.py líneas 952-963 (básico):
if followers > 0:
    if followers < min_followers: bot_flag += 1
    if ff_ratio > 10 and followers < 5000: bot_flag += 2
    if ff_ratio > 20: bot_flag += 3
    if posts_count < 10 and followers > 5000: bot_flag += 1
```

**Señales proxy disponibles post-enrichment:**
1. `engagement_rate` = (avg_likes + avg_comments) / followers
2. `followers / avg_likes` ratio (alto = probable bot)
3. `posts_count` / account_age ratio
4. `is_business` (menos probable bots)

**Código ideal:**
```python
# Bot score compuesto (0-1):
def bot_score(profile) -> float:
    score = 0.0
    followers = profile.get("follower_count", 0)
    avg_likes = profile.get("avg_likes", 0)
    avg_comments = profile.get("avg_comments", 0)
    ff_ratio = profile.get("ff_ratio", 0)
    posts_count = profile.get("posts_count", 0)

    if followers > 0:
        er = (avg_likes + avg_comments) / followers
        if er < 0.005 and followers > 5000:
            score += 0.4  # Muy bajo engagement rate
        if followers / max(avg_likes, 1) > 500:
            score += 0.2  # followers/avg_likes muy alto
    if ff_ratio > 10: score += 0.2
    if ff_ratio > 20: score += 0.1
    if posts_count < 10 and followers > 5000: score += 0.1
    return score

# Skip si bot_score > 0.6:
if bot_score(profile) > 0.6:
    continue  # Skip this handle
```

**Recomendación:** Implementar como H35 post-asesoría. 2h de desarrollo, $0 costo.

---

### 20.9 Roadmap de Fixes para Opus 5

| Hito | Brechas | Esfuerzo Total | Costo Extra |
|------|---------|----------------|-------------|
| **H29** | Brecha 3 (geo post-enrich) + Brecha 4 (tier) + Brecha 6 (verified) | 1h | $0 |
| **H31** | Brecha 1 (engagement quality) | 1h | +$0.10-0.20 |
| **H32** | Brecha 2 (niche captions) + Brecha 5 (cross-ref) | 1.5h | +$0.05 |
| **H33** | Brecha 7 (time-decay) | 1h | $0 |
| **H35** | Brecha 8 (bot detection avanzada) | 2h | $0 |
| **TOTAL** | **8 brechas** | **~6.5h** | **+$0.15-0.25** |

**Nota:** H30 y H34 reservados para otros items.

---

### 20.10 Request Explícito para Opus 5

> Opus 5: Analiza las 8 brechas arriba. Para cada una, proporciona:
> 1. Confirmación del fix propuesto o alternativa mejor
> 2. Código exacto del patch para `worker.py` y `candidate_analyzer.py`
> 3. Orden de aplicación recomendada (H29 primero, etc.)
> 4. Cualquier conflicto con Hito 28 Fix B que deba resolverse

---

### 20.11 Fixes Inmediatos (H29 — 15 min, $0)

Estos 3 fixes son triviales y pueden aplicarse en un solo commit:

```python
# worker.py — prefilter_profiles, después de geo + niche:
# 1. Tier enforcement:
if followers < TIER_MIN_FOLLOWERS or followers > TIER_MAX_FOLLOWERS:
    bot_flags[handle] = 10

# 2. Verified boost:
if is_verified:
    rough *= 1.15

# 3. Geo post-enrichment (después de enrichment):
# (enrichment return, recalcular geo con country/city si disponible)
```

---

## 21. Hito 29 — Hotfix Extra='forbid' Solo en Frontera de Entrada

> **Fecha:** 2026-08-21
> **Auditoría:** #15 — Hito 29 Hotfix
> **Detectado por:** Opus 5
> **Severidad:** 🔴 CRÍTICA — TODOS LOS RUNS MORÍAN ANTES DE GASTAR $0

### 21.1 Qué Pasó

Opus 5 recomendó `extra="forbid"` en los schemas para cerrar la clase de bugs de "campo que se pierde en silencio". El equipo lo aplicó correctamente en el Hito 28 — a los dos schemas. Ahí está el problema: no se distinguish que esos dos schemas hacen cosas distintas.

```
discovery.py  →  DiscoverySearchRequest(...)         ← entrada de API
memory.py:222 →  brief_parsed = brief.model_dump()   ← incluye max_candidates
                          ↓ se guarda en Postgres
worker.py:324 →  BriefStructured(**brief_parsed)     ← extra="forbid"
                  ValidationError: max_candidates no permitido
```

`DiscoverySearchRequest` tiene `max_candidates`. `BriefStructured` **no lo tenía**. Con `forbid`, el worker revienta al deserializar, **antes de la primera llamada HTTP**.

### 21.2 Alcance

`launch_discovery_run` se invoca desde **tres endpoints** (`discovery.py:315, 511, 567`) y su firma recibe `DiscoverySearchRequest`. Los tres caminos —Explorar, Analizar y el chat— guardan el mismo dump.

**Todos los runs fallan.** El producto estaba caído hasta aplicar el fix. Costo real: $0 (falla antes de gastar), pero la demo habría sido un fracaso.

### 21.3 La Regla Correcta

> **`forbid` va en la FRONTERA DE ENTRADA, `ignore` en la deserialización de datos persistidos.**

En la API, `forbid` atrapa typos del cliente y ahí gana. En un schema que lee JSON guardado, `forbid` convierte cualquier evolución del schema en una rotura de todas las filas históricas — y hay 48 runs guardados con campos que ya cambiaron.

### 21.4 El Fix

**Archivo:** `packages/discovery/discovery/schemas.py`

**BriefStructured (lee JSON persistido):**
```python
model_config = ConfigDict(extra="ignore")  # Antes: extra="forbid"
max_candidates: int = Field(default=20, ge=1, le=100)  # Nuevo campo
```

**DiscoverySearchRequest (frontera de entrada — SIN CAMBIOS):**
```python
model_config = ConfigDict(extra="forbid")  # Correcto, permanece así
```

### 21.5 Tests Anti-Regresión

Archivo: `apps/api/tests/test_hito29_e2e_regression.py`

| Test | Descripción |
|------|-------------|
| `test_full_round_trip_discovery_request_to_brief_structured` | DiscoverySearchRequest → model_dump() → BriefStructured debe funcionar |
| `test_briefstructured_ignores_extra_fields_from_persistence` | Campos unknown se ignoran (no fallan) |
| `test_briefstructured_max_candidates_default_20` | Default de max_candidates es 20 |
| `test_briefstructured_max_candidates_respected_when_provided` | max_candidates se respeta si está en JSON |
| `test_discovery_search_request_still_forbids_extra_fields` | DiscoverySearchRequest SÍ rechaza typos |
| `test_historical_run_sample_1` | Backward compat con runs históricos |
| `test_historical_run_sample_2_with_old_fields` | Campos antiguos se ignoran |

### 21.6 Verificación

```bash
psql $DATABASE_URL -c "SELECT brief_parsed ? 'max_candidates' FROM discovery_runs ORDER BY created_at DESC LIMIT 1;"
# Debe devolver 't' — confirma que el bug estaba en los datos guardados
```

### 21.7 Lección

Nueve auditorías, nueve bugs, todos de la misma familia — cosas que fallan sin avisar. El de hoy lo introdujo Opus 5 dando una regla a medias. Eso confirma el diagnóstico: **el problema no es la falta de cuidado, es que el sistema no avisa cuando algo va mal.**

Por eso el paso que más rinde no es corregir bugs más rápido, sino el **test end-to-end que los haga visibles**. Con `extra='forbid'` bien puesto y un test que ejecute Explorar → Analizar de punta a punta, esta regresión habría durado treinta segundos en vez de llegar al día de la demo.

---

*Documento generado: 2026-08-21 — Arquitectura LENS v5.5 (Hito 29 hotfix aplicado). HikerAPI balance: $43.00 USD. Regresión de extra='forbid' corregida: forbid en frontera de entrada, ignore en persistencia. 8 brechas para Opus 5 — postergadas post-validación.*
