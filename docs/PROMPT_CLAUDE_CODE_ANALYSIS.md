# Segunda Auditoría — LENS Discovery Module (Post-Fixes)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Solicitud:** **SEGUNDA AUDITORÍA** — la primera auditoría (2026-08-14) identificó 7 issues críticos; los hitos 1–7 fueron aplicados y commitados. Pedimos que validen los fixes, identifiquen regresiones y propongan los próximos mejoras.
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI + DeepSeek

---

## OBJETIVO

La primera auditoría de LENS encontró que **$50-72 USD se consumieron en 2 días** por bugs evitables. Ejecutamos 7 hitos de fix:

| Hito | Commit | Desc |
|------|--------|------|
| 1 | `be32a39` | Elimina Apify (roto), step2p6 (roto), prefilter muerto |
| 2 | `835bf2a` | Excepciones `SourceUnavailable`/`TransientSourceError` que propagan |
| 3+4 | `4819857` | `BudgetFuse` + `HikerAPICircuitBreaker` |
| 5 | `766cfee` | ARQ idempotency key `discovery:{run_id}` |
| 6 | `2da78ab` | `is_private` en merge + cache TTL 30min |
| 7 | `9b43316` | Documentación actualizada |

**Pedimos:**
1. Validar que los fixes no introdujeron regressions
2. Identificar los issues que quedaron abiertos
3. Proponer la siguiente tanda de mejoras priorizadas

---

## ESTRUCTURA DEL PROYECTO

```
lawebcore/
├── apps/
│   ├── api/                              # FastAPI backend (Railway)
│   │   └── app/
│   │       ├── api/v1/                  # 40+ endpoints
│   │       ├── core/
│   │       │   ├── budget_fuse.py       # ★ nuevo — budget enforcement
│   │       │   ├── hikerapi_circuit_breaker.py  # ★ nuevo
│   │       │   └── worker_enqueuer.py   # ★ actualizado — _job_id
│   │       ├── models/                  # SQLAlchemy ORM
│   │       ├── services/                # AI services
│   │       └── workers/
│   │           └── worker.py            # ~1760 líneas
│   └── web/                             # React 19 frontend (Vercel)
├── packages/
│   ├── discovery/                        # ★ LENS Discovery Module
│   │   └── discovery/
│   │       ├── exceptions.py           # ★ nuevo — SourceUnavailable, TransientSourceError, BudgetExhausted
│   │       ├── orchestrator.py
│   │       ├── brief_parser.py
│   │       ├── profile_generator.py
│   │       ├── candidate_analyzer.py
│   │       ├── query_builder.py
│   │       ├── memory.py
│   │       ├── result_ranker.py
│   │       ├── scoring/
│   │       │   ├── lens_score.py
│   │       │   ├── geo_boost.py        # geo_score here
│   │       │   └── niche.py
│   │       └── tools/
│   │           ├── hikerapi_client.py  # ★ actualizado — exceptions + breaker + cache
│   │           ├── hikerapi_circuit_breaker.py  # ★ nuevo
│   │           ├── instagram_source.py
│   │           └── metricool_client.py
│   ├── shared-core/
│   └── shared-ai/
├── supabase/migrations/
│   └── 00000000000104_discovery_run_partial_status.sql  # ★ nuevo
└── docs/
    ├── ARQUITECTURA_LENS.md            # v3.0 post-auditoría
    └── LENS_REVIEW_ARQUITECTURA_2026-08-14.md  # auditoría original
```

**Archivos eliminados en Hito 1:** `apify_instagram_source.py`, `source_registry.py`.

---

## ESTADO ACTUAL POST-FIXES

### Lo que SE arregló

```
✅ 4xx/5xx ya no se swallow como warning — propagan como excepciones
✅ BudgetFuse: monthly cap $10 USD + per-run limit 120 calls + 70% alert
✅ CircuitBreaker: 5xx consecutive → OPEN, TTL 300s, Redis-backed
✅ ARQ idempotency: _job_id=discovery:{run_id} — no más doble cobro por redeploy
✅ step2p6 follower expansion ELIMINADO (gastaba 1 enrich por run y devolvía vacío)
✅ Apify ELIMINADO (estaba roto, no era fallback funcional)
✅ Prefiltro muerto ELIMINADO (30 líneas + logs engañosos)
✅ search_hashtag_recent ahora con cache_ttl=1800 (30 min vs 0)
✅ is_private preservado en el merge de enrichment
✅ discovery_run_status enum: valor 'partial' añadido (migración lista para ejecutar)
```

