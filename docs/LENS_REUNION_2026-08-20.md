# LENS — Documento para la reunión

> **Commit revisado:** `1be52f1` (Hito 26 aplicado y desplegado)
> **Parche adjunto:** `hito27.patch` — 1 archivo, compilado
> **Método:** verificación del código real contra lo que afirma la documentación

---

## 1. LO PRIMERO — UN BUG QUE HACE QUE EL MODO ANALIZAR CUESTE 11× MÁS

### Qué encontré

`analyze_selected` (`discovery.py:562`) construye el brief así:

```python
brief_parsed["discovery_mode"] = "analyze"
brief_parsed["handles_to_analyze"] = body.handles_to_analyze
brief_parsed["parent_run_id"] = str(body.run_id)      # ← se asigna
brief = DiscoverySearchRequest(**brief_parsed)         # ← se pierde aquí
```

**`DiscoverySearchRequest` no tiene el campo `parent_run_id`.** Lo tiene `BriefStructured` (línea 94), pero no el schema que usa este endpoint. Pydantic v2 descarta los campos extra en silencio (`extra='ignore'` por defecto), y `launch_discovery_run` persiste `brief.model_dump()` — así que el `parent_run_id` nunca llega a la base.

### La cadena de consecuencias

En el worker:

```python
parent_run_id = getattr(brief, "parent_run_id", None)   # → None
_skip_discovery = is_analyze_mode and parent_run_id      # → False
```

1. **No se saltan los pasos de discovery** → se repiten las ~32 llamadas (**$0.64 tirados**)
2. **No se cargan los candidatos del run padre** desde la base
3. `handles_to_enrich = [h for h in brief.handles_to_analyze if h in profiles]` — y `profiles` viene del discovery nuevo, así que **sólo se enriquecen los handles que casualmente vuelvan a aparecer**

**Modo Analizar cuesta ~$0.70 en vez de $0.06.** Y si la búsqueda fresca no devuelve los mismos handles, enriquece cero.

### El fix

Está en `hito27.patch`: añadir `parent_run_id` a `DiscoverySearchRequest`. Tres líneas.

**Es el mismo patrón que llevamos siete auditorías persiguiendo:** un dato que se asigna, se pierde en silencio, y el sistema sigue adelante como si nada. No falla — hace lo incorrecto sin avisar.

### Bug secundario incluido en el mismo parche

```python
platforms: list[Platform] = Field(default=lambda: [Platform.INSTAGRAM])
```

Es `default=`, no `default_factory=`. En Pydantic v2 el `default` se usa tal cual **y no se valida**, así que `brief.platforms` es el objeto lambda, no una lista. Hoy es latente porque nadie lee ese campo — pero revienta el día que se añada TikTok.

---

## 2. LO QUE SÍ ESTÁ BIEN

Vale decirlo con la misma claridad, porque el trabajo de ayer fue bueno:

| Verificado en código | Estado |
|---|---|
| Dict de modo Explorar con columnas correctas | ✅ aplicado tal cual |
| Ledger protegido con try/except | ✅ |
| `EXPLORED` en el enum de Pydantic | ✅ |
| Migración 00106 aplicada en Railway | ✅ confirmado por el equipo |
| Frontend envía `discovery_mode` | ✅ |
| Polling reconoce `explored` | ✅ (`useRunPolling`, `LensSearchPage`) |
| Endpoint `/analyze-selected` | ✅ existe y encola |
| Deploys Railway + Vercel | ✅ |

El flujo Explorar funciona de punta a punta en el código. **El que está roto es Analizar**, y por una línea.

---

## 3. CORRECCIONES A LA DOCUMENTACIÓN

Estas no son cosméticas: si alguien retoma el proyecto leyendo estos documentos, va a trabajar con datos falsos.

### 3.1 El "Bug 1" del Hito 26 está mal documentado

Los tres documentos describen el bug así:

```python
# ❌ ANTES (según la doc):
"username": raw.get("username"),           # ← no existe columna 'username'
"profile_pic_url": raw.get("profile_pic_url"),
"follower_count": raw.get("followers"),
```

**Ese código nunca existió.** El bug real era:

```python
# ❌ ANTES (real):
"handle": handle,
"profile": p,                # ← no es columna
"rough_score": rough,        # ← no es columna
"_is_explore_mode": True,    # ← no es columna
# y faltaban run_id y platform, que forman el ON CONFLICT
```

La causa era la misma (claves que no son columnas), pero el "antes" documentado es inventado. Conviene corregirlo para que el historial sirva.

### 3.2 "Tasa de éxito ~80% con supervisión humana"

