# LENS — Checklist pre-demo

> **Para:** presentación de mañana
> **Commit revisado:** `f7fa614`
> **Parche:** `hito26_demo.patch` — aplicar con `git apply`
> **Tiempo estimado de todo:** ~45 minutos + 1 run de prueba

---

## 0. LO QUE TIENES QUE SABER EN 30 SEGUNDOS

Encontré **tres bloqueantes que romperían la demo en vivo**. Los tres se arreglan hoy: dos son código (parche adjunto, ya compilado) y uno es una línea de SQL en Railway.

El peor es silencioso y es el que más daño haría delante del cliente:

> **En modo Explorar, el chat dice "Encontré 12 perfiles, seleccioná los que quieras analizar" — y la lista aparece vacía.**

No es un fallo visible: es el sistema afirmando éxito mientras no entrega nada. Es exactamente el peor momento para que pase.

---

## 1. 🔴 BLOQUEANTE 1 — Modo Explorar inserta 0 candidatos, siempre

### Qué pasa

En modo Explorar, `worker.py` construye los candidatos con esta forma:

```python
scored.append({
    "handle": handle,
    "profile": p,              # ← no es una columna
    "match_score": rough * 100,
    "rough_score": rough,      # ← no es una columna
    "_is_explore_mode": True,  # ← no es una columna
    ...
})
```

Pero `_deduplicate_and_insert_candidates()` llama a `upsert_many()`, que deriva las columnas del primer registro:

```python
cols = list(records[0].keys())   # railway_pg.py:289
sql = f"INSERT INTO discovery_candidates ({','.join(cols)}) ..."
```

El SQL resultante incluye `profile`, `rough_score` y `_is_explore_mode`, que **no existen en la tabla**. Y le falta `run_id` y `platform`, que además forman el `ON CONFLICT (run_id, platform, handle)`.

El INSERT en lote falla, el fallback individual falla igual para cada registro, y el resultado es `inserted = 0`.

### Por qué es tan peligroso para la demo

El mensaje al usuario se construye con `len(scored)` —los candidatos *antes* de insertarse— así que dice **"Encontré 12 perfiles"** aunque en la base quedaron cero. El analista abre la lista y no hay nada que seleccionar. El flujo Explorar → Analizar queda muerto en el primer paso.

### El fix (incluido en el parche)

El dict de modo Explorar ahora tiene **exactamente la misma forma** que el del camino normal: `run_id`, `platform`, `full_name`, `bio`, `avatar_url`, `country`, `city`, `status`, `fetched_at`, `raw_payload`… Los campos que no aplican sin enrichment (`followers`, `engagement_rate`, `tier`) van en `None` o `0`, no inventados.

Además cambié el criterio de inclusión: antes exigía `rough > 0`, lo que dejaba fuera a cualquier perfil de hashtag sin bio (que son la mayoría) y podía devolver una lista vacía. Ahora entran **todos los prefiltrados** — que ya son el top-N por rough score. En modo Explorar el punto es justamente que decide el analista, no el algoritmo.

---

## 2. 🔴 BLOQUEANTE 2 — La migración 00106 no está aplicada

### Qué pasa

El worker escribe `status = "explored"` al terminar un run en modo Explorar (`worker.py:1687`). Pero `explored` **no existe todavía en el enum de PostgreSQL** — la migración `00000000000106` está creada en el repo y sin aplicar en Railway (lo dice tu propia documentación en dos sitios).

`_run_update()` no tiene `try/except`. PostgreSQL rechaza el valor, la excepción sube al `except Exception` general, y el run se marca **`failed`** — después de haber hecho todo el trabajo y gastado el saldo.

En la demo se vería como: el run corre 2 minutos, y al final aparece en rojo como fallido.

### El fix — una línea, hazla primero

```sql
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'explored';
```

**Verificación:**

```sql
SELECT enumlabel FROM pg_enum
WHERE enumtypid = 'discovery_run_status'::regtype;
-- debe incluir: pending, running, completed, partial, failed, cancelled, explored
```

*(El enum de Pydantic sí tiene `EXPLORED` — ese lo verifiqué y está bien. El problema es solo del lado de la base.)*

---

## 3. 🔴 BLOQUEANTE 3 — El ledger de costos puede tumbar el run

### Qué pasa

Al cerrar el run, el worker inserta en `budget_transactions` (`worker.py:1844`) **sin protección**. Si la migración `00107` no está aplicada, la tabla no existe, el INSERT falla, y el `except Exception` marca el run como `failed`.

Igual que el bloqueante 2: el trabajo ya está hecho, los candidatos ya están insertados, el dinero ya se gastó — y el run aparece fallido.

### El fix (incluido en el parche)

El INSERT del ledger va ahora dentro de un `try/except` con log de warning. **La contabilidad auxiliar nunca debe tumbar un run que ya terminó su trabajo.**

Aun así, aplica la migración 00107 si puedes — pero con este fix ya no es bloqueante.

---

## 4. ⚠️ RIESGO NO BLOQUEANTE — `get_balance()` sin verificar en el caso bueno

El fix del hito 25 resolvió el caso de saldo cero (`state: false` → `0.0`). Correcto y bien hecho.

Pero **nadie ha visto todavía qué devuelve HikerAPI con saldo positivo.** El parser busca `balance`, `balance_usd`, `credits_usd`, `amount`. Si el campo real se llama de otra forma, `get_balance()` devuelve `None`, el pre-flight se omite y vuelves al comportamiento anterior.

No rompe la demo (con $50 el run corre igual), pero significa que el guardarraíl que construiste sigue sin estar validado en el único caso que importa.

**Verificación, 10 segundos y $0.02:**

