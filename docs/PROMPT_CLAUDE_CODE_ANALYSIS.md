# PROMPT_CLAUDE_CODE_ANALYSIS — Índice de Auditorías LENS

> **Última actualización:** 2026-08-27
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Hito actual:** Hitos 30-34 aplicados (commit `bd973c7`) + 8 Fixes Fase 35 aplicados (commit `2446e75`)
> **HikerAPI balance:** ~$38.00 USD
> **NUEVO:** Iteración 2 — Fix C-1 (RunStatus enum mismatch) + Fix C-2 (Influencer.primary_tier type mismatch) + preparación corrida de validación
> **NUEVO:** Audit #18 — Análisis acoplamiento frontend-backend (2 issues críticos bloqueantes)

Este documento es un **índice histórico** de las auditorías de LENS Discovery. La auditoría más reciente es **#17 — Análisis post-Hitos 30-34** (subagente explore + plan detallado para pendientes #0-#10).

---

## Auditorías Completas

| # | Archivo | Fecha | Auditor | Tema principal |
|---|---------|-------|---------|----------------|
| 1 | `LENS_REVIEW_ARQUITECTURA_2026-08-14.md` | 2026-08-14 | — | Arquitectura original |
| 2 | `LENS_AUDIT2_2026-08-14.md` | 2026-08-14 | — | Segunda pasada |
| 3 | `LENS_AUDIT3_2026-08-14.md` | 2026-08-14 | — | Tercera pasada |
| 5 | `LENS_AUDIT5_2026-08-17.md` | 2026-08-17 | — | Post-Hito 20 |
| 6 | `LENS_AUDIT6_2026-08-17.md` | 2026-08-17 | — | Sexta auditoría |
| **7** | `LENS_AUDIT7_2026-08-18.md` | **2026-08-18** | **Claude Code Opus 5** | Bug N1 refutado, causa real era enrichment 402 |
| **8** | `LENS_AUDIT8_2026-08-19.md` | **2026-08-19** | **Claude Code Opus 5** | Hito 23 patch analysis |
| **9** | `LENS_AUDIT9_2026-08-19.md` | **2026-08-19** | **MiniMax + datos Railway** | Verificación empírica — 48 runs, $28.33, 1 candidato |
| **10** | `LENS_ASESORIA_INGENIERO_2026-08-20.md` | **2026-08-20** | **MiniMax + usuario** | 4 bugs críticos corregidos — dict columnas, frontend mode, polling, ledger try/except |
| **11** | `LENS_REUNION_2026-08-20.md` | **2026-08-20** | **Claude Code Opus 5** | Bug `parent_run_id` descartado, 5 correcciones a la documentación, recomendación $20 |
| **12** | `LENS_REUNION_2026-08-20.md` (Fix A/B/C docs) | **2026-08-20** | **MiniMax** | Fix A (pre-flight), Fix B (DeepSeek), Fix C (useRunPolling) documentados |
| **13** | *Commit `a21dd97`* | **2026-08-20** | **Claude Code Opus 5 + MiniMax** | Hito 28: Fix A (pre-flight mode-aware), Fix B (DeepSeek skip explorar), extra='forbid', 17 tests |
| **14** | *`docs/ARQUITECTURA_LENS.md` v5.4* | **2026-08-20** | **MiniMax** | Pipeline Coverage Analysis: 8 brechas identificadas |
| **15** | *`docs/hito29_hotfix.patch`* | **2026-08-21** | **Opus 5** | HOTFIX: extra='forbid' revertido — ignore en BriefStructured |
| **16** | *`docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md`* | **2026-08-25** | **Santiago Lanz + MiniMax** | Plan Main basado en Informe Lanz v1.2 |
| **17** | *`docs/PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md`* | **2026-08-26** | **Claude Code Fable 5 + MiniMax** | Plan oficial Fable 5. Análisis subagente detecta regresión merge enrichment. Plan #0-#10 |
| **18** | *`docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md` (actualizado)* | **2026-08-27** | **MiniMax** | Análisis acoplamiento frontend-backend. 2 issues críticos: RunStatus enum mismatch (HTTP 500), Influencer.primary_tier type mismatch. 8 fixes Fase 35 aplicados (commit `2446e75`). Plan_main reescrito completamente. |
| **19** | *`docs/PROMPT_CLAUDE_CODE_FABLE_5_ITERACION_2.md`* | **2026-08-27** | **MiniMax** | Prompt para Iteración 2 de Fable 5: Fix C-1 (RunStatus enum) + Fix C-2 (Influencer.primary_tier) + preparación validación |

---

## Estado Actual del Proyecto

### Hitos Aplicados (1-34 + 35)

