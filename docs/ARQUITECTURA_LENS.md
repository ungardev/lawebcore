# La Web Core — Arquitectura Técnica (versión 3.1 post-segunda-auditoría LENS)

> **Versión:** 3.1 — 2026-08-14
> **Reemplaza a:** `docs/ARQUITECTURA_LENS.md` v3.0 (`27ed99f`)
> **Commit de referencia:** `cc3f57c` (Hitos 8-12 aplicados: en_id, 402, breaker, apify, target_country, replay)
> **Auditoría segunda-pass:** `LENS_AUDIT2_2026-08-14.md`

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

⚠️ **RLS no protege el camino de datos actual:** la aplicación se conecta con la credencial propietaria de la base, y RLS no se aplica al propietario salvo `FORCE ROW LEVEL SECURITY`. **Multi-tenancy real: no implementado.**

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

La numeración "STEP N" en comentarios/logs del worker es **distinta** de la numeración de funciones `_fetch_stepN()`. Esta tabla usa funciones para evitar ambigüedad.

| Fase | Función en código | Fuente HikerAPI | Estado por defecto | Datos que devuelve |
|---|---|---|---|---|
| Ubicación | `search_location` + `location_medias_*` | `/v1/fbsearch/places`, `/v1/location/medias/*` | **Desactivado** (`HIKERAPI_STEP0_LOCATION=false`) | Usuario reducido |
| Hashtag top | `_fetch_step1` | `/v2/hashtag/medias/top` | Activo — 3 hashtags | ⚠️ Usuario **reducido**: sin bio ni seguidores |
| Hashtag recientes | `_fetch_step1_recent` | `/v2/hashtag/medias/recent` | Activo — 2 hashtags (TTL 30 min) | ⚠️ Usuario **reducido** |
| Keyword | `_fetch_step2` | `/v2/fbsearch/accounts` | Activo — 3 keywords × (1 + 2 sufijos geo) | Perfil **completo** |
| Reels | `_fetch_step2p5` | reels serp | Activo — 1 keyword | Usuario reducido |
| Top search | `_fetch_step3` | `/gql/topsearch` | Activo — 1 keyword | Perfil **completo** |
| Sugeridos | `_fetch_step4` | `/v2/user/suggested/profiles` | Activo — 1 semilla | Perfil completo |
| **Enrichment** | `enrich_profile` por handle | `/v1/user/by/username` | **Activo — mayor costo**, hasta `MAX_CALLS_PER_RUN` | Perfil completo + posts |
| Fraude (opcional) | `get_user_about` | `/v1/user/about` | **Desactivado** (`HIKERAPI_INCLUDE_ABOUT=false`) | país, antigüedad, alias previos |
| Scoring | `lens_score` + `geo_score` + `niche_relevance` | — | Activo | costo $0 |
| Análisis IA | `candidate_analyzer` | DeepSeek | Según `analyze_with_ai` del brief | content/audience/brand_fit |

⚠️ **Problema de diseño no resuelto:** las fuentes marcadas "usuario reducido" devuelven objetos **sin biografía ni número de seguidores**. El prefiltro que decide a quién enriquecer puntúa con `0.5·geo + 0.5·niche`, y ambas señales se leen de la biografía. Para perfiles llegados por hashtag o reels el cálculo tiende a cero — la selección de handles a enriquecer queda determinada por empates.

---

## 4. APIs y servicios

### 4.1 HikerAPI (proveedor primario)

```
Costo: ~$0.0006 USD por request
Docs:  https://api.hikerapi.com/docs
Panel: https://hikerapi.com/billing
```

