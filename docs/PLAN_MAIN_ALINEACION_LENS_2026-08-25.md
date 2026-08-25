# PLAN MAIN — Alineación LENS Discovery
## Basado en el Informe de Santiago Lanz (v1.2, 24-ago-2026)

> **Para:** Claude Code Fable 5
> **De:** MiniMax M2.7/M3 (modelo agente de programación) + contexto completo del repositorio
> **Fecha:** 25 de agosto de 2026
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Commit base:** `81db353` (Hito 29 hotfix — extra='forbid' solo en frontera de entrada)
> **HikerAPI balance:** $43.00 USD
> **Documentos de referencia:**
> - `docs/La Web Figital - Informe de Alineación Técnica LENS.md` (Santiago Lanz, v1.2)
> - `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` (índice histórico de auditorías)
> - `docs/ARQUITECTURA_LENS.md` v5.5 (arquitectura actual del sistema)
> - `docs/LENS_ASESORIA_INGENIERO_2026-08-20.md` (contexto de ingeniería)

---

## Resumen Ejecutivo

El informe de Santiago Lanz **no invalida** los 29 hitos previos del equipo. Los **contextualiza y prioriza**.

El equipo construyó correctamente 28 hitos. Lo que falta no es más código: es **estándar y veracidad del sistema**. Lanz identifica **3 decisiones de arquitectura** que hacen que el sistema no pueda decir la verdad sobre sí mismo, y **4 prácticas que ya existen en el repo** pero solo aplican al subsistema P.I.A.R.

**Decisión adoptada:** Plan secuencial siguiendo Lanz §7: **Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5**.

**Importante:** El trabajo previo del equipo (Hitos 1-29) está correcto. No se deshace nada. Se construye sobre lo existente.

---

## Contexto: Qué Es LENS y Por Qué Estamos Aquí

**LENS Discovery** es el sistema de descubrimiento de influencers de La Web Figital Agency. Permite describir un brief en lenguaje natural y recibir los mejores perfiles de Instagram verificados con scoring propietario.

**Estado actual:**
- 48 ejecuciones históricas, 1 candidato producido
- $43.00 USD de saldo disponible (recargado 2026-08-20)
- Pipeline funcionando en Railway (deploy `81db97` del 21-ago)
- Hito 29 hotfix aplicado (regresión extra='forbid' corregida)

**Por qué 1 candidato en 48 runs:**
- Lanz §2 identifica la cadena: perfiles llegan con `followers=0` → se descartan silenciosamente
- El enriquecimiento es la única fuente de followers, pero las búsquedas devuelven perfiles reducidos
- El sistema no distingue "no traje el dato" de "el enriquecimiento falló"
- El instrumento de medición informa éxito en ambos casos

---

## Las 3 Decisiones de Arquitectura Identificadas por Lanz

### Arquitectura 1: "Ante un error, producir un valor plausible y continuar"

179 manejadores `except Exception` amplios en el repositorio. 33 cadenas `or 0` en worker.py. Cada una convierte "no sé" en un número que el sistema toma por verdadero.

**4 casos verificados a mano:**

| Ubicación | Qué hace | Consecuencia |
|-----------|----------|--------------|
| `embeddings.py:46-58` | Vector de 384 ceros | Fragmento indexing como bueno, nunca hallable |
| `candidate_analyzer.py:348-382` | `_fallback_scores()` | Puntajes iguales a los de IA real, sin `ai_summary` |
| `worker.py:1280+` | `followers=0` → descarte | Perfil bueno pero incompleto → descartado sin rastro |
| `budget_fuse.py:213-222` | `can_make_call()` → `True` en error | **Y NADIE LA LLAMA** — código muerto |

### Arquitectura 2: "Se compra dos veces lo que ya se tiene"

- Cache vence en 24h → dato pagado se pierde
- Tabla `influencers` existe pero solo recibe nombre y bio (sin followers, engagement, avg_likes)
- `primary_tier` hardcoded "MICRO"
- Sin deduplicación por handle (el ETL del otro subsistema sí la hace)
- PITR de la DB puede no estar activado

### Arquitectura 3: "Se busca en tres lugares, y la semántica no se usa"

