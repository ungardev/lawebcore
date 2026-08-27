# PLAN DE ALINEACIÓN Y DESARROLLO — LENS DISCOVERY

## Hitos 30 a 35 · Dirección técnica

> **Repositorio:** `github.com/ungardev/lawebcore` **Commit de código verificado:** `81db353` (21-08-26) — sigue siendo HEAD de código; `13944c0` (25-08-26) es solo documentación **Base normativa:** Informe de Alineación Técnica de Santiago Lanz v1.2 (24-08-26) **Documento que corrige y extiende:** `PLAN_MAIN_ALINEACION_LENS_2026-08-25.md` **Fecha:** 25-08-26 **Dirección técnica:** Claude Fable 5 · Full Stack Engineer Senior **Ejecución:** Ungar Villamizar **Saldo HikerAPI:** $43,00 USD

---

## 0\. Estado de la verificación

Antes de dictar un plan sobre un informe ajeno hay que comprobarlo. Descargué el árbol del repositorio en el commit `81db353` y verifiqué las afirmaciones de Lanz una por una contra el código real.

| \# | Afirmación de Lanz | Verificación | Resultado |
| :---- | :---- | :---- | :---- |
| 1 | `worker.py:534` ejecuta `hashtag_queries[:3]` | Línea 534 literal | ✅ Exacto |
| 2 | `worker.py:547` ejecuta `hashtag_queries[:2]` | Línea 547 literal | ✅ Exacto |
| 3 | `worker.py:562` ejecuta `keyword_queries[:3]` | Línea 562 literal | ✅ Exacto |
| 4 | `worker.py:585` ejecuta `keyword_queries[:1]` | Línea 585 literal | ✅ Exacto |
| 5 | `worker.py:394-395` guarda el tamaño del plan, no el ejecutado | `len(plan.keyword_queries)` / `len(plan.hashtag_queries)` | ✅ Exacto |
| 6 | `untracked_no_followers` tiene un solo punto de incremento | Único `+= 1` en línea 1282 | ✅ Exacto |
| 7 | `worker.py:1751` no considera candidatos entregados | `"partial" if step3_degraded else "completed"` | ✅ Exacto |
| 8 | 33 cadenas `or 0` en `worker.py` | Conteo automático: **33** | ✅ Exacto |
| 9 | `budget_fuse.can_make_call()` devuelve `True` ante error | Docstring dice "Returns False…", línea 222 `return True` | ✅ Exacto |
| 10 | `_normalize_user()` emite nombres duales | Líneas 842-862, pares confirmados | ✅ Exacto |
| 11 | Caché de perfil vence en 24 h | `CACHE_TTL_PROFILE = 86400`, línea 17 | ✅ Exacto |
| 12 | `discovery.py` guarda tier fijo y sin métricas | Línea 858 `"primary_tier": "MICRO"`, línea 864 `"discovery_query": ""` | ✅ Exacto |

**Doce de doce.** El informe de Lanz es preciso al número de línea. Se adopta como base normativa de este plan sin reservas.

Métricas propias del repositorio, medidas en el mismo commit:

| Métrica | Valor |
| :---- | :---- |
| `worker.py` | 2.246 líneas |
| `except Exception` solo en `worker.py` | 27 |
| Cadenas `or 0` en `worker.py` | 33 |
| Menciones camelCase (`followersCount`, `followsCount`, `postsCount`, `isBusinessAccount`) en `worker.py` | **59** |
| Menciones snake\_case (`follower_count`, `following_count`, `posts_count`) en `worker.py` | **46** |

---

## 1\. Correcciones al PLAN MAIN

El plan generado por MiniMax es un buen resumen del informe, pero introduce tres desviaciones que hay que corregir antes de ejecutar. Ninguna es menor.

### 1.1 El orden de fases contradice a Lanz

Lanz ordena su §7 así: **1** fallar en voz alta · **2** contrato de datos · **3** tabla maestra · **4** ensanchar la búsqueda · **5** decisión de negocio.

El PLAN MAIN lo reordena a: 1 fallar en voz alta · **2 ensanchar** · 3 contrato · 4 tabla maestra.

Adelantar el ensanche tiene una consecuencia concreta: multiplica el volumen de perfiles que atraviesan un normalizador que todavía convierte «dato ausente» en cero. Se pagarían llamadas adicionales para descubrir más perfiles que el mismo defecto sigue descartando en silencio. El ensanche es la palanca de calidad, pero su valor diagnóstico —«si el conjunto crece y el resultado no cambia, entonces el problema es de orden y no de alcance»— solo existe si el instrumento que mide el resultado ya dice la verdad.

**Decisión: se respeta el orden de Lanz.** El ensanche va después del contrato de datos.

### 1.2 La aritmética de costos está invertida

