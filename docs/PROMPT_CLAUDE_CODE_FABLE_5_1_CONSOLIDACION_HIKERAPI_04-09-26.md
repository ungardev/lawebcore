# PROMPT_CLAUDE_CODE_FABLE_5_1 — CONSOLIDACIÓN HIKERAPI
## Auditoría Maestra + Catálogo de 89 Bugs + Plan de Fixes Escalonado
## Fecha: 04-sep-2026 · La Web Figital Agency

> **Repositorio:** `github.com/ungardev/lawebcore`
> **HEAD actual:** batch N-1..N-4 (04-sep-2026) — cliente HikerAPI alineado a OpenAPI spec (ver `FIXES_HIKERAPI_CONTRACT_PRE_E2E_04-09-26.md`)
> **Commits previos:** `370443c` docs · `7ce50da` credentials removed · `644c513` B1/B2/B3 + logging · `a67ad72` FIX 1
> **Run de referencia:** `10a59ecf` (03-sep-2026) — 188 handles → 25 enriched → 0 candidatos
> **HikerAPI docs:** https://api.hikerapi.com/docs | https://api.hikerapi.com/openapi.json
> **HikerAPI balance:** ~$35 USD restantes · pre-flight FUNCIONAL vía `/sys/balance`
> **Regla de oro:** "Mostrar candidatos en logs > rechazar candidatos"
> **Auditor principal:** MiniMax M2.7/M3 + 2 explore agents + GLM 5.3 Flash (auditoría OpenAPI exhaustiva)

---

## SECCIÓN 1 — CONTEXTO

### 1.1 Qué es LENS
LENS (Lens) es el módulo de descubrimiento de influencers de La Web Core (La Web Figital Agency, Venezuela). El pipeline descubre candidatos venezolanos en Instagram usando:
- **Apify** para scraping de hashtags y búsqueda
- **HikerAPI** (8 de 154 endpoints activos) para enriquecimiento de perfiles
- **DeepSeek** para análisis de afinidad de marca
- **PostgreSQL/Railway** para persistencia y estado

### 1.2 Situación actual
- Run `10a59ecf`: 188 handles → 25 enriquecidos → **0 candidatos**
- Causa raíz: cadena de bugs (B1/B2/B3 + más) que impedían scoring correcto
- Commit `644c513` aplicó B1/B2/B3 + logging exhaustivo + tests de regresión
- Commit `7ce50da` removió credenciales hardcodeadas (B-NEW-4, remediación parcial)
- E2E post-`644c513` aún **no validado**

### 1.3 Decisiones del equipo (04-sep-2026)
- Key HikerAPI: **rotación diferida** — se mantiene la misma key durante desarrollo
- Remoción de credenciales: **Opción A** (HEAD solo, no rewrite de historia)
- Estrategia: escalonada — avanzar con la misma key mientras se establece el proceso correcto
- TEST_PASSWORD: diferido también — por ahora se usa env var

---

## SECCIÓN 2 — ARQUITECTURA ACTUAL VERIFICADA

### 2.1 Pipeline de descubrimiento (4 pasos)

```
Brief → STEP 0 (Location Bootstrap) [GATED: HIKERAPI_STEP0_LOCATION=false]
     → STEP 1 (Hashtags: Apify) → handles
     → STEP 2 (Keywords: Apify) → handles
     → STEP 3 (Enriquecimiento HikerAPI: get_user_info) → enriched profiles
     → STEP 4 (Scoring +Filtering) → candidates
```

### 2.2 Límites por step

| Parámetro | Valor actual | Archivo |
|-----------|-------------|---------|
| `MAX_HANDLES_TO_ENRICH` | 25 | `worker.py:60` |
| `MAX_CALLS_PER_RUN` | 120 | `config.py:87` |
| `TIER_MIN_FOLLOWERS` | 500 (no usado como filtro) | `worker.py:54` |
| `ENRICHMENT_INCLUDE_ABOUT` | `false` (default) | `worker.py:75` |
| `HIKERAPI_STEP0_LOCATION` | `false` (default) | `worker.py:470` |

### 2.3 HikerAPI — Endpoints activos (8/154)

