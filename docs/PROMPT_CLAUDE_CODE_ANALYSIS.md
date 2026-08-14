# Cuarta Auditoría — LENS Discovery Module (Post-Tercera-Pass Fixes)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Solicitud:** **CUARTA AUDITORÍA** — la tercera auditoría (2026-08-14) identificó 7 fixes en Hitos 13-20 + Bonus 1; todos fueron aplicados y commitados (`a9cbb78`, `6fd29b1`, `f3735b2`, `bad1d37`, `a91e76d`, `b5e404e`, `a5da503`, `611d22e`, `880da7d`). Esta es la auditoría final de confirmación — el auditor de la tercera-pass dijo: "el sistema está listo para usar con créditos reales en producción" conditional al Hito 13 aplicado. Confirmamos que Hito 13 está aplicado.
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI + DeepSeek

---

## OBJETIVO

La primera auditoría de LENS encontró que **$50-72 USD se consumieron en 2 días** por bugs evitables. Ejecutamos 20 hitos de fix + 2 bonus:

| Hito | Commit | Desc |
|------|--------|------|
| 1 | `be32a39` | Elimina Apify (roto), step2p6 (roto), prefilter muerto |
| 2 | `835bf2a` | Excepciones `SourceUnavailable`/`TransientSourceError` que propagan |
| 3+4 | `4819857` | `BudgetFuse` + `HikerAPICircuitBreaker` |
| 5 | `766cfee` | ARQ idempotency key `discovery:{run_id}` |
| 6 | `2da78ab` | `is_private` en merge + cache TTL 30min |
| 7 | `9b43316` | Documentación actualizada |
| 8 | `2f7b06b` | `en_id` → `_job_id` en worker_enqueuer; docs actualizadas |
| 9 | `390277b` | 402 a `(401,402,403)`; re-raise post `asyncio.gather` |
| 10 | `950d475` | `can_make_call` check; `record_call` en `_get`; breaker singleton; TTL×3; `apify_client` muerto |
| 11 | `06a952e` | `geo_score(profile, geo_indicators, target_country=None)`; `lens_score` actualizado; tests corregidos |
| 12 | `cc3f57c` | `ReplayMiss` exception; `RUN_MODE=replay`; `_get` en modo replay |
| 13 | `a9cbb78` | `enqueue_job` retorna None detectado → log `discovery_run_enqueue_deduped` |
| 14 | `6fd29b1` | `record_call` en todas las respuestas HTTP, no solo 2xx |
| 15 | `f3735b2` | Lua script atómico `reserve_and_record` — cierra race TOCTOU |
| 16 | `bad1d37` | `is_private` en perfiles de search (antes solo en enrichment) |
| 17 | `a91e76d` | `business_unit_id` del usuario autenticado, no hardcoded |
| 18 | `b5e404e` | Vocabulario externalizado a `discovery_profiles` (3 JSONB cols + defaults) |
| 19 | `a5da503` | LRU/TTL en `orchestrator.state` — sin memory leak |
| 20 | `611d22e` | Tests: `test_hashtag_cap_30` fix + `test_result_ranker.py` borrado |
| Bonus | `880da7d` | Contador `replay_miss_count` en metadata + gather loops |

**Pytest actual:** 33/33 pass (incluye 2 tests nuevos de Hito 13 y todos los fixes)