Aparece en dos documentos como si fuera un dato medido. **No hay ninguna medición que lo respalde** — el modo Explorar nunca ha corrido en producción con saldo.

En una reunión con dirección o cliente, un número inventado que luego se desmiente cuesta más credibilidad que no dar número. Sugiero cambiarlo por *"pendiente de medir en el primer run real"*.

### 3.3 Contradicciones numéricas entre documentos

| Dato | Un sitio dice | Otro dice |
|---|---|---|
| Costo Modo Analizar | $0.43/handle | $0.06/handle |
| `MAX_HANDLES_TO_ENRICH` | 50 | 25 |
| Costo Modo Explorar | $0.24 | $0.48 |
| Enrichment por handle | $0.02 | $0.0006 (línea heredada) |

El costo por handle es $0.02 — eso está confirmado empíricamente ($5.00 → $3.38 en 81 requests). Los demás números hay que unificarlos a partir de ahí.

### 3.4 "Modo Explorar — Descubrimiento Sin Costo"

El título dice "sin costo" y el cuerpo dice "$0.24-0.48". Es descubrimiento **barato**, no gratis. Con un cliente delante, la diferencia importa.

### 3.5 El selector de modo no existe

La documentación dice *"El usuario elige Modo Explorar en la UI"*. En realidad `LensSearchPage.tsx:51` tiene `discovery_mode: 'explore' as const` **hardcodeado**. No hay selector, y el modo `auto` es inalcanzable desde esa página.

No está mal como decisión (auto es el que produjo 1 candidato en 48 runs), pero hay que llamarlo por su nombre: es una constante, no una elección del usuario.

---

## 4. PREGUNTAS PARA LA REUNIÓN

Estas son las decisiones que van a determinar la estructura del trabajo. No las puedo responder yo.

### Sobre el producto

**1. ¿El modo `auto` se elimina o se mantiene?**
Hoy está inalcanzable desde la UI pero vivo en el worker (~400 líneas: prefiltro, scoring completo, filtros de tienda y geo). Mantenerlo cuesta mantenimiento y confunde; eliminarlo simplifica mucho. Si se mantiene, ¿para qué caso de uso?

**2. ¿Cuál es la unidad de valor que se le cobra al cliente?**
¿Una búsqueda? ¿Un candidato entregado? ¿Una campaña? De esto depende si $0.24 por Explorar es caro o barato, y si el presupuesto de $10/mes tiene sentido.

**3. ¿Cuántas búsquedas al mes necesita una campaña real?**
Con $10 son ~40 Explorar o ~16 campañas completas. Si una campaña de Nestlé necesita 5 iteraciones de brief, son 3 campañas al mes. ¿Alcanza?

### Sobre el presupuesto

**4. ¿El tope de $10/mes es una restricción real o un valor heredado?**
Se fijó cuando se creía que costaba $0.0006/llamada — 33× menos. A $0.02 ese tope es lo que hace que todo sea apretado. ¿Se puede subir a $30-50 ahora que el gasto está bajo control?

**5. ¿Se resuelve el desfase Redis↔DB de $25.13 o se acepta y se resetea?**
Los runs anteriores al Hito 21 nunca escribieron en Redis. Reconstruir ese histórico es arqueología; declarar septiembre como mes cero y arrancar limpio con el ledger cuesta 10 minutos. Yo haría lo segundo.

### Sobre el alcance

**6. ¿Multi-tenancy antes o después del segundo cliente?**
Hoy no existe: la app se conecta con la credencial propietaria y RLS no aplica. Con un cliente no importa; con dos es un riesgo de fuga de datos entre marcas. ¿Hay un segundo cliente en el horizonte de 3 meses?

**7. ¿Qué pasa con el engagement rate?**
HikerAPI no devuelve posts en el endpoint de perfil, así que el ER es siempre `None` y pesa 0.389 en el score — el componente más grande del ranking está vacío. Traerlo cuesta ~$0.02 por perfil adicional. ¿Vale ese costo, o se re-pondera el score sin ER?

**8. ¿El `accepted` que nunca se actualiza es prioritario?**
Lleva marcado como crítico varias auditorías. ¿Alguien lo usa realmente, o es una columna heredada que conviene borrar?

---

## 5. RECOMENDACIONES PARA ESTRUCTURAR EL TRABAJO

### 5.1 Adoptar una regla: ningún dato se pierde en silencio

Siete auditorías, siete bugs de la misma familia:

