# SÉPTIMA AUDITORÍA — LENS Discovery Module (Post-Hito 22)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI "Start" ($0.02/req) + DeepSeek

> ⚠️ **NOTA DE CORRECCIÓN (Hito 23):** Esta auditoría fue corregida por Opus 5. El Bug N1 estaba equivocado — la causa real de 0 candidatos era enrichment fallido con 402, no `exclude_stores`. Ver `LENS_AUDIT7_2026-08-18.md` para el análisis completo de Opus 5. Esta versión se mantiene como registro histórico del análisis original.

---

## CONTEXTO — QUÉ PASÓ

### Hito 22 aplicado (commit `7e4a99b`)

Después de la Sexta Auditoría, el equipo aplicó Hito 22 con los fixes de los 3 bugs críticos:
- Bug 1: `PARTIAL = "partial"` añadido al enum Pydantic ✅
- Bug 2: Método `get_run_calls()` en `budget_fuse.py` + worker actualiza `actual_cost_usd` ✅
- Redeploy en Railway — worker recargó código ✅

### Test Run Real Hito 22 (Run ID: `0c44ea23-53f6-42a8-8a9c-c6ec85359d2e`)

**Fecha:** 2026-08-18, 19:50:56 → 19:52:40 UTC (110 segundos)

**Brief:**
```json
{
  "product_name": "Test Hito 22",
  "industry": "belleza",
  "niches": ["makeup", "skincare", "haircare", "nails", "beauty blogger", "belleza Venezuela"],
  "platforms": ["instagram"],
  "audience_countries": ["VE"],
  "exclude_stores": true,
  "analyze_with_ai": true
}
```

**Pipeline logs:**
```
[discovery_run_task] START run_id=0c44ea23-53f6-42a8-8a9c-c6ec85359d2e
[STEP1] 60 posts from hashtags source=hikerapi
[STEP2] 66 users from keywords source=hikerapi
[STEP1_RECENT] 40 posts from recent hashtag search
[STEP2p5_REELS] 0 creators from reels search
[STEP3] 0 accounts from topsearch
[STEP4] 0 accounts from suggested
[DIAG] unique_handles=133
[STEP 3] Profile enrichment (HTTP 402 Payment Required — balance agotado)
[SCORING] 0 scored → 0 score≥5 → 0 qualified (tienda_excluded=True)
[discovery_run_task] DONE total_candidates=0
```

**Resultados verificados:**

| Indicador | Resultado | Análisis |
|-----------|-----------|----------|
| `status` | `partial` | ✅ 200 OK — no más 500 Error |
| `actual_cost_usd` | **$1.64** | ✅ Cost tracking funcionando |
| `api_costs` insertado | **82 calls × $0.02** | ✅ Registro correcto |
| `total_unique_handles` | **133** | ✅ Discovery efectivo |
| `total_candidates` | **0** | ❌ Todos filtrados por `exclude_stores=true` |
| `step3_degraded` | `true` | ✅ Flag correcto (402 mid-enrichment) |

**Redis confirmadas:**
```
lens:budget:hikerapi:2026-08 = "1.64"
lens:budget:run:0c44ea23-53f6-42a8-8a9c-c6ec85359d2e = 82
```

---

## ESTADO DE BUGS ANTERIORES

| Bug # | Descripción | Estado |
|-------|-------------|--------|
| 1 | Pydantic enum sin `partial` | ✅ **RESUELTO** — `PARTIAL = "partial"` añadido |
| 2 | `actual_cost_usd = 0` (silos de costo) | ✅ **RESUELTO** — `$1.64` grabado correctamente |
| 3 | Balance insuficiente ($5 agotados rápido) | ⚠️ **PERSISTE** — HikerAPI balance = $0 remaining |

---

## 3 BUGS NUEVOS PARA OPUS 5

> ⚠️ **CORREGIDO por Opus 5:** El Bug N1 estaba equivocado. La causa real de 0 candidatos era el enrichment fallido con 402, no `exclude_stores`. Los fixes N2 y N3 fueron abordados parcialmente en Hito 23.

---

