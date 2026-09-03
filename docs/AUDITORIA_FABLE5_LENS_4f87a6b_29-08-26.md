# AUDITORÍA TÉCNICA — LENS DISCOVERY

## Verificación contra el plan de alineación Lanz v2.1 §7

> **Repositorio:** `github.com/ungardev/lawebcore` · Branch `main` **Commit auditado:** `4f87a6b` **Método:** lectura directa del árbol vía API de GitHub, archivo por archivo **Restricción:** solo lectura. Ningún archivo del repositorio fue modificado **Fuente de verdad:** el código. Donde un documento contradice al código, prevalece el código **Fecha:** 29-08-26 **Auditor:** Claude Fable 5 · Full Stack Engineer Senior

---

## 0\. FIXES CRÍTICOS — confirmación de integridad

Los seis fixes que el prompt pide confirmar sin re-analizar. **Cinco verificados intactos, uno no alcanzado.**

| \# | Fix | Estado | Evidencia |
| :---- | :---- | :---- | :---- |
| 1 | **Funnel Invariant computado** | ✅ **Intacto** | `worker.py:1823` — `funnel_ok = (len(step1_handles) - len(profiles)) == drop_ledger.total()`. **No es `True` literal.** Se pasa a `determine_final_status()` en `:1834` |
| 2 | **FunnelTracker sin `# noqa`** | ✅ **Intacto** | `worker.py:291` — `funnel = FunnelTracker()` sin supresión. Cero ocurrencias de `F841` en el archivo. `funnel.summary()` invocado en `:1841` |
| 3 | **`flush_drop_ledger()` llamado** | ✅ **Intacto** | `worker.py:1977` — `await flush_drop_ledger(str(run_id), drop_ledger, railway_pg)`. Importado en `:45` |
| 4 | **DeepSeek thinking disabled** | ✅ **Intacto** | `deepseek_client.py:64-66` — `extra_body={"thinking": {"type": "disabled"}}`. Comentario en `:45-46` documenta que `deepseek-v4-flash` lo trae activado por defecto |
| 5 | **`POLL_TERMINAL_STATUSES` (10 valores)** | ⏳ **No verificado** | No alcanzado en esta pasada. Requiere lectura de `apps/web/src/features/lens/` |
| 6 | **`response_format` en LLM sites** | ✅ **Intacto** | `candidate_analyzer.py:326` · `brief_parser.py:191` y `:361` · `deepseek_client.py:167` (dentro de `complete_json`) |

**El hallazgo crítico de la auditoría anterior — el invariante cableado a `True` — está corregido y correcto.** El fix aplicado coincide exactamente con el propuesto.

---

## 1\. TABLA DE HALLAZGOS

| \# | Hallazgo | Severidad | Estado | Archivo:Línea |
| :---- | :---- | :---- | :---- | :---- |
| **H-1** | `FunnelTracker` poblado en 3 de 6 stages — `discovered`, `deduped` y `prefiltered` quedan en 0 | 🔴 **P0** | Nuevo | `worker.py:1206, 1707, 1819` vs `observability.py:191-196` |
| **H-2** | Mismatch de nombre: el worker escribe `_discovery_query`, el endpoint lee `discovery_query` | 🔴 **P0** | Nuevo | `worker.py:397-860` vs `discovery.py:906, 927` |
| **H-3** | 57 referencias camelCase en `worker.py` — **subió** desde 55 | 🟠 P1 | Regresión | `worker.py` (conteo global) |
| **H-4** | Política de frescura no existe — sin constante en config, `enriched_at` escrito y nunca leído | 🟠 P1 | Confirmado | `config.py` (ausente) · `discovery.py:694` |
| **H-5** | 16 cadenas `or 0` en `worker.py` | 🟠 P1 | Confirmado | `worker.py` (conteo global) |
| **H-6** | 29 `except Exception` en `worker.py` | 🟠 P1 | Confirmado | `worker.py` (conteo global) |
| **H-7** | `_extract_json()` con regex sigue vivo y en uso pese a `response_format` | 🟡 P2 | Confirmado | `brief_parser.py:205-206, 309` |
| **H-8** | `is_discoverable` escrito, nunca leído — columna muerta | 🟡 P2 | Confirmado | `discovery.py:925` |
| **H-9** | `MAX_HANDLES_TO_ENRICH` sigue cableado en el worker, no externalizado a config | 🟡 P2 | Confirmado | `worker.py:50` · ausente en `config.py` |
| **H-10** | `LegacyCompatReader` referenciado en docs, inexistente en código | 🟡 P2 | Confirmado | `observability.py` (0 referencias) |
| **H-11** | `CONTRACT_VIOLATION` definido en el enum, nunca emitido | 🟡 P2 | Confirmado | `observability.py:48` |
| **H-12** | `assert_invariant()` definido en `FunnelTracker`, nunca invocado | 🟡 P2 | Nuevo | `observability.py:202` |

---

## 2\. ITEMS POR FASE

### FASE 1 — Data Contract

| Item | Encontrado | Evidencia |
| :---- | :---- | :---- |
| Dual-names (\~55 refs) | **Sí — 57 refs** | `worker.py`. Patrones buscados: `followersCount`, `followsCount`, `postsCount`, `isBusinessAccount`, `userName`, `followerCount`, `followingCount`, `postCount`, `biographyText`. **Subió desde 55 en `ce148e1`** |
| `LegacyCompatReader` | **No existe** | Cero referencias en `observability.py` (318 líneas). Referenciado en `13a_data_contract_discovery.md` |
| `CONTRACT_VIOLATION` | **No se emite** | Definido en `observability.py:48` como valor del enum `RunEvent`. Sin ninguna invocación en el pipeline |
| `_normalize_user()` devuelve `None` | ✅ **Sí** | `hikerapi_client.py:823-825` — confirmado en auditorías previas, sin regresión |

**Estado FASE 1: \~30% cumplido.** El productor está limpio; los consumidores no. La convención legacy no solo persiste, creció en dos referencias.

### FASE 2 — Fail Loudly

| Item | Encontrado | Evidencia |
| :---- | :---- | :---- |
| `except Exception` en hot path | **29 en `worker.py`** | Conteo global del archivo (2.385 líneas) |
| Cadenas `or 0` restantes | **16** | Trayectoria: 33 → 21 → 16\. Baja de forma sostenida |
| **Funnel Invariant computado** | ✅ **Sí** | `worker.py:1823` — computado, no afirmado |
| **`FunnelTracker` usado** | ⚠️ **Parcial — 3 de 6 stages** | `funnel.enriched` (`:1206`), `funnel.scored` (`:1707`), `funnel.delivered` (`:1819`). Faltan `discovered`, `deduped`, `prefiltered` |
| `determine_final_status()` invocado | ✅ **Sí** | `worker.py:1832` con `funnel_invariant_ok=funnel_ok` y `budget_aborted=budget_aborted` |
| `budget_aborted` seteado | ✅ **Sí** | `worker.py:1982`, evaluado en `:2025` |
| `flush_drop_ledger()` | ✅ **Sí** | `worker.py:1977` |

**Estado FASE 2: \~75% cumplido.** El esqueleto de observabilidad funciona. Lo que falta es que el embudo reporte la verdad completa (H-1).

### FASE 3 — Mastery Path

| Item | Encontrado | Evidencia |
| :---- | :---- | :---- |
| Política de frescura | **No implementada** | Sin `FRESHNESS_*` ni equivalente en `config.py` (108 líneas) |
| `enriched_at` leído | **No** | Escrito en `discovery.py:694`. Sin ninguna consulta que lo use para gating |
| `is_discoverable` | **Muerta** | Escrito en `discovery.py:925`. Sin lectura en el codebase |
| `discovery_query` poblado | ⚠️ **Capturado, no propagado** | Worker lo escribe como `_discovery_query` en 12 sitios (`:397, 540, 561, 576, 593, 605, 620, 636, 660, 773, 804, 860`). El endpoint lee `discovery_query` sin guion bajo (`discovery.py:906, 927`) → **ver H-2** |
| Métricas carry-through | ✅ **Sí** | `discovery.py:973` (`followers`), `:976` (`raw_payload`), `:971` (`social_account_id`) |
| Tier 9 sub-tiers | ✅ **Sí** | `_derive_tier()` — verificado en auditoría del 25-08 |
| UPSERT social\_accounts \+ snapshot | ✅ **Sí** | `discovery.py:978` — `on_conflict` sobre la tripleta |

**Estado FASE 3: \~55% cumplido.** El camino a la tabla maestra funciona salvo por la trazabilidad de query (H-2) y la frescura.

### FASE 4 — AI / Discovery

| Item | Encontrado | Evidencia |
| :---- | :---- | :---- |
| `brief_parser` `response_format` | ✅ **Tiene** | `:191` y `:361` — ambos call sites |
| `profile_generator` `response_format` | ✅ **Tiene (indirecto)** | `:502` usa `deepseek_client.complete_json()`, que aplica `response_format` en `deepseek_client.py:167` |
| `candidate_analyzer` `response_format` | ✅ **Tiene** | `:326` |
| `_extract_json` regex | **Existe y se usa** | `brief_parser.py:205-206` (definición), `:309` (invocación). Regex de rescate también en `deepseek_client.py:158` |
| DeepSeek thinking disabled | ✅ **Sí** | `deepseek_client.py:64-66` |
| `DEEPSEEK_MODEL` | ✅ `deepseek-v4-flash` | `config.py:55` |
| `api_costs` con columna `model` | **No verificado** | Fuera del alcance de esta pasada |

**Estado FASE 4: \~85% cumplido.** Los cuatro call sites de LLM están cubiertos. Queda limpiar el regex redundante.

### FASE 5 — Ensanche

| Item | Encontrado | Evidencia |
| :---- | :---- | :---- |
| Límites 6/4/6/3 | ✅ **Aplicados** | `config.py:96-99` — `HASHTAG_TOP=6`, `HASHTAG_RECENT=4`, `KEYWORD=6`, `TOP_SEARCH=3` |
| `MAX_HANDLES_TO_ENRICH` | ⚠️ **Cableado en el worker** | `worker.py:50`. No externalizado a `config.py` |
| `MAX_CALLS_PER_RUN` | 120 | `config.py:87` |

---

## 3\. PROPUESTA DE FIXES

### P0 — H-1 · `FunnelTracker` reporta ceros en media pipeline

**Archivo:** `apps/api/app/workers/worker.py`

**Problema:** `FunnelTracker` declara seis etapas (`observability.py:191-196`): `discovered`, `deduped`, `prefiltered`, `enriched`, `scored`, `delivered`. El worker solo asigna tres. Las otras tres quedan en `0`.

En consecuencia, `funnel.summary()` (`worker.py:1841`) emite un resumen que reporta `discovered=0` en una corrida que descubrió doscientos perfiles.

El invariante principal (`:1823`) **sí funciona** porque se computa aparte con sets locales — por eso esto no bloquea el E2E. Pero el resumen que se registra para auditoría dice algo distinto de lo que pasó, que es exactamente el patrón que el Hito 30 existe para eliminar.

**Fix propuesto:**

\# Tras el paso de descubrimiento, donde step1\_handles queda consolidado:

funnel.discovered \= len(step1\_handles\_raw)      \# antes de deduplicar

funnel.deduped    \= len(step1\_handles)          \# después de deduplicar

\# Tras el pre-filtro, antes de enriquecer:

funnel.prefiltered \= len(handles\_to\_enrich)

\# Ya existentes — sin cambios:

funnel.enriched  \= len(enriched\_profiles)   \# :1206

funnel.scored    \= len(scored)              \# :1707

funnel.delivered \= total                    \# :1819

**Rationale:** el instrumento tiene que reflejar el embudo completo o no sirve para diagnosticar dónde se pierden los perfiles. Con tres etapas en cero, una corrida que entregue cero candidatos no permite distinguir si el problema estuvo en el descubrimiento, en la deduplicación o en el pre-filtro — que es justamente la pregunta que el embudo debía responder. Los nombres de variable deben confirmarse contra el contexto real antes de aplicar.

---

### P0 — H-2 · `_discovery_query` nunca llega a la tabla maestra

**Archivo:** `apps/api/app/api/v1/discovery.py:906, 927`

**Problema:** la FASE 3.1 se aplicó a medias. El worker captura la query de origen correctamente en doce puntos, pero la escribe con guion bajo inicial:

worker.py:561   item\["\_discovery\_query"\] \= f"hashtag:{tag}"

worker.py:593   item\["\_discovery\_query"\] \= f"keyword:{kw}"

worker.py:620   item\["\_discovery\_query"\] \= f"topsearch:{kw}"

El endpoint de guardado lee el nombre sin guion bajo:

discovery.py:906   "discovery\_query": candidate.get("discovery\_query", ""),

discovery.py:927   "discovery\_query": candidate.get("discovery\_query", ""),

**Resultado:** `influencers.discovery_query` sigue guardándose vacío. El trabajo de captura está hecho y se pierde en el último salto.

**Fix propuesto:**

\# discovery.py:906 y :927 — leer ambas formas durante la transición

"discovery\_query": (

    candidate.get("discovery\_query")

    or candidate.get("\_discovery\_query")

    or ""

),

**Rationale:** el prefijo con guion bajo es convención de campo interno del worker, no de la fila persistida. Lo correcto a mediano plazo es que el worker escriba el nombre final al construir el candidato persistido, pero leer ambas formas desbloquea la trazabilidad hoy sin tocar los doce puntos de captura. Es la misma clase de mismatch productor/consumidor que causó la Regresión \#0 y el BUG \#1 — conviene tratarlo con la misma seriedad aunque su impacto sea menor.

---

### P1 — H-3 · Las referencias camelCase crecieron

**Archivo:** `apps/api/app/workers/worker.py`

**Problema:** 57 referencias a la convención del proveedor retirado. Trayectoria del conteo: 59 (`81db353`) → 55 (`ce148e1`) → **57 (`4f87a6b`)**. La FASE 1 no avanza; retrocedió dos.

**Fix propuesto:** no es un fix puntual sino una pasada de limpieza sobre los ocho sitios de construcción de diccionarios en los pasos de búsqueda (`worker.py:376-933`), eliminando la escritura dual y dejando solo snake\_case. Debe ir acompañado de una prueba de guardia que falle el build si reaparece:

def test\_no\_legacy\_camelcase\_in\_worker():

    src \= Path("apps/api/app/workers/worker.py").read\_text()

    legacy \= \["followersCount", "followsCount", "postsCount", "isBusinessAccount"\]

    found \= \[k for k in legacy if k in src\]

    assert not found, f"Convención legacy reintroducida: {found}"

**Rationale:** sin guardia automatizada el conteo va a seguir oscilando. Es la tercera iteración en que se reporta y la primera en que sube.

---

### P1 — H-4 · Política de frescura

**Archivos:** `packages/shared-core/shared_core/config.py`, `apps/api/app/api/v1/discovery.py`

**Problema:** `enriched_at` se escribe (`discovery.py:694`) y nunca se lee. No existe constante de ventana en config. Cada búsqueda que se solape con otra vuelve a pagar los mismos perfiles.

**Fix propuesto:**

\# config.py

DISCOVERY\_FRESHNESS\_HOURS: int \= 168      \# 7 días — decisión Q2 pendiente

\# Antes de enriquecer, en el worker:

cutoff \= datetime.now(UTC) \- timedelta(hours=settings.DISCOVERY\_FRESHNESS\_HOURS)

if influencer.get("enriched\_at") and influencer\["enriched\_at"\] \> cutoff:

    drop\_profile(handle, DropReason.SKIPPED\_FRESH, stage="enrich", ledger=drop\_ledger)

    continue

**Rationale:** es el único ítem pendiente con retorno económico directo. Requiere además apagar o elevar `CACHE_TTL_PROFILE = 86400` en `hikerapi_client.py:17`; con los dos mecanismos activos el perfil se vuelve a pagar al día siguiente y la ventana de siete días no tiene efecto real. **Bloqueado por decisión de negocio Q2** (ventana de 7, 14 o 30 días).

---

### P2 — H-7 · Regex redundante en `brief_parser`

**Archivo:** `packages/discovery/discovery/brief_parser.py:205-206, 309`

**Problema:** con `response_format={"type": "json_object"}` activo en ambos call sites, el `_extract_json()` con `re.search` quedó como rescate. Hoy es redundante; el riesgo es que enmascara violaciones de contrato — si el modelo devuelve JSON válido con forma inesperada, el regex recorta el primer bloque entre llaves y el parseo puede tener éxito sobre algo que no es la respuesta.

**Fix propuesto:**

try:

    data \= json.loads(raw)

except json.JSONDecodeError as e:

    logger.error(RunEvent.CONTRACT\_VIOLATION.value,

                 where="brief\_parser", error=str(e))

    raise

**Rationale:** cierra de paso H-11 — sería la primera emisión real de `CONTRACT_VIOLATION`, que hoy está definido y nunca se usa.

---

### P2 — H-8, H-9, H-12 · Deuda técnica

| Ítem | Fix |
| :---- | :---- |
| `is_discoverable` (H-8) | Decidir: eliminar la escritura en `discovery.py:925` o implementar la consulta que la use. No dejarla a medias |
| `MAX_HANDLES_TO_ENRICH` (H-9) | Externalizar a `config.py` como los cuatro límites de búsqueda ya externalizados. Requiere decisión Q4 sobre subir de 25 |
| `assert_invariant()` (H-12) | `observability.py:202` está definido y nunca se invoca. Usarlo por etapa dentro del worker, o eliminarlo. Es código muerto del mismo tipo que `can_make_call()` |

---

## 4\. VEREDICTO FINAL

### 4.1 ¿Cuántos ítems de FASE 1-4 están resueltos?

| Fase | Resueltos | Pendientes | % |
| :---- | :---- | :---- | :---- |
| FASE 1 — Data Contract | 1 de 4 | 3 | **\~30%** |
| FASE 2 — Fail Loudly | 5 de 7 | 2 | **\~75%** |
| FASE 3 — Mastery Path | 4 de 7 | 3 | **\~55%** |
| FASE 4 — AI / Discovery | 6 de 7 | 1 | **\~85%** |
| **Total** | **16 de 25** | **9** | **\~64%** |

### 4.2 ¿Hay bugs nuevos?

**Sí, dos — ambos P0, ninguno bloqueante:**

- **H-1** — `FunnelTracker` con la mitad del embudo sin poblar. No estaba en ninguna auditoría previa. El invariante funciona porque se computa por otra vía, pero el resumen registrado es engañoso.  
- **H-2** — el mismatch `_discovery_query` / `discovery_query`. Es consecuencia directa de la FASE 3.1 aplicada en la iteración anterior: se resolvió la captura y no la propagación.

Ambos comparten la firma del proyecto: **un extremo de la cadena corregido y el otro no.** Es el cuarto caso documentado de esta misma clase — Regresión \#0, BUG \#1, C-1 frontend, y ahora H-2.

### 4.3 ¿El E2E del lunes está en riesgo?

**No.** Ningún hallazgo bloquea la corrida:

- El invariante del embudo se computa correctamente y `INCONSISTENT` es alcanzable  
- `flush_drop_ledger()` persiste el libro de descartes  
- `determine_final_status()` recibe los tres parámetros reales  
- `thinking` está desactivado, con lo que el costo del modelo no se dispara  
- Los cuatro call sites de LLM tienen salida estructurada garantizada

**H-1 degrada el diagnóstico, no el resultado.** Si la corrida entrega candidatos, se verá. Si entrega cero, el libro de descartes lo explicará por causa aunque el `summary` reporte ceros en tres etapas.

**Recomendación:** aplicar H-1 antes del lunes si hay margen — son tres asignaciones y mejora sustancialmente la calidad del diagnóstico de la corrida que se va a pagar. Si no hay margen, la corrida es válida igual.

### 4.4 Orden de prioridad

| \# | Fix | Prioridad | Costo | Bloquea E2E |
| :---- | :---- | :---- | :---- | :---- |
| 1 | H-1 · Poblar las 3 etapas faltantes del embudo | P0 | $0 | No, pero mejora el diagnóstico |
| 2 | H-2 · Leer `_discovery_query` en el endpoint | P0 | $0 | No |
| — | **Corrida E2E** | — | **\~$1,14** | — |
| 3 | H-4 · Política de frescura | P1 | $0 | Bloqueada por Q2 |
| 4 | H-3 · Limpieza camelCase \+ prueba de guardia | P1 | $0 | No |
| 5 | H-5, H-6 · `or 0` y `except Exception` | P1 | $0 | No |
| 6 | H-7 · Regex redundante \+ emitir `CONTRACT_VIOLATION` | P2 | $0 | No |
| 7 | H-8, H-9, H-12 · Deuda técnica | P2 | $0 | No |

---

## 5\. LO QUE NO SE VERIFICÓ EN ESTA PASADA

Para constancia de los límites de esta auditoría:

- `POLL_TERMINAL_STATUSES` en el frontend — fix crítico \#5 del prompt  
- `api_costs` con columna `model`  
- Distribución de los 29 `except Exception` entre hot path y resto  
- Los ocho sitios de dual-write, uno por uno — solo se midió el conteo agregado  
- `apply_migrations.py` y el estado de las migraciones en producción

---

## 6\. PENDIENTE ARRASTRADO — quinta iteración sin respuesta

⚡ **`TIER_MIN_FOLLOWERS = 5_000` · `worker.py:54`**

No aparece en Lanz v2.1, ni en la auditoría exhaustiva M3, ni en los 23 hallazgos de la v2, ni en las 23 entradas del índice.

Si actúa como filtro duro y no como parámetro de reparto por tiers, el sistema excluye por diseño el tramo **NANO bajo (500–5K)**, que según la metodología propia de la agencia aporta entre el **80% y el 85% de las views** de una campaña.

De ser así, la corrida del lunes mediría un motor incapaz de encontrar el tipo de creador que sostiene las campañas de La Web, y ninguno de los 16 ítems resueltos cambiaría ese resultado.

**Se responde leyendo los usos de esa constante. Cuesta cero dólares y cero riesgo.** Es la única pregunta abierta desde el 19-08 que nadie ha contestado.

---

*Auditoría elaborada sobre el commit `4f87a6b` del repositorio `lawebcore`. Todas las referencias son a archivo y línea verificables en ese commit. Ningún archivo del repositorio fue modificado.*

*Documento generado por La Web Figital Agency · 29-08-26 · Uso interno*  