```bash
curl -s -H "x-access-key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/account | jq
```

Si el campo del saldo no está entre los cuatro que busca el parser, añádelo a la tupla de `get_balance()`.

---

## 5. ORDEN DE EJECUCIÓN — HOY

| # | Acción | Tiempo |
|---|---|---|
| 1 | `ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'explored';` en Railway | 2 min |
| 2 | `git apply hito26_demo.patch` | 1 min |
| 3 | Aplicar migración `00107_budget_transactions.sql` (opcional con el fix) | 3 min |
| 4 | Redeploy en Railway — **y confirmar que el worker recargó** | 5 min |
| 5 | `curl` de balance y ajustar el parser si hace falta | 5 min |
| 6 | **Run de prueba en modo Explorar** | ~$0.24 |
| 7 | **Run de prueba en modo Analizar con 3 handles** | ~$0.06 |

> ⚠️ **El paso 4 no es rutinario.** Ya te pasó una vez: Railway desplegó y el worker de ARQ siguió con el código viejo en memoria. Verifica en los logs que aparece un mensaje del código nuevo antes de dar por buena la prueba.

**Costo total de la validación: ~$0.30.** Con $50 de saldo, irrelevante.

---

## 6. QUÉ VERIFICAR EN EL RUN DE PRUEBA

No lo des por bueno porque "no dio error". Comprueba estos cuatro:

| # | Comprobación | Cómo | Qué esperar |
|---|---|---|---|
| 1 | El run termina en `explored` | `GET /runs/{id}` | `status: "explored"`, **no** `failed` |
| 2 | **Hay candidatos en la lista** | `GET /runs/{id}/candidates` | `total_candidates > 0` y la lista no vacía |
| 3 | Los candidatos tienen `handle` y `bio` | la propia lista | campos poblados, no `null` |
| 4 | El costo se registró | `actual_cost_usd` en el run | > 0 y coherente (~$0.24) |

**La número 2 es la que importa.** Es exactamente la que fallaba y la que el cliente va a ver.

Si `total_candidates` sigue en 0, mira el log `scoring_diagnostic` — te dice en qué filtro mueren, con los contadores por nombre.

---

## 7. RECOMENDACIONES PARA LA PRESENTACIÓN

### Prepara el run con antelación, no en vivo

Corre el modo Explorar **hoy** con el brief que vas a presentar. Los resultados quedan en la base y en la caché de Redis (TTL 12 h para hashtags, 24 h para perfiles). Mañana:

- Si demuestras en vivo, la caché hace que sea más rápido y más barato.
- Si algo falla, ya tienes el run bueno en el historial para mostrar.

**Nunca hagas una demo en vivo de un flujo que no corriste antes con los mismos datos.**

### Cuenta la historia correcta

La narrativa fuerte no es "el algoritmo elige por ti" — es la que el producto realmente hace bien:

> *"LENS descubre en dos minutos cuentas que el equipo no tenía en el radar. El analista elige cuáles valen la pena, y LENS las analiza en profundidad. Encontrar es automático; decidir sigue siendo humano."*

Eso es honesto, es lo que el sistema hace, y **posiciona el modo Explorar + Analizar como una decisión de diseño y no como una limitación**. Cualquier agencia entiende que nadie contrata a un influencer sin mirarlo.

### Muestra el control de costos — es tu mejor activo

De todo lo construido, la infraestructura de control es lo más sólido y lo que más diferencia frente a un competidor: fusible de presupuesto, corte automático, circuit breaker, contabilidad por run, costo real por búsqueda al centavo.

Un dato concreto vale más que la arquitectura: **"cada búsqueda cuesta $0.24 y el sistema se detiene solo si se pasa del presupuesto."** Eso a un cliente le habla.

### Ten a mano el número honesto

Si preguntan cuántos influencers ha encontrado el sistema hasta hoy, la respuesta honesta es que **está entrando en producción ahora**. Los 48 runs previos fueron desarrollo y depuración, no operación.

No inventes una métrica de éxito histórica: no existe todavía, y si alguien pide ver los datos, queda peor. Lo que sí puedes mostrar con orgullo es el run de mañana funcionando.

### Lo que no haría

- **No presentes el modo automático (`auto`).** Es el que tiene el prefiltro ciego y el que produjo 1 candidato en 48 runs. Presenta Explorar → Analizar.
- **No prometas volumen** ("500 influencers al mes"). El presupuesto actual da para ~40 búsquedas de Explorar al mes.
- **No improvises un brief nuevo en vivo.** Usa el que probaste hoy.

---

## 8. SI ALGO FALLA MAÑANA

**Plan B, en orden:**

1. **El run se queda colgado** → tienes el run de hoy en el historial. Muéstralo y sigue.
2. **La lista sale vacía** → abre `scoring_diagnostic` en los logs; el contador dominante te dice por qué. Es información, no un fallo mudo.
3. **El pre-flight aborta por saldo** → el mensaje ya es claro y accionable ("recarga en hikerapi.com/billing"). Es incluso una buena demostración de que los controles funcionan.
4. **Railway se cae** → capturas de pantalla del run de hoy.

---

## 9. RESUMEN

**Hoy, sin falta:** la línea de SQL del `ALTER TYPE`, el parche, redeploy con verificación de que el worker recargó, y **un run completo de Explorar → Analizar con el brief real de mañana**.

Son unos 45 minutos y ~$0.30.

**Mañana:** presenta Explorar → Analizar, con el run de hoy como red de seguridad, y apóyate en el control de costos como diferenciador.

---

*Revisión sobre `f7fa614`. Los tres bloqueantes se verificaron leyendo el código; el parche compila (`py_compile`). No se ejecutó el pipeline ni se consumieron créditos.*