- Plan arma 30 hashtags + 20 keywords
- **Se ejecutan 3 hashtags + 3 keywords** (las demás nunca se consultan)
- Quedan ~88 llamadas sin usar por corrida dentro del tope de 120
- Metadata registra 30 y 20 → miente sobre lo que ejecutó
- La búsqueda semántica (embeddings + pgvector) existe en el repo pero LENS no la usa

---

## Las 4 Prácticas que Ya Existen en el Repo

| Práctica | Dónde | Aplica a LENS? |
|----------|-------|----------------|
| **Contrato de datos formal** | `13_data_contract_hub.md` v1.0 | ❌ No — solo a P.I.A.R. |
| **ETL con normalización** | `scripts/etl_drive.py`, `etl_excel.py`, `etl_ism_backfill.py` | ❌ No — solo a P.I.A.R. |
| **Infraestructura de cron jobs** | `worker.py:2238-2241` | ⚠️ Parcial — cron existe, tarea `sync_metricool_task` solo loguea |
| **Modelo de entidades completo** | migración `00005` (influencers + social_accounts + metrics_snapshot) | ❌ Parcial — LENS llena solo la ficha de contacto |

**Conclusión de Lanz:** "Este equipo sabe hacer las cuatro cosas que a LENS le faltan, y las tiene escritas y andando a pocos archivos de distancia."

---

## Verificaciones Pendientes (Lanz §8 — No Pudimos Verificar)

Antes de ejecutar código, necesitamos respuestas a estas 4 preguntas:

| # | Pregunta | Cómo verificar | Impacto |
|---|----------|---------------|---------|
| V1 | ¿Qué modelo de IA está configurado en Railway env vars? | Panel Railway → Variables | `deepseek-chat` fue discontinuado el 24-jul-2026 |
| V2 | ¿El alias `deepseek-chat` sigue resolviendo en producción? | `curl` al endpoint de account | Si no, todo el sistema de IA cae |
| V3 | ¿PITR activado en la DB de Railway? | Panel Railway → Postgres → Backups | Si no, pérdida total de datos si falla la DB |
| V4 | ¿Redis tiene política de eviction? | Panel Railway → Redis → Settings | Afecta contadores de gasto y cache de perfiles |

**Acción:** Crear `docs/LANZ_VERIFICACIONES_2026-08-25.md` con las respuestas antes de empezar Fase 1.

---

## FASE 0 — Verificaciones (30 min)

**Objetivo:** Responder las 4 preguntas de Lanz §8 antes de tocar código.

```bash
# V1 y V2: Verificar modelo configurado y si deepseek-chat sigue resolviendo
curl -s -H "x-access-key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/account | jq

# V3: Panel Railway → verificar PITR
# V4: Panel Railway → verificar Redis eviction policy
```

**Output:** `docs/LANZ_VERIFICACIONES_2026-08-25.md`

**Criterio de éxito:** Las 4 preguntas tienen respuesta documentada con evidencia.

---

## FASE 1 — Que el Sistema Pueda Fallar en Voz Alta (4-6 h)

> **Lanz §7 Punto 1 — Bloqueante de todo lo demás**
>
> "Mientras un error produzca un valor plausible, ninguna mejora es verificable."

### 1.1 Separar el contador `untracked_no_followers` en dos

**Problema:** Una sola variable cuenta tanto "el dato no vino" como "el enrichment falló". El mensaje solo puede nombrar una causa.

**Archivo:** `apps/api/app/workers/worker.py`

```python
# ACTUAL (líneas 1280-1282):
followers = p.get("followersCount") or p.get("follower_count") or 0
if followers == 0:
    untracked_no_followers += 1  # ← Un solo counter para dos causas

# PROPUESTO:
if profile_source == "reduced":
    untracked_missing_follower_field += 1  # Perfil vino sin followers
elif profile_source == "enriched" and followers == 0:
    untracked_enrichment_failed += 1  # Enrichment sí corrió pero falló
```

### 1.2 Estado final distingue "haber corrido" de "haber entregado"

**Problema:** `worker.py:1751` — ejecución con 0 candidatos queda en "completed".

```python
# ACTUAL:
final_status = "partial" if step3_degraded else "completed"

# PROPUESTO:
if total_candidates == 0 and not is_explore_mode:
    final_status = "failed"
    error_detail = "no_candidates_after_scoring"
elif total_candidates == 0 and is_explore_mode:
    final_status = "explored"  # Explorar puede ser vacío — es válido
elif step3_degraded:
    final_status = "partial"
else:
    final_status = "completed"
```