El PLAN MAIN afirma que tras ensanchar la búsqueda quedan «\~97 runs restantes (vs 67 antes del ensanche)». Ensanchar aumenta el costo por corrida; por lo tanto reduce la cantidad de corridas que el saldo alcanza. El número no puede subir.

Cálculo correcto, con las constantes verificadas en el código (`ESTIMATED_DISCOVERY_CALLS = 32`, `MAX_HANDLES_TO_ENRICH = 25`) y la tarifa vigente de $0,02 por llamada:

| Escenario | Llamadas por corrida | Costo por corrida | Corridas con $43,00 |
| :---- | :---- | :---- | :---- |
| Actual | 32 \+ 25 \= 57 | $1,14 | **37** |
| Ensanche conservador (+22 llamadas) | 79 | $1,58 | **27** |
| Ensanche agresivo (estimado) | \~130 | $2,60 | **16** |

**Decisión: el ensanche se aprueba solo en su versión conservadora, y solo después de la Fase 0**, porque el número de corridas disponibles cae un 27% y eso es una decisión de presupuesto, no de ingeniería.

### 1.3 La derivación de tier usa la escala equivocada

El PLAN MAIN propone un `_derive_tier()` con la escala genérica de cinco tramos (NANO \<10K, MICRO \<100K, MID \<500K, MACRO \<1M, MEGA). El manual de filtros de la agencia (`14_influencer_lens_manual_filtros_ia.md`, §2.1) establece que **discovery y scoring usan la escala granular de nueve sub-tiers**, y que la escala genérica es solo para pricing y reportes evolutivos.

Implementar la escala genérica en el camino de discovery contradice la metodología propia de la casa y hace que el score de engagement se compare contra un benchmark que no corresponde al sub-tier real del perfil.

**Decisión: `_derive_tier()` devuelve el sub-tier de nueve tramos.** Ver Hito 32.3.

---

## 2\. Hallazgos nuevos, no cubiertos por el informe

Cinco cosas que aparecieron al revisar el código y que ninguno de los dos documentos previos recoge.

### H-1 · El `or 0` no nace en `worker.py`. Nace en el cliente. 🔴

Lanz señala `worker.py:1280` como el punto donde un perfil sin seguidores se convierte en cero. Es cierto, pero es el segundo lugar donde ocurre. El primero está tres capas antes, en `packages/discovery/discovery/tools/hikerapi_client.py:823-825`:

follower\_count  \= user.get("follower\_count", 0\) or 0

following\_count \= user.get("following\_count", 0\) or 0

media\_count     \= user.get("media\_count", 0\) or user.get("posts\_count", 0\) or 0

El normalizador ya destruyó la diferencia entre «el proveedor no mandó el campo» y «el perfil tiene cero seguidores» **antes de que el worker vea el dato**. Cuando `worker.py:1280` hace su propio `or 0`, está operando sobre un cero que ya venía fabricado.

**Consecuencia para el plan:** corregir únicamente `worker.py` —que es lo que propone el PLAN MAIN en su Fase 1— no puede funcionar. La información ya no existe en ese punto. **La corrección tiene que empezar en la línea 823 del cliente**, y solo después propagar hacia el worker. Este es el cambio de secuencia más importante de este documento.

### H-2 · El sistema podría estar excluyendo por diseño el tier que sostiene el negocio ⚠️

En `worker.py:54-55`:

TIER\_MIN\_FOLLOWERS \= 5\_000

TIER\_MAX\_FOLLOWERS \= 50\_000

La metodología de la agencia establece que los Nanos aportan entre el **80% y el 85% de las views totales** de una campaña, y define NANO bajo como el tramo de 500 a 5.000 seguidores. Un piso de 5.000 deja ese tramo completo fuera del rango, y un techo de 50.000 corta MICRO alto y todo lo que está por encima.

No pude determinar desde el código si estas constantes actúan como filtro duro o solo como límites del reparto por tiers (`TIER_DISTRIBUTION`, línea 58). **La diferencia es decisiva:** si es filtro duro, el producto está estructuralmente incapacitado para encontrar el perfil que más rinde en las campañas de la agencia, y ninguna corrección de las fases siguientes lo arregla.

**Acción: es la primera pregunta de la Fase 0\.** Antes que las cuatro de Lanz.

### H-3 · Los pares de nombres duales son más de los reportados

Lanz lista cinco pares. El retorno de `_normalize_user()` (líneas 842-862) tiene siete conceptos duplicados:

| Concepto | Nombres emitidos simultáneamente |
| :---- | :---- |
| Seguidores | `follower_count` · `followersCount` |
| Seguidos | `following_count` · `followsCount` |
| Publicaciones | `posts_count` · `postsCount` |
| Cuenta de empresa | `is_business` · `isBusinessAccount` |
| Verificado | `is_verified` · `verified` |
| Biografía | `biography` · `bio` |
| Foto de perfil | `avatar_url` · `profilePicUrl` · `profilePicUrlHD` |

