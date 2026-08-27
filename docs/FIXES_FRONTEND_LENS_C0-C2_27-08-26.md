# FIXES CRÍTICOS DE ACOPLE — LENS DISCOVERY

## Iteración 2 · Issues C-0, C-1, C-2 \+ análisis de pendientes

> **Repositorio:** `github.com/ungardev/lawebcore` **Commit de código verificado:** `2446e75` · **HEAD:** `52dd488` (solo documentación) **Método:** lectura directa del árbol vía API de GitHub. Solo lectura, ningún archivo modificado **Fuente de verdad:** el código. Donde un documento contradice al código, prevalece el código **Fecha:** 27-08-26 **Dirección técnica:** Claude Fable 5 · Full Stack Engineer Senior **Ejecución:** Ungar Villamizar

---

## Nota de alcance — qué puedo y qué no

**No tengo acceso de escritura al repositorio.** No puedo hacer `git commit`, `git push`, ni revisar los logs de despliegue de Railway: no hay credenciales de git en este entorno y el sandbox no alcanza `codeload.github.com` ni `raw.githubusercontent.com`.

**Lo que sí hice:** leer el código real de `2446e75` vía la API de GitHub, verificar cada issue contra el archivo y la línea, y producir los diffs exactos listos para aplicar.

**Las Tareas 1 a 4 del prompt quedan divididas así:** el análisis y el código son de este documento; el `git add`, el commit, el push y la verificación del despliegue quedan del lado de quien tenga el repositorio local.

---

## RESUMEN EJECUTIVO

| Issue | Veredicto | Severidad | Novedad |
| :---- | :---- | :---- | :---- |
| **C-0** — Tipo ENUM de Postgres sin los estados del Hito 30 | 🔴 **Confirmado** | **Crítica** | **No estaba identificado en el prompt** |
| **C-1** — `DiscoveryRunStatus` de Pydantic incompleto | 🔴 Confirmado | Crítica | Son **6** valores, no 5 |
| **C-2** — `Influencer.primary_tier` sin sub-tiers | 🟠 Confirmado | Media | Falta además `| null` |

**El hallazgo C-0 precede a C-1 y lo invalida como primer paso.** Aplicar C-1 sin C-0 cambia el síntoma y no el resultado.

---

# C-0 — El fallo no es HTTP 500\. Es que el UPDATE nunca llega a la base.

## Veredicto: CONFIRMADO — hallazgo nuevo, no contemplado en el plan

### Evidencia

`discovery_runs.status` **no es un `TEXT` con restricción CHECK. Es un tipo ENUM de Postgres.**

\-- supabase/migrations/00000000000106\_discovery\_run\_explored\_status.sql

\-- Migration: 00106\_discovery\_run\_explored\_status

\-- Desc: Adds 'explored' status to discovery\_run\_status enum for Hito 24 (Modo Explorar).

ALTER TYPE discovery\_run\_status ADD VALUE IF NOT EXISTS 'explored';

Las migraciones `00000000000104_discovery_run_partial_status.sql` y `00000000000106_discovery_run_explored_status.sql` existen precisamente porque **cada estado nuevo exigió extender el tipo**. Revisadas las 46 migraciones del directorio: **no existe ninguna migración que agregue los estados del Hito 30\.**

### Tabla de cobertura — qué escribe el worker contra qué acepta Postgres

| Origen en el código | Estado emitido | ¿Existe en el ENUM de Postgres? |
| :---- | :---- | :---- |
| `worker.py:1787` | `delivered` | ❌ **No** |
| `worker.py:1789`, `worker.py:1967` | `degraded` | ❌ **No** |
| `worker.py:320` | `aborted_budget` | ❌ **No** |
| `determine_final_status()` | `empty` | ❌ **No** |
| `determine_final_status()` | `inconsistent` | ❌ **No** |
| `RunStatus.QUEUED` (`observability.py:75`) | `queued` | ❌ **No** |
| `worker.py:1943`, `worker.py:1975` | `failed` | ✅ Sí |
| — | `running` | ✅ Sí |

Definición completa del enumerado del worker:

observability.py:72   class RunStatus(str, Enum):

observability.py:73       """Estados de corrida con semántica precisa."""

observability.py:75       QUEUED \= "queued"

observability.py:76       RUNNING \= "running"

observability.py:77       DELIVERED \= "delivered"

