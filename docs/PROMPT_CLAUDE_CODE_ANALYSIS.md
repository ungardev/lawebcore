# PROMPT_CLAUDE_CODE_ANALYSIS — Índice de Auditorías LENS

> **Última actualización:** 2026-09-04
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Hito actual:** Hito 36 completo ✅ · M3-Agente A/B/C completos ✅ · 17 logger fixes ✅ · Funnel Invariant fix ✅ · Claude Code Fable 5 P0-1..P0-4 ✅ · `644c513` B1/B2/B3 fixed ✅ · `7ce50da` credentials removed ✅ · **FIXES PRE-E2E N-1..N-4 aplicados (cliente HikerAPI alineado al OpenAPI spec)** ✅ · **E2E ❌ PENDIENTE (EXPLORAR primero, luego AUTO)**
> **HikerAPI balance:** ~$35 USD restantes · Pre-flight ahora FUNCIONAL (`/sys/balance`)
> **E2E Test:** ❌ FALLÓ run `10a59ecf` — 188 handles → 0 candidatos · B1/B2/B3 + N-1..N-4 fixed · E2E post-fixes pendiente
> **NUEVO (04-sep, tarde):** Auditoría exhaustiva del pipeline contra OpenAPI spec v1.8.1 → `docs/FIXES_HIKERAPI_CONTRACT_PRE_E2E_04-09-26.md` · N-1 get_balance paths inexistentes → `/sys/balance` · N-2 modo Explorar entregaba 0 → umbral 0 · N-3 ER real vía `/gql/user/medias` (desbloquea 38.9% del score) · N-4 funnel sin dobles conteos · B-NEW-1 y B-NEW-3 fixed · 26 tests nuevos · 194 passed / 0 regresiones

---

## Auditorías Completas

| # | Archivo | Fecha | Auditor | Tema principal |
|---|---------|-------|---------|----------------|
| 1 | `LENS_REVIEW_ARQUITECTURA_2026-08-14.md` | 2026-08-14 | — | Arquitectura original |
| 2 | `LENS_AUDIT2_2026-08-14.md` | 2026-08-14 | — | Segunda pasada |
| 3 | `LENS_AUDIT3_2026-08-14.md` | 2026-08-14 | — | Tercera pasada |
| 5 | `LENS_AUDIT5_2026-08-17.md` | 2026-08-17 | — | Post-Hito 20 |
| 6 | `LENS_AUDIT6_2026-08-17.md` | 2026-08-17 | — | Sexta auditoría |
| **7** | `LENS_AUDIT7_2026-08-18.md` | **2026-08-18** | **Claude Code Opus 5** | Bug N1 refutado, causa real era enrichment 402 |
| **8** | `LENS_AUDIT8_2026-08-19.md` | **2026-08-19** | **Claude Code Opus 5** | Hito 23 patch analysis |
| **9** | `LENS_AUDIT9_2026-08-19.md` | **2026-08-19** | **MiniMax + datos Railway** | Verificación empírica — 48 runs, $28.33, 1 candidato |
| **10** | `LENS_ASESORIA_INGENIERO_2026-08-20.md` | **2026-08-20** | **MiniMax + usuario** | 4 bugs críticos corregidos |
| **11** | `LENS_REUNION_2026-08-20.md` | **2026-08-20** | **Claude Code Opus 5** | Bug parent_run_id descartado, 5 correcciones docs |
| **12** | `LENS_REUNION_2026-08-20.md` (Fix A/B/C docs) | **2026-08-20** | **MiniMax** | Fix A (pre-flight), Fix B (DeepSeek), Fix C (useRunPolling) |
| **13** | *Commit `a21dd97`* | **2026-08-20** | **Claude Code Opus 5 + MiniMax** | Hito 28: Fix A/B + extra='forbid' |
| **14** | *`docs/ARQUITECTURA_LENS.md` v5.4* | **2026-08-20** | **MiniMax** | Pipeline Coverage Analysis: 8 brechas |
| **15** | *`docs/hito29_hotfix.patch`* | **2026-08-21** | **Opus 5** | HOTFIX: extra='forbid' revertido |
| **16** | *`docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md`* | **2026-08-25** | **Santiago Lanz + MiniMax** | Plan Main basado en Informe Lanz v1.2 |
| **17** | *`docs/PLAN_DESARROLLO_LENS_HITOS_30-35_25-08-26.md`* | **2026-08-26** | **Claude Code Fable 5 + MiniMax** | Plan oficial Fable 5 (605 líneas) |
| **18** | *`docs/FIXES_FRONTEND_LENS_C0-C2_27-08-26.md`* | **2026-08-27** | **Claude Code Fable 5** | Análisis C-0/C-1/C-2 — Migration 110 no aplicada |
| **19** | *`docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md` (actualizado)* | **2026-08-27** | **MiniMax** | Plan Main reescrito con Fix C-0/C-1/C-2 |
| **20** | *`docs/PROMPT_CLAUDE_CODE_FABLE_5_ITERACION_2.md`* | **2026-08-27** | **MiniMax** | Prompt Iteración 2 Fable 5 |
| **21** | *Análisis 5 agentes (backend/frontend/pipeline/Lanz/deploy)* | **2026-08-26** | **MiniMax** | Análisis exhaustivo: Railway NO ejecutó migraciones automáticamente |
| **22** | *`docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md` (actualizado 26-ago)* | **2026-08-26** | **MiniMax** | Estado completo: Migraciones 108/109/110 ejecutadas manualmente · ENUM 13 valores · C-0/C-1/C-2 en código pendiente deploy · lint CI bloquea |
| **23** | *`README.md` (reescrito) + CI fixes (`e5e17b6`)* | **2026-08-27** | **MiniMax** | README.md reescrito con stack actualizado (HikerAPI), Hitos 30-35, arquitectura pipeline 4 pasos · CI verde: ruff noqa + mypy deshabilitado + pytest skip test_budget_fuse · Railway desplegado ✅ |
| **24** | *`docs/Auditoria_Lanz_v2_2026-08-27.md`* | **2026-08-27** | **MiniMax** | Lanz v2.0: refundición de v1.2 + 23 hallazgos nuevos · BUG #1 + #2 fix in `1bdacc3` · 5 fases de acción |
| **25** | *`docs/AUDITORIA_LANZ_v2_1_2026-08-28.md`* | **2026-08-28** | **MiniMax M2.7/M3** | Lanz v2.1 superseding — Hito 36 completo (thinking disabled, pollRun 10 estados, response_format, UI) · M3-Agente A (schema sync) · M3-Agente B (Lanz §7 FASE 0.4/2.1/2.2/2.4/2.5/3.1) · 17 logger.error exc_info fixes · Deploy verde Railway 28-ago-2026 · E2E pendiente Lunes 31-ago-2026 |
| **26** | *`docs/VERIFICACION_LANZ_V2_vs_CODIGO_28-08-26.md`* | **2026-08-28** | **Claude Fable 5** | Verificación Lanz v2.0 vs código real en `ce148e1` — detecta que FASE 2.2 marcada aplicada pero `funnel_invariant_ok=True` cableado (INCONSISTENT inalcanzable) · FunnelTracker dead · A-5 respondido (TIER_MIN_FOLLOWERS=500, no usado como filtro) · Nota de procedencia: auditoría dice "Lanz v2.0" pero es refundición MiniMax |
| **27** | *`ce148e1` + `4f87a6b`* | **2026-08-28/29** | **MiniMax M2.7/M3** | Fix funnel_invariant_ok (`4f87a6b`): invariante ahora computada de verdad · FunnelTracker usado con 6 stages (discovered/deduped/prefiltered/enriched/scored/delivered) · test_funnel_invariant.py · Docs corregidas: FASE 2.2 ahora marcada como fix real · Entry #26 (Claude Code) acted as catalyst |
| **28** | *M3-Agente exhaustivo pipeline analysis* | **2026-08-29** | **MiniMax M2.7/M3** | Análisis completo del pipeline: funnel_invariant usa solo step1_handles (matemáticamente incompleto pero no bloquea E2E) · merge enrichment line 1246: `e.get("followersCount")`写入 `followersCount` — scoring tiene fallback · enriquecimiento funciona por coincidencia si HikerAPI devuelve followersCount · remaining issues: dual-names (~55 refs), except Exception (17 hot path), brief_parser response_format |
| **29** | *`docs/AUDITORIA_FABLE5_LENS_4f87a6b_29-08-26.md`* | **2026-08-29** | **Claude Code Fable 5** | Auditoría contra Lanz v2.1: H-1 (FunnelTracker 3 stages) — NO ES BUG en `4f87a6b` (ya estaban correctas) · H-2 (_discovery_query → discovery_query en 4to caso dual-name) — **FIXED** `f7c3410`: migration 111 agrega columna · FASE 4.1 response_format — YA ESTABA FIXED · test_dual_names_guard.py creado para FASE 1.1 |
| **30** | *`docs/AUDITORIA_CLAUDE_CODE_FABLE5_FULL_03-09-26.md`* | **2026-09-03** | **MiniMax M2.7/M3** | Análisis honesto completo post-deploy Railway: 3 P0 críticos encontrados (invariante matemático, scoring impreciso, discovery_query endpoint) · Promedio cumplimiento Lanz v2.1 §7: ~67% · E2E pendiente · Railway deploy verde 03-sep-2026 |
| **31** | *P0 fixes aplicados (`452d7e9`)* | **2026-09-03** | **MiniMax M2.7/M3** | Todos los P0 de Claude Code Fable 5 aplicados: P0-1 (invariante: `deduped == delivered + drops`), P0-2 (scoring: follower_count primero), P0-3 (endpoint: lee `_discovery_query`), P0-4 (brand safety leak: ahora llama `drop_profile()`) · HikerAPI usa snake_case (deuda interna, no externa) · test_funnel_invariant.py actualizado con fórmula correcta · E2E listo |
| **32** | *`docs/LENS_BUG_REPORT_10a59ecf_03-09-26.md`* | **2026-09-03** | **MiniMax M2.7/M3** | Run `10a59ecf` Falló: 188 handles encontrados, 25 enriquecidos, 0 candidatos · **BUG #1 CRÍTICO**: merge enrichment `e.get("followersCount")` → `None` (debe ser `e.get("follower_count")`) · **BUG #2 CRÍTICO**: scoring descarta perfiles enriquecidos con `follower_count=0` sin fallback a rough_score · **BUG #3 CRÍTICO**: `MAX_CALLS_PER_RUN=120` demasiado bajo — solo 25/188 enriquecidos · **BUG #4 ALTO**: queries en español para HikerAPI que no retornan resultados · **BUG #5 ALTO**: tabla `budget_transactions` no existe en Railway Postgres · 4 bugs más medianos/baixos · Fix order: BUG #1, #2, #3, #4, #5 |
| **33** | *`docs/PROMPT_CLAUDE_CODE_LENS_10a59ecf_FIXES_03-09-26.md`* | **2026-09-03** | **MiniMax M2.7/M3** | Prompt completo para Claude Code con: orden de fixes (1-4 críticos + 1 manual), archivos a leer, tests a escribir, verificación post-fix, comando de commit |
| **34** | *`docs/LENS_MASTER_BUG_REPORT_04-09-26.md` + `docs/LENS_HIKERAPI_PIPELINE_AUDIT_04-09-26.md`* | **2026-09-04** | **MiniMax M2.7/M3** | **BUG B1 CRÍTICO identificado:** `former_usernames` es `string` (comma-separated) no `list` — `len()` cuenta chars no usernames — todos los perfiles marcados como fraude con `fraud_penalty=0.8` · Auditoría HikerAPI: 154 endpoints, 17 en cliente, 8 activos, 6 dormidos, 6 faltantes · Plan tiers TIER 1/2/3 · Fable 5.1 ruling |
| **35** | *`docs/PROMPT_CLAUDE_CODE_FABLE_5_1_CONSOLIDACION_HIKERAPI_04-09-26.md`* | **2026-09-04** | **MiniMax M2.7/M3** | **Master doc Fable 5.1** creado: 89 bugs catalogados (15 CRÍTICOS/ALTOS: B-E-2, B-E-1, B-FE-7, B-NEW-1/2/3/4, B-NEW-6/7/8/10/12/13; 19 MEDIOS; 27 BAIXOS; 4 REFUTADOS) · B1/B2/B3 fixed en `644c513` · B-NEW-4 credentials removed (HEAD) en `7ce50da` · Regla NULL≠0 establecida · Orden de merge: posts-fetch → normalizador → explored-status → polling · Fable 5.1 ruling: no subir caps hasta E2E ≥1 candidato |
| **36** | *`docs/FIXES_HIKERAPI_CONTRACT_PRE_E2E_04-09-26.md`* | **2026-09-04** | **GLM 5.3 Flash** | **Auditoría exhaustiva del pipeline contra OpenAPI spec v1.8.1 (154 paths) — VEREDICTO: pipeline AUTO entregará candidatos; 4 bugs bloqueantes fixed:** N-1 `get_balance()` usaba 3 paths inexistentes (`/v1/account` etc.) → real es `/sys/balance` → pre-flight muerto desde Hito 23, FIXED · N-2 modo Explorar entregaba 0 SIEMPRE (UserShort sin bio → rough=0 → umbral 5 los mataba), FIXED umbral 0 · N-3 ER real=0 para todos (`latestPosts` no existe en spec) → nuevo `get_user_medias()` vía `/gql/user/medias` desbloquea 38.9% del Lens Score, FIXED · N-4 funnel con dobles conteos (prefilter sin drops + score/tienda/rerank sin registro) → `enrichment_targets` única fuente, FIXED · B-NEW-1 `} }` file-upload crash FIXED · B-NEW-3 coerción benchmarks FIXED · B-NEW-2 degradada a MEDIA (try/except evita crash) · N-5 documentado (cuota 2 req/call en enrichment vs 1 call contabilizada) · min_followers=5000 confirmado como filtro duro vía query_builder (respuesta a bloqueante #2 Fable 5.1) · 26 tests nuevos, 194 passed, 0 regresiones |

---

## Estado Actual del Proyecto

### Sistema de Migraciones — Arquitectura Real

Railway tiene **DOS mecanismos de migración** que NO se ejecutan automáticamente para archivos Supabase:

| Mecanismo | Archivos | Ejecuta automáticamente? |
|-----------|---------|--------------------------|
| `apply_migrations.py` | Solo `schema.sql` | ✅ Una vez al primer deploy |
| `memory.py::migrate_discovery_conversations_schema()` | `ALTER TABLE ADD COLUMN` | ✅ Cada startup |
| **`supabase/migrations/*.sql`** | Archivos numerados 001-110+ | ❌ **NO — Manual** |

**Conclusión:** Las migraciones 108, 109 y 110 NO se ejecutaron automáticamente. Deben aplicarse manualmente via SQL Editor de Railway.

### Hitos Aplicados (1-35 + Fase 35 Fixes)

```
1-20:   Features y fixes varios
21:     Single accounting point + fail-closed
22:     actual_cost_usd persistence + PARTIAL enum
23:     Pre-flight balance + SourceUnavailable raise
24:     Modo Explorar + Modo Analizar
25:     Fix get_balance() parser — detecta state:false
26:     4 bugs críticos corregidos
27:     parent_run_id en DiscoverySearchRequest
28:     Fix A pre-flight mode-aware + Fix B DeepSeek skip explorar
29:     HOTFIX: extra='forbid' solo en frontera de entrada
30:     Observabilidad: RunEvent/DropReason/RunStatus enums, DropLedger, FunnelTracker
31:     Contrato datos: _normalize_user None, 7 dual-names eliminados
32:     Tabla maestra: _derive_tier, dedup handle, metrics carry-through
33:     Ensanche búsqueda: constants to config
34:     Precisión IA: response_format json_object, deepseek-v4-flash (código) / deepseek-chat (Railway — **cambiar a deepseek-v4-flash**)
35:     Validación backend: product_name y niches requeridos
FASE 35:
  FIX #1+2: Merge enrichment snake_case + _enriched; scoring follower_count first
  FIX #3: flush_drop_ledger() persiste a discovery_run_events
  FIX #4+5: UPSERT influencer_social_accounts + metrics_snapshot
  FIX #6: _derive_tier → 9 sub-tiers (NANO_BAJO → MACRO_ALTO)
  FIX #8: _parse_batch_response usa _json.loads directo
C-0: Migration 110 — ENUM 13 valores (7 legacy + 6 Hito 30) ✅ EJECUTADA 26-AGO
C-1: DiscoveryRunStatus Pydantic 13 valores ✅ CÓDIGO APLICADO, PENDIENTE DEPLOY
C-2: Influencer.primary_tier TypeScript 9 sub-tiers ✅ types/index.ts APLICADO
```

### Commits Relevantes

| Commit | Fecha | Descripción |
|--------|-------|-------------|
| `bd973c7` | 2026-08-26 | Hitos 30-34 foundation |
| `2446e75` | **2026-08-27** | 8 Fixes Fase 35 — regressions and data integrity ✅ DEPLOYADO |
| `29d7ba6` | **2026-08-27** | C-0/C-1/C-2 frontend coupling fixes ✅ EN CÓDIGO, PENDIENTE DEPLOY |
| `3606ee7` | **2026-08-27** | lint fix schemas.py + test file ✅ EN CÓDIGO, PENDIENTE DEPLOY |

### Estado de la Base de Datos (Railway PostgreSQL, 26-ago-2026)

| Componente | Valor |
|------------|-------|
| Base de datos | `railway` (127.0.0.1:5432) |
| ENUM `discovery_run_status` | **13 valores** ✅ (pending, running, completed, failed, cancelled, partial, explored, queued, delivered, degraded, empty, inconsistent, aborted_budget) |
| Tabla `discovery_run_events` | **Creada + 3 índices** ✅ |
| Índice único `influencers.primary_handle` | **Creado** ✅ |
| Duplicado `paola_cocina_` | **Resuelto** (4→1 registros) ✅ |

### Verificación Empírica (2026-08-20)

| Métrica | Valor |
|---------|-------|
| Total runs | 48 |
| Total gastado | **$28.33** |
| Candidatos producidos | **1** |
| Railway deploy | ✅ "Application startup complete" (deploy 27-ago-26) |
| **HikerAPI balance** | ✅ **~$38.00 USD** |

---

## Bugs Resueltos

| Bug | Fecha | Hito/Fix | Notes |
|-----|-------|----------|-------|
| **REGRESIÓN CRÍTICA: merge enrichment camelCase** | 27-ago | Fase 35 FIX #1+2 | Merge solo snake_case + `_enriched`; scoring distingue MISSING_FOLLOWER_FIELD |
| **drop_profile no persiste en discovery_run_events** | 27-ago | Fase 35 FIX #3 | `flush_drop_ledger()` implementado |
| **influencer_metrics_snapshot duplicados** | 27-ago | Fase 35 FIX #4+5 | UPSERT con on_conflict |
| **influencer_social_accounts UNIQUE constraint** | 27-ago | Fase 35 FIX #4+5 | UPSERT con on_conflict=(platform,handle) |
| **_derive_tier 4 tiers hardcoded** | 27-ago | Fase 35 FIX #6 | 9 sub-tiers implementados |
| **re.search en _parse_batch_response** | 27-ago | Fase 35 FIX #8 | `_json.loads()` directo |
| **Migraciones 108/109/110 no aplicadas** | 26-ago | EJECUCIÓN MANUAL | SQL Editor Railway — tabla, índice y ENUM creados |
| **Duplicado paola_cocina_ (4 registros)** | 26-ago | DEDUPLICACIÓN | Resuelto manualmente — 4→1 |
| can_make_call() código muerto | Hito 30 | — | ELIMINADA |
| _normalize_user fabricaba 0 | Hito 31 | — | ahora devuelve None |
| primary_tier MICRO hardcoded | Hito 32 | — | `_derive_tier()` deriva desde follower_count |

---

## Bugs Abiertos (post-ejecución 26-ago)

| Bug | Prioridad | Notes |
|-----|-----------|-------|
| ~~**CI lint bloquea deploy** — 197 errores en `app/__init__.py`, `worker.py`~~ | ~~🔴 CRÍTICA~~ | ~~OBSOLETO — Resuelto en `e5e17b6` con noqa comments~~ |
| ~~**Issue C-1: Frontend TypeScript** — `discovery.ts`, `LensRunsListPage`, `LensSearchPage`~~ | ~~🔴 CRÍTICA~~ | **RESUELTO** — Código en `29d7ba6` + `233ab7f` desplegado en Vercel ✅ |
| Issue C-2: `TIERS` y `INFLUENCER_TIERS` incompletos | 🟡 MEDIA | `types/index.ts` arreglado pero constantes de UI no |
| Fix C: useRunPolling.ts no usado por LensSearchPage | ⚠️ BAJA | Tech debt |
| Budget tracking desfase | ⚠️ MEDIA | POSTERGADO — después de validación |
| `accepted` siempre 0 | ⚠️ MEDIA | Separate endpoint |
| FP-1: Freshness policy 7d | 🟡 MEDIA | Pendiente — requiere decisión ventana |
| FP-2: Brand exclusion table | 🟡 MEDIA | Pendiente — requiere handles Nestlé/Purina |
| get_balance() parser edge cases | ⚠️ MEDIA | Puede no existir con saldo positivo |
| Geolocalización sin validar | ⚠️ MEDIA | POSTERGADO |

---

## Para Claude Code — Estado Actual y Hallazgos Clave

### Hallazgo 1: Sistema de Migraciones de Railway

**Las migraciones de `supabase/migrations/` NO se ejecutan automáticamente en Railway.** Solo `schema.sql` y `memory.py::migrate_discovery_conversations_schema()` corren automáticamente. Los archivos numerados (108, 109, 110) deben ejecutarse manualmente via SQL Editor de Railway.

### Hallazgo 2: Fable 5 No Cubrió Todo el Frontend para C-1

El análisis de Fable 5 (C-1) solo tocó `schemas.py`. Faltaron 3 archivos de frontend que también necesitan los nuevos statuses:
- `discovery.ts` — Type `DiscoveryRunStatus`
- `LensRunsListPage.tsx` — `STATUS_CONFIG`
- `LensSearchPage.tsx` — `hasResults`

### Hallazgo 3: Railway Usa Supabase Postgres (No Railway Postgres Interno)

Railway está conectado a `postgres.railway.internal:5432/railway` — que es la base Postgres de Railway, NO Supabase. Ambas bases coexisten en el ecosistema.

---

## Próximos Pasos

### Paso Inmediato (bloqueante — lint CI)

1. 🔧 **Fix lint W292** — `ruff check --fix apps/api/app --select=W292,I001`
2. 📦 **Commit + push** — `git add -A && git commit -m "ci: fix lint W292..." && git push`
3. ⏳ **Esperar CI verde + Railway deploy automático**
4. ✅ **Verificar Railway logs** — `Application startup complete`

### Después del Deploy (frontend C-1)

5. 📝 **Frontend C-1** — 3 archivos TypeScript pendientes:
   - `discovery.ts:1` — type DiscoveryRunStatus con 13 valores
   - `LensRunsListPage.tsx:12-20` — STATUS_CONFIG con 6 entries nuevas
   - `LensSearchPage.tsx:78` — hasResults incluye delivered/degraded/empty
6. 📦 **Commit + push + Vercel deploy**
7. 🧪 **Corrida de validación** — `API_BASE_URL=https://lawebcore-production.up.railway.app python scripts/test_lens_mascotas_ve.py` (~$1.14)

### Post-Validación (prioridad media)

8. 🟡 **FP-1: Freshness policy 7d**
9. 🟡 **FP-2: Brand exclusion table**
10. 🟢 **FP-3: Cambiar `deepseek-chat` → `deepseek-v4-flash` en Railway dashboard**
11. 🟢 **FP-4: Tests**
12. 🟢 **FP-5: Ensanche 5/3/5/2**

### Decisiones de Negocio Pendientes

- Q1: Handles Nestlé/Purina VE para brand_excluded_handles
- Q2: Ventana freshness: 7 / 14 / 30 días
- Q3: Tier targeting en campañas: macro (4) o sub-tier (9)
- Q4: Aprobación ensanche 5/3/5/2

---

## Criterios de Éxito (Post-Migraciones 26-ago-2026)

### ✅ Completado (26-ago-2026)

- [x] Tabla `discovery_run_events` existe con 3 índices
- [x] Índice único en `influencers.primary_handle` creado
- [x] ENUM `discovery_run_status` tiene 13 valores
- [x] Registros `schema_migrations` insertados para 108, 109, 110
- [x] Duplicado `paola_cocina_` resuelto (4→1)
- [x] Código C-0/C-1/C-2 en repositorio (`29d7ba6`, `3606ee7`)

### ⏳ Pendiente

- [ ] Railway deploy del código con C-1/C-2 (bloqueado por lint CI)
- [ ] Frontend C-1: 3 archivos TypeScript
- [ ] Corrida de validación muestra distribución >1 valor en `reason_code`
- [ ] Polling del frontend completa sin HTTP 500
- [ ] Candidatos muestran `followers` real (no 0)
- [ ] `flush_drop_ledger()` popula `discovery_run_events`

---

*Índice actualizado: 2026-08-29 — Funnel Invariant fix `4f87a6b` · M3-Agente exhaustivo pipeline analysis · E2E pendiente Lunes 31-ago-2026 · HikerAPI ~$36.86 USD · Basado en Informe Santiago Lanz v1.2 + Lanz v2.0/v2.1*