### H-4 · La convención legacy domina, no es residual

En `worker.py`, la convención del proveedor retirado aparece **59 veces** contra **46** de la convención vigente. No se trata de una migración a medio terminar: la nomenclatura de Apify sigue siendo la mayoritaria en el archivo central del pipeline, siete meses después de haber cambiado de proveedor.

### H-5 · Cuatro fichas de la auditoría de plataforma siguen sin dueño

La auditoría de interfaz del 19-08-26 documentó defectos de capa de producto que ni el informe de Lanz ni el PLAN MAIN abordan, porque se ven ejecutando la aplicación y no leyendo el código:

| Ficha | Defecto | Riesgo |
| :---- | :---- | :---- |
| L-02 | El paso 6 del asistente ejecuta con el brief vacío | Cada corrida en falso consume saldo real |
| L-03 | Los filtros de exclusión corporativa son texto libre interpretado por el modelo | **Riesgo de compliance con Nestlé** — no es determinista ni auditable |
| L-04 | El resumen previo a ejecutar omite producto, nicho y exclusiones | No se puede verificar qué se va a ejecutar antes de pagar |
| L-05 | La cuenta oficial del propio cliente aparece como candidato | El único candidato entregado en agosto fue `@dogchowve` |

Se incorporan como Hito 35\.

---

## 3\. Plan de Logging — diseño

Esta sección responde al pedido explícito: hoy no hay veracidad sobre qué falla. Lanz define el requisito («que el sistema pueda fallar en voz alta») pero no diseña la capa. Este es el diseño.

### 3.1 Principio rector

> **Un sistema observable no es el que registra mucho. Es el que puede responder, sin adivinar, por qué un perfil no llegó al entregable.**

Toda la arquitectura de logging se subordina a esa pregunta. Si un log no ayuda a responderla, no se escribe.

### 3.2 Fundación existente

`structlog` ya está en uso (`hikerapi_client.py:14`, `worker.py`). No hay que introducir una dependencia nueva. Lo que falta es disciplina sobre lo que ya existe: contexto propagado, taxonomía cerrada de eventos, y persistencia de lo que hoy solo va a `stdout` y Railway rota.

### 3.3 Capa 1 — Contexto de corrida propagado

Todo registro emitido durante una corrida debe llevar `run_id` sin que nadie tenga que pasarlo a mano por la pila de llamadas.

\# Al entrar a discovery\_run\_task, una sola vez:

structlog.contextvars.bind\_contextvars(

    run\_id=run\_id,

    mode=discovery\_mode,

    brief\_id=brief\_id,

    provider="hikerapi",

)

\# Al salir, siempre, incluso ante excepción:

structlog.contextvars.clear\_contextvars()

Regla: **ningún log dentro del pipeline vuelve a recibir `run_id` como argumento explícito.** Si aparece, es señal de que el contexto no se está propagando.

### 3.4 Capa 2 — Taxonomía cerrada de eventos

Los nombres de evento dejan de ser texto libre. Se declara un enumerado y el linter rechaza cualquier otro:

run.started              run.finished            run.aborted

plan.built               plan.executed

source.called            source.succeeded        source.failed

profile.discovered       profile.deduped         profile.dropped

enrich.requested         enrich.succeeded        enrich.failed

score.computed           score.fallback\_used

candidate.persisted      candidate.saved\_as\_influencer

budget.reserved          budget.exhausted        budget.threshold\_hit

contract.violation

`contract.violation` es el evento que se emite cuando un dato llega con una forma que el contrato de la Fase 31 no admite. Debe ser ruidoso: es el canario de toda la capa de datos.

### 3.5 Capa 3 — Libro de descartes

Es el corazón del diseño y lo que hoy no existe en ninguna forma. **Ningún perfil puede desaparecer del pipeline sin dejar un registro con causa.**

def drop\_profile(username: str, reason: DropReason, stage: str, detail: dict | None \= None):

    """Único punto de salida de un perfil del pipeline. No hay \`continue\` sin pasar por acá."""

    \_drop\_ledger\[reason\] \+= 1

    logger.info("profile.dropped", username=username, reason=reason.value, stage=stage, \*\*(detail or {}))

Enumerado de causas, cerrado y exhaustivo:

| Código | Significado | Etapa |
| :---- | :---- | :---- |
| `MISSING_FOLLOWER_FIELD` | El proveedor nunca envió el campo. **No es cero.** | normalización |
| `ENRICHMENT_FAILED` | El enriquecimiento corrió y falló | enriquecimiento |
| `ENRICHMENT_SKIPPED_BUDGET` | No se enriqueció por saldo (402 o fusible) | enriquecimiento |
| `BELOW_MIN_FOLLOWERS` | Por debajo del piso configurado | prefiltro |
| `ABOVE_MAX_FOLLOWERS` | Por encima del techo configurado | prefiltro |
| `GEO_MISMATCH` | No cumple el criterio geográfico | prefiltro |
| `NICHE_MISMATCH` | No cumple el nicho del brief | scoring |
| `EXCLUDED_STORE` | Comercio, no creador | exclusión |
| `EXCLUDED_FOUNDATION` | Fundación o ente gubernamental | exclusión |
| `EXCLUDED_BRAND_OWN` | Cuenta de la marca del brief o cuenta asociada | exclusión |
| `FRAUD_SIGNAL` | Señal de engagement inflado | anti-fraude |
| `DUPLICATE_HANDLE` | Ya presente en el conjunto | deduplicación |
| `PRIVATE_ACCOUNT` | Cuenta privada, sin datos suficientes | normalización |
| `SCORE_BELOW_THRESHOLD` | Puntaje bajo el umbral de entrega | scoring |

Los tres códigos de exclusión resuelven además la ficha L-03: convierten el filtro de brand safety de una nota en texto libre a un descarte trazable, con nombre y con recuento. Eso es lo que se le puede mostrar a compliance de Nestlé.

### 3.6 Capa 4 — Embudo con invariante

Por corrida se registra un embudo monótono:

descubiertos → deduplicados → prefiltrados → enriquecidos → puntuados → entregados

Y se verifica la identidad contable:

assert entrada\_etapa \- salida\_etapa \== sum(descartes\_de\_esa\_etapa)

Si la identidad no se cumple, hay un camino de salida que nadie registró. La corrida se marca `inconsistent` y se emite `contract.violation`.

**Esta es la propiedad que hace al instrumento auditarse a sí mismo.** Es lo que impide que el problema de fondo —perfiles que desaparecen sin rastro— vuelva a ocurrir, incluso si alguien agrega un filtro nuevo y olvida instrumentarlo. El filtro nuevo rompe la identidad y la corrida lo delata.

### 3.7 Capa 5 — Máquina de estados de la corrida

El estado actual (`completed` / `partial`) mezcla haber corrido con haber entregado. Se reemplaza por:

| Estado | Condición | Interpretación |
| :---- | :---- | :---- |
| `queued` | En cola | — |
| `running` | En ejecución | — |
| `delivered` | ≥1 candidato entregado, sin degradación | Éxito |
| `degraded` | ≥1 candidato, con alguna etapa degradada | Éxito parcial |
| `empty` | 0 candidatos, embudo cuadra | **Fracaso explicado** — el libro de descartes dice por qué |
| `inconsistent` | 0 candidatos, embudo no cuadra | **Fracaso del instrumento** — hay una fuga sin registrar |
| `aborted_budget` | Detenida por saldo | Fracaso por presupuesto |
| `failed` | Excepción no controlada | Fracaso técnico |

La distinción entre `empty` e `inconsistent` es la que hoy no existe y la que convierte cada corrida en cero en un dato utilizable en vez de un misterio.

### 3.8 Capa 6 — Persistencia

Los registros no pueden vivir solo en la salida estándar. Se añade una tabla:

CREATE TABLE discovery\_run\_events (

  id            BIGSERIAL PRIMARY KEY,

  run\_id        UUID NOT NULL REFERENCES discovery\_runs(id),

  ts            TIMESTAMPTZ NOT NULL DEFAULT now(),

  event         TEXT NOT NULL,          \-- taxonomía cerrada §3.4

  stage         TEXT,

  reason\_code   TEXT,                   \-- enumerado §3.5

  username      TEXT,

  payload       JSONB NOT NULL DEFAULT '{}'::jsonb

);

CREATE INDEX idx\_run\_events\_run    ON discovery\_run\_events(run\_id);

CREATE INDEX idx\_run\_events\_reason ON discovery\_run\_events(reason\_code) WHERE reason\_code IS NOT NULL;

Con esa tabla, la pregunta «¿por qué esta corrida no entregó nada?» se responde con una consulta, no con una investigación.

### 3.9 Capa 7 — Alertas

Tres reglas, evaluadas al cerrar cada corrida:

| Regla | Umbral | Severidad |
| :---- | :---- | :---- |
| Corrida termina en `inconsistent` | Cualquiera | 🔴 Crítica — el instrumento está roto |
| Una sola causa concentra \>70% de los descartes | Por corrida | 🟠 Alta — nombra la causa en la alerta |
| Tasa de error del proveedor \>20% | Por corrida | 🟠 Alta |
| Tres corridas consecutivas en `empty` | Ventana móvil | 🟠 Alta |

### 3.10 Política de niveles

| Nivel | Cuándo | Regla dura |
| :---- | :---- | :---- |
| `ERROR` | Requiere acción humana | Nunca se usa para algo que el sistema ya manejó |
| `WARNING` | Degradado pero continuó | **Obligatorio incrementar un contador.** Un warning sin contador está prohibido: es exactamente el patrón que produjo este informe |
| `INFO` | Ciclo de vida y embudo | — |
| `DEBUG` | Detalle de desarrollo | Apagado en producción |

