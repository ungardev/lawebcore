# LENS · FIXES — Resiliencia Railway (worker muerto + cron diario)
## 04/05-09-2026 · La Web Figital Agency

> **Origen:** Ungar detecta errores en Railway Deploy Logs ANTES de correr el E2E vía UI. Instinto correcto: sin estos fixes el E2E habría fallado silenciosamente.

---

## INCIDENTE 1 — 🔴 CRÍTICO: Worker de discovery MUERTO desde 23:17

```
Process arq-worker: redis.exceptions.ConnectionError: Connection reset by peer
→ el proceso arq-worker murió por completo
```

**Causa raíz:** el loop de polling de arq NO captura `ConnectionError`. Un blip de red del proxy Redis de Railway (`hopper.proxy.rlwy.net`) mató el proceso completo.

**Por qué era silencioso y permanente:** el worker corre como proceso daemon dentro del contenedor de la API (`main.py` lifespan). La API seguía sirviendo `/health → 200` → Railway nunca reinicia el contenedor → **cero workers vivos**: cualquier discovery run quedaba `queued` para siempre.

**FIX (main.py):** `arq_worker_supervised()` — bucle que relanza `run_worker` ante `ConnectionError/TimeoutError/OSError` con backoff (5s→60s, tope 60s). Pool nuevo en cada intento. Errores fatales de código sí abortan (con traceback). 3 tests: blip→reconecta, fatal→propaga, salida limpia.

## INCIDENTE 2 — 🟡 Cron diario 09:00 falla (j_failed=1 diario)

```
SELECT ... WHERE is_active = $1 | PARAMS: ['true']
DataError: a boolean is required (got type str)
```

**Causa raíz:** `railway_pg._parse_filters` convertía `is_active=eq.true` en un parámetro STRING; asyncpg exige bool real para columnas booleanas.

**FIX (railway_pg.py):** `_maybe_parse_datetime` ahora coerciona literales PostgREST `true/false` → `True/False` (aplica a eq, gte/lte/gt/lt e in). `scheduled_reports_cron` (stub que solo loguea) blindado con try/except para que jamás ensucie el health.

## BONUS — Bug latente descubierto y corregido: `col=in.(...)` con "="

La forma PostgREST `handle=in.('a','b')` **contiene "="** → caía en la rama eq de `_parse_filters` y se trataba como **igualdad contra el string literal `"('a','b')"` → 0 filas siempre**. El modo **Analizar** construye exactamente ese filtro para cargar los handles del run padre (`discovery.py`) → analyze mode habría devuelto 0 perfiles silenciosamente.

**FIX:** la rama eq detecta valores `(...)` y los expande a `IN ($1,$2)` con coerción de tipos.

## VERIFICACIÓN

| Check | Resultado |
|---|---|
| `test_infra_resilience.py` (nuevo) | **13/13** — coerción (eq true/false, in dot-form, in con "=", strings/datetime/uuid intactos, "true-story" no coerciona), cron blindado, supervisor (blip/fatal/limpio) |
| Suite completa | **223 passed** (+13), 7 failed = baseline pre-cambios intacto |
| ruff | 0 errores nuevos (los 9 señalados son pre-existentes en railway_pg.py: G201/BLE001) |

## OPERACIÓN POST-DEPLOY

1. Deploy Railway → contenedor fresco = worker vivo de nuevo (el supervisor previene recurrencia).
2. Verificar en logs: `arq_worker_started_as_separate_process` + ante el próximo blip de Redis: `arq_worker_connection_blip_restarting` (y el worker sobrevive).
3. Mañana 09:00 UTC: `scheduled_reports_cron_running` sin `j_failed`.
4. **Recién entonces: E2E vía UI** (~$1.45, mascotas/VE).

---

## ⚠️ CORRECCIÓN v2 (07-sep-2026): el supervisor v1 tenía un bug — worker muerto AL ARRANCAR

El deploy del 07-sep (14:22 UTC) mostró el supervisor v1 muriendo en el arranque:

```
main.py:65  await run_worker(WorkerSettings)
arq/worker.py:899  run_worker: worker.run()
arq/worker.py:313  self.loop.run_until_complete(self.main_task)
RuntimeError: This event loop is already running
```

**Causa raíz (bug de la v1):** `run_worker` de arq es **SYNC** — crea y maneja su propio event loop (`worker.run()` → `run_until_complete`). La v1 lo envolvió en `async def` + `asyncio.run(...)`: el await evaluaba la llamada síncronamente con un loop ya corriendo → RuntimeError → `except Exception: raise` → **el proceso moría al arranque** → producción quedó SIN worker otra vez (no aparecía "Starting worker for 5 functions" en los logs).

**Por qué los tests no lo detectaron:** el fake era `async def fake_run_worker` — validaba el contrato equivocado. Lección: el fake debe replicar el contrato REAL de la librería, no el de nuestra abstracción.

**FIX v2:** supervisor **sync puro** — `run_worker(WorkerSettings)` directo (bloquea con su propio loop, idéntico al código original que funcionó en producción), `time.sleep(backoff)` ante blips (bloquear el thread es correcto: el proceso existe solo para el worker), y **event loop NUEVO por intento** (`asyncio.new_event_loop()` + close en finally) para no heredar loops cerrados. `_arq_worker_entry` llama directo, sin `asyncio.run`.

**Tests v2 al contrato real:** fake **sync** de `run_worker` + patch de `time.sleep` — 4 casos: blip→reconecta, OSError(104)→reconecta, fatal→propaga, salida limpia. 14/14 en el archivo, 224 passed en la suite.

**Verificación post-deploy v2 (el check exacto que falló hoy):**
```
Starting worker for 5 functions: discovery_run_task, ...   ← DEBE aparecer tras el arranque
```

---

*GLM 5.3 Flash (opencode) · 04/05/07-sep-2026*
