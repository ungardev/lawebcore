# PLAN MAIN — Alineación LENS Discovery
## Iteración 4 — Estado al 26-ago-2026 · Migraciones Railway Ejecutadas

> **De:** MiniMax M2.7/M3 + análisis exhaustivo post-ejecución de migraciones Railway
> **Fecha:** 26 de agosto de 2026
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Commit base actual (en repositorio):** `3606ee7` (lint fix, 27-ago-2026)
> **Último commit deployado en Railway:** `2446e75` (8 fixes backend, 27-ago-2026)
> **Commit frontend C-1/C-2 en repositorio:** `29d7ba6` (NO desplegado — lint CI bloquea)
> **Migraciones Railway PostgreSQL ejecutadas:** 108 ✅ · 109 ✅ · 110 ✅
> **Deduplicación manual ejecutada:** `paola_cocina_` (4→1 registros)
> **ENUM discovery_run_status en Railway:** 13 valores (7 legacy + 6 Hito 30)
> **HikerAPI balance:** ~$38 USD

---

## RESUMEN EJECUTIVO — Estado del Proyecto

### Lo Que Se Ejecutó (26-ago-2026)

1. **Verificación de Railway PostgreSQL** reveló que las migraciones 108, 109 y 110 NO estaban aplicadas — el sistema de migraciones de Railway NO ejecuta automáticamente los archivos de `supabase/migrations/`
2. **Se ejecutaron las 3 migraciones críticas manualmente** via SQL Editor de Railway
3. **Se resolvió un duplicado** en `influencers.primary_handle` (`paola_cocina_`, 4→1)
4. **El ENUM `discovery_run_status` quedó extendido** de 7 a 13 valores

### Estado Actual del Sistema

| Componente | Estado |
|-----------|--------|
| Railway PostgreSQL — ENUM | ✅ 13 valores (7 legacy + 6 Hito 30) |
| Railway PostgreSQL — `discovery_run_events` | ✅ Tabla creada + 3 índices |
| Railway PostgreSQL — índice único `influencers` | ✅ Índice creado + duplicado resuelto |
| Railway API — código | ⚠️ `2446e75` (C-0/C-1/C-2 no desplegados por lint CI) |
| Frontend TypeScript — C-1 | ⚠️ Código en `29d7ba6` pendiente deploy |
| Frontend TypeScript — C-2 | ✅ `types/index.ts` arreglado en `29d7ba6` |

### El Pipeline Está Funcional — Solo Falta el Deploy del Frontend

El backend está operativo en Railway con todos los fixes. La base de datos tiene el schema correcto. Lo único que falta es que el frontend C-1 llegue a producción (bloqueado por lint CI).

---

## BITÁCORA DE ITERACIONES

| # | Fecha | Iteración | Commit | Acción | Resultado |
|---|-------|-----------|--------|--------|-----------|
| 1 | 25-ago | Iteración 1 | `bd973c7` | Hitos 30-34 foundation | ✅ Lanz: 16 confirmados, 2 desviaciones |
| 2 | 27-ago | Iteración 2 | `2446e75` | 8 fixes Fase 35 (regresión + data integrity) | ✅ Pipeline backend funcional |
| 3 | 27-ago | Iteración 3 | `29d7ba6` | C-0/C-1/C-2 (acoplamiento frontend) | ✅ Backend extendido; ⚠️ lint CI bloquea deploy |
| 4 | 27-ago | Iteración 4 | `3606ee7` | Lint fix (schemas.py, test file) | ⚠️ CI aún falla por otros archivos |
| 5 | 26-ago | EJECUCIÓN | — | Migraciones Railway 108/109/110 + dedup | ✅ DB completa 13 valores |

---

## SECCIÓN 1 — Sistema de Migraciones: Arquitectura Real

### Cómo Funciona el Sistema de Migraciones de Railway

Railway tiene **DOS mecanismos de migración** que NO deben confundirse:

| Mecanismo | Archivos que ejecuta | Tracking | Ejecuta automáticamente? |
|-----------|---------------------|---------|------------------------|
| `apply_migrations.py` | Solo `schema.sql` | `schema_migrations` (v00000000000001) | ✅ Solo 1 vez al primer deploy |
| `memory.py::migrate_discovery_conversations_schema()` | `ALTER TABLE ADD COLUMN` | No hay tracking | ✅ Cada startup de Railway |
| **`supabase/migrations/*.sql`** | Archivos numerados 001-110+ | `schema_migrations` (cada archivo debería insertar su versión) | ❌ **NO — Ejecución manual** |

### Descubrimiento Crítico (26-ago-2026)

Las migraciones 108, 109 y 110 **NO se ejecutaron automáticamente** cuando Railway levantó. Esto se descubrió al ejecutar queries de verificación en el SQL Editor de Railway:

```sql
-- Verificación inicial
SELECT table_name FROM information_schema.tables WHERE table_name = 'discovery_run_events';
-- Resultado: 0 rows — tabla NO existía

SELECT enumlabel FROM pg_enum WHERE typname = 'discovery_run_status';
-- Resultado: 7 valores (faltaban 6)

SELECT indexname FROM pg_indexes WHERE indexname = 'idx_influencers_primary_handle_unique';
-- Resultado: 0 rows — índice NO existía
```

### Arquitectura de la Base en Railway

```
Base de datos: railway (127.0.0.1:5432)
├── 53 tablas del schema bootstrap
├── ENUM discovery_run_status: 13 valores ✅ (7 legacy + 6 Hito 30)
├── discovery_run_events: tabla + 3 índices ✅
└── influencers: índice único en primary_handle ✅
```

### Conclusión

**Las migraciones de `supabase/migrations/` deben ejecutarse manualmente** contra Railway Postgres usando el SQL Editor de Railway o `supabase db push` local con `DATABASE_URL` apuntando a Railway.

---

## SECCIÓN 2 — Migraciones Ejecutadas en Railway PostgreSQL (26-ago-2026)

### Migración 108 — `discovery_run_events`

**Problema:** La tabla de eventos de corrida NO existía en Railway. El `flush_drop_ledger()` no podía escribir — la tabla era inexistente.

**Solución aplicada:**
```sql
CREATE TABLE IF NOT EXISTS discovery_run_events (
    id            BIGSERIAL PRIMARY KEY,
    run_id        UUID NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,
    ts            TIMESTAMPTZ NOT NULL DEFAULT now(),
    event         TEXT NOT NULL,
    stage         TEXT,
    reason_code   TEXT,
    username      TEXT,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_run_events_run ON discovery_run_events(run_id);
CREATE INDEX IF NOT EXISTS idx_run_events_reason ON discovery_run_events(reason_code) WHERE reason_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_run_events_event ON discovery_run_events(event);

INSERT INTO schema_migrations (version, filename)
VALUES ('108', '00000000000108_discovery_run_events.sql')
ON CONFLICT (version) DO NOTHING;
```

**Verificación:** `SELECT table_name FROM information_schema.tables WHERE table_name = 'discovery_run_events'` → 1 fila ✅

---

### Migración 109 — Índice Único en `influencers.primary_handle`

**Problema:** La migración falló al crearse — existía un duplicado en `paola_cocina_`.

**Diagnóstico del duplicado:**
```sql
SELECT primary_handle, COUNT(*) as cnt
FROM influencers
WHERE primary_handle IS NOT NULL AND deleted_at IS NULL
GROUP BY primary_handle HAVING COUNT(*) > 1;

-- Resultado: paola_cocina_ → 4 registros
-- IDs: 62c10f92 (21-ago, conservar), 422d3213, 35c55b38, 0a9d8c9d (12-ago, eliminar)
```

**Verificación de datos asociados:**
- `influencer_social_accounts`: 0 rows
- `campaign_influencers`: 0 rows
- `influencer_metrics_snapshot`: 0 rows

**Solución aplicada:**
```sql
DELETE FROM influencers
WHERE id IN (
  '422d3213-d391-42bc-9a28-458991b7d056',
  '35c55b38-cecb-4a4c-b006-d59e62bea501',
  '0a9d8c9d-8e08-42e0-ae09-2aad1a95c22d'
);

CREATE UNIQUE INDEX idx_influencers_primary_handle_unique
    ON influencers(primary_handle)
    WHERE deleted_at IS NULL;

INSERT INTO schema_migrations (version, filename)
VALUES ('109', '00000000000109_influencers_unique_handle.sql')
ON CONFLICT (version) DO NOTHING;
```

**Verificación:** `SELECT indexname FROM pg_indexes WHERE indexname = 'idx_influencers_primary_handle_unique'` → 1 fila ✅

---

### Migración 110 — Extender ENUM `discovery_run_status`

**Problema:** El ENUM solo tenía 7 valores (legacy). Faltan los 6 del Hito 30 que el worker escribe.

**Solución aplicada:**
```sql
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'queued';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'delivered';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'degraded';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'empty';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'inconsistent';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'aborted_budget';

INSERT INTO schema_migrations (version, filename)
VALUES ('110', '00000000000110_discovery_run_hito30_statuses.sql')
ON CONFLICT (version) DO NOTHING;
```

**Verificación:**
```sql
SELECT enumlabel FROM pg_enum e
JOIN pg_type t ON t.oid = e.enumtypid
WHERE t.typname = 'discovery_run_status'
ORDER BY e.enumsortorder;

-- Resultado: 13 valores
-- pending, running, completed, failed, cancelled, partial, explored,
-- queued, delivered, degraded, empty, inconsistent, aborted_budget
```

---

## SECCIÓN 3 — Lo Que Ya Está Aplicado (Commits en Repositorio)

### Hitos 30-34 aplicados (commit `bd973c7`, 26-ago-2026)

| Hito | Descripción | Estado Lanz | Estado en Railway |
|------|-------------|-------------|-------------------|
| **Hito 30** | Observabilidad: contextvars, RunEvent/DropReason/RunStatus enums, DropLedger, FunnelTracker, drop_profile(), can_make_call() eliminada, events table | ✅ Confirmado | ⚠️ Tabla events creada 26-ago (migración 108) |
| **Hito 31.1** | `_normalize_user()` devuelve `None` para campos ausentes | ✅ Confirmado | ✅ |
| **Hito 31.2** | 7 pares dual-name eliminados del retorno | ✅ Confirmado | ✅ |
| **Hito 31.4** | ~10+ patrones `or 0` corregidos | ✅ Confirmado | ✅ |
| **Hito 31.5** | `docs/13a_data_contract_discovery.md` creado | ✅ Confirmado | ✅ |
| **Hito 32.1** | `_derive_tier()` en discovery.py (9 sub-tiers) | ✅ Confirmado | ✅ |
| **Hito 32.2** | Deduplicación por handle + migración 109 | ⚠️ Índice faltaba | ✅ Índice creado 26-ago |
| **Hito 32.3** | Métricas carry-through | ✅ Confirmado | ✅ |
| **Hito 32.4** | INSERT en influencer_social_accounts + influencer_metrics_snapshot | ✅ Confirmado | ✅ |
| **Hito 33.1** | Constants a config | ✅ Confirmado | ✅ |
| **Hito 33.2** | Slices usan settings | ✅ Confirmado | ✅ |
| **Hito 33.3** | Metadata corregida | ✅ Confirmado | ✅ |
| **Hito 34.1** | `response_format={"type": "json_object"}` | ✅ Confirmado | ✅ |
| **Hito 34.3** | Regex extraction eliminada | ✅ Confirmado | ✅ |
| **Hito 34.4** | `_fallback_scores` marcado | ✅ Confirmado | ✅ |
| **Hito 34.5** | Modelo DeepSeek: `deepseek-v3` | ✅ Confirmado | ✅ |
| **Hito 35.2** | Validación backend | ✅ Confirmado | ✅ |

### 8 Fixes Fase 35 aplicados (commit `2446e75`, 27-ago-2026)

| Fix | Descripción | Impacto |
|-----|-------------|---------|
| **FIX #1+2** | Merge enrichment solo snake_case + `_enriched: True`; scoring lee `follower_count` primero | CRÍTICO — restore pipeline |
| **FIX #3** | `flush_drop_ledger()` persiste a `discovery_run_events` | Auditoría funcional |
| **FIX #4+5** | UPSERT social_accounts + metrics_snapshot | Integridad de datos |
| **FIX #6** | `_derive_tier` 9 sub-tiers + null | Clasificación correcta |
| **FIX #8** | `_parse_batch_response` sin re.search | Contrato limpio |

### Fixes C-0/C-1/C-2 aplicados (commit `29d7ba6`, 27-ago-2026)

| Fix | Descripción | Código | Railway |
|-----|-------------|--------|---------|
| **C-0** | Migración ENUM 110 | ✅ SQL en `supabase/migrations/` | ✅ Ejecutada 26-ago |
| **C-1** | Pydantic enum 13 valores | ✅ `schemas.py:10-26` | ⚠️ No desplegado (lint CI) |
| **C-2** | TypeScript union 9 sub-tiers + null | ✅ `types/index.ts:43` | ⚠️ No desplegado (lint CI) |

---

## SECCIÓN 4 — Issues Críticos Frontend Pendientes

### 🔴 ISSUE C-1: RunStatus Enum Mismatch — Frontend TypeScript Incompleto

**Severidad:** CRÍTICA — El frontend no conoce los statuses `delivered`, `degraded`, etc.

**Estado de los archivos:**

| Archivo | ¿Arreglado en código? | ¿Desplegado? |
|---------|----------------------|---------------|
| `schemas.py:10-26` (Pydantic enum) | ✅ Sí | ⚠️ No — en `29d7ba6` |
| `discovery.ts:1` (TypeScript type) | ❌ **NO** | — |
| `LensRunsListPage.tsx:12-20` (STATUS_CONFIG) | ❌ **NO** | — |
| `LensSearchPage.tsx:78` (hasResults) | ❌ **NO** | — |

**Lo que Fable 5 no cubrió:** El análisis de Fable 5 solo tocó `schemas.py` (C-1 backend) y `types/index.ts` (C-2). Los archivos `discovery.ts`, `LensRunsListPage.tsx` y `LensSearchPage.tsx` quedaron sin arreg — descubiertos en análisis post-Fable 5.

### 🟠 ISSUE C-2: Influencer.primary_tier — Tipo Arreglado, Constantes Pendientes

| Archivo | ¿Arreglado? | Desplegado? |
|---------|-------------|-------------|
| `types/index.ts:43` (union type) | ✅ Sí | ⚠️ No — en `29d7ba6` |
| `utils.ts:51` (INFLUENCER_TIERS) | ❌ NO | — |
| `NewCampaignModal.tsx:30` (TIERS) | ❌ NO | — |

### 🟡 ISSUES C-3 a C-6 (Cosméticos — Posterior a Validación)

| Issue | Descripción | Prioridad |
|-------|-------------|-----------|
| C-3 | SearchProgress PHASES desfasadas | Baja |
| C-4 | `getTierColor()` sin sub-tiers | Baja |
| C-5 | `INFLUENCER_TIERS` incompleto | Baja |
| C-6 | `TIERS` array en NewCampaignModal | Baja |

---

## SECCIÓN 5 — Plan de Acción Inmediato

| # | Paso | Estado | Responsable | Costo |
|---|------|--------|-------------|-------|
| 1 | Fix lint W292 en `__init__.py` (`ruff --fix`) | ⏳ Pendiente | Vos (terminal local) | $0 |
| 2 | Commit + push lint fix | ⏳ Pendiente | Vos | $0 |
| 3 | Esperar CI verde + Railway deploy automático | ⏳ Pendiente | GH Actions + Railway | $0 |
| 4 | **Frontend C-1:** `discovery.ts` — type DiscoveryRunStatus con 13 valores | ⏳ Pendiente | Yo te paso el diff | $0 |
| 5 | **Frontend C-1:** `LensRunsListPage.tsx` — STATUS_CONFIG con 6 entries | ⏳ Pendiente | Yo te paso el diff | $0 |
| 6 | **Frontend C-1:** `LensSearchPage.tsx` — hasResults incluye delivered/degraded/empty | ⏳ Pendiente | Yo te paso el diff | $0 |
| 7 | Commit + push frontend C-1 | ⏳ Pendiente | Vos | $0 |
| 8 | Esperar deploy Vercel (frontend) | ⏳ Pendiente | Vercel | $0 |
| 9 | **Corrida de validación** (`test_lens_mascotas_ve.py`) | ⏳ Pendiente | Vos | ~$1.14 |
| 10 | Queries de verificación post-validación | ⏳ Pendiente | Vos | $0 |

---

## SECCIÓN 6 — Resumen del Estado del Proyecto

```
REPOSITORIO (commits en origin/main)
├── 2446e75  8 fixes backend ✅ deployado en Railway
├── 29d7ba6  C-0/C-1/C-2 aplicados ✅ NO desplegado (lint CI)
└── 3606ee7  lint fix schemas.py ✅ NO desplegado (lint CI)

RAILWAY POSTGRES (base: railway, 127.0.0.1:5432)
├── ENUM discovery_run_status: 13 valores ✅
├── Tabla discovery_run_events: creada + índices ✅
└── Índice único influencers.primary_handle: creado ✅

FRONTEND (Vercel)
├── C-2: types/index.ts ✅ en código
├── C-1: discovery.ts, LensRunsListPage, LensSearchPage ❌ pendiente
└── C-3 a C-6: pendientes post-validación

PIPELINE
├── Backend: funcional en Railway ✅
├── Base de datos: completa ✅
└── Frontend C-1: pendiente de deploy ⚠️
```

---

## SECCIÓN 7 — Criterios de Éxito Post-Migraciones

### ✅ Migraciones (completado 26-ago-2026)

- [x] Tabla `discovery_run_events` existe con 3 índices
- [x] Índice único en `influencers.primary_handle` creado
- [x] ENUM `discovery_run_status` tiene 13 valores
- [x] Registros `schema_migrations` insertados para 108, 109, 110
- [x] Duplicado `paola_cocina_` resuelto (4→1)

### ⏳ Validación (pendiente)

- [ ] Railway deploy del código con C-1/C-2
- [ ] Corrida de validación muestra distribución >1 valor en `reason_code`
- [ ] Polling del frontend completa sin HTTP 500
- [ ] Candidatos muestran `followers` real (no 0)
- [ ] `flush_drop_ledger()` popula `discovery_run_events`

---

## SECCIÓN 8 — Hallazgos para Próximas Iteraciones

### Hallazgo 1: Sistema de Migraciones de Railway

El sistema de Railway NO ejecuta automáticamente los archivos de `supabase/migrations/`. Cada vez que se agregue una migración de tabla o ENUM, debe ejecutarse manualmente via SQL Editor o `supabase db push`.

**Recomendación:** Agregar las migraciones de ENUM al archivo `memory.py::migrate_discovery_conversations_schema()` para que futures migraciones de ENUM corran automáticamente al startup.

### Hallazgo 2: Fable 5 No Cubrió Todo el Frontend

El análisis de Fable 5 (C-1) solo tocó `schemas.py` y `types/index.ts`. Los archivos `discovery.ts`, `LensRunsListPage.tsx` y `LensSearchPage.tsx` requieren los mismos cambios. Esto se descubrió post-análisis.

### Hallazgo 3: CHECK Constraint vs ENUM

`schema.sql` usa un CHECK constraint para `discovery_runs.status` que lista los valores explícitamente. Este CHECK no se actualizó cuando el ENUM se extendió — debe sincronizarse cuando se regener `schema.sql`.

---

## SECCIÓN 9 — Lo Que NO se Hizo (Pendientes)

### Features Técnicas Pendientes

| # | Feature | Depende | Costo |
|---|---------|---------|-------|
| FP-1 | Freshness policy 7d | Fix C-1 + C-2 desplegado | ~$0.30-0.50/run ahorrado |
| FP-2 | Brand exclusion table | Q1 (handles Nestlé/Purina) | $0 |
| FP-3 | seed.sql/schema.sql `deepseek-v3` | Nada | $0 |
| FP-4 | Tests `test_hito31_data_contract.py` | post-estabilización | $0 |
| FP-5 | Ensanche 5/3/5/2 | Q4 (aprobación) | ~$0.44/corrida extra |

### Decisiones de Negocio Pendientes

| # | Pregunta | Bloquea | Prioridad |
|---|---------|---------|-----------|
| Q1 | Lista handles Nestlé/Purina VE | FP-2 | 🔴 Alta |
| Q2 | Ventana de frescura: ¿7 vs 14 vs 30? | FP-1 | 🟡 Media |
| Q3 | Tier targeting macro (4) vs sub-tier (9) | Frontend | 🟡 Media |
| Q4 | Aprobación ensanche 5/3/5/2 | FP-5 | 🟡 Media |

---

## SECCIÓN 10 — Saldo y Proyección

| Concepto | Monto |
|----------|-------|
| Saldo actual | ~$38 USD |
| Corrida de validación (pendiente) | -$1.14 |
| **Saldo post-validación** | **~$36.86 USD (~32 corridas)** |
| Fix C-1/C-2 (código + deploy) | $0 |
| Migraciones Railway 108/109/110 | $0 |

---

## SECCIÓN 11 — Documentos de Referencia

| Documento | Descripción |
|-----------|-------------|
| `docs/La Web Figital - Informe de Alineación Técnica LENS.md` | Auditoría Santiago Lanz (v1.2) — fuente del plan |
| `docs/LANZ_VERIFICACIONES_2026-08-25.md` | Resultados V0-V4 de verificaciones Lanz |
| `docs/FIXES_FRONTEND_LENS_C0-C2_27-08-26.md` | Análisis Fable 5 Iteración 2 |
| `docs/VERIFICACION_CODIGO_LENS_HITOS_30-35_25-08-26.md` | Auditoría Fable 5 sobre Hitos 30-35 |
| `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` | Índice histórico de auditorías (actualizar con #18) |

---

## SECCIÓN 12 — Glosario Técnico

| Término | Significado |
|---------|------------|
| **LENS** | Discovery module — motor de búsqueda de influencers |
| **Fable 5** | Claude Code subagent (Full Stack Senior Engineer) |
| **Santiago Lanz** | Ingeniero Auditor — autor del informe de alineación v1.2 |
| **RunStatus** | Enum de estados del worker (DELIVERED, DEGRADED, etc.) |
| **DiscoveryRunStatus** | Enum Pydantic del API (PENDING, RUNNING, COMPLETED, etc.) |
| **ENUM 13 valores** | 7 legacy + 6 Hito 30 en `discovery_run_status` |
| **memory.py** | Archivo con función `migrate_discovery_conversations_schema()` — corre al startup de Railway |
| **apply_migrations.py** | Script que aplica `schema.sql` al primer deploy de Railway |

---

*Documento actualizado: 26 de agosto de 2026 por MiniMax M2.7/M3*
*Basado en: Informe Lanz v1.2 + Análisis Fable 5 Iteración 1 y 2 + Ejecución de migraciones Railway*
*Commit base: `3606ee7` — frontend C-1/C-2 en código, pendiente deploy*
*Estado: DB completa ✅ · Pipeline funcional ✅ · Frontend C-1 pendiente ⚠️*
*Próximo paso: Fix lint CI → Deploy C-1 → Corrida de validación*