---

## 4\. Hitos

Numeración continuando desde el Hito 29\. Cada hito es desplegable y reversible por separado. Nada se reescribe: se corrige sobre lo construido, que es la indicación explícita de Lanz y de la agencia.

### Fase 0 — Verificaciones (sin código, \~45 min)

| \# | Pregunta | Cómo se responde | Bloquea |
| :---- | :---- | :---- | :---- |
| **V0** | ¿`TIER_MIN_FOLLOWERS = 5_000` es filtro duro o reparto por tiers? | Lectura de sus usos en `worker.py` | **Todo** — hallazgo H-2 |
| V1 | ¿Qué modelo está configurado en las variables de Railway? | Panel de Railway | Hito 34 |
| V2 | ¿El alias `deepseek-chat` todavía resuelve? (Railway tiene `deepseek-chat` retired) | **SÍ resuelve** pero está discontinuado. Cambiar a `deepseek-v4-flash` | Hito 34 |
| V3 | ¿Está activada la recuperación a un punto en el tiempo en la base? | Panel de Railway | Riesgo de pérdida total |
| V4 | ¿Redis tiene política de desalojo por memoria? | Panel de Railway | Integridad de contadores de gasto |

**Entregable:** `docs/LANZ_VERIFICACIONES_2026-08-25.md` con evidencia de cada respuesta.

---

### HITO 30 — Observabilidad y verdad del sistema

> Lanz §7.1 · **Bloqueante de todo lo demás.** Mientras un error produzca un valor plausible, ninguna mejora es verificable — incluidas las 29 ya hechas.

| Sub-hito | Alcance | Archivos |
| :---- | :---- | :---- |
| 30.1 | Contexto de corrida propagado con `contextvars` (§3.3) | `worker.py` |
| 30.2 | Taxonomía cerrada de eventos (§3.4) | nuevo `packages/shared-core/shared_core/observability.py` |
| 30.3 | Libro de descartes con enumerado de causas (§3.5) | `worker.py`, `observability.py` |
| 30.4 | Embudo con invariante contable (§3.6) | `worker.py` |
| 30.5 | Máquina de estados de corrida (§3.7) | `worker.py:1745-1760` |
| 30.6 | Tabla `discovery_run_events` \+ migración (§3.8) | `supabase/migrations/` |
| 30.7 | Mensaje al usuario derivado de la causa dominante del libro | `worker.py:140-180` |
| 30.8 | Eliminar `can_make_call()` y `check_run_limit()` — código muerto que documenta el criterio contrario al vigente | `budget_fuse.py:212-222, 262-264` |

**Nota sobre 30.7:** el mensaje deja de tener condiciones cableadas. Se deriva de `max(drop_ledger)` y nombra el código de causa. El anclaje al caso `0c44ea23` en el docstring de la línea 163 se elimina: un ejemplo concreto en una función genérica es lo que orientó el diagnóstico hacia el saldo durante tres semanas.

**Criterio de aceptación:**

- [ ] Ninguna corrida puede terminar sin que el embudo cuadre o se marque `inconsistent`  
- [ ] Todo `continue` que descarta un perfil pasa por `drop_profile()`  
- [ ] Una corrida en cero se puede explicar con una consulta SQL sobre `discovery_run_events`  
- [ ] `worker.py` no contiene `WARNING` sin contador asociado  
- [ ] Estado `delivered` / `empty` / `inconsistent` operativo  
- [ ] Tests: `test_hito30_observability.py` — invariante del embudo, causa dominante, estados terminales, ausencia de código muerto

**Rollback:** el hito solo agrega instrumentación y una tabla nueva. Revertir es un `git revert` sin migración de datos hacia atrás.

---

### HITO 31 — Contrato de datos único

> Lanz §7.2 · La regla ya está escrita en `13_data_contract_hub.md` para el otro subsistema. Se transporta, no se inventa.

| Sub-hito | Alcance | Archivos |
| :---- | :---- | :---- |
| **31.1** | **`_normalize_user()` deja de fabricar ceros.** Campo ausente devuelve `None`. Es el hallazgo H-1 y es lo primero. | `hikerapi_client.py:823-825` |
| 31.2 | `_normalize_user()` emite una sola forma por concepto: snake\_case inglés. Se eliminan los siete pares duales | `hikerapi_client.py:842-862` |
| 31.3 | Ventana de compatibilidad: capa de lectura que acepta ambas convenciones durante un despliegue, con `contract.violation` registrado cada vez que llega la legacy | `observability.py` |
| 31.4 | Sustitución de las 33 cadenas `or 0` en `worker.py`. `None` se propaga; el descarte se decide con causa explícita | `worker.py` |
| 31.5 | Documento `docs/13a_data_contract_discovery.md` v1.0, anexo del contrato del hub | `docs/` |
| 31.6 | Prueba de guardia en integración continua: falla el build si reaparece `or 0` en contexto de métricas o si vuelve la convención legacy | `apps/api/tests/` |

