# Hito 23 — Dejar de pagar por runs condenados

> **Base:** commit `da9cf5e`
> **Parche:** `hito23.patch` — aplicar con `git apply`
> **Archivos:** 2 · **+150 / −5 líneas** · compilan (`py_compile`)
> **Auditoría de origen:** `LENS_AUDIT7_2026-08-18.md`

---

## 0. EL HALLAZGO QUE MOTIVA ESTE HITO

Al preparar el parche encontré **por qué el 402 no abortó el run**, aunque el hito 9 ya lanzaba `SourceUnavailable` y el hito 22 la re-lanzaba tras el `gather`.

`worker.py`, bloque de enrichment:

```python
try:
    enrichment_results = await asyncio.gather(...)
    for res in enrichment_results:
        if isinstance(res, SourceUnavailable):
            raise res              # ← hito 9/22: aborta el run
    ...
except Exception as e:             # ← se lo traga aquí mismo
    step3_degraded = True
    step3_error = str(e)
```

`SourceUnavailable` hereda de `Exception`. **El `except Exception` de tres líneas más abajo captura el mismo `raise` que acabábamos de añadir** y lo convierte en degradación silenciosa.

Es el mismo patrón que ya corregimos dos veces —el `except Exception` genérico de la auditoría 1, el `return_exceptions=True` de la auditoría 2— reaparecido en un tercer lugar. Por eso el run `0c44ea23` recibió 402 en la primera llamada de enrichment y **siguió gastando hasta el final**.

---

## 1. CORRECCIONES INCLUIDAS

| # | Corrección | Archivo | Ahorro / efecto |
|---|---|---|---|
| 1 | `except SourceUnavailable: raise` antes del `except Exception` | `worker.py` bloque enrichment | Aborta al primer 402 en vez de gastar el run completo |
| 2 | Pre-flight de saldo antes de la primera llamada | `worker.py` + `hikerapi_client.get_balance()` | Evita arrancar runs que no pueden terminar |
| 3 | Mensaje derivado del contador dominante | `worker.py` + `_build_zero_candidates_message()` | El usuario deja de recibir diagnósticos falsos |
| 4 | `MAX_HANDLES_TO_ENRICH` 50 → 25 | `worker.py:48` | Run de $1.64 → ~$1.14 |

**No incluye** el fix del Bug N1 (`exclude_stores`) ni el N3 (validación geo post-enrichment). El motivo está en §4.

---

## 2. DETALLE

### 2.1 · Abortar al primer 402 — la que deja de quemar dinero

```python
except SourceUnavailable:
    # El `raise res` del hito 9 caía en el `except Exception` de abajo, que
    # lo convertía en degradación silenciosa. Un 402/401/429 debe abortar:
    # sin enrichment ningún perfil tiene seguidores y el resultado será 0
    # candidatos. Seguir adelante sólo gasta dinero en un run ya condenado.
    raise
except Exception as e:
    step3_degraded = True
    ...
```

El orden importa: Python evalúa los `except` de arriba abajo, así que el específico tiene que ir primero.

**Nota de diseño:** `BudgetExhausted` sigue degradando a `partial` a propósito. Llegar al tope de llamadas con 30 perfiles enriquecidos es un resultado parcial legítimo. Un 402 no: significa que no hay datos para nadie.

### 2.2 · Pre-flight de saldo

```python
if settings.RUN_MODE != "replay" and hasattr(instagram_source, "get_balance"):
    estimated_calls = ESTIMATED_DISCOVERY_CALLS + MAX_HANDLES_TO_ENRICH
    estimated_cost = estimated_calls * settings.HIKERAPI_COST_PER_CALL_USD
    balance = await instagram_source.get_balance()
    if balance is not None and balance < estimated_cost:
        raise SourceUnavailable(
            f"Saldo insuficiente: ${balance:.2f} disponibles y se necesitan "
            f"~${estimated_cost:.2f}... No se gastó nada en este intento.",
            status_code=402, provider="hikerapi",
        )
```

`BudgetFuse.assert_budget_available()` valida tu presupuesto **interno** (el contador de Redis). Esto valida el saldo **real del proveedor**. Son cosas distintas y hasta ahora nadie miraba la segunda.

⚠️ **Requiere verificación tuya.** No conozco la ruta exacta del endpoint de balance de HikerAPI. `get_balance()` prueba tres candidatos (`/v1/account`, `/v1/user/balance`, `/account`) y **devuelve `None` ante cualquier fallo**, en cuyo caso el worker continúa sin pre-flight — el comportamiento actual. Nunca bloquea un run por no encontrar el endpoint.

Confirma la ruta en https://api.hikerapi.com/docs y déjala sola. Si HikerAPI no expone balance, el fix 2.1 sigue cubriendo el caso: el run aborta al primer 402 habiendo gastado solo el descubrimiento.

### 2.3 · El mensaje dice la verdad

