# LENS — Revisión de Ingeniería: Arquitectura, Costos y Control Operacional

> **Fecha:** 2026-08-14
> **Commit analizado:** `a250b0c` (HEAD de `main`)
> **Documentos revisados:** `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` y `docs/ARQUITECTURA_LENS.md`
> **Método:** análisis estático del código actual; cada afirmación se contrastó contra el repositorio, no contra la documentación
> **Perspectiva:** ingeniería de sistemas — diseño, control de costos, observabilidad y operabilidad

---

## 0. RESUMEN EJECUTIVO

Los dos documentos describen bien el *síntoma* (costos disparados, pipeline sin resultados) pero atribuyen la causa al lugar equivocado. La lectura correcta es más simple y más incómoda:

**El sistema no tiene frenos.** No existe límite de presupuesto, no existe corte por saldo, no existe idempotencia en el encolado, y los errores de la API externa se tragan en silencio. Un bucle que llama a una API de pago, sin techo y sin freno, operado manualmente en modo prueba-y-error, gastó $50-72 en dos días. Eso no es un bug de `MAX_HANDLES_TO_ENRICH`: es la ausencia de una capa de control que en cualquier sistema que consume APIs de pago es obligatoria antes del primer request.

Los "0 candidatos" de los últimos runs se explican por el saldo agotado (`InsufficientFunds 402`) — eso está claro y no es un misterio arquitectónico. **Pero el hecho de que el sistema haya respondido "0 candidatos" en 10 segundos en vez de "no hay créditos" es en sí mismo el defecto más importante de este informe**, porque es lo que convirtió un problema de facturación trivial en dos días de diagnóstico arquitectónico. Un sistema que no distingue entre "busqué y no encontré nada" y "no pude buscar" no es operable.

Además, la documentación de arquitectura contiene errores de hecho que llevan a decisiones equivocadas: describe un modelo de datos que no existe, afirma multi-tenancy por RLS que en la práctica no aplica, y da dos cifras de costo contradictorias en el mismo documento.

**Prioridad de la semana, en orden:** (1) fail-fast y corte por presupuesto — sin esto, cualquier recarga se vuelve a quemar; (2) corregir la documentación para que refleje el sistema real; (3) recién entonces, la calidad de candidatos.

---

## 1. CORRECCIONES A `PROMPT_CLAUDE_CODE_ANALYSIS.md`

### 1.1 "Pipeline retorna 0 candidatos" — causa confirmada y matiz importante

El documento lista cuatro causas posibles (422 en `get_user_about`, STEP 0 con endpoint incorrecto, hashtags B2B, scoring estricto). **La causa real de los runs recientes es el saldo agotado**, y el propio documento la tiene a la vista: "Balance actual: -717 requests, $0.0 USD. Cuenta agotada (`InsufficientFunds 402`)".

La evidencia encaja: "0 candidatos en 10 segundos, sin error visible" es exactamente el comportamiento de un pipeline donde cada llamada falla de inmediato con 402 y cada excepción se captura así:

```python
except Exception as e:
    logger.warning("source_hashtag_error", source=source_name, hashtag=tag, error=str(e))
```

Ese patrón se repite en los siete bloques `_fetch_stepN` de `worker.py`. Con saldo cero, las siete búsquedas devuelven listas vacías, el run llega al final sin datos y se cierra como completado con `total_candidates=0`.

**Corrección al documento:** eliminar las cuatro "causas posibles" y sustituirlas por la causa real, más el defecto de diseño que la ocultó (§3.1 de este informe).

**Matiz que no hay que perder:** el propio documento menciona un run distinto — *"min_match_score = 10 eliminaba 254 profiles → 0"*. Ese run **sí tenía datos** (254 perfiles encontrados) y aun así produjo cero candidatos. Esa es una falla estructural independiente del saldo, y sigue viva. Se analiza en §3.2.

### 1.2 "Causa raíz: `MAX_HANDLES_TO_ENRICH = 500`"

Correcto como causa proximal del gasto, e incorrecto como causa raíz. La constante explica el costo *por run*; no explica por qué nadie se enteró hasta $50. La causa raíz es la ausencia de límite de presupuesto y de telemetría de gasto en vivo. Con un corte configurado en $5/mes, la misma constante de 500 habría abortado el tercer run con un mensaje claro, y el equipo habría ajustado el parámetro el primer día con $1.50 gastados.