### Lo que NO se arregló (abierto)

```
⚠️  Enriquecimiento decide sobre muestra casi aleatoria — decide el gasto ANTES de tener datos
⚠️  geo_score con bugs visibles en tests (city matching, country disqualification)
⚠️  Vocabulario de negocio hardcodeado en worker.py (~150 líneas en español)
⚠️  Estado del orchestrator en memoria — columna state existe y no se usa
⚠️  Multi-tenancy inexistente — bloquea segundo cliente
⚠️  La migración 00000000000104 NO se ha ejecutado aún en producción
```

---

## PIPELINE ACTUAL (worker.py ~1760 líneas)

```
1. build brief → DeepSeek parsea brief_text → BriefStructured
2. QueryBuilder genera plan: hashtags, keywords, reels, topsearch, suggested
3. _fetch_step1 (hashtag top, 3)     → enrich: NO (usuario reducido)
4. _fetch_step1_recent (hashtag, 2)  → enrich: NO (usuario reducido)  [TTL=30min]
5. _fetch_step2 (keyword, 3×3)        → enrich: SÍ (perfil completo)
6. _fetch_step2p5 (reels, 1)         → enrich: NO (usuario reducido)
7. _fetch_step3 (topsearch, 1)       → enrich: SÍ (perfil completo)
8. _fetch_step4 (suggested, 1)        → enrich: SÍ (perfil completo)
9. PREFILTRO: se seleccionan hasta MAX_HANDLES_TO_ENRICH handles
              ⚠️ PROBLEMA: scoring se hace sin bio ni seguidores
10. ENRICHMENT: enrich_profile() por handle
                - circuit_breaker.can_proceed() → si OPEN aborta
                - budget_fuse.record_call() después de cada llamada
                - hasta MAX_CALLS_PER_RUN=120
11. SCORING: lens_score, geo_score, niche_relevance
12. CANDIDATE_ANALYZER: DeepSeek (si analyze_with_ai=true)
13. upsert_many → PostgreSQL
```

---

## CONSTANTES ACTUALES ( worker.py )

```python
MAX_HANDLES_TO_ENRICH = 50
MAX_POSTS_PER_HASHTAG = 20
ENRICHMENT_INCLUDE_ABOUT = False   # desactivado por defecto
HASHTAGS_TOP = 3
HASHTAGS_RECENT = 2
KEYWORDS = 3
TOP_SEARCH = 1
SUGGESTED_SEEDS = 1
REELS_KEYWORDS = 1
```

**Nuevas vars de entorno (Settings en shared_core):**
```python
MONTHLY_BUDGET_USD = 10.0          # corte mensual hard
MAX_CALLS_PER_RUN = 120            # por-run
BUDGET_ALERT_THRESHOLD = 0.7       # warn al 70%
HIKERAPI_COST_PER_CALL_USD = 0.0006
HIKERAPI_5XX_BREAKER_THRESHOLD = 5
HIKERAPI_5XX_BREAKER_TTL_S = 300
```

---

## PREGUNTAS PARA CLAUDE CODE — SEGUNDA AUDITORÍA

### A. Validación de fixes

1. ¿Los 7 hitos aplicados son correctos y completos? ¿Hay edge cases donde pueden fallar?
2. El circuit breaker se instancia DENTRO de `_get()` de hikerapi_client — ¿esto crea un nuevo estado por cada llamada o comparten estado vía Redis correctamente?
3. `BudgetFuse.assert_budget_available()` se llama ANTES del gather de enrichment, pero `record_call()` está dentro de `_enrich_one()`. Si una excepción ocurre después de `assert_budget_available()` pero antes de `record_call()`, ¿el costo no se registra? ¿Es eso un bug?
4. El `_job_id` de ARQ usa `discovery:{run_id}`. ¿ARQ deduplica solo jobs pending/running o también completed? Si un run falla Y se reintenta manualmente, ¿se permite?

### B. Scoring — bugs abiertos

5. Los tests de smoke fallan en `geo_score`: perfiles CO con `geo_indicators=["bogota","medellin"]` obtienen score 0.0 cuando el país del perfil es CO. ¿Está `geo_score` bien implementada?
6. El test `test_no_ve_artifacts_in_non_ve_profile` falla: perfil CO con `geo_indicators=["colombia","bogota","medellin"]` devuelve `geo=0.0`. ¿El problema es en `geo_score` o en el test?
7. ¿Cómo recalibrar `geo_score`, `lens_score` y `niche_relevance` para que funcionen correctamente con el flujo actual?