### BUG N1 — `exclude_stores` elimina 100% de handles en VE (❌ REFUTADO)

**Severidad:** N/A — Diagnóstico incorrecto.

**Lo que creíamos:** El filtro `exclude_stores=true` eliminaba el 100% de handles en VE porque "influencers de belleza" ≈ "tiendas".

**Lo que Opus 5 probó:**
- El log `tienda_excluded=True` es el **valor del flag de configuración**, NO un conteo de tiendas excluidas
- Los handles NUNCA fueron enriquecidos — el enrichment murió en la primera llamada con 402
- La causa real: `followers=0` para todos → filtrados en `worker.py:1054` → `0 scored`
- Los handles "de tiendas" (`shopmarianazambrano.ve`, etc.) aparecían en STEP1/STEP2 con perfiles REDUCIDOS (sin follower data)

**Veredicto:** NO es un bug. POSTERGADO hasta que el pipeline produzca candidatos con enrichment funcional.

---

### BUG N2 — Mensaje al usuario engañoso (✅ CORREGIDO EN HITO 23)

**Severidad:** ⚠️ MEDIA

**Problema original:** Mensaje fijo "filtro geográfico" sin importar la causa real.

**Fix aplicado (Hito 23):** `_build_zero_candidates_message()` deriva el mensaje del contador dominante:
- Si enrichment falló → "no pude completar la búsqueda"
- Si tiendas dominan → "X cuentas son comerciales"
- Si sin seguidores → "X no tienen seguidores"

---

### BUG N3 — Geolocalización sin validación post-enrichment (⚠️ POSTERGADO)

**Severidad:** ⚠️ MEDIA

**Problema:** `geo_indicators` no se validan contra bio post-enrichment.

**Decisión:** POSTERGADO — no hay candidatos aún para validar geo.

---

### BUG REAL — Run condenado sin pre-flight de saldo (🔴 CRÍTICA)

**Severidad:** 🔴 CRÍTICA — $3.26 desperdiciados en 2 runs.

**Problema:** BudgetFuse valida el presupuesto INTERNO de Redis, pero no el saldo REAL de HikerAPI. El run iniciaba discovery ($0.64) y moría en enrichment con 402. Sin enrichment, 0 candidatos garantizados.

**Costo confirmado:**
| Run | Costo | Resultado |
|-----|-------|-----------|
| `0c44ea23` (Hito 22) | **$1.64** | 0 candidatos |
| `1a1d6128` (pre-Hito 22) | **$1.64** | 0 candidatos |
| **Total** | **$3.26** | — |

**Fix aplicado (Hito 23):**
1. `except SourceUnavailable: raise` — 402 ya no se silencia
2. `get_balance()` pre-flight — aborta si saldo < costo estimado
3. `MAX_HANDLES_TO_ENRICH` 50→25 — reduce enrichment de $1.00 a ~$0.50

---

## CONTEXTO ECONÓMICO (Importante — CORREGIDO)

```
COSTO POR RUN (confirmado con datos reales):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Discovery (31 calls):    $0.62
Enrichment 50 handles:  $1.00
────────────────────────
Total típico:           $1.64 / run

CON OPTIMIZACIÓN HITO 23:
Enrichment 25 handles:  ~$0.50
Discovery + 25 handles: ~$1.14 / run
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HIKERAPI BALANCE:       $0 remaining ⚠️
TOTAL DESPERDICIADO:    $3.26 (2 runs condenados)
PARA 5 RUNS NECESITAS:  $10-15 USD mínimo
PARA 10 RUNS/MES:       $20-30 USD
```

⚠️ **$3.26 DESPERDICIADOS** en 2 runs que nunca podían producir candidatos (sin pre-flight de saldo). Con Hito 23, el próximo run que detecte saldo insuficiente abortará con $0 de gasto.

**Optimización Hito 23:** `MAX_HANDLES_TO_ENRICH` 50→25 reduce enrichment de $1.00 a ~$0.50 por run. Con $10: ~8-9 runs completos.

---

## PLAN DE VERIFICACIÓN POST-FIX (HITO 23 APLICADO)