Un sistema correcto se protege de sus propios parámetros mal calibrados. Este no lo hace.

### 1.3 "STEP 2.6 Network Expansion — 2 calls, follower expansion disabled"

El documento lo da por desactivado. En el código no está desactivado: está **roto de una forma que igual cuesta dinero**.

```python
async def _fetch_step2p6():
    seeds = list(step1_handles | step2_handles)[:1]
    niche_kws: list[str] = []          # ← siempre vacío
    for handle in seeds:
        profile = await instagram_source.enrich_profile(handle)   # ← 1 llamada pagada
        ...
        for niche_kw in niche_kws:      # ← nunca itera
```

`niche_kws` se inicializa vacío y nunca se llena, así que el bucle interno no ejecuta jamás. Pero `enrich_profile()` ya se llamó: **cada run gasta una llamada de enrichment para producir exactamente cero resultados**. Además, esa llamada ocurre en `asyncio.gather` junto a los steps 1-recent y 2.5, antes de cualquier prefiltro.

Es poco dinero por run, pero es la clase de coste silencioso que multiplicado por 80 runs de prueba explica parte del gasto.

### 1.4 Inventario de steps — la numeración es contradictoria

El documento describe STEP 0 a STEP 5 en orden lógico. El código usa esos números con **dos significados distintos a la vez**:

| Nombre en código | Qué hace realmente | Qué dice la doc que es "STEP N" |
|---|---|---|
| `_fetch_step3()` | Top search por keyword | STEP 3 = "Profile Enrichment" |
| `_fetch_step4()` | Suggested profiles | STEP 4 = "Scoring" |

Es decir, `_fetch_step3` **no** es el STEP 3 del pipeline, y `_fetch_step4` **no** es el STEP 4. En el mismo archivo conviven `print("[STEP3] accounts from topsearch")` y `print("STEP 3: Profile enrichment")`.

Esto no es cosmético: cuando alguien lee un log que dice "STEP 3 falló", no puede saber si se rompió el topsearch o el enrichment — que cuestan y significan cosas completamente distintas. En dos días de depuración a contrarreloj, esa ambigüedad cuesta horas.

**Recomendación:** renombrar por función, no por número: `fetch_by_hashtag_top`, `fetch_by_hashtag_recent`, `fetch_by_keyword`, `fetch_by_topsearch`, `fetch_by_suggested`, `fetch_by_reels`, `expand_by_followers`. Los números fueron útiles cuando había cuatro pasos; con nueve fuentes ya no describen nada.

---

## 2. CORRECCIONES A `ARQUITECTURA_LENS.md`

Este documento es la referencia técnica del proyecto. Tiene errores de hecho que inducen decisiones equivocadas.

### 2.1 El modelo de datos descrito no es el que existe (§5)

| La doc dice | El código/esquema real usa |
|---|---|
| `discovery_runs.brief (JSON)` | `brief_parsed` (JSONB) |
| `discovery_candidates.enriched_data (JSON)` | `raw_payload` (JSONB) |
| `discovery_candidates.ai_analysis (JSON)` | columnas separadas: `content_quality`, `audience_quality`, `brand_fit`, `ai_rationale` |
| `discovery_conversations.messages (JSON)` | tabla aparte `discovery_messages` |
| `discovery_profiles.brief_id / profile_data / cached_at` | `fingerprint`, `vertical_slug`, `hashtags`, `keywords`, `niche_keywords`, `geo_indicators`, `buy_intent_keywords`, `elite_data`, `source`, `times_used` |

La sección 5 describe un esquema imaginado. Cualquier desarrollador nuevo que escriba una query contra esa documentación falla en el primer intento.

### 2.2 Contradicción interna: ¿Supabase o Railway Postgres? (§1 vs §4.4)

La sección 1 dice "PostgreSQL 16 via Supabase Cloud". La sección 4.4 dice "Ubicación: `postgres.railway.internal:5432/railway`". El diagrama de la sección 2 dibuja "Supabase DB (PostgreSQL)".

El código importa `railway_pg` desde `shared_core` y usa asyncpg directo contra Railway Postgres. **La base es Railway; Supabase quedó como legado.** Hay que decidir cuál es la fuente de verdad y decirlo una sola vez.

### 2.3 La afirmación de multi-tenancy por RLS es falsa en la práctica (§1)

> "RLS: Row-level security por `business_unit_id`, `client_id`, `team_id`"

