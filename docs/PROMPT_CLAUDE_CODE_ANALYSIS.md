# PROMPT_CLAUDE_CODE_ANALYSIS — Índice de Auditorías LENS

> **Última actualización:** 2026-08-20
> **Repositorio:** https://github.com/ungardev/lawebcore

Este documento es un **índice histórico** de las auditorías de LENS Discovery. La auditoría más reciente es **`LENS_REUNION_2026-08-20.md`** (análisis de Claude Code Opus 5 posterior a `LENS_ASESORIA_INGENIERO_2026-08-20.md`).

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
| **11** | **`LENS_REUNION_2026-08-20.md`** | **2026-08-20** | **Claude Code Opus 5** | Bug `parent_run_id` descartado, 5 correcciones a la documentación, recomendación $20 |

---

## Estado Actual del Proyecto

### Hitos Aplicados (1-27)

```
1-20: Features y fixes varios
21:   Single accounting point + fail-closed
22:   actual_cost_usd persistence + PARTIAL enum
23:   Pre-flight balance + except SourceUnavailable raise + _build_zero_candidates_message
24:   Modo Explorar + Modo Analizar
25:   Fix get_balance() parser — detecta state:false → retorna 0.0
26:   4 bugs críticos corregidos — dict columnas DB, frontend discovery_mode, polling explored, ledger try/except
27:   parent_run_id en DiscoverySearchRequest (modo Analizar no repite discovery) + platforms default_factory
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
| HikerAPI balance | 🔴 $0 — requiere recarga $20 (~58 campañas completas) |

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

### Bugs Abiertos

| Bug | Prioridad | Notes |
|-----|-----------|-------|
| Budget tracking desfase | 🔴 CRÍTICA | $25.13 Redis↔DB mismatch |
| `accepted` siempre 0 | 🔴 CRÍTICA | No se actualiza post-seleccion |
| 1 candidato en 48 runs | 🔴 CRÍTICA | Producto no entrega valor |
| Geolocalización sin validar | ⚠️ MEDIA | POSTERGADO — no hay candidatos |
| get_balance() con saldo>0 sin verificar | ⚠️ MEDIA | Parser busca `balance`, puede no existir con saldo positivo |

---

## Próximos Pasos

1. ✅ **Migration 00106** — ejecutada y confirmada
2. ✅ **Hito 27** — `parent_run_id` en DiscoverySearchRequest (aplicado en este commit)
3. ⏳ **Recargar $20 HikerAPI** — (~58 campañas completas, recomendación Opus 5)
4. ⏳ **Test Modo Explorar** — validar status=`explored`, candidatos con handle+bio populated
5. ⏳ **Test Modo Analizar** — validar enrichment selectivo sobre handles seleccionados
6. ⏳ **Demo con marca real** — Nestlé o similar

---

## Para Opus 5 — Última Auditoría

La auditoría más reciente con análisis técnico completo es **`LENS_REUNION_2026-08-20.md`** (documento de 255 líneas escrito por Opus 5 tras auditar `LENS_ASESORIA_INGENIERO_2026-08-20.md`).

Contiene:
- Bug crítico: modo Analizar repetía ~$0.64 de discovery por `parent_run_id` descartado en schema
- Fix: 1 línea en `DiscoverySearchRequest` + 1 línea de `default_factory=`
- 4 bugs del Hito 26 verificados como correctamente corregidos
- **5 correcciones a la documentación** identificadas por Opus 5:
  1. Bug 1 del Hito 26 documentado con código incorrecto
  2. "Tasa de éxito 80%" — dato inventado, pendiente de medir
  3. "Modo Explorar — Sin Costo" — debería decir "Barato"
  4. `discovery_mode` hardcodeado en LensSearchPage.tsx, no hay selector
  5. Costo campaña completa: ~$0.34 (no $0.67 como decía antes)
- Recomendación de recarga: **$20** (no $50)

**Recomendación:** Leer `LENS_REUNION_2026-08-20.md` y `LENS_ASESORIA_INGENIERO_2026-08-20.md` para contexto completo.

---

*Índice generado: 2026-08-20 — Proyecto LENS con 27 hitos aplicados, 1 candidato histórico, $28.33 gastados. Hito 27: fix modo Analizar + 5 correcciones a la documentación.*