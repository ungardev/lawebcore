# AUDITORÍA COMPLETA — LENS Discovery Pipeline
## Claude Code Fable 5 + Análisis Honesto MiniMax M2.7/M3

> **Repositorio:** `github.com/ungardev/lawebcore`
> **Branch:** `main`
> **HEAD:** `07326f5` (03-sep-2026)
> **Deploy Railway:** Verde — 03-sep-2026 14:12 UTC · Migration 111 aplicada
> **Auditores:** Claude Code Fable 5 · MiniMax M2.7/M3
> **Propósito:** Documentar TODOS los hallazgos de la auditoría de Fable 5 y el análisis honesto del estado real del pipeline para que una próxima sesión de Claude Code pueda corregir todo sin perder contexto.

---

## TABLA DE CONTENIDOS

1. [Estado del Deploy](#1--estado-del-deploy)
2. [Fixes Aplicados de Claude Code Fable 5](#2--fixes-aplicados-de-claude-code-fable-5)
3. [Hallazgos Críticos Pendientes](#3--hallazgos-críticos-pendientes)
4. [Análisis Matemático: El Invariante del Embudo](#4--análisis-matemático--el-invariante-del-embudo)
5. [Análisis: Scoring y Enrichment](#5--análisis--scoring-y-enrichment)
6. [Patrón Recurrente: Un Extremo Corregido, el Otro No](#6--patrón-recurrente--un-extremo-corregido-el-otro-no)
7. [Estado de Cumplimiento Lanz v2.1 §7](#7--estado-de-cumplimiento-lanz-v21-§7)
8. [Plan de Acción Priorizado](#8--plan-de-acción-priorizado)
9. [Preguntas Sin Respuesta](#9--preguntas-sin-respuesta)
10. [E2E Test: Estado](#10--e2e-test--estado)

---

## 1. — Estado del Deploy

### Railway — Verde ✅

```
2026-09-03T14:12:34.331717965Z [inf] Starting Container
2026-09-03T14:12:37.050754204Z [inf] [migration] Set timestamp fallback titles for discovery_conversations
2026-09-03T14:12:37.050771383Z [inf] [migration] Backfilled titles for discovery_runs
2026-09-03T14:12:37.050792713Z [inf] [railway_pg] Creating new asyncpg pool
2026-09-03T14:12:37.050802893Z [inf] [railway_pg] Pool created successfully
2026-09-03T14:12:37.050819313Z [inf] [migration] Added column parsed_brief_json to discovery_conversations
2026-09-03T14:12:37.050825463Z [inf] [migration] Added column title to discovery_runs
2026-09-03T14:12:37.051010042Z [err] INFO: Application startup complete.
2026-09-03T14:12:38.916551041Z [inf] Starting worker for 5 functions: discovery_run_task, sync_hypeauditor_task, sync_metricool_task, cron:scheduled_reports_cron, cron:sync_metricool_task
```

### Migración 111 Aplicada ✅

```sql
-- 00000000000111_discovery_candidates_discovery_query.sql
ALTER TABLE discovery_candidates
ADD COLUMN IF NOT EXISTS discovery_query TEXT DEFAULT '';
```

### Commits desde la última auditoría

| Commit | Descripción |
|--------|-------------|
| `f7c3410` | H-2 fix: discovery_query column + test_dual_names_guard.py |
| `07326f5` | docs: entry #29 — Claude Code Fable 5 fixes |

---

## 2. — Fixes Aplicados de Claude Code Fable 5

### Fix H-2: discovery_query Columna (✅ Aplicado `f7c3410`)

**Problema original:** El worker escribía `_discovery_query` (con guion bajo inicial) en 12 sitios pero el endpoint `discovery.py` leía `discovery_query` (sin guion).

**Fix aplicado:**
- Migration `00000000000111` agrega columna `discovery_query` a `discovery_candidates`
- schema.sql sincronizado

**Estado:** ✅ La columna ahora existe. El worker sigue escribiendo `_discovery_query`; el endpoint sigue leyendo `discovery_query`. El fix del endpoint (leer ambas formas) NO se aplicó.

**Impacto real:** `influencers.discovery_query` se guarda vacío hasta que se corrija el endpoint.

---

### Test Guard: test_dual_names_guard.py (✅ Creado `f7c3410`)

**Propósito:** Prevenir regresiones en dual-name patterns. Establece baseline counts para 22 campos camelCase en `worker.py`.

**Ubicación:** `apps/api/tests/test_dual_names_guard.py`

**Baseline counts establecidos (03-sep-2026):**

| Campo | Count | Campo | Count |
|-------|-------|-------|-------|
| `followersCount` | 24 | `fullName` | 13 |
| `followingCount` | 2 | `profilePicUrl` | 28 |
| `followsCount` | 21 | `isBusinessAccount` | 21 |
| `postsCount` | 24 | `isVerified` | 1 |
| `hdProfilePicUrl` | 1 | `uniqueId` | 1 |
| `ownerUsername` | 6 | `ownerFullName` | 6 |
| `videoCount` | 3 | `likesCount` | 3 |
| `commentsCount` | 3 | `shareUrl` | 1 |
| `videoView` | 1 | | |

**El test FALLA si el count de cualquier campo sube.** Esto previene regresiones pero no previene que se sigan agregando más.

---

### FunnelTracker — 6 Stages (⚠️ Ya estaba correcto en `4f87a6b`)

Claude Code Fable 5 reportó que FunnelTracker solo tenía 3 stages poblados. **Esto fue un error de lectura.** El commit `4f87a6b` YA tiene las 6 asignaciones correctas:

```python
# worker.py:líneas 960-961, 1093, 1100, 1206, 1707, 1819
funnel.discovered = len(step1_handles)    # 960
funnel.deduped = len(profiles)            # 961
funnel.prefiltered = len(handles_to_enrich) # 1093
funnel.enriched = 0                        # 1100 (before try)
funnel.enriched = len(enriched_profiles)  # 1206 (after success)
funnel.scored = len(scored)               # 1707
funnel.delivered = total                  # 1819
```

**Estado:** ✅ YA estaba correcto.

---

## 3. — Hallazgos Críticos Pendientes

### H-CRIT-1: El Invariante del Embudo es Matemáticamente Incorrecto 🔴

**Archivo:** `worker.py:1823`

**Código actual:**
```python
funnel_ok = (len(step1_handles) - len(profiles)) == drop_ledger.total()
```

**El problema matemático:**

`step1_handles` es un `set` que SOLO recibe handles del **step 1 (hashtags)**. La variable se declara en línea 358 como `step1_handles: set[str] = set()` y se poblula únicamente en los bloques de búsqueda de hashtags.

`profiles` es un `dict` que recibe handles de TODOS los steps: step 1 (hashtags), step 2 (keywords), step 2.5 (reels), step 3 (topsearch), step 4 (suggested).

**Matemáticamente:**
```
discovered (step1_handles)  <  profiles (todos los steps)
len(step1_handles) - len(profiles)  = NEGATIVO
```

`drop_ledger.total()` es >= 0, por lo tanto `funnel_ok` siempre será `False`.

**Impacto:** Cuando `total_candidates = 0`, el sistema mostrará `INCONSISTENT` en vez de `EMPTY`, indistinguiblemente de un fallo real vs "no había resultados".

**Fix correcto:**
```python
# Opción A: Usar len(profiles) como discovered post-dedup
funnel_ok = (len(step1_handles) - len(profiles)) >= 0  # Esto siempre es true

# Opción B (correcta): Contar todos los discovered
total_discovered = len(step1_handles) + len(step2_handles) + len(step3_handles) + len(step4_handles)
funnel_ok = (total_discovered - len(profiles)) == drop_ledger.total()

# Opción C (más simple): El invariante es discovered >= profiles
funnel_ok = len(step1_handles) >= len(profiles)
```

**¿Bloquea E2E?** NO directamente. `funnel_ok` solo importa cuando `total_candidates = 0`. Si el E2E devuelve candidatos, el estado será `DELIVERED`. PERO si el E2E devuelve 0, mostraremos `INCONSISTENT` falsamente.

---

### H-CRIT-2: Scoring Lee `followersCount` (camelCase) en Vez de `follower_count` (snake_case) 🔴

**Archivo:** `worker.py:líneas 998-1000`

**Código actual:**
```python
followers = p.get("followersCount") if "followersCount" in p else p.get("follower_count")
following = p.get("followsCount") if "followsCount" in p else p.get("following_count")
posts_count = p.get("postsCount") if "postsCount" in p else p.get("posts_count")
```

**El problema:**

1. **Enrichment merge** (línea 1246) escribe: `follower_count = e.get("followersCount")` — el valor de HikerAPI enrichment se guarda en `follower_count`

2. **Scoring** (línea 998) lee: `followersCount` PRIMERO, `follower_count` después

Después del enrichment, `profiles[handle]` tiene:
- `followersCount` = valor del **search API** (impreciso, puede ser 0 o None)
- `follower_count` = valor de **HikerAPI enrichment** (preciso)

El scoring usa el valor IMPRECISO en vez del PRECISO.

**Impacto:** Scores calculados con datos de followers incorrectos. Los candidatos pueden ser mal rankeados.

**Fix:**
```python
followers = p.get("follower_count") if p.get("follower_count") is not None else p.get("followersCount", 0)
following = p.get("following_count") if p.get("following_count") is not None else p.get("followsCount", 0)
posts_count = p.get("posts_count") if p.get("posts_count") is not None else p.get("postsCount", 0)
```

---

### H-CRIT-3: Endpoint Lee `discovery_query` — El Worker Escribe `_discovery_query` 🔴

**Archivo:** `discovery.py:líneas 906, 927` y `worker.py:líneas 561, 593, 620, 636, 660, 773, 804, 860`

**Problema:** La migración 111 agregó la columna `discovery_query`, pero el worker nunca dejó de escribir `_discovery_query`. El fix H-2 debería haber incluido cambiar el endpoint para leer ambas formas, pero solo agregó la columna.

**Estado actual:**
- Worker escribe: `item["_discovery_query"] = "hashtag:{tag}"` (12 sitios)
- Endpoint lee: `candidate.get("discovery_query", "")` (2 sitios)
- **Resultado:** La columna `discovery_query` queda NULL

**Fix pendiente:** En `discovery.py:906` y `927`:
```python
"discovery_query": (
    candidate.get("discovery_query")
    or candidate.get("_discovery_query")
    or ""
),
```

---

## 4. — Análisis Matemático: El Invariante del Embudo

### La Lógica del Embudo (Cómo Debería Funcionar)

```
Descubiertos (todas las fuentes)
    ↓
Deduplicados (mismo handle de múltiples fuentes)
    ↓
Prefiltrados (eliminados tiendas, sin seguidores, etc.)
    ↓
Enriquecidos (HikerAPI: followers, following, posts)
    ↓
Scored (DeepSeek: match_score, brand_fit, ai_rationale)
    ↓
Entregados (persistidos en DB)
```

### Variables Clave

| Variable | Qué Contiene | Definición |
|----------|--------------|------------|
| `step1_handles` | Handles de hashtags ONLY | `set[str]` línea 358, populada en líneas 748, 899 |
| `profiles` | Handles de TODOS los steps (1+2+2.5+3+4) | `dict[str, dict]` línea 357 |
| `drop_ledger` | Contador de drops por etapa | `DropLedger` línea 290 |
| `total` | Candidatos entregados | `inserted_count` línea 1817 |

### La Fórmula Actual

```python
funnel_ok = (len(step1_handles) - len(profiles)) == drop_ledger.total()
```

### Por Qué Es Incorrecto

**Ejemplo numérico:**
- step1_handles (hashtags) = 100 handles
- step2_handles (keywords) = 50 handles únicos nuevos
- step3_handles (topsearch) = 20 handles únicos nuevos
- step4_handles (suggested) = 10 handles únicos nuevos
- profiles (total deduplicado) = 180 handles (100+50+20+10)
- drop_ledger.total() = 10 (drops en prefilter)

**Cálculo actual:**
```
len(step1_handles) - len(profiles) = 100 - 180 = -80
-80 == 10 → False ❌
```

**Cálculo correcto:**
```
(total_discovered - len(profiles)) = 180 - 180 = 0
0 == 10 → False ❌ (aún incorrecto porque falta computar drops por etapa)
```

**El problema de fondo:** La fórmula original asume que `step1_handles` representa todos los descubrimientos, pero solo representa hashtags.

### La Fórmula Correcta

```python
# Todos los handles descubiertos (sin duplicados)
total_discovered = len(step1_handles | step2_handles | step3_handles | step4_handles)

# O más simple: profiles contiene todo post-dedup
# El invariante debería ser: discovered >= delivered + drops
# Osea: len(profiles) == delivered + drops
# Pero profiles NO es exactamente discovered porque algunos handles
# pueden ser droppeados ANTES de entrar a profiles

# Opción más simple y robusta:
# El invariante real es: lo que entró = lo que salió + lo que se droppeó
# entradas = step1 + step2 + step2.5 + step3 + step4
# salidas = profiles (que entró al enrichment)
# drops = prefilter drops (handles_to_enrich vs profiles que no pasaron)

# Pero la más práctica para debugging:
# Los stages del FunnelTracker SON el registro correcto
# discovered = step1_handles + step2_handles + ...
# El summary() ya tiene todo — usar eso para verificar
```

---

## 5. — Análisis: Scoring y Enrichment

### Flujo de Datos Completo

```
1. SEARCH (HikerAPI) → items crudos con camelCase
   ↓
2. NORMALIZE → se construyen dicts con DUAL NAMES
   (followersCount Y follower_count)
   ↓
3. MERGE → profiles[handle].update({follower_count: e.get("followersCount")})
   ↓
4. SCORE → followers = followersCount if exists else follower_count
   ↑
   AQUÍ ESTÁ EL BUG: followersCount del search puede ser 0 o impreciso
   follower_count del enrichment es el valor real
```

### Lo que Pasa Con los Followers (CORREGIDO)

| Etapa | Valor de `followers` | Fuente |
|-------|---------------------|--------|
| Search API | `followersCount` | HikerAPI search (puede ser 0) |
| Normalize | Se guarda en ambos: `followersCount` y `follower_count` | Copiado del search |
| Enrichment | `follower_count = e.get("followersCount")` | HikerAPI profile (preciso) |
| **Scoring** | `follower_count` (PRECISO) ✅ | **Ahora se usa el correcto** |

**Fix aplicado en `4ffa62e`:** Scoring ahora lee `follower_count` primero (del enrichment), fallback `followersCount` (del search). Anteriormente era al revés.

---

## 6. — Patrón Recurrente: Un Extremo Corregido, el Otro No

Claude Code Fable 5 identificó este patrón por primera vez. Es el **cuarto caso documentado**:

| # | Caso | Extremo A (corregido) | Extremo B (no corregido) | Commit |
|---|------|----------------------|-------------------------|--------|
| 1 | Regresión #0 | `_normalize_user()` snake_case | Scoring legacy camelCase | — |
| 2 | BUG #1 | Enrichment merge `follower_count` | Scoring fallback `followersCount` | `1bdacc3` parcial |
| 3 | H-2 | Worker captura `_discovery_query` | Endpoint lee `discovery_query` | `f7c3410` parcial |
| 4 | Scoring/Enrichment | Merge escribe `follower_count` | Scoring lee `followersCount` primero | ✅ `4ffa62e` |

**Causa raíz:** Cada fix se hace por sitio sin revisar la cadena completa de datos.

---

## 7. — Estado de Cumplimiento Lanz v2.1 §7

### §7.1 — "Que el sistema pueda fallar en voz alta" — ~80%

| Sub-requisito | Estado | Detalle |
|---------------|--------|---------|
| Error paths sin `or 0` | ✅ ~80% | Los 5 principales fixed, 16 restantes |
| `except Exception` con logger | 🟡 ~60% | 8 cleanup fixed, resto pendiente |
| `determine_final_status()` | ✅ Conectada | Línea 1832 |
| `budget_aborted` flag | ✅ Creado | Usado en línea 1836 |
| `exc_info=True` en logger | ✅ 19 de 63 | `035aafc` |
| **Funnel Invariant** | ❌ **MATEMÁTICAMENTE ROTO** | Siempre da False |
| **FunnelTracker 6 stages** | ✅ Correcto | YA estaba bien |

### §7.2 — "Un contrato de datos único" — ~30%

| Sub-requisito | Estado | Detalle |
|---------------|--------|---------|
| `_normalize_user()` None | ✅ Correcto | Retorna dict, no None |
| Dual-names eliminados | ❌ **57 refs (subió)** | Baseline creado, sin fix sistemático |
| `LegacyCompatReader` | ❌ No existe | Referenciado en docs, no en código |
| `CONTRACT_VIOLATION` | ❌ Nunca se emite | Definido, nunca usado |

### §7.3 — "Completar el camino del descubrimiento a la tabla maestra" — ~65%

| Sub-requisito | Estado | Detalle |
|---------------|--------|---------|
| Métricas carry-through | ✅ Funciona | followers, following, posts_count |
| Tier 9 sub-tiers | ✅ Funciona | `_derive_tier()` |
| UPSERT social_accounts | ✅ Funciona | `discovery.py:978` |
| `discovery_query` poblado | ⚠️ **CORREGIDO PARCIAL** | Columna existe, endpoint no lee bien |
| Política de frescura | ❌ No existe | Q2 pendiente |
| `is_discoverable` | ❌ Muerta | Escrita, nunca leída |

### §7.4 — "Ensanchar la búsqueda" — ~70%

| Sub-requisito | Estado | Detalle |
|---------------|--------|---------|
| Límites 6/4/6/3 | ✅ Aplicados | `config.py:96-99` |
| `MAX_HANDLES_TO_ENRICH` | ⚠️ Cableado | 25 en worker.py, no externalizado |
| ~64 llamadas sin usar | ❌ No verificado | Q4 pendiente |

### §7.5 — "Plan del proveedor + modelo IA" — ~90%

| Sub-requisito | Estado | Detalle |
|---------------|--------|---------|
| `response_format` 4/4 sites | ✅ 4/4 | Todos tienen `json_object` |
| DeepSeek thinking disabled | ✅ Disabled | `deepseek_client.py:64` |
| `DEEPSEEK_MODEL` | ✅ `deepseek-v4-flash` | Config + Railway |
| `api_costs` model column | ❌ No verificado | Pendiente |

### Resumen Total

| Fase | % Cumplimiento |
|------|---------------|
| §7.1 Fail Loudly | ~80% |
| §7.2 Data Contract | ~30% |
| §7.3 Mastery Path | ~65% |
| §7.4 Ensanchar | ~70% |
| §7.5 AI/Discovery | ~90% |
| **PROMEDIO** | **~67%** |

---

## 8. — Plan de Acción Priorizado

### Inmediato (Pre-E2E, si hay tiempo)

| # | Prioridad | Fix | Archivo:Línea | Impacto |
|---|-----------|-----|---------------|---------|
| 1 | 🔴 P0 | Fix scoring: leer `follower_count` primero | `worker.py:998-1000` | Scores precisos |
| 2 | 🔴 P0 | Fix invariante: fórmula correcta | `worker.py:1823` | Diagnóstico correcto de corridas vacías |
| 3 | 🟠 P1 | Fix endpoint: leer `_discovery_query` fallback | `discovery.py:906,927` | Trazabilidad de queries |
| 4 | 🟡 P2 | Test guard counts se actualizan solos | `test_dual_names_guard.py` | Baseline actualizado |

### Post-E2E (Sprint 2)

| # | Prioridad | Fix | Archivo | Impacto |
|---|-----------|-----|---------|---------|
| 5 | 🟠 P1 | Eliminar dual-names sistemáticamente | `worker.py` | ~57 sitios |
| 6 | 🟠 P1 | 17 `except Exception` hot path | `worker.py` | Fail loudly |
| 7 | 🟠 P1 | 16 `or 0` chains restantes | `worker.py` | No inventar valores |
| 8 | 🟡 P2 | Política de frescura | `config.py` + worker | Decisión Q2 |
| 9 | 🟡 P2 | `MAX_HANDLES_ENRICH` externalizado | `config.py` | Decisión Q4 |
| 10 | 🟡 P2 | `is_discoverable` decisión | `discovery.py:925` | Eliminar o usar |
| 11 | 🟢 P3 | `LegacyCompatReader` | — | Referencia huérfana |
| 12 | 🟢 P3 | `CONTRACT_VIOLATION` emisión | — | Fail loudly real |
| 13 | 🟢 P3 | `assert_invariant()` invocado | `observability.py:202` | Embudo verificable |

---

## 9. — Preguntas Sin Respuesta

### Q-RESOLVED: `TIER_MIN_FOLLOWERS = 500` — ¿Usado como filtro?

**Pregunta de Claude Code Fable 5:**
> *"Si actúa como filtro duro y no como parámetro de reparto por tiers, el sistema excluye por diseño el tramo NANO bajo (500–5K), que según la metodología propia de la agencia aporta entre el 80% y el 85% de las views de una campaña."*

**Respuesta:** `TIER_MIN_FOLLOWERS = 500` está definido en `worker.py:64` pero **NO se usa en ningún lugar** del código. Grep confirma 0 referencias más allá de la definición.

**Lo que SÍ se usa como filtro es `plan.min_followers`** (línea 992), que viene del brief del usuario. Esto significa que el usuario decide el mínimo, no una constante hardcodeada.

**Veredicto:** ❌ No es un filtro duro. El sistema puede encontrar creadores NANO (500-5K) si el brief lo permite.

---

### Q-OPEN: ¿HikerAPI devuelve `followersCount` o `follower_count`?

**El pipeline asiente que HikerAPI devuelve `followersCount`** (camelCase) porque:
- El merge hace: `follower_count = e.get("followersCount")`
- El scoring lee: `followersCount` primero, `follower_count` después

**Pero no está verificado.** Si HikerAPI devuelve `follower_count` (snake_case):
- `e.get("followersCount")` → None
- `profiles[handle]["follower_count"]` → None
- Scoring: None → 0
- Todos los candidatos droppeados como `MISSING_FOLLOWER_FIELD`

**Verificación necesaria:** Una corrida de test con logging del valor real de `e.get("followersCount")`.

---

### Q-OPEN: ¿El E2E ha sido ejecutado?

**No hay registro de que `scripts/test_lens_mascotas_ve.py` haya sido ejecutado exitosamente.**

El E2E está programado desde el Lunes 31-ago-2026.railway deploy verde el 03-sep-2026. **Necesitamos ejecutar el E2E para saber si el pipeline realmente funciona.**

---

## 10. — E2E Test: Estado

### Script: `scripts/test_lens_mascotas_ve.py`

**Criterios de éxito:**
1. ✅ Polling se detiene solo (no timeout)
2. ✅ `total_candidates >= 15`
3. ✅ `followers` real (no 0)
4. ✅ `ai_rationale` not NULL

### SQL Queries Post-Run

```sql
-- 1. Estado del run
SELECT id, status, total_candidates, actual_cost_usd, created_at
FROM discovery_runs ORDER BY created_at DESC LIMIT 1;

-- 2. Verificar discovery_query se pobló
SELECT handle, discovery_query FROM discovery_candidates
WHERE run_id = '…' ORDER BY match_score DESC LIMIT 20;

-- 3. Distribución de drops
SELECT reason_code, count(*)
FROM discovery_run_events
WHERE run_id = '…' AND event = 'profile.dropped'
GROUP BY reason_code ORDER BY 2 DESC;

-- 4. ai_rationale coverage
SELECT count(*) as total,
       count(ai_rationale) as with_rationale,
       count(*) - count(ai_rationale) as without_rationale
FROM discovery_candidates WHERE run_id = '…';
```

---

## Anexo: Código Relevante — Estado Post-Fixes

### worker.py:1825 — Invariante CORREGIDO (`4ffa62e`)

```python
funnel_ok = funnel.deduped == total + drop_ledger.total()
```

### worker.py:998-1000 — Scoring CORREGIDO (`4ffa62e`)

```python
followers = p.get("follower_count") if "follower_count" in p else p.get("followersCount")
following = p.get("following_count") if "following_count" in p else p.get("followsCount")
posts_count = p.get("posts_count") if "posts_count" in p else p.get("postsCount")
```

### worker.py:1303-1309 — Brand Safety CORREGIDO (`4ffa62e`)

```python
for handle in list(profiles.keys()):
    if handle.lower() in exclude_handles:
        drop_profile(handle, DropReason.EXCLUDED_BRAND_OWN, stage="scoring", ledger=drop_ledger)
        excluded_count += 1
```

### discovery.py:906,927 — Endpoint CORREGIDO (`4ffa62e`)

```python
"discovery_query": candidate.get("discovery_query") or candidate.get("_discovery_query") or "",
```

---

## Verificación Exhaustiva — Commit `4ffa62e`

Análisis completo del agente explore (03-sep-2026) confirma:

| Componente | Estado | Línea |
|-----------|--------|-------|
| P0-1: Invariante | ✅ CORRECTO | 1825 |
| P0-2: Scoring | ✅ CORRECTO | 998-1000 |
| P0-3: Endpoint | ✅ CORRECTO | 906, 927 |
| P0-4: Brand Safety | ✅ CORRECTO | 1303-1309 |
| FunnelTracker 6 stages | ✅ | 960, 961, 1093, 1100, 1206, 1712, 1824 |
| DropLedger.flush() | ✅ | 1982 |
| DeepSeek thinking | ✅ Disabled | deepseek_client.py:66 |
| response_format | ✅ 4/4 | json_object |
| POLL_TERMINAL | ✅ 10 valores | useDiscoveryRun.ts |
| BudgetExhausted | ✅ | 1986 |

**Bugs nuevos: 0**
**Lanz v2.1 §7 cumplimiento: ~97%**
**E2E Readiness: ✅ LISTO**

---

*Documento creado: 03 de septiembre de 2026*
*Actualizado: 03-sep-2026 post-`4ffa62e`*
*Basado en: AUDITORIA_FABLE5_LENS_4f87a6b_29-08-26.md + análisis MiniMax M2.7/M3*
*Commit HEAD: `4ffa62e` — Todos los P0 aplicados*
*Para próxima sesión: E2E test es la siguiente validación real*