Row-Level Security de PostgreSQL se aplica al rol que ejecuta la query. El worker y la API se conectan por asyncpg con la credencial de servicio (dueño de la base). **Para el propietario de la tabla, RLS no aplica salvo que se fuerce con `FORCE ROW LEVEL SECURITY`, y aun así el service role la evade.** Las políticas existen en las migraciones, pero no protegen nada en el camino real de datos.

Si mañana se vende Lens a una segunda agencia, el aislamiento entre inquilinos **no existe hoy**. El filtrado por unidad de negocio tiene que hacerse explícitamente en las queries de la aplicación, o hay que introducir un rol de aplicación distinto del propietario. Documentar "tenemos RLS" y creerlo es el escenario en que se filtran datos de un cliente a otro.

Es una corrección de documentación hoy y una decisión de arquitectura antes del segundo cliente.

### 2.4 Las dos tablas de costo se contradicen (§7)

La primera tabla suma "~211 llamadas ≈ $0.13 por run", incluyendo 50 llamadas de `get_user_about` ($0.030) y 42 de STEP 0 ($0.025). La tabla siguiente ("configuración ultra-económica") dice que `get_user_about` está deshabilitado y STEP 0 también, y concluye "~60 calls/run = ~$0.04".

En el código, ambos están apagados por defecto:

```python
ENRICHMENT_INCLUDE_ABOUT = os.getenv("HIKERAPI_INCLUDE_ABOUT", "false").lower() == "true"
step0_enabled = os.getenv("HIKERAPI_STEP0_LOCATION", "false").lower() == "true"
```

**La cifra vigente es ~$0.04/run.** La primera tabla describe una configuración que ya no se usa y debe marcarse como histórica, o desaparecer. Tener dos cifras oficiales de costo en el mismo documento es cómo se toman malas decisiones de presupuesto.

### 2.5 "Modo ultra-económico no persiste en deploy — config hardcodeada" (§11)

Parcialmente incorrecto, y la mezcla es el verdadero problema. Los interruptores de STEP 0 y `about` **sí** son variables de entorno (persisten en Railway). Pero `MAX_HANDLES_TO_ENRICH = 50`, `MAX_POSTS_PER_HASHTAG = 20`, los cortes `[:3]`, `[:2]`, `[:1]` de cada step y `min_match_score = 5` son constantes de módulo o literales embebidos en el cuerpo de la función.

El resultado es que la configuración de costos vive en dos lugares con dos ciclos de vida distintos: unos se cambian en el panel de Railway, otros requieren commit y redeploy. En una crisis de costos, eso es exactamente lo que no se quiere.

**Recomendación:** un solo objeto de configuración del pipeline (Pydantic Settings), con todos los límites, cargado de entorno con defaults conservadores, y registrado en el log al inicio de cada run. Que el run diga con qué presupuesto arrancó.

---

## 3. HALLAZGOS NUEVOS (no están en ninguno de los dos documentos)

### 3.1 🔴 Los errores de la API se tragan en silencio — el defecto que costó dos días

Este es el hallazgo central, y es la lección operacional del incidente.

Los siete bloques de búsqueda capturan `Exception` genérica y siguen adelante con lista vacía. Un `402 InsufficientFunds` es indistinguible de "el hashtag no tiene posts". El pipeline llega al final, escribe `status = "completed"` y `total_candidates = 0`, y la interfaz le dice al usuario que no se encontraron candidatos.

**El sistema mintió.** No es que no hubiera candidatos: es que no se pudo buscar. Y como la causa quedó enterrada en un `logger.warning`, el equipo pasó dos días buscando un problema de arquitectura donde había un problema de facturación.

**Corrección:** clasificar los errores por naturaleza, no capturarlos todos igual.

```python
class SourceUnavailable(Exception):
    """El proveedor no puede atender: saldo, credenciales, rate limit, caída."""

# En el cliente HTTP:
if response.status_code in (401, 402, 403, 429):
    raise SourceUnavailable(f"{response.status_code}: {response.text[:200]}")
```

Y en el worker: si cualquier step lanza `SourceUnavailable`, **abortar el run** con `status = "failed"` y un `error` legible ("Sin créditos en HikerAPI — recargar en hikerapi.com/billing"). El usuario debe ver eso en el chat, no "no encontré candidatos".

Regla general: **un fallo de infraestructura nunca debe presentarse como un resultado de negocio.** Vale para saldo, credenciales, rate limits y timeouts.

