# LENS — Modelo de IA, búsqueda por UI y anomalías

> **Commit auditado:** `8a3f16f` (HEAD de `main`)
> **Parche:** `hito36.patch` — 3 archivos, Python compilado
> **Encargo:** evaluar `deepseek-v4-flash` vs `deepseek-chat`, viabilidad de migrar a Gemini, y si la búsqueda por UI ya funciona
> **Marco:** Plan de Alineación de Santiago Lanz (v1.2) y Lanz v2.0
> **Método:** lectura del árbol + **verificación contra la documentación oficial de DeepSeek** (no inferencia)

---

## §1 — RESPUESTA CORTA A LAS TRES PREGUNTAS

| Pregunta | Respuesta |
|---|---|
| ¿`deepseek-v4-flash` es correcto? | **Sí, existe y es el modelo vigente.** Verificado en la documentación oficial. El cambio fue acertado. |
| ¿Está funcionando bien? | **No del todo.** El modelo trae *thinking mode* activado por defecto, y eso rompe tres supuestos del código sin lanzar ni un error. |
| ¿Se puede buscar desde la UI? | **Sí, la búsqueda corre y los candidatos aparecen** — pero después el frontend hace 200 peticiones inútiles y termina mostrando un error falso. |
| ¿Migrar a Gemini ahora? | **No todavía**, y el motivo está en §5. |

---

## §2 — EL MODELO: `deepseek-v4-flash` ES CORRECTO

Conviene decirlo primero porque es la duda que originó el encargo, y porque yo mismo llegué con sospecha: *"flash"* es convención de Google, no de DeepSeek. **Me equivoqué.** La documentación oficial lista tres modelos vigentes:

| Modelo | Versión | Contexto | Salida máx. |
|---|---|---|---|
| `deepseek-v4-flash` | DeepSeek-V4-Flash-0731 | 1M | 384K |
| `deepseek-v4-pro` | DeepSeek-V4-Pro-0813 | 1M | 384K |
| `deepseek-v4-flash-vision-exp` | — | 1M | 384K |

`deepseek-v4-flash` es la elección correcta para este caso de uso: mismo contexto que `pro` y **tres veces más barato**.

Precio (por 1M tokens, cache miss):

| | Off-peak | Peak |
|---|---|---|
| Entrada | $0.22 | $0.44 |
| Salida | $0.66 | $1.32 |

**Dato nuevo que no está en ninguna documentación del proyecto:** el precio es el doble en horario pico — 01:00-04:00 y 06:00-10:00 UTC de lunes a viernes. Para Venezuela (UTC-4) eso es **21:00-00:00 y 02:00-06:00**. Las corridas de prueba nocturnas caen en tarifa doble.

---

## §3 — 🔴 EL PROBLEMA REAL: EL MODO *THINKING* VIENE ACTIVADO

Este es el hallazgo central y no aparece en Lanz v1.2, en Lanz v2.0 ni en el PLAN_MAIN.

De la documentación oficial de DeepSeek, textual:

> *"Thinking mode is enabled by default, with the default effort being high"*

Y, en la misma página:

> *"Thinking mode does not support the **temperature**, top_p, presence_penalty, or frequency_penalty parameters. Please note that, for compatibility with existing software, **setting these parameters will not trigger an error but will also have no effect**."*

Migrar de `deepseek-chat` a `deepseek-v4-flash` cambió tres cosas, y **ninguna de las tres lanza un error**:

### 3.1 — `temperature` dejó de tener efecto

El código lo fija en dos sitios:

```python
deepseek_client.py:45   temperature=self.temperature      # 0.1
candidate_analyzer.py:324   temperature=0.2
```

Ese `0.2` estaba puesto para que la puntuación de candidatos fuera estable entre corridas. **Hoy se ignora.** Dos corridas sobre el mismo candidato pueden dar puntajes distintos, y el sistema no tiene forma de notarlo.

Es exactamente el patrón que Lanz documenta en su §3: un parámetro que el proveedor acepta, descarta y no reporta.

### 3.2 — Se paga razonamiento en cada llamada

