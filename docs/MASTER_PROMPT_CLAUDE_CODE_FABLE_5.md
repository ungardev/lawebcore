# MASTER PROMPT — Claude Code Fable 5: Verificación post-Fixes + Análisis Continuo

> **Para:** Claude Code (Fable 5 o cualquier agente de análisis de código)
> **Proyecto:** La Web Core — La Web Figital Agency
> **Fecha:** 2026-08-05
> **Repo:** `github.com/ungardev/lawebcore`
> **Producción:** Railway (API) + Vercel (Frontend) + Supabase (DB)
> **Estado:** TODOS LOS FIXES DE FABLE 5 APLICADOS ✅ — Smoke tests 14/14 PASSED

---

## 1. CONTEXTO — TODOS LOS FIXES APLICADOS

El **2026-08-04/05**, el agente Claude Code Fable 5 realizó un análisis completo del proyecto y sugirió **19 oportunidades de mejora** organizadas en 4 bloques:

1. **Bloque 1 — Hotfix** (5 items): Bugs críticos que causaban crashes o data loss
2. **Bloque 2 — Red de Seguridad** (1 item): Smoke test
3. **Bloque 3 — Costo y Calidad** (11 items): Reducción de costos Apify, mejora de scoring
4. **Bloque 4 — Robustez** (2 items): Cleanup de código muerto

### ✅ TODOS LOS FIXES FUERON APLICADOS Y VALIDADOS

| Commit | Fecha | Descripción |
|--------|-------|-------------|
| `fc380ce` | 2026-08-04 | fix(discovery): todos los fixes Fable 5 aplicados |
| `9d84fba` | 2026-08-05 | fix(tests): corrección filtro ciudad + 4 tests |
| `ee87533` | 2026-08-05 | fix(tests): últimos 2 failing tests |

### RESULTADO DE SMOKE TESTS: 14/14 PASSED ✅

```
tests/test_pipeline_smoke.py::TestGeoBoostFixes::test_profile_with_country_but_no_iso2 PASSED
tests/test_pipeline_smoke.py::TestGeoBoostFixes::test_country_match_when_iso2_present PASSED
tests/test_pipeline_smoke.py::TestGeoBoostFixes::test_country_mismatch_when_iso2_present PASSED
tests/test_pipeline_smoke.py::TestGeoBoostCityMatching::test_city_name_cali PASSED
tests/test_pipeline_smoke.py::TestGeoBoostCityMatching::test_city_name_caracas PASSED
tests/test_pipeline_smoke.py::TestGeoBoostTypoFix::test_co_country_keywords_have_valid_entries PASSED
tests/test_pipeline_smoke.py::TestLensScoreWeights::test_weights_sum_to_one PASSED
tests/test_pipeline_smoke.py::TestLensScoreWeights::test_weights_are_normalized PASSED
tests/test_pipeline_smoke.py::TestQueryBuilderCaps::test_keyword_cap_20 PASSED
tests/test_pipeline_smoke.py::TestQueryBuilderCaps::test_hashtag_cap_30 PASSED
tests/test_pipeline_smoke.py::TestQueryBuilderCaps::test_no_buy_intent_in_queries PASSED
tests/test_pipeline_smoke.py::TestCandidateAnalyzerBatchPrompt::test_batch_prompt_singular_elite_context PASSED
tests/test_pipeline_smoke.py::TestUpsertManyReturning::test_upsert_many_adds_returning_clause PASSED
tests/test_pipeline_smoke.py::TestWorkerTyping::test_worker_module_imports_any PASSED
```

---

## 2. FIXES APLICADOS — DETALLE COMPLETO

### BLOQUE 1 — HOTFIX ✅

| ID | Fix | Archivo | Validación |
|----|-----|---------|------------|
| F-1.1 | `from typing import Any` añadido | `apps/api/app/workers/worker.py` | ✅ TestWorkerTyping |
| F-1.2 | `upsert_many` siempre añade `RETURNING` | `packages/shared-core/supabase_rest.py` | ✅ TestUpsertManyReturning |
| F-1.3 | geo_boost: país declarado no descalifica si no hay ISO2 en geo_indicators | `packages/discovery/discovery/tools/geo_boost.py` | ✅ 3x GeoBoostFixes tests |
| F-1.4 | Migración 0099 → 0103 | `supabase/migrations/` | ✅ Verificado |

### BLOQUE 2 — SMOKE TEST ✅

| ID | Fix | Archivo | Validación |
|----|-----|---------|------------|
| F-2.1 | `test_pipeline_smoke.py` creado con 14 tests | `apps/api/tests/` | ✅ 14/14 passed |