### C. Arquitectura — issues abiertos

8. El vocabulario de negocio está hardcodeado en worker.py (~150 líneas de listas en español). ¿Cuál es la forma más limpia de externalizarlo a `discovery_profiles` sin romper el pipeline actual?
9. El estado del orchestrator vive en memoria (se pierde al reiniciar). ¿Deberíamos usar la columna `state` de `discovery_conversations` o hay una solución más simple?
10. Multi-tenancy: ¿cuál es el approach correcto — filtrado por `business_unit_id` en todas las queries, o un rol de base separado?

### D. Siguiente tanda de fixes

11. ¿Cuáles de los issues abiertos deberían resolverse ANTES deputar a producción con un segundo cliente?
12. ¿Vale la pena implementar un "modo replay" (costo $0) para iterar scoring sin gastar llamadas? ¿cómo debería funcionar?
13. ¿Cómo debería verse un dashboard de observabilidad mínimo viable para el pipeline?

---

## LO QUE ESPERAMOS DE TI — SEGUNDA PASADA

Sé brutalmente honesto. Enfócate en:

### Validación (urgente antes de recarga de créditos)
- [ ] ¿Los fixes de los hitos 1-7 son correctos o tienen bugs sutiles?
- [ ] ¿El circuit breaker y budget fuse se implementaron bien o hay race conditions?

### Scoring y calidad (bloquea la utilidad del producto)
- [ ] Diagnóstico completo de `geo_score` — ¿por qué fallan los tests?
- [ ] ¿Cómo debería funcionar el prefilter para que no sea "casi aleatorio"?

### Arquitectura (siguiente sprint)
- [ ] Plan concreto para externalizar el vocabulario de negocio
- [ ] Decisión: ¿usar la columna `state` o implementar un redis-based state?

### Producto listo para escalar (multi-cliente)
- [ ] Plan de multi-tenancy que no destruya el rendimiento
- [ ] Dashboard de costos mínimo viable

---

## RECURSOS

### Archivos clave para esta auditoría

| Archivo | Líneas | Relevancia |
|---|---|---|
| `apps/api/app/workers/worker.py` | ~1760 | Pipeline completo, budget/breaker integrados |
| `packages/discovery/discovery/tools/hikerapi_client.py` | ~770 | Circuit breaker + cache TTL |
| `packages/discovery/discovery/exceptions.py` | 60 | Nuevo — excepciones del pipeline |
| `packages/discovery/discovery/scoring/geo_boost.py` | — | geo_score con bugs en tests |
| `packages/discovery/discovery/scoring/lens_score.py` | — | lens_score weights |
| `apps/api/app/core/budget_fuse.py` | 183 | Budget enforcement |
| `packages/discovery/discovery/tools/hikerapi_circuit_breaker.py` | 161 | Circuit breaker |
| `apps/api/app/core/worker_enqueuer.py` | 63 | ARQ idempotency |
| `supabase/migrations/00000000000104_...sql` | 11 | Enum partial — **ejecutar manualmente** |
| `docs/ARQUITECTURA_LENS.md` | — | Arquitectura v3.0 completa |

### Información del proyecto
- **Cliente actual:** Nestlé Venezuela / Purina Dog Chow
- **Budget objetivo:** < $10 USD/mes
- **Performance target:** Run completa en < 3 min, < 120 API calls
- **Decisión de arquitectura:** short-term fixes — no se reactivó Apify

---

## CÓMO EMPEZAR ESTA AUDITORÍA

1. Lee `docs/ARQUITECTURA_LENS.md` (v3.0 — refleja el estado actual)
2. Lee `apps/api/app/workers/worker.py` — enfócate en las secciones de budget_fuse, circuit_breaker y enrichment
3. Lee `packages/discovery/discovery/scoring/geo_boost.py` — busca el bug que hace fallar los tests
4. Revisa `packages/discovery/discovery/tools/hikerapi_client.py:_get()` — valida el circuit breaker integration
5. Identifica gaps en los fixes aplicados y propone los próximos hitos

**Sé directo, sé brutal en honestidad, enfócate en soluciones prácticas.**

---

*Documento generado: 2026-08-14 — Segunda auditoría post-LENS fixes*
*Para: Claude Code Opus 5 / Senior Full-Stack Developer*