| Método | Endpoint | Notas |
|---|---|---|
| `search_hashtag()` | `/v2/hashtag/medias/top` | usuario reducido, TTL 12 h |
| `search_hashtag_recent()` | `/v2/hashtag/medias/recent` | TTL 30 min (fix hito 6) |
| `search_keyword()` | `/v2/fbsearch/accounts` | perfil completo |
| `search_top_accounts()` | `/gql/topsearch` | perfil completo, TTL 12 h |
| `enrich_profile()` | `/v1/user/by/username` | ★ principal costo |
| `get_user_about()` | `/v1/user/about?id=` | sin `safe_int` |
| `suggested_profiles()` | `/v2/user/suggested/profiles` | |
| `search_location()` | `/v1/fbsearch/places?query=` | |
| `location_medias_top/recent()` | `/v1/location/medias/*` | param `location_pk` |

**Modelo de excepciones (hito 2):**

`hikerapi_client._get()` lanza excepciones que **propagan** hasta el top-level del worker, abortando el run:

| Condición | Excepción | Efecto en run |
|---|---|---|
| 401 / 403 | `SourceUnavailable` | `status=failed`, mensaje accionable |
| 402 (credits exhausted) | `SourceUnavailable` | `status=failed`, mensaje con link billing |
| 429 (rate limited) | `SourceUnavailable` | `status=failed`, mensaje accionable |
| 5xx | `TransientSourceError` | counted by circuit breaker → `SourceUnavailable` after 5 consecutive |
| timeout | `TransientSourceError` | counted by circuit breaker → `SourceUnavailable` after 5 consecutive |

**Circuit breaker (hitos 3+4):** `HikerAPICircuitBreaker` en `packages/discovery/discovery/tools/hikerapi_circuit_breaker.py`. Estado CLOSED→OPEN→HALF_OPEN. Umbral: 5 errores 5xx/timeout. TTL: 300 s. Redis-backed.

### 4.2 Apify — ELIMINADO (hito 1)

`INSTAGRAM_SOURCE` ya solo acepta el valor `hikerapi`. Los archivos `apify_instagram_source.py` y `source_registry.py` fueron eliminados en `be32a39`. No hay fallback a Apify.

### 4.3 DeepSeek-V3
Parsing de brief, generación de `DiscoveryProfile`, análisis de candidatos. `deepseek-chat`, caché de prompt habilitada. ~$0.001 USD/1K tokens.

---

## 5. Modelo de datos — Discovery

```
discovery_runs
├── id (UUID)
├── brief_text            — brief original en texto
├── brief_parsed (JSONB)  — BriefStructured serializado
├── status               — pending | running | completed | partial | failed
│                         ⚠️ 'partial' requiere migración 00000000000104
├── total_candidates
├── actual_cost_usd
├── metadata (JSONB)      — current_step, completed_steps, contadores
├── title
├── error
├── started_at, completed_at, created_at
└── business_unit_id (FK)

discovery_candidates       — UNIQUE(run_id, platform, handle)
├── id, run_id (FK)
├── handle, full_name, bio, avatar_url, url
├── platform, country, city
├── followers, following, posts_count
├── engagement_rate, avg_likes, avg_comments
├── match_score           — 0-100 (lens_score)
├── niche_relevance, geo_relevance
├── content_quality, audience_relevance, audience_quality
├── brand_fit             — DeepSeek (si analyze_with_ai)
├── ai_rationale          — resumen DeepSeek
├── rationale             — texto generado por reglas
├── tier, is_tienda, status
├── raw_payload (JSONB)   — lens_score, geo_score, cross_referenced,
│                           fraud_signals, engagement_analytics
└── fetched_at

discovery_conversations
├── id, discovery_run_id (FK, nullable)
├── current_step, accumulated_brief, parsed_brief_json
├── pending_refinements, message_count, title
└── state (JSONB)         — ⚠️ existe pero el orchestrator NO la usa:
                            el estado sigue en memoria y se pierde al reiniciar

discovery_messages         — tabla propia (NO un JSON dentro de conversations)
├── id, conversation_id (FK)
├── role, content
├── tool_calls (JSONB), tool_results (JSONB)
└── reasoning, cost_usd, latency_ms

discovery_profiles         — vocabulario por vertical, generado por LLM
├── id, fingerprint (UNIQUE)
├── vertical_slug, languages (JSONB), countries (JSONB)
├── hashtags, keywords, niche_keywords (JSONB)
├── geo_indicators, buy_intent_keywords (JSONB)
├── elite_data (JSONB)    — 9 subcampos de contexto de campaña
├── source                — seed | llm | manual | fallback
├── quality_score, times_used
└── created_at, updated_at

api_costs
└── provider, operation, entity_id, cost_usd, tokens_in/out, occurred_at
```