```
1-20:   Features y fixes varios
21:     Single accounting point + fail-closed
22:     actual_cost_usd persistence + PARTIAL enum
23:     Pre-flight balance + except SourceUnavailable raise + _build_zero_candidates_message
24:     Modo Explorar + Modo Analizar
25:     Fix get_balance() parser — detecta state:false → retorna 0.0
26:     4 bugs críticos corregidos — dict columnas DB, frontend discovery_mode, polling explored, ledger try/except
27:     parent_run_id en DiscoverySearchRequest (modo Analizar no repite discovery) + platforms default_factory
28:     Fix A pre-flight mode-aware ($0.64/$0.10/$1.14) + Fix B DeepSeek skip explorar + extra='forbid' schemas
29:     HOTFIX: extra='forbid' solo en frontera de entrada (regresión corregida)
30:     Observabilidad: RunEvent/DropReason/RunStatus enums, DropLedger, FunnelTracker, contextvars, can_make_call eliminada, events table
31:     Contrato datos: _normalize_user None, 7 dual-names eliminados, or 0 corregidos, data contract doc
32:     Tabla maestra: _derive_tier, dedup handle, metrics carry-through, social_accounts, metrics_snapshot
33:     Ensanche búsqueda: constants to config, settings, metadata truth
34:     Precisión IA: response_format json_object, regex eliminado, deepseek-v3
35:     Validación backend: product_name y niches requeridos
FASE 35: 8 Fixes aplicados (commit `2446e75`):
  - FIX #1+2: Merge enrichment snake_case + _enriched flag; scoring follower_count first
  - FIX #3: flush_drop_ledger() persiste ledger a discovery_run_events
  - FIX #4+5: UPSERT influencer_social_accounts + metrics_snapshot con social_account_id
  - FIX #6: _derive_tier → 9 sub-tiers (NANO_BAJO → MACRO_ALTO)
  - FIX #8: _parse_batch_response usa _json.loads directo
```

### Commits Relevantes

| Commit | Fecha | Descripción |
|--------|-------|-------------|
| `bd973c7` | 2026-08-26 | Hitos 30-34 foundation |
| `2446e75` | **2026-08-27** | **8 Fixes Fase 35 — regressions and data integrity** |
| `18ae963` | 2026-08-26 | Docs sync |

### Verificación Empírica (2026-08-20)

| Métrica | Valor |
|---------|-------|
| Total runs | 48 |
| Total gastado | **$28.33** |
| Candidatos producidos | **1** |
| Railway deploy | ✅ "Application startup complete" (deploy 27-ago-26) |
| **HikerAPI balance** | ✅ **~$38.00 USD** (~$5 ejecutados en Hitos 30-34 + 35) |

### Bugs Resueltos (desde última actualización)

| Bug | Hito | Notes |
|-----|-------|-------|
| **REGRESIÓN CRÍTICA: merge enrichment camelCase** | **Fase 35 FIX #1+2** | Merge ahora solo snake_case + `_enriched`; scoring distingue MISSING_FOLLOWER_FIELD |
| **drop_profile no persiste en discovery_run_events** | **Fase 35 FIX #3** | `flush_drop_ledger()` implementado; Capa 6 de observabilidad operativa |
| **influencer_metrics_snapshot duplicados** | **Fase 35 FIX #4+5** | UPSERT con `on_conflict=(influencer_id,social_account_id,snapshot_date,source)` |
| **influencer_social_accounts UNIQUE constraint** | **Fase 35 FIX #4+5** | UPSERT con `on_conflict=(platform,handle)`; captura `social_account_id` |
| **_derive_tier 4 tiers** | **Fase 35 FIX #6** | 9 sub-tiers implementados (NANO_BAJO → MACRO_ALTO) |
| **re.search en _parse_batch_response** | **Fase 35 FIX #8** | `_json.loads()` directo |
| can_make_call() código muerto | **Hito 30** | ELIMINADA: retornaba True en error y nadie la llamaba. reserve_and_record() ya fail-closed. |
| _normalize_user fabricaba 0 | **Hito 31** | ahora devuelve None para campos ausentes |
| primary_tier MICRO hardcoded | **Hito 32** | `_derive_tier()` deriva desde follower_count |
| Metadata mentía sobre ejecución | **Hito 33** | `hashtags_planned_count` vs `hashtags_executed_count` |

### Bugs Abiertos (post-2446e75)

| Bug | Prioridad | Notes |
|-----|-----------|-------|
| **Issue C-1: RunStatus enum mismatch (HTTP 500)** | 🔴 CRÍTICA | Worker escribe `delivered/degraded/aborted_budget` pero Pydantic enum no los conoce. HTTP 500 en polling. |
| **Issue C-2: Influencer.primary_tier type mismatch** | 🟡 MEDIA | Backend ahora escribe 9 sub-tiers; frontend type solo conoce 4 macro |
| Fix C: useRunPolling.ts no usado por LensSearchPage | ⚠️ BAJA | Tech debt — hook usado por LensChatPage, NO por LensSearchPage |
| Budget tracking desfase | ⚠️ MEDIA | POSTERGADO — después de validación |
| `accepted` siempre 0 | ⚠️ MEDIA | No se actualiza post-selección (es separate endpoint) |
| Geolocalización sin validar | ⚠️ MEDIA | POSTERGADO — no hay candidatos |
| FP-1: Freshness policy 7d | 🟡 MEDIA | Pendiente — requiere decisión de ventana |
| FP-2: Brand exclusion table | 🟡 MEDIA | Pendiente — requiere handles Nestlé/Purina |
| get_balance() parser edge cases | ⚠️ MEDIA | Parser busca `balance`, puede no existir con saldo positivo |

