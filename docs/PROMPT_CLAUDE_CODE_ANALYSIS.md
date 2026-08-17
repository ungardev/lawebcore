# QUINTA AUDITORÍA — LENS Discovery Module (Análisis Exhaustivo de Costos + Fixes Completos)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Solicitud:** **QUINTA AUDITORÍA EXHAUSTIVA** — el sistema tiene 20 hitos + Bonus 1 aplicados y 33/33 tests pasando. Necesitamos que valides todos los fixes, corrijas la configuración de costos (el plan real de HikerAPI es **$0.02/request**, no $0.0006), y hagas un análisis detallado del costo real de un discovery run con el plan "Start" actual.
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI "Start" ($0.02/req) + DeepSeek

---

## CONTEXTO CRÍTICO — PLAN HIKERAPI "START"

```
╔══════════════════════════════════════════════════════════════════╗
║  PLAN HIKERAPI "START" — $0.02 USD por request              ║
╠══════════════════════════════════════════════════════════════════╣
║  Costo por request:   $0.02 USD                              ║
║  Balance prepago:    $20 USD (~1,000 requests)               ║
║  Todos los endpoints de Instagram incluidos (100+)           ║
║                                                                  ║
║  ⚠️ EL SISTEMA ACTUALMENTE TIENE CONFIGURADO:              ║
║     HIKERAPI_COST_PER_CALL_USD = 0.0006                    ║
║     ESTO ES 33 VECES MÁS BARATO QUE EL PLAN REAL          ║
║     (legacy de cuando el plan costaba ~$0.0006/req)        ║
║                                                                  ║
║  IMPACTO: BudgetFuse muestra gastos incorrectos              ║
║  Budget real se agota 33× más rápido de lo que muestra     ║
╚══════════════════════════════════════════════════════════════════╝

PRESUPUESTO OBJETIVO: < $10 USD/mes

ESCENARIOS REALES CON $0.02/req:
  Run completo (81 requests): $1.62 USD  →  ~6 runs/mes con $10
  Run sin enrichment (31 req): $0.62 USD  →  ~16 runs/mes con $10
  Run parcial cache (56 req): $1.12 USD  →  ~8 runs/mes con $10
```

---

## OBJETIVO

Ejecutamos 20 hitos + 1 bonus de fixes. El sistema pasa 33/33 tests. Pero **la configuración de costos de HikerAPI está desactualizada** — usa $0.0006 cuando el plan real cobra $0.02. Esto significa que el BudgetFuse muestro números falsos.

**Pedimos:**
1. Validar que los 20 hitos + Bonus 1 fueron correctamente aplicados
2. **Corregir `HIKERAPI_COST_PER_CALL_USD` a `$0.02`** en la configuración
3. Hacer análisis de costos detallado: ¿cuántos requests por fase? ¿cómo optimizar?
4. Proponer estrategias de reducción de costo sin perder calidad
5. Verificar `pytest` → 33/33 pass
6. Identificar cualquier issue que quede bloqueante para producción

---

## PLAN DE PRECIOS DETALLADO — HikerAPI "Start"

### Costos por endpoint

```
Endpoint                          │ Requests/run │ Costo/run ($0.02)
─────────────────────────────────┼──────────────┼────────────────
/v2/hashtag/by/name              │  5 (3 top+2) │  $0.10
/v2/hashtag/medias/top          │  9 (3×3 pág) │  $0.18
/v2/hashtag/medias/recent        │  4 (2×2 pág) │  $0.08
/v2/fbsearch/accounts           │  9 (3×3 var) │  $0.18
/gql/reels_serp                  │  1           │  $0.02
/gql/topsearch                   │  2           │  $0.04
/v2/user/suggested/profiles      │  1           │  $0.02
─────────────────────────────────┼──────────────┼────────────────
SUBTOTAL Discovery               │ 31           │  $0.62
─────────────────────────────────┼──────────────┼────────────────
/v1/user/by/username (enrich)     │ hasta 50     │  $1.00
─────────────────────────────────┼──────────────┼────────────────
TOTAL RUN COMPLETO              │ hasta 81     │  $1.62
```

### Preguntas específicas sobre costos

