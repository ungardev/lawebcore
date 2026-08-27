# La Web Core — Arquitectura Técnica (versión corregida)

> **Versión:** 2.0 — 2026-08-14
> **Reemplaza a:** `docs/ARQUITECTURA_LENS.md` v1.0 (2026-08-13)
> **Commit de referencia:** `a250b0c`
> **Correcciones marcadas con** ⚠️ **respecto a la v1.0**

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
⚠️ **Corrección v1.0:** la v1.0 afirmaba "PostgreSQL 16 via Supabase Cloud" en §1 y "postgres.railway.internal" en §4.4. Son afirmaciones incompatibles.

- **Motor real en producción:** PostgreSQL en **Railway** (`postgres.railway.internal:5432/railway`), accedido con asyncpg desde `railway_pg`
- **Supabase:** legado. Las migraciones viven en `supabase/migrations/` por historia del proyecto, pero el camino de datos de discovery no pasa por Supabase
- **Extensiones:** `uuid-ossp`, `pgcrypto`, `pg_trgm`, `vector` (pgvector)

⚠️ **Corrección importante sobre RLS:** la v1.0 afirmaba "Row-level security por `business_unit_id`, `client_id`, `team_id`". Las políticas existen en las migraciones, pero **no protegen el camino de datos actual**: la aplicación se conecta con la credencial propietaria de la base, y RLS no se aplica al propietario salvo `FORCE ROW LEVEL SECURITY` (y aun así el service role la evade).

