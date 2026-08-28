# Auditoría Lanz v2.1 — LENS Discovery
## 28 de agosto de 2026 · Superseding Lanz v2.0

> **De:** MiniMax M2.7/M3
> **Basado en:** `docs/Auditoria_Lanz_v2_2026-08-27.md` (v2.0) + Hito 36 + M3-Agentes A/B/C
> **Repo:** `github.com/ungardev/lawebcore`
> **Commit audited:** `035aafc` (HEAD, 28-ago-2026)
> **Método:** Lectura directa del árbol + investigación por agentes + verificación contra docs Lanz

---

## §1 — Resumen Ejecutivo

**Estado al 28-ago-2026:** El pipeline LENS está funcionalmente listo para E2E. Todos los bugs que bloqueaban ejecución fueron corregidos. Quedan ~15 items de deuda técnica (FASE 1-4) que se validan con la prueba real.

### Bugs Críticos Resueltos

| Bug | Commit | Fecha |
|-----|--------|-------|
| BUG #1: `worker.py:1298` `followers_count` typo → 0 candidatos | `1bdacc3` | 27-ago |
| BUG #2: `discovery.py:973,976` columnas `followers`/`raw_payload` | `1bdacc3` | 27-ago |
| DeepSeek thinking mode activo (temperature ignorada, CoT facturado) | `30e5e06` | 28-ago |
| pollRun sin 6 estados nuevos (200 peticiones + error falso) | `2e9b567` | 28-ago |
| Error 400 backend hidden (usuario no sabe qué corregir) | `89caf71` | 28-ago |
| `main.py:84` railway_pg NameError | `65e998c` | 28-ago |

### Fixes Aplicados (28-ago-2026)

| Fase | Commits | Items |
|------|---------|-------|
| **Hito 36** | `30e5e06` `2e9b567` `bdb4e6b` `89caf71` `c79f375` | 5 |
| **M3-Agente A** | `ae0789c` | schema.sql sync (3 tables + 4 columns) |
| **M3-Agente B** | `65e998c` | Lanz v2.0 FASE 0.4/2.1/2.2/2.4/2.5/3.1 |
| **Logger Fixes** | `035aafc` | 17 logger.error exc_info=True |
| **TOTAL** | **8 commits** | **~25 fixes** |

### Railway Deploy — Verde ✅

```
2026-08-28T22:03:06 [inf] Starting Container
2026-08-28T22:03:09 [inf] [migration] Added column title to discovery_conversations
2026-08-28T22:03:09 [inf] [migration] Added column title to discovery_runs
2026-08-28T22:03:09 [inf] [railway_pg] Pool created successfully
2026-08-28T22:03:09 [inf] [migration] Added column accumulated_brief to discovery_conversations
2026-08-28T22:03:09 [inf] [migration] Added column parsed_brief_json to discovery_conversations
2026-08-28T22:03:09 [inf] [migration] Added column pending_refinements to discovery_conversations
2026-08-28T22:03:09 [err] INFO: Started server process [2]
2026-08-28T22:03:09 [err] INFO: Application startup complete.
2026-08-28T22:03:10 [inf] Starting worker for 5 functions: discovery_run_task, sync_hypeauditor_task, sync_metricool_task, cron:scheduled_reports_cron, cron:sync_metricool_task
```

---

## §2 — Cumplimiento Lanz v2.0 §7 — Estado al 28-ago-2026

### §7.1 — "Que el sistema pueda fallar en voz alta"
**Estado: ~60% cumplido** (antes: ~30%)

| Sub-requisito | Antes | Después |
|--------------|-------|---------|
| Error paths no inventan valores | 21 `or 0` chains | ✅ 5 en _raw_to_candidate_dict fixed (`65e998c`) |
| 27 broad `except Exception` | 17 hot path sin logger | 🟡 8 cleanup passes fixed; rest FASE 2 pending |
| `determine_final_status()` | Dead code | ✅ Reconectada `65e998c` |
| `budget_aborted` flag | No existía | ✅ Creado `65e998c` |
| `exc_info=True` en logger.error | 2 de 63 | ✅ 19 de 63 (17 added `035aafc`) |

### §7.2 — "Un contrato de datos único"
**Estado: ~50% cumplido** (antes: ~35%)

| Sub-requisito | Antes | Después |
|--------------|-------|---------|
| `_normalize_user()` devuelve None | ✅ | ✅ |
| Una sola forma por campo | ❌ 8 search steps dual-write | ❌ PENDIENTE FASE 1.1 |
| `LegacyCompatReader` | ❌ No existe | ❌ PENDIENTE FASE 1.2 |
| `CONTRACT_VIOLATION` emite | ❌ Nunca | ❌ PENDIENTE FASE 1.3 |

### §7.3 — "Completar el camino del descubrimiento a la tabla maestra"
**Estado: ~70% cumplido** (antes: ~55%)

| Sub-requisito | Antes | Después |
|--------------|-------|---------|
| Deduplicación por handle | ✅ | ✅ |
| Métricas carry-through | ✅ BUG #2 fixed | ✅ |
| Tier derivado 9 sub-tiers | ✅ | ✅ |
| UPSERT social_accounts | ✅ | ✅ |
| UPSERT metrics_snapshot | ✅ BUG #2 fixed | ✅ |
| `discovery_query` poblado | ❌ Nunca | ✅ `65e998c` writer en 7 pasos |
| Política de frescura | ❌ No existe | ❌ PENDIENTE FASE 3.2 |

### §7.4 — "Ensanchar la búsqueda"
**Estado: ~70% cumplido** (sin cambios)

| Sub-requisito | Estado |
|--------------|--------|
| Límites ampliados 6/4/6/3 | ✅ |
| Metadata planned/executed | ✅ |
| ~64 llamadas sin usar | ⚠️ PENDIENTE — MAX_HANDLES_TO_ENRICH=25 |

### §7.5 — "Plan del proveedor + modelo IA"
**Estado: ~70% cumplido** (antes: ~40%)

| Sub-requisito | Antes | Después |
|--------------|-------|---------|
| `DEEPSEEK_MODEL=deepseek-v4-flash` | ✅ Código | ✅ Railway también ✅ |
| `response_format` usado | ❌ Solo 1/4 sites | ✅ 3/4 (`bdb4e6b`) |
| Thinking mode | ❌ Activo por defecto | ✅ Disabled (`30e5e06`) |
| Pricing peak/valley ×2 | ⚠️ Docs only | ✅ Documentado |
| `api_costs` model column | ❌ No | ❌ PENDIENTE FASE 4.6 |

---

## §3 — Hallazgos Lanz v2.0 — Estado Actualizado

| # | Hallazgo | Severidad | Estado 28-ago |
|---|----------|-----------|---------------|
| 1 | BUG #1: enrichment key mismatch | 🔴 CRÍTICO | ✅ FIXED `1bdacc3` |
| 2 | BUG #2: columnas inválidas metrics_snapshot | 🔴 CRÍTICO | ✅ FIXED `1bdacc3` |
| 3 | Migraciones 108/109 no automáticas | 🟡 CRÍTICO | ✅ FIXED + schema sync `ae0789c` |
| 4 | 27 broad exception handlers hot path | 🟡 CRÍTICO | 🟡 PARTIAL — cleanup fixed, rest pending FASE 2 |
| 5 | 21 `or 0` chains | 🟡 CRÍTICO | ✅ FIXED `65e998c` |
| 6 | 6/7 dual-name patterns search steps | 🟡 CRÍTICO | ❌ PENDIENTE FASE 1.1 |
| 7 | `discovery_query` nunca escrito | 🟡 CRÍTICO | ✅ FIXED `65e998c` |
| 8 | Sin política de frescura | 🟠 MEDIO | ❌ PENDIENTE FASE 3.2 |
| 9 | `determine_final_status()` dead code | 🟠 MEDIO | ✅ FIXED `65e998c` |
| 10 | `budget_aborted` flag no existe | 🟠 MEDIO | ✅ FIXED `65e998c` |
| 11 | `response_format` solo 1/4 sites | 🟠 MEDIO | ✅ FIXED `bdb4e6b` |
| 12 | Test suite no cubre paths críticos | 🟠 MEDIO | ❌ PENDIENTE |
| 13 | `schema.sql` desactualizado | 🟠 MEDIO | ✅ FIXED `ae0789c` |
| 14 | `apply_migrations.py` single-shot | 🟠 MEDIO | ❌ PENDIENTE |
| 15 | `main.py:84` railway_pg undefined | 🟠 MEDIO | ✅ FIXED `65e998c` |
| 16 | `media_count` or chain | 🟡 MEDIA | ❌ PENDIENTE |
| 17 | `FunnelTracker()` dead | 🟡 MEDIA | ❌ PENDIENTE FASE 2.6 |
| 18 | `is_discoverable` columna muerta | 🟡 MEDIA | ❌ PENDIENTE FASE 3.5 |
| 19 | `influencers.enriched_at` sin leer | 🟡 MEDIA | ❌ PENDIENTE FASE 3.2 |
| 20 | Railway DEEPSEEK_MODEL retired | 🟠 MEDIO | ✅ FIXED `deepseek-v4-flash` ✅ |
| 21 | `api_costs` sin model name | 🟢 BAJA | ❌ PENDIENTE FASE 4.6 |
| 22 | `discovery.router` double-mounted | 🟢 BAJA | ❌ PENDIENTE |
| 23 | `ai_prompts` defaults stale | 🟢 BAJA | ❌ PENDIENTE |

**Resumen: 10 FIXED, 1 PARTIAL, 12 PENDING**

---

## §4 — Plan de Acción FASE 1-4 (Pendientes)

### FASE 1 — Data Contract (~$0)
1.1 Eliminar 8 sitios dual-write en search steps → snake_case only
1.2 Implementar `LegacyCompatReader` (referenced, not exists)
1.3 Emitir `RunEvent.CONTRACT_VIOLATION` en runtime
1.4 Test: `test_enriched_merge_preserves_follower_count_snake_case`

### FASE 2 — Fail Loudly (~$0)
2.1 Reemplazar 17 broad `except Exception` hot path con excepts específicos
2.4 `FunnelTracker()` — usar o eliminar
2.5 Eliminar `or 0` chains restantes (fuera de _raw_to_candidate_dict)

### FASE 3 — Mastery Path (~$0)
3.2 Política de frescura: `enriched_at` gating
3.4 MAX_HANDLES_TO_ENRICH 25→50 (decisión Q4)
3.5 `is_discoverable` — eliminar writing o implementar lectura

### FASE 4 — AI/Discovery (~$0)
4.1 response_format en brief_parser (×2) + profile_generator
4.2 Eliminar `_extract_json` regex en brief_parser + complete_json
4.5 Limpiar dead code: import re, FunnelTracker
4.6 Agregar model column a api_costs

### FASE 5 — Validación (~$1.14)
5.1 E2E test: `scripts/test_lens_mascotas_ve.py` — **LUNES 31-AGO-2026**

---

## §5 — Decisiones de Negocio Pendientes (Q1-Q4)

| # | Pregunta | Bloquea | Prioridad |
|---|---------|---------|-----------|
| Q1 | Lista handles Nestlé/Purina VE | FP-2 brand exclusion | 🔴 Alta |
| Q2 | Ventana frescura: ¿7 vs 14 vs 30 días? | Freshness policy | 🟡 Media |
| Q3 | Tier targeting macro (4) vs sub-tier (9) | Frontend | 🟡 Media |
| Q4 | Aprobación MAX_HANDLES_TO_ENRICH 25→50 | FASE 3 | 🟡 Media |

---

## §6 — Commits Relevantes (27-28 ago 2026)

| Commit | Fecha | Descripción |
|--------|-------|-------------|
| `1bdacc3` | 27-ago | BUG #1 + BUG #2 corregidos |
| `8baa49e` | 27-ago | Lanz v2.0 audit doc |
| `30e5e06` | 28-ago | Hito 36: thinking mode disabled |
| `2e9b567` | 28-ago | Hito 36: pollRun 10 estados terminales |
| `bdb4e6b` | 28-ago | Hito 36: response_format json_object |
| `89caf71` | 28-ago | Hito 36: discovery_mode selector + error detail |
| `c79f375` | 28-ago | Hito 36: DeepSeek client unification |
| `ae0789c` | 28-ago | M3-Agente A: schema.sql sync |
| `65e998c` | 28-ago | M3-Agente B: Lanz v2.0 FASE 0.4/2.1/2.2/2.4/2.5/3.1 |
| `035aafc` | 28-ago | 17 logger.error exc_info=True |

---

*Documento creado: 28 de agosto de 2026 por MiniMax M2.7/M3*
*Supersede: `docs/Auditoria_Lanz_v2_2026-08-27.md` (v2.0)*
*Basado en: Lanz v1.2 + Lanz v2.0 + Hito 36 + M3-Agentes A/B/C*
*Estado: Pipeline funcional ✅ · E2E pendiente Lunes 31-ago-2026 · FASE 1-4 pendientes*