---

## 6. Variables de entorno

```bash
# Datos
DATABASE_URL=postgresql+asyncpg://...@postgres.railway.internal:5432/railway
ARQ_REDIS_URL=redis://...

# APIs
HIKERAPI_API_KEY=***
DEEPSEEK_API_KEY=sk-***

# LENS Budget & Cost Controls (hitos 3+4)
MONTHLY_BUDGET_USD=10.0          # corte mensual hard
MAX_CALLS_PER_RUN=120             # tope por run
BUDGET_ALERT_THRESHOLD=0.7        # warn al 70%
HIKERAPI_COST_PER_CALL_USD=0.0006
HIKERAPI_5XX_BREAKER_THRESHOLD=5  # consecutive 5xx → open
HIKERAPI_5XX_BREAKER_TTL_S=300    # segundos en estado open

# Control de feature flags
HIKERAPI_STEP0_LOCATION=false     # búsqueda por ubicación
HIKERAPI_INCLUDE_ABOUT=false     # llamada de fraude/país
ENABLE_AI_ANALYZER=false          # análisis DeepSeek global

API_ENV=production
ADMIN_TOKEN=***
```

---

## 7. Costos del pipeline

### Configuración vigente (defaults)

| Fase | Llamadas aprox. | Costo aprox. |
|---|---|---|
| Hashtag top (3) | ~6 | $0.004 |
| Hashtag recientes (2) | ~4 | $0.002 |
| Keyword (3 × 3 variantes) | ~9 | $0.005 |
| Reels (1) | ~1 | $0.001 |
| Top search (1) | ~2 | $0.001 |
| Sugeridos (1) | ~1 | $0.001 |
| **Enrichment** | **hasta 120** | **hasta $0.072** |
| **Total por run** | **~74-120** | **~$0.045-$0.085** |

### Controles de presupuesto implementados (hitos 3+4)

`BudgetFuse` (`apps/api/app/core/budget_fuse.py`) enforce:
1. **`MONTHLY_BUDGET_USD=10.0`** — acumulado mensual en Redis, corte al 100%
2. **`MAX_CALLS_PER_RUN=120`** — por-run call counter en Redis
3. **`BUDGET_ALERT_THRESHOLD=0.7`** — log warning al 70%, alert enviado solo una vez por mes
4. **`_job_id=f"discovery:{run_id}"`** en ARQ (hito 5, corregido en hito 8) — idempotencia, previene doble cobro por redeploy/restart

### Configuraciones desactivadas (referencia)

| Opción | Llamadas extra | Costo extra |
|---|---|---|
| `HIKERAPI_STEP0_LOCATION=true` | +42 | +$0.025 |
| `HIKERAPI_INCLUDE_ABOUT=true` | +50 | +$0.030 |

---

## 8. Módulos nuevos (ciclo LENS 2026-08-14)

| Módulo | Ubicación | Responsabilidad |
|---|---|---|
| `exceptions.py` | `packages/discovery/discovery/exceptions.py` | `SourceUnavailable`, `TransientSourceError`, `BudgetExhausted` |
| `hikerapi_circuit_breaker.py` | `packages/discovery/discovery/tools/` | State machine CLOSED→OPEN→HALF_OPEN, Redis-backed |
| `hikerapi_circuit_breaker.py` | `apps/api/app/core/` | Copia para uso desde worker |
| `budget_fuse.py` | `apps/api/app/core/` | Budget tracking y enforcement Redis |
| `worker_enqueuer.py` | `apps/api/app/core/` | `enqueue_job` con `_job_id=discovery:{run_id}` |
| `00000000000104_...sql` | `supabase/migrations/` | Añade valor `partial` al enum `discovery_run_status` |