| # | Método | Endpoint | Uso | Costo/llamada |
|---|--------|---------|-----|---------------|
| 1 | `get_balance()` | `GET /account/balance` | preflight | — |
| 2 | `search_hashtag()` | `GET /v2/hashtag/by/name` | STEP 1 | $0.02 |
| 3 | `get_hashtag_medias_top()` | `GET /v2/hashtag/medias/top` | STEP 1 | $0.02 |
| 4 | `get_hashtag_medias_recent()` | `GET /v2/hashtag/medias/recent` | STEP 1 | $0.02 |
| 5 | `search_accounts_v2()` | `GET /v3/fbsearch/accounts` | STEP 2 | $0.02 |
| 6 | `get_user_info()` | `GET /v2/user/by/username` | STEP 3 (enrichment) | $0.02 |
| 7 | `search_topsearch()` | `GET /gql/topsearch` | STEP 3 | $0.02 |
| 8 | `search_reels()` | `GET /v2/fbsearch/reels` | STEP 2.5 | $0.02 |

### 2.4 HikerAPI — Endpoints dormidos (6)

| # | Método | Endpoint | Estado | Potencial |
|---|--------|---------|--------|-----------|
| 9 | `search_followers_of()` | `GET /v1/user/search/followers` | Nunca llamado | STEP 4 expansion |
| 10 | `web_profile_info()` | `GET /gql/user/web_profile_info` | Nunca llamado | Fallback enrichment |
| 11 | `get_user_about()` | `GET /v1/user/about` | Cableado, flag OFF | Fraud signals, account age |
| 12 | `search_location()` | `GET /v1/fbsearch/places` | Cableado, flag OFF | STEP 0 location bootstrap |
| 13 | `location_medias_top()` | `GET /v1/location/medias/top` | Gated por #12 | Location-based discovery |
| 14 | `location_medias_recent()` | `GET /v1/location/medias/recent/chunk` | Gated por #12 | Location-based discovery |

### 2.5 HikerAPI — Endpoints faltantes (6+)

| # | Endpoint | Para qué sirve | Prioridad |
|---|---------|---------------|-----------|
| 15 | `GET /g2/user/followers` | Followers paginados de seed accounts | ⭐⭐ KILLER |
| 16 | `GET /v2/user/explore/businesses/by/id` | Recomendados por categoría | ⭐ |
| 17 | `GET /v1/media/likers` | Engagement expansion | ⭐ |
| 18 | `GET /v2/user/clips` | ER real de Reels | ⭐⭐ |
| 19 | `GET /v3/fbsearch/places` | Búsqueda de lugares v3 | — |
| 20 | `GET /v1/fbsearch/topsearch/hashtags` | Hashtag bootstrap | — |

---

## SECCIÓN 3 — CATÁLOGO DE 89 BUGS

> **Formato:** B-{tipo}-{número} · P0=Crítico/ALTO · P1=Medio · P2=Baixu
> **B-E-#** = Existing bugs del código base
> **B-NEW-#** = Bugs encontrados en segunda auditoría (MiniMax M3 + 2 explore agents)
> **B-FE-#** = Frontend bugs
> **B-INF-#** = Bugs informativos (no requieren acción)
> **B-FABLE-#** = Bugs identificados por Fable 5.1

### 3.1 Bugs CRÍTICOS / ALTA priorizados (P0)

| ID | Gravedad | Descripción | Archivo:Línea | Estado | Fix |
|----|----------|-------------|---------------|--------|-----|
| **B-E-2** | 🔴 CRÍTICA | `latestPosts` nunca se fetch — ER real = 0 para todos | `hikerapi_client.py` | ✅ **FIXED (N-3, 04-sep)** — `get_user_medias()` vía `/gql/user/medias` |
| **B-E-1** | 🔴 CRÍTICA | Normalizador pierde `is_business`/`is_verified` (camelCase → snake_case) | `hikerapi_client.py:846-860` | PENDIENTE | Agregar campos al normalizador |
| **B-FE-7** | 🔴 CRÍTICA | `RunStatus` no tiene `EXPLORED` — polling infinito en estado terminal | `worker_enqueuer.py:1862-1868` | ✅ **FIXED (04-sep, FE)** — hooks alineados a `RunStatus` real + test de contrato |
| **B-NEW-1** | 🔴 CRÍTICA | `}` en template `.format()` — crash 100% en parse_from_document | `brief_parser.py:163` | ✅ **FIXED (04-sep)** — `} }` → `}}` |
| **B-NEW-2** | 🔴 CRÍTICA | `elite_data` column missing → DB persist broken 100% | `profile_generator.py:543,294-307` | PENDIENTE | Agregar columna + normalizar |
| **B-NEW-3** | 🔴 CRÍTICA | benchmarks LLM sin type coercion + fuera de try block | `profile_generator.py:420` | ✅ **FIXED (04-sep)** — coerción int/float |
| **B-NEW-4** | 🔴 CRÍTICA | HikerAPI key + test password hardcoded in 3 scripts | `test_run5_validation.py:63`, `test_hikerapi.py:177`, `test_purina_dogchow.py:92` | ✅ **REMEDIADO PARCIAL** (HEAD limpio; rotación pendiente) | Rotar key + guardas |
| **B-E-4** | 🟡 ALTA | TLD duplicates: `co_`/`mx_`/`ar_`/`pe_`/`cl_` × 2 en tier bucketing | `worker.py:1476-1483` | PENDIENTE | Fix tier assignment |
| **B-FE-15** | 🟡 ALTA | Polling infinito para 6 estados terminales reales | `useRunPolling.ts:36-40` | PENDIENTE | Filtrar estados terminales |
| **B-NEW-6** | 🟡 ALTA | Apify `should_skip_business` hardcoded True → ignora business accounts | `apify_client.py` | PENDIENTE | Parametrizar |
| **B-NEW-7** | 🟡 ALTA | `country_boost()` usa lógica inconsistente con scoring | `geo_boost.py` | PENDIENTE | Unificar lógica |
| **B-NEW-8** | 🟡 ALTA | `result_ranker.py` weights difieren de `geo_boost.py` | score mismatch | PENDIENTE | Unificar weights |
| **B-NEW-10** | 🟡 ALTA | `engagement_rate` se calcula 2 veces con lógicas distintas | `worker.py:1438` | PENDIENTE | Una sola fuente |
| **B-NEW-12** | 🟡 ALTA | `funnel_invariant` usa solo `step1_handles` (incompleto) | `worker.py` | PENDIENTE | Incluir todos los pasos |
| **B-NEW-13** | 🟡 ALTA | Auto-hashtags VE appendeados AL FINAL con cap 30 → nunca incluidos | `brief_parser.py` | PENDIENTE | Prepend o subir cap |

