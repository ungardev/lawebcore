# La Web Core — Arquitectura Técnica LENS Discovery (versión 3.8)

> **Versión:** 3.8 — 2026-08-19
> **Reemplaza a:** `docs/ARQUITECTURA_LENS.md` v3.7 (`da9cf5e`)
> **Commit de referencia:** `hito23` (Hitos 1-23 aplicados)
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Auditorías previas:** `LENS_REVIEW_ARQUITECTURA_2026-08-14.md` (original), `LENS_AUDIT2_2026-08-14.md` (segunda), `LENS_AUDIT3_2026-08-14.md` (tercera), auditoría 5 (2026-08-17), auditoría 6 (2026-08-17), auditoría 7 (2026-08-18 post-Hito-22 + Opus 5), `LENS_AUDIT8_2026-08-19.md` (Opus 5 Hito 23)

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

## ⚠️ ALERTA DE COSTO — HikerAPI Balance Agotado

```
╔══════════════════════════════════════════════════════════════════════╗
║  HIKERAPI BALANCE: $0.00 USD — AGOTADO                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Costo por run confirmado:  $1.50 - $3.00 USD                    ║
║  Runs posibles con $10:      ~5-6 runs completos                 ║
║  Runs posibles con $20:      ~10-13 runs completos                ║
║  Runs posibles con $50:      ~25-33 runs completos               ║
╠══════════════════════════════════════════════════════════════════════╣
║  RECOMENDACIÓN:                                                    ║
║  • Reducir MAX_HANDLES_TO_ENRICH de 50 a 20 → ahorra 60%       ║
║  • Con $10 y 20 handles: ~15 runs/mes                          ║
║  • Negociar plan bulk con HikerAPI para descuentos               ║
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
| Bonus | `880da7d` | ReplayMiss invisible | Contador en metadata |

### 9.2 Abiertos (Post-Hito 23)

| Issue | Prioridad | Detalle | Estado |
|-------|-----------|---------|--------|
| HIKERAPI_COST_PER_CALL_USD legacy | ✅ RESUELTO | Cost ahora $0.02 real en config | — |
| **Worker con código viejo (pre-Hito 21)** | ✅ **RESUELTO** | Hito 22 — redeploy verificado con logs | — |
| **actual_cost_usd no se persiste** | ✅ **RESUELTO** | Hito 22 — $1.64 grabado correctamente | — |
| **`lens:budget:run:{id}` no se crea** | ✅ **RESUELTO** | Hito 22 — key creada con 82 calls | — |
| discovery_runs.metadata sin `partial` enum | ✅ **RESUELTO** | Hito 22 — enum actualizado | — |
| **`except Exception` silencia SourceUnavailable** | 🔴 **RESUELTO HITO 23** | 402 → degraded; ahora `raise` antes de `except Exception` | — |
| **Sin pre-flight de saldo (runs condenados)** | 🔴 **RESUELTO HITO 23** | `get_balance()` antes de discovery; aborta si insuficiente | — |
| **`exclude_stores` filtra 100% handles VE** | ❌ **REFUTADO** | Opus 5 probó que la causa fue enrichment 402, no tiendas | — |
| Mensaje engañoso al usuario | ✅ **RESUELTO HITO 23** | `_build_zero_candidates_message` naming counter real | — |
| MAX_HANDLES_TO_ENRICH 50→25 | ✅ **RESUELTO HITO 23** | Enrichment cost $1.00→~$0.50 | — |
| **`accepted` nunca se actualiza** | 🔴 **CRÍTICA** | `discovery_runs.accepted` siempre 0 | **PENDIENTE** |
| Geolocalización sin validación post-enrichment | ⚠️ **MEDIA** | POSTERGADO — no hay candidatos aún para validar | **PENDIENTE** |
| Enriquecimiento sobre muestra casi aleatoria | **Alta** | Prefiltro decide sin bio; afecta calidad | **PENDIENTE** |
| geo_no_signal filter rechaza hashtag profiles | ⚠️ **MEDIA** | Perfiles de hashtag sin bio → geo_score=0.0 → filtrados | **PENDIENTE** |
| Filtrado business_unit_id en endpoints discovery | **Media** | Hito 17 arregló campaigns; discovery aún no filtra | **PENDIENTE** |
| discovery_profiles sin 3 columnas nuevas | **Media** | Migration 105 creada, debe ejecutarse | **PENDIENTE** |
| HikerAPI balance agotado | 🔴 **BLOQUEANTE** | $0 remaining — necesita recarga para tests | **NUEVO** |

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

## 14. Recursos

| Recurso | URL |
|---------|-----|
| Repositorio | https://github.com/ungardev/lawebcore |
| API Docs | `https://lawebcore-production.up.railway.app/api/docs` |
| HikerAPI billing | `https://hikerapi.com/billing` |
| HikerAPI docs | `https://api.hikerapi.com/docs` |
| Railway | `https://railway.app/project/lawebcore` |
| Vercel | `https://vercel.com/lawebcore` |

---

*Documento generado: 2026-08-19 — Arquitectura LENS v3.8 (23 hitos aplicados + Opus 5 audit7 refutations). Hito 23 aplicado: pre-flight balance, except SourceUnavailable raise, _build_zero_candidates_message, MAX_ENRICH 50→25. Bug N1 refutado por Opus 5 — causa real era enrichment 402. Test runs 0c44ea23 + 1a1d6128 condenado sin pre-flight ($3.26 desperdiciado). Auditorías completas en `LENS_REVIEW_ARQUITECTURA_2026-08-14.md`, `LENS_AUDIT2_2026-08-14.md`, `LENS_AUDIT3_2026-08-14.md`, auditoría 5-7, `LENS_AUDIT7_2026-08-18.md`, `LENS_AUDIT8_2026-08-19.md`.*