Antes el texto era fijo y decía siempre *"pasaron el filtro geográfico"*. Ahora `_build_zero_candidates_message()` decide en tres niveles:

1. **Si el enrichment falló** y ≥80% de los perfiles quedaron sin seguidores → lo dice explícitamente y sugiere recargar.
2. **Si el filtro de tiendas** eliminó ≥80% de los que sí puntuaron → lo dice y ofrece desactivar `exclude_stores`.
3. **Si no** → nombra el contador que más descartó, con su número.

El caso 2 es la versión honesta de lo que el Bug N1 quería resolver: cuando las tiendas **sean** de verdad la causa, el mensaje lo dirá con datos. En el run `0c44ea23` habría salido el caso 1, que es lo que realmente pasó.

**Detalle de implementación:** `stores_excluded_count` se captura justo donde se aplica el filtro, porque `qualified` se reasigna después del análisis de IA y compararlo más tarde daría un número equivocado.

### 2.4 · Menos enrichment

`MAX_HANDLES_TO_ENRICH` de 50 a 25. Es el 61% del costo del run ($1.00 de $1.64). Con el prefiltro aún ciego, los 25 que se descartan son tan arbitrarios como los que se conservan — **pierdes cantidad de ruido, no calidad**.

---

## 3. LO QUE ESTE PARCHE CAMBIA EN EL COMPORTAMIENTO

| Escenario | Antes | Después |
|---|---|---|
| Saldo insuficiente al arrancar | Gasta ~$0.64 en descubrimiento, muere en enrichment, 0 candidatos | Aborta antes de la primera llamada. **$0 gastados** |
| 402 a mitad del enrichment | Continúa, gasta el run entero, `status=partial`, 0 candidatos | Aborta. `status=failed` con mensaje de recarga |
| Tope de llamadas alcanzado | `partial` | `partial` (sin cambios — es correcto) |
| 0 candidatos por tiendas | *"filtro geográfico"* (falso) | *"N cuentas son comerciales, puedes desactivar excluir tiendas"* |
| 0 candidatos por otra causa | *"filtro geográfico"* (falso) | Nombra el contador dominante con su número |
| Costo por run completo | $1.64 | ~$1.14 |

---

## 4. LO QUE DELIBERADAMENTE NO INCLUYE

### Bug N1 — `exclude_stores`

**No lo toqué porque el diagnóstico no se sostiene.** El log dice `0 scored`: la lista llegó vacía al scoring y `exclude_stores` —que se aplica después— nunca tuvo nada que filtrar. El `tienda_excluded=True` del log es el valor del flag de configuración, no un conteo.

**Antes de decidir nada, mira `untracked_no_followers` en el log del run `0c44ea23`.** Predicción: 133. Si se confirma, el Bug N1 queda descartado. Si sale distinto, revisa mi análisis.

El fix 2.3 cubre el caso real por si algún día las tiendas **sí** son la causa: el mensaje lo dirá con el número exacto, y entonces la decisión de incluirlas será de negocio y con datos.

### Bug N3 — validación geo post-enrichment

Correcto como idea, pero afina el ranking de una lista que hoy está vacía. Además, exigir 2-3 `geo_indicators` es demasiado estricto: *"Maracaibo"* a secas es señal válida y quedaría fuera. Vale la pena cuando haya candidatos que medir.

---

## 5. VERIFICACIÓN

**Sin gastar nada:**

```bash
git apply hito23.patch
# redeploy en Railway — el worker ARQ no recarga código solo
```

1. **Lee `untracked_no_followers`** del run `0c44ea23` — cierra la pregunta del Bug N1 sin gastar.
2. Con saldo en $0, lanza un run: debe terminar en **`status=failed`** con el mensaje de saldo, **sin gastar** (pre-flight) o gastando solo 1 llamada si el endpoint de balance no existe.
3. `RUN_MODE=replay` sobre el dataset cacheado: verifica que el mensaje de 0 candidatos nombra la causa real.

**Con la recarga (recomiendo $10, no $20):**

Un run debe costar ~$1.14 y responder una sola pregunta: **¿`total_candidates > 0`?** Si sigue en 0, el log `scoring_diagnostic` dirá en qué escalón exacto mueren — que es justo lo que no se estaba leyendo.

---

## 6. LO QUE SIGUE ABIERTO

- **El prefiltro ciego.** Decide a quién enriquecer con bio vacía; los 25 handles se eligen casi al azar. Es el siguiente cuello de botella de calidad.
- **El descubrimiento desbalanceado.** Se gastan ~$0.64 en descubrir 133 handles de los que solo se pueden evaluar 25. Descubrir menos y enriquecer todo sale más barato y produce más.
- **El ER sigue sin existir.** El hito 22 hizo que su ausencia no mate candidatos, pero `lens_score` pondera ER en 0.389 y ese componente vale cero para todos.

---

*Correcciones preparadas sobre `da9cf5e`. No se ejecutó código del pipeline ni se consumieron créditos.*