1. ¿Cómo afecta el enrichment completo ($1.62/run) vs enrichment parcial?
2. ¿Cuántos runs con enrichment completo puedo hacer con $10/mes?
3. ¿Merece la pena reducir MAX_HANDLES_TO_ENRICH para bajar el costo?
4. ¿El cache realmente reduce los costos en un escenario real de uso?
5. ¿DeepSeek (análisis IA) agrega costo significativo?

---

## ESTRUCTURA DEL PROYECTO

```
lawebcore/
├── apps/
│   ├── api/                              # FastAPI backend (Railway)
│   │   └── app/
│   │       ├── api/v1/                  # ~50 endpoints
│   │       ├── core/
│   │       │   ├── budget_fuse.py      # Budget + Lua atómico reserve_and_record
│   │       │   ├── hikerapi_circuit_breaker.py  # Singleton Redis-backed
│   │       │   └── worker_enqueuer.py   # ARQ _job_id + dedup check
│   │       ├── models/                  # SQLAlchemy ORM
│   │       ├── services/
│   │       └── workers/
│   │           └── worker.py            # ~1819 líneas
│   └── web/                             # React 19 (Vercel)
├── packages/
│   ├── discovery/
│   │   └── discovery/
│   │       ├── exceptions.py            # SourceUnavailable, TransientSourceError, BudgetExhausted, ReplayMiss
│   │       ├── orchestrator.py          # LRU/TTL state cache
│   │       ├── brief_parser.py
│   │       ├── profile_generator.py
│   │       ├── candidate_analyzer.py
│   │       ├── query_builder.py
│   │       ├── memory.py
│   │       ├── result_ranker.py
│   │       ├── scoring/
│   │       │   ├── lens_score.py       # target_country kwarg
│   │       │   ├── geo_boost.py        # target_country explícito
│   │       │   └── niche.py
│   │       └── tools/
│   │           ├── hikerapi_client.py   # _get() con record_call universal + replay
│   │           ├── hikerapi_circuit_breaker.py  # Singleton
│   │           ├── instagram_source.py  # Protocol abstraction
│   │           └── metricool_client.py
│   ├── shared-core/
│   │   └── shared_core/config.py       # ⚠️ HIKERAPI_COST_PER_CALL_USD = 0.0006 (LEGACY)
│   └── shared-ai/
├── supabase/migrations/
│   ├── 00000000000104_discovery_run_partial_status.sql
│   └── 00000000000105_discovery_profile_signal_keywords.sql
└── docs/
    ├── ARQUITECTURA_LENS.md        # v3.3 — con análisis de costos
    ├── LENS_REVIEW_ARQUITECTURA_2026-08-14.md
    ├── LENS_AUDIT2_2026-08-14.md
    └── LENS_AUDIT3_2026-08-14.md
```

---

## PIPELINE ACTUAL (worker.py ~1819 líneas)

```
DeepSeek → BriefStructured
    ↓
QueryBuilder → DiscoveryPlan
    ↓
┌─ STEP 1: Hashtag Top (3 hashtags)
│   1× /v2/hashtag/by/name  (info)
│   3× /v2/hashtag/medias/top  (hasta 3 páginas cada uno)
│   → usuario REDUCIDO (sin bio ni followers)
│   → CACHE TTL 12h
│   Costo: 12 requests = $0.24
│
├─ STEP 1_recent: Hashtag Recent (2 hashtags)
│   1× /v2/hashtag/by/name
│   2× /v2/hashtag/medias/recent (2 páginas)
│   → usuario REDUCIDO
│   → CACHE TTL 30 min
│   Costo: 6 requests = $0.12
│
├─ STEP 2: Keyword (3 keywords × 3 variantes geo)
│   9× /v2/fbsearch/accounts
│   → usuario COMPLETO (bio, followers)
│   → CACHE TTL 30 min
│   Costo: 9 requests = $0.18
│
├─ STEP 2p5: Reels serp (1 keyword)
│   1× /gql/reels_serp
│   → usuario REDUCIDO
│   Costo: 1 request = $0.02
│
├─ STEP 3: Top search (1 keyword)
│   2× /gql/topsearch
│   → usuario COMPLETO
│   → CACHE TTL 12h
│   Costo: 2 requests = $0.04
│
├─ STEP 4: Suggested (1 seed)
│   1× /v2/user/suggested/profiles
│   → usuario COMPLETO
│   Costo: 1 request = $0.02
│
│  SUBTOTAL Discovery: 31 requests = $0.62
│
├─ PREFILTRO ( scoring sin bio para hashtag/reels )
│   Commerce signals + creator signals (Hito 18 externalizable)
│   Exclusion keywords filter (Hito 18)
│
└─ STEP 10: ENRICHMENT (hasta MAX_HANDLES_TO_ENRICH=50)
    hasta 50× /v1/user/by/username
    Lua atómico reserve_and_record() (Hito 15)
    can_make_call() antes de cada HTTP (Hito 15)
    record_call() en TODAS las respuestas HTTP (Hito 14)
    → Costo: hasta 50 requests = $1.00

TOTAL RUN COMPLETO: hasta 81 requests = $1.62
```