**Secuencia obligatoria: 31.1 antes que 31.4.** Corregir el worker sin corregir el cliente no tiene efecto — la información ya se destruyó aguas arriba. Esta es la corrección más importante que este plan hace sobre el PLAN MAIN.

**Sobre la ventana de compatibilidad (31.3):** es lo que permite cumplir «sin explotar nada». El despliegue no rompe a los consumidores que todavía leen `followersCount`; los registra y los va apagando. Se retira en el Hito 33, cuando el contador de `contract.violation` llegue a cero por siete días.

**Criterio de aceptación:**

- [ ] `_normalize_user()` devuelve `None` para campo ausente, nunca `0`  
- [ ] Un solo nombre por concepto en la salida del normalizador  
- [ ] Cero cadenas `or 0` en contexto de métricas en `worker.py`  
- [ ] `contract.violation` se emite y se cuenta  
- [ ] Tests: `test_hito31_data_contract.py`

**Rollback:** bandera de entorno `CONTRACT_STRICT=false` que restituye la emisión dual durante un despliegue. Se retira con el hito.

---

### HITO 32 — El camino a la tabla maestra

> Lanz §7.3 · El modelo de entidades existe desde la migración `00000000000005`. Faltan cuatro cosas en el camino, no el camino.

| Sub-hito | Alcance | Archivos |
| :---- | :---- | :---- |
| 32.1 | `POST /candidates/{id}/save` arrastra las métricas pagadas: `follower_count`, `engagement_rate`, `avg_likes`, más `raw_data`, `source_id` y `fetched_at` | `discovery.py:850-869` |
| 32.2 | Deduplicación por handle \+ índice único en `influencers.primary_handle`. Segundo guardado actualiza, no duplica | `discovery.py`, migración nueva |
| 32.3 | `_derive_tier()` con **la escala de nueve sub-tiers de LWFA**, no la genérica de cinco. Corrección 1.3 | `discovery.py` |
| 32.4 | Se crean las filas de `influencer_social_accounts` e `influencer_metrics_snapshot` | `discovery.py` |
| 32.5 | Política de frescura de 7 días: no se vuelve a pagar un perfil con instantánea reciente. Reemplaza al caché de 24 h como mecanismo de ahorro | `discovery.py`, `hikerapi_client.py:17` |
| 32.6 | Lista de exclusión por marca: la cuenta del cliente del brief y sus variantes nunca son candidatas. Cierra la ficha L-05 | `worker.py`, tabla de configuración por marca |
| 32.7 | `worker.py:1739-1741` deja de marcar `status = "saved"` sin crear el influencer detrás | `worker.py` |

**Sobre 32.5:** es el sub-hito con retorno económico directo. Hoy un perfil pagado vence a las 24 horas y la siguiente búsqueda que se solape vuelve a comprarlo. Con la instantánea persistida y una ventana de frescura de siete días, el gasto en el proveedor deja de ser un costo que se repite y pasa a ser un activo que se acumula. Es la diferencia entre una herramienta que cobra por búsqueda y una base de datos propia.

**Criterio de aceptación:**

- [ ] Guardar un candidato produce filas en las tres tablas  
- [ ] El mismo handle guardado dos veces no produce dos influencers  
- [ ] El tier corresponde al sub-tier real según la tabla de nueve tramos  
- [ ] Un perfil con instantánea de menos de 7 días no genera llamada al proveedor  
- [ ] La cuenta de la marca del brief nunca aparece como candidato  
- [ ] Tests: `test_hito32_master_table.py`

**Rollback:** el índice único es la única operación no trivialmente reversible. Se aplica en dos pasos — primero detección y reporte de duplicados existentes, después la restricción — para no fallar el despliegue si ya hay handles repetidos en la tabla.

---

### HITO 33 — Ensanchar la búsqueda

> Lanz §7.4 · Lo único que sube el techo de calidad. Ningún ajuste de puntaje rescata a quien nunca entró al conjunto.

| Sub-hito | Alcance |
| :---- | :---- |
| 33.1 | Las cuatro constantes dejan de estar cableadas y pasan a configuración por entorno |
| 33.2 | Ensanche conservador: `[:3]→[:5]`, `[:2]→[:3]`, `[:3]→[:5]`, `[:1]→[:2]` |
| 33.3 | La metadata registra ejecutado y planificado por separado, más el cociente entre ambos |
| 33.4 | Corrida de medición: misma brief antes y después, comparando el embudo del Hito 30 |
| 33.5 | Retirar la ventana de compatibilidad del Hito 31.3 si `contract.violation` lleva siete días en cero |