Con `effort: high` por defecto, cada llamada genera una cadena de pensamiento que se factura **como tokens de salida** ($0.66–1.32/1M). El scoring analiza hasta 80 candidatos en lotes de 10 — son 8 llamadas por corrida, cada una razonando antes de responder.

No es catastrófico en dinero (DeepSeek sigue siendo un orden de magnitud más barato que HikerAPI, tal como dice Lanz §5.5), pero **sí en latencia**, y sobre todo: se está pagando por un razonamiento cuyo resultado se descarta.

### 3.3 — 🔴 `max_tokens=2500` puede truncar el JSON

Esta es la consecuencia grave. En modo thinking, `max_tokens` cubre **razonamiento + respuesta**. La documentación de JSON Output advierte explícitamente:

> *"Set the max_tokens parameter reasonably to prevent the JSON string from being truncated midway."*

Con `max_tokens=2500` y `effort=high`, el razonamiento puede consumir el presupuesto y dejar el JSON a medias. Entonces:

```
_parse_batch_response() → _json.loads() lanza
    → except → _fallback_scores()
        → los 3 puntajes quedan iguales a los de un candidato analizado por el modelo
```

Y eso es, palabra por palabra, el caso que Lanz documenta en su tabla de la §3: *"Sustituye el análisis de IA por `_fallback_scores()` … los tres puntajes numéricos quedan iguales a los de un candidato analizado por el modelo."*

**El modo thinking no rompe el sistema: lo empuja al camino de degradación silenciosa que el informe Lanz señala como el problema de fondo.** Y como `ai_rationale` sólo se escribe en el camino de IA, la única señal de que se degradó es una columna vacía que nadie mira.

### 3.4 — El fix

En el parche: desactivar thinking explícitamente en el cliente.

```python
extra_body={
    "cache": {"mode": "enabled"},
    "thinking": {"type": "disabled"},
}
```

Con eso `temperature` vuelve a funcionar, desaparece el costo de razonamiento y `max_tokens=2500` vuelve a ser suficiente para el JSON.

**Es una decisión, no sólo un fix.** Para parsear un brief y puntuar contra una rúbrica queremos salida estructurada, barata y reproducible — no razonamiento. Si mañana alguna tarea se beneficia del thinking, se activa **en esa llamada**, no globalmente.

---

## §4 — 🟠 BÚSQUEDA POR UI: FUNCIONA, PERO TERMINA EN UN ERROR FALSO

### Lo que sí funciona

Verificado en código:

| Pieza | Estado |
|---|---|
| BUG #1 (`worker.py:1298` `follower_count`) | ✅ corregido |
| BUG #2 (`discovery.py:973,976` `followers`/`raw_payload`) | ✅ corregido |
| La UI arma el brief y llama a `createRun` | ✅ |
| `TERMINAL_STATUSES` en `LensSearchPage:78` — los 8 estados terminales | ✅ |
| Los candidatos se muestran cuando el run termina | ✅ |

**Sí se puede lanzar una búsqueda desde la UI y ver resultados.**

### 🟠 El defecto: `pollRun` no conoce los estados nuevos

`useDiscoveryRun.ts:58` corta el polling sólo en cuatro estados:

```typescript
'completed' || 'failed' || 'partial' || 'explored'
```

Pero desde el Hito 30 el worker termina en:

```python
worker.py:1786   RunStatus.INCONSISTENT / RunStatus.EMPTY
worker.py:1788   RunStatus.DELIVERED          ← el caso de éxito normal
worker.py:1790   RunStatus.DEGRADED
worker.py:319    RunStatus.ABORTED_BUDGET
```

**Una corrida exitosa termina en `delivered`, que no está en la lista.** Consecuencia:

1. Los candidatos **sí** aparecen (`hasResults` usa `TERMINAL_STATUSES`, que está completa, y `loadRun` actualiza el estado en cada vuelta)
2. Pero `pollRun` sigue: **200 intentos × 3s = 10 minutos, 200 peticiones a la API**
3. Al final lanza `Timeout esperando resultados`
4. El usuario ve `toast.error('Error al ejecutar la búsqueda')` **sobre una búsqueda que salió bien**

Es el mismo bug del Hito 26 —cuando el polling no reconocía `explored`— reaparecido porque el enum creció de 7 a 13 valores y **`pollRun` quedó fuera de la actualización mientras `TERMINAL_STATUSES` sí se actualizó**. Dos listas del mismo concepto en el mismo feature, desincronizadas.

