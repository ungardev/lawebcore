# SEXTA AUDITORÍA — LENS Discovery Module (Análisis Post-Test Run Real)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Solicitud:** Después de aplicar Hito 21, ejecutamos un test run real. Los resultados revelan bugs críticos que necesitan fixes precisos. Necesitamos que analices el código, confirmes nuestros hallazgos, y nos des los fixes exactos para cada problema.
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI "Start" ($0.02/req) + DeepSeek

---

## CONTEXTO — QUÉ PASÓ

Ejecutamos un test run el 2026-08-17 con saldo real de HikerAPI. El run terminó en `status=completed` con **0 candidatos** a pesar de encontrar **123 handles**. Aquí está el desglose:

### Datos del Run

```
Run ID: 1a1d6128-d1e4-4922-b7c7-1c2cb949c658
Status: completed
total_candidates: 0
accepted: 0
actual_cost_usd: 0.0          ← Bug: no se persiste
total_unique_handles: 123       ← Discovery encontró handles
keywords_count: 20              ← Muchas variaciones de keywords
step3_degraded: false            ← Enrichment no falló
replay_miss_count: 0
completed_steps: todos los steps ejecutaron
```

### Redis Después del Run

```
GET lens:budget:hikerapi:2026-08
"1.64"                          ← 82 calls × $0.02 = $1.64 ✅

GET lens:budget:run:1a1d6128-d1e4-4922-b7c7-1c2cb949c658
(nil)                           ← NO EXISTE ❌
```

### Lo Que Esto Significa

1. **82 calls facturadas** = ~31 discovery + ~50 enrichment (modelo viejo de doble conteo parcial)
2. **No existe `lens:budget:run:{id}`** → el worker estaba ejecutando código **PRE-Hito 21**
3. **0 candidatos** = pipeline encontró handles pero todos fueron filtrados en scoring
4. **actual_cost_usd = 0.0** = no se persistió el costo del run

---

## HALLAZGO #1 — Worker Con Código Viejo (🔴 CRÍTICA)

**Problema:** El ARQ worker no recargó el código después del deploy. El proceso mantiene el código en memoria — Railway deployó pero el worker seguía con la versión pre-Hito 21.

**Evidencia:**
- `lens:budget:run:{id}` no existe (Hito 21 crea esta key)
- 82 calls facturadas pero sin run counter específico

**Fix necesario:** Redeploy de Railway para reiniciar el worker ARQ.

**Pero esto reveló OTROS BUGS que estaban latentes:**

---

## HALLAZGO #2 — 123 Handles, 0 Candidatos (🔴 CRÍTICA)

**Problema:** El pipeline descubre 123 handles pero **todos son filtrados** en la fase de scoring. Nunca se inserta ninguno en `discovery_candidates`.

**Causa más probable identificada:** El filtro `geo_no_signal` en worker.py línea 1119:

```python
if geo_indicators and geo < 0.4 and not has_hard_geo_signal(p, target_country):
    geo_no_signal += 1
    continue
```

**Por qué filtra el 100%:**
- Perfiles de hashtag tienen: bio vacía, country vacío, locationName vacío
- `geo_score()` devuelve 0.0 (no hay nada que matchear)
- `has_hard_geo_signal()` retorna False (sin señales duras de VE)
- Condición: `True and True and True` → **FILTRADO**

**Sources afectadas:**
- `search_hashtag()` → usuario REDUCIDO (sin bio ni followers)
- `search_hashtag_recent()` → usuario REDUCIDO
- `search_reels_by_keyword()` → usuario REDUCIDO

**Sources NO afectadas:**
- `search_keyword()` → usuario COMPLETO (con bio y followers)
- `search_top_accounts()` → usuario COMPLETO
- `suggested_profiles()` → usuario COMPLETO

**Fix necesario:** El filtro `geo_no_signal` no debería aplicar a fuentes que inherently no tienen bio/location (hashtag/reels). O debe haber un fallback: si el handle viene de hashtag y tiene `followers > threshold`, debe pasar aunque geo_score sea bajo.

---

## HALLAZGO #3 — actual_cost_usd No Se Persiste (🔴 CRÍTICA)

**Problema:** Después de Hito 21, `record_call()` ya no se llama en el worker. El costo total del run no se está grabando en `discovery_runs.actual_cost_usd`.

