# PLAN MAIN — Alineación LENS Discovery
## Basado en el Informe de Santiago Lanz (v1.2, 24-ago-2026) + Análisis Claude Code Fable 5

> **Para:** Claude Code Fable 5 (subagente con acceso directo a https://github.com/ungardev/lawebcore)
> **De:** MiniMax M2.7/M3 (modelo agente de programación) + análisis exhaustivo post-commit `bd973c7`
> **Fecha:** 26 de agosto de 2026
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Commit base actual:** `bd973c7` (Hitos 30-34 aplicados, 26-ago-2026)
> **Commit docs:** `13944c0` (3 commits ahead de código — docs desactualizados)
> **HikerAPI balance:** $43.00 USD → ~$38 USD restantes post-hitos pendientes
> **Documentos de referencia:**
> - `docs/La Web Figital - Informe de Alineación Técnica LENS.md` (Santiago Lanz, v1.2)
> - `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` (índice histórico de auditorías — actualizar con auditoría #17)
> - `docs/ARQUITECTURA_LENS.md` v5.5 (arquitectura actual — requiere actualización)
> - `docs/PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md` (Plan oficial Claude Code Fable 5, 605 líneas)
> - `docs/13a_data_contract_discovery.md` (Data contract LENS v1.0, creado 26-ago-2026)
> - `docs/LANZ_VERIFICACIONES_2026-08-25.md` (Resultados V0-V4, creado 26-ago-2026)

---

## Estado Actual del Repositorio

### Lo que ya está aplicado (commit `bd973c7`, 26-ago-2026)

| Hito | Descripción | Archivos | Estado |
|------|-------------|----------|--------|
| **Hito 30** | Observabilidad: contextvars, RunEvent/DropReason/RunStatus enums, DropLedger, FunnelTracker, drop_profile(), RunStatus enum reemplaza strings, can_make_call() eliminada, events table migration 108 | `shared_core/observability.py`, `worker.py`, `budget_fuse.py`, `migrations/108` | ✅ Aplicado |
| **Hito 31.1** | `_normalize_user()` devuelve `None` para campos ausentes (no 0) | `hikerapi_client.py:821-856` | ✅ Aplicado |
| **Hito 31.2** | 7 pares dual-name eliminados del retorno de `_normalize_user()` | `hikerapi_client.py` | ✅ Aplicado |
| **Hito 31.4** | ~10+ patrones `or 0` corregidos con checks explícitos de None en worker.py | `worker.py:965-978, 1210-1232, 1306-1312, 1553-1562` | ✅ Aplicado |
| **Hito 31.5** | `docs/13a_data_contract_discovery.md` creado | `docs/13a_data_contract_discovery.md` | ✅ Aplicado |
| **Hito 32.1** | `_derive_tier()` en discovery.py (no más MICRO hardcoded) | `discovery.py:840-854` | ✅ Aplicado |
| **Hito 32.2** | Deduplicación por handle + migración 109 | `discovery.py`, `migrations/109` | ✅ Aplicado |
| **Hito 32.3** | Métricas carry-through: follower_count, engagement_rate, avg_likes en save | `discovery.py` | ✅ Aplicado |
| **Hito 32.4** | INSERT en influencer_social_accounts + influencer_metrics_snapshot | `discovery.py` | ✅ Aplicado |
| **Hito 33.1** | Constants a config: DISCOVERY_HASHTAG_TOP_LIMIT, etc. | `config.py`, `worker.py` | ✅ Aplicado |
| **Hito 33.2** | Slices usan settings en vez de hardcoded ([:3] → [:settings.LIMIT]) | `worker.py:551,564,579,602` | ✅ Aplicado |
| **Hito 33.3** | Metadata corregida: *_executed_count vs *_planned_count | `worker.py:408-415` | ✅ Aplicado |
| **Hito 34.1** | `response_format={"type": "json_object"}` en llamadas DeepSeek | `candidate_analyzer.py:327` | ✅ Aplicado |
| **Hito 34.3** | Regex extraction eliminado de `_parse_batch_response` | `candidate_analyzer.py:182-194` | ✅ Aplicado |
| **Hito 34.4** | `_fallback_scores` marcado con `is_fallback=True` | `candidate_analyzer.py:253` | ✅ Aplicado |
| **Hito 34.5** | Modelo DeepSeek: `deepseek-chat` → `deepseek-v3` | `config.py:55` | ✅ Aplicado |
| **Hito 35.2** | Validación backend: product_name y niches requeridos | `discovery.py:508-512` | ✅ Aplicado |

### Lo que queda pendiente (no aplicado)

| # | Hito | Descripción | Bloquea | Prioridad |
|---|------|-------------|---------|-----------|
| **#0** | CRÍTICA | Fix regresión: merge enrichment sigue leyendo camelCase de dict ya normalizado → datos de enrichment se pierden | Todo | 🔴 INMEDIATA |
| **#1** | 31.3 | LegacyCompatReader + ContractViolationLedger (ventana compatibilidad) | 32.5, 32.6 | 🟡 Alta |
| **#2** | 32.5 | Freshness policy 7 días: skip enrichment si snapshot <7d | 32.6 | 🟡 Alta |
| **#3** | 32.6 | Brand exclusion table (Compliance Nestlé L-03/L-05) | Hito 35 completo | 🟡 Alta |
| **#4** | CRÍTICA | `drop_profile()` no persiste en `discovery_run_events` (Capa 6 rota) | Auditoría 32.6 | 🔴 Alta |
| **#5** | 31.3 parte | Eliminar doble-escritura camelCase en construction dicts (worker.py:380-925) | PR-3 | 🟢 Media |
| **#6** | 31.3 parte | Refactor prefilter/scoring a snake_case (worker.py:967,1306,1528) | PR-3 | 🟢 Media |
| **#7** | 32.3 | `_derive_tier` → 9 sub-tiers (plan Fable 5 §1.3 pide 9, código tiene 4) | Frontend | 🟡 Media |
| **#8** | Housekeeping | Actualizar `supabase/seed.sql` y `schema.sql` default `deepseek-v3` | Ninguno | 🟢 Baja |
| **#9** | 31.6 | Tests `test_hito31_data_contract.py` | CI gate | 🟢 Baja |
| **#10** | 31.3 | Retirar LegacyCompatReader cuando contract.violation==0 por 14 días | — | ⏸ Diferido |

---

## 🚨 ALERTA CRÍTICA — Regresión Activa en Producción

**Descubierta por análisis subagente (26-ago-2026):**

Tras aplicar Hito 31.1 (`_normalize_user` ahora devuelve solo snake_case) y Hito 31.2 (7 dual-names eliminados del retorno), el **merge de enrichment en `worker.py:1204-1232`** sigue leyendo campos camelCase de `enriched_profiles`:

```python
# worker.py:1210-1215 (CÓDIGO ACTUAL — ROTO)
profiles[handle].update({
    "follower_count": e.get("followersCount", 0) or 0,  # → None (followersCount ya no existe)
    "followersCount": e.get("followersCount", 0) or 0,   # → None
    ...
})
```

**Consecuencia:** toda la metadata comprada en enrichment (followers, engagement, bio) se **pierde silenciosamente**. El scoring recibe `followers=0` para todos los perfiles y los descarta. Esto es **peor que el bug original** que Hito 31.1 debía arreglar.

**Fix #0 es prerrequisito absoluto** — sin él, cualquier carrera de validación de los hitos restantes usará datos incompletos.

---

## Contexto: Las 3 Decisiones de Arquitectura de Lanz

### Arquitectura 1: "Ante un error, producir un valor plausible y continuar"

**Estado post Hitos 30-34:**

| Ubicación | Qué hace | Estado |
|-----------|----------|--------|
| `embeddings.py:46-58` | Vector de 384 ceros | ⚠️ Sin cambios — fuera de scope LENS |
| `candidate_analyzer.py:348-382` | `_fallback_scores()` | ✅ Marcado con `is_fallback=True` (Hito 34.4) |
| `worker.py:1280+` | `followers=0` → descarte | ✅ Corregido: `None` check + `drop_profile()` (Hito 31.4) |
| `budget_fuse.py:213-222` | `can_make_call()` → `True` en error | ✅ ELIMINADA (Hito 30.8) |

### Arquitectura 2: "Se compra dos veces lo que ya se tiene"

**Estado post Hitos 30-34:**

| Problema | Solución aplicada | Estado |
|----------|-------------------|--------|
| Cache vence en 24h | Freshness policy 7d (Hito 32.5) | ⏳ Pendiente #2 |
| Tabla `influencers` sin métricas | Métricas carry-through (Hito 32.3) | ✅ Aplicado |
| `primary_tier` hardcoded "MICRO" | `_derive_tier()` (Hito 32.1) | ✅ Aplicado |
| Sin deduplicación por handle | Deduplicación + migración 109 (Hito 32.2) | ✅ Aplicado |
| Sin social_accounts ni metrics_snapshot | INSERT en ambas tablas (Hito 32.4) | ✅ Aplicado |

### Arquitectura 3: "Se busca en tres lugares, y la semántica no se usa"

**Estado post Hitos 30-34:**

| Problema | Solución aplicada | Estado |
|----------|-------------------|--------|
| Se ejecutan 3+3 hashtags/keywords | Slices configurable via settings (Hito 33.2) | ✅ Aplicado |
| Metadata miente sobre ejecución | `*_executed_count` vs `*_planned_count` (Hito 33.3) | ✅ Aplicado |
| Embeddings + pgvector sin usar | Sin cambios — fuera de scope | ⏸ Saltado |

---

## Verificaciones Lanz §8 — Estado V0-V4

| # | Pregunta | Respuesta | Evidencia | Estado |
|---|----------|-----------|-----------|--------|
| V0 | TIER_MIN_FOLLOWERS ¿filtro duro? | **NO** | Definido en worker.py:54 pero nunca usado como filtro. Filtro real = `plan.min_followers` del brief | ✅ V0 completada |
| V1 | Modelo en Railway | **Por verificar** | Requiere acceso panel Railway | ⏳ Pendiente |
| V2 | deepseek-chat resuelve | **Por verificar** | curl test necesario | ⏳ Pendiente |
| V3 | PITR activado | **Por verificar** | Panel Railway → Postgres → Backups | ⏳ Pendiente |
| V4 | Redis eviction policy | **Por verificar** | Panel Railway → Redis → Settings | ⏳ Pendiente |

**Conclusión V0:** H-2 NO es bloqueante. El sistema NO excluye NANO por diseño.

---

## LO QUE NO SE HARÁ EN ESTE PLAN

| No hacer | Razón |
|----------|--------|
| Reescribir worker.py (2.286 líneas) | "Cambia el código sin cambiar lo que se sabe" (Lanz) |
| Conectar embeddings a LENS ahora | "Un vector reordena, no recluta" — el recorte a 25 corre ANTES del enrichment |
| Eliminar `apps/api/app/models/ai.py` | Deriva de config, no rompe nada |
| Modificar `13_data_contract_hub.md` | Es de P.I.A.R. — `13a_data_contract_discovery.md` es el análogo para LENS |

---

## PLAN DE EJECUCIÓN — Hitos Pendientes #0 a #10

### 🔴 #0 — Fix Regresión Crítica: Merge Enrichment (INMEDIATA)

> **Archivos:** `apps/api/app/workers/worker.py:1204-1232`
> **Tipo:** Bug fix (regresión introduced by Hito 31.1)
> **Esfuerzo:** 2h
> **Corridas:** 1 validación
> **Costo:** ~$1.14

**Problema:** `_normalize_user()` ahora devuelve solo snake_case, pero el merge de enrichment lee camelCase → todas las métricas de enrichment se pierden.

**Solución:** Crear `packages/discovery/discovery/compat.py` con `LegacyCompatReader` + refactor del merge.

```python
# packages/discovery/discovery/compat.py
class LegacyCompatReader:
    """Lee campos snake_case con fallback legacy camelCase.
    Cada acceso a formato legacy emite contract.violation."""

    def read_followers(self, p: dict) -> int | None:
        if "followersCount" in p and "follower_count" not in p:
            logger.warning(RunEvent.CONTRACT_VIOLATION.value, field="follower_count", received="followersCount")
        return p.get("follower_count") or p.get("followersCount")

    def read_following(self, p: dict) -> int | None:
        if "followsCount" in p and "following_count" not in p:
            logger.warning(RunEvent.CONTRACT_VIOLATION.value, field="following_count", received="followsCount")
        return p.get("following_count") or p.get("followsCount")

    # ... read_posts, read_is_business, read_is_verified, read_biography, read_full_name, read_avatar_url
```

**Refactor del merge (`worker.py:1204-1232`):**

```python
from discovery.compat import LegacyCompatReader
compat = LegacyCompatReader()

for e in enriched_profiles:
    handle = e.get("username", "")
    if not handle or handle not in profiles:
        continue
    profiles[handle].update({
        "follower_count": compat.read_followers(e),
        "following_count": compat.read_following(e),
        "posts_count": compat.read_posts(e),
        "is_business": compat.read_is_business(e),
        "is_verified": compat.read_is_verified(e),
        "bio": compat.read_biography(e),
        "biography": compat.read_biography(e),
        "full_name": compat.read_full_name(e),
        "avatar_url": compat.read_avatar_url(e),
        "country": e.get("country", ""),
        "is_private": e.get("is_private", profiles[handle].get("is_private", False)),
        "locationName": e.get("location_name", profiles[handle].get("locationName", "")),
        "engagement_rate": e.get("engagement_rate"),
    })
```

**Verificación:**
```bash
rg -n "followersCount|followsCount|postsCount|isBusinessAccount|profilePicUrl|fullName" \
   apps/api/app/workers/worker.py | wc -l
# Debe ser 0 tras refactor completo
```

---

### 🟡 #1 — LegacyCompatReader + ContractViolationLedger (Hito 31.3)

> **Archivos:** `packages/discovery/discovery/compat.py`, `packages/shared-core/shared_core/observability.py`
> **Tipo:** Nueva funcionalidad
> **Esfuerzo:** 3h
> **Corridas:** 0 (replay)
> **Costo:** $0

```python
# packages/shared-core/shared_core/observability.py (añadir)

class ContractViolationLedger:
    """Contador de contract.violation. Persiste en Redis con TTL 7d."""
    def __init__(self, redis_client=None):
        self._local_count = 0
        self._redis = redis_client
        self._key = "lens:contract_violation:count"

    async def record(self) -> None:
        self._local_count += 1
        if self._redis:
            try:
                await self._redis.incr(self._key)
            except Exception:
                pass

    async def get_total(self) -> int:
        if self._redis:
            try:
                return int(await self._redis.get(self._key) or 0)
            except Exception:
                pass
        return self._local_count

    async def reset(self) -> None:
        self._local_count = 0
        if self._redis:
            try:
                await self._redis.delete(self._key)
            except Exception:
                pass
```

**Criterio de retirada:** `contract.violation == 0` por 14 días consecutivos → eliminar `LegacyCompatReader` y `ContractViolationLedger`.

---

### 🟡 #2 — Hito 32.5: Freshness Policy (7 días)

> **Archivos:** `packages/discovery/discovery/freshness.py`, `apps/api/app/api/v1/discovery.py`, `supabase/migrations/00110_snapshot_freshness.sql`
> **Tipo:** Nueva funcionalidad
> **Esfuerzo:** 4h
> **Corridas:** 1 validación + 1 medición
> **Costo:** ~$1.14 + ~$1.58

**Migración `00110_snapshot_freshness.sql`:**

```sql
CREATE INDEX IF NOT EXISTS idx_metrics_snapshot_freshness
    ON influencer_metrics_snapshot(influencer_id, platform, snapshot_date DESC);

COMMENT ON COLUMN influencer_metrics_snapshot.snapshot_date
    IS 'Freshness window: snapshots <7 días reutilizables sin re-pago (Hito 32.5)';
```

**Módulo `packages/discovery/discovery/freshness.py`:**

```python
"""Hito 32.5 — Política de freshness de 7 días para enrichment."""
from datetime import datetime, timedelta, timezone

FRESHNESS_WINDOW_DAYS = 7

async def get_fresh_snapshot_or_none(
    handle: str,
    platform: str = "instagram",
) -> dict | None:
    """Devuelve snapshot fresco o None si debe enriquecerse."""
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=FRESHNESS_WINDOW_DAYS)
    rows = await railway_pg.select(
        table="influencer_metrics_snapshot",
        select="*",
        filters=[f"snapshot_date=gte.{cutoff.isoformat()}", f"platform=eq.{platform}"],
        order="snapshot_date.desc",
        limit=20,
    )
    for row in rows:
        sa = await railway_pg.select_one(
            table="influencer_social_accounts",
            select="handle",
            filters=[f"id=eq.{row['social_account_id']}"] if row.get("social_account_id")
                    else [f"influencer_id=eq.{row['influencer_id']}", f"platform=eq.{platform}"],
        )
        if sa and sa.get("handle", "").lower() == handle.lower():
            return row
    return None
```

**Integración pre-enrichment en `worker.py`** (antes del bloque de enrichment):

```python
from discovery.freshness import get_fresh_snapshot_or_none

handles_to_enrich_fresh = []
handles_skip_fresh = []
for h in handles_to_enrich:
    snap = await get_fresh_snapshot_or_none(h, platform="instagram")
    if snap:
        profiles[h].update({
            "follower_count": snap.get("follower_count"),
            "engagement_rate": snap.get("engagement_rate"),
            "avg_likes": snap.get("avg_likes"),
            "_from_snapshot": True,
        })
        handles_skip_fresh.append(h)
    else:
        handles_to_enrich_fresh.append(h)

await _run_update_metadata(run_id, {
    "profiles_skipped_fresh": len(handles_skip_fresh),
    "profiles_to_enrich": len(handles_to_enrich_fresh),
})
handles_to_enrich = handles_to_enrich_fresh
```

**Costo estimado:** ~30% handles repetidos entre runs → ~$0.20-0.40 USD ahorrados por corrida.

---

### 🟡 #3 — Hito 32.6: Brand Exclusion Table (Compliance Nestlé)

> **Archivos:** `supabase/migrations/00111_brand_excluded_handles.sql`, `apps/api/app/core/brand_exclusions.py`, `apps/api/app/workers/worker.py`
> **Tipo:** Nueva funcionalidad (compliance)
> **Esfuerzo:** 4h
> **Corridas:** 1 validación con brief Purina
> **Costo:** ~$1.14
> **⚠️ Pendiente decisión de negocio:** lista real de handles Nestlé/Purina VE

**Migración `00111_brand_excluded_handles.sql`:**

```sql
CREATE TYPE brand_exclusion_category AS ENUM (
    'BRAND_OWN', 'BRAND_VARIANT', 'STORE', 'FOUNDATION', 'COMPETITOR'
);

CREATE TABLE IF NOT EXISTS brand_excluded_handles (
    id              BIGSERIAL PRIMARY KEY,
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    handle_variant  TEXT NOT NULL,  -- 'dogchowve' (lower, sin @)
    category        brand_exclusion_category NOT NULL,
    reason          TEXT,
    added_by        UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (brand_id, handle_variant, category)
);

CREATE INDEX idx_brand_excl_brand ON brand_excluded_handles(brand_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_brand_excl_handle ON brand_excluded_handles(handle_variant) WHERE deleted_at IS NULL;

COMMENT ON TABLE brand_excluded_handles IS
    'Hito 32.6 — Exclusión determinista de handles por marca (L-05/L-03)';
```

**Módulo `apps/api/app/core/brand_exclusions.py`:**

```python
"""Hito 32.6 — Carga y aplicación de exclusiones por marca."""
async def get_excluded_handles_for_run(
    brand_id: str | None,
    plan_exclude_handles: list[str],
) -> dict[str, str]:
    exclusions: dict[str, str] = {}
    for h in plan_exclude_handles or []:
        exclusions[h.lower()] = "EXCLUDED_BRAND_OWN"
    if brand_id:
        rows = await railway_pg.select(
            table="brand_excluded_handles",
            select="handle_variant, category",
            filters=[f"brand_id=eq.{brand_id}", "deleted_at=is.null"],
        )
        for r in rows:
            reason_code = {
                "BRAND_OWN": "EXCLUDED_BRAND_OWN",
                "BRAND_VARIANT": "EXCLUDED_BRAND_OWN",
                "STORE": "EXCLUDED_STORE",
                "FOUNDATION": "EXCLUDED_FOUNDATION",
                "COMPETITOR": "EXCLUDED_BRAND_OWN",
            }.get(r["category"], "EXCLUDED_BRAND_OWN")
            exclusions[r["handle_variant"].lower()] = reason_code
    return exclusions
```

**Integración en `worker.py:1265-1285`** (reemplazar exclude_handles simple):

```python
from app.core.brand_exclusions import get_excluded_handles_for_run

brand_id_str = str(brief.brand_id) if getattr(brief, "brand_id", None) else None
exclusions = await get_excluded_handles_for_run(brand_id_str, plan.exclude_handles)
original_count = len(profiles)
for handle_lower, reason_code in exclusions.items():
    if handle_lower in profiles:
        profiles.pop(handle_lower)
        drop_profile(handle_lower, DropReason(reason_code), "scoring",
                    {"source": "brand_exclusion_table", "brand_id": brand_id_str},
                    ledger=drop_ledger)
```

**Auditoría compliance:**
```sql
SELECT run_id, ts, username, payload->>'brand_id' AS brand_id
FROM discovery_run_events
WHERE event = 'profile.dropped'
  AND reason_code IN ('EXCLUDED_BRAND_OWN', 'EXCLUDED_STORE', 'EXCLUDED_FOUNDATION')
  AND ts > NOW() - INTERVAL '30 days';
```

---

### 🔴 #4 — Fix Crítico: `drop_profile()` Persiste en `discovery_run_events`

> **Archivo:** `packages/shared-core/shared_core/observability.py`
> **Tipo:** Bug fix (Capa 6 de observabilidad rota)
> **Esfuerzo:** 3h
> **Corridas:** 0 (replay)
> **Costo:** $0
> **Bloquea:** Auditoría de Hito 32.6

**Problema:** La tabla `discovery_run_events` existe (migración 108) pero `drop_profile()` solo emite log — no persiste nada. Las queries de compliance devolverán cero filas.

```python
# En observability.py — modificar drop_profile()
async def drop_profile_persistent(
    username: str,
    reason: DropReason,
    stage: str,
    run_id: str,
    detail: dict | None = None,
    ledger: DropLedger | None = None,
) -> None:
    """Único punto de salida — persiste en DB + log."""
    if ledger is not None:
        ledger.record(reason)
    logger.info(
        RunEvent.PROFILE_DROPPED.value,
        username=username,
        reason=reason.value,
        stage=stage,
        run_id=run_id,
        **(detail or {}),
    )
    try:
        await railway_pg.insert("discovery_run_events", {
            "run_id": run_id,
            "event": RunEvent.PROFILE_DROPPED.value,
            "stage": stage,
            "reason_code": reason.value,
            "username": username,
            "payload": detail or {},
        })
    except Exception as e:
        logger.warning("drop_profile_persist_failed", error=str(e))
```

**Decisión:** ¿refactorizar `drop_profile()` existente para añadir persistencia, o crear `drop_profile_persistent` separado? Recomendación: modificar `drop_profile()` existente y pasar `run_id` via contextvars o como parámetro.

---

### 🟢 #5 — Eliminar Doble-Escritura CamelCase en Construction Dicts

> **Archivos:** `apps/api/app/workers/worker.py:380-925` (8 zonas)
> **Tipo:** Refactor calidad
> **Esfuerzo:** 3h
> **Corridas:** 0 (replay)
> **Costo:** $0

Eliminar las escrituras `profiles[handle]["followersCount"] = ...` que escriben el mismo valor en clave camelCase E snake_case. Dejar solo snake_case.

**Comando verificación:**
```bash
rg -n '"\w+":\s*p\.get\(' apps/api/app/workers/worker.py | wc -l
# Debe ser 0 tras refactor
```

---

### 🟢 #6 — Refactor Prefilter/Scoring a Snake_case

> **Archivos:** `apps/api/app/workers/worker.py:967-969, 1306, 1528`
> **Tipo:** Refactor calidad
> **Esfuerzo:** 2h
> **Corridas:** 0 (replay)
> **Costo:** $0

Reemplazar `p.get("followersCount") or p.get("follower_count")` por acceso directo a `p.get("follower_count")` usando `LegacyCompatReader`.

---

### 🟡 #7 — `_derive_tier` → 9 Sub-Tiers (Gap vs Plan Fable 5 §1.3)

> **Archivos:** `apps/api/app/api/v1/discovery.py`, `packages/discovery/discovery/tools/geo_boost.py`
> **Tipo:** Cambio de contrato (frontend-visible)
> **Esfuerzo:** 3h
> **Corridas:** 1 validación
> **Costo:** ~$1.14
> **⚠️ Pendiente confirmación:** ¿escala de 9 sub-tiers o mantener 4?

**Problema:** El plan Fable 5 §1.3 menciona "LWFA usa 9 sub-tiers" pero el código actual tiene solo 4 (`NANO/MICRO/MID/MACRO`). El enum `influencer_subtier` existe en `supabase/schema.sql:36`.

**Escala actual (4 niveles):**
```python
def _derive_tier(followers: int | None) -> str:
    if followers is None: return "NANO"
    if followers < 10_000: return "NANO"
    if followers < 100_000: return "MICRO"
    if followers < 500_000: return "MID"
    return "MACRO"
```

**Escala propuesta (9 niveles, si se confirma):**
```python
def _derive_tier(followers: int | None) -> str:
    if followers is None: return "UNKNOWN"
    if followers < 1_000: return "NANO_VERY_LOW"
    if followers < 5_000: return "NANO_LOW"
    if followers < 10_000: return "NANO_MID"
    if followers < 50_000: return "MICRO_LOW"
    if followers < 100_000: return "MICRO_MID"
    if followers < 250_000: return "MID_LOW"
    if followers < 500_000: return "MID_HIGH"
    return "MACRO"
```

**Acción requerida:** Confirmar con Ungar/Ignacio si se usa la escala de 9 sub-tiers o se mantiene la de 4.

---

### 🟢 #8 — Housekeeping: `deepseek-v3` en seed.sql y schema.sql

> **Archivos:** `supabase/seed.sql:246,261,270`, `supabase/schema.sql:501`
> **Tipo:** Housekeeping
> **Esfuerzo:** 30min
> **Corridas:** 0
> **Costo:** $0

```sql
-- seed.sql: actualizar default de 'deepseek-chat' a 'deepseek-v3'
-- schema.sql:501: actualizar default de ai_models
```

---

### 🟢 #9 — Tests `test_hito31_data_contract.py`

> **Archivo:** `apps/api/tests/test_hito31_data_contract.py`
> **Tipo:** CI gate
> **Esfuerzo:** 3h
> **Corridas:** 0 (CI local)
> **Costo:** $0

```python
class TestDataContract:
    def test_normalize_user_returns_none_for_missing(self):
        """_normalize_user devuelve None si follower_count ausente."""

    def test_normalize_user_snake_case_only(self):
        """_normalize_user retorna solo snake_case, sin camelCase."""

    def test_legacy_compat_reader_reads_both_formats(self):
        """LegacyCompatReader acepta followersCount y follower_count."""

    def test_contract_violation_ledger_counts(self):
        """ContractViolationLedger incrementa al leer formato legacy."""
```

---

### ⏸ #10 — Retirar LegacyCompatReader (Post-14 días con 0 violaciones)

> **Tipo:** Cleanup diferido
> **Esfuerzo:** 1h
> **Corridas:** 1 validación
> **Costo:** ~$1.14
> **Depende:** #1 + ventana de 14 días con `contract.violation == 0`

---

## Resumen de Esfuerzo y Costo Total

| # | Hito | Esfuerzo | Corridas | Costo |
|---|------|-----------|---------|-------|
| #0 | Fix regresión merge | 2h | 1 | ~$1.14 |
| #1 | LegacyCompatReader + ContractViolationLedger | 3h | 0 | $0 |
| #2 | Freshness policy 7d | 4h | 2 | ~$2.72 |
| #3 | Brand exclusion table | 4h | 1 | ~$1.14 |
| #4 | drop_profile persiste en DB | 3h | 0 | $0 |
| #5 | Eliminar doble-escritura camelCase | 3h | 0 | $0 |
| #6 | Refactor prefilter/scoring snake_case | 2h | 0 | $0 |
| #7 | _derive_tier → 9 sub-tiers | 3h | 1 | ~$1.14 |
| #8 | Housekeeping seed.sql/schema.sql | 30min | 0 | $0 |
| #9 | Tests Hito 31 | 3h | 0 | $0 |
| #10 | Retirar LegacyCompatReader (diferido) | 1h | 1 | ~$1.14 |
| **TOTAL** | | **~28.5h** | **6** | **~$7.42** |

**Saldo restante:** $43 - $7.42 ≈ **$35.58 USD** (~22 corridas de operación).

---

## Orden de Ejecución Óptimo

```
#0 (REGRESIÓN CRÍTICA) → #4 (persistencia drop_profile, prerrequisito auditoría)
         ↓
#1 (LegacyCompatReader) → habilita #2 y #3
         ↓
#2 (Freshness) antes de #3 (Brand Exclusion) — reduces ruido en auditoría
         ↓
#5 → #6 → #7 (refactors de calidad, aprovechan base correcta)
         ↓
#8 (housekeeping)
         ↓
#9 (tests CI gate)
         ↓
#10 (post-14 días ventana, diferido)
```

---

## Decisiones Pendientes de Negocio (No Técnicas)

1. **Lista real de handles Nestlé/Purina VE** para seed de `brand_excluded_handles`. El placeholder propuesto NO debe ejecutarse hasta firma de compliance.
2. **Threshold freshness: ¿7 vs 14 vs 30 días?** Sugerencia: parametrizable por `brand_id`.
3. **Escala de tiers: ¿4 niveles o 9 sub-tiers?** Afecta contrato API y frontend.
4. **Retención de snapshots >90 días:** ¿borrar? ¿365 días? ¿agregados mensuales?

---

## Criterios de Éxito Globales Post-Hitos

- [ ] `drop_profile()` persiste en `discovery_run_events` (Capa 6 operativa)
- [ ] `contract.violation == 0` por 14 días consecutivos → LegacyCompatReader retirado
- [ ] Freshness policy: handles con snapshot <7d no generan llamada HikerAPI
- [ ] Brand exclusion: cuenta propia de marca nunca llega a candidatos
- [ ] `_derive_tier` usa escala correcta (4 o 9 según decisión)
- [ ] `deepseek-v3` en seed.sql/schema.sql (alineado con config.py)
- [ ] ≥20 tests nuevos pasando (incluyendo anti-regresión Hito 29)
- [ ] Railway deploy exitoso en cada fase

---

## Comandos de Verificación Post-Deploy

```bash
# Verificar drop_profile persiste en DB:
psql $DATABASE_URL -c "SELECT COUNT(*) FROM discovery_run_events WHERE reason_code IS NOT NULL;"

# Verificar zero camelCase en worker.py:
rg -n "followersCount|followsCount|postsCount|isBusinessAccount" apps/api/app/workers/worker.py | wc -l

# Verificar freshness index:
psql $DATABASE_URL -c "\d influencer_metrics_snapshot" | grep idx_metrics

# Verificar brand_excluded_handles existe:
psql $DATABASE_URL -c "\d brand_excluded_handles"

# Run de prueba (~$1.14):
curl -X POST https://api.lawebcore.com/api/v1/discovery/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_name":"Purina Dog Chow","niches":["mascotas","perros"],"audience_countries":["VE"],"discovery_mode":"auto"}'

# Audit compliance exclusions:
psql $DATABASE_URL -c "SELECT username, reason_code, COUNT(*) FROM discovery_run_events WHERE reason_code LIKE 'EXCLUDED%' GROUP BY username, reason_code;"
```

---

## Para Cada Fase: Criterio de Éxito Antes de Pasar a la Siguiente

| # | Criterio |
|---|----------|
| **#0** | Merge enrichment lee snake_case; enrichment metadata visible en scoring |
| **#1** | `LegacyCompatReader` existe y lee ambos formatos; `ContractViolationLedger` registra |
| **#2** | Handles con snapshot <7d NO aparecen en `handles_to_enrich`; metadata muestra `profiles_skipped_fresh` |
| **#3** | Tabla `brand_excluded_handles` existe; query compliance devuelve filas |
| **#4** | `SELECT COUNT(*) FROM discovery_run_events WHERE event='profile.dropped'` > 0 |
| **#5** | 0 escrituras camelCase en worker.py:380-925 |
| **#6** | 0 lecturas camelCase en scoring loop |
| **#7** | `_derive_tier` devuelve sub-tiers correctos (4 o 9 según decisión) |
| **#8** | seed.sql y schema.sql tienen `deepseek-v3` como default |
| **#9** | `pytest apps/api/tests/test_hito31_data_contract.py` pasa |
| **#10** | `contract.violation == 0` por 14 días consecutivos |

---

## Documentos Actualizados por Este Plan

| Documento | Cambio |
|-----------|--------|
| `PLAN_MAIN_ALINEACION_LENS_2026-08-25.md` | Este archivo — estado actual + plan pendientes |
| `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` | Auditoría #17 (Claude Code Fable 5 análisis completo) |
| `docs/ARQUITECTURA_LENS.md` | Actualizar a v5.6 con Hitos 30-35 aplicados |
| `docs/LANZ_VERIFICACIONES_2026-08-25.md` | Resultado V0 completado; V1-V4 pendientes |
| `docs/13a_data_contract_discovery.md` | Data contract v1.0 (ya creado) |
| `docs/PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md` | Plan oficial Fable 5 (referencia) |

---

*Plan actualizado: 2026-08-26 por MiniMax M2.7/M3*
*Basado en análisis subagente explore post-commit `bd973c7`*
*Informe Lanz v1.2 + Plan Claude Code Fable 5*
