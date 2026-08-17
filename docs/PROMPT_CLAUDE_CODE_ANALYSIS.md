# SEXTA AUDITORÍA — LENS Discovery Module (Análisis Post-Test Run Real — CORREGIDO)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Solicitud:** Después de aplicar Hito 21, ejecutamos un test run real con saldo real. El log completo del worker revela 3 bugs exactos. Necesitamos que los confirmes y nos des los fixes precisos.
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI "Start" ($0.02/req) + DeepSeek

---

## CONTEXTO — QUÉ PASÓ (DEL LOG REAL)

```
Run ID: 1a1d6128-d1e4-4922-b7c7-1c2cb949c658
Worker: Hito 21 activo ✅ (115 handles encontrados, no 123 como dijimos antes)
Status en DB: partial
Pipeline: CORRIÓ completo hasta el final
Costo HikerAPI: ~$1.62 (~81 requests)
GET /runs/{id}: 500 Internal Server Error ❌
actual_cost_usd en DB: 0.0 ❌
Enrichment: step3_degraded=true (402 Payment Required)
```

### Del Log Completo (-lineas relevantes):

```
[DISCARD] hikerapi_balance_before=$5.00
[DISCARD] hikerapi_balance_after=$3.38
DiscoveryRun task started for brief_id=abc123
_build_brief: DeepSeek parseó el brief en 1.8s
QueryBuilder.build: 3 hashtags, 20 keywords, 2 reels, 1 topsearch, 1 suggested
STEP 1: Running hashtag search for 3 hashtags
STEP 1_recent: Running recent hashtag search
STEP 2: Running keyword search for 20 keywords
STEP 2p5: Running reels search
STEP 3: Enriching 50 profiles (HikerAPI)
  └─ 402 Payment Required para varios handles ❌
STEP 4: Scoring 50 candidates
STEP 5: Skipping AI analysis (analyze_with_ai=False)
Upserted 0 candidates (0 survived scoring)
UPDATE discovery_runs SET actual_cost_usd=$1 WHERE id = $2 vals=[0]
```

---

## HALLAZGO #1 — Pydantic enum sin `partial` (🔴 CRÍTICA — 500 Error)

**Problema:** `GET /api/v1/lens/discovery/runs/{run_id}` devuelve 500 porque Pydantic no reconoce `status='partial'`.

**Archivo:** `packages/discovery/discovery/schemas.py` líneas 11-16

```python
# ACTUAL — falla con ValidationError:
class DiscoveryRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # ← FALTA PARTIAL

# FIJO:
class DiscoveryRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # ← AGREGAR ESTA LÍNEA
```

**Causa raíz:** La migración `00000000000104_*` añadió `partial` a la columna PostgreSQL `discovery_run_status` pero se olvidó de actualizar el enum de Pydantic en `schemas.py`.

**Fix exacto:** Agregar `PARTIAL = "partial"` al enum `DiscoveryRunStatus`.

---

## HALLAZGO #2 — `actual_cost_usd` siempre 0 (🔴 CRÍTICA)

**Problema:** `actual_cost_usd` se graba como `0.0` en la DB a pesar de que HikerAPI facturó ~$1.62.

**Causa raíz — Sistema de costos fragmentado en 3 silos:**

```
┌─────────────────────────────────────────────────────────────┐
│ HikerAPIClient (hikerapi_client.py)                         │
│  - enrich_profile(), search_hashtag(), etc.                 │
│  - NO tiene método record_cost()                            │
│  - NO graba costos en ningún lado                          │
└─────────────────────────────────────────────────────────────┘
                            ↓ (nunca se conecta)
┌─────────────────────────────────────────────────────────────┐
│ ApifyClient (apify_client.py)                               │
│  - record_cost() → guarda en self._costs (in-memory dict)  │
│  - sgtotal_cost(), get_and_clear_cost()                    │
│  - PERO es una instancia distinta al tracker del worker    │
└─────────────────────────────────────────────────────────────┘
                            ↓ (nunca se conecta)
┌─────────────────────────────────────────────────────────────┐
│ DiscoveryCostTracker (discovery_cost_tracker.py)            │
│  - get_run_summary() → lee de _apify_costs y _deepseek_costs│
│  - Worker usa ESTE tracker al final del run                │
│  - NUNCA recibe costos de HikerAPIClient                  │
└─────────────────────────────────────────────────────────────┘

Worker líneas 1463-1472:
  tracker = get_discovery_cost_tracker()      # nueva instancia
  cost_summary = tracker.get_run_summary(run_id)
  total_cost = cost_summary["total_usd"]      # 0.0 ← SILO
  await railway_pg.update(
      table="discovery_runs",
      values={"actual_cost_usd": total_cost},  #写入 0.0
      ...
  )
```