**Criterio de parada propio.** Este hito trae su propia respuesta: si el conjunto de candidatos crece y el resultado sigue en cero, el problema es de orden y no de alcance, y la conversación se mueve al ranking. Es la pregunta que hoy nadie puede responder, y una sola corrida instrumentada la responde.

**Requisito previo:** aprobación explícita del costo. El ensanche conservador lleva la corrida de $1,14 a $1,58 y reduce el saldo disponible de 37 a 27 corridas.

---

### HITO 34 — Precisión de la capa de IA

> Lanz §5.3 y §5.4 · El PLAN MAIN omite este punto por completo. Es barato y es el que fija la calidad del puntaje.

| Sub-hito | Alcance | Archivos |
| :---- | :---- | :---- |
| 34.1 | Usar el modo JSON garantizado del proveedor. `response_format` no aparece ni una vez en el repositorio | `candidate_analyzer.py` |
| 34.2 | Declarar el esquema de la respuesta de puntuación, como ya se hace con `BriefStructured` en `brief_parser.py:323`. Hoy la puntuación no valida forma | `candidate_analyzer.py:182-190` |
| 34.3 | Eliminar la extracción por expresión regular de la línea 187 | `candidate_analyzer.py` |
| 34.4 | `_fallback_scores()` deja de emitir puntajes indistinguibles de los del modelo. Se marcan y viajan marcados | `candidate_analyzer.py:348-382` |
| 34.5 | Fijar el modelo de forma explícita y quitar el valor por omisión retirado de `config.py:55` y `.env.example:32` | `config.py`, `.env.example` |
| 34.6 | Limpiar la deriva de configuración: `models/ai.py:34-35` apunta a otro proveedor y otra época | `models/ai.py`, `ai_service.py:6` |

**Sobre el cambio de modelo:** no se decide en este hito. Lanz es explícito en que el costo del modelo no es la variable relevante —el gasto está en el proveedor de datos, en otro orden de magnitud— y en que la elección de modelo depende del plan de datos que se contrate. **Primero el plan de datos, después el modelo.** Lo que sí se hace acá es dejar de depender de que el modelo acierte un formato que nadie le está exigiendo.

---

### HITO 35 — Producto y brand safety

> Fichas L-02 a L-05 de la auditoría de plataforma del 19-08-26. No las cubre ninguno de los dos documentos previos.

| Sub-hito | Alcance | Ficha |
| :---- | :---- | :---- |
| 35.1 | Validación de campos obligatorios en el envío del asistente, no solo en la transición entre pasos | L-02 |
| 35.2 | El backend rechaza una solicitud de discovery sin producto y sin nicho, antes de gastar la primera llamada | L-02 |
| 35.3 | El resumen del paso 6 muestra los ocho campos del brief y marca los vacíos | L-04 |
| 35.4 | Las exclusiones corporativas dejan de ser texto libre y pasan a reglas seleccionables, persistidas por marca, evaluadas de forma determinista, y registradas con los códigos `EXCLUDED_*` del §3.5 | **L-03** |
| 35.5 | El historial persiste la marca y el brief de cada corrida | L-06 |

**35.4 es el sub-hito con exposición comercial.** Es el control que se le describe a Nestlé como configurado en el sistema y que hoy es una nota opcional interpretada por un modelo de lenguaje. Mientras siga así, no debería presentarse como control de compliance ante el cliente.

---

## 5\. Secuencia y dependencias

Fase 0 — Verificaciones (V0 primero: define si H-2 invalida el resto)

   │

   ▼

HITO 30 — Observabilidad ◄── BLOQUEANTE ABSOLUTO

   │        sin esto, ningún hito posterior es verificable

   ▼

HITO 31 — Contrato de datos

   │        31.1 (cliente) ANTES que 31.4 (worker) — hallazgo H-1

   ▼

HITO 32 — Tabla maestra

   │        depende del contrato: no se persiste lo que no tiene forma

   ▼

HITO 33 — Ensanchar búsqueda ◄── requiere aprobación de costo

   │        trae su propio criterio de parada

   ▼

HITO 34 — Precisión de IA (independiente, puede adelantarse si hay holgura)

   │

   ▼

HITO 35 — Producto y brand safety

   │

   ▼

Decisión de negocio: plan del proveedor → después, modelo

**Hitos 30 y 31 no consumen saldo.** Se pueden ejecutar íntegros con el modo replay a costo cero. Solo el Hito 33 exige corridas reales.

---

## 6\. Reglas de ingeniería — el estándar de la casa

Lanz cierra su informe con la observación central: las prácticas que le faltan a LENS ya están escritas y andando en el mismo repositorio, para el otro subsistema. El problema no es capacidad, es un estándar que no se declaró como obligatorio. Estas son las reglas que se declaran.