### 3.2 Bugs MEDIOS (P1)

| ID | Descripción | Archivo:Línea | Estado |
|----|-------------|---------------|--------|
| **B-E-5** | `tier` plural mismatch en algunas ramas | `query_builder.py` | PENDIENTE |
| **B-NEW-5** | Tier plural/singular mismatch | `query_builder.py` | PENDIENTE |
| **B-NEW-9** | Redis pool leak: nuevo pool por cada enrichment call | `profile_generator.py:294` | PENDIENTE |
| **B-NEW-11** | Dedup ARQ 1h + bool ignorado → zombie runs | `worker_enqueuer.py` | PENDIENTE |
| **B-NEW-14** | `TIMEOUT_PER_HANDLE` no se respeta en enrichment async | `config.py` | PENDIENTE |
| **B-NEW-15** | Cache TTL inconsistency entre cliente y servidor | `hikerapi_client.py` | PENDIENTE |
| **B-NEW-16** | `exclude_handles` schema existe pero no se wirea a Apify | `apify_client.py` | PENDIENTE |
| **B-FE-16** | Error boundary genérico oculta errores específicos | `CandidateCard.tsx` | PENDIENTE |
| **B-FE-17** | Progress bar con valores inconsistentes (steps vs %) | `SearchProgress.tsx` | PENDIENTE |
| **B-FE-18** | BriefWizard permite submission con campos inválidos | `BriefWizard.tsx` | PENDIENTE |

### 3.3 Bugs BAIXOS (P2)

| ID | Descripción | Archivo:Línea | Estado |
|----|-------------|---------------|--------|
| **B-NEW-17** | `country_boost` recalcula en vez de memoizar | `geo_boost.py` | PENDIENTE |
| **B-NEW-18** | Logging inconsistency: algunos eventos con prefijo, otros sin | `worker.py` | PENDIENTE |
| **B-NEW-19** | `DualName` guard recheckea en cada scoring, no en discovery | `worker.py` | PENDIENTE |
| **B-FE-19** | HashtagChips permite input vacío | `HashtagChips.tsx` | PENDIENTE |
| **B-FE-20** | Sidebar no indica ruta activa | `Sidebar.tsx` | PENDIENTE |
| **B-FE-21** | Dark mode transition abrupta | `index.css` | PENDIENTE |
| **B-FE-22** | Font-display inconsistente: Montserrat vs Instrument Serif | `tailwind.config.js` + `index.css` | PENDIENTE |
| **B-FE-23** | Color tokens duplicados en tailwind.config.js | `tailwind.config.js` | PENDIENTE |
| **B-FE-24** | Cities field permite trailing comma → dato cortado | `BriefWizard.tsx` | PENDIENTE |
| **B-FE-25** | Orchestrator state in-memory perdido en restart | `orchestrator.py` | PENDIENTE |
| **B-FE-26** | Audit log para cambios de brief no persiste | `brief_parser.py` | PENDIENTE |