| # | Bug | Forma |
|---|---|---|
| 1 | 402 reportado como "0 candidatos" | `except Exception` |
| 2 | Fail-fast inerte | `gather(return_exceptions=True)` |
| 3 | `en_id` en vez de `_job_id` | parámetro inexistente |
| 4 | Doble conteo del gasto | dos puntos de contabilidad |
| 5 | ER siempre cero | campo que dejó de existir |
| 6 | Flag leído como conteo | f-string ambiguo |
| **7** | **`parent_run_id` descartado** | **campo ausente en el schema** |

**Ninguno falló ruidosamente. Todos hicieron lo incorrecto en silencio.**

Dos medidas concretas:

- **`model_config = ConfigDict(extra='forbid')`** en los schemas de entrada. Con eso, el bug de hoy habría sido un `ValidationError` en el primer test en vez de $0.64 por run.
- **Un test end-to-end del flujo Explorar → Analizar** que verifique que el run hijo tiene `parent_run_id` poblado y que **no** repite el discovery. Los 59 tests actuales no lo cubren.

### 5.2 Separar "documentación de estado" de "bitácora de cambios"

Hoy `ARQUITECTURA_LENS.md` tiene 1.166 líneas donde conviven la arquitectura, el historial de 26 hitos, tres análisis de costos que se contradicen y logs de runs concretos. Cada versión añade una sección sin depurar la anterior — por eso hay dos secciones numeradas "12" y datos incompatibles.

Sugerencia:

- **`ARQUITECTURA.md`** — sólo el estado actual. Sin historial. Si algo se arregló, se corrige la descripción; no se añade una nota.
- **`CHANGELOG.md`** — los hitos en orden, una línea cada uno.
- **`COSTOS.md`** — una sola tabla de costos, la vigente.

Un documento que se contradice a sí mismo deja de usarse, y eso ya está pasando.

### 5.3 Instrumentar la conversión, no sólo el costo

El control de costos está resuelto. Lo que no se mide es **si el producto sirve**:

- De N handles descubiertos en Explorar, ¿cuántos selecciona el analista? *(mide si el descubrimiento es relevante)*
- De los seleccionados, ¿cuántos sobreviven al scoring? *(mide si el enrichment aporta)*
- De los guardados, ¿cuántos se contactan de verdad? *(mide si el producto sirve)*

Tres números. Sin ellos, dentro de un mes seguiremos discutiendo el costo por run sin saber si el resultado vale.

### 5.4 Fijar el criterio de éxito antes del primer run

Antes de recargar, conviene escribir la respuesta a: **"¿qué resultado del primer run de Explorar nos hace decir que esto funciona?"**

Sugiero: *≥15 handles con bio no vacía, de los cuales el analista seleccionaría al menos 5.* Es concreto, se evalúa en dos minutos y no admite interpretación.

Sin ese criterio escrito de antemano, cualquier resultado se puede racionalizar como progreso — que es exactamente lo que ha pasado durante tres semanas.

---

## 6. ORDEN SUGERIDO

| # | Acción | Cuándo | Costo |
|---|---|---|---|
| 1 | Aplicar `hito27.patch` (`parent_run_id` + `platforms`) | Antes de recargar | $0 |
| 2 | Test E2E Explorar → Analizar que verifique `parent_run_id` y ausencia de re-discovery | Antes de recargar | $0 |
| 3 | `extra='forbid'` en los schemas de entrada | Esta semana | $0 |
| 4 | Corregir las contradicciones de la doc (§3) | Esta semana | $0 |
| 5 | Recargar HikerAPI | Tras 1-2 | $10-50 |
| 6 | Run de Explorar con criterio de éxito escrito | Tras 5 | ~$0.24 |
| 7 | Run de Analizar con 3 handles | Tras 6 | ~$0.06 |
| 8 | Instrumentar las tres métricas de conversión | Próximo sprint | $0 |

**Los pasos 1 y 2 son el punto clave: sin el fix del `parent_run_id`, el primer test de Analizar va a costar $0.70 y probablemente enriquecer cero handles** — y se va a interpretar como "otro bug del pipeline" cuando en realidad es una línea de schema.

---

## 7. SOBRE EL MONTO A RECARGAR

Con el fix aplicado:

| Concepto | Costo |
|---|---|
| Explorar | ~$0.24 |
| Analizar (5 handles) | ~$0.10 |
| **Campaña completa** | **~$0.34** |

**$10 dan ~29 campañas completas. $20 dan ~58.**

Recomiendo **$20**: suficiente para validar el flujo, iterar el brief varias veces y hacer una demo, sin exponerse a un sobregiro si algo se escapa. Los $50 que menciona la documentación son más de lo necesario en esta fase.

---

*Verificación estática sobre `1be52f1`. El parche compila (`py_compile`). No se ejecutó el pipeline ni se consumieron créditos.*