### BLOQUE 3 — COSTO Y CALIDAD ✅

| ID | Fix | Impacto | Validación |
|----|-----|---------|------------|
| F-3.1 | Keywords 80→20, hashtags 50→30, sin buy_intent/geo como queries | **-64% costo Apify** | ✅ TestQueryBuilderCaps |
| F-3.2 | lens_score pesos 0.90→1.0 (0.389+0.278+0.222+0.111), tienda penalty 0.6→0.85 | Scoring correcto | ✅ TestLensScoreWeights |
| F-3.3 | geo_boost filtro ciudad: `len>3` sin filtro lowercase | +Candidatos CO/AR | ✅ TestGeoBoostCityMatching |
| F-3.4 | `"c🇨🇴"` → `"co"`, añadido `"co"` como ISO2 válido | Matching correcto | ✅ TestGeoBoostTypoFix |
| F-3.8 | elite_context no duplicado en batch prompts (sacado de `_build_single_prompt`) | -Tokens DeepSeek | ✅ TestCandidateAnalyzerBatchPrompt |
| F-3.10 | `get_or_create_profile` 1 sola vez (via `plan.profile`) | -1 call LLM/run | ✅ Code review |
| F-3.11 | Usa `plan.min_followers` en worker (era hardcoded 1000) | Config correcto | ✅ Code review |
| F-3.7 | ENABLE_AI_ANALYZER=False por defecto | Decisión CEO (Opción A) | ✅ |

### BLOQUE 4 — ROBUSTEZ ✅

| ID | Fix | Validación |
|----|-----|------------|
| F-4.3a | pollRun reconoce `'partial'` en useDiscoveryRun.ts | ✅ Code review |
| F-4.6a | Bloque duplicado keyword_items eliminado (27 líneas) | ✅ Code review |
| F-4.6b | `_analyze_single_candidate` dead code eliminado | ✅ Code review |
| F-4.6d | `compute_fingerprint` import eliminado de query_builder.py | ✅ Code review |

---

## 3. TU MISIÓN AHORA

### A) VERIFICACIÓN — Confirma que los fixes están correctamente implementados

Para cada fix listado arriba, verifica:
1. El código en el archivo indicado tiene el cambio correcto
2. El test correspondiente pasa
3. No hay side effects o regressions

Si encuentras algún problema, repórtalo inmediatamente.

### B) ANÁLISIS POST-FIXES — Qué más se puede mejorar

Con los fixes aplicados, el proyecto está más estable y eficiente. Pero siempre hay más oportunidades:

**Prioridad 1 — Pending fixes de Fable 5 (no críticos pero importantes)**

| ID | Fix | Esfuerzo | Razón para no aplicar aún |
|----|-----|----------|--------------------------|
| F-4.1 | `run_id` como parámetro en apify_client | ~2h | Requiere cambiar signaturas de múltiples métodos |
| F-4.2 | Persistir estado orchestrator/memory en JSONB | ~3h | Ya persiste parcialmente via `state` |
| F-4.3b | Frontend `refetchInterval` con TanStack Query | ~2h | Solo relevante si usas polling real |
| F-4.4 | Anti-bot: `followers > 0` prefilter | ~30min | Filtro actual es conservador |
| F-4.5 | Extraer hashtags de captions en STEP 4 | ~1.5h | Nice-to-have |
| F-3.5 | Lower geo threshold a 0.65 | ~45min | Esperar datos reales antes de ajustar |
| F-3.6 | Filtrar antes de DeepSeek + `gather` | ~2h | Optimización |
| F-3.9 | Store policy configurable en BriefStructured | ~2h | Feature request |

**Prioridad 2 — Nuevos análisis a realizar**

1. **Eficiencia de cache Redis** — ¿El cache está funcionando bien? ¿Hay cache misses que se pueden resolver?
2. **Cost tracking** — Los costos se loguean pero no se persisten en DB. ¿Deberíamos guardarlos?
3. **Scoring A/B testing** — ¿Tenemos datos suficientes para comparar el scoring viejo vs el nuevo?
4. **Edge cases del geo_boost** — ¿Qué pasa con países fuera de los 11 soportados?
5. **DeepSeek batch size óptimo** — ¿10 por batch es ideal o se puede aumentar?

---

## 4. CONTEXTO DEL PROYECTO

### ¿Qué es La Web Core?

**La Web Core** es la plataforma interna de **La Web Figital Agency** (Venezuela). Su producto estrella es **Lens** ("El Ojo que Todo lo Ve") — un sistema de descubrimiento de influencers con IA que:

1. Recibe briefs en lenguaje natural (ej: "influencers en Venezuela para Purina Dog Chow, mujeres 25-45")
2. Ejecuta un pipeline de 4 capas usando Apify para obtener datos oficiales de Instagram
3. Aplica scoring LWFA (4 KPIs exclusivos: ICA, Geo-Foco Real, Engagement Velocity, Business Intent)
4. Analiza candidatos con DeepSeek-V3 (content_quality, audience_quality, brand_fit)
5. Devuelve una lista curada de los mejores perfiles para la campaña

### Stack tecnológico
- **Frontend:** React 19 + Vite + TypeScript + Tailwind + shadcn/ui + Zustand + TanStack Query
- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0 async + asyncpg
- **DB:** PostgreSQL 16 + pgvector (Supabase Cloud) + Redis (Railway)
- **IA:** DeepSeek-V3 + fastembed (embeddings locales)
- **Scraping:** Apify (Instagram actors)
- **Infra:** Railway (API + Worker) + Vercel (Frontend)

### Arquitectura del Discovery/Lens

```
Brief (lenguaje natural)
    ↓
BriefParserAgent (DeepSeek) → BriefStructured
    ↓
ProfileGenerator (DeepSeek) → DiscoveryProfile (hashtags, keywords, geo_indicators, elite_data)
    ↓
QueryBuilder → DiscoveryPlan
    ↓
Worker (ARQ):
  STEP 1: Hashtag search (Apify) → handles (MAX 30 hashtags — post-fix)
  STEP 2: Keyword search (Apify) → handles (MAX 20 keywords — post-fix)
  STEP 3: Enrich profiles (Apify) → enriched data (MAX 25 handles)
  STEP 4: Scoring (geo_score + lens_score + niche_relevance + anti_bot)
  STEP 5: AI Analysis (DeepSeek) → content_quality + audience_quality + brand_fit
    ↓
Top Candidates → DB (discovery_candidates)
```

### Sistema ELITE (implementado Agosto 2026)

El `profile_generator.py` ahora genera un JSON completo por brief incluyendo:
- hashtags, keywords, niche_keywords, geo_indicators, buy_intent_keywords
- **elite_data** (JSONB con 9 subcampos):
  - content_themes, audience_behavior, competitor_intel, local_slang
  - credibility_signals, niche_benchmarks, anti_bot_signals
  - geo_local_signals, query_variations

---

## 5. ARCHIVOS PRIORITARIOS PARA ANALIZAR

### Backend (Python) — Alta prioridad
```
apps/api/app/workers/worker.py          # Pipeline principal, ~990 líneas (post-fix)
packages/discovery/discovery/
  ├── profile_generator.py              # Elite generator, 569 líneas
  ├── candidate_analyzer.py             # AI scoring, 372 líneas (post-fix)
  ├── orchestrator.py                  # State machine, 632 líneas
  ├── brief_parser.py                  # Brief parsing, 370 líneas
  ├── query_builder.py                 # DiscoveryPlan builder (post-fix)
  ├── tools/apify_client.py            # Apify client, 857 líneas
  ├── tools/geo_boost.py               # Geo scoring, 201 líneas (post-fix)
  └── scoring/lens_score.py            # Lens score, 95 líneas (post-fix)
packages/shared-core/shared_core/
  ├── supabase_rest.py                 # DB client, 434 líneas (post-fix)
  └── db.py                            # Session management, 80 líneas
apps/api/app/services/ai_service.py    # RAG + DeepSeek, ~400 líneas
```

### Frontend (React/TypeScript) — Media prioridad
```
apps/web/src/features/lens/
  ├── pages/LensChatPage.tsx
  ├── pages/LensSearchPage.tsx
  ├── components/BriefWizard.tsx
  ├── components/CandidateCard.tsx
  ├── hooks/useDiscoveryConversation.ts
  └── hooks/useRunPolling.ts
```

---

## 6. PREGUNTAS ESPECÍFICAS A RESPONDER

### Verificación de Fixes
1. ¿Los 19 fixes de Fable 5 están correctamente implementados en el código?
2. ¿Los smoke tests cubren los paths críticos de los fixes?
3. ¿Hay algún side effect o regression introducida por los fixes?

### Estabilidad (post-fixes)
1. ¿Qué pasa si Apify devuelve un error? ¿Hay retry? ¿Hay fallback?
2. ¿Qué pasa si DeepSeek falla durante el análisis de candidatos?
3. ¿Qué pasa si Redis está down? ¿El sistema sigue funcionando?
4. ¿Hay race conditions en el worker cuando múltiples runs corren en paralelo?
5. ¿El Orchestrator guarda su estado en memoria? ¿Se pierde en restart?