**Fix exacto — dos opciones:**

**Opción A (recomendada):** Que `HikerAPIClient` use `DiscoveryCostTracker` directamente. El challenge es que `HikerAPIClient` no recibe el `tracker` como parámetro — necesitaría pasarlo desde el worker u orquestador.

**Opción B (quick fix):** El worker al final del run llama a `hikerapi_client.get_total_cost()` si existiera, pero no existe.

**Opción C (correcta arquitectura):** Crear un singleton de costo que `HikerAPIClient` y `DiscoveryCostTracker` compartan. O hacer que el worker pase el tracker al `HikerAPIClient`.

---

## HALLAZGO #3 — Balance agotado en enrichment (⚠️余额不足)

**Problema:** Los $5 de HikerAPI se gastan casi todo en discovery (~81 requests). Cuando llega el enrichment de 50 profiles, el balance es insuficiente → `402 Payment Required`.

**Del log:**
```
hikerapi_balance_before=$5.00
hikerapi_balance_after=$3.38
# Ya se gastaron $1.62 antes del enrichment

Enrichment: 402 Payment Required para varios handles
step3_degraded: true
```

**Fix sugerido:**
1. Reducir handles a enriquecer (prefilter más agresivo a top 20)
2. O aumentar balance antes de test runs
3. O trackear el balance restante antes de enrichment y ajustar el batch size dinámicamente

---

## RESUMEN DE BUGS PARA OPUS 5

| # | Bug | Gravedad | Archivo | Línea | Fix |
|---|-----|----------|---------|-------|-----|
| 1 | Pydantic enum sin `partial` | 🔴 CRÍTICA | `schemas.py` | 11-16 | Agregar `PARTIAL = "partial"` al enum |
| 2 | `actual_cost_usd = 0` (silos de costo) | 🔴 CRÍTICA | `hikerapi_client.py` + `discovery_cost_tracker.py` | — | Conectar HikerAPIClient al cost tracker |
| 3 | Balance insuficiente en enrichment | ⚠️ | Pipeline design | — | Reducir handles o aumentar balance |

---

## PLAN DE VERIFICACIÓN POST-FIX

Después de que Opus 5 aplique los fixes:

1. **Fix Bug 1:** `GET /runs/{id}` debe devolver `200` con `status="partial"` sin ValidationError
2. **Fix Bug 2:** Nuevo test run — `actual_cost_usd` debe ser > 0 después del run
3. **Fix Bug 3:** Verificar que enrichment no reciba 402 (balance suficiente)

---

## CÓMO PROCEDER

1. **Opus 5:** Apply fixes a los 3 bugs
2. **Nosotros:** Redeploy en Railway
3. **Nuevo test run** con balance充值 de HikerAPI
4. **Verificar:** `GET /runs/{id}` → 200, `actual_cost_usd` > 0, enrichment sin 402

---

## ARQUITECTURA ACTUAL (worker.py ~1836 líneas)

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

## INFRAESTRUCTURA ACTUAL

```
GitHub:        https://github.com/ungardev/lawebcore
Repo actual:   commit 7b3bc5d (Hito 21 aplicado)
Backend:       Railway — lawebcore-production
Frontend:      Vercel — lawebcore.vercel.app
PostgreSQL:    Railway (postgres.railway.internal:5432/railway)
Redis:         Railway (ARQ + cache + budget)
API:           https://lawebcore-production.up.railway.app/api/v1
```

**Credenciales en localStorage (`laweb_token`):**
```
ungar.villamizar@hacemosloquenosgusta.com
Rol: admin_general
```

---

## LO QUE NECESITAMOS DE OPUS 5

**Sé brutalmente honesto. El sistema tiene 21 hitos aplicados pero 0 candidatos producción. Necesitamos:**

1. **Fix Bug 1 (5 min):** Agregar `PARTIAL = "partial"` al enum `DiscoveryRunStatus`
2. **Fix Bug 2 (30-60 min):** Diseñar e implementar la conexión entre `HikerAPIClient` y el sistema de costo. Necesitamos que cada llamada a HikerAPI grabe su costo en algún lado que el worker pueda leer al final.
3. **Fix Bug 3 (quick):** Reducir handles a enriquecer o aumentar balance
4. **Cualquier otro bug** que encuentres en el código mientras investigas

**La recompensa:** El pipeline de discovery más caro y complejo que hemos construido, funcionando en producción por primera vez.

---

*Documento generado: 2026-08-17 — Sexta auditoría LENS post-test-run-real CORREGIDO (3 bugs confirmados del log)*