| \# | Regla | Se verifica con |
| :---- | :---- | :---- |
| R1 | Un dato ausente se escribe `NULL`. Nunca `0`, nunca un valor plausible | Prueba de guardia en CI |
| R2 | Un `except` amplio o registra y re-lanza, o incrementa un contador y lo dice. Nunca traga en silencio | Revisión de código |
| R3 | Ningún perfil sale del pipeline sin pasar por `drop_profile()` con causa del enumerado | Invariante del embudo |
| R4 | Un `WARNING` sin contador asociado está prohibido | Prueba de guardia en CI |
| R5 | Los nombres de evento salen de la taxonomía cerrada. Nada de texto libre | Linter |
| R6 | La metadata registra lo que ocurrió, nunca lo que se planificó — o registra ambos, separados y etiquetados | Revisión de código |
| R7 | Un hito no se da por terminado si no puede demostrar que entregó. «Corrió sin excepción» no es evidencia | Criterio de aceptación por hito |
| R8 | Todo módulo nuevo se acoge al contrato de datos. Es obligatorio, no recomendado | Revisión de código |
| R9 | Ninguna función que documenta un límite puede devolver el valor permisivo ante un error. Los fusibles fallan cerrados | Revisión de código |
| R10 | El código muerto se borra, no se comenta ni se deja «por si acaso» | Revisión de código |

R9 nace del caso del fusible: el criterio correcto ya estaba aplicado y razonado en `reserve_and_record()`, y el opuesto quedó escrito en la función de al lado. El estándar existía; lo que faltaba era que valiera para las dos.

---

## 7\. Modelo de costos

| Concepto | Valor verificado |
| :---- | :---- |
| Llamadas de descubrimiento por corrida | 32 (`ESTIMATED_DISCOVERY_CALLS`) |
| Perfiles enriquecidos por corrida | 25 (`MAX_HANDLES_TO_ENRICH`) |
| Tope por corrida | 120 llamadas |
| Holgura sin usar | \~88 llamadas por corrida, dentro del tope ya configurado |
| Costo por corrida actual | $1,14 |
| Saldo disponible | $43,00 |
| Corridas disponibles hoy | 37 |
| Corridas tras el ensanche conservador | 27 |

**Consumo de saldo por hito:**

| Hito | Corridas reales necesarias | Costo |
| :---- | :---- | :---- |
| Fase 0 | 0 | $0 |
| 30 | 0 (modo replay) | $0 |
| 31 | 0 (modo replay) | $0 |
| 32 | 1 de validación | \~$1,14 |
| 33 | 2 de medición, antes y después | \~$2,72 |
| 34 | 1 de validación | \~$1,58 |
| 35 | 1 de validación | \~$1,58 |
| **Total** | **5** | **\~$7,02** |

Queda saldo para aproximadamente 22 corridas de operación real tras completar el plan.

---

## 8\. Lo que este plan no hace

| No se hace | Razón |
| :---- | :---- |
| Reescribir `worker.py` | Lanz es explícito: un refactor general cambia el código sin cambiar lo que se sabe, y lo que falta acá es saber. Los hitos 30 y 31 se hacen sin tocar su estructura. Cuando el sistema informe la verdad, qué conviene separar será una pregunta con datos |
| Conectar la capa semántica a LENS | Un vector reordena, no recluta. El recorte a 25 corre antes del enriquecimiento, donde un handle de hashtag trae usuario y nombre y nada más: no hay texto que vectorizar. Va después del Hito 33 y con esa expectativa |
| Cambiar de proveedor de modelo | Bloqueado por la decisión de negocio. El plan de datos primero, el modelo después |
| Implementar las ocho brechas del análisis de cobertura interno | Afinan el ranking. Suben la precisión de un conjunto que hoy tiene el techo puesto por el Hito 33\. Se eligen dos o tres después, con datos reales |
| Tocar `13_data_contract_hub.md` | Es el estándar del subsistema P.I.A.R. y está bien. Se crea el anexo `13a` para discovery |
| Eliminar el cliente del proveedor anterior | 869 líneas de código no operativo. Se retira en el Hito 33.5, cuando la ventana de compatibilidad cierre — no antes, para no perder la referencia durante la migración de nombres |

---

## 9\. Primer paso concreto

**Hoy, sin gastar saldo y sin tocar código:** responder V0 leyendo los usos de `TIER_MIN_FOLLOWERS` en `worker.py`. Si resulta ser un filtro duro, el producto no puede encontrar el tramo de creadores que aporta el 80–85% de las views de las campañas de la agencia, y ese hallazgo se antepone a todo lo demás de esta lista.

**Después:** Hito 30, íntegro, con modo replay. Es la única corrección que hace verificables a las otras cinco y a las veintinueve anteriores.

---

*Plan de desarrollo elaborado sobre el commit `81db353` del repositorio `lawebcore`, verificado línea por línea. Base normativa: Informe de Alineación Técnica de Santiago Lanz v1.2.*

*Documento generado por La Web Figital Agency · 25-08-26 · Uso interno*  