**Fix en el parche:** una constante `POLL_TERMINAL_STATUSES` compartida, con los 10 estados terminales.

### 🟠 El error de validación no llega al usuario

`discovery.py:508,510` valida y devuelve 400 con el campo exacto:

```python
raise HTTPException(status_code=400, detail="product_name es obligatorio")
```

Pero la UI lo captura con un `toast.error('Error al ejecutar la búsqueda')` genérico. **El usuario que olvida el nombre del producto no sabe qué corregir.** No hay validación en cliente ni se muestra el `detail` del backend.

**Fix en el parche:** extraer `response.data.detail` y mostrarlo.

---

## §5 — SOBRE MIGRAR A GEMINI U OTRO PROVEEDOR

El encargo plantea migrar **después** de una prueba real exitosa. Estoy de acuerdo con ese orden, y añado tres consideraciones.

### 5.1 — Con el fix del thinking, no hay razón técnica urgente para migrar

Los motivos que justificarían un cambio, según Lanz §5.5, son *"salida estructurada garantizada, validación contra esquema y comportamiento estable"*. Los tres están cubiertos por `deepseek-v4-flash`:

| Necesidad | ¿Lo cubre? |
|---|---|
| JSON garantizado | ✅ `response_format: {"type":"json_object"}` |
| Tool calls | ✅ |
| Contexto suficiente | ✅ 1M tokens |
| Comportamiento estable | ✅ **con thinking desactivado** |
| Costo | ✅ de los más baratos del mercado |

Y Lanz ya lo dijo: **el costo del modelo no es la variable relevante** — el gasto real está en HikerAPI, un orden de magnitud arriba. Migrar para ahorrar en el LLM no mueve la aguja.

### 5.2 — Lo que sí falta es independiente del proveedor

Tres de los cuatro puntos de contacto con el LLM **no usan salida estructurada**:

| Sitio | ¿`response_format`? |
|---|---|
| `candidate_analyzer.py:326` (scoring) | ✅ |
| `brief_parser.py:186` | ❌ |
| `brief_parser.py:355` | ❌ |
| `profile_generator.py:502` (vía `complete_json`) | ❌ — `complete_json` llama a `complete()` sin pasar `response_format` |

Cambiar de proveedor sin arreglar esto traslada el problema. **Arreglarlo primero hace la migración trivial después**, porque el contrato queda declarado y probado.

### 5.3 — Si se migra, la forma correcta

El acoplamiento a DeepSeek es pequeño y está bien contenido: `deepseek_client.py` usa `ChatOpenAI` con `base_url`. Gemini expone endpoint compatible con OpenAI, así que la migración sería cambiar `base_url` + `model` + la clave.

**Pero antes conviene extraer una interfaz `LLMClient`** —igual que existe `InstagramSource` para los datos— para que el proveedor sea una configuración y no una dependencia. Sin eso se repite la historia de Apify → HikerAPI: una migración que arrastra convenciones del proveedor anterior al contrato interno (Lanz §2.2).

**Mi recomendación:** dejar DeepSeek, aplicar el fix del thinking, cerrar los tres `response_format` que faltan, y **reevaluar el proveedor cuando exista la interfaz**. La migración pasa entonces de proyecto a parámetro.

---

## §6 — ANOMALÍAS ADICIONALES

| # | Anomalía | Severidad | Dónde |
|---|---|---|---|
| 1 | Modo thinking activo → temperature ignorada, riesgo de truncar JSON | 🔴 | `deepseek_client.py:43-49` |
| 2 | `pollRun` sin los 6 estados nuevos → 200 peticiones + error falso | 🟠 | `useDiscoveryRun.ts:58` |
| 3 | Error 400 del backend no llega al usuario | 🟠 | `LensSearchPage.tsx` catch |
| 4 | `complete_json()` no pasa `response_format` — el nombre promete lo que no hace | 🟠 | `deepseek_client.py:143` |
| 5 | Precio pico/valle ×2 no está en ningún cálculo de costo del proyecto | 🟡 | docs |
| 6 | `discovery_mode: 'explore'` hardcodeado — no hay selector | 🟡 | `LensSearchPage.tsx:51` |
| 7 | Dos listas de estados terminales en el mismo feature | 🟡 | `LensSearchPage:78` vs `useDiscoveryRun:58` |