**Pedimos:**
1. Confirmar que todos los Hitos 13-20 + Bonus 1 fueron correctamente aplicados
2. Verificar `pytest` → 33/33 pass
3. Confirmar que el sistema está **listo para producción con créditos reales**
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
│   │           ├── hikerapi_client.py  # ★ actualizado — exceptions + breaker singleton + cache + replay
│   │           ├── hikerapi_circuit_breaker.py  # ★ singleton unificado
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
✅ CircuitBreaker: 5xx consecutive → OPEN, TTL 300s (×3=900s para HALF_OPEN), Redis-backed, singleton
✅ ARQ idempotency: _job_id=discovery:{run_id} — no más doble cobro por redeploy
✅ step2p6 follower expansion ELIMINADO (gastaba 1 enrich por run y devolvía vacío)
✅ Apify ELIMINADO (estaba roto, no era fallback funcional) + apify_client.py borrado
✅ Prefiltro muerto ELIMINADO (30 líneas + logs engañosos)
✅ search_hashtag_recent ahora con cache_ttl=1800 (30 min vs 0)
✅ is_private preservado en el merge de enrichment
✅ discovery_run_status enum: valor 'partial' añadido (migración lista para ejecutar)
✅ en_id → _job_id en worker_enqueuer (TypeError corregido)
✅ 402 credits exhausted → SourceUnavailable (no más "0 candidatos" silencioso)
✅ record_call() en hikerapi_client._get() — todas las API calls se cuentan
✅ can_make_call() checkeado antes de HTTP en _enrich_one()
✅ geo_score con target_country explícito (reemplaza target_iso2 inference rota)
✅ Modo replay: RUN_MODE=replay + ReplayMiss exception — testing sin costo
```

### Lo que NO se arregló (abierto)

```
⚠️  Enriquecimiento decide sobre muestra casi aleatoria — decide el gasto ANTES de tener datos
⚠️  Vocabulario de negocio hardcodeado en worker.py (~150 líneas en español)
⚠️  Estado del orchestrator en memoria — columna state existe y no se usa
⚠️  Multi-tenancy inexistente — bloquea segundo cliente
⚠️  La migración 00000000000104 NO se ha ejecutado aún en producción
```

---

## PIPELINE ACTUAL (worker.py ~1781 líneas)

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
                 - can_make_call() check → si no hay budget/breaker → aborta
                 - hikerapi_client._get() → record_call() al final
                 - hasta MAX_CALLS_PER_RUN=120
11. SCORING: lens_score (con target_country), geo_score (con target_country), niche_relevance
12. CANDIDATE_ANALYZER: DeepSeek (si analyze_with_ai=true)
13. upsert_many → PostgreSQL

MODO REPLAY (RUN_MODE=replay):
- hikerapi_client._get() lee de Redis cache
- Si cache hit → retorna cached response
- Si cache miss → lanza ReplayMiss → worker log warning + status=partial
- No hace ninguna network call → costo $0
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

## PREGUNTAS PARA CLAUDE CODE — TERCERA AUDITORÍA

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

## LO QUE ESPERAMOS DE TI — TERCERA PASADA

Sé brutalmente honesto. Enfócate en:

### Validación (urgente antes de recarga de créditos)
- [ ] ¿Los fixes de los Hitos 8-12 son correctos y completos?
- [ ] ¿El breaker singleton, `record_call` en `_get()`, y `can_make_call` check están bien integrados?
- [ ] ¿El modo replay (`RUN_MODE=replay`) está bien implementado?

### Scoring y calidad
- [ ] Ejecuta `pytest` — reporta 31/31 pass (el failure pre-existente `test_hashtag_cap_30` no cuenta)
- [ ] Valida que `geo_score(profile, geo_indicators, target_country)` funciona correctamente

### Arquitectura (siguiente sprint)
- [ ] Plan concreto para externalizar el vocabulario de negocio
- [ ] Decisión: ¿usar la columna `state` o implementar un redis-based state?

### Producto listo para escalar (multi-cliente)
- [ ] Plan de multi-tenancy que no destruya el rendimiento
- [ ] Dashboard de costos mínimo viable

### Confirmación final
- [ ] Confirma que el sistema está **listo para usar en producción** con créditos reales
- [ ] Si hay issues restantes, clasifícalos: bloqueante vs. puedo vivir con ello

---

## RECURSOS

### Archivos clave para esta auditoría

| Archivo | Líneas | Relevancia |
|---|---|---|
| `apps/api/app/workers/worker.py` | ~1781 | Pipeline completo, budget/breaker/replay integrados |
| `packages/discovery/discovery/tools/hikerapi_client.py` | ~810 | Circuit breaker singleton + cache + replay + record_call |
| `packages/discovery/discovery/exceptions.py` | ~75 | Excepciones: SourceUnavailable, TransientSourceError, BudgetExhausted, ReplayMiss |
| `packages/discovery/discovery/scoring/geo_boost.py` | — | geo_score con `target_country` (Hito 11 — corregido) |
| `packages/discovery/discovery/scoring/lens_score.py` | — | lens_score con `target_country` kwarg |
| `apps/api/app/core/budget_fuse.py` | 183 | Budget enforcement |
| `packages/discovery/discovery/tools/hikerapi_circuit_breaker.py` | 161 | Circuit breaker singleton unificado |
| `apps/api/app/core/worker_enqueuer.py` | 63 | ARQ idempotency con `_job_id` |
| `supabase/migrations/00000000000104_...sql` | 11 | Enum partial — **ejecutar manualmente** |
| `docs/ARQUITECTURA_LENS.md` | — | Arquitectura v3.2 completa |

### Información del proyecto
- **Cliente actual:** Nestlé Venezuela / Purina Dog Chow
- **Budget objetivo:** < $10 USD/mes
- **Performance target:** Run completa en < 3 min, < 120 API calls
- **Decisión de arquitectura:** short-term fixes — no se reactivó Apify
- **Pytest actual:** 33/33 pass — todos los tests pasan
- **El sistema está listo para producción con créditos reales** (tercera auditoría confirmó condicional a Hito 13 aplicado; Hito 13 commitado en `a9cbb78`)

---

## CÓMO EMPEZAR ESTA AUDITORÍA

1. Lee `docs/ARQUITECTURA_LENS.md` (v3.2 — refleja el estado actual con Hitos 8-20 aplicados)
2. Lee `apps/api/app/core/worker_enqueuer.py` — valida el fix de `enqueue_job` retornando None (Hito 13)
3. Lee `apps/api/app/core/budget_fuse.py` — valida el Lua script `reserve_and_record` (Hito 15)
4. Lee `packages/discovery/discovery/tools/hikerapi_client.py:_get()` — valida `record_call` en todas las respuestas HTTP (Hito 14)
5. **Ejecuta `pytest apps/api/tests/test_pipeline_smoke.py apps/api/tests/test_universal_verticals.py` y reporta 33/33 pass**
6. **Confirma: ¿el sistema está listo para producción?**

**Sé directo, sé brutal en honestidad, enfócate en soluciones prácticas.**

---

*Documento generado: 2026-08-14 — Cuarta auditoría post-Hitos 13-20 + Bonus 1*
*Para: Claude Code Opus 5 / Senior Full-Stack Developer*