### 3.4 Bugs ya ARREGLADOS (histórico)

| ID | Descripción | Commit | Estado |
|----|-------------|--------|--------|
| **BUG #1** (original) | Merge enrichment `followersCount` → camelCase | `a67ad72` | ✅ FIXED |
| **B1** | `former_usernames` string vs list — fraude penalty universal | `644c513` | ✅ FIXED |
| **B2** | `country="VE"` hardcoded en path TikTok | `644c513` | ✅ FIXED |
| **B3** | `audience_credibility/quality=50` fabricados | `644c513` | ✅ FIXED |
| **B-FABLE-P0-1** | Invariante de funnel mal calculado | `452d7e9` | ✅ FIXED |
| **B-FABLE-P0-2** | Scoring usaba `followersCount` en vez de `follower_count` | `452d7e9` | ✅ FIXED |
| **B-FABLE-P0-3** | Endpoint de query mal leído | `452d7e9` | ✅ FIXED |
| **B-FABLE-P0-4** | Brand safety leak | `452d7e9` | ✅ FIXED |
| **B-NEW-4** | Credenciales hardcodeadas | `7ce50da` | ✅ REMEDIADO PARCIAL |

### 3.5 Bugs INFORMATIVOS — REFUTADOS (no requieren acción)

| ID | Afirmación original | Veredicto | Evidencia |
|----|---------------------|-----------|-----------|
| **B-INF-1** | `HIKERAPI_INCLUDE_ABOUT` estaba "desconectado" | ❌ REFUTADO | Cableado en `worker.py:75` y `worker.py:1157` — solo apagado por default |
| **B-INF-2** | `HIKERAPI_STEP0_LOCATION` estaba "desconectado" | ❌ REFUTADO | Cableado en `worker.py:470` y `worker.py:472-513` — solo apagado por default |

---

## SECCIÓN 4 — FIXES YA APLICADOS (commit `644c513`)

### 4.1 B1 fix: `_coerce_former_usernames()` type-agnostic
- **Archivo:** `hikerapi_client.py:659`
- **Qué hace:** Normaliza `former_usernames` sea string, list[str], list[dict], o None
- **Impacto:** Elimina fraude penalty universal de -20% sobre todos los perfiles enriquecidos

### 4.2 B2/B3 fix: valores fabricados eliminados
- **TikTok:** `country=None` (antes `"VE"` hardcoded), `engagement_rate=None` (antes `0.05`)
- **YouTube:** `engagement_rate=None` (antes `0.02`)
- **Instagram Apify:** `audience_quality=None` (antes `50`)
- **Regla:** NULL ≠ 0 — lo que no se midió no se fabula

### 4.3 Logging exhaustivo añadido
- `enrichment_merged` (info) — cada perfil enriquecido con campos clave
- `enrichment_orphan_handle` (warning) — handle en respuesta API que no existe en profiles
- `enrichment_missing` (warning) — perfil no enriquecido con `drop_profile(ENRICHMENT_FAILED)`
- `fraud_penalty_applied` (info) — promoción de debug a info con contexto completo

### 4.4 None-safety en fraud scoring
- `former_usernames_count` y `account_age_days` ahora None-safe
- Paréntesis explícitos en condición `elif` (precedencia sin ambigüedad)

### 4.5 Tests de regresión creados
- `test_former_usernames_coercion.py` — 12 casos parametrizados
- `test_no_fabricated_metrics.py` — regex scan contra valores fabricados
- `test_enrichment_field_names.py` (extensión) — verifies normalizer no emite engagement_rate

---

## SECCIÓN 5 — FILOSOFÍA DE FIXES

### 5.1 Reglas fundamentales

1. **NULL ≠ 0:** Lo que no se midió no se fabula. Ningún literal numérico como default.
2. **Type-agnostic:** El código debe funcionar con cualquier forma que devuelva la API externa.
3. **Structlog events:** Cada handle produce eventos estructurados, no logs de texto libre.
4. **Cada fix con test:** Antes de cerrar un bug, escribir test de regresión.
5. **No subir límites hasta validar E2E:** Fable 5.1 ruling — duplicar el costo del mismo fallo no es optimización.

### 5.2 Orden de merge recomendado

| Orden | Fix | Archivos | Bloquea |
|-------|-----|----------|---------|
| 1 | Posts-fetch para ER real (B-E-2) | `hikerapi_client.py`, `worker.py` | P0 activo — ER=0 para todos |
| 2 | Normalizador: is_business/is_verified (B-E-1) | `hikerapi_client.py` | Tier assignment roto |
| 3 | RunStatus.EXPLORED (B-FE-7) | `worker_enqueuer.py`, `useRunPolling.ts` | Polling infinito |
| 4 | parse_from_document `}` crash (B-NEW-1) | `brief_parser.py:163` | Brief parsing crash |
| 5 | elite_data column missing (B-NEW-2) | `profile_generator.py` + migration | DB persist broken |
| 6 | TLD duplicates (B-E-4) | `worker.py:1476-1483` | Tier bucketing incorrecto |
| 7 | Redis pool leak (B-NEW-9) | `profile_generator.py:294` | Resource leak |
| 8 | Dedup ARQ 1h (B-NEW-11) | `worker_enqueuer.py` | Zombie runs |

### 5.3 Política de caps

| Parámetro | Valor actual | Fable 5.1 ruling |
|-----------|-------------|-------------------|
| `MAX_HANDLES_TO_ENRICH` | 25 | No subir hasta E2E entregue ≥1 candidato |
| `MAX_CALLS_PER_RUN` | 120 | No subir hasta E2E entregue ≥1 candidato |
| `HIKERAPI_INCLUDE_ABOUT` | `false` | Encender DESPUÉS de B1 fix |
| `HIKERAPI_STEP0_LOCATION` | `false` | Encender después de TIER 1 validado |

---

## SECCIÓN 6 — COSTOS ESTIMADOS

| Configuración | Calls/run | Costo/run | Candidatos esperados |
|--------------|-----------|-----------|---------------------|
| Actual (sin B1/B2/B3) | ~86 | $1.72 | 0 |
| Post-`644c513` (B1/B2/B3 fixed) | ~86 | $1.72 | ¿? (E2E pendiente) |
| TIER 1 + dormant endpoints | ~165 | $3.30 | 15-25 |
| TIER 2 + límites elevados | ~290 | $5.80 | 60-100 |
| TIER 3 + 6 endpoints nuevos | ~290 | $5.80 | 50-80 |

---

## SECCIÓN 7 — INSTRUCCIONES PARA CLAUDE CODE FABLE 5.1

### 7.1 Archivos críticos a leer primero

```
packages/discovery/discovery/tools/hikerapi_client.py   # Cliente HikerAPI, normalizador
apps/api/app/workers/worker.py                          # Pipeline worker, scoring, fraud
apps/api/app/workers/worker_enqueuer.py                  # RunStatus enum, enqueuing
packages/discovery/discovery/brief_parser.py             # Parseo de brief, crash B-NEW-1
packages/discovery/discovery/profile_generator.py        # elite_data B-NEW-2, Redis B-NEW-9
packages/discovery/discovery/query_builder.py             # Tier plural/singular B-NEW-5
apps/web/src/features/lens/hooks/useRunPolling.ts        # Polling infinito B-FE-15
apps/api/app/core/worker_enqueuer.py                     # RunStatus.EXPLORED B-FE-7
```

### 7.2 Documentación de referencia

- **Éste documento** — `docs/PROMPT_CLAUDE_CODE_FABLE_5_1_CONSOLIDACION_HIKERAPI_04-09-26.md`
- **Auditoría HikerAPI** — `docs/LENS_HIKERAPI_PIPELINE_AUDIT_04-09-26.md`
- **Master Bug Report** — `docs/LENS_MASTER_BUG_REPORT_04-09-26.md`
- **Fixes B1/B2/B3** — `docs/FIXES_B1_LOGGING_ENDPOINTS_LENS_a67ad72_04-09-26.md`
- **OpenAPI spec** — `https://api.hikerapi.com/openapi.json`

### 7.3 Flujo de trabajo

1. Leer specs + OpenAPI (`api.hikerapi.com/openapi.json`)
2. Leer documentación de referencia listada arriba
3. Leer archivos críticos de §7.1
4. Identificar gaps entre docs y código real
5. Para cada P0: escribir test primero, luego fix
6. Para cada P1: fix + test inline
7. Para cada P2: fix si <15 min, else diferir
8. Commit por grupo lógico, no por archivo
9. Push y validar E2E antes de siguiente batch

### 7.4 Criterios de aceptación

- **E2E mínimo:** 1 candidato de 188 handles (con B1/B2/B3 aplicados en `644c513`)
- **Polling:** 0 estados terminales con polling infinito post-fix
- **Tests:** 31/31 passing en suite LENS (2 pre-existentes failure OK)
- **Costos:** mantener ≤ $0.10/candidato validado

---

*Documento generado: 04-sep-2026 · La Web Figital Agency*
*Para entrega a: Claude Code Fable 5.1*
*Basado en: run `10a59ecf`, commits `a67ad72` → `644c513` → `7ce50da`, auditoría 7,346 líneas*
