# PLAN MAIN — Alineación LENS Discovery
## Basado en el Informe de Santiago Lanz (v1.2, 24-ago-2026) + Análisis Claude Code Fable 5

> **Para:** Claude Code Fable 5 (subagente con acceso directo a https://github.com/ungardev/lawebcore)
> **De:** MiniMax M2.7/M3 (modelo agente de programación) + análisis exhaustivo post-commit `2446e75`
> **Fecha:** 27 de agosto de 2026
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Commit base actual:** `2446e75` (8 fixes aplicados: Hitos 35.1-35.8, 27-ago-2026)
> **Commit anterior:** `bd973c7` (Hitos 30-34 foundation, 26-ago-2026)
> **HikerAPI balance:** ~$38 USD restantes
> **Saldo tras validación pendiente:** ~$36.86 USD

---

## RESUMEN EJECUTIVO — Estado del Proyecto

El proyecto LENS Discovery se encuentra en **fase de estabilización avanzada**. Los 8 fixes de la fase 35 (regresión crítica + data integrity) fueron aplicados y pusheados en commit `2446e75`. El deploy en Railway fue exitoso.

**El backend está técnicamente operativo.** Sin embargo, antes de hacer una corrida de validación en producción (~$1.14), se realizó un análisis de acoplamiento frontend-backend que reveló **2 issues críticos en el frontend** que impedirían que el usuario vea los candidatos aunque el backend funcione perfectamente.

**Issue crítico #1:** El enum `RunStatus` en el worker escribe 5 valores que NO existen en el Pydantic enum `DiscoveryRunStatus` del endpoint GET runs. **Esto causa HTTP 500 en cada corrida exitosa** — el polling del frontend nunca completará y el usuario no verá candidatos.

**Issue crítico #2:** `Influencer.primary_tier` ahora almacena 9 sub-tiers pero el tipo TypeScript del frontend solo conoce 4 valores macro.

---

## Documentos de Referencia

| Documento | Descripción |
|-----------|-------------|
| `docs/La Web Figital - Informe de Alineación Técnica LENS.md` | Auditoría Santiago Lanz (v1.2, 24-ago-2026) — fuente del plan |
| `docs/VERIFICACION_CODIGO_LENS_HITOS_30-35_25-08-26.md` | Auditoría completa de Fable 5 sobre commit `18ae963` |
| `docs/PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md` | Plan de desarrollo oficial Fable 5 (605 líneas) |
| `docs/13a_data_contract_discovery.md` | Data contract LENS v1.0 |
| `docs/LANZ_VERIFICACIONES_2026-08-25.md` | Resultados V0-V4 de verificaciones Lanz |
| `docs/ARQUITECTURA_LENS.md` | Arquitectura LENS v5.6 (requiere actualización) |
| `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` | Índice histórico de auditorías (actualizar con #17) |

---

## SECCIÓN 1 — Lo Que Ya Está Aplicado (Commit `2446e75`)

### Hitos 30-34 aplicados (commit `bd973c7`, 26-ago-2026)

| Hito | Descripción | Archivos | Estado |
|------|-------------|----------|--------|
| **Hito 30** | Observabilidad: contextvars, RunEvent/DropReason/RunStatus enums, DropLedger, FunnelTracker, drop_profile(), can_make_call() eliminada, events table migration 108 | `shared_core/observability.py`, `worker.py`, `budget_fuse.py`, `migrations/108` | ✅ Aplicado |
| **Hito 31.1** | `_normalize_user()` devuelve `None` para campos ausentes | `hikerapi_client.py:821-856` | ✅ Aplicado |
| **Hito 31.2** | 7 pares dual-name eliminados del retorno de `_normalize_user()` | `hikerapi_client.py` | ✅ Aplicado |
| **Hito 31.4** | ~10+ patrones `or 0` corregidos con checks explícitos de None | `worker.py` | ✅ Aplicado |
| **Hito 31.5** | `docs/13a_data_contract_discovery.md` creado | `docs/13a_data_contract_discovery.md` | ✅ Aplicado |
| **Hito 32.1** | `_derive_tier()` en discovery.py (no más MICRO hardcoded) | `discovery.py:840-854` | ✅ Aplicado |
| **Hito 32.2** | Deduplicación por handle + migración 109 | `discovery.py`, `migrations/109` | ✅ Aplicado |
| **Hito 32.3** | Métricas carry-through: follower_count, engagement_rate, avg_likes en save | `discovery.py` | ✅ Aplicado |
| **Hito 32.4** | INSERT en influencer_social_accounts + influencer_metrics_snapshot | `discovery.py` | ✅ Aplicado |
| **Hito 33.1** | Constants a config: DISCOVERY_HASHTAG_TOP_LIMIT, etc. | `config.py`, `worker.py` | ✅ Aplicado |
| **Hito 33.2** | Slices usan settings en vez de hardcoded | `worker.py:551,564,579,602` | ✅ Aplicado |
| **Hito 33.3** | Metadata corregida: *_executed_count vs *_planned_count | `worker.py:408-415` | ✅ Aplicado |
| **Hito 34.1** | `response_format={"type": "json_object"}` en llamadas DeepSeek | `candidate_analyzer.py:327` | ✅ Aplicado |
| **Hito 34.3** | Regex extraction eliminado de `_parse_batch_response` | `candidate_analyzer.py:182-194` | ✅ Aplicado |
| **Hito 34.4** | `_fallback_scores` marcado con `is_fallback=True` | `candidate_analyzer.py:253` | ✅ Aplicado |
| **Hito 34.5** | Modelo DeepSeek: `deepseek-chat` → `deepseek-v3` | `config.py:55` | ✅ Aplicado |
| **Hito 35.2** | Validación backend: product_name y niches requeridos | `discovery.py:508-512` | ✅ Aplicado |

### 8 Fixes Fase 35 aplicados (commit `2446e75`, 27-ago-2026)

| Fix | Descripción | Archivos | Impacto |
|-----|-------------|----------|---------|
| **FIX #1+2** | Merge enrichment ahora solo snake_case + `_enriched: True`; scoring lee `follower_count` primero y distingue `MISSING_FOLLOWER_FIELD` de explore mode | `worker.py:1209, 1305` | **CRÍTICO —恢复 pipeline de enrichment** |
| **FIX #3** | `flush_drop_ledger()` persiste el ledger a `discovery_run_events`; `DropLedger.counts()` y `stage_of()` agregados | `observability.py`, `worker.py:1927` | **Auditoría funcional** |
| **FIX #4+5** | UPSERT `influencer_social_accounts` con `on_conflict=platform,handle`; captura `social_account_id`; UPSERT `influencer_metrics_snapshot` con `social_account_id` y sin columna `platform` inexistente | `discovery.py:949` | **Integridad de datos de influencers** |
| **FIX #6** | `_derive_tier` expandido a 9 sub-tiers alineados con `TIER_BENCHMARKS`; retorna `None` para `followers=None` | `discovery.py:844` | **Clasificación correcta de tiers** |
| **FIX #8** | `re.search` en `_parse_batch_response` reemplazado por `_json.loads()` directo | `candidate_analyzer.py:182` | **Contrato de datos más limpio** |

### Lo Que NO se hizo de los pendientes originales

Los items #1, #2, #3, #4, #5, #6, #7, #8 del plan original fueron **reestructurados o descartados** según el análisis de Fable 5:

| # original | Decisión | Razón |
|------------|---------|-------|
| **#0** | ✅ Aplicado como FIX #1+2 | Era la regresión más crítica |
| **#1** (LegacyCompatReader) | ⏸ Descartado | Fable 5 determinó que leer directo `e.get("follower_count")` es la solución correcta — no se necesita ventana de compatibilidad |
| **#2** (Freshness 7d) | ⏸ Pendiente | Requiere Fix #4+5 (ya aplicado) + decisión de negocio sobre ventana |
| **#3** (Brand exclusion) | ⏸ Pendiente | Requiere lista real de handles Nestlé/Purina VE |
| **#4** (drop_profile persistence) | ✅ Aplicado como FIX #3 | `flush_drop_ledger()` implementado |
| **#5** (Dual write camelCase) | ⏸ Parcialmente aplicado | Fix #1+2 ya elimina la escritura dual en merge; otras 8 zonas no críticas |
| **#6** (Prefilter snake_case) | ✅ Aplicado en scoring | Fix #2 ahora lee `follower_count` directo |
| **#7** (_derive_tier 9 tiers) | ✅ Aplicado como FIX #6 | 9 sub-tiers implementados |
| **#8** (seed.sql/schema.sql) | ⏸ Pendiente | Housekeeping menor |
| **#9** (Tests) | ⏸ Pendiente | CI gate — se hará post-estabilización |
| **#10** (Retirar LegacyCompatReader) | ⏸ No aplica | LegacyCompatReader no se implementó |

---

## SECCIÓN 2 — Análisis de Acoplamiento Frontend-Backend

### Metodología

Se realizó un análisis exhaustivo del frontend en `apps/web/src` y los 8 fixes del backend. Se leyeron **todos los archivos** de la carpeta `features/lens/` + archivos de types + API client + hooks + páginas.

### Veredicto General

**El pipeline de datos funciona end-to-end.** Los fixes del backend no rompen el wire contract — los candidatos siguen llegando con los mismos campos. Sin embargo, **2 issues críticos impiden que el usuario vea los resultados** si se hiciera una corrida ahora.

---

## SECCIÓN 3 — Issues Críticos Frontend-Backend

### 🔴 ISSUE C-1: RunStatus Enum Mismatch — HTTP 500 en Toda Corrida Exitosa

**Severidad:** CRÍTICA — Bloquea cualquier corrida exitosa

**Descripción:**

El worker (`worker.py`) escribe statuses a `discovery_runs.status` usando el enum `RunStatus` de `observability.py`:

```python
# observability.py:72-83 — lo que el WORKER escribe:
class RunStatus(str, Enum):
    QUEUED = "queued"           # línea 320
    RUNNING = "running"         # línea 280
    DELIVERED = "delivered"     # línea 1787
    DEGRADED = "degraded"       # línea 1788, 1967
    EMPTY = "empty"
    INCONSISTENT = "inconsistent"
    ABORTED_BUDGET = "aborted_budget"  # línea 320
    FAILED = "failed"           # línea 1943
```

Pero el endpoint API `GET /lens/discovery/runs/{run_id}` usa `response_model=DiscoveryRunResponse` con:

```python
# schemas.py:11-19 — lo que el Pydantic enum CONOCE:
class DiscoveryRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"
    EXPLORED = "explored"
```

**5 valores nuevos NO están en el enum Pydantic:**
- `queued`
- `delivered`
- `degraded`
- `empty`
- `inconsistent`
- `aborted_budget`

**Consecuencia:** Cuando el worker termina con `DELIVERED` (el caso más común, línea 1787), la siguiente llamada al polling `GET /runs/{id}` retornará **HTTP 500** por validación Pydantic fallida. El frontend nunca verá candidatos.

**¿Cuándo afecta?**
- `DELIVERED` → **toda corrida exitosa** (línea 1787)
- `DEGRADED` → corridas con enrichment parcial (línea 1788, 1967)
- `ABORTED_BUDGET` → monthly budget agotado (línea 320)

**Archivos afectados:**
- `packages/discovery/discovery/schemas.py:11-19` — `DiscoveryRunStatus` enum (falta 5 valores)
- `apps/api/app/api/v1/discovery.py:760-772` — `GET /runs/{run_id}` usa `response_model=DiscoveryRunResponse`

**Fix requerido:**
Opción A (recomendada): Extender `DiscoveryRunStatus` en `schemas.py` con los 5 valores faltantes.
Opción B: Quitar `response_model=DiscoveryRunResponse` del endpoint GET runs.

**Costo del fix:** $0 (30 minutos)

---

### 🔴 ISSUE C-2: Influencer.primary_tier Type Mismatch

**Severidad:** MEDIA — No bloquea búsqueda, pero corrompe datos guardados

**Descripción:**

Después de FIX #6, `_derive_tier` devuelve 9 sub-tiers:
```
NANO_BAJO (<2k), NANO_ALTO (<10k), MICRO_BAJO (<30k), MICRO_MEDIO (<100k),
MICRO_ALTO (<500k), MID_BAJO (<1M), MID_ALTO (<5M), MACRO_BAJO (<10M), MACRO_ALTO (10M+)
```

Cuando el usuario guarda un candidato como influencer, `discovery.py:902` escribe:
```python
"primary_tier": _derive_tier(follower_count),  # devuelve "MICRO_ALTO" etc.
```

Pero el tipo TypeScript del frontend:
```typescript
// apps/web/src/types/index.ts:43
primary_tier: 'NANO' | 'MICRO' | 'MID' | 'MACRO' | 'MEGA' | 'MIX';
```

**No incluye los 9 sub-tiers nuevos.**

**Consecuencia:**
- La lista de influencers guardados y la vista de campañas mostrarán `—` o valores por default para el campo `primary_tier`
- El type system de TypeScript miente en runtime
- Componentes que filtran por `primary_tier` en campañas fallan silenciosamente

**Archivos afectados:**
- `apps/web/src/types/index.ts:43` — `Influencer.primary_tier` (falta 9 sub-tiers)
- `apps/web/src/features/campaigns/components/NewCampaignModal.tsx:30` — `TIERS` array (falta sub-tiers)
- `apps/web/src/lib/utils.ts:51` — `INFLUENCER_TIERS` const

**Fix requerido:**
Ampliar el union type en `types/index.ts:43` para incluir los 9 sub-tiers:
```typescript
primary_tier: 'NANO' | 'NANO_BAJO' | 'NANO_ALTO' | 'MICRO' | 'MICRO_BAJO' | 'MICRO_MEDIO' | 'MICRO_ALTO' | 'MID' | 'MID_BAJO' | 'MID_ALTO' | 'MACRO' | 'MACRO_BAJO' | 'MACRO_ALTO' | 'MEGA' | 'MIX';
```

**Costo del fix:** $0 (30 minutos)

---

### 🟡 ISSUE C-3: Tier Filter Chips Desaparecen en CandidateList

**Severidad:** BAJA — No bloquea, es degradación cosmética

**Descripción:**

`CandidateList.tsx:20` define:
```typescript
const ALL_TIERS = ['NANO', 'MICRO', 'MID', 'MACRO'] as const;
```

Y filtra: `candidates.some((c) => c.tier === t)`.

**NOTA:** Los candidatos que el frontend recibe del endpoint SON los del worker, y el worker clasifica con `classify_tier()` de `geo_boost.py:122-130` que devuelve 4 tiers (NANO/MICRO/MID/MACRO). Los candidatos en pantalla **siguen siendo 4-tier**.

Solo los influencers **guardados** reciben los 9 sub-tiers de `_derive_tier()`.

**Estado:** NO AFECTA a la búsqueda activa. El filtro de tiers en `CandidateList` funciona correctamente para candidatos. El issue aplica solo si el frontend en el futuro muestra candidatos guardados (que ya tienen 9 sub-tiers).

**Fix opcional:** Cuando se decida migrar los candidatos a 9 sub-tiers, actualizar `ALL_TIERS` y los chips.

---

### 🟡 ISSUE C-4: Tier Badge Sin Color (getTierColor Fallback)

**Severidad:** BAJA — Degradación cosmética

**Descripción:**

`getTierColor()` en `format.ts:65-78` solo tiene casos para `MACRO/MID/MICRO/NANO`. Cuando recibe `MICRO_ALTO` o `NANO_BAJO`, cae al caso `default` que da color gris apagado.

**Impacto real:** Los badges de tier perderán el código de color semántico. No afecta funcionalidad, solo legibilidad visual.

**Fix:** Agregar casos para los 9 sub-tiers en `getTierColor()` y `getTierLabel()`.

---

### 🟡 ISSUE C-5: SearchProgress PHASES Desfasadas vs worker.current_step

**Severidad:** BAJA — Desfasaje visual en los chips de progreso

**Descripción:**

Frontend `SearchProgress.tsx:21-29` define PHASES:
```
parsing_brief, building_queries, step1_hashtag_search, step2_keyword_search,
step3_profile_enrichment, step4_scoring, inserting_candidates
```

Worker `current_step` escribe:
- `step1_hashtag_search` ✅
- `step3_profile_enrichment` ✅
- `step4_scoring` ✅
- `step5_ai_analysis` → **NO EXISTE en frontend** (el frontend no tiene `step5_ai_analysis` en PHASES)
- `step2_keyword_search` → **EL WORKER YA NO LO ESCRIBE** (el worker salta de step1 a step3)

**Consecuencia visual:** Los chips `step2_keyword_search` y `inserting_candidates` siempre quedan en estado "waiting" y `step5_ai_analysis` cae al fallback "Procesando discovery".

**Fix opcional:** Agregar `step5_ai_analysis` a PHASES en `SearchProgress.tsx`. Eliminar `step2_keyword_search` y `inserting_candidates` o marcarlos como deprecated.

---

### 🟡 ISSUE C-6: LensEmptyState Variants No Utilizadas

**Severidad:** BAJA — Código muerto

**Descripción:**

`LensEmptyState.tsx` define variants `no_results` y `no_candidates` pero **ningún componente las usa**. La variante `no_conversations` sí se usa en `LensChatPage.tsx:145`.

Cuando el worker emite el mensaje de cero candidatos (`_build_zero_candidates_message`), se renderiza como un turno de chat normal, no como un estado vacío especial.

**Fix opcional:** Integrar `no_candidates` variant o remover el código muerto.

---

## SECCIÓN 4 — Items Pendientes del Plan Original

### Still Pending: Decisiones de Negocio

| # | Pregunta | Bloquea | Prioridad |
|---|---------|---------|-----------|
| Q1 | Lista real de handles Nestlé/Purina VE para `brand_excluded_handles` | Hito 32.6 | 🔴 Alta |
| Q2 | Ventana de frescura: ¿7 vs 14 vs 30 días? | Hito 32.5 | 🟡 Media |
| Q3 | ¿Tier targeting en campañas a nivel macro (4) o sub-tier (9)? | Frontend tiers | 🟡 Media |
| Q4 | ¿Aprobación de ensanche 5/3/5/2? (Fix opcional D-2) | $0.44/corrida extra | 🟡 Media |

### Still Pending: Features Técnicas

| # | Feature | Descripción | Costo |
|---|---------|-------------|-------|
| **FP-1** | Freshness policy 7d | Skip enrichment si existe snapshot <7 días | ~$0.30-0.50/run ahorrado |
| **FP-2** | Brand exclusion table | Compliance Nestlé L-03/L-05 | $0 |
| **FP-3** | seed.sql/schema.sql `deepseek-v3` | Housekeeping | $0 |
| **FP-4** | Tests `test_hito31_data_contract.py` | CI gate | $0 |
| **FP-5** | Ensanche 5/3/5/2 | Más hashtags/keywords en búsqueda | ~$0.44/corrida extra |

---

## SECCIÓN 5 — El Pipeline Completo: Cómo Funciona LENS

### 5.1 Arquitectura General

```
Usuario (brief) → API → ARQ Worker (Redis) → HikerAPI + DeepSeek → DB → API → Frontend
```

El worker `discovery_run_task` es un job async de ARQ que corre en Railway. Cada corrida cuesta entre **$0.24 (explore)** y **$1.14+ (auto completo)**.

### 5.2 Inputs

**BriefStructured** (de `packages/discovery/discovery/schemas.py`):
```python
BriefStructured(
    product_name="collar para perros",
    niches=["mascotas", "perros"],
    hashtags=[],           # El sistema los deriva con IA
    audience_countries=["VE"],
    max_candidates=20,
    discovery_mode="auto", # auto | explore | analyze
    exclude_stores=True,
    influencer_preferences={"min_followers": 5000, "max_followers": 50000},
)
```

**Del brief se deriva un `DiscoveryPlan`** con:
- `hashtag_queries`: 20-30 hashtags VE-específicos
- `keyword_queries`: 15-25 keywords de nicho
- `profile_data`: inteligencia IA del campaña cacheada en Redis (40d)

### 5.3 Etapas del Pipeline

#### Etapa 0 — Búsqueda por Ubicación (opcional)
Solo si `HIKERAPI_STEP0_LOCATION=true`. Busca por ciudades en `audience_cities`.

#### Etapa 1 — Hashtags
```
search_hashtag("#mascotasvzla") → 20 posts top + 20 recent → extrae handles
```
API: `GET /v2/hashtag/medias/top` + `/v2/hashtag/medias/recent`
Límites: `DISCOVERY_HASHTAG_TOP_LIMIT=10`, `DISCOVERY_HASHTAG_RECENT_LIMIT=10`, `MAX_POSTS_PER_HASHTAG=20`

#### Etapa 2 — Keywords y Reels
```
search_keyword("mascotas") → cuentas que matchean la keyword
search_reels_by_keyword("mascotas") → creators descubiertos por Reels
```
API: `GET /v3/fbsearch/accounts` + `GET /v2/fbsearch/reels`
Límites: `DISCOVERY_KEYWORD_LIMIT=10`, `DISCOVERY_TOP_SEARCH_LIMIT=5`
Para VE: también busca `"mascotas vzla"` y `"mascotas venezuela"`

#### Etapa 3 — Prefiltrado (Rough Scoring)
Antes de enriquecer (caro), pre-filtra a **top 25 handles** con scoring aproximado:
```python
geo = geo_score(profile, geo_indicators)       # 0.0-1.0
niche = niche_relevance(profile, keywords)     # 0.0-1.0
rough = 0.5 * geo + 0.5 * niche
# + penalizaciones por bot (+ creator boost)
```
Solo los 25 mejores proceden a enrichment.

#### Etapa 4 — Enrichment (HikerAPI) ← FIX #1+2修复此处
```
enrich_profile(handle) → /v2/user/by/username
  → followersCount, followsCount, postsCount, biography, latestPosts
  → optionally: /v1/user/about (senales de fraude)
```
Costo: $0.02/llamada × 25 = $0.50

**El contrato de datos (hikerapi_client.py:_normalize_user):**
- Recibe respuesta camelCase del API externo
- Devuelve snake_case: `followersCount → follower_count`
- Si falta: `None` (NO `0`) — Hito 31.1

**FIX #1+2修复详情:**
- ANTES: merge escribía `followersCount = None` (dual write) → scoring leía `p.get("followersCount")` que existía con valor `None` → convertía a `0` → descartaba TODO perfil enriquecido
- AHORA: merge solo snake_case + `_enriched:True`; scoring lee `follower_count` primero; distingue `MISSING_FOLLOWER_FIELD` (enriquecido pero sin datos) de explore mode

#### Etapa 5 — Scoring (lens_score)
Todos los perfiles (no solo enriquecidos) pasan scoring:

```python
score = (
    0.389 * tier_normalized_er     # 35% — ER relativo al benchmark del tier
    + 0.278 * geo_score           # 25% — señal geográfica VE
    + 0.222 * niche_relevance     # 20% — overlap keywords en bio/username
    + 0.111 * business_intent     # 10% — URL externa, business account, verificado
)
if cross_referenced: score *= 1.15  # +10% si encontrado en hashtags Y keywords
```

**Filtros duros que descartan:**
1. `MISSING_FOLLOWER_FIELD` — enriquecido pero sin followers
2. `BELOW_MIN_FOLLOWERS` — debajo del mínimo
3. `ABOVE_MAX_FOLLOWERS` — encima del máximo
4. `BOT_PATTERN` — ER >30% o ER <0.5% con >5k followers
5. `GEO_MISMATCH` — TLD no VE, país en bio no coincide
6. `POLITICAL_CONTENT` — keywords de exclusión política

**Tier classification (FIX #6):** 9 sub-tiers:
```
NANO_BAJO (<2k) → NANO_ALTO (<10k) → MICRO_BAJO (<30k) → MICRO_MEDIO (<100k)
→ MICRO_ALTO (<500k) → MID_BAJO (<1M) → MID_ALTO (<5M)
→ MACRO_BAJO (<10M) → MACRO_ALTO (10M+)
```

**Tier diversification:** Redistribuye para no entregar solo NANO:
55% NANO, 30% MICRO, 10% MID, 5% MACRO

#### Etapa 6 — AI Analysis (DeepSeek) ← Solo modo "auto"
Solo si `analyze_with_ai=True` y modo `auto` (NO `explore`):
```python
analyze_candidates_batch(candidates, brief, profile_data)
# Batches de 10, hasta 5 concurrentes
# Por candidato: content_quality, audience_quality, brand_fit (0-100)
```
Costo DeepSeek: ~$0.50 por corrida

**FIX #8:** `_parse_batch_response` ahora usa `_json.loads()` directo en vez de `re.search`.

#### Etapa 7 — Deduplicación e Inserción
```python
upsert_many(
    table="discovery_candidates",
    records=candidates,
    on_conflict=["run_id", "platform", "handle"],
)
```
**FIX #4+5:** UPSERT en `influencer_social_accounts` y `influencer_metrics_snapshot` — sin duplicados, con `social_account_id`.

#### Etapa 8 — Costes y Observabilidad
```python
hikerapi_calls = budget_fuse.get_run_calls(run_id)  # Redis counter
actual_cost_usd = hikerapi_calls * $0.02 + deepseek_cost
```

**FIX #3:** `flush_drop_ledger()` persiste el ledger de descartes a `discovery_run_events`.

### 5.4 Estados de Corrida

```
DELIVERED   → éxito total
DEGRADED    → enrichment parcial (budget cap)
EMPTY        → 0 candidatos (funnel OK)
INCONSISTENT → 0 candidatos Y funnel no cuadra
ABORTED_BUDGET → monthly budget agotado
FAILED        → exception no manejada
```

**Issue C-1:** `DELIVERED`, `DEGRADED`, `ABORTED_BUDGET`, `EMPTY`, `INCONSISTENT` NO están en el Pydantic enum `DiscoveryRunStatus`. Causan HTTP 500.

---

## SECCIÓN 6 — Flujo de Datos Detallado

### 6.1 De Brief a DiscoveryPlan

```
BriefStructured → QueryBuilder.build() → DiscoveryPlan
                                     → hashtag_queries (20-30 hashtags VE)
                                     → keyword_queries (15-25 keywords)
                                     → min_followers, max_followers
                                     → profile_data (inteligencia IA cacheada)
```

ProfileData se genera via `get_or_create_profile(brief)` → DeepSeek LLM → cache Redis 40d + DB.

### 6.2 Perfil Raw → Perfil Enriquecido

```
HikerAPI (hashtag/keyword/reels) → profiles[handle] con datos RAW
    ↓
Prefilter (rough scoring: geo + niche) → top 25 handles
    ↓
HikerAPI /v2/user/by/username → profiles[handle] con datos ENRIQUECIDOS
    ↓
Scoring (lens_score) → candidate dict
    ↓
AI Analysis (DeepSeek) → candidate con content_quality, audience_quality, brand_fit
    ↓
upsert_many → discovery_candidates table
```

### 6.3 Descripción de Campos Clave

| Campo | Origen | Descripción |
|-------|--------|-------------|
| `match_score` | `lens_score()` | Score 0-100: 35% ER normalizado + 25% geo + 20% niche + 10% business + 10% cross_ref |
| `niche_relevance` | `niche_relevance()` | 0-100: keyword overlap en bio/username + hashtag overlap |
| `geo_relevance` | `geo_score()` | 0-100: ciudad, gentilicios, keywords VE |
| `content_quality` | DeepSeek | 0-100: producción, coherencia de nicho |
| `audience_quality` | DeepSeek | 0-100: señales de autenticidad, detección de bots |
| `brand_fit` | DeepSeek | 0-100: alineación con brief |
| `tier` | `classify_tier()` / `_derive_tier()` | Clasificación por seguidores |
| `is_tienda` | keyword detection | Bool — si es cuenta comercial |
| `rationale` | `build_rationale()` / DeepSeek | Razonamiento en español |

### 6.4 Save Candidate Flow

```
User click "Guardar" → POST /candidates/{id}/save
    → upsert influencers (ON CONFLICT primary_handle → UPDATE)
    → upsert influencer_social_accounts (ON CONFLICT platform,handle → do nothing)
    → capture social_account_id
    → upsert influencer_metrics_snapshot (ON CONFLICT influencer_id,social_account_id,snapshot_date,source)
    → UPDATE discovery_candidates SET status='saved'
    → UPDATE discovery_runs SET accepted = accepted + 1
```

**FIX #4+5:** Todo es ahora UPSERT — sin duplicados de social accounts ni métricas.

---

## SECCIÓN 7 — Sistema de Costos y Budget

### 7.1 Arquitectura de Budget

```
PRESUPUESTO MENSUAL: $10 USD (HikerAPI)
    └── Redis: lens:budget:hikerapi:2026-08

LÍMITE POR RUN: 120 llamadas
    └── Redis: lens:budget:run:{run_id}
```

### 7.2 Flujo de Costos

1. **Pre-flight**: `get_balance()` vs `estimated_calls * $0.02`. Si insufficient → `SourceUnavailable` (402).
2. **Por llamada**: `reserve_and_record()` (Lua script atómico en Redis) — única fuente de verdad de llamadas HikerAPI. Cache hits NO cuentan.
3. **Post-run**: `actual_cost_usd = hikerapi_calls * $0.02 + deepseek_cost`

### 7.3 Costos por Modo

| Modo | Discovery | Enrichment | AI | Total |
|------|-----------|------------|-----|-------|
| Explore | ~32 calls ($0.64) | $0 | $0 | ~$0.24 |
| Analyze | 0 | ~N calls ($0.02N) | ~$0.50 | ~$0.50 + $0.02N |
| Auto | ~32 calls ($0.64) | 25 calls ($0.50) | ~$0.50 | ~$1.14 + DeepSeek |

### 7.4 BudgetFuse — Source of Truth

唯一 punto de registro de llamadas HikerAPI: `budget_fuse.reserve_and_record()` en `hikerapi_client.py:240`. Lua script atómico previene race conditions.

---

## SECCIÓN 8 — Sistema de Observabilidad

### 8.1 Arquitectura de 7 Capas

```
1. Taxonomy: enums cerrados (RunEvent, DropReason, RunStatus)
2. Drop book: DropLedger + drop_profile() — único punto de salida
3. Invariant funnel: FunnelTracker con verificación contable
4. State machine: RunStatus transitions
5. Events table: discovery_run_events (FIX #3 ahora la popula)
6. Alerts: budget thresholds con logging
7. Context: structlog.contextvars
```

### 8.2 Drop Reasons Disponibles

```
MISSING_FOLLOWER_FIELD — enriquecido pero sin followers
ENRICHMENT_FAILED — llamada falló
ENRICHMENT_SKIPPED_BUDGET — enrichment saltado por budget
BELOW_MIN_FOLLOWERS — debajo del mínimo
ABOVE_MAX_FOLLOWERS — encima del máximo
BOT_PATTERN — ER sospechoso (>30% o <0.5% con >5k)
GEO_MISMATCH — señal geográfica no coincide
POLITICAL_CONTENT — keyword de exclusión política
EXCLUDED_STORE — cuenta comercial
FRAUD_SIGNAL — señal de fraude (former usernames, account age)
SCORE_BELOW_THRESHOLD — score menor al umbral
PRIVATE_ACCOUNT — cuenta privada
DUPLICATE_HANDLE — duplicado
```

### 8.3 FIX #3: flush_drop_ledger()

**Implementado:**
```python
async def flush_drop_ledger(run_id, ledger, railway_pg):
    # Una bulk INSERT a discovery_run_events
    # con una fila por cada DropReason no-zero
```

Se llama al final del run (worker.py:1927) después de que el worker completa.

**Verificación:**
```sql
SELECT reason_code, SUM((payload->>'count')::int) as total
FROM discovery_run_events
WHERE event = 'profile.dropped'
GROUP BY reason_code;
```

---

## SECCIÓN 9 — Arquitectura de la Base de Datos

### 9.1 Tablas Principales

```
discovery_runs           — runs individuales (status, cost, candidates count)
    └── discovery_candidates  — candidatos por run (handle, score, metrics)
            └── influencers   — influencers guardados
                    └── influencer_social_accounts  — cuentas por plataforma
                    └── influencer_metrics_snapshot  — métricas históricas

discovery_conversations  — conversaciones de chat
    └── discovery_messages  — mensajes

discovery_run_events    — log de eventos (drops) ← FIX #3 ahora la popula
budget_transactions     — libro de costos immutable
```

### 9.2 Schema discovery_candidates

```sql
UNIQUE (run_id, platform, handle) — un candidato por handle por run
status: new | saved | dismissed | contacted | replied | won | lost
tier: NANO | MICRO | MID | MACRO  (del worker, 4-tier)
is_tienda: BOOLEAN — detección por keywords
```

### 9.3 Schema influencers

```sql
UNIQUE (primary_handle) — un influencer por handle
primary_tier: NANO_BAJO | ... | MACRO_ALTO  (de _derive_tier, 9 sub-tiers) ← Issue C-2
```

---

## SECCIÓN 10 — Plan de Acción Inmediato

### Paso 1 (AHORA): Fix Issues Críticos Frontend (~$0)

Antes de hacer cualquier corrida de validación, resolver:

| # | Issue | Fix | Archivo | Tiempo |
|---|-------|-----|---------|--------|
| C-1 | RunStatus enum mismatch | Extender `DiscoveryRunStatus` con 5 valores faltantes | `schemas.py:11-19` | 30 min |
| C-2 | Influencer.primary_tier type | Ampliar union type con 9 sub-tiers | `types/index.ts:43` | 30 min |

### Paso 2: Validación Backend (~$1.14)

Después de Fix C-1 y C-2, hacer una corrida de validación en modo `auto` para confirmar:
- `discovery_run_events` muestra distribución de `reason_code` (no solo `MISSING_FOLLOWER_FIELD ≈ 100%`)
- El frontend muestra candidatos con datos reales de followers
- El polling completa sin HTTP 500

### Paso 3: Optional Frontend Improvements (~$0)

| # | Mejora | Archivo |
|---|--------|---------|
| C-4 | `getTierColor()` y `getTierLabel()` para 9 sub-tiers | `format.ts` |
| C-5 | Agregar `step5_ai_analysis` a PHASES de SearchProgress | `SearchProgress.tsx:21-29` |
| C-6 | LensEmptyState variants usadas o eliminadas | `LensEmptyState.tsx` |

### Paso 4: Features Pendientes

| # | Feature | Depende | Costo |
|---|---------|---------|-------|
| FP-1 | Freshness policy 7d | Fix C-1 + C-2 | ~$0.30-0.50/run ahorrado |
| FP-2 | Brand exclusion table | Q1 (handles Purina) | $0 |
| FP-3 | seed.sql/schema.sql `deepseek-v3` | Nada | $0 |
| FP-4 | Tests | post-estabilización | $0 |
| FP-5 | Ensanche 5/3/5/2 | Q4 (aprobación) | ~$0.44/corrida extra |

---

## SECCIÓN 11 — Saldo y Proyección

| Concepto | Monto |
|----------|-------|
| Saldo inicial | $43.00 USD |
| Corrida de validación (pendiente) | -$1.14 |
| Saldo post-validación | ~$41.86 USD (~36 corridas) |
| Fix C-1 + C-2 (frontend) | $0 |
| **Si validación OK + Fix C-1+C-2 aplicados** | **~$41.86 USD** |

---

## SECCIÓN 12 — Criterios de Éxito

### Para esta iteración (Fix C-1 + C-2)

- [ ] `DiscoveryRunStatus` enum incluye `delivered`, `degraded`, `aborted_budget`, `empty`, `inconsistent`
- [ ] `Influencer.primary_tier` TypeScript type incluye 9 sub-tiers
- [ ] Railway deploy exitoso
- [ ] Corrida de validación muestra distribución >1 valor en `discovery_run_events.reason_code`
- [ ] Polling del frontend completa sin HTTP 500
- [ ] Candidatos muestran `followers` real (no 0)

### Para el proyecto completo (post-todos los fixes)

- [ ] `flush_drop_ledger()` popula `discovery_run_events` en cada run
- [ ] `discovery_run_events.reason_code` muestra distribución realista (no solo una causa)
- [ ] 0 candidatos con `followers=0` después de enrichment exitoso
- [ ] `primary_tier` en influencers tiene 9 sub-tiers correctamente clasificados
- [ ] UPSERT de social accounts sin duplicados
- [ ] Ensanche 5/3/5/2 aprobado e implementado (opcional)

---

## SECCIÓN 13 — Decisiones Pendientes de Negocio

| # | Pregunta | Opciones | Impacto |
|---|---------|---------|---------|
| Q1 | Lista real de handles Nestlé/Purina VE | Necesaria para FP-2 (brand exclusion) | Compliance L-03/L-05 |
| Q2 | Ventana de frescura | 7 / 14 / 30 días (parametrizable por brand?) | Ahorro en HikerAPI calls |
| Q3 | Tier targeting en campañas | Macro (4) o sub-tier (9) | UX de campaign builder |
| Q4 | Ensanche 5/3/5/2 | Aprobar / Rechazar | +$0.44/corrida, más candidatos |

---

## SECCIÓN 14 — Glosario Técnico

| Término | Significado |
|---------|-------------|
| **LENS** | Discovery module — motor de búsqueda de influencers |
| **Fable 5** | Claude Code subagent (Full Stack Senior Engineer) — fuente de verdad técnica |
| **Santiago Lanz** | Ingeniero Auditor — autor del informe de alineación v1.2 |
| **BriefStructured** | Schema del brief de campaña |
| **DiscoveryPlan** | Plan derivado del brief (queries, límites, profile_data) |
| **ProfileData** | Inteligencia IA cacheada del campaña (benchmarks, señales, geo) |
| **HikerAPI** | API de Instagram data (perfiles, hashtags, búsqueda) |
| **DeepSeek** | LLM para análisis de candidatos y generación de profile_data |
| **BudgetFuse** | Sistema Redis de control de budget y límites por run |
| **DropLedger** | Contador de razones de descarte de perfiles |
| **flush_drop_ledger()** | Función que persiste el ledger a discovery_run_events |
| **RunStatus** | Enum de estados del worker (DELIVERED, DEGRADED, etc.) |
| **DiscoveryRunStatus** | Enum Pydantic del API (PENDING, RUNNING, COMPLETED, etc.) ← Issue C-1 |
| **LensScore** | Fórmula de scoring: 35% ER + 25% geo + 20% niche + 10% business + 10% cross_ref |
| **9 sub-tiers** | NANO_BAJO → MACRO_ALTO (clasificación de influencers por seguidores) |
| **UPSERT** | INSERT ON CONFLICT DO UPDATE — no crea duplicados |
| **ARQ** | Cola de jobs async en Redis (worker de background) |
| **Railway** | Plataforma de deployment (Postgres + Redis + Workers) |

---

*Documento actualizado: 27 de agosto de 2026 por MiniMax M2.7/M3*
*Basado en: Informe Lanz v1.2 + Análisis Fable 5 post-commit `2446e75` + Análisis acoplamiento frontend*
*Commit base: `2446e75` — 8 fixes aplicados*
*Próximo paso: Fix C-1 + C-2 → Corrida de validación*