**Esfuerzo: 2 h. Es la corrección de mayor retorno del informe.**

### 3.2 🔴 No hay techo de gasto ni corte automático

`app/core/discovery_cost_tracker.py` registra costos, pero no los limita: no existe ninguna noción de presupuesto mensual, gasto acumulado ni corte. El objetivo declarado es "< $10 USD/mes" y se gastaron $50-72 en dos días sin que nada interviniera.

**Corrección mínima viable (2-3 h):**

1. Tabla o clave en Redis con el gasto acumulado del mes en curso, por proveedor.
2. Un `assert_budget_available()` al inicio de `discovery_run_task` que consulte ese acumulado contra `MONTHLY_BUDGET_USD` (variable de entorno) y aborte el run con un mensaje explícito si se superó.
3. Un tope por run: si el contador de llamadas de un run pasa `MAX_CALLS_PER_RUN` (p.ej. 120), abortar ese run y marcarlo `partial` — protege contra un bucle nuevo mal calibrado.
4. Umbral de aviso al 70% del presupuesto en el log y en el panel.

Esto no es sofisticado: es el equivalente a un fusible. Cualquier sistema que consuma una API de pago en un bucle automático lo necesita antes de su primer request en producción.

### 3.3 🔴 El primer prefiltro es código muerto — y su log engaña

En `worker.py` (~684-727) hay un prefiltro que descarta perfiles por pocos seguidores, por cuenta de empresa con menos de 50k y por cuenta privada. Calcula `prefiltered_handles` y lo usa:

```python
handles_to_enrich = prefiltered_handles[:MAX_HANDLES_TO_ENRICH]     # línea ~727
```

Pero unas 110 líneas más abajo, ese resultado se sobrescribe:

```python
prefilter_handles = await _prefilter_profiles(profiles, ...)         # usa TODOS los profiles
handles_to_enrich = [h for h, _ in prefilter_handles]                # línea ~836
```

El segundo prefiltro parte de `profiles` completo, no de `prefiltered_handles`. **El primer filtro no tiene ningún efecto sobre qué se enriquece.** Sin embargo emite este log:

```python
logger.info("step1_prefiltered", total=..., after_prefilter=...,
            stores_filtered=..., low_followers_filtered=..., private_filtered=...)
```

Ese log reporta un filtrado que nunca ocurrió. Si alguien lo usó para diagnosticar por qué no salían candidatos, lo mandó en la dirección equivocada.

Agravante: el filtro de privadas nunca podría haber funcionado. `_normalize_user` del cliente sí devuelve `is_private`, pero **los bloques de merge del worker no copian ese campo** a `profiles[handle]`, así que `p.get("is_private", False)` es siempre `False`.

**Corrección:** eliminar el primer prefiltro (o fusionar sus reglas dentro de `_prefilter_profiles`, que es el que manda) y quitar el log que lo acompaña.

### 3.4 🟠 Se pierden campos entre la fuente y el scoring (copy-paste de 7 bloques)

El worker mezcla los resultados de cada fuente en `profiles` con **siete bloques de diccionario casi idénticos de ~20 líneas cada uno** (hashtag, keyword, topsearch, suggested, hashtag-recent, reels, follower-expansion). Son ~140 líneas de copia con variaciones menores.

El costo real de esa duplicación ya se está pagando: `_normalize_user` devuelve `country` (ISO del perfil) e `is_private`, y **ningún bloque de merge copia esos dos campos**. Se obtienen de la fuente y se tiran antes de llegar al scoring. El país solo reaparece después del enrichment.

Es el modo de fallo clásico del copy-paste: alguien añade un campo en el normalizador y tiene que acordarse de tocarlo en siete sitios.

**Corrección:** una sola función `merge_source_results(profiles, items, source_tag, handle_set)` que reciba la lista y la etiqueta de origen. Elimina ~120 líneas y cierra la fuga de campos. **Esfuerzo: 1.5 h.**

### 3.5 🟠 La abstracción de fuentes no abstrae — el fallback a Apify es imposible hoy

`InstagramSource` (Protocol) declara **5 métodos**: `search_hashtag`, `search_keyword`, `enrich_profile`, `get_user_about`, `close`.

El worker invoca, además de esos: `search_hashtag_recent`, `search_top_accounts`, `suggested_profiles`, `search_reels_by_keyword`, `search_followers_of`, `search_location`, `location_medias_top`, `location_medias_recent`, y dos métodos **privados** del cliente concreto — `_normalize_user` y `_extract_user_from_post` — a través de comprobaciones `hasattr()`.