---

## CONSTANTES DEL PIPELINE

```python
MAX_HANDLES_TO_ENRICH = 50        # enrichment: hasta 50 calls
MAX_POSTS_PER_HASHTAG = 20       # límite por hashtag
HASHTAGS_TOP = 3                # step1: 3 hashtags
HASHTAGS_RECENT = 2             # step1_recent: 2 hashtags
KEYWORDS = 3                    # step2: 3 keywords base
TOP_SEARCH = 1                  # step3: 1 keyword
SUGGESTED_SEEDS = 1            # step4: 1 semilla
ENRICHMENT_INCLUDE_ABOUT = False  # get_user_about OFF por defecto
```

**Vars de entorno en config:**
```python
MONTHLY_BUDGET_USD = 10.0           # Corte mensual hard
MAX_CALLS_PER_RUN = 120             # Límite de requests por run
BUDGET_ALERT_THRESHOLD = 0.7        # Warning al 70% ($7)
HIKERAPI_COST_PER_CALL_USD = 0.0006  # ⚠️ LEGACY — corregir a 0.02
HIKERAPI_5XX_BREAKER_THRESHOLD = 5   # 5xx → breaker OPEN
HIKERAPI_5XX_BREAKER_TTL_S = 300     # 5min OPEN, ×3=15min HALF_OPEN
RUN_MODE = "live"                    # 'live' o 'replay'
```

---

## LO QUE PEDIMOS QUE HAGAS

### 1. Fix crítico: HIKERAPI_COST_PER_CALL_USD

El archivo `packages/shared-core/shared_core/config.py` tiene:
```python
HIKERAPI_COST_PER_CALL_USD: float = 0.0006  # ← LEGACY
```

**Debe ser:**
```python
HIKERAPI_COST_PER_CALL_USD: float = 0.02  # Plan Start real
```

Esto hace que BudgetFuse funcione correctamente con el plan real.

**Verifica:** Busca `HIKERAPI_COST_PER_CALL_USD` en todo el codebase y actualiza en todos los lugares donde se use como hardcoded value.

### 2. Análisis exhaustivo de costos

Calcula para cada configuración:

| Config | Discovery | Enrichment | Total req | Costo/run | Runs $10/mes |
|--------|-----------|------------|-----------|-----------|--------------|
| Completo (50 enrich) | 31 | 50 | 81 | $1.62 | ~6 |
| Reducido (25 enrich) | 31 | 25 | 56 | $1.12 | ~8 |
| Mínimo (10 enrich) | 31 | 10 | 41 | $0.82 | ~12 |
| Discovery only | 31 | 0 | 31 | $0.62 | ~16 |

**Pregunta:** ¿cuál es el Sweet Spot entre costo y calidad de candidatos?

### 3. Estrategias de optimización de costos

Evalúa estas estrategias con datos concretos:

a) **Reducir MAX_HANDLES_TO_ENRICH a 25 o 10** — ¿cuántos candidatos de calidad se pierden?
b) **Priorizar enrichment solo para perfiles con geo_score > threshold** — ya tenemos la data antes de enrichment
c) **Cachear resultados de enrichment** — ¿feasible? ¿cuál TTL?
d) **Discovery only (sin enrichment)** — ¿los candidatos de keyword/topsearch son suficientemente completos?
e) **DeepSeek solo para top N candidatos** — ¿reduce costo significativamente?