observability.py:78       DEGRADED \= "degraded"

observability.py:79       EMPTY \= "empty"

observability.py:80       INCONSISTENT \= "inconsistent"

observability.py:81       ABORTED\_BUDGET \= "aborted\_budget"

observability.py:82       FAILED \= "failed"

**Ocho estados en el worker. Dos de ellos existen en Postgres.**

### Dictamen

El `UPDATE discovery_runs SET status='delivered'` falla en la base con:

ERROR: invalid input value for enum discovery\_run\_status: "delivered"

La corrida ejecuta el pipeline completo, intenta escribir su estado terminal, Postgres lo rechaza — y si ese `UPDATE` está bajo un `except Exception`, **la corrida queda colgada en `running` indefinidamente**.

Esto explica los dos runs en estado «En curso» desde el 12 de agosto que quedaron documentados en la auditoría de plataforma del 19-08-26.

**Por qué el orden importa:** si solo se aplica C-1 (el enumerado de Pydantic), el `GET /runs/{id}` deja de devolver 500 pero responde `running`, porque el valor `delivered` nunca llegó a escribirse. **Arreglar Pydantic sin arreglar Postgres cambia el síntoma y no el resultado.** Es el mismo patrón que la Regresión \#0 de la iteración anterior: corregir un extremo de la cadena y no el otro.

### FIX C-0 — nueva migración

**Archivo:** `supabase/migrations/00000000000110_discovery_run_hito30_statuses.sql`

\-- Migration: 00110\_discovery\_run\_hito30\_statuses

\-- Desc: El Hito 30 introduce RunStatus (observability.py:72-83) con 6 estados

\--       que el tipo discovery\_run\_status no conoce. Sin esto, el UPDATE del

\--       estado terminal falla en la base y la corrida queda colgada en 'running'.

\--

\-- IMPORTANTE: ALTER TYPE ... ADD VALUE no puede ejecutarse dentro de un bloque

\-- de transacción, y el valor nuevo no puede usarse en la misma transacción en

\-- que se agregó. Esta migración debe correr sola, fuera de transacción.

ALTER TYPE discovery\_run\_status ADD VALUE IF NOT EXISTS 'queued';

ALTER TYPE discovery\_run\_status ADD VALUE IF NOT EXISTS 'delivered';

ALTER TYPE discovery\_run\_status ADD VALUE IF NOT EXISTS 'degraded';

ALTER TYPE discovery\_run\_status ADD VALUE IF NOT EXISTS 'empty';

ALTER TYPE discovery\_run\_status ADD VALUE IF NOT EXISTS 'inconsistent';

ALTER TYPE discovery\_run\_status ADD VALUE IF NOT EXISTS 'aborted\_budget';

**Verificación previa — correr antes de la migración:**

SELECT enumlabel

FROM pg\_enum e

JOIN pg\_type t ON t.oid \= e.enumtypid

WHERE t.typname \= 'discovery\_run\_status'

ORDER BY e.enumsortorder;

\-- Esperado antes: pending, running, completed, failed, cancelled, partial, explored

**Verificación posterior:** la misma consulta debe devolver los 6 valores nuevos además de los 7 anteriores.

**Riesgo de regresión:** Bajo. `ADD VALUE` es aditivo y no toca ninguna fila existente. **Orden de aplicación:** **1**

---

# TAREA 1 — C-1 · RunStatus Enum Mismatch

## Veredicto: CONFIRMADO — con dos correcciones al enunciado

### Evidencia

schemas.py:11   class DiscoveryRunStatus(str, Enum):

schemas.py:12       PENDING \= "pending"

schemas.py:13       RUNNING \= "running"

schemas.py:14       COMPLETED \= "completed"

schemas.py:15       FAILED \= "failed"

schemas.py:16       CANCELLED \= "cancelled"

schemas.py:17       PARTIAL \= "partial"    \# hito 22 — el worker ya lo emite

schemas.py:18       EXPLORED \= "explored"  \# hito 24 — modo explorar

schemas.py:252  class DiscoveryRunResponse(BaseModel):

schemas.py:253      id: UUID

schemas.py:254      status: DiscoveryRunStatus     ← acá revienta la serialización

schemas.py:255      total\_candidates: int \= 0

**Confirmado que `DiscoveryRunResponse.status` sí está tipado con el enumerado.** Un valor `delivered` proveniente de la base produce `ValidationError` al serializar la respuesta, que FastAPI traduce a HTTP 500\.