---

## 9. Issues conocidos

### Resueltos (hitos aplicados)

| Hito | Bug/Issue | Fix |
|---|---|---|
| 1 (`be32a39`) | `ApifyInstagramSource` + `source_registry.py` | Eliminados — `INSTAGRAM_SOURCE` solo acepta `hikerapi` |
| 1 (`be32a39`) | `_fetch_step2p6` roto | Eliminado — function + llamada de enrich |
| 1 (`be32a39`) | Prefiltro muerto con log engañoso | Eliminado — 30 líneas de prefilter + logs asociados |
| 1 (`be32a39`) | `step2p6_follower_expansion` en metadata | Eliminado de todos los `completed_steps` |
| 2 (`835bf2a`) | Errores 4xx/5xx capturados como `warning` | `SourceUnavailable`/`TransientSourceError` propagan al top-level |
| 2 (`835bf2a`) | 402 = "0 candidatos" indistinguible | `SourceUnavailable` → `status=failed` + mensaje accionable |
| 3+4 (`4819857`) | Sin fusible de presupuesto | `BudgetFuse.assert_budget_available()` al inicio del run |
| 3+4 (`4819857`) | 5xx causing cascade sin corte | `HikerAPICircuitBreaker` — 5 consecutive → OPEN |
| 3+4 (`4819857`) | Sin límite por-run | `BudgetFuse` per-run counter + `MAX_CALLS_PER_RUN=120` |
| 5 (`766cfee`) | Doble cobro por redeploy/restart | `_job_id=f"discovery:{run_id}"` en ARQ `enqueue_job` (bugfix `27ed99f`) |
| 6 (`2da78ab`) | `is_private` perdido en merge de enrichment | Añadido al bloque `update()` en worker.py |
| 6 (`2da78ab`) | `search_hashtag_recent` sin caché | `cache_ttl=0` → `cache_ttl=1800` (30 min) |
| 7 (`9b43316`) | Documentación desactualizada | Reemplazado por esta versión |

### Abiertos

| Issue | Prioridad | Detalle |
|---|---|---|
| Enriquecimiento sobre muestra casi aleatoria | **Alta** | §3 — decide gasto sin datos; afecta calidad de candidatos |
| Vocabulario de negocio hardcodeado | **Media** | worker.py tiene ~150 líneas de listas en español; ata el pipeline a mascotas-Venezuela |
| Estado del orchestrator en memoria | **Media** | columna `state` existe y no se usa; se pierde al reiniciar |
| Multi-tenancy inexistente | **Media** | bloquea un segundo cliente en la misma instancia |
| Scoring / geo_score con bugs | **Media** | Tests muestran fallos en city matching y country disqualification |
| `discovery_run_status` enum sin `partial` | **Baja** | Migración `00000000000104` creada pero debe ejecutarse manualmente |

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

`restartPolicyMaxRetries=3` ahora es seguro gracias a `_job_id` (hito 5, fix hito 8).

---

## 11. Recursos

| Recurso | URL |
|---|---|
| API Docs | `https://lawebcore-production.up.railway.app/api/docs` |
| HikerAPI billing | `https://hikerapi.com/billing` |
| Railway | `https://railway.app/project/lawebcore` |
| Vercel | `https://vercel.com/lawebcore` |

---

*Documento derivado de la auditoría LENS (`LENS_REVIEW_ARQUITECTURA_2026-08-14.md`) con los 7 hitos de fix aplicados. Para detalle completo de la auditoría original, ver `LENS_REVIEW_ARQUITECTURA_2026-08-14.md`.*