Conclusión: cambiar `INSTAGRAM_SOURCE=apify` no degrada el sistema, lo rompe. `ApifyInstagramSource` (148 líneas) no implementa ocho de los métodos que el worker necesita. **La respuesta a "¿vale la pena rehabilitar Apify como fallback?" es que hoy no hay fallback que rehabilitar: hay un contrato incompleto que da la ilusión de portabilidad.**

Que el worker llame métodos con guion bajo de una implementación concreta es la señal más clara de que la abstracción se saltó: son justamente esos dos métodos los que hacen imposible sustituir el proveedor.

**Corrección (mediano plazo, 6-8 h):** ampliar el Protocol para cubrir las capacidades que el pipeline realmente usa, y declarar cuáles son opcionales de forma explícita (`supports("location_search") -> bool`) en vez de con `hasattr`. La normalización debe ser responsabilidad de cada fuente y devolver siempre el mismo dict — nunca invocada desde el worker.

### 3.6 🟠 Se decide en qué gastar antes de tener los datos para decidir

Este es el defecto estructural que explica el run con 254 perfiles y 0 candidatos, y **es independiente del saldo**.

Los endpoints de hashtags y reels devuelven objetos de usuario reducidos: usuario, nombre, foto, verificado, privado. **No traen biografía ni número de seguidores.** Al pasar por `_normalize_user`, esos perfiles quedan con `biography=""` y `follower_count=0`.

Después, el prefiltro que sí manda los puntúa así:

```python
rough = 0.5 * geo + 0.5 * niche
```

Y tanto `geo_score` como `niche_relevance` leen principalmente de la biografía. Con la biografía vacía, ambos tienden a cero, y **el top-50 que se manda a enriquecer queda determinado por empates en cero — es decir, por el orden de inserción del diccionario.** Se paga por enriquecer 50 handles elegidos casi al azar.

Los que sobreviven pasan luego por siete filtros secuenciales de `continue`: seguidores, bot por ER, listas negras de sufijos en el handle, país declarado, señales de otros países en la bio, umbral geográfico y palabras políticas. Cada uno razonable por separado; encadenados sobre una muestra ya aleatoria, el resultado esperado es cero.

**No se arregla bajando umbrales** (ya bajaron `min_match_score` de 35 a 5). Hay dos salidas legítimas:

- **A — Priorizar fuentes que sí traen datos.** `search_keyword` (`/v2/fbsearch/accounts`) y `topsearch` devuelven perfiles con seguidores y biografía. Usarlas como columna vertebral, y los hashtags solo como señal de refuerzo para handles ya conocidos por otra vía (que es justamente el bonus de referencia cruzada que ya existe en el score).
- **B — Aceptar que el enrichment *es* el descubrimiento** y presupuestarlo: enriquecer una muestra amplia y barata en dos fases (una llamada ligera para todos, la costosa solo para los que pasan), en vez de fingir que se puede rankear sin datos.

La opción A es más barata y se puede probar esta semana. Recomiendo A, midiendo cuántos candidatos finales aporta cada fuente antes de decidir.

### 3.7 🟡 Sin idempotencia en el encolado

`enqueue_discovery_run(run_id)` no pasa `_job_id` a ARQ. Dos clics en "Buscar", un reintento del frontend o un redeploy con jobs en vuelo pueden ejecutar el mismo run dos veces y **cobrar dos veces**. ARQ soporta deduplicación por `_job_id`: usar `f"discovery:{run_id}"` lo resuelve en una línea.

### 3.8 🟡 La lógica de negocio volvió a estar hardcodeada en el worker

Dentro de `worker.py` hay ahora, en español y embebidas en el cuerpo de la función:

- ~90 términos de "tienda" (`tienda_keywords_hard`)
- ~40 señales de "creador"
- una lista negra de sufijos de handle por país
- una lista de señales de "no venezolano" (`"españa"`, `"colombia"`, `"miami"`, …)
- palabras clave políticas

Esto **contradice directamente** el sistema `discovery_profiles` que ya se construyó, cuyo propósito era exactamente que ese vocabulario fuera dato generado por brief y no código. El pipeline volvió a ser específico de mascotas-Venezuela.