### Corrección 1 al enunciado — son 6 valores, no 5

El prompt afirma «5 valores nuevos no existen en el enum Pydantic» y luego lista 6 entre paréntesis. La cuenta correcta es **6**: `queued`, `delivered`, `degraded`, `empty`, `inconsistent`, `aborted_budget`.

### Corrección 2 al enunciado — el fix debe ser aditivo

El prompt dice «extender», que es lo correcto, pero conviene dejarlo escrito como restricción dura: **los valores antiguos no se eliminan.** Los 48 runs históricos de la base tienen `completed`, `partial`, `explored` y `pending`. Reemplazar el enumerado en vez de ampliarlo haría que el endpoint devolviera 500 sobre todo el historial — se cambiaría un bug por otro más amplio.

### FIX C-1

**Archivo destino:** `packages/discovery/discovery/schemas.py:11-18`

class DiscoveryRunStatus(str, Enum):

    \# \--- Legacy: presentes en runs históricos. NO ELIMINAR. \---

    PENDING \= "pending"

    RUNNING \= "running"

    COMPLETED \= "completed"

    FAILED \= "failed"

    CANCELLED \= "cancelled"

    PARTIAL \= "partial"      \# hito 22

    EXPLORED \= "explored"    \# hito 24

    \# \--- Hito 30: deben coincidir 1:1 con RunStatus en observability.py:72-83 \---

    QUEUED \= "queued"

    DELIVERED \= "delivered"

    DEGRADED \= "degraded"

    EMPTY \= "empty"

    INCONSISTENT \= "inconsistent"

    ABORTED\_BUDGET \= "aborted\_budget"

### Prueba de guardia — recomendada, es la que impide que esto se repita

**Archivo nuevo:** `apps/api/tests/test_status_enum_parity.py`

def test\_run\_status\_is\_subset\_of\_api\_enum():

    """RunStatus (worker) ⊆ DiscoveryRunStatus (API).

    Si el worker emite un estado que el API no conoce, el GET devuelve 500\.

    Esta prueba falla en CI antes de que llegue a producción.

    """

    from shared\_core.observability import RunStatus

    from discovery.schemas import DiscoveryRunStatus

    worker\_states \= {s.value for s in RunStatus}

    api\_states \= {s.value for s in DiscoveryRunStatus}

    assert worker\_states \<= api\_states, (

        f"Estados del worker sin cobertura en el API: {worker\_states \- api\_states}"

    )

**Commit sugerido:** `fix(lens): extend DiscoveryRunStatus enum with Hito 30 statuses` **Riesgo de regresión:** Bajo **Orden de aplicación:** **2**

**Criterio de éxito:** `GET /runs/{run_id}` devuelve `delivered` sin HTTP 500 — **siempre que C-0 se haya aplicado primero**, porque de lo contrario el valor en la base seguirá siendo `running`.

---

# TAREA 2 — C-2 · `Influencer.primary_tier` Type Mismatch

## Veredicto: CONFIRMADO

### Evidencia

// apps/web/src/types/index.ts:43

primary\_tier: 'NANO' | 'MICRO' | 'MID' | 'MACRO' | 'MEGA' | 'MIX'

Verificado por búsqueda automática sobre el archivo completo (132 líneas): **cero ocurrencias de `NANO_BAJO`** ni de ningún otro sub-tier.

### Dictamen

El FIX \#6 de la iteración anterior hizo que `_derive_tier()` (`discovery.py:844`) devuelva los 9 sub-tiers de la escala LWFA. Cuando un analista guarda un candidato, `influencers.primary_tier` recibe valores como `MICRO_MEDIO` que el tipo de TypeScript no contempla. La vista de influencers guardados y la de campañas muestran `—` en la columna de tier.

### FIX C-2

**Archivo destino:** `apps/web/src/types/index.ts:43`

  primary\_tier:

    // Legacy — influencers cargados antes del FIX \#6 (Hito 32.3)

    | 'NANO' | 'MICRO' | 'MID' | 'MACRO' | 'MEGA' | 'MIX'

    // Hito 32.3 — sub-tiers LWFA (\_derive\_tier en discovery.py:844)

    | 'NANO\_BAJO' | 'NANO\_ALTO'

    | 'MICRO\_BAJO' | 'MICRO\_MEDIO' | 'MICRO\_ALTO'

    | 'MID\_BAJO' | 'MID\_ALTO'

    | 'MACRO\_BAJO' | 'MACRO\_ALTO'

    | null;   // \_derive\_tier devuelve None cuando no hay followers