### 1.3 Mensaje dinámico según causa del fallo

**Problema:** El mensaje ancla a un run específico (`0c44ea23`) y solo nombra enriquecimiento.

```python
# PROPUESTO:
if untracked_missing_follower_field >= total_profiles * 0.8:
    return "⚠️ El 80% de perfiles llegó sin el campo de seguidores. " \
           "El proveedor devolvió datos incompletos. Esto NO es saldo insuficiente."
elif untracked_enrichment_failed >= total_profiles * 0.8:
    return "⚠️ El 80% de perfiles falló al enriquecer. " \
           "Probablemente saldo agotado. Recargar y reintentar."
else:
    return "⚠️ No se encontraron candidatos. Revisar el brief o intentar otro nicho."
```

### 1.4 Eliminar o activar `can_make_call()` (código muerto)

**Archivo:** `apps/api/app/core/budget_fuse.py:213-222`

**Hallazgo crítico:** `can_make_call()` retorna `True` ante error Y NADIE la invoca. `MAX_CALLS_PER_RUN` nunca se aplica en producción.

**Decisión:** **Eliminar** la función. `reserve_and_record()` (línea 241) ya fail-closed y sí corre. No tiene sentido mantener código que miente sobre el límite.

```python
# ELIMINAR estas líneas de budget_fuse.py:
# - can_make_call() líneas 212-222
# - check_run_limit() líneas 262-264
# NOTA: el límite real lo enforcea reserve_and_record() en hikerapi_client._get():241
```

### 1.5 Tests

**Archivo nuevo:** `apps/api/tests/test_hito30_fail_loud.py`

```python
class TestFailLoud:
    async def test_zero_candidates_marks_failed():
        """0 candidatos en modo no-explorar → status failed."""

    async def test_missing_follower_field_vs_enrichment_failed():
        """Los dos counters son distintos y se incrementan independientemente."""

    async def test_user_message_differs_per_failure_mode():
        """El mensaje dinámico refleja la causa real del fallo."""

    async def test_budget_fuse_dead_code_removed():
        """can_make_call() y check_run_limit() ya no existen o están desconectadas."""
```

**Criterio de éxito Fase 1:**
- [ ] Contador separado en dos: `missing_follower_field` y `enrichment_failed`
- [ ] Estado `failed` cuando `total_candidates == 0` y no es Explorar
- [ ] Mensaje dinámico según causa (3 escenarios)
- [ ] `can_make_call()` eliminada o desconectada
- [ ] 4 tests nuevos pasando
- [ ] Railway deploy exitoso

---

## FASE 2 — Ensanchar la Búsqueda (1-2 h)

> **Lanz §7 Punto 4 — Lo único que sube el techo de calidad**
>
> "Ningún ajuste de puntaje rescata a un influencer que nunca entró al conjunto."

### 2.1 Ensanchar constantes de búsqueda

**Archivo:** `apps/api/app/workers/worker.py`

```python
# ACTUAL                              # PROPUESTO (v2 conservadora)
# Línea 534: for tag in plan.hashtag_queries[:3]:      → [:5]   (+2)
# Línea 547: for tag in plan.hashtag_queries[:2]:      → [:3]   (+1)
# Línea 562: for kw in plan.keyword_queries[:3]:        → [:5]   (+2)
# Línea 585: for kw in plan.keyword_queries[:1]:        → [:2]   (+1)
```

**Costo extra estimado por run: ~$0.44**
- Hashtag top: 2 más × 2 pages × 3 calls = +12 calls = +$0.24
- Hashtag recent: 1 más × 2 = +2 calls = +$0.04
- Keyword: 2 más × 3 = +6 calls = +$0.12
- Top search: 1 más × 2 = +2 calls = +$0.04

**Con $43.00:** ~97 runs restantes (vs 67 antes del ensanche)

**Nota:** Una versión más agresiva ([:10]/[:5]/[:10]/[:3]) costaría ~$1.46 extra y requiere decisión de Fase 5 primero.

### 2.2 Metadata dice la verdad sobre ejecución

**Archivo:** `apps/api/app/workers/worker.py:394-395`

```python
# ACTUAL (miente):
"keywords_count": len(plan.keyword_queries),   # 20, no lo que se ejecutó
"hashtags_count": len(plan.hashtag_queries),  # 30, no lo que se ejecutó

# PROPUESTO:
"hashtags_executed_count": hashtags_executed,   # Lo que realmente se llamó
"keywords_executed_count": keywords_executed,
"hashtags_planned_count": len(plan.hashtag_queries),
"keywords_planned_count": len(plan.keyword_queries),
"hashtags_execution_ratio": hashtags_executed / len(plan.hashtag_queries),  # 0.17 (3/18)
"keywords_execution_ratio": keywords_executed / len(plan.keyword_queries),  # 0.15 (3/20)
```

### 2.3 Tests

**Archivo nuevo:** `apps/api/tests/test_hito31_widen_search.py`

```python
class TestWidenSearch:
    async def test_hashtag_top_sliced_to_5():
        """Se consultan hasta 5 hashtags de top."""

    async def test_hashtag_recent_sliced_to_3():
        """Se consultan hasta 3 hashtags de recent."""

    async def test_keyword_search_sliced_to_5():
        """Se consultan hasta 5 keywords."""

    async def test_metadata_records_executed_not_planned():
        """hashtags_count/executed_ratio refleja lo real, no el plan."""
```

**Criterio de éxito Fase 2:**
- [ ] Constantes ensanchadas (v2 conservadora)
- [ ] Metadata dice ejecución real (3 de 18 hashtags, 3 de 20 keywords)
- [ ] 4 tests pasando
- [ ] Railway deploy exitoso

---

## FASE 3 — Contrato de Datos Único (6-8 h)

> **Lanz §7 Punto 2 — La regla ya está escrita en `13_data_contract_hub.md`**
>
> "NULL contra 0, y snake_case en inglés calzando 1:1 con las columnas."

### 3.1 Eliminar nombres duales en `_normalize_user()`

**Archivo:** `packages/discovery/discovery/tools/hikerapi_client.py:821-864`

```python
# ACTUAL (5 pares de nombres — convención Apify + HikerAPI):
return {
    "follower_count": follower_count,
    "followersCount": follower_count,        # ← ELIMINAR (Apify legacy)
    "following_count": following_count,
    "followsCount": following_count,         # ← ELIMINAR
    "posts_count": media_count,
    "postsCount": media_count,               # ← ELIMINAR
    "is_business": bool(...),
    "isBusinessAccount": bool(...),          # ← ELIMINAR
    "is_verified": bool(...),
    "verified": bool(...),                   # ← ELIMINAR
}

# PROPUESTO (solo snake_case inglés):
return {
    "follower_count": follower_count or None,
    "following_count": following_count or None,
    "posts_count": media_count or None,
    "is_business": bool(user.get("is_business", False)),
    "is_verified": bool(user.get("is_verified", False)),
    "_follower_count_source": "hikerapi",   # Trazabilidad
}
```

### 3.2 NULL ≠ 0: Reemplazar 33 cadenas `or 0`

**Archivo:** `apps/api/app/workers/worker.py`

```python
# ACTUAL (33 occurrences):
followers = p.get("followersCount") or p.get("follower_count") or 0

# PROPUESTO:
followers = p.get("follower_count")  # None si no existe — NO 0
# Y en el scoring:
if followers is None:
    missing_follower_field_counter += 1
elif followers == 0:
    enrichment_failed_counter += 1
```

**Buscar y reemplazar global en worker.py:**
- `or 0` en contextos de métricas → `or None`
- Agregar trazabilidad de fuente (`_source = "hikerapi"` o similar)

### 3.3 Crear `13a_data_contract_discovery.md`

**Archivo nuevo:** `docs/13a_data_contract_discovery.md`

```markdown
# Data Contract LENS Discovery — Anexo al Hub

**Versión:** 1.0
**Fecha:** 2026-08-25
**Estándar padre:** `13_data_contract_hub.md` v1.0
**Aplica a:** packages/discovery/ y apps/api/app/workers/

## Reglas Fundamentales

1. **NULL ≠ 0.** Campo ausente se escribe como SQL NULL, no como 0.
   - `followers = None` (no `followers = 0`)
   - `following_count = None` (no `following_count = 0`)

2. **Una convención de nombres: snake_case inglés.**
   - Solo `follower_count` (NO `followersCount`)
   - Solo `following_count` (NO `followsCount`)
   - Solo `posts_count` (NO `postsCount`)

3. **raw_data obligatorio.** Payload crudo del proveedor en JSONB.
   - `raw_data: dict` — siempre presente, aunque vacío `{}`

4. **source_id obligatorio.** Identificador del proveedor.
   - `source_id: str` — "hikerapi" o según corresponda

5. **fetched_at obligatorio.** Timestamp de cuándo se pagó la llamada.
   - `fetched_at: datetime` — con timezone UTC

6. **Trazabilidad de campos duales.** Si un campo viene de dos fuentes,
   usar sufijo `_source`: `follower_count_hikerapi`, `follower_count_apify`.

## Tabla de Campos

| Campo | Tipo | Requerido | Notas |
|-------|------|-----------|-------|
| `follower_count` | int? | Sí | NULL si ausente — NO 0 |
| `following_count` | int? | Sí | NULL si ausente |
| `posts_count` | int? | Sí | NULL si ausente |
| `is_business` | bool | Sí | default False |
| `is_verified` | bool | Sí | default False |
| `raw_data` | dict | Sí | Payload crudo |
| `source_id` | str | Sí | Nombre del proveedor |
| `fetched_at` | datetime | Sí | UTC |

## Migración de Datos

Los datos guardados antes de este contrato (con convención dual) son retrocompatibles:
- Queries deben usar `COALESCE(follower_count, followersCount)` temporalmente
- Progresivamente migrar a solo `follower_count`
```

### 3.4 Tests

**Archivo nuevo:** `apps/api/tests/test_hito32_data_contract.py`

```python
class TestDataContract:
    def test_normalize_user_snake_case_only():
        """_normalize_user retorna solo snake_case, sin camelCase."""

    def test_normalize_user_returns_none_for_missing():
        """Campo ausente retorna None, no 0."""

    def test_or_zero_replaced_globally():
        """No quedan cadenas 'or 0' en worker.py para métricas."""

    def test_data_contract_doc_exists():
        """13a_data_contract_discovery.md existe y declara NULL≠0."""

    def test_raw_data_field_present():
        """Los candidatos persistidos tienen raw_data."""
```

**Criterio de éxito Fase 3:**
- [ ] `_normalize_user` solo retorna snake_case
- [ ] 33 cadenas `or 0` reemplazadas por `or None` con trazabilidad
- [ ] `13a_data_contract_discovery.md` creado
- [ ] 5 tests pasando
- [ ] Railway deploy exitoso

---

## FASE 4 — Completar el Camino a la Tabla Maestra (4-6 h)

> **Lanz §7 Punto 3 — El camino ya existe, solo tiene 4 huecos**
>
> "Lo que convierte el gasto en un activo que se acumula."

### 4.1 Arreglar `POST /candidates/{id}/save`

**Archivo:** `apps/api/app/api/v1/discovery.py:838-887`

```python
# ACTUAL (huecos):
values = {
    "full_name": candidate.get("full_name", ""),
    "primary_handle": candidate.get("handle", ""),
    "bio": candidate.get("bio", ""),
    "country": candidate.get("country", "VE"),
    "city": candidate.get("city", ""),
    "avatar_url": candidate.get("avatar_url", ""),
    "primary_tier": "MICRO",  # ← HARDCODED, debería derivarse
    "discovery_query": "",     # ← VACÍO, debería venir del candidato
    # FALTAN: follower_count, engagement_rate, avg_likes
    # FALTAN: raw_data, source_id, fetched_at
}

# PROPUESTO:
values = {
    "full_name": candidate.get("full_name", ""),
    "primary_handle": candidate.get("handle", ""),
    "bio": candidate.get("bio", ""),
    "country": candidate.get("country", "VE"),
    "city": candidate.get("city", ""),
    "avatar_url": candidate.get("avatar_url", ""),
    # CORREGIDO — derive tier:
    "primary_tier": _derive_tier(candidate.get("follower_count")),
    # CORREGIDO — discovery_query:
    "discovery_query": candidate.get("discovery_query", ""),
    # NUEVO — métricas:
    "follower_count": candidate.get("follower_count"),
    "engagement_rate": candidate.get("engagement_rate"),
    "avg_likes": candidate.get("avg_likes"),
    # NUEVO — contrato de datos:
    "raw_data": candidate.get("raw_data", {}),
    "source_id": candidate.get("source_id"),
    "fetched_at": candidate.get("fetched_at"),
}
```

### 4.2 Deduplicar por handle

```python
# ANTES DEL INSERT:
existing = await railway_pg.select(
    table="influencers",
    select="id",
    where={"primary_handle": handle}
)
if existing:
    influencer_id = existing[0]["id"]  # UPDATE en vez de INSERT
    # Actualizar métricas si son más frescas
else:
    influencer_id = await railway_pg.insert(...)
```

### 4.3 Helper `_derive_tier()`

```python
def _derive_tier(followers: int | None) -> str:
    """Copiado de scripts/etl_ism_backfill.py:193."""
    if followers is None:
        return "NANO"
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    if followers < 1_000_000:
        return "MACRO"
    return "MEGA"
```

### 4.4 Crear `influencer_social_accounts` e `influencer_metrics_snapshot`

```python
# Después de crear/actualizar influencer:
await railway_pg.insert(
    table="influencer_social_accounts",
    values={
        "influencer_id": influencer_id,
        "platform": "instagram",
        "handle": handle,
        "url": candidate.get("url"),
        "is_primary": True,
    }
)

await railway_pg.insert(
    table="influencer_metrics_snapshot",
    values={
        "influencer_id": influencer_id,
        "platform": "instagram",
        "snapshot_date": datetime.now(timezone.utc).date(),
        "follower_count": candidate.get("follower_count"),
        "engagement_rate": candidate.get("engagement_rate"),
        "avg_likes": candidate.get("avg_likes"),
        "raw_data": candidate.get("raw_data", {}),
    }
)
```

### 4.5 Política de frescura (7 días)

```python
# Verificar si ya existe snapshot reciente:
last_snapshot = await railway_pg.select(
    table="influencer_metrics_snapshot",
    select="snapshot_date",
    where={"influencer_id": influencer_id},
    order_by="snapshot_date DESC",
    limit=1
)
if last_snapshot:
    days_old = (datetime.now().date() - last_snapshot[0]["snapshot_date"]).days
    if days_old < 7:
        return {"id": influencer_id, "status": "skipped_fresh"}
```

### 4.6 Tests

**Archivo nuevo:** `apps/api/tests/test_hito33_save_master_table.py`

```python
class TestSaveMasterTable:
    async def test_save_carries_follower_metrics():
        """Se guardan follower_count, engagement_rate, avg_likes."""

    async def test_save_dedupes_by_handle():
        """Guardar dos veces el mismo handle no produce duplicados."""

    async def test_save_derives_tier_from_followers():
        """Tier se deriva de followers, no está hardcoded."""

    async def test_save_creates_social_account_row():
        """Se crea fila en influencer_social_accounts."""

    async def test_save_creates_metrics_snapshot_row():
        """Se crea fila en influencer_metrics_snapshot."""

    async def test_save_skips_if_recent_snapshot():
        """No se re-paga si la última snapshot tiene < 7 días."""
```

**Criterio de éxito Fase 4:**
- [ ] `discovery.py:838` arrastra métricas pagadas
- [ ] Deduplicación por handle
- [ ] Tier derivado de followers (no hardcoded MICRO)
- [ ] Filas creadas en social_accounts y metrics_snapshot
- [ ] Política de frescura: 7 días
- [ ] 6 tests pasando
- [ ] Railway deploy exitoso

---

## FASE 5 — Decisión de Negocio (NO TÉCNICA)

> **Lanz §7 Punto 5 — Bloqueante para las 8 brechas y cambio de modelo**

### Preguntas a responder (lado negocio):

1. ¿Cuántas búsquedas al mes se piensan vender?
2. ¿Cuánto puede costar cada una?
3. ¿Cuál es el plan vigente en HikerAPI?
4. ¿Cuál es el saldo actual y cuándo se acaba al ritmo estimado?

### Output esperado:

**Archivo:** `docs/PLAN_PROVEEDOR_DECISION_2026-08-25.md`

---

## LO QUE NO SE HARÁ EN ESTE PLAN