---

## Próximos Pasos

### Iteración 2 (AHORA) — Fix Frontend Bloqueantes

1. 🔴 **Issue C-1: RunStatus enum mismatch** — Extender `DiscoveryRunStatus` en schemas.py con `delivered/degraded/aborted_budget/empty/inconsistent`
2. 🟡 **Issue C-2: Influencer.primary_tier type** — Widen union type en types/index.ts con 9 sub-tiers
3. ✅ **8 Fixes Fase 35 aplicados** — commit `2446e75` (2026-08-27)
4. ⏳ **Corrida de validación** — ~$1.14 — después de Fix C-1 + C-2

### Post-Validación (prioridad media)

5. 🟡 **FP-1: Freshness policy 7d** — skip enrichment si snapshot <7 días
6. 🟡 **FP-2: Brand exclusion table** — requiere handles Nestlé/Purina
7. 🟢 **FP-3: seed.sql/schema.sql deepseek-v3** — housekeeping
8. 🟢 **FP-4: Tests** — CI gate post-estabilización
9. 🟢 **FP-5: Ensanche 5/3/5/2** — requiere aprobación (+$0.44/corrida)

### Decisiones de Negocio Pendientes

- Q1: Handles Nestlé/Purina VE para brand_excluded_handles
- Q2: Ventana freshness: 7 / 14 / 30 días
- Q3: Tier targeting en campañas: macro (4) o sub-tier (9)
- Q4: Aprobación ensanche 5/3/5/2

---

## Para Claude Code Fable 5 — Iteración 2

La Iteración 2 (prompt en `docs/PROMPT_CLAUDE_CODE_FABLE_5_ITERACION_2.md`) tiene dos objetivos:
1. **Aplicar Fix C-1**: Extender `DiscoveryRunStatus` enum en schemas.py con los 5 valores faltantes
2. **Aplicar Fix C-2**: Widen `Influencer.primary_tier` union type en types/index.ts con los 9 sub-tiers
3. **Commit + push + verificar Railway deploy**
4. **Documentar approach para los fixes opcionales** (FP-1 a FP-5)

### Análisis Acoplamiento Frontend-Backend (Audit #18)

| Issue | Severidad | Fix | Costo |
|-------|-----------|-----|-------|
| C-1: RunStatus enum mismatch (HTTP 500) | 🔴 CRÍTICA | schemas.py + DiscoveryRunStatus | $0 |
| C-2: Influencer.primary_tier type | 🟡 MEDIA | types/index.ts | $0 |
| C-3: Tier filter chips disappear | 🟢 BAJA | CandidateList.tsx ALL_TIERS | $0 (opcional) |
| C-4: Tier badge sin color | 🟢 BAJA | format.ts getTierColor | $0 (opcional) |
| C-5: SearchProgress PHASES desfasadas | 🟢 BAJA | SearchProgress.tsx | $0 (opcional) |
| C-6: LensEmptyState variants no usadas | 🟢 BAJA | — | $0 (código muerto) |

### Resumen de Fixes Aplicados (commit `2446e75`)

**FIX #1+2 (🔴 CRÍTICO):** Merge enrichment ahora solo snake_case + `_enriched: True`; scoring lee `follower_count` primero y distingue `MISSING_FOLLOWER_FIELD` de explore mode. **恢复了 el pipeline de enrichment — antes todos los perfiles enriquecidos se descartaban como si tuvieran 0 seguidores.**

**FIX #3:** `flush_drop_ledger()` persiste el ledger de descartes a `discovery_run_events`. Auditoría funcional.

**FIX #4+5:** UPSERT en `influencer_social_accounts` y `influencer_metrics_snapshot` — sin duplicados, con `social_account_id`.

**FIX #6:** `_derive_tier` ahora devuelve 9 sub-tiers alineados con `TIER_BENCHMARKS`.

**FIX #8:** `_parse_batch_response` usa `_json.loads()` directo en vez de `re.search`.

---

*Índice actualizado: 2026-08-27 — Proyecto LENS con 8 Fixes Fase 35 aplicados (commit `2446e75`). Fix C-1 + C-2 pendientes. Plan Main reescrito en docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md. Iteración 2 prompt en docs/PROMPT_CLAUDE_CODE_FABLE_5_ITERACION_2.md. Basado en Informe Santiago Lanz v1.2 + Plan Claude Code Fable 5. HikerAPI ~$38 USD restantes.*