**Después de aplicar Hito 23:**

1. **Pre-flight test (sin costo):** Run con `RUN_MODE=replay` — debe abortar en pre-flight si `balance=0`
2. **Recharge HikerAPI:** $10 mínimo
3. **Test con enrichment funcional:** Re-run con `exclude_stores=false`, verificar `total_candidates > 0`
4. **Verificar mensaje:** El mensaje debe nombrar la causa real (enrichment / tiendas / geo / sin seguidores)
5. **Bug N1 (exclude_stores):** POSTERGADO hasta paso 3 — no tiene sentido abordar hasta que haya candidatos

---

## CÓMO PROCEDER

1. **Opus 5:** Aplica fixes N1, N2, N3
2. **Nosotros:** Redeploy en Railway
3. **Nosotros:** Recargar HikerAPI (mínimo $10)
4. **Nuevo test run** con `exclude_stores=false`
5. **Verificar:** `total_candidates > 0`, mensaje claro, geo_score > threshold

---

## INFRAESTRUCTURA ACTUAL

```
Repositorio:    https://github.com/ungardev/lawebcore
Repo actual:    commit 7e4a99b (Hito 22 aplicado)
Backend:        Railway — lawebcore-production
Frontend:       Vercel — lawebcore.vercel.app
PostgreSQL:     Railway (postgres.railway.internal:5432/railway)
Redis:          Railway (ARQ + cache + budget)
API:            https://lawebcore-production.up.railway.app/api/v1
HikerAPI:       Balance $0 — necesita recarga
```

**Credenciales en localStorage (`laweb_token`):**
```
ungar.villamizar@hacemosloquenosgusta.com
Rol: admin_general
```

---

## ARQUITECTURA WORKER.PY ACTUAL

```
DeepSeek → BriefStructured → QueryBuilder → DiscoveryPlan
                                              ↓
                          ┌─ STEP 1: Hashtag Top (3×)     → usuario REDUCIDO
                          ├─ STEP 1_recent (2×)           → usuario REDUCIDO
                          ├─ STEP 2: Keyword (3×3)         → usuario COMPLETO
                          ├─ STEP 2p5: Reels (1×)          → usuario REDUCIDO
                          ├─ STEP 3: Topsearch (1×2)      → usuario COMPLETO
                          └─ STEP 4: Suggested (1×)       → usuario COMPLETO
                                                    ↓
                                PREFILTRO (top 50 por rough score)
                                                    ↓
                                ENRICHMENT (hasta 50 handles)
                                                    ↓
                                SCORING (geo + niche + lens_score)
                                                    ↓
                                INSERT → discovery_candidates
```

---

## LO QUE NECESITAMOS DE OPUS 5

**Sé brutalmente honesto. El sistema tiene 22 hitos aplicados pero 0 candidatos producción en VE (el mercado más importante). Necesitamos:**

1. **Fix N1 (exclude_stores VE) — 30-60 min:** Diseñar e implementar la solución para que el pipeline funcione en mercados donde "influencer de belleza" ≈ "tienda". Opcional: reducir MAX_HANDLES_TO_ENRICH para bajar costo.

2. **Fix N2 (mensaje engañoso) — 10 min:** Cambiar el mensaje final del worker para que diga "filtro tiendas" en vez de "filtro geográfico".

3. **Fix N3 (geo post-enrichment validation) — 30 min:** Implementar validación de geo_indicators contra bio del perfil después del enrichment.

4. **Cualquier otro bug** que encuentres en el código mientras investigas.

**La recompensa:** El pipeline de discovery más caro y complejo que hemos construido, funcionando en producción por primera vez con candidatos reales en VE.

---

*Documento generado: 2026-08-18 — Séptima auditoría LENS post-Hito-22-test-run-real. CORREGIDO: Bug N1 refutado por Opus 5 (causa real era enrichment 402). Hito 23 aplicado con pre-flight balance, except SourceUnavailable raise, _build_zero_candidates_message, MAX_ENRICH 50→25. Ver `LENS_AUDIT7_2026-08-18.md` para análisis completo de Opus 5.*