### El `| null` no es opcional

El FIX \#6 hace que `_derive_tier()` devuelva `None` cuando `followers is None`. Fue una decisión deliberada —no inventar un tier cuando no hay dato, en línea con la regla NULL ≠ 0 del contrato de datos— y el frontend tiene que saberlo, o el render falla en el primer influencer sin métricas.

**Commit sugerido:** `fix(lens): widen Influencer.primary_tier to 9 subtiers + null` **Riesgo de regresión:** Bajo **Orden de aplicación:** **3**

**Criterio de éxito:** TypeScript compila sin errores y los 9 sub-tiers son tipos válidos.

### Archivos adicionales a revisar

El prompt señala dos lugares más. Ambos son de baja prioridad y no bloquean la corrida:

| Archivo | Qué contiene | ¿Bloquea? |
| :---- | :---- | :---- |
| `apps/web/src/lib/utils.ts` (\~línea 51\) | `INFLUENCER_TIERS` | No — afecta filtros de la interfaz |
| `apps/web/src/features/campaigns/components/NewCampaignModal.tsx` (\~línea 30\) | `TIERS` | No — afecta el selector de tier en campañas nuevas |

---

# TAREA 3 — Alineación backend-frontend

## Sobre `DiscoveryCandidate.tier`

Coincido con el prompt en **no tocarlo**. Hay dos caminos distintos y está bien que difieran:

| Camino | Función | Escala | Destino |
| :---- | :---- | :---- | :---- |
| Candidato de discovery | `classify_tier()` — `geo_boost.py:122-130` | 4 tramos | `discovery_candidates.tier` |
| Influencer guardado | `_derive_tier()` — `discovery.py:844` | 9 sub-tiers | `influencers.primary_tier` |

## ⚠️ Pero es una decisión que hay que declarar, no heredar

El manual de la agencia (`14_influencer_lens_manual_filtros_ia.md`, §2.1) establece que **discovery y scoring** usan la escala granular de 9 sub-tiers, reservando la genérica para pricing y reportes evolutivos.

Hoy el candidato se puntúa contra un benchmark de 4 tramos y se guarda con uno de 9: **el mismo perfil cambia de tier al pasar de candidato a influencer.** Funciona, pero es incoherente y va a confundir a quien compare las dos vistas.

**Recomendación:** dejarlo escrito en el PLAN\_MAIN como decisión consciente y temporal, o unificar en un hito posterior. Lo que no conviene es que quede como un accidente sin documentar.

## `getTierColor()` y `getTierLabel()`

`apps/web/src/lib/format.ts`. No es bloqueante mientras `DiscoveryCandidate.tier` siga en 4 tramos. Solo afecta la vista de influencers guardados, donde los sub-tiers aparecerán sin color asignado. Ver Tarea 5, punto C-4.

---

# TAREA 5 — Análisis de esfuerzo de los pendientes

| \# | Pendiente | Esfuerzo | Análisis |
| :---- | :---- | :---- | :---- |
| **FP-1** | **Freshness Policy 7d** | **2–3 h** | La base ya está: el índice único de snapshot del FIX \#4 garantiza una fila por influencer y día. Falta la consulta de última instantánea antes de enriquecer, la constante `DISCOVERY_FRESHNESS_DAYS` en `config.py`, y un `drop_profile(..., SKIPPED_FRESH)` para que el ahorro quede contabilizado. **Advertencia:** hay que apagar o subir `CACHE_TTL_PROFILE = 86400` en `hikerapi_client.py:17` — con los dos mecanismos activos se sigue re-pagando el perfil al día siguiente y la política de 7 días no tendría efecto real |
| **FP-2** | **Brand Exclusion Table** | **4–6 h** | Migración de tabla `brand_excluded_handles` con clave por marca, módulo de carga, evaluación previa al enriquecimiento, y uso de los códigos `EXCLUDED_STORE` / `EXCLUDED_FOUNDATION` / `EXCLUDED_BRAND_OWN` que ya existen en `DropReason`. **Es el pendiente con exposición comercial:** es el control de brand safety que se le describe a compliance de Nestlé y que hoy no existe como filtro determinista. También cierra la ficha L-05 — que la cuenta oficial del cliente aparezca como candidato |
| **C-3** | **SearchProgress PHASES desfasadas** | **1 h** | **Cosmético, no bloqueante.** El frontend muestra una lista de fases que ya no corresponde: le falta `step5_ai_analysis` y conserva `step2_keyword_search`, que el worker ya no emite. Ninguna lógica depende de esa lista; el impacto es que la barra de progreso se ve desalineada durante la corrida. Prioridad baja, después de la validación |
| **C-4** | **`getTierColor()` para 9 sub-tiers** | **1–2 h** | Cosmético mientras los candidatos sigan en 4 tramos. Solo afecta la vista de influencers guardados. Sugerencia de diseño: mantener la familia de color por tier base y variar la intensidad por sub-nivel — NANO\_BAJO e NANO\_ALTO comparten tono, distinta saturación. Así la vista sigue legible de un vistazo sin nueve colores distintos compitiendo |