Dos consecuencias concretas: para el segundo cliente hay que volver a editar Python; y algunos filtros son demasiado gruesos — un creador venezolano cuya bio diga "envíos a Colombia" queda descartado por la lista de señales no-VE, y `"local"` o `"precio"` marcan como tienda a muchos creadores legítimos.

**Recomendación:** devolver esos vocabularios al `DiscoveryProfile` (ya existe el campo, ya existe el generador). Mantenerlos en código solo como semilla de respaldo.

### 3.9 🟡 Caché desactivada en un endpoint de pago

`search_hashtag_recent` llama con `cache_ttl=0`. Es coherente con querer datos frescos, pero durante una sesión de pruebas —80 runs en dos días sobre el mismo brief— significa pagar cada repetición. Un TTL de 30-60 minutos habría absorbido la mayor parte de esas pruebas sin afectar la calidad.

**Recomendación:** TTL de 30 min por defecto y un `force_fresh` explícito para producción, tal como ya existe en el cliente de Apify.

---

## 4. RESPUESTAS A LAS 18 PREGUNTAS DEL DOCUMENTO

### A. Análisis arquitectónico

**1. ¿La separación Discovery ↔ API ↔ Web tiene acoplamiento problemático?**
El corte por paquetes es correcto. El problema no es la separación entre capas sino **dentro** de `discovery`: `worker.py` tiene 1.762 líneas y mezcla orquestación, normalización de datos, reglas de negocio, scoring y persistencia. Además el worker vive en `apps/api` mientras la lógica que usa vive en `packages/discovery` — la frontera está en el lugar equivocado. El orquestador del pipeline debería estar en el paquete, y `apps/api` conservar solo el arranque de ARQ.

**2. ¿El flujo de steps 0-5 es correcto?**
El flujo conceptual sí (descubrir → filtrar → enriquecer → puntuar). Lo que está mal es que la decisión de gasto ocurre antes de tener datos (§3.6), y que la numeración ya no describe la realidad (§1.4). Con nueve fuentes, conviene modelarlo como un conjunto de *recolectores* configurables, cada uno con su costo declarado y su aporte medido, en vez de una secuencia numerada fija.

**3. ¿`BriefStructured → DiscoveryPlan → Candidates` es el patrón correcto?**
Sí, es el acierto de diseño del proyecto y hay que defenderlo. La degradación actual es que el worker esquiva el `DiscoveryProfile` y vuelve a hardcodear vocabulario (§3.8). El patrón no falló: se dejó de usar.

**4. ¿`instagram_source` abstracto / `hikerapi_client` concreto es la mejor forma?**
La forma es correcta; la implementación no cumple el contrato (§3.5). Un Protocol de 5 métodos frente a 13 llamadas reales, con `hasattr` y métodos privados de por medio, es una abstracción nominal. O se completa el contrato, o es más honesto eliminar la capa y admitir que hay un solo proveedor.

### B. Estrategia de costos

**5. ¿Cuál es la mejor estrategia para un pipeline útil y económico?**
En este orden: (a) fusible de presupuesto y fail-fast — sin eso lo demás es irrelevante; (b) medir aporte por fuente: cuántos candidatos *finales* produce cada una por dólar, y apagar las que no rinden; (c) caché agresiva durante desarrollo (TTL largo + un modo `replay` que reutilice el último dataset sin gastar); (d) recién entonces afinar límites. Hoy los límites se ajustan a ciegas porque no se mide el aporte de cada fuente.

**6. ¿Cómo evitar el "burn rate" con reintentos?**
Nunca reintentar errores no reintentables. 401/402/403 son permanentes hasta intervención humana: reintentarlos es quemar saldo y tiempo. Solo 429, 5xx y timeouts merecen reintento, con backoff exponencial y tope global de reintentos **por run**, no por llamada. Añadir un cortacircuitos: tras N fallos consecutivos de la fuente, abortar el run.

**7. ¿Vale la pena rehabilitar Apify como fallback?**
No como está planteado. Hoy no existe fallback (§3.5), y mantener dos proveedores completos duplica superficie de mantenimiento. Recomiendo: **un solo proveedor primario bien instrumentado**, y que la resiliencia venga de degradar con elegancia (caché + mensaje claro al usuario) en vez de un segundo proveedor a medio implementar. Si más adelante el volumen justifica multi-fuente, primero hay que completar el contrato.

### C. Calidad de candidatos