**Causa:** Hito 21 centralizó todo el accounting en `HikerAPIClient._get()`. El worker ya no llama `record_call()` después de enrichment. No hay ningún código que lea `lens:budget:run:{id}` y lo persiste en la DB.

**Fix necesario:** Al final del `discovery_run_task`, después de que el run completa, leer `lens:budget:run:{run_id}` de Redis y grabar `actual_cost_usd` en `discovery_runs`.

```python
# Al final del run, después de upsert_many:
run_key = f"lens:budget:run:{run_id}"
r = await redis.get(run_key)
call_count = int(r or 0)
actual_cost = call_count * settings.HIKERAPI_COST_PER_CALL_USD
await railway_pg.update(
    table="discovery_runs",
    filters=[f"id=eq.{run_id}"],
    values={"actual_cost_usd": actual_cost}
)
```

---

## HALLAZGO #4 — accepted Nunca Se Actualiza (🔴 CRÍTICA)

**Problema:** `discovery_runs.accepted` permanece en `0` siempre — nunca se actualiza cuando un candidato se marca como "saved".

**Causa:** El endpoint `PUT /discovery/candidates/{id}/status` actualiza el status del candidato pero NO hace `UPDATE discovery_runs SET accepted = accepted + 1`.

**Fix necesario:** En el endpoint que marca un candidato como "saved", hacer un trigger o update directo del counter en `discovery_runs`.

---

## HALLAZGO #5 — Prefiltro Débil, enrichment sobre muestra casi aleatoria (🔴 ALTA)

**Problema:** Antes del enrichment, el prefilter selecciona los top 50 handles basándose en scoring sin datos completos (sin bio para hashtag/reels). El enrichment se hace sobre una muestra que no representa los mejores candidatos.

**Causa:** El scoring en el prefilter usa `rough = 0.5 * geo + 0.5 * niche` pero para hashtag profiles con bio vacía, ambos valores son 0.5 por defecto → el orden es casi aleatorio.

**Fix necesario (Hito 23 propuesto):**
- Apagar hashtag-top, hashtag-recent, reels (las 3 fuentes con perfil reducido)
- Quedarse solo con keyword, topsearch, suggested (que dan perfil completo)
- Bajar enrichment a 25 handles
- Resultado: $0.74/run en vez de $1.62/run, y calidad más alta

---

## HALLAZGO #6 — keys de Redis Solo Monthly, No Run-Specific (⚠️ INVESTIGAR)

**Problema:** Después del test run, solo existe `lens:budget:hikerapi:2026-08`. No hay key de run específico.

**Dos posibilidades:**
1. El worker viejo (pre-Hito 21) nunca creó la key de run
2. El formato de la key cambió en Hito 21

**Necesitamos confirmar:** Después de un deploy con Hito 21 activo, ¿se crea `lens:budget:run:{id}`? Si no, hay un bug en cómo `reserve_and_record()` crea la run key.

---

## RESUMEN DE BUGS PARA OPUS 5

| # | Bug | Gravedad | Archivo | Línea | Fix Pendiente |
|---|-----|----------|---------|-------|---------------|
| 1 | Worker con código pre-Hito 21 | 🔴 CRÍTICA | Infra | Railway | Redeploy worker ARQ |
| 2 | geo_no_signal rechaza 100% hashtag profiles | 🔴 CRÍTICA | worker.py | 1119 | Fallback para fuentes sin bio |
| 3 | actual_cost_usd no se persiste | 🔴 CRÍTICA | worker.py | ~1400 | Leer run_key y persistir al final |
| 4 | accepted siempre 0 | 🔴 CRÍTICA | discovery.py | ~800 | Actualizar counter al guardar |
| 5 | Prefiltro débil (scoring sin data) | 🔴 ALTA | worker.py | ~800 | Hito 23: apagar fuentes reducidas |
| 6 | Run-specific Redis key no se crea | ⚠️ INVESTIGAR | budget_fuse.py | — | Verificar tras redeploy |

---

## PLAN DE VERIFICACIÓN POST-REDEPLOY

Después de hacer redeploy en Railway:

1. **Lanzar nuevo test run** con brief simple:
```json
{
  "product_name": "Test post-redeploy",
  "industry": "belleza",
  "niches": ["skincare", "haircare"],
  "platforms": ["instagram"],
  "audience_countries": ["VE"],
  "max_candidates": 10,
  "analyze_with_ai": false
}
```

