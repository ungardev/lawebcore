# Hito 21 — Que el contador de presupuesto diga la verdad

> **Base:** commit `c295e86`
> **Parche:** `hito21.patch` (aplicar con `git apply`)
> **Archivos tocados:** 3 · **+81 / −38 líneas**
> **Verificado:** los tres archivos compilan (`py_compile`). Tests pendientes de tu visto bueno.

---

## Qué arregla

| Bug (auditoría 5) | Estado |
|---|---|
| §2.1 Doble conteo del gasto mensual en enrichment | ✅ |
| §2.2 Las llamadas servidas desde caché también cobran | ✅ |
| §2.3 `evalsha` sin fallback `NOSCRIPT` | ✅ |
| §2.4 `fail open` peligroso a $0.02/call | ✅ |
| §2.5 `MAX_CALLS_PER_RUN` solo cubría enrichment | ✅ (efecto colateral del rediseño) |
| §2.7b Default `cost_per_call_usd = 0.0006` | ✅ |
| §2.7d Docstring con precio legado | ✅ |

---

## La decisión de diseño

El problema de fondo no era el doble conteo en sí, sino que **había dos puntos de contabilidad** que se fueron desincronizando: `reserve_and_record()` en el worker y `record_call()` en el cliente.

La corrección no es restarle una suma a uno de los dos: es **dejar un solo punto**.

**Antes:**
```
worker._enrich_one()
    └── reserve_and_record()  → contador del run + gasto mensual
        └── enrich_profile()
            └── _get()
                ├── ¿caché? → return (sin registrar, pero ya cobrado arriba)
                └── HTTP → record_call() → gasto mensual OTRA VEZ
```

**Ahora:**
```
worker._enrich_one()
    └── enrich_profile()
        └── _get()
            ├── ¿breaker abierto? → SourceUnavailable
            ├── ¿caché? → return (sin cobrar)
            ├── ¿replay? → ReplayMiss (sin cobrar)
            └── reserve_and_record()  ← ÚNICO punto de cobro
                └── HTTP
```

`_get()` es el único sitio por el que pasan todas las llamadas y el único que sabe si hubo petición real. Poner ahí la contabilidad resuelve los tres bugs a la vez.

**Beneficio no buscado:** como `_get()` es universal, ahora las 31 llamadas de descubrimiento **también** consumen cupo del run. Antes solo lo hacía el enrichment, así que el límite era decorativo (§2.5).

---

## Cambios por archivo

### `apps/api/app/core/budget_fuse.py`

1. **Docstring** — documenta el modelo de contabilidad y advierte explícitamente de no llamar `record_call()` para una petición que ya pasó por `reserve_and_record()`.
2. **Default** `cost_per_call_usd: 0.0006 → 0.02`.
3. **Fallback `NOSCRIPT`** — si Redis se reinicia o se ejecuta `SCRIPT FLUSH`, el SHA desaparece. Ahora se detecta y se reintenta con `eval()`, que vuelve a registrar el script:
   ```python
   except Exception as e:
       if "NOSCRIPT" not in str(e).upper():
           raise
       self._lua_sha = None
       result = await r.eval(self._RESERVE_AND_RECORD_SCRIPT, ...)
   ```
4. **Fail closed** — ante error de Redis, `return False` en vez de `True`. Redis ya es dependencia dura (ARQ no funciona sin él), así que bloquear no cuesta disponibilidad, y a $0.02/call un fusible que se autodesactiva puede quemar el presupuesto mensual en un run.

El script Lua **no se tocó**: ya era atómico y correcto. Sigue haciendo ambos incrementos, que ahora es lo apropiado porque es el único punto de cobro.

### `packages/discovery/discovery/tools/hikerapi_client.py`

1. Eliminada la función interna `_record_if_applicable()` y sus **7 llamadas**.
2. Añadida la reserva justo antes del `client.get()`, después de la caché y del breaker.
3. Si la reserva falla, lanza `BudgetExhausted`.

### `apps/api/app/workers/worker.py`

1. Eliminada la llamada a `reserve_and_record()` de `_enrich_one()` (ya redundante).
2. `except BudgetExhausted: raise` en `_enrich_one` — sin esto el `except Exception` genérico se lo tragaba.
3. Tras el `gather`, se cuentan los `BudgetExhausted` y el run se marca **degradado** (`partial`) en vez de fallar:
   ```python
   if budget_capped:
       step3_degraded = True
       step3_error = f"Tope de {MAX_CALLS_PER_RUN} llamadas alcanzado: {budget_capped} perfiles sin enriquecer."
   ```
   Llegar al tope no es un error: es el fusible haciendo su trabajo. Conservas los candidatos ya obtenidos y el run lo dice con claridad.

---

## ⚠️ Ajuste obligatorio de `MAX_CALLS_PER_RUN`

**Corrijo una recomendación de la auditoría 5.** Ahí sugerí bajar `MAX_CALLS_PER_RUN` a 60. **Con este parche eso truncaría los runs**, porque ahora el contador incluye el descubrimiento:

| Config | Llamadas por run | `MAX_CALLS_PER_RUN` recomendado |
|---|---|---|
| Actual (31 descubrimiento + 50 enrich) | 81 | **100** (deja margen para reintentos) |
| Tras el hito 23 (12 + 25) | 37 | 50 |

**Deja `MAX_CALLS_PER_RUN=120` o bájalo a 100 — nunca a 60 mientras no apliques el hito 23.**

---

## Cómo aplicarlo

```bash
git apply hito21.patch
```

Si el repo cambió desde `c295e86`, revisa los tres bloques a mano — son cortos y están documentados arriba.

---

## Verificación sin gastar créditos

**Prueba 1 — replay a costo cero (la que prueba el fix):**
1. `RUN_MODE=replay`
2. Lanza un run sobre un brief con datos ya cacheados
3. Consulta el gasto: `GET lens:budget:hikerapi:{YYYY-MM}` en Redis

**Esperado: $0.00.** Antes de este parche habría registrado ~$2.62.

**Prueba 2 — el tope se respeta:**
1. `MAX_CALLS_PER_RUN=5` temporalmente
2. Lanza un run normal
3. Debe terminar en `partial`, con el mensaje de perfiles sin enriquecer, y el contador de Redis en 5

**Prueba 3 — fallback NOSCRIPT:**
1. Con el worker corriendo, ejecuta `SCRIPT FLUSH` en Redis
2. Lanza un run
3. Debe aparecer `budget_fuse_noscript_fallback` en los logs y seguir funcionando

---

## Lo que este parche NO arregla

- **§2.6 — el prefiltro ciego.** Sigue pasando `"country": ""` y decidiendo con bio vacía. Es el hito 23, y es el que de verdad mejora la calidad de los candidatos.
- **§2.7a — `_replay_miss_count_for_run` global.** Hito 24.
- **§2.7c — el timeout no registra gasto.** Ahora la reserva ocurre *antes* del HTTP, así que un timeout **sí** queda contabilizado. Corregido de rebote, con criterio conservador.

---

*Cambios preparados sobre `c295e86`. No se ejecutó código del pipeline ni se consumieron créditos.*