**8. ¿Por qué 0 candidatos con 254 perfiles?**
Ver §3.6. En resumen: los perfiles de hashtags llegan sin biografía ni seguidores; el prefiltro los puntúa con esos campos vacíos, así que el top-50 a enriquecer sale prácticamente al azar; y sobre esa muestra se aplican siete filtros encadenados. El resultado esperado es cero. (Los runs de 10 segundos son otra cosa: saldo agotado.)

**9. ¿El scoring está mal calibrado?**
El scoring no es el cuello de botella — bajarlo de 35 a 5 no cambió el resultado, que es la prueba de que el problema está aguas arriba. Los pesos actuales (0.389/0.278/0.222/0.111) son razonables y **no hay que tocarlos sin datos**: recalibrar sin decisiones reales de usuario es sobreajustar a ruido. Lo que sí hay que arreglar es qué llega al scoring.

**10. ¿Cómo encontrar creadores reales y no tiendas?**
La señal más fiable no está en la biografía sino en el comportamiento: proporción comentarios/likes (los creadores conversan, las tiendas reciben consultas de precio), regularidad de publicación, presencia de rostro humano recurrente, y ratio seguidos/seguidores. Las listas de palabras son frágiles y sesgadas — `"local"` y `"precio"` descartan creadores legítimos. Recomiendo mover el peso de la detección hacia métricas de engagement, que ya llegan en el enrichment, y dejar el vocabulario como señal secundaria proveniente del `DiscoveryProfile`.

### D. Observabilidad

**11. ¿Qué métricas mínimas?**
Cuatro familias, todas por `run_id`: **costo** (llamadas y USD por fuente y por step), **embudo** (cuántos perfiles entran y salen de cada etapa, con el motivo de descarte agregado), **calidad** (candidatos finales por fuente de origen — es la métrica que hoy falta y la que permite apagar fuentes) y **fiabilidad** (tasa de error por fuente, separando 402/429/5xx). La cuarta es la que habría avisado del saldo el primer día.

**12. ¿Cómo construir el dashboard de costos?**
No hace falta herramienta nueva. Ya existen Prometheus y `api_costs`. Con un contador por `(run_id, source, step)` y una vista SQL sobre `api_costs` agregada por día y campaña se cubre el 90% del valor. Lo importante no es el gráfico sino **la alerta**: aviso al 70% del presupuesto mensual y corte al 100%.

### E. Arquitectura de fallback

**13. Si HikerAPI falla, ¿cuál debe ser la estrategia?**
Distinguir el tipo de fallo. Saldo o credenciales: abortar de inmediato con mensaje accionable, nunca degradar en silencio (§3.1). Rate limit o 5xx: reintentar con backoff dentro de un tope por run. Caída prolongada: servir desde caché lo que haya y marcar el run como `partial` diciéndolo explícitamente.

**14. ¿Arreglar Apify o buscar otra cosa?**
Ver pregunta 7. Antes de evaluar proveedores hay que poder medir: sin métricas de aporte por fuente no hay forma de comparar dos proveedores objetivamente.

**15. ¿Meta Business API / TikTok Research API?**
Meta Graph solo devuelve datos de cuentas que autorizaron a la app: sirve para medir campañas en marcha, no para descubrir influencers nuevos. Para el caso de uso de Lens no sustituye a HikerAPI. TikTok Research API está restringida a instituciones académicas en la mayoría de jurisdicciones. **Ninguna de las dos resuelve el problema de descubrimiento**; conviene sacarlas del roadmap como alternativa de datos y dejarlas, si acaso, como enriquecimiento posterior.

### F. Refactor

**16. ¿Qué partes de `worker.py` están "smelly"?**
Por orden de daño: los siete bloques de merge duplicados (§3.4); las ~150 líneas de vocabulario de negocio embebido (§3.8); la función `discovery_run_task` de más de 1.000 líneas con un solo `try` gigante que convierte cualquier fallo en un estado indistinguible; el prefiltro muerto (§3.3); y la numeración de steps contradictoria (§1.4).

**17. ¿Cómo manejar el "freshness"?**
Por tipo de dato y no de forma global: el perfil (seguidores, bio) tolera 24 h sin problema; los posts recientes de un hashtag, 30-60 min; la lista de ubicaciones, semanas. Y un `force_fresh` explícito solo cuando el usuario pide "dame otros". Hoy hay un TTL uniforme y un endpoint sin caché (§3.9), que es el peor de los dos mundos.

