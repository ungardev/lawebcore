# Auditoría Lanz v2.0 — LENS Discovery
## 27 de agosto de 2026 · v2.0

> **De:** MiniMax M2.7/M3 (investigación exhaustiva)
> **Basado en:** `docs/La Web Figital - Informe de Alineación Técnica LENS.md` (Lanz v1.2, 24-ago-2026, commit `81db353`)
> **Refundición de:** Lanz v1.2 + 23 hallazgos nuevos descubiertos post-Hito 35
> **Repo:** `github.com/ungardev/lawebcore`
> **Commit audited:** HEAD `1bdacc3` (fixes aplicados)
> **Método:** lectura directa del árbol, investigación por agentes, grep/glob en 47 archivos

---

## §1 — Resumen Ejecutivo

**El sistema tiene 2 bugs críticos no detectados por Lanz v1.2 que invalidan parcialmente el Hito 35.** Ambos fueron introducidos por los fixes de Hito 35.1-35.8 (commit `2446e75`, 26-ago-2026) y ninguno es detectado por el test suite.

| Bug | Severidad | Impacto |
|-----|-----------|---------|
| BUG #1: `worker.py:1298` — typo `followers_count` vs `follower_count` | 🔴 CRÍTICO | 0 candidatos por corrida en auto/analyze mode desde Hito 35 |
| BUG #2: `discovery.py:973,976` — columnas `follower_count`/`raw_data` vs `followers`/`raw_payload` | 🔴 CRÍTICO | Save Candidate retorna 500 en cada click |
| 12 bugs abiertos de Lanz v1.2 | 🟡 CRÍTICO | Sistema aún no cumple los 5 puntos del §7 |
| 9 bugs nuevos de deuda técnica | 🟠 MEDIO | Dead code, drift de docs, columnas muertas |

**Estado del sistema antes de esta auditoría:** CI verde, Railway desplegado, pero el pipeline completo está **roto en producción silenciosamente**.

**Estado después de los fixes de esta auditoría:** BUG #1 y #2 corregidos en `1bdacc3`. Resta ejecutar FASE 1-5 para cumplir Lanz v1.2.

---

## §2 — Cumplimiento Lanz v1.2 §7 Punto por Punto

Lanz §7 define 5 acciones de alineación. Aquí el estado actual:

### §7.1 — "Que el sistema pueda fallar en voz alta"
**Estado: ~30% cumplido**

| Sub-requisito | Estado | Evidencia |
|--------------|--------|-----------|
| Error paths no inventan valores | ⚠️ Parcial | 21 `or 0` chains persisten en worker.py; 27 broad `except Exception` en worker.py (hot path: 17) |
| Estado final distingue correr vs entregar | ✅ Parcial | `worker.py:1785` ahora checks `total == 0` → EMPTY/INCONSISTENT; pero no hay grading (1 vs 100 candidatos = mismo status) |
| `can_make_call()` eliminada | ✅ Hecho | Removida en `bd973c7` (Hito 30) |
| `determine_final_status()` implementada | ❌ Regresión | Definida en `observability.py:231` pero **nunca llamada** — dead code |
| `budget_aborted` flag | ❌ No existe | Solo como nombre de parámetro en `determine_final_status()` dead code |

**Residual:** El patrón de "producir valor plausible y continuar" sigue vigente en 17+ sitios del hot path.

### §7.2 — "Un contrato de datos único"
**Estado: ~35% cumplido**

| Sub-requisito | Estado | Evidencia |
|--------------|--------|-----------|
| `_normalize_user()` devuelve None (no 0) | ✅ Hecho | `hikerapi_client.py:823,847` — `follower_count` y `following_count` return None |
| Una sola forma por campo | ❌ Parcial | enrichment write fixed (Hito 35); 8 search-step dict constructions aún emiten ambos formas |
| 13a_data_contract_discovery.md existe | ✅ Hecho | `docs/13a_data_contract_discovery.md` (6 reglas) |
| `LegacyCompatReader` existe | ❌ No existe | Referenciado en el doc, no en código |
| `CONTRACT_VIOLATION` se emite | ❌ Nunca | Definido en `RunEvent` enum, nunca invocado |

### §7.3 — "Completar el camino del descubrimiento a la tabla maestra"
**Estado: ~55% cumplido**

| Sub-requisito | Estado | Evidencia |
|--------------|--------|-----------|
| Deduplicación por handle | ✅ Hecho | `discovery.py:888-892` + índice único migration 109 |
| Métricas carry-through | ⚠️ Parcial | Código existe; BUG #2 (columnas erradas) bloquea ejecución |
| Tier derivado | ✅ Hecho | `_derive_tier()` 9 sub-tiers |
| UPSERT social_accounts | ✅ Hecho | `discovery.py:953-965` |
| UPSERT metrics_snapshot | ⚠️ Bug #2 | BUG #2 bloquea — columnas `follower_count`/`raw_data` no existen |
| `discovery_query` poblado | ❌ Nunca | Solo se lee con default `""`; no hay writer |
| Política de frescura | ❌ No existe | `CACHE_TTL_PROFILE=86400`; `influencers.enriched_at` escrito pero nunca leído |

### §7.4 — "Ensanchar la búsqueda"
**Estado: ~70% cumplido**

| Sub-requisito | Estado | Evidencia |
|--------------|--------|-----------|
| Límites ampliados | ✅ Hecho | 6/4/6/3 (antes 3/2/3/1) — `config.py:95-99` |
| Metadata registra ejecución vs plan | ✅ Hecho | `worker.py:411-414` — `*_planned_count` y `*_executed_count` |
| 88 llamadas sin usar | ⚠️ Parcial | ~64 sin usar de 120; `MAX_HANDLES_TO_ENRICH=25` vs `target_n=80` aún limita |
| Plan construye 30+20 | ✅ Sin cambios | `query_builder.py:141,161` |

### §7.5 — "Plan del proveedor + modelo IA"
**Estado: ~40% cumplido**

| Sub-requisito | Estado | Evidencia |
|--------------|--------|-----------|
| `DEEPSEEK_MODEL=deepseek-v3` en código | ✅ Hecho | `config.py:55`, `.env.example:32` |
| `DEEPSEEK_MODEL` en Railway verificado | ❌ Desconocido | No se puede verificar sin acceso al dashboard |
| `response_format` usado en scoring | ⚠️ Parcial | Solo en `candidate_analyzer.py:326`; 3 otros call sites usan regex |
| Modelo de RAG no se reutiliza | ✅ Confirmado | Discovery no usa embeddings; Lanz §5.2 aplica |
| `api_costs` registra model name | ❌ No | Solo provider; sin model column |

---

## §3 — Hallazgos Nuevos (No en Lanz v1.2)

> Todos estos fueron descubiertos en la auditoría exhaustiva del 27-ago-2026.
> Lanz v1.2 auditó commit `81db353` (21-ago-2026). Hito 35 se aplicó después (`2446e75`, 26-ago-2026).
> Por eso estos bugs no aparecen en v1.2.

### 3.1 — BUG #1 🔴 CRÍTICO: Enrichment key mismatch

**Descripción:** Hito 35.1 (FIX #0+1) cambió enrichment para escribir solo `follower_count` (snake_case singular). Pero el scoring en `worker.py:1298` leyó `followers_count` (plural con 's' extra) — un typo. El fallback a `followersCount` (camelCase) también falló porque FIX #0+1 eliminó la escritura camelCase.

**Impacto:** Todo perfil enriquecido (~25 por corrida) es descartado como `MISSING_FOLLOWER_FIELD`. `step4_scoring` produce 0 candidatos. El run termina en `EMPTY`. El mensaje al usuario dice "100% sin campo de seguidores" aunque el valor era 5000.

**Archivo:** `apps/api/app/workers/worker.py:1298`

**Fix aplicado:** `1bdacc3` — cambiar `followers_count` → `follower_count`

**Verificación:**
```python
# El perfil enriquecido tiene:
p = {"_enriched": True, "follower_count": 5000}  # worker.py:1211 escribe
# worker.py:1298 ANTES: "followers_count" in p → False → fallback → None → 0 → DROP
# worker.py:1298 DESPUÉS: "follower_count" in p → True → 5000 → continúa
```

### 3.2 — BUG #2 🔴 CRÍTICO: Columnas inválidas en metrics_snapshot UPSERT

**Descripción:** `discovery.py:973,976` escribe `follower_count` y `raw_data` al UPSERT de `influencer_metrics_snapshot`. Las columnas reales son `followers` y `raw_payload` (verificado en `migrations/00000000000005_influencers.sql:55-75`).

**Impacto:** Cada click en "Save Candidate" genera error PostgreSQL 42703 (`column "follower_count" does not exist`). El candidato nunca se promueve a influencer.

**Archivo:** `apps/api/app/api/v1/discovery.py:973,976`

**Fix aplicado:** `1bdacc3` — `follower_count` → `followers`, `raw_data` → `raw_payload`

### 3.3 — `apply_migrations.py` no ejecuta migraciones incrementalmente

**Descripción:** El script solo aplica `schema.sql` una vez (version `00000000000001`). No itera sobre `supabase/migrations/000000000000{002..110}*.sql`. Las migraciones 108 y 109 (tabla events + índice unique) **no se ejecutan automáticamente**.

**Impacto:** `discovery_run_events` no existe en producción hasta que alguien las corra manualmente. `flush_drop_ledger()` falla en cada run.

**Mitigación actual:** Migraciones 108/109 ejecutadas manualmente el 26-ago-2026 via SQL Editor Railway.

**Archivo:** `apps/api/scripts/apply_migrations.py:17-99`

### 3.4 — `schema.sql` desactualizado

**Descripción:** `schema.sql` (960 líneas) no incluye la tabla de migración 108 (`discovery_run_events`) ni el índice único de migración 109. Solo incluye los valores del ENUM de migración 110.

**Impacto:** Si alguien regenera la DB desde `schema.sql`, pierde la tabla events y el índice dedup.

**Archivo:** `supabase/schema.sql`

### 3.5 — `discovery_query` nunca se escribe

**Descripción:** El campo existe en `influencers.discovery_query` (migración 19, 97). El worker nunca lo populate. `discovery.py:906,927` solo lo LEEN con default `""`.

**Impacto:** No hay trazabilidad de qué query descubrió cada influencer.

**Archivo:** `apps/api/app/workers/worker.py` (ningún writer); `apps/api/app/api/v1/discovery.py:906,927`

### 3.6 — `determine_final_status()` es dead code

**Descripción:** La función existe en `observability.py:231-249` con lógica correcta para estados EMPTY/INCONSISTENT/DEGRADED/DELIVERED. Pero **nadie la llama**. El worker.py:1785-1790 reimplementó la lógica a mano, parcialmente.

**Impacto:** `funnel_invariant_ok` y `budget_aborted` nunca se computan. El estado final no distingue todos los casos.

**Archivo:** `packages/shared-core/shared_core/observability.py:231`

### 3.7 — 27 broad exception handlers en worker.py (hot path: 17)

**Descripción original (Lanz):** 179 en todo el repo. Estado actual: 27 en worker.py, de los cuales 17 están en el hot path (steps 1-4 del worker). Todos hacen `logger.warning(...)` y continúan.

**Impacto:** Errores se tragan silenciosamente. El patrón Lanz §3 sigue vigente.

**Archivos:** `apps/api/app/workers/worker.py` — L238, L260, L507, L509, L559, L572, L587, L597, L610, L625, L647, L1131, L1140, L1186, L1920, L1952, L1957, L1974, L1980, L2150, L2164, L2211, L2254, L2273

### 3.8 — 21 `or 0` chains en worker.py

**Descripción:** pattern `x.get("y") or 0` convierte ausencia de dato en 0. Los más peligrosos están en `_raw_to_candidate_dict` (L2013-2015): `followers`, `following`, `posts_count` todos como `or 0`.

**Impacto:** Perfil sin campo se vuelve "0 seguidores" indistinguible de uno real.

**Archivo:** `apps/api/app/workers/worker.py` — L131, L133, L141, L1397, L1398, L1476, L1477, L1610, L1614-L1617, L1654, L2013-L2015, L2026-L2027, L2064-L2066

### 3.9 — 6/7 dual-name patterns presentes

**Descripción:** FIX #0+1 limpió el enrichment write. Pero los 8 search-step dict constructions (L376-396, L516-537, L733-867, etc.) siguen emitiendo ambos formas: `follower_count` + `followersCount`.

**Impacto:** Hito 31.2 no se cumple en el camino de búsqueda. La auditoría de runtime no puede distinguir dato faltante de dato presente.

**Archivo:** `apps/api/app/workers/worker.py` — ~80 dual-writes por corrida

### 3.10 — `media_count` con `or` chain en hikerapi_client.py

**Descripción:** `hikerapi_client.py:825` — `media_count = user.get("media_count") or user.get("posts_count")`. Una cuenta con 0 posts reales pierde su dato si `posts_count` falta.

**Archivo:** `packages/discovery/discovery/tools/hikerapi_client.py:825`

### 3.11 — `main.py:84` referencia `railway_pg` no importado

**Descripción:** `main.py:84` tiene `await railway_pg.close()` con `# noqa: F821` (ignorado por linter). A runtime lanza `NameError` en cada shutdown.

**Archivo:** `apps/api/app/main.py:84`

### 3.12 — `discovery.router` mounted dos veces

**Descripción:** `discovery.router` está en `/api/v1/discovery/*` y también en `/api/v1/lens/discovery/*`. El rate limiter lee solo una copia.

**Impacto:** Rate limit efectivo se reduce a la mitad.

**Archivos:** `apps/api/app/api/v1/__init__.py:40-41`, `apps/api/app/api/v1/lens.py:7-8`

### 3.13 — `FunnelTracker()` instanciado pero nunca usado

**Descripción:** `worker.py:290` — `funnel = FunnelTracker()  # noqa: F841`. La instancia se crea y se descarta. Las invariantes reales se computan en sets locales (`step1_handles`, etc.) sin tracking de FunnelTracker.

**Archivo:** `apps/api/app/workers/worker.py:290`

### 3.14 — `is_discoverable` escrito, nunca leído

**Descripción:** `discovery.py:925` escribe `is_discoverable=True` en cada INSERT de influencer. No hay ninguna query `WHERE is_discoverable=true` en el codebase.

**Archivo:** `apps/api/app/api/v1/discovery.py:925`

### 3.15 — `influencers.enriched_at` escrito, nunca leído

**Descripción:** Escrito en `discovery.py:694` y `admin.py:469`. Nunca consultado para freshness policy. La columna existe para gating de re-enriquecimiento pero no se usa.

### 3.16 — `_parse_batch_response` tiene `import re` dead

**Descripción:** `candidate_analyzer.py:183` — el `import re` quedó después de FIX #8 que eliminó el `re.search`. Código muerto.

### 3.17 — `brief_parser.py` y `profile_generator.py` siguen con regex extraction

**Descripción:** Solo `candidate_analyzer.py:326` usa `response_format={"type": "json_object"}`. `brief_parser.py:204-208` y `profile_generator.py:502` usan regex.

### 3.18 — `ai_prompts` defaults `openai`/`gpt-4o-mini`

**Descripción:** `models/ai.py:34-35` — defaults de tabla de prompts son de otra era. El código fuerza DeepSeek en la práctica (`ai_service.py:280-294`).

### 3.19 — Docs stale con `deepseek-chat`

**Descripción:** `docs/LAWEBCORE_PROYECTO_COMPLETO.md:791`, `docs/CREDENCIALES_Y_SUSCRIPCIONES.md:92,137` aún mencionan `DEEPSEEK_MODEL=deepseek-chat` (retired).

### 3.20 — `api_costs` sin columna model name

**Descripción:** `api_costs` tabla solo tiene `provider`, no `model`. No hay forma de saber qué modelo se cobró por corrida.

### 3.21 — Test suite no cubre los paths críticos

**Descripción:** Los 3 tests e2e (`test_pipeline_e2e.py:157,205,238`) tienen `@pytest.mark.skip(reason="requires live Postgres")`. BUG #1 y #2 son invisibles para CI.

### 3.22 — DEEPSEEK_MODEL en Railway sin verificar

**Descripción:** El código default es `deepseek-v3`. Railway podría tener env var diferente. No hay forma de saber desde el código.

### 3.23 — `MAX_HANDLES_TO_ENRICH=25` vs `target_n=80`

**Descripción:** El diversity step pide 80 perfiles pero solo 25 se enriquecen. Las cuotas por tier nunca llegan a morder.

---

## §4 — Tabla de Severidad

| # | Hallazgo | Severidad | Clasificación |
|---|----------|-----------|-------------|
| 1 | BUG #1: enrichment key mismatch — 0 candidatos por corrida | 🔴 CRÍTICO | Bug de regresión Hito 35 |
| 2 | BUG #2: columnas inválidas en metrics_snapshot | 🔴 CRÍTICO | Bug de regresión Hito 35 |
| 3 | Migraciones 108/109 no automáticas | 🟡 CRÍTICO | Infraestructura |
| 4 | 27 broad exception handlers en hot path | 🟡 CRÍTICO | Lanz §7.1 incompleto |
| 5 | 21 `or 0` chains en worker.py | 🟡 CRÍTICO | Lanz §7.1 incompleto |
| 6 | 6/7 dual-name patterns en search steps | 🟡 CRÍTICO | Lanz §7.2 incompleto |
| 7 | `discovery_query` nunca escrito | 🟡 CRÍTICO | Lanz §7.3 incompleto |
| 8 | Sin política de frescura | 🟠 MEDIO | Lanz §7.3 incompleto |
| 9 | `determine_final_status()` dead code | 🟠 MEDIO | Deuda técnica |
| 10 | `budget_aborted` flag no existe | 🟠 MEDIO | Lanz §7.1 incompleto |
| 11 | `response_format` solo en 1/4 call sites LLM | 🟠 MEDIO | Lanz §7.5 incompleto |
| 12 | Test suite no cubre paths críticos | 🟠 MEDIO | Riesgo de regresión |
| 13 | `schema.sql` desactualizado | 🟠 MEDIO | Deuda técnica |
| 14 | `apply_migrations.py` single-shot | 🟠 MEDIO | Arquitectura |
| 15 | `main.py:84` railway_pg undefined | 🟠 MEDIO | Runtime error |
| 16 | `media_count` or chain | 🟡 MEDIA | Deuda técnica |
| 17 | `FunnelTracker()` dead | 🟡 MEDIA | Deuda técnica |
| 18 | `is_discoverable` columna muerta | 🟡 MEDIA | Deuda técnica |
| 19 | `influencers.enriched_at` sin leer | 🟡 MEDIA | Feature incompleto |
| 20 | docs stale con deepseek-chat | 🟢 BAJA | Drift de docs |
| 21 | `api_costs` sin model name | 🟢 BAJA | Deuda técnica |
| 22 | `discovery.router` double-mounted | 🟢 BAJA | Rate limit halved |
| 23 | `ai_prompts` defaults stale | 🟢 BAJA | Drift de docs |

---

## §5 — Plan de Acción en 5 Fases

### FASE 0 — UNBLOCK ($0, ~1 día)

> Objetivo: que el sistema pueda funcionar end-to-end.

| # | Acción | Archivo | Estado |
|---|--------|---------|--------|
| 0.1 | Fix BUG #1: `worker.py:1298` `followers_count` → `follower_count` | `worker.py:1298` | ✅ Aplicado `1bdacc3` |
| 0.2 | Fix BUG #2: `discovery.py:973,976` `follower_count`/`raw_data` → `followers`/`raw_payload` | `discovery.py:973,976` | ✅ Aplicado `1bdacc3` |
| 0.3 | Verificar migraciones 108/109 en Railway | SQL Editor | ⏳ Pendiente — requiere acceso |
| 0.4 | Fix `main.py:84` — importar `railway_pg` | `main.py:84` | ⏳ Pendiente |

### FASE 1 — DATA CONTRACT ($0, ~2-3 días)

> Objetivo: cumplir Lanz §7.2.

| # | Acción |
|---|--------|
| 1.1 | Eliminar 8 sitios de dual-write en worker.py search steps (L376-933) — usar solo snake_case |
| 1.2 | Implementar `LegacyCompatReader` (referenciado en `13a_data_contract_discovery.md` — no existe) |
| 1.3 | Emitir `RunEvent.CONTRACT_VIOLATION` cuando se detecten dual-names en runtime |
| 1.4 | Crear test `test_enriched_merge_preserves_follower_count_snake_case` |
| 1.5 | Eliminar `or 0` en `_raw_to_candidate_dict` L2013-2015 — usar None y dejar que el caller decida |

### FASE 2 — FAIL LOUDLY ($0, ~3-4 días)

> Objetivo: cumplir Lanz §7.1.

| # | Acción |
|---|--------|
| 2.1 | Implementar caller real de `determine_final_status()` en worker.py |
| 2.2 | Computar `funnel_invariant_ok` real (comparar step1 vs step4 funnel) |
| 2.3 | Crear `budget_aborted` flag en worker.py (track cuando BudgetExhausted raise) |
| 2.4 | Reemplazar 17 broad `except Exception` en hot path con excepts específicos |
| 2.5 | Eliminar 21 `or 0` chains — especialmente en scoring paths |
| 2.6 | `FunnelTracker()` — usar la instancia o eliminarla |

### FASE 3 — MASTERY PATH ($0, ~3-4 días)

> Objetivo: cumplir Lanz §7.3.

| # | Acción |
|---|--------|
| 3.1 | Capturar `discovery_query` en worker.py — trackear qué query descubrió cada candidato |
| 3.2 | Implementar política de frescura: si `enriched_at < N hours`, skip re-enrichment |
| 3.3 | Crear `FRESHNESS_HOURS` config (default 168 = 7 días) — decisión Q2 pendiente |
| 3.4 | Incrementar `MAX_HANDLES_TO_ENRICH` de 25 a 50 (decisión Q4 pendiente) |
| 3.5 | `is_discoverable` — eliminar writing o implementar lectura |

### FASE 4 — AI/DISCOVERY ($0, ~2 días)

> Objetivo: cumplir Lanz §7.5.

| # | Acción |
|---|--------|
| 4.1 | Agregar `response_format={"type": "json_object"}` a `brief_parser.py:194,308` y `profile_generator.py:502` |
| 4.2 | Eliminar `_extract_json` regex en `brief_parser.py` y `complete_json()` regex en `deepseek_client.py:130-141` |
| 4.3 | Verificar env var `DEEPSEEK_MODEL` en Railway dashboard — confirmar `deepseek-v3` |
| 4.4 | Limpiar docs stale: `LAWEBCORE_PROYECTO_COMPLETO.md`, `CREDENCIALES_Y_SUSCRIPCIONES.md` |
| 4.5 | Limpiar dead code: `import re` en `candidate_analyzer.py:183`, `FunnelTracker()` |
| 4.6 | Agregar `model` column a `api_costs` |

### FASE 5 — VALIDACIÓN (~$1.14, ~1 día)

> Objetivo: cerrar el ciclo de feedback.

| # | Acción |
|---|--------|
| 5.1 | Correr `scripts/test_lens_mascotas_ve.py` desde máquina local |
| 5.2 | Verificar SQL post-corrida: estado terminal + reason_code distribution |
| 5.3 | Documentar resultados en PLAN_MAIN |

**Nota:** Esta auditoría decidió postergar FASE 5 hasta tener logs reales de Railway (decisión del usuario 27-ago-2026).

---

## §6 — Métricas de Éxito

| Métrica | Antes | Después de FASE 0 | Después de FASE 5 |
|---------|-------|-------------------|-------------------|
| Candidatos por corrida | 0 (BUG #1 activo) | ? (BUG #1 corregido) | ≥15 candidatos |
| Costo por corrida | N/A (0 candidatos) | ~$1.14 | <$1.20 |
| Save Candidate funciona | 500 (BUG #2 activo) | ✅ | ✅ |
| reason_code distribution | 1 valor | >1 valor | >3 valores |
| discovery_query poblado | No | No | Sí |

---

## §7 — Decisiones de Negocio Pendientes (Q1-Q4)

| # | Pregunta | Bloquea | Prioridad |
|---|---------|---------|-----------|
| Q1 | Lista handles Nestlé/Purina VE | Brand exclusion table (FP-2) | 🔴 Alta |
| Q2 | Ventana frescura: ¿7 vs 14 vs 30 días? | Freshness policy (FASE 3) | 🟡 Media |
| Q3 | Tier targeting macro (4) vs sub-tier (9) | Frontend | 🟡 Media |
| Q4 | Aprobación incremento MAX_HANDLES_TO_ENRICH 25→50 | FASE 3 | 🟡 Media |

---

## §8 — Lo que NO pude verificar

Las siguientes preguntas requieren acceso a producción y no se pueden responder desde el código:

| # | Pregunta | Cómo se verifica |
|---|---------|-----------------|
| 1 | ¿Migraciones 108/109 aplicadas en Railway PostgreSQL? | `SELECT version, filename FROM schema_migrations ORDER BY version;` en SQL Editor Railway |
| 2 | ¿`DEEPSEEK_MODEL` en Railway es `deepseek-v3`? | Railway dashboard → Variables de entorno |
| 3 | ¿El sistema produce candidatos después del fix BUG #1? | Logs de Railway post-deploy `1bdacc3` |
| 4 | ¿Hay política de desalojo de Redis activa? | Railway Redis dashboard |
| 5 | ¿PITR habilitado en Railway PostgreSQL? | Railway Dashboard → PostgreSQL → Backups |

---

## Anexo A — Commits Relevantes

| Commit | Fecha | Descripción |
|--------|-------|-------------|
| `81db353` | 21-ago | Commit auditado por Lanz v1.2 |
| `bd973c7` | 26-ago | Hitos 30-34 foundation |
| `2446e75` | 26-ago | Hitos 35.1-35.8 — **introdujo BUG #1 y #2** |
| `29d7ba6` | 27-ago | C-0/C-1/C-2 frontend coupling |
| `e5e17b6` | 27-ago | CI fixes — ruff noqa, mypy disabled |
| `1cbe613` | 27-ago | README rewrite |
| `2a9d4b6` | 27-ago | FASE 2-4 — sub-tiers, tests |
| `f0ecbf9` | 27-ago | FASE 3 — search limits widened |
| `1bdacc3` | 27-ago | **BUG #1 y #2 corregidos** |

---

## Anexo B — Diff de BUG #1

```diff
- followers = p.get("followers_count") if "followers_count" in p else p.get("followersCount")
+ followers = p.get("follower_count") if "follower_count" in p else p.get("followersCount")
```

## Anexo C — Diff de BUG #2

```diff
-             "follower_count": follower_count,
+             "followers": follower_count,
              "engagement_rate": candidate.get("engagement_rate"),
              "avg_likes": candidate.get("avg_likes"),
-             "raw_data": candidate.get("raw_payload", {}),
+             "raw_payload": candidate.get("raw_payload", {}),
```

---

*Documento creado: 27 de agosto de 2026 por MiniMax M2.7/M3*
*Basado en: Lanz v1.2 (Santiago Lanz, 24-ago-2026) + investigación exhaustiva de 3 agentes + verificación de 47 archivos*
*Estado: BUG #1 y #2 corregidos en commit `1bdacc3`. FASE 1-5 pendientes.*