Los hallazgos 2, 4 y 7 son la misma familia que Lanz describe en su §3: **piezas que se desincronizan y no avisan.**

---

## §7 — QUÉ HACER, EN ORDEN

| # | Acción | Costo | Tiempo |
|---|---|---|---|
| 1 | Aplicar `hito36.patch` (thinking off + pollRun + error visible) | $0 | 5 min |
| 2 | Deploy Railway + Vercel — **verificar en logs que el worker recargó** | $0 | 10 min |
| 3 | Añadir `response_format` a `brief_parser` (×2) y `complete_json` | $0 | 30 min |
| 4 | **Búsqueda real desde la UI** con el brief de mascotas VE | ~$1.14 | 5 min |
| 5 | Verificar los cuatro criterios de §8 | $0 | 5 min |
| 6 | Decidir sobre el proveedor de LLM **con los datos del paso 4** | — | — |

Saldo actual ~$38–43. La validación cuesta ~$1.14.

---

## §8 — CRITERIOS DE LA PRUEBA REAL

Escribirlos antes de correr, para que el resultado no admita interpretación:

| # | Criterio | Cómo se comprueba |
|---|---|---|
| 1 | El run termina en `delivered` y el polling se detiene solo | Sin "Timeout esperando resultados" en la UI |
| 2 | `total_candidates ≥ 15` | Respuesta de `GET /runs/{id}` |
| 3 | Los candidatos traen `followers` real, no 0 | Lista en la UI |
| 4 | **`ai_rationale` no es NULL** | `SELECT count(*) FROM discovery_candidates WHERE run_id=… AND ai_rationale IS NOT NULL` |

**El cuarto es el que prueba que el modelo funcionó.** Si `ai_rationale` viene vacío, el scoring cayó a `_fallback_scores()` y la IA no participó — que es justo lo que el modo thinking podía provocar en silencio.

Y una consulta más, para cerrar el diagnóstico de Lanz §7.1:

```sql
SELECT reason_code, count(*) FROM discovery_run_events
WHERE run_id = '…' GROUP BY reason_code ORDER BY 2 DESC;
```

Si hay **más de un** `reason_code`, el instrumento ya distingue causas — que es la métrica de éxito de todo el plan de alineación.

---

## §9 — LO QUE NO RECOMIENDO

- **Migrar de modelo antes del paso 4.** Cambiar de proveedor sobre un sistema que aún no completó una corrida exitosa mezcla dos variables y hace imposible saber cuál falló.
- **Subir `max_tokens` en vez de desactivar el thinking.** Trata el síntoma, sigue pagando razonamiento descartado y deja `temperature` ignorada.
- **Empezar las FASES 1-4 de Lanz v2.0 antes de la prueba real.** Son correctas, pero se validan contra el mismo instrumento que aún no se ha probado. El paso 4 cuesta $1.14 y dice cuáles de esas fases importan de verdad.

---

## §10 — NOTA SOBRE EL MÉTODO

Este análisis corrigió una suposición mía: llegué pensando que `deepseek-v4-flash` era un nombre inventado, por la convención *flash*. La documentación oficial dice lo contrario y **la decisión del equipo fue correcta**.

Vale la pena señalarlo porque es el mismo punto que hace Lanz al final de su §5.4: *"ningún análisis del propio código puede detectar que un proveedor externo cambió"*. Los tres hallazgos de este informe —thinking por defecto, temperature ignorada, precio pico/valle— **no están en el repositorio**. Sólo aparecen leyendo al proveedor.

Conviene que eso sea una práctica y no una casualidad: **cada vez que se cambie un modelo o un plan externo, leer la documentación del proveedor antes de desplegar.** El código no puede avisar de lo que no sabe.

---

*Verificado sobre `8a3f16f`. Documentación de DeepSeek consultada el 2026-08-28 en `api-docs.deepseek.com`. El parche compila. No se ejecutó el pipeline ni se consumieron créditos.*
