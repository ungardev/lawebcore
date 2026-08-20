# PROMPT_CLAUDE_CODE_ANALYSIS — Índice de Auditorías LENS

> **Última actualización:** 2026-08-20
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Hito actual:** Hito 28 (Fix A pre-flight mode-aware + Fix B DeepSeek skip + extra='forbid')
> **HikerAPI balance:** $43.00 USD ✅

Este documento es un **índice histórico** de las auditorías de LENS Discovery. La auditoría más reciente es **`LENS_HITO28_2026-08-20.md`** (análisis de Claude Code Opus 5 con Fix A/B patch). **Pendiente de generar** `LENS_HITO28_2026-08-20.md` con el opúsculo completo de Opus 5.

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
| **Hito 28 commit** | ✅ `a21dd97` — Fix A/B + extra='forbid' aplicados |
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
| **extra='forbid' en schemas** | **Hito 28** | BriefStructured + DiscoverySearchRequest — clase de bug cerrada — `a21dd97` |

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
3. ✅ **Hito 28** — Fix A (pre-flight mode-aware) + Fix B (DeepSeek skip) + extra='forbid' (commit `a21dd97`)
4. ⏳ **Deploy Railway** — push `a21dd97` a producción (pre-flight requiere deploy para activar)
5. ⏳ **Validación con $43** — ~$0.76 para primer run Explorar + Analizar 5 handles
6. ⏳ **Demo con marca real** — Nestlé o similar

---

## Para Opus 5 — Última Auditoría

La auditoría más reciente es **`LENS_REUNION_2026-08-20.md`** (documento de 255 líneas escrito por Opus 5). **Pendiente:** generar `LENS_HITO28_2026-08-20.md` con el análisis completo de Opus 5 sobre Fix A/B.

### Resumen de Hito 28 (para análisis de Opus 5)

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

**Validación mañana:** ~$0.76 de los $43.00 USD

---

*Índice generado: 2026-08-20 — Proyecto LENS con 28 hitos aplicados, HikerAPI $43.00, 1 candidato histórico. Hito 28: Fix A (pre-flight mode-aware), Fix B (DeepSeek skip explorar), extra='forbid'. 17 tests nuevos. Validación tomorrow.*