2. **Verificar Redis** después del run:
```bash
GET lens:budget:hikerapi:2026-08    # Costo monthly
GET lens:budget:run:{nuevo_run_id}   # Costo del run específico
```

3. **Verificar candidatos**:
```bash
curl "https://lawebcore-production.up.railway.app/api/v1/lens/discovery/runs/{nuevo_run_id}/candidates?limit=100"
```

4. **Esperado con Hito 21 activo:**
   - `lens:budget:run:{id}` existe con valor = número de calls
   - `actual_cost_usd` se persiste en la DB después del run
   - Algunos candidatos sobreviven el scoring (aunque sean pocos)

---

## PREGUNTAS PARA OPUS 5

### Pregunta 1 — Fix exacto del geo_no_signal
¿Cómo modificamos el filtro de la línea 1119 para que NO rechace perfiles de hashtag/reels que tienen `followers > 5000` aunque tengan geo_score = 0.0? Necesitamos el código exacto.

### Pregunta 2 — Persistencia de actual_cost_usd
¿Cuál es la ubicación exacta en worker.py donde debemos agregar el código para leer `lens:budget:run:{id}` y persistir `actual_cost_usd`? Hay que hacerlo al final del run, después de `_deduplicate_and_insert_candidates()`.

### Pregunta 3 — accepted counter
¿Cuál es el mejor lugar para actualizar `discovery_runs.accepted` — en el endpoint `PUT /discovery/candidates/{id}/status` o con un trigger en la DB?

### Pregunta 4 — Hito 23 viability
¿Es viable implementar Hito 23 (apagar hashtag-top/recent/reels) sin perder demasiada cobertura de descubrimiento? ¿Cuántos candidatos únicos esperamos perder?

### Pregunta 5 — Tests
¿Podemos añadir tests que validen que los candidatos de hashtag/reels con followers altos sobreviven el scoring aunque tengan bio vacía?

---

## CÓMO PROCEDER

1. **Primero:** Hacer redeploy de Railway para activar Hito 21
2. **Segundo:** Lanzar test run post-redeploy y verificar que `lens:budget:run:{id}` se crea
3. **Tercero:** Implementar fixes de Opus 5 para los bugs 2, 3, 4
4. **Cuarto:** Implementar Hito 23 si Opus 5 lo aprueba
5. **Quinto:** Tests y validación final

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
Docs:          https://github.com/ungardev/lawebcore/tree/main/docs
```

**Credenciales en localStorage (`laweb_token`):**
```
ungar.villamizar@hacemosloquenosgusta.com
Rol: admin_general
```

---

## ARQUITECTURA ACTUAL (worker.py ~1836 líneas)

```
DeepSeek → BriefStructured → QueryBuilder → DiscoveryPlan
                                              ↓
                        ┌─ STEP 1: Hashtag Top (3×)     → usuario REDUCIDO
                        ├─ STEP 1_recent (2×)           → usuario REDUCIDO
                        ├─ STEP 2: Keyword (3×3)         → usuario COMPLETO ✅
                        ├─ STEP 2p5: Reels (1×)          → usuario REDUCIDO
                        ├─ STEP 3: Topsearch (1×2)      → usuario COMPLETO ✅
                        └─ STEP 4: Suggested (1×)       → usuario COMPLETO ✅
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

## CANDIDATOS PARA OPUS 5

Te pasamos todo en bandeja:

1. **ARQUITECTURA_LENS.md v3.5** — toda la documentación actualizada con los hallazgos del test run
2. **Repo completo** — https://github.com/ungardev/lawebcore en commit `7b3bc5d`
3. **Redis** — accesible via Railway Redis addon
4. **PostgreSQL** — accesible via Railway PostgreSQL addon

**Lo que necesitamos de vos:**
1. Fix exacto para geo_no_signal (línea 1119 de worker.py)
2. Código exacto para persistir actual_cost_usd al final del run
3. Fix para accepted counter
4. Evaluación de Hito 23 (apagar fuentes reducidas)
5. Cualquier otro bug que encuentres en el código

**Sé brutalmente honesto. El sistema tiene 21 hitos aplicados pero 0 candidatos producción. Necesitamos los fixes, no la teoría.**

---

*Documento generado: 2026-08-17 — Sexta auditoría LENS post-test-run-real*
*Repo: https://github.com/ungardev/lawebcore | Commit: 7b3bc5d*
*Para: Claude Code Opus 5 / Senior Full-Stack Developer*