**18. ¿Separar scoring de pipeline?**
Sí, y en buena medida ya está hecho: `scoring/lens_score.py` y `scoring/niche.py` existen. Lo que falta es dejar de reintroducir reglas de negocio en el worker (§3.8). El worker debe orquestar y no opinar sobre qué es una tienda.

---

## 5. PLAN DE ACCIÓN

### Corto plazo — esta semana (antes de recargar créditos)

| # | Acción | Por qué | Esfuerzo |
|---|---|---|---|
| 1 | **Fail-fast en 401/402/403/429** con excepción propia; el run aborta con `status="failed"` y mensaje accionable en el chat | Sin esto, la próxima recarga se puede quemar igual y el sistema volverá a decir "0 candidatos" | 2 h |
| 2 | **Fusible de presupuesto**: acumulado mensual + corte + tope de llamadas por run + aviso al 70% | Es el control que faltaba; convierte un riesgo abierto en uno acotado | 3 h |
| 3 | **Idempotencia en el encolado** (`_job_id` en ARQ) | Elimina el cobro doble por doble clic o redeploy | 15 min |
| 4 | **Eliminar el prefiltro muerto y su log** (§3.3) | Telemetría que engaña es peor que no tener telemetría | 30 min |
| 5 | **Arreglar `_fetch_step2p6`**: o se completa `niche_kws`, o se elimina | Gasta una llamada por run para devolver nada | 30 min |
| 6 | **Caché de 30 min en `search_hashtag_recent`** | Las sesiones de prueba dejan de pagar cada repetición | 15 min |
| 7 | **Corregir ambos documentos** con las secciones 1 y 2 de este informe | La doc está guiando decisiones con datos falsos | 1 h |

**Total: ~7-8 h.** Recomiendo no recargar créditos hasta tener 1, 2 y 3 desplegados.

### Mediano plazo — este mes

| # | Acción | Esfuerzo |
|---|---|---|
| 8 | Unificar los 7 bloques de merge en una función; recuperar `country` e `is_private` (§3.4) | 1.5 h |
| 9 | Métrica de **aporte por fuente** (candidatos finales por fuente y por dólar) y apagar las que no rindan | 3 h |
| 10 | Reordenar el descubrimiento hacia fuentes con datos completos (§3.6, opción A) | 4 h |
| 11 | Devolver el vocabulario de negocio al `DiscoveryProfile` (§3.8) | 3 h |
| 12 | Configuración única del pipeline en Pydantic Settings, registrada al inicio de cada run (§2.5) | 2 h |
| 13 | Modo `replay`: repetir un run sobre el último dataset cacheado, con costo cero, para probar scoring | 3 h |

El punto 13 merece énfasis: **la mayor parte de los $50 se gastó probando lógica de scoring, que no necesita datos frescos.** Un modo replay habría permitido las mismas 80 iteraciones por el costo de una.

### Largo plazo — próximo trimestre

| # | Acción |
|---|---|
| 14 | Completar el contrato `InstagramSource` o eliminar la capa (§3.5) — decisión explícita, no ambigüedad |
| 15 | Multi-tenancy real: filtrado por unidad de negocio en la aplicación o rol de base separado (§2.3) — **obligatorio antes del segundo cliente** |
| 16 | Extraer el orquestador de `apps/api` a `packages/discovery` |
| 17 | Bucle de retroalimentación (guardado/descartado) y recalibración del scoring **con datos reales**, no antes de ~200 decisiones |

---

## 6. LO QUE NO RECOMIENDO HACER

- **Recargar créditos antes de tener el fusible.** Es la decisión con peor relación riesgo/beneficio disponible ahora mismo.
- **Seguir bajando `min_match_score`.** Ya bajó de 35 a 5 sin efecto; el problema no está ahí y cada bajada degrada la calidad de lo que sí llegue a salir.
- **Recalibrar los pesos del score.** Sin decisiones reales de usuario es sobreajuste a ruido.
- **Añadir un tercer proveedor de datos** mientras el contrato del primero esté incompleto.
- **Invertir en Meta Business API o TikTok Research API** esperando que resuelvan el descubrimiento: por diseño no lo hacen (pregunta 15).
- **Reescribir `worker.py` de cero.** Es grande y tiene problemas, pero funciona y contiene mucho conocimiento del dominio. Extraer por partes, con la red de pruebas puesta.

---

*Revisión sobre `a250b0c`. No se ejecutó código del repositorio ni se consumieron créditos de ninguna API.*