| No hacer | Razón |
|----------|-------|
| Reescribir worker.py (2.245 líneas) | "Cambia el código sin cambiar lo que se sabe" (Lanz) |
| Conectar embeddings a LENS ahora | "Un vector reordena, no recluta" — el recorte a 25 corre ANTES del enrichment |
| Implementar las 8 brechas del Audit #14 | Afinan ranking, no suben techo — postergadas hasta post-Fase 4 |
| Cambiar modelo de IA | Bloqueado por Fase 5 (decisión de negocio) |
| Modificar `13_data_contract_hub.md` | Es de P.I.A.R. — crear `13a_data_contract_discovery.md` |
| Eliminar `apps/api/app/models/ai.py` | Deriva de config, no rompe nada |

---

## Resumen de Esfuerzo y Costo

| Fase | Esfuerzo | Costo Extra Por Run |
|------|-----------|---------------------|
| 0. Verificaciones | 30 min | ~$0.002 |
| 1. Fallar en voz alta | 4-6 h | $0 |
| 2. Ensanchar búsqueda | 1-2 h | ~$0.44 |
| 3. Contrato de datos | 6-8 h | $0 |
| 4. Tabla maestra | 4-6 h | $0 |
| 5. Decisión negocio | — | — |
| **TOTAL** | **~16-22 h** | **~$0.44** |

---

## Orden de Implementación

```
1. Fase 0 — Verificaciones (30 min)
      ↓
2. Fase 1 — Fallar en voz alta (4-6 h) ← BLOQUEANTE de todo
      ↓
3. Fase 2 — Ensanchar búsqueda (1-2 h) ← INDEPENDIENTE, costo $0.44
      ↓
4. Fase 3 — Contrato de datos (6-8 h) ← Depende de Fase 1
      ↓
5. Fase 4 — Tabla maestra (4-6 h) ← Depende de Fase 3
      ↓
6. Pausa — esperar decisión Fase 5
      ↓
7. Post-pausa — elegir 2-3 de las 8 brechas con datos reales
```

---

## Criterios de Éxito Globales

- [ ] El sistema distingue "no traje el dato" vs "el enriquecimiento falló"
- [ ] El estado final distingue "haber corrido" vs "haber entregado"
- [ ] La búsqueda ejecuta 5+ hashtags/keywords (vs 3 antes)
- [ ] Un campo ausente se escribe como NULL, no como 0
- [ ] El tier se deriva de followers, no se hardcodea
- [ ] Las métricas pagadas llegan a `influencer_metrics_snapshot`
- [ ] El mismo handle dos veces no produce dos influencers
- [ ] ≥18 tests nuevos pasando (4+4+5+6)
- [ ] Railway deploy sin errores tras cada fase

---

## Para Cada Fase: Criterio de Éxito Antes de Pasar a la Siguiente

| Fase | Criterio |
|------|----------|
| **0** | 4 verificaciones respondidas con evidencia |
| **1** | `total_candidates == 0` → `status = failed` (no `completed`) |
| **2** | Metadata muestra `execution_ratio < 1.0` (la búsqueda no está al máximo) |
| **3** | `_normalize_user` solo tiene snake_case; 0 cadenas `or 0` en worker.py |
| **4** | `influencer_metrics_snapshot` tiene filas con `follower_count` no NULL |
| **5** | Decisión documentada sobre plan de proveedor y modelo de IA |

---

## Comandos de Verificación Post-Deploy

```bash
# Verificar que worker recargó:
python -c "from discovery.schemas import BriefStructured; b = BriefStructured(max_candidates=20); print('OK:', b.max_candidates)"

# Verificar modelo (V2):
curl -s -H "x-access-key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/account | jq

# Verificar PITR (V3):
# Panel Railway → Postgres → Backups → Point-in-time recovery: ¿ON?

# Run de prueba Explorar (~$0.64 + $0.10 enrich):
curl -X POST https://api.lawebcore.com/api/v1/discovery/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"brief_text": "...", "discovery_mode": "explore"}'

# Contar candidatos:
psql $DATABASE_URL -c "SELECT COUNT(*) FROM discovery_candidates WHERE run_id = '$RUN_ID';"
```

---

*Plan generado: 2026-08-25 por MiniMax M2.7/M3 basado en `docs/La Web Figital - Informe de Alineación Técnica LENS.md` (Santiago Lanz, v1.2)*