---

# ORDEN DE APLICACIÓN

| \# | Fix | Archivo | Riesgo | Costo HikerAPI |
| :---- | :---- | :---- | :---- | :---- |
| 1 | **C-0** — ENUM de Postgres | `supabase/migrations/00000000000110_*.sql` (nuevo) | Bajo | $0 |
| 2 | **C-1** — Enum de Pydantic \+ prueba de paridad | `packages/discovery/discovery/schemas.py:11-18` | Bajo | $0 |
| 3 | **C-2** — Union de TypeScript | `apps/web/src/types/index.ts:43` | Bajo | $0 |
| 4 | Despliegue y confirmación de arranque limpio del worker | Railway | — | $0 |
| 5 | **Corrida de validación** | — | — | **\~$1,14** |

---

# RECOMENDACIÓN SOBRE LA CORRIDA DE VALIDACIÓN

## No procedas todavía

Con C-0 sin resolver, la corrida gastaría $1,14 y terminaría colgada en `running`: el pipeline correría bien, el estado terminal fallaría en la base, y no habría forma de saber si funcionó. Se perdería el dinero y, peor, se perdería la señal.

## Criterio de éxito — dos consultas, no una

\-- 1\. El estado terminal se escribió efectivamente

SELECT id, status, total\_candidates, actual\_cost\_usd

FROM discovery\_runs

ORDER BY created\_at DESC

LIMIT 1;

\-- Debe devolver 'delivered' o 'empty'.

\-- Si devuelve 'running', la migración C-0 no se aplicó o no tomó efecto.

\-- 2\. El libro de descartes tiene más de una causa representada

SELECT reason\_code, (payload-\>\>'count')::int AS n

FROM discovery\_run\_events

WHERE run\_id \= :run\_id AND event \= 'profile.dropped'

ORDER BY 2 DESC;

\-- Si MISSING\_FOLLOWER\_FIELD sigue concentrando \~100%, el problema no era

\-- el merge de enriquecimiento y hay que volver sobre el paso de enrichment.

La segunda consulta es la que realmente valida los ocho fixes de la iteración anterior. La primera solo valida que el instrumento funciona.

---

# PENDIENTE ARRASTRADO — sin respuesta desde la primera auditoría

⚡ **A-5 · `TIER_MIN_FOLLOWERS = 5_000` en `worker.py:54`**

Ninguna de las dos iteraciones lo tocó. Si esa constante actúa como filtro duro y no como parámetro de reparto por tiers, el sistema excluye por diseño el tramo **NANO bajo (500–5K)**, que según la metodología propia de la agencia aporta entre el **80% y el 85% de las views** de una campaña.

De ser así, ninguno de los fixes aplicados —ni los ocho de la iteración anterior ni los tres de esta— cambia el resultado del producto: el motor seguiría siendo estructuralmente incapaz de encontrar el tipo de creador que sostiene las campañas de La Web.

**Se responde leyendo los usos de esa constante en el código. Cuesta cero dólares, cero riesgo, y sigue sin respuesta.**

---

*Verificación elaborada sobre el commit `2446e75` del repositorio `lawebcore`. Todas las referencias son a archivo y línea verificables en ese commit. Ningún archivo del repositorio fue modificado durante esta auditoría.*

*Documento generado por La Web Figital Agency · 27-08-26 · Uso interno*  