### 4. Validación de Hitos 13-20 + Bonus 1

Confirma que estos cambios están correctos:

- **Hito 13** (`a9cbb78`): `enqueue_job` check `job is None` + log `discovery_run_enqueue_deduped`
- **Hito 14** (`6fd29b1`): `record_call` en todas las HTTP responses (404, 4xx, 5xx, 2xx)
- **Hito 15** (`f3735b2`): Lua script `reserve_and_record` atómico en BudgetFuse
- **Hito 16** (`bad1d37`): `is_private` en perfiles de hashtag y keyword search
- **Hito 17** (`a91e76d`): `business_unit_id` del usuario autenticado en campaigns
- **Hito 18** (`b5e404e`): 3 JSONB cols en `discovery_profiles` + defaults
- **Hito 19** (`a5da503`): LRU/TTL en `orchestrator.state`
- **Hito 20** (`611d22e`): test_hashtag_cap_30 + test_result_ranker.py borrado
- **Bonus** (`880da7d`): `replay_miss_count` en metadata

### 5. Ejecuta pytest

```bash
pytest apps/api/tests/test_pipeline_smoke.py apps/api/tests/test_universal_verticals.py -v
```

Reporta: **33/33 pass**

### 6. Dashboard de observabilidad

¿Qué métricas mínimo viables necesitamos?

- `budget_fuse_monthly_spent` vs `MONTHLY_BUDGET_USD`
- `budget_fuse_run_requests` vs `MAX_CALLS_PER_RUN`
- `circuit_breaker_state` (CLOSED/OPEN/HALF_OPEN)
- `discovery_run_status` (completed/partial/failed)
- `replay_miss_count` (diagnóstico de modo replay)

---

## LO QUE ESPERAMOS DE TI

Sé brutalmente honesto. Enfócate en:

### Prioridad 1 — Fix de costo HIKERAPI
- [ ] Cambia `HIKERAPI_COST_PER_CALL_USD` a `$0.02` en `config.py`
- [ ] Verifica que no haya otros hardcoded $0.0006 en el codebase
- [ ] Confirma que BudgetFuse ahora muestra números reales

### Prioridad 2 — Análisis de costos
- [ ] Tabla completa de costo por fase (ya la tienes en ARQUITECTURA_LENS.md v3.3)
- [ ] Sweet spot: ¿cuántos enrichment calls valen la pena con $10/mes?
- [ ] Estrategia de optimización concreta (una o dos que sean implementables en 1-2 días)

### Prioridad 3 — Validación de código
- [ ] 33/33 tests pass
- [ ] Lua script de `reserve_and_record` está bien
- [ ] El replay mode funciona correctamente (nunca hace network call en modo replay)

### Prioridad 4 — Producto listo
- [ ] ¿Está el sistema listo para producción con créditos reales de HikerAPI Start?
- [ ] ¿Cuántos runs de prueba podemos hacer con $20 de balance prepago?
- [ ] ¿Cuándo debemos alertar al usuario que recargue?

---

## CÓMO EMPEZAR ESTA AUDITORÍA

1. Lee `docs/ARQUITECTURA_LENS.md` (v3.3 — tiene el análisis de costos completo)
2. Lee `packages/shared-core/shared_core/config.py` → busca `HIKERAPI_COST_PER_CALL_USD`
3. Cambia el valor a `$0.02` y verifica que todo compile
4. Lee `apps/api/app/core/budget_fuse.py` → verifica el Lua script
5. Ejecuta `pytest apps/api/tests/test_pipeline_smoke.py apps/api/tests/test_universal_verticals.py`
6. Reporta: costo real por run, runs posibles con $10/mes, y si el sistema está listo para producción

**Sé directo, sé brutal en honestidad, enfócate en soluciones prácticas.**

---

*Documento generado: 2026-08-17 — Quinta auditoría LENS post-Hitos 1-20 + Bonus 1*
*Para: Claude Code Opus 5 / Senior Full-Stack Developer*