**Estado real de multi-tenancy: no implementado.** El aislamiento entre inquilinos tendría que hacerse por filtrado explícito en las queries de la aplicación o con un rol de base distinto del propietario. Debe resolverse antes de incorporar un segundo cliente en la misma instancia.

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
│                   encola vía ARQ                         │
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
┌─────────────┐
│    Redis    │  cola ARQ + caché de respuestas
└─────────────┘
```

---

## 3. Pipeline de descubrimiento

⚠️ **Corrección v1.0:** la numeración de steps de la v1.0 no coincide con el código. En `worker.py`, `_fetch_step3()` es **top search** y `_fetch_step4()` es **suggested profiles**, mientras que los comentarios y logs del mismo archivo llaman "STEP 3" al enrichment y "STEP 4" al scoring. Hay dos significados simultáneos para los mismos números.

Esta tabla describe el pipeline **por función**, que es como se recomienda renombrarlo en el código:

| Fase | Función en código | Fuente HikerAPI | Estado por defecto | Datos que devuelve |
|---|---|---|---|---|
| Ubicación | `search_location` + `location_medias_*` | `/v1/fbsearch/places`, `/v1/location/medias/*` | **Desactivado** (`HIKERAPI_STEP0_LOCATION=false`) | Usuario reducido |
| Hashtag top | `_fetch_step1` | `/v2/hashtag/medias/top` | Activo — 3 hashtags | ⚠️ Usuario **reducido**: sin bio ni seguidores |
| Hashtag recientes | `_fetch_step1_recent` | `/v2/hashtag/medias/recent` | Activo — 2 hashtags | ⚠️ Usuario **reducido** |
| Keyword | `_fetch_step2` | `/v2/fbsearch/accounts` | Activo — 3 keywords × (1 + 2 sufijos geo) | Perfil **completo** |
| Reels | `_fetch_step2p5` | reels serp | Activo — 1 keyword | Usuario reducido |
| Expansión de seguidores | `_fetch_step2p6` | `search_followers_of` | ⚠️ **Roto**: gasta 1 `enrich_profile` y devuelve siempre vacío | — |
| Top search | `_fetch_step3` | `/v3/fbsearch/topsearch` | Activo — 1 keyword | Perfil **completo** |
| Sugeridos | `_fetch_step4` | `/v2/user/suggested/profiles` | Activo — 1 semilla | Perfil completo |
| **Enrichment** | `enrich_profile` por handle | `/v1/user/by/username` | **Activo — mayor costo**, 50 handles | Perfil completo + posts |
| Fraude (opcional) | `get_user_about` | `/v1/user/about` | **Desactivado** (`HIKERAPI_INCLUDE_ABOUT=false`) | país, antigüedad, alias previos |
| Scoring | `lens_score` + `geo_score` + `niche_relevance` | — | Activo | costo $0 |
| Análisis IA | `candidate_analyzer` | DeepSeek | Según `analyze_with_ai` del brief | content/audience/brand_fit |

⚠️ **Nota crítica de diseño (nueva):** las fuentes marcadas "usuario reducido" devuelven objetos de usuario **sin biografía ni número de seguidores**. El prefiltro que decide a quién enriquecer puntúa con `0.5·geo + 0.5·niche`, y ambas señales se leen de la biografía. Para perfiles llegados por hashtag o reels ese cálculo tiende a cero, así que la selección de los 50 handles a enriquecer queda determinada por empates — es decir, casi al azar.

**Consecuencia:** el sistema decide en qué gastar antes de tener los datos necesarios para decidir. Es la causa estructural del run que encontró 254 perfiles y produjo 0 candidatos. Ver `LENS_REVIEW_ARQUITECTURA_2026-08-14.md` §3.6.

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
| `search_hashtag()` | `/v2/hashtag/medias/top` | usuario reducido |
| `search_hashtag_recent()` | `/v2/hashtag/medias/recent` | ⚠️ `cache_ttl=0` — sin caché |
| `search_keyword()` | `/v2/fbsearch/accounts` | perfil completo |
| `search_top_accounts()` | `/v3/fbsearch/topsearch` | perfil completo |
| `enrich_profile()` | `/v1/user/by/username` | ★ principal costo |
| `get_user_about()` | `/v1/user/about?id=` | sin `safe_int` |
| `suggested_profiles()` | `/v2/user/suggested/profiles` | |
| `search_location()` | `/v1/fbsearch/places?query=` | |
| `location_medias_top/recent()` | `/v1/location/medias/*` | param `location_pk` |

**Parámetros que causan 422:** `safe_int` en `/gql/user/about` y `/v1/location/search`; `id` en lugar de `location_pk` en los endpoints de ubicación.

⚠️ **Manejo de errores — defecto abierto:** los errores de HikerAPI se capturan con `except Exception` y se registran como `warning`, dejando la lista vacía y permitiendo que el run termine "correctamente". Un `402 InsufficientFunds` (saldo agotado) resulta indistinguible de "el hashtag no tiene resultados": el run reporta `completed` con `total_candidates=0`.

**Esto ya ocurrió y costó dos días de diagnóstico.** Corrección pendiente: excepción `SourceUnavailable` para 401/402/403/429 que aborte el run con `status="failed"` y mensaje accionable.

### 4.2 Apify (legado — no operativo)

⚠️ **Corrección v1.0:** la v1.0 lo describe como "fallback deshabilitado", lo que sugiere que basta reactivarlo. **No existe fallback funcional.**

El Protocol `InstagramSource` declara 5 métodos (`search_hashtag`, `search_keyword`, `enrich_profile`, `get_user_about`, `close`), pero el worker invoca 13, incluidos dos métodos privados del cliente concreto (`_normalize_user`, `_extract_user_from_post`) mediante comprobaciones `hasattr()`.

`ApifyInstagramSource` (148 líneas) no implementa ocho de los métodos que el worker necesita. Cambiar `INSTAGRAM_SOURCE=apify` no degrada el sistema: lo rompe. Rehabilitar Apify exige completar antes el contrato.

### 4.3 DeepSeek-V4-Flash
Parsing de brief, generación de `DiscoveryProfile`, análisis de candidatos. `deepseek-v4-flash`, caché de prompt habilitada. ~$0.001 USD/1K tokens.

---

## 5. Modelo de datos — Discovery

⚠️ **Corrección v1.0:** la sección 5 de la v1.0 describía un esquema que no existe (`brief`, `enriched_data`, `ai_analysis`, `messages`, `brief_id`, `profile_data`, `cached_at`). Este es el esquema real.

```
discovery_runs
├── id (UUID)
├── brief_text            — brief original en texto
├── brief_parsed (JSONB)  — BriefStructured serializado
├── status                — pending | running | completed | partial | failed
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

⚠️ **Nota:** `discovery_profiles` existe para que el vocabulario de negocio sea dato y no código. El `worker.py` actual **lo evita** y vuelve a llevar embebidas ~150 líneas de listas en español (términos de tienda, señales de creador, listas negras por país, palabras políticas). Esto revierte la universalización y ata el pipeline al vertical mascotas-Venezuela.

---

## 6. Variables de entorno

```bash
# Datos
DATABASE_URL=postgresql+asyncpg://...@postgres.railway.internal:5432/railway
ARQ_REDIS_URL=redis://...

# APIs
HIKERAPI_API_KEY=***
DEEPSEEK_API_KEY=sk-***
APIFY_API_KEY=***                  # legado, no operativo

# Selección de fuente
INSTAGRAM_SOURCE=hikerapi          # hikerapi | apify (apify NO funcional)

# Control de costos (efectivos)
HIKERAPI_STEP0_LOCATION=false      # búsqueda por ubicación
HIKERAPI_INCLUDE_ABOUT=false       # llamada de fraude/país
ENABLE_AI_ANALYZER=false           # análisis DeepSeek global

API_ENV=production
ADMIN_TOKEN=***
```

⚠️ **Corrección v1.0:** la v1.0 decía que el modo económico "no persiste en deploy, config hardcodeada". Es mixto y ese es el problema: los interruptores de arriba **sí** son de entorno, pero los límites cuantitativos son constantes de módulo o literales en el cuerpo de la función:

```python
MAX_HANDLES_TO_ENRICH = 50      # worker.py
MAX_POSTS_PER_HASHTAG = 20
plan.hashtag_queries[:3]         # literales embebidos por step
plan.keyword_queries[:3]
min_match_score = 5              # dentro de la función
```

La configuración de costos vive en dos lugares con dos ciclos de vida (panel de Railway vs. commit + redeploy). Recomendación: un único objeto Pydantic Settings con todos los límites, registrado en el log al inicio de cada run.

---

## 7. Costos del pipeline

⚠️ **Corrección v1.0:** la v1.0 daba dos cifras contradictorias (~211 llamadas / $0.13 y ~60 / $0.04). La primera incluía `get_user_about` y STEP 0, ambos **apagados por defecto**.

### Configuración vigente (defaults del código)

| Fase | Llamadas aprox. | Costo aprox. |
|---|---|---|
| Hashtag top (3) | ~6 | $0.004 |
| Hashtag recientes (2) | ~4 | $0.002 |
| Keyword (3 × 3 variantes) | ~9 | $0.005 |
| Reels (1) | ~1 | $0.001 |
| Expansión de seguidores | 1 (⚠️ desperdiciada) | $0.001 |
| Top search (1) | ~2 | $0.001 |
| Sugeridos (1) | ~1 | $0.001 |
| **Enrichment (50 handles)** | **50** | **$0.030** |
| **Total** | **~74** | **~$0.045** |

### Configuraciones desactivadas (referencia histórica)

| Opción | Llamadas extra | Costo extra |
|---|---|---|
| `HIKERAPI_STEP0_LOCATION=true` | +42 | +$0.025 |
| `HIKERAPI_INCLUDE_ABOUT=true` | +50 | +$0.030 |
| `MAX_HANDLES_TO_ENRICH=500` (histórico) | +900 | +$0.54 |

### ⚠️ Control de presupuesto: NO EXISTE

`app/core/discovery_cost_tracker.py` **registra** costos pero no los limita. No hay presupuesto mensual, ni gasto acumulado consultable, ni corte automático, ni tope de llamadas por run.

**Consecuencia documentada:** $50-72 USD consumidos en dos días contra un objetivo de $10/mes, sin que ningún mecanismo interviniera. Con `MAX_HANDLES_TO_ENRICH=500` y ~80 runs de prueba, la aritmética se cumple exactamente.

**Controles mínimos pendientes:**
1. `MONTHLY_BUDGET_USD` + acumulado por proveedor + corte al 100% y aviso al 70%
2. `MAX_CALLS_PER_RUN` (~120) que aborte el run y lo marque `partial`
3. Sin reintentos en 401/402/403 (errores permanentes)
4. Modo `replay` con costo cero para iterar sobre scoring sin gastar

El punto 4 merece énfasis: la mayor parte del gasto se produjo probando lógica de scoring, que no necesita datos frescos.

---

## 8. Issues conocidos

### Corregidos (2026-08-13)

| Bug | Fix |
|---|---|
| `get_user_about()` 422 | `/gql/user/about?user_id` → `/v1/user/about?id` |
| `search_location()` | `/v1/location/search` → `/v1/fbsearch/places?query` |
| `location_medias_*` | param `id` → `location_pk` |
| Costo excesivo | `MAX_HANDLES_TO_ENRICH` 500 → 50 |

### Abiertos

| Issue | Prioridad | Detalle |
|---|---|---|
| Sin fusible de presupuesto | **Crítica** | §7 — no recargar créditos antes de tenerlo |
| 402 se reporta como "0 candidatos" | **Crítica** | §4.1 — fallo de infraestructura presentado como resultado de negocio |
| Saldo HikerAPI agotado | Crítica | requiere recarga (después del fusible) |
| Sin idempotencia en encolado | Alta | doble clic o redeploy = cobro doble |
| Prefiltro muerto con log engañoso | Alta | resultado sobrescrito 110 líneas después; su log reporta filtrado inexistente |
| `_fetch_step2p6` roto | Alta | gasta 1 `enrich_profile` por run y devuelve vacío |
| Enriquecimiento sobre muestra casi aleatoria | Alta | §3 — decide gasto sin datos |
| `country` e `is_private` se pierden en el merge | Media | 7 bloques duplicados no copian esos campos |
| Contrato `InstagramSource` incompleto | Media | 5 métodos declarados, 13 usados |
| Vocabulario de negocio hardcodeado | Media | revierte la universalización |
| Estado del orchestrator en memoria | Media | columna `state` existe y no se usa |
| Multi-tenancy inexistente | Media | bloquea el segundo cliente |
| `search_hashtag_recent` sin caché | Baja | `cache_ttl=0` en endpoint de pago |

---

## 9. Deployment

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

⚠️ `restartPolicyMaxRetries = 3` combinado con la falta de idempotencia (§8) implica que un crash con jobs en vuelo puede reejecutar runs y volver a cobrarlos.

---

## 10. Recursos

| Recurso | URL |
|---|---|
| API Docs | `https://lawebcore-production.up.railway.app/api/docs` |
| HikerAPI billing | `https://hikerapi.com/billing` |
| Railway | `https://railway.app/project/lawebcore` |
| Vercel | `https://vercel.com/lawebcore` |

---

*Correcciones derivadas del análisis estático del commit `a250b0c`. Detalle completo y plan de acción en `LENS_REVIEW_ARQUITECTURA_2026-08-14.md`.*
