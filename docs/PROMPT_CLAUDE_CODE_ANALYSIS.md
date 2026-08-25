# PROMPT_CLAUDE_CODE_ANALYSIS — Índice de Auditorías LENS

> **Última actualización:** 2026-08-26
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Hito actual:** Hitos 30-34 aplicados (commit `bd973c7`), Hitos #0/#1/#2/#3/#4/#5/#6/#7/#8/#9/#10 pendientes
> **HikerAPI balance:** ~$38.00 USD (~$5 ejecutados en Hitos 30-34)
> **NUEVO:** Audit #17 — Análisis completo Claude Code Fable 5 post-Hitos 30-34 (subagente explore)

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
| **13** | *Commit `a21dd97`* | **2026-08-20** | **Claude Code Opus 5 + MiniMax** | Hito 28: Fix A (pre-flight mode-aware), Fix B (DeepSeek skip explorar), extra='forbid', 17 tests — **APLICADO** |
| **14** | *`docs/ARQUITECTURA_LENS.md` v5.4* | **2026-08-20** | **MiniMax** | Pipeline Coverage Analysis: 8 brechas identificadas — engagement quality, niche captions, geo post-enrich, tier enforcement, cross-ref boost, verified boost, time-decay, bot detection avanzada. Roadmap postergado post-validación |
| **15** | *`docs/hito29_hotfix.patch`* | **2026-08-21** | **Opus 5** | HOTFIX CRÍTICO: extra='forbid' en BriefStructured rompía TODOS los runs. Regla correcta: forbid en frontera de entrada (DiscoverySearchRequest), ignore en persistencia (BriefStructured). 48 runs históricos con campos que ya cambiaron. Fix: schemas.py BriefStructured extra=ignore + max_candidates. Tests anti-regresión en test_hito29_e2e_regression.py |
| **16** | *`docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md`* | **2026-08-25** | **Santiago Lanz + MiniMax** | Plan Main de alineación basado en Informe Lanz v1.2. 5 fases: Fallar en voz alta → Ensanchar búsqueda → Contrato datos → Tabla maestra → Decisión negocio. ~16-22h trabajo, ~$0.44/radicional. Basado en 25 claims verificadas contra código. Respetar estándar 13_data_contract_hub.md como padre. |
| **17** | *`docs/PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md`* | **2026-08-26** | **Claude Code Fable 5 + MiniMax** | Plan oficial Fable 5 (605 líneas). Hitos 30-34 aplicados (commit `bd973c7`). Análisis subagente detecta regresión crítica: merge enrichment sigue leyendo camelCase de dict ya normalizado. 3 gaps nuevos: drop_profile no persiste en DB, influencer_metrics_snapshot sin social_account_id, influencer_social_accounts UNIQUE constraint revienta al re-guardar. Plan detallado para #0-#10 generado. |

---

## Estado Actual del Proyecto

