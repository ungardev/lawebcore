# PROMPT_CLAUDE_CODE_ANALYSIS — Índice de Auditorías LENS

> **Última actualización:** 2026-08-20
> **Repositorio:** https://github.com/ungardev/lawebcore

Este documento es un **índice histórico** de las auditorías de LENS Discovery. La auditoría más reciente y completa es **`LENS_ASESORIA_INGENIERO_2026-08-20.md`** (documento de ingeniería para advisor — sesión 2026-08-20 con 4 bugs críticos corregidos).

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
| **10** | **`LENS_ASESORIA_INGENIERO_2026-08-20.md`** | **2026-08-20** | **MiniMax + usuario** | **4 bugs críticos corregidos — dict columnas, frontend mode, polling, ledger try/except** |

---

## Estado Actual del Proyecto

### Hitos Aplicados (1-26)

```
1-20: Features y fixes varios
21:   Single accounting point + fail-closed
22:   actual_cost_usd persistence + PARTIAL enum
23:   Pre-flight balance + except SourceUnavailable raise + _build_zero_candidates_message
24:   Modo Explorar + Modo Analizar
25:   Fix get_balance() parser — detecta state:false → retorna 0.0
26:   4 bugs críticos corregidos — dict columnas DB, frontend discovery_mode, polling explored, ledger try/except
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
| HikerAPI balance | 🔴 $0 — requiere recarga $50 |

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
2. ⏳ **Recargar $50 HikerAPI** — mínimo según billing
3. ⏳ **Test Modo Explorar** — validar status=`explored`, candidatos con handle+bio populated
4. ⏳ **Test Modo Analizar** — validar enrichment selectivo sobre handles seleccionados
5. ⏳ **Demo con marca real** — Nestlé o similar

---

## Para Opus 5 — Última Auditoría

La auditoría más reciente con datos empíricos completos y sesión de debugging detallada es **`LENS_ASESORIA_INGENIERO_2026-08-20.md`**.

Contiene:
- 48 runs históricos con costos reales
- Bug del parser `get_balance()` identificado y arreglado (Hito 25)
- Desfase Redis↔DB de $25.13 documentado
- **4 bugs críticos descubiertos y corregidos en la sesión 2026-08-20:**
  1. Dict candidato con claves incorrectas (columnas DB)
  2. Frontend no enviaba `discovery_mode`
  3. Polling no cargaba candidatos en status `explored`
  4. Ledger crash sin migration 00107
- Railway deploy exitoso (18:26 UTC) + Vercel deploy exitoso (11:30 UTC)
- Migration 00106 confirmada aplicada

**Recomendación:** Leer `LENS_ASESORIA_INGENIERO_2026-08-20.md` completo antes de dar nuevas recomendaciones sobre recarga de HikerAPI.

---

*Índice generado: 2026-08-20 — Proyecto LENS con 26 hitos aplicados, 1 candidato histórico, $28.33 gastados, 4 bugs críticos corregidos en sesión 2026-08-20.*