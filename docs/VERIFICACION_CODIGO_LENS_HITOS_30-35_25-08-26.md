# VERIFICACIÓN CÓDIGO REAL vs. PLANES — LENS DISCOVERY

> **Commit auditado:** `18ae963` (25-08-26 20:33) — HEAD del repositorio
> **Commit de implementación:** `bd973c7` (25-08-26 19:33) — «fix(LENS): Hitos 30-35 foundation»
> **Repositorio:** `github.com/ungardev/lawebcore`
> **Método:** lectura directa del árbol vía API de GitHub, archivo por archivo y línea por línea
> **Restricción cumplida:** solo lectura. No se modificó ningún archivo del repositorio
> **Fuente de verdad:** el código. Donde un documento contradice al código, prevalece el código
> **Fecha:** 25-08-26
> **Dirección técnica:** Claude Fable 5 · Full Stack Engineer Senior

---

## FASE 1 — Verificación de hitos aplicados (30-35)

| Hito | Veredicto | Evidencia |
|---|---|---|
| 30.1 `bind_contextvars` | ✅ Confirmado | 1 ocurrencia en `worker.py` |
| 30.2 Enums | ✅ Confirmado | `observability.py:16 RunEvent`, `:51 DropReason`, `:72 RunStatus` |
| 30.3 `DropLedger` / `drop_profile` | ✅ Confirmado | `observability.py:85`, `:109` · 10 llamadas en `worker.py` |
| 30.5 Estados de corrida | ✅ Confirmado | `worker.py:1786-1788` usan `RunStatus.DELIVERED` / `RunStatus.DEGRADED` |
| 30.6 Migración 108 | ✅ Confirmado | `supabase/migrations/00000000000108_discovery_run_events.sql` presente |
| 30.8 Código muerto del fusible | ✅ Confirmado | `budget_fuse.py` pasa de 310 a 294 líneas. `can_make_call()` y `check_run_limit()` **eliminadas**. Solo queda `reserve_and_record` (:93) |
| 31.1 `None` en vez de `0` | ✅ Confirmado | `hikerapi_client.py:823-825` — `user.get("follower_count")` sin `or 0` |
| 31.2 Solo snake_case | ✅ Confirmado | Return :842-856 limpio. **0 referencias camelCase en todo el archivo** |
| 32.1 Métricas arrastradas | ✅ Confirmado | `discovery.py:873`, `:896`, `:917`, `:958` |
| 32.2 Deduplicación por handle | ✅ Confirmado | `select_one` :876-880 → UPDATE :884 / INSERT :902. Migración `00000000000109_influencers_unique_handle.sql` |
| **32.3 `_derive_tier()`** | ⚠️ **Desviación** | Ver D-1 |
| 32.4 Social accounts + snapshot | ✅ Confirmado | `discovery.py:941`, `:952` |
| 33.1 Constantes en config | ✅ Confirmado | `config.py:95-98` · slices en `worker.py:553,566,581,604` usan `settings.*` |
| **33.2 Ensanche** | ❌ **No aplicado** | Ver D-2 |
| 33.3 Metadata planned/executed | ✅ Confirmado | `worker.py:411-414` |
| 34.1 `response_format` | ✅ Confirmado | `candidate_analyzer.py:327` |
| **34.3 Sin `re.search`** | ⚠️ **Desviación** | Ver D-3 |
| 34.5 `deepseek-v4-flash` | ✅ Confirmado | `config.py:55` (actualizado a deepseek-v4-flash) |
| 35.2 Validación backend | ✅ Confirmado | `discovery.py:507-510` |

**Resumen: 16 confirmados, 2 desviaciones, 1 no aplicado.**

---

## FASE 2 — Regresión crítica #0

### Veredicto: **CONFIRMADA — y es más grave de lo que el plan describe**

#### Evidencia 1 — el merge lee camelCase de una fuente que ya no lo emite

```
worker.py:1204   for e in enriched_profiles:
worker.py:1205       handle = e.get("username", "")
worker.py:1206       if not handle or handle not in profiles:
worker.py:1207           continue
worker.py:1208       about_data = e.get("about")
worker.py:1209       profiles[handle].update({
worker.py:1210           "follower_count":    e.get("followersCount"),
worker.py:1211           "followersCount":    e.get("followersCount"),
worker.py:1212           "following_count":   e.get("followsCount"),
worker.py:1213           "followsCount":      e.get("followsCount"),
worker.py:1214           "posts_count":       e.get("postsCount"),
worker.py:1215           "postsCount":        e.get("postsCount"),
worker.py:1216           "is_business":       e.get("isBusinessAccount", False),
worker.py:1217           "isBusinessAccount": e.get("isBusinessAccount", False),
worker.py:1218           "is_verified":       ...
```

`enriched_profiles` proviene de `_normalize_user()`, que tras el Hito 31.2 emite **únicamente** `follower_count`, `following_count`, `posts_count`, `is_business`, `is_verified`. Las claves camelCase **no existen** en el diccionario `e`.

**Campos afectados: 4 lecturas fallidas que escriben 8 claves.** Más `is_verified` en :1218-1219.

**Valor exacto tras el merge:**
```
profiles[handle]["follower_count"]  = None      # para TODO perfil enriquecido
profiles[handle]["followersCount"]  = None
profiles[handle]["following_count"] = None
profiles[handle]["posts_count"]     = None
profiles[handle]["is_business"]     = False     # siempre, por el default
```

#### Evidencia 2 — el `None` se reconvierte a `0` doce líneas después

```
worker.py:1305   for handle, p in profiles.items():
worker.py:1306       followers = p.get("followersCount") if "followersCount" in p else p.get(...)
worker.py:1307       if followers is None:
worker.py:1308           followers = 0
worker.py:1309       if followers == 0:
worker.py:1310           untracked_no_followers += 1
```

La línea 1211 escribió la clave `"followersCount"` con valor `None`. Por lo tanto la condición `"followersCount" in p` evalúa a **True**, `p.get("followersCount")` devuelve `None`, y **la línea 1308 lo convierte en `0` otra vez**.

### Dictamen

El Hito 31.1 eliminó la fabricación de ceros en el cliente, y las líneas 1210 y 1308 la reintroducen íntegra en el worker. El sistema hoy hace exactamente lo que hacía antes del Hito 31 — descartar todo perfil enriquecido como si tuviera cero seguidores — con la única diferencia de que ahora lo etiqueta con más precisión. **El efecto neto sobre candidatos entregados es cero.**

Esto es precisamente la secuencia advertida en `PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md`, §2 hallazgo H-1: *«corregir únicamente `worker.py` no puede funcionar — la información ya se destruyó aguas arriba»*. Se ejecutó la mitad inversa: se corrigió el cliente y no el worker, y el resultado es el mismo empate. La lección se sostiene en las dos direcciones — **el contrato de datos solo sirve si productor y consumidor cambian en el mismo despliegue.**

### Respuesta a las dos preguntas planteadas

**¿`LegacyCompatReader` es la solución correcta o basta leer `e.get("follower_count")` directamente?**

→ **Leer directo.** `_normalize_user()` es el único productor de `enriched_profiles` y ya está garantizado en snake_case — verificado: cero referencias camelCase en `hikerapi_client.py`. Un lector de compatibilidad añadiría una capa que no protege de nada, perpetuaría la convención muerta y daría cobertura para no terminar la migración.

**¿El merge necesita traducir `followersCount` → `follower_count` o simplemente leer el campo correcto?**

→ **Leer el campo correcto y además dejar de escribir la clave camelCase.** Escribirla es lo que hace que `"followersCount" in p` sea True en la línea 1306 y desvía la lectura por la rama equivocada. Traducir sería tratar el síntoma.

---

### FIX #1 — `worker.py:1209-1219`

```python
        for e in enriched_profiles:
            handle = e.get("username", "")
            if not handle or handle not in profiles:
                continue
            about_data = e.get("about")
            # HITO 31.4: _normalize_user() emite solo snake_case desde el Hito 31.2.
            # Leer camelCase acá devolvía None para todos los perfiles enriquecidos
            # y anulaba por completo el efecto del Hito 31.1.
            profiles[handle].update({
                "follower_count":  e.get("follower_count"),
                "following_count": e.get("following_count"),
                "posts_count":     e.get("posts_count"),
                "is_business":     e.get("is_business", False),
                "is_verified":     e.get("is_verified", False),
                "_enriched":       True,          # marca de procedencia para el FIX #2
            })
```

> **Nota:** eliminar las cinco claves camelCase del `update()` es parte del fix, no es opcional. Mientras se sigan escribiendo, la línea 1306 entrará por la rama equivocada aunque el valor sea correcto.

**Archivo destino:** `apps/api/app/workers/worker.py` (~línea 1209)
**Prueba:** `apps/api/tests/test_hito31_4_merge_snake_case.py::test_enriched_merge_preserves_follower_count`
**Riesgo de regresión:** Bajo
**Orden de aplicación:** 1

---

### FIX #2 — `worker.py:1305-1310` (separación de contadores — Hito 30.7 pendiente)

```python
        for handle, p in profiles.items():
            followers = p.get("follower_count")          # None real, sin fallback
            was_enriched = p.get("_enriched", False)

            if followers is None:
                reason = (DropReason.ENRICHMENT_FAILED if was_enriched
                          else DropReason.MISSING_FOLLOWER_FIELD)
                drop_profile(handle, reason, stage="normalize", ledger=ledger)
                if is_explore_mode:
                    ...  # se conserva con puntaje aproximado
                    continue
                continue

            if followers == 0:
                drop_profile(handle, DropReason.BELOW_MIN_FOLLOWERS,
                             stage="prefilter", ledger=ledger,
                             detail={"followers": 0})
                continue
```

**Archivo destino:** `apps/api/app/workers/worker.py` (~línea 1305)
**Prueba:** `test_hito30_7_counters_split.py::test_missing_field_vs_enrichment_failed`
**Riesgo de regresión:** Bajo
**Orden de aplicación:** 2

**Consulta SQL de producción (post-deploy):**
```sql
SELECT reason_code, COUNT(*)
FROM discovery_run_events
WHERE run_id = :run_id AND event = 'profile.dropped'
GROUP BY reason_code
ORDER BY 2 DESC;
-- Antes del fix: MISSING_FOLLOWER_FIELD concentra ~100%
-- Después: debe aparecer una distribución real entre causas
```

---

## FASE 3 — Verificación de las tres brechas nuevas

### GAP #4 — `drop_profile()` no persiste en la base de datos

**Veredicto: CONFIRMADO**

```
observability.py:109   def drop_profile(              ← síncrona, no async
observability.py:110       username: str,
observability.py:111       reason: DropReason,
observability.py:112       stage: str,
observability.py:113       detail: dict[str, Any] | None = None,
observability.py:114       ledger: DropLedger | None = None,
observability.py:115   ) -> None:
observability.py:120       import structlog
observability.py:122       logger = structlog.get_logger()
observability.py:123       if ledger is not None:
observability.py:124           ledger.record(reason)
observability.py:125       logger.info(
observability.py:126           RunEvent.PROFILE_DROPPED.value,
observability.py:127           username=username,
observability.py:128           reason=reason.value,
observability.py:129           stage=stage,
observability.py:130           **(detail or {}),
observability.py:131       )
```

Cero referencias a `railway_pg` o `insert(` en las 265 líneas del archivo.

**Dictamen**

La migración 108 creó la tabla `discovery_run_events` y nadie escribe en ella. La consulta que debería responder «¿por qué esta corrida no entregó nada?» hoy devuelve cero filas. Toda la trazabilidad vive en la salida estándar de Railway, que rota. El Hito 30.6 está implementado a medias: existe el destino, no existe el camino.

**¿Dónde debería ir la instrucción INSERT?**

**No dentro de `drop_profile()`.** La función es síncrona y se invoca dentro del bucle caliente de perfiles; convertirla en `async` obligaría a un `await` por cada descarte — hasta 200 viajes de ida y vuelta a Postgres por corrida, sobre un pipeline que ya es lento. El diseño correcto es **acumular en el ledger y volcar una sola vez al cerrar la corrida.**

### FIX #3 — `observability.py`, agregar al final del archivo

```python
async def flush_drop_ledger(
    run_id: str,
    ledger: "DropLedger",
    railway_pg,
) -> int:
    """Vuelca el libro de descartes a discovery_run_events.

    Una sola escritura por corrida. Se llama al cerrar el run, nunca dentro
    del bucle de perfiles.
    """
    rows = [
        {
            "run_id": run_id,
            "event": RunEvent.PROFILE_DROPPED.value,
            "reason_code": reason.value if hasattr(reason, "value") else str(reason),
            "stage": ledger.stage_of(reason),
            "payload": {"count": count},
        }
        for reason, count in ledger.counts().items()
        if count > 0
    ]
    if not rows:
        return 0
    await railway_pg.insert(table="discovery_run_events", values=rows)
    return len(rows)
```

`DropLedger` necesita dos accesores si aún no los expone: `counts()` que devuelva el diccionario causa→conteo, y `stage_of(reason)` que devuelva la etapa asociada.

**Llamada — `worker.py`, junto al bloque de estado final (~línea 1786):**
```python
        await flush_drop_ledger(run_id, ledger, railway_pg)
```

**Archivo destino:** `packages/shared-core/shared_core/observability.py` (final) + `apps/api/app/workers/worker.py` (~1786)
**Prueba:** `test_hito30_6_ledger_persist.py::test_flush_writes_one_row_per_reason`
**Riesgo de regresión:** Bajo
**Orden de aplicación:** 3

**Consulta SQL de producción:**
```sql
SELECT COUNT(*) FROM discovery_run_events WHERE run_id = :run_id;
-- Debe ser > 0 tras la primera corrida con el fix aplicado
```

---

### GAP #5 — `influencer_metrics_snapshot` sin `social_account_id`

**Veredicto: CONFIRMADO**

```
discovery.py:952   await railway_pg.insert(
discovery.py:953       table="influencer_metrics_snapshot",
discovery.py:954       values={
discovery.py:955           "influencer_id": influencer_id,
discovery.py:956           "platform": "instagram",
discovery.py:957           "snapshot_date": datetime.now(timezone.utc).date(),
discovery.py:958           "follower_count": follower_count,
```

No existe `social_account_id` en el INSERT. Revisadas las 46 migraciones del directorio: no hay ninguna que declare unicidad sobre `(influencer_id, platform, snapshot_date)`. La única restricción añadida por los hitos es la 109, sobre `influencers.primary_handle`.

**¿Es posible tener múltiples filas del mismo `influencer_id` para la misma `snapshot_date`?**

**Sí.** Guardar el mismo candidato dos veces el mismo día produce dos instantáneas idénticas. Esto rompe la política de frescura del Hito 32.5: la consulta `ORDER BY snapshot_date DESC LIMIT 1` es no determinista entre filas empatadas en fecha, y el conteo de instantáneas por influencer deja de ser una serie temporal utilizable.

### FIX #4 — nueva migración `00000000000110_metrics_snapshot_unique.sql`

```sql
ALTER TABLE influencer_metrics_snapshot
  ADD COLUMN IF NOT EXISTS social_account_id UUID
  REFERENCES influencer_social_accounts(id) ON DELETE CASCADE;

-- Deduplicar antes de imponer la restricción
DELETE FROM influencer_metrics_snapshot a
USING influencer_metrics_snapshot b
WHERE a.ctid < b.ctid
  AND a.influencer_id = b.influencer_id
  AND a.platform      = b.platform
  AND a.snapshot_date = b.snapshot_date;

CREATE UNIQUE INDEX IF NOT EXISTS uq_metrics_snapshot_day
  ON influencer_metrics_snapshot (influencer_id, platform, snapshot_date);
```

**`discovery.py:952` — reemplazar el INSERT:**
```python
    await railway_pg.insert(
        table="influencer_metrics_snapshot",
        values={
            "influencer_id": influencer_id,
            "social_account_id": social_account_id,   # ← proviene del FIX #5
            "platform": "instagram",
            "snapshot_date": datetime.now(timezone.utc).date(),
            "follower_count": follower_count,
            "engagement_rate": candidate.get("engagement_rate"),
            "avg_likes": candidate.get("avg_likes"),
            "raw_data": candidate.get("raw_data", {}),
        },
        on_conflict="influencer_id,platform,snapshot_date",
    )
```

**Archivo destino:** `supabase/migrations/` (nuevo) + `apps/api/app/api/v1/discovery.py` (~952)
**Prueba:** `test_hito32_5_snapshot_unique.py::test_same_day_save_twice_yields_one_row`
**Riesgo de regresión:** Medio — el `DELETE` toca datos existentes. Ejecutar primero la consulta de verificación
**Orden de aplicación:** 5

**Consulta SQL de producción (antes y después):**
```sql
SELECT influencer_id, snapshot_date, COUNT(*)
FROM influencer_metrics_snapshot
GROUP BY 1, 2
HAVING COUNT(*) > 1;
-- Antes: puede devolver filas. Después: debe devolver cero
```

---

### GAP #6 — `influencer_social_accounts` sin restricción UNIQUE ni UPSERT

**Veredicto: CONFIRMADO**

```
discovery.py:941   await railway_pg.insert(
discovery.py:942       table="influencer_social_accounts",
discovery.py:943       values={
discovery.py:944           "influencer_id": influencer_id,
discovery.py:945           "platform": "instagram",
discovery.py:946           "handle": handle,
discovery.py:947           "url": f"https://instagram.com/{handle}" if handle else None,
discovery.py:948           "is_primary": True,
discovery.py:949       },
discovery.py:950   )
```

INSERT puro, sin `on_conflict`. Sin restricción de unicidad en ninguna de las 46 migraciones.

**¿Qué sucede si un analista guarda un candidato, lo descarta y lo vuelve a guardar?**

El bloque de deduplicación de influencers (`:876-880`) **sí** detecta el handle existente y ejecuta un UPDATE en vez de un INSERT — el Hito 32.2 funciona. Pero la inserción de la cuenta social corre **incondicionalmente después**, en las dos ramas del `if existing`. Resultado: **una fila nueva de `influencer_social_accounts` en cada guardado**, todas marcadas `is_primary = True`. Tres guardados producen tres cuentas primarias para el mismo influencer, y cualquier consulta que asuma una sola cuenta primaria devuelve resultados no determinísticos.

### FIX #5 — nueva migración `00000000000111_social_accounts_unique.sql`

```sql
DELETE FROM influencer_social_accounts a
USING influencer_social_accounts b
WHERE a.ctid < b.ctid
  AND a.influencer_id = b.influencer_id
  AND a.platform      = b.platform
  AND lower(a.handle) = lower(b.handle);

CREATE UNIQUE INDEX IF NOT EXISTS uq_social_account_identity
  ON influencer_social_accounts (influencer_id, platform, lower(handle));
```

**`discovery.py:941` — reemplazar el INSERT:**
```python
    social_account = await railway_pg.insert(
        table="influencer_social_accounts",
        values={
            "influencer_id": influencer_id,
            "platform": "instagram",
            "handle": handle,
            "url": f"https://instagram.com/{handle}" if handle else None,
            "is_primary": True,
        },
        on_conflict="influencer_id,platform,handle",
        returning="representation",
    )
    social_account_id = social_account["id"] if social_account else None
```

**Archivo destino:** `supabase/migrations/` (nuevo) + `apps/api/app/api/v1/discovery.py` (~941)
**Prueba:** `test_hito32_4_social_account_upsert.py::test_save_twice_yields_one_account`
**Riesgo de regresión:** Medio — mismo `DELETE` previo
**Orden de aplicación:** 4

**Consulta SQL de producción:**
```sql
SELECT influencer_id, platform, handle, COUNT(*)
FROM influencer_social_accounts
GROUP BY 1, 2, 3
HAVING COUNT(*) > 1;
-- Antes: puede devolver filas. Después: debe devolver cero
```

---

## DESVIACIONES

### D-1 · `_derive_tier()` usa 4 tramos, no los 9 sub-tiers de LWFA

**Veredicto: Desviación**

```
discovery.py:844   def _derive_tier(followers: int | None) -> str:
discovery.py:845       """Deriva el tier desde follower_count.
discovery.py:847       Alineado con classify_tier() en geo_boost.py:122-130.
discovery.py:848       4 tramos: NANO (<10k), MICRO (10k-100k), MID (100k-500k), MACRO"""
discovery.py:850       if followers is None:
discovery.py:851           return "NANO"          ← default silencioso
discovery.py:852       if followers < 10_000:  return "NANO"
discovery.py:854       if followers < 100_000: return "MICRO"
discovery.py:856       if followers < 500_000: return "MID"
discovery.py:858       return "MACRO"
```

**Dictamen**

Dos problemas distintos. El primero es el que ya se señaló en `PLAN_DESARROLLO_LENS_HITOS_30-35`, §1.3: la metodología de la agencia (`14_influencer_lens_manual_filtros_ia.md`, §2.1) exige la escala granular de nueve sub-tiers para discovery y scoring, reservando la escala genérica para pricing y reportes evolutivos. Con cuatro tramos, el score de engagement de cada candidato se compara contra un benchmark que no corresponde a su sub-tier real.

El segundo nadie lo señaló y es más grave en términos del propio Hito 30: `followers is None → "NANO"`. Un perfil sin dato de seguidores se clasifica como NANO. Es exactamente el patrón «ante un error, producir un valor plausible y continuar» que todo el Hito 30 existe para erradicar, reintroducido dentro del hito que debía cerrarlo.

### FIX #6 — `discovery.py:844`

```python
def _derive_tier(followers: int | None) -> str | None:
    """Sub-tier LWFA de 9 tramos. Devuelve None si no hay dato — nunca un default.

    Fuente: 14_influencer_lens_manual_filtros_ia.md §2.1 (escala de discovery).
    NO usar la escala genérica de 5 tramos: esa es para pricing y reportes.
    """
    if followers is None:
        return None                       # el llamador decide; no se inventa tier
    if followers <     5_000: return "NANO_BAJO"
    if followers <    10_000: return "NANO_ALTO"
    if followers <    30_000: return "MICRO_BAJO"
    if followers <    60_000: return "MICRO_MEDIO"
    if followers <   100_000: return "MICRO_ALTO"
    if followers <   250_000: return "MID_BAJO"
    if followers <   500_000: return "MID_ALTO"
    if followers <   750_000: return "MACRO_BAJO"
    if followers < 1_000_000: return "MACRO_ALTO"
    return "MEGA"
```

Requiere una migración adicional si `influencers.primary_tier` tiene una restricción CHECK con los cuatro valores antiguos. Verificar antes de aplicar.

**Archivo destino:** `apps/api/app/api/v1/discovery.py` (~844)
**Prueba:** `test_hito32_3_tier_9_tramos.py::test_derive_tier_returns_subtier` y `::test_none_followers_returns_none`
**Riesgo de regresión:** Medio — hay datos existentes clasificados en cuatro tramos
**Orden de aplicación:** 6

---

### D-2 · Hito 33.2 no se aplicó — el techo de calidad sigue puesto

**Veredicto: No aplicado**

```
config.py:95   DISCOVERY_HASHTAG_TOP_LIMIT: int = 3
config.py:96   DISCOVERY_HASHTAG_RECENT_LIMIT: int = 2
config.py:97   DISCOVERY_KEYWORD_LIMIT: int = 3
config.py:98   DISCOVERY_TOP_SEARCH_LIMIT: int = 1
```

**Dictamen**

La externalización (33.1) se ejecutó correctamente: las constantes salieron del worker y los slices leen `settings.*`. El ensanche (33.2) no. Los valores son **idénticos** a las constantes cableadas que Lanz documentó en `worker.py:534, 547, 562, 585` del commit `81db353`.

La búsqueda sigue explorando **3 hashtags y 3 palabras clave de un plan de 30 y 20**, y siguen quedando aproximadamente 88 llamadas sin usar dentro del tope de 120 ya configurado.

Este es el único punto de toda la lista que **sube el techo de calidad** (Lanz §7.4: *«ningún ajuste de puntaje rescata a un influencer que nunca entró al conjunto»*). Mientras siga en 3/2/3/1, ningún otro fix cambia qué influencers entran al conjunto — solo cambian cómo se ordenan y se etiquetan los mismos de siempre.

### FIX #7 — variables de entorno en Railway, sin tocar código

```
DISCOVERY_HASHTAG_TOP_LIMIT=5
DISCOVERY_HASHTAG_RECENT_LIMIT=3
DISCOVERY_KEYWORD_LIMIT=5
DISCOVERY_TOP_SEARCH_LIMIT=2
```

**Costo:** el ensanche conservador lleva la corrida de $1,14 a $1,58. Con saldo de $43,00, las corridas disponibles pasan de **37 a 27**.

**Requiere aprobación de presupuesto.** No es una decisión de ingeniería.

**Orden de aplicación:** 8 — después de validar los fixes 1 a 6, para que la corrida de medición del ensanche se compare contra un pipeline que ya funciona

---

### D-3 · `re.search` sigue presente en `_parse_batch_response`

**Veredicto: Desviación**

```
candidate_analyzer.py:182   def _parse_batch_response(content: str) -> list[dict[str, Any]]:
candidate_analyzer.py:183       """Parse LLM response as JSON. Uses response_format=json_object from the caller."""
candidate_analyzer.py:186       match = re.search(r"\{[\s\S]*\}", content, re.DOTALL)
candidate_analyzer.py:189       data = _json.loads(match.group())
```

**Dictamen**

El docstring de la línea 183 afirma que la función se apoya en `response_format`, y el `response_format` sí está configurado (`:327`), pero la extracción por expresión regular quedó en el código. Hoy es redundante; el riesgo real es que **enmascara violaciones de contrato**: si el modelo devuelve JSON válido con una forma inesperada, la regex recorta el primer bloque entre llaves y `json.loads` puede tener éxito sobre algo que no es la respuesta esperada. El fallo se degrada en silencio hacia `_fallback_scores()` en lugar de reportarse.

### FIX #8 — `candidate_analyzer.py:182-190`

```python
def _parse_batch_response(content: str) -> list[dict[str, Any]]:
    """response_format=json_object garantiza JSON válido. Sin regex de rescate."""
    try:
        data = _json.loads(content)
    except _json.JSONDecodeError as e:
        logger.error(
            RunEvent.CONTRACT_VIOLATION.value,
            where="candidate_analyzer._parse_batch_response",
            error=str(e),
        )
        raise
```

**Archivo destino:** `packages/discovery/discovery/candidate_analyzer.py` (~182)
**Prueba:** `test_hito34_3_no_regex_parse.py::test_malformed_json_raises_not_silently_falls_back`
**Riesgo de regresión:** Bajo
**Orden de aplicación:** 7

---

## GAPS ADICIONALES — señalados por Lanz, no atendidos por las soluciones actuales

| # | Hallazgo | Evidencia | Prioridad |
|---|---|---|---|
| **A-1** | **El Hito 31.4 no se aplicó a `worker.py`.** Lanz §2.2 documenta el contrato de nombres duales como causa del hallazgo central del informe | `worker.py` mantiene **59 referencias camelCase**: líneas 384-391, 525-531, 742-748, 773-779, 827-833, 856-862, 885-891, 915-921, 967-969, 1011, 1210-1217, 1306, 1528, 1564-1565, 2001-2014, 2063. Son **exactamente las mismas 59 del commit `81db353`**, antes de los hitos | 🔴 Alta |
| **A-2** | **21 cadenas `or 0` sobreviven** en `worker.py` (eran 33 antes de los hitos). La regla NULL ≠ 0 del contrato se aplicó a un tercio del archivo | Conteo automático sobre `18ae963` | 🔴 Alta |
| **A-3** | **El invariante del embudo no opera.** `FunnelTracker` está definido (`observability.py:134`) e `InconsistentFunnelError` también (`:172`), pero solo hay 2 referencias en `worker.py` | Sin invariante activo, el estado `inconsistent` nunca se dispara y la propiedad autoauditable del Hito 30 — la que impide que vuelvan a desaparecer perfiles sin rastro — no existe | 🟠 Media |
| **A-4** | **`untracked_no_followers` sigue siendo un contador único** (`worker.py:1310`). El Hito 30.7 pedía separarlo en dos causas | Es el defecto exacto que Lanz documenta en §2.4: un solo contador cubriendo dos causas distintas, y un mensaje que siempre elige la misma | 🔴 Alta — se resuelve con el FIX #2 |
| **A-5** | **`TIER_MIN_FOLLOWERS = 5_000` sin resolver.** Hallazgo H-2 del plan de desarrollo. Si es filtro duro, excluye el tramo NANO bajo (500–5K), que según la metodología de la agencia aporta el 80–85% de las views de una campaña | `worker.py:54-55` | 🔴 Alta — se resuelve leyendo el código, costo $0 |
| **A-6** | **El caché de perfil sigue en 24 horas** (`hikerapi_client.py:17`, `CACHE_TTL_PROFILE = 86400`). El Hito 32.5 pedía sustituirlo por la política de frescura de 7 días. Con ambos mecanismos activos se sigue re-pagando el perfil al día siguiente | Lanz §4: *«un activo que se paga y no se conserva»* | 🟠 Media |

**A-1 y A-2 son la Regresión #0 en su forma general.** El Hito 31 se aplicó al productor (`hikerapi_client.py`) y no a los consumidores. La Regresión #0 es la manifestación que rompe el pipeline hoy; las otras 55 referencias camelCase son deuda latente que va a romper lo siguiente que se toque en ese archivo.

---

## FASE 5 — Decisiones de negocio pendientes

| Tema | ¿Información suficiente en el repositorio? | Detalle |
|---|---|---|
| **Handles Nestlé / Purina** | ⚠️ **Parcial** | Existe `supabase/migrations/00000000000102_replace_purina_discovery_profile.sql` — hay un perfil de descubrimiento de Purina versionado en migraciones. **No se verificó su contenido en esta auditoría.** Lo que sí es concluyente: **no existe tabla de exclusión por marca en ninguna de las 46 migraciones.** El Hito 32.6 (excluir la cuenta del cliente del brief, ficha L-05) **no se implementó**, por lo que `@dogchowve` seguiría apareciendo como candidato válido en una búsqueda para Purina Dog Chow |
| **Escala de tiers** | ✅ **Suficiente para diagnosticar, requiere decisión tuya** | `discovery.py:847` declara explícitamente alineación con `classify_tier()` en `geo_boost.py:122-130`, con **4 tramos**. No hay ninguna referencia a la escala de 9 sub-tiers en el repositorio. La escala granular de la agencia vive únicamente en `14_influencer_lens_manual_filtros_ia.md`, que está fuera del repositorio. **La decisión es de producto, no de código:** si la escala de 9 tramos es la norma, hay que llevarla al repositorio como fuente única |
| **Política de retención de datos** | ❌ **Requiere input externo** | Sin política documentada en migraciones, esquemas ni configuración. Los únicos vencimientos presentes son los TTL de Redis (`hikerapi_client.py:16-18`), que son caché de llamadas, no retención de datos de influencers. No hay borrado lógico programado ni ventana de conservación declarada |
| **Ventana de frescura de 7 días** | ❌ **Requiere input externo** | El valor no aparece en `config.py` — no es configurable. Si distintas marcas necesitan frescura distinta (una campaña activa exige datos del día; un scouting exploratorio tolera 30 días), hay que promoverlo a `DISCOVERY_FRESHNESS_DAYS` con posibilidad de sobrescritura por marca. **Es decisión de producto y afecta directamente el costo por búsqueda** |

---

## ORDEN DE APLICACIÓN CONSOLIDADO

| # | Fix | Archivo | Riesgo | Consumo de saldo |
|---|---|---|---|---|
| 1 | Merge en snake_case | `worker.py:1209-1219` | Bajo | $0 |
| 2 | Contadores separados, sin `followers = 0` | `worker.py:1305-1310` | Bajo | $0 |
| 3 | Persistir el libro de descartes | `observability.py` + `worker.py:~1786` | Bajo | $0 |
| 4 | UPSERT en social accounts | migración 111 + `discovery.py:941` | Medio | $0 |
| 5 | `social_account_id` + unicidad de snapshot | migración 110 + `discovery.py:952` | Medio | $0 |
| 6 | `_derive_tier` a 9 tramos | `discovery.py:844` | Medio | $0 |
| 7 | Quitar `re.search` | `candidate_analyzer.py:186` | Bajo | $0 |
| — | **Corrida de validación end-to-end** | — | — | **~$1,14** |
| 8 | Ensanche 5/3/5/2 | variables de entorno en Railway | Bajo | **+$0,44 por corrida** |

**Los siete primeros fixes cuestan $0 y se validan con una sola corrida.** Sin el fix #1, ninguno de los demás es medible: el pipeline seguiría descartando el 100% de los perfiles enriquecidos y cualquier mejora quedaría enmascarada.

---

## RECOMENDACIÓN OPERATIVA

⚡ **Antes de tocar una línea de código:** resolver A-5 leyendo los usos de `TIER_MIN_FOLLOWERS` en `worker.py`. Si resulta ser un filtro duro y no un parámetro de reparto por tiers, los ocho fixes de esta lista no cambian el resultado del producto, y esa es la conversación que hay que tener primero. Es una lectura de código, cuesta cero dólares y cero riesgo.

**Después:** aplicar los fixes 1 y 2 juntos, en un solo despliegue. Son el mismo defecto en dos puntos del mismo archivo y separarlos deja el pipeline en un estado intermedio inconsistente.

**Criterio de éxito de la primera corrida post-fix:** que `discovery_run_events` devuelva una distribución de causas de descarte con más de un código representado. Si sigue devolviendo `MISSING_FOLLOWER_FIELD` cerca del 100%, el problema no era el merge y hay que volver al enriquecimiento.

---

*Verificación elaborada sobre el commit `18ae963` del repositorio `lawebcore`. Todas las referencias son a archivo y línea verificables en ese commit. Ningún archivo del repositorio fue modificado durante esta auditoría.*

*Documento generado por La Web Figital Agency · 25-08-26 · Uso interno*