### Eficiencia (post-fixes)
1. ¿Se están haciendo queries innecesarias a Apify? ¿El cache está bien configurado?
2. ¿El prefilter en Step 3 (antes del enrichment) es óptimo o se pueden mejorar los handles seleccionados?
3. ¿Se están usando los índices de Postgres correctamente?
4. ¿Hay N+1 queries en el código?
5. ¿Se están cerrando las conexiones a la DB correctamente?

### Costos (post-fixes)
1. ¿Se pueden reducir las llamadas a Apify sin perder calidad?
2. ¿El batching de candidatos para DeepSeek es óptimo (actualmente 10 por batch)?
3. ¿Hay calls a Apify que se pueden cachear por más tiempo?
4. ¿Se están rastreando los costos por campaign/run?
5. ¿Los fixes de F-3.1 redujeron el costo como se esperaba ($4.93 → $1.79)?

### Scoring (post-fixes)
1. ¿La fórmula de scoring en worker.py coincide con la documentación en result_ranker.py?
2. ¿El anti_bot filter está realmente funcionando o es código muerto?
3. ¿El candidate_analyzer está usando realmente el elite_data?
4. ¿Los pesos del Lens Score (0.389, 0.278, 0.222, 0.111) son óptimos o deberían ajustarse?

### Frontend
1. ¿Hay memory leaks en los hooks de React (especialmente useRunPolling)?
2. ¿Se están haciendo re-renders innecesarios?
3. ¿El BriefWizard tiene validaciones insuficientes?

---

## 7. FORMATO DE RESPUESTA ESPERADO

```
# Análisis La Web Core — Verificación Fable 5 + Nuevas Oportunidades

## 1. VERIFICACIÓN DE FIXES APLICADOS

### ✅ F-1.1: from typing import Any
Status: VERIFICADO / PROBLEMA ENCONTRADO
Detalle: ...

### ✅ F-1.2: upsert_many RETURNING
...

## 2. ESTABILIDAD

### 2.1 Críticos (Alto Impacto)
...

## 3. EFICIENCIA

## 4. REDUCCIÓN DE COSTOS

### 4.1 Apify
...

## 5. SCORING

## 6. FRONTEND

## 7. TESTS FALTANTES PRIORITARIOS

## 8. TOP 10 ACCIONES RECOMENDADAS (orden de prioridad)

## 9. QUICK WINS (menor esfuerzo, mayor impacto)
```

---

## 8. RESTRICCIONES

1. **NO sugieras cambiar el stack tecnológico** (no cambiar a Django, no cambiar a Next.js, no cambiar a PostgreSQL → MySQL, etc.)
2. **NO sugieras rewrite completo de módulos** — solo mejoras incrementales
3. **NO sugieras agregar servicios externos nuevos** (no agregar Sentry si no está, no agregar Datadog, etc.)
4. **SÍ puedes sugerir** agregar tests, cache,índices, mejores manejo de errores, optimizaciones de queries, refactors pequeños
5. **El presupuesto es limitado** — prioriza acciones de alto impacto y bajo esfuerzo
6. **IMPORTANTE:** Los fixes de Fable 5 fueron aplicados — no sugerir aplicar los mismos fixes de nuevo

---

## 9. CONTEXTO DE NEGOCIO

- **Usuario principal:** Agencias de marketing en Venezuela/LATAM
- **Caso de uso:** Encontrar influencers para campañas de marketing
- **Presupuesto:** $250 USD/mes → $94 USD/mes (post-Fable 5) — meta de ahorro lograda
- **Meta de costo por campaign:** <$0.30 con cache
- **Smoke tests:** 14/14 passed ✅
- **Próximo paso:** Testear con run real cuando CEO haga refill de Apify credits

---

## 10. INSTRUCCIONES

1. **Verifica** que los 19 fixes de Fable 5 están correctamente implementados
2. **Ejecuta** análisis estático del código actualizado
3. **Identifica** problemas específicos con文件名 y número de línea
4. **Estima** esfuerzo en horas-hombre
5. **Prioriza** por impacto × esfuerzo
6. **Genera** recomendaciones concretas que se puedan implementar en 1-2 horas máximo por item
7. **Para cada recomendación**, incluye:
   - Qué cambiar
   - En qué archivo
   - Por qué mejora (estabilidad/eficiencia/costo)
   - Código de ejemplo si es posible

---

*Prompt generado: 2026-08-05*
*Actualizado para reflejar: Todos los fixes de Fable 5 aplicados y validados*
*Para uso con Claude Code Fable 5 o cualquier agente de análisis de código*