### Hitos Aplicados (1-34)

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
```

### Verificación Empírica (2026-08-20)

| Métrica | Valor |
|---------|-------|
| Total runs | 48 |
| Total gastado | **$28.33** |
| Candidatos producidos | **1** |
| Runs condenmados por saldo | 2 (0c44ea23, c859eba1) |
| Railway deploy | ✅ 18:26 UTC (`7796dc9`) |
| Vercel deploy | ✅ 11:30 UTC (`df41d9e`) |
| Migration 00106 | ✅ Aplicada y confirmada |
| Modo Explorar en código | ✅ 4 bugs corregidos |
| **Hito 28 commit** | ✅ `a21dd97` — Fix A/B correctos, extra='forbid' parcialmente revertido por Hito 29 |
| **HikerAPI balance** | ✅ **$43.00 USD** — recargado 2026-08-20 (~67 runs Explorar) |

### Bugs Resueltos

| Bug | Hito | Notes |
|-----|-------|-------|
| Parser get_balance() roto | **Hito 25** | `state:false` → 0.0, pre-flight aborta |
| `exclude_stores` como causa | ❌ Refutado | Opus 5 probó enrichment 402 |
| Pre-flight silenciado | Hito 23 | `raise SourceUnavailable` antes de `except Exception` |
| Mensaje fijo misleading | Hito 23 | `_build_zero_candidates_message()` |
| **Dict candidato claves incorrectas** | **Hito 26** | columnas DB correctas (`handle`, `avatar_url`, etc.) |
| **Frontend no enviaba discovery_mode** | **Hito 26** | `'explore' as const` en LensSearchPage |
| **Polling no cargaba candidatos explored** | **Hito 26** | `useRunPolling.ts` reconoce status `explored` |
| **TypeScript error discovery_mode literal** | **Hito 26** | `as const` corrige tipo |
| **Ledger crash sin migration 00107** | **Hito 26** | try/except protege; 00107 ahora opcional |
| **`parent_run_id` descartado en schema** | **Hito 27** | Pydantic descartaba el campo; Analizar repetía ~$0.64 de discovery |
| **`platforms` default= en vez de default_factory=** | **Hito 27** | Bug latente Pydantic v2; rompe con TikTok |
| **Fix A: Pre-flight sobreestimaba costo** | **Hito 28** | Modo-aware: Explorar $0.64, Analizar real, Auto $1.14 — `a21dd97` |
| **Fix B: DeepSeek corrompía decisión en Explorar** | **Hito 28** | Skip DeepSeek en Explorar; rationale honesto preservado — `a21dd97` |
| **extra='forbid' REVERSIÓN — solo en frontera de entrada** | **Hito 29** | REVERSIÓN PARCIAL: extra='forbid' en BriefStructured rompía TODOS los runs. Regla correcta: forbid en DiscoverySearchRequest (frontera entrada), ignore en BriefStructured (persistencia) — `a21dd97` revertido |
| **can_make_call() código muerto** | **Hito 30** | ELIMINADA: retornaba True en error y nadie la llamaba. reserve_and_record() ya fail-closed. |
| **_normalize_user fabricaba 0** | **Hito 31** | FIX H-1: ahora devuelve None para campos ausentes. 7 dual-names eliminados del retorno. |
| **primary_tier MICRO hardcoded** | **Hito 32** | `_derive_tier()` deriva desde follower_count. No más MICRO hardcoded. |
| **Metadata mentía sobre ejecución** | **Hito 33** | `hashtags_planned_count` vs `hashtags_executed_count`. Slice usa settings. |
| **deepseek-chat retirado** | **Hito 34** | Modelo actualizado a deepseek-v3. response_format json_object añadido. |
| **Proveedor sin validación entrada** | **Hito 35** | Backend valida product_name y niches requeridos. |

### Bugs Abiertos

| Bug | Prioridad | Notes |
|-----|-----------|-------|
| Fix C: useRunPolling.ts no usado por LensSearchPage | ⚠️ BAJA | Tech debt — hook usado por LensChatPage, NO por LensSearchPage — NO action needed |
| Budget tracking desfase | 🔴 CRÍTICA | $25.13 Redis↔DB mismatch |
| `accepted` siempre 0 | 🔴 CRÍTICA | No se actualiza post-seleccion |
| 1 candidato en 48 runs | 🔴 CRÍTICA | Producto no entrega valor — parcialmente corregido con Hitos 30-34 |
| Geolocalización sin validar | ⚠️ MEDIA | POSTERGADO — no hay candidatos |
| **REGRESIÓN CRÍTICA: merge enrichment camelCase** | 🔴 CRÍTICA | Hito 31.1 нормализовал pero merge sigue leyendo followersCount → datos perdidos |
| **drop_profile no persiste en discovery_run_events** | 🔴 CRÍTICA | Tabla existe (migración 108) pero función solo loguea — Capa 6 de observabilidad rota |
| **influencer_metrics_snapshot duplicados por día** | 🔴 CRÍTICA | No hay UPSERT ni social_account_id en INSERT — mismo candidato = N filas |
| **9 sub-tiers vs 4 en _derive_tier** | 🟡 MEDIA | Plan Fable 5 §1.3 pide 9 sub-tiers, código tiene 4 — decisión pendiente |
| get_balance() con saldo>0 sin verificar | ⚠️ MEDIA | Parser busca `balance`, puede no existir con saldo positivo |

---

## Próximos Pasos

1. ✅ **Hitos 30-34 aplicados** — commit `bd973c7` (2026-08-26)
2. 🔴 **#0 Fix regresión merge enrichment** — INMEDIATO: worker.py:1204-1232 con LegacyCompatReader
3. 🔴 **#4 drop_profile persiste** — discovery_run_events necesita INSERT real
4. 🟡 **#1 LegacyCompatReader + ContractViolationLedger** — ventana de compatibilidad 14 días
5. 🟡 **#2 Freshness policy 7d** — skip enrichment si snapshot <7 días
6. 🟡 **#3 Brand exclusion table** — Compliance Nestlé L-03/L-05
7. 🟡 **#7 _derive_tier 9 sub-tiers** — confirmar escala con Ungar/Ignacio
8. 🟢 **#5/#6 refactors camelCase** — limpieza técnica
9. 🟢 **#8 housekeep seed.sql/schema.sql** — deepseek-v3 default
10. ⏳ **#9 tests CI gate** — test_hito31_data_contract.py
11. ⏸ **#10 retirar LegacyCompatReader** — post-14 días con contract.violation==0

---

## Para Claude Code Fable 5 — Última Auditoría

La auditoría más reciente es **#17 — Análisis post-Hitos 30-34** (`docs/PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md` + subagente explore). Esta auditoría:
1. Verificó todos los Hitos 30-34 aplicados contra commit `bd973c7`
2. Detectó regresión crítica: merge enrichment sigue leyendo camelCase post-Hito 31.1
3. Identificó 3 gaps nuevos no anticipados por el plan Fable 5 original
4. Produjo plan detallado #0-#10 con código ejecutable para cada hito pendiente

### Auditoría #14 — Pipeline Coverage Analysis

**8 brechas identificadas:**

| # | Brecha | Severidad | Esfuerzo | Costo Extra |
|---|--------|-----------|----------|-------------|
| 1 | Quality Score (engagement real) | 🟡 MEDIA | 1h | +$0.10-0.20 |
| 2 | Nicho real (captions) | 🟡 MEDIA | 30min | +$0.05 |
| 3 | Geo post-enrichment | 🟢 BAJA | 30min | $0 |
| 4 | Tier enforcement (5K-50K) | 🟢 BAJA | 15min | $0 |
| 5 | Cross-reference boost | 🟡 MEDIA | 1h | $0 |
| 6 | Verified boost | 🟢 BAJA | 15min | $0 |
| 7 | Time-decay | 🟡 MEDIA | 1h | $0 |
| 8 | Bot detection avanzada | 🟡 MEDIA | 2h | $0 |

**Roadmap propuesto:** H29-H35 (~6.5h total, +$0.15-0.25/radiobutton)

**Request explícito a Opus 5:**
> Analiza las 8 brechas en `docs/ARQUITECTURA_LENS.md` Sección 20. Para cada una, proporciona: (1) confirmación del fix o alternativa mejor, (2) código del patch, (3) orden de aplicación recomendada (H29 primero), (4) conflictos con Hito 28 Fix B que deban resolverse.

**Fixes H29 inmediatos (15 min, $0):**
```python
# worker.py — prefilter_profiles:
# Tier enforcement + Verified boost + Geo post-enrichment
```

---

### Resumen de Hito 28 (para contexto)

**Fix A — Pre-flight mode-aware (🔴 CRÍTICA):**
- Antes: 57 calls = $1.14 siempre
- Después: Explorar $0.64, Analizar ~$0.06-0.10, Auto $1.14
- El "último dólar inutilizable" ahora se recupera

**Fix B — DeepSeek skip en Explorar (🔴 CRÍTICA — NO era costo, era corrupción de decisión):**
- Antes: DeepSeek corría con `followers=0`, sobrescribía rationale honesto
- Después: DeepSeek solo corre en Auto y Analizar
- Rationale honesto preservado: "descubierto sin enriquecer, señal derivada de la bio"

**extra='forbid' — Cierre de clase de bug:**
- BriefStructured y DiscoverySearchRequest ahora con `ConfigDict(extra="forbid")`
- Campo inesperado = ValidationError inmediato

**Tests:** 17 nuevos en `test_hito28_e2e.py` (17 passed)
- TestExtraForbidSchemas: 5 tests
- TestPreflightModeAware: 6 tests
- TestDeepSeekSkipInExplore: 5 tests
- TestExploreMax25Candidates: 1 test

**Validación tomorrow:** ~$0.76 de los $43.00 USD

---

*Índice actualizado: 2026-08-26 — Proyecto LENS con Hitos 30-34 aplicados (commit `bd973c7`). Plan Main actualizado en docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md. Hitos pendientes #0-#10 (~28.5h, ~$7.42). Basado en Informe Santiago Lanz v1.2 + Plan Claude Code Fable 5. HikerAPI ~$38 USD restantes.*