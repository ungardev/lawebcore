# PROMPT_CLAUDE_CODE_ANALYSIS — Índice de Auditorías LENS

> **Última actualización:** 2026-08-21
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Hito actual:** Hito 29 (HOTFIX extra='forbid' solo en frontera de entrada — regresión corregida)
> **HikerAPI balance:** $43.00 USD ✅
> **NUEVO v5.5:** Audit #15 — Hito 29 Hotfix (extra='forbid' regresión detectada por Opus 5)

Este documento es un **índice histórico** de las auditorías de LENS Discovery. La auditoría más reciente es **#15 — Hito 29 Hotfix** (regresión crítica detectada por Opus 5: extra='forbid' solo en frontera de entrada).

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

---

## Estado Actual del Proyecto

### Hitos Aplicados (1-28)

```
1-20: Features y fixes varios
21:   Single accounting point + fail-closed
22:   actual_cost_usd persistence + PARTIAL enum
23:   Pre-flight balance + except SourceUnavailable raise + _build_zero_candidates_message
24:   Modo Explorar + Modo Analizar
25:   Fix get_balance() parser — detecta state:false → retorna 0.0
26:   4 bugs críticos corregidos — dict columnas DB, frontend discovery_mode, polling explored, ledger try/except
27:   parent_run_id en DiscoverySearchRequest (modo Analizar no repite discovery) + platforms default_factory
28:   Fix A pre-flight mode-aware ($0.64/$0.10/$1.14) + Fix B DeepSeek skip explorar + extra='forbid' schemas
29:   HOTFIX: extra='forbid' solo en frontera de entrada (regresión corregida) — BriefStructured extra=ignore + max_candidates
30-33: Alineación Lanz §7: Fallar en voz alta + Ensanchar búsqueda + Contrato datos + Tabla maestra
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

### Bugs Abiertos

| Bug | Prioridad | Notes |
|-----|-----------|-------|
| Fix C: useRunPolling.ts no usado por LensSearchPage | ⚠️ BAJA | Tech debt — hook usado por LensChatPage, NO por LensSearchPage — NO action needed |
| Budget tracking desfase | 🔴 CRÍTICA | $25.13 Redis↔DB mismatch |
| `accepted` siempre 0 | 🔴 CRÍTICA | No se actualiza post-seleccion |
| 1 candidato en 48 runs | 🔴 CRÍTICA | Producto no entrega valor |
| Geolocalización sin validar | ⚠️ MEDIA | POSTERGADO — no hay candidatos |
| get_balance() con saldo>0 sin verificar | ⚠️ MEDIA | Parser busca `balance`, puede no existir con saldo positivo |

---

## Próximos Pasos

1. ✅ **Migration 00106** — ejecutada y confirmada
2. ✅ **Hito 27** — `parent_run_id` en DiscoverySearchRequest (commit `hito27`)
3. ✅ **Hito 28** — Fix A (pre-flight mode-aware) + Fix B (DeepSeek skip) + extra='forbid' parcial (commit `a21dd97`)
4. ✅ **Hito 29 HOTFIX** — extra='forbid' solo en frontera de entrada (regresión corregida)
5. ⏳ **Deploy Railway** — push Hito 29 a producción (HOTFIX crítico antes de cualquier run)
6. ⏳ **Validación con $43** — ~$0.76 para primer run Explorar + Analizar 5 handles
7. ⏳ **Brecha 4 (tier)** — cuestionar si rango 5K-50K tiene sentido ANTES de reforzarlo
8. ⏳ **8 brechas restantes** — postergadas hasta tener datos del primer Explorar (≥15 handles con bio)

---

## Para Opus 5 — Última Auditoría

La auditoría más reciente es **#15 — Hito 29 Hotfix** (`docs/hito29_hotfix.patch` + `docs/LENS_RESUMEN_REUNION_2026-08-21.md`). Esta auditoría corrige una regresión crítica introducida por Opus 5 en el Hito 28: extra='forbid' aplicado incorrectamente a BriefStructured.

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

*Índice generado: 2026-08-25 — Proyecto LENS con 29 hitos aplicados + Plan Lanz (Fases 0-5). HikerAPI $43.00. Plan Main alineación en docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md. Basado en Informe Santiago Lanz v1.2 (25 claims verificadas contra código). ~16-22h de trabajo restantes.*