# QUINTA AUDITORÍA — LENS Discovery Module (Post-Hito 21)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Solicitud:** **QUINTA AUDITORÍA EXHAUSTIVA** — el sistema tiene 21 hitos + Bonus 1 aplicados. La auditoría 5 de Opus 5 identificó bugs críticos en el modelo de contabilidad. Hito 21 se aplicó para corregirlos. Necesitamos que valides los fixes yconfirmes que el sistema está listo para producción.
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI "Start" ($0.02/req) + DeepSeek

---

## ESTADO ACTUAL — POST-HITO 21

```
╔══════════════════════════════════════════════════════════════════╗
║  HIKERAPI "START" — $0.02 USD por request              ║
╠══════════════════════════════════════════════════════════════════╣
║  Costo por request:   $0.02 USD                              ║
║  Balance prepago:    $20 USD (~1,000 requests)               ║
║  Todos los endpoints de Instagram incluidos (100+)           ║
║                                                                  ║
║  ✅ CONFIGURACIÓN ACTUAL (post Hito 21):               ║
║     HIKERAPI_COST_PER_CALL_USD = 0.02                     ║
║     BudgetFuse funcionando con costo real                  ║
║     Single accounting point en HikerAPIClient._get()      ║
║                                                                  ║
║  🔧 FIXES APLICADOS EN HITO 21:                        ║
║     §2.1 Doble conteo: eliminado                          ║
║     §2.2 Caché cobraba: eliminado                          ║
║     §2.3 NOSCRIPT sin fallback: corregido                  ║
║     §2.4 Fail-open peligroso: fail-closed                  ║
║     §2.5 MAX_CALLS_PER_RUN decorativo: ahora real         ║
╚══════════════════════════════════════════════════════════════════╝

PRESUPUESTO OBJETIVO: < $10 USD/mes

ESCENARIOS REALES CON $0.02/req:
  Run completo (81 requests): $1.62 USD  →  ~6 runs/mes con $10
  Run sin enrichment (31 req): $0.62 USD  →  ~16 runs/mes con $10
  Run parcial cache (56 req): $1.12 USD  →  ~8 runs/mes con $10
```

---

## OBJETIVO

Ejecutamos 21 hitos + 1 bonus de fixes. El sistema pasa 33/33 tests + tests de Hito 21. **El modelo de contabilidad ahora es correcto** — un solo punto de cobro en `HikerAPIClient._get()`.

**Pedimos:**
1. Validar que los 21 hitos + Bonus 1 fueron correctamente aplicados
2. Hacer análisis de costos detallado: ¿cuántos requests por fase? ¿cómo optimizar?
3. Proponer estrategias de reducción de costo sin perder calidad
4. Verificar `pytest` → 33/33 + nuevos tests
5. Confirmar que el sistema está listo para producción con créditos reales
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

### 1. ✅ FIX YA APLICADO: HIKERAPI_COST_PER_CALL_USD + Modelo de Contabilidad

**Archivos tocados por Hito 21:**
- `apps/api/app/core/budget_fuse.py` — NOSCRIPT fallback + fail-closed + docstring
- `packages/discovery/discovery/tools/hikerapi_client.py` — single accounting point en `_get()`
- `apps/api/app/workers/worker.py` — remueve `reserve_and_record` redundante, propaga `BudgetExhausted`, run `partial` al alcanzar tope

**Verificación pendiente:**
```bash
pytest apps/api/tests/test_budget_fuse.py -v
```
Esperado: 8 tests passing (5 nuevos + 3 existentes)

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

### 4. Validación de Hitos 13-21 + Bonus 1

Confirma que estos cambios están correctos:

- **Hito 13** (`a9cbb78`): `enqueue_job` check `job is None` + log `discovery_run_enqueue_deduped`
- **Hito 14** (`6fd29b1`): `record_call` en todas las HTTP responses (404, 4xx, 5xx, 2xx)
- **Hito 15** (`f3735b2`): Lua script `reserve_and_record` atómico en BudgetFuse
- **Hito 16** (`bad1d37`): `is_private` en perfiles de hashtag y keyword search
- **Hito 17** (`a91e76d`): `business_unit_id` del usuario autenticado en campaigns
- **Hito 18** (`b5e404e`): 3 JSONB cols en `discovery_profiles` + defaults
- **Hito 19** (`a5da503`): LRU/TTL en `orchestrator.state`
- **Hito 20** (`611d22e`): test_hashtag_cap_30 + test_result_ranker.py borrado
- **Hito 21** (aplicado): Single accounting point + NOSCRIPT fallback + fail-closed
- **Bonus** (`880da7d`): `replay_miss_count` en metadata

### 5. Ejecuta pytest

```bash
pytest apps/api/tests/test_pipeline_smoke.py apps/api/tests/test_universal_verticals.py apps/api/tests/test_budget_fuse.py -v
```

Reporta: **33/33 + 8 tests de Hito 21 = ~41 pass**

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

### Prioridad 1 — ✅ FIX YA APLICADO (Hito 21)
- [x] `HIKERAPI_COST_PER_CALL_USD` = `$0.02` en `config.py`
- [x] BudgetFuse con single accounting point en `HikerAPIClient._get()`
- [x] NOSCRIPT fallback implementado
- [x] Fail-closed ante error de Redis

### Prioridad 2 — Análisis de costos
- [ ] Sweet spot: ¿cuántos enrichment calls valen la pena con $10/mes?
- [ ] Estrategia de optimización concreta (Hito 23: apagar hashtag-top/recent/reels)

### Prioridad 3 — Validación de código
- [ ] 33/33 + tests de Hito 21 pasan
- [ ] Lua script de `reserve_and_record` está bien
- [ ] El replay mode funciona correctamente (nunca hace network call en modo replay)

### Prioridad 4 — Producto listo
- [ ] Validar fail-fast con saldo agotado (run termina en `failed` con mensaje de recarga)
- [ ] ¿Cuántos runs de prueba podemos hacer con $20 de balance prepago?
- [ ] ¿Cuándo debemos alertar al usuario que recargue?

---

## CÓMO EMPEZAR ESTA AUDITORÍA

1. Lee `docs/ARQUITECTURA_LENS.md` (v3.4 — tiene el análisis de costos completo + Hito 21)
2. Lee `docs/HITO21_CAMBIOS.md` → entender qué se arregló
3. Ejecuta `pytest apps/api/tests/test_pipeline_smoke.py apps/api/tests/test_universal_verticals.py apps/api/tests/test_budget_fuse.py -v`
4. Valida fail-fast: encola un run con saldo agotado → debe terminar en `failed` con mensaje claro
5. Reporta: costo real por run, runs posibles con $10/mes, y si el sistema está listo para producción

**Sé directo, sé brutal en honestidad, enfócate en soluciones prácticas.**

---

*Documento generado: 2026-08-17 — Quinta auditoría LENS post-Hitos 1-21 + Bonus 1*
*Para: Claude Code Opus 5 / Senior Full-Stack Developer*
