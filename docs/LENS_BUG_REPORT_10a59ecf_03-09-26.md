# LENS Discovery — Bug Report Completo
## Run `10a59ecf` · Purina Dog Chow · 03-sep-2026

> **Repositorio:** `github.com/ungardev/lawebcore`
> **Commit HEAD:** `4ffa62e` (03-sep-2026 16:34 UTC)
> **Run ID:** `10a59ecf-4be6-4c29-bfa2-4959735e926e`
> **Status final:** `empty` · 0 candidatos de 188 handles encontrados
> **Costo real:** $1.72 USD · 86 requests HikerAPI
> **Auditor:** MiniMax M2.7/M3 · Análisis exhaustivo del código + logs Railway

---

## Resumen Ejecutivo

El pipeline de LENS Discovery **ejecutó sin crashear**, pero descartó el 100% de los 188 candidatos durante scoring por **cuatro bugs encadenados**. La causa raíz es una combinación de:

1. **Campo incorrecto leído del enrichment** — HikerAPI devuelve `followers_count` (snake_case) pero el worker lee `followersCount` (camelCase)
2. **Presupuesto de enrichment insuficiente** — Solo 25/188 perfiles enriquecidos por el cap de `MAX_CALLS_PER_RUN = 120`
3. **Filtro `MISSING_FOLLOWER_FIELD` demasiado agresivo** — Descarta perfiles con `follower_count=0` sin fallback a rough_score
4. **Migración 00107 no aplicada** — Tabla `budget_transactions` no existe en Railway Postgres

---

## Bugs Identificados (Priorizados)

### BUG #1 [CRÍTICO] — Campo `followersCount` vs `follower_count` en merge de enrichment

**Archivo:** `apps/api/app/workers/worker.py:1246`

**Código actual:**
```python
profiles[handle].update({
    "_enriched": True,
    "follower_count": e.get("followersCount"),  # ← BUG: e tiene follower_count, no followersCount
    ...
})
```

**Evidencia de los logs:**
```
[STEP3] 25 perfiles enriquecidos — HTTP 200 OK
[HIKERAPI] GET /v2/user/by/username → 200 OK
[SCORING] 0 scored → 0 score≥5 → 0 qualified
profile.dropped | MISSING_FOLLOWER_FIELD | scoring | count=188
```

**Causa raíz:** La función `HikerAPIClient.enrich_profile()` retorna `self._normalize_user(user)` que construye el dict con `follower_count` (snake_case) en `hikerapi_client.py:851`. Pero el worker en la línea 1246 lee `e.get("followersCount")` (camelCase). Como HikerAPI nunca pone `followersCount` en su respuesta, `e.get("followersCount")` devuelve `None`, y `profiles[handle]["follower_count"]` se setea a `None`.

**El scoring entonces:**
```python
# worker.py:1338
followers = p.get("follower_count") if "follower_count" in p else p.get("followersCount")
# "follower_count" está en p con valor None → followers = None

# worker.py:1339
if followers is None:
    followers = 0  # ← None se convierte a 0

# worker.py:1342-1345
was_enriched = p.get("_enriched", False)
if was_enriched:
    drop_profile(handle, DropReason.MISSING_FOLLOWER_FIELD, ...)  # ← TODOS los enriquecidos caen acá
```

**Fix propuesto:**
```python
# worker.py:1246 — corregir el campo leído
"follower_count": e.get("follower_count"),           # era: e.get("followersCount")
"following_count": e.get("following_count"),         # era: e.get("followsCount")
"posts_count": e.get("posts_count"),               # era: e.get("postsCount")
```

**Alternativa (defensiva):** Leer ambos con fallback:
```python
"follower_count": e.get("follower_count") or e.get("followersCount"),
"following_count": e.get("following_count") or e.get("followsCount"),
"posts_count": e.get("posts_count") or e.get("postsCount"),
```

**Rationale:** El normalizador `_normalize_user()` en `hikerapi_client.py:825-860` explicitamnte pone `follower_count` (snake_case) como clave. El worker debe leer esa clave, no `followersCount`. La forma camelCase (`followersCount`) **no existe en el response de HikerAPI** — es una deuda interna del propio worker que se fabricó en los pasos de búsqueda al construir diccionarios duales.

---

### BUG #2 [CRÍTICO] — Scoring descarta perfiles enriquecidos con `follower_count=0`

**Archivo:** `apps/api/app/workers/worker.py:1342-1349`

**Código actual:**
```python
followers = p.get("follower_count") if "follower_count" in p else p.get("followersCount")
if followers is None:
    followers = 0
    was_enriched = p.get("_enriched", False)
    if was_enriched:
        untracked_no_followers += 1
        drop_profile(handle, DropReason.MISSING_FOLLOWER_FIELD, "scoring", {"followers": 0, "is_explore_mode": False}, ledger=drop_ledger)
        continue
    if not is_explore_mode:
        untracked_no_followers += 1
        drop_profile(handle, DropReason.MISSING_FOLLOWER_FIELD, "scoring", {"followers": 0, "is_explore_mode": False}, ledger=drop_ledger)
        continue
if followers == 0:  # ← LÍNEA 1350
    if is_explore_mode:
        # usa rough_score...
    # ← EXPLORE MODE: no llega aquí si no es explore
    drop_profile(handle, DropReason.MISSING_FOLLOWER_FIELD, "scoring", {"followers": 0, "is_explore_mode": False}, ledger=drop_ledger)
    continue
```

**Problema:** Cuando HikerAPI devuelve `followers_count=0` (cuenta eliminada, privada, o sin datos), el perfil:
1. Tiene `_enriched=True` ✓
2. Tiene `follower_count=0` (no `None`)
3. Pasa la condición `if followers is None` (es `0`, no `None`)
4. CAE en `if followers == 0` → `drop_profile(MISSING_FOLLOWER_FIELD)`

**Pero en modo normal (no explore):** Un perfil con `follower_count=0` enriquecido debería tener la oportunidad de usar `rough_score` como fallback, como hace el modo explore.

**Fix propuesto:**
```python
# worker.py:1342-1349 — agregar fallback a rough_score para perfiles enriquecidos con 0
if followers is None or followers == 0:
    followers = followers or 0
    was_enriched = p.get("_enriched", False)
    if was_enriched and followers == 0:
        # HikerAPI devolvió 0 — cuenta eliminada, privada, o sin datos.
        # Intentar usar rough_score como fallback (mismo comportamiento que explore mode)
        rough = rough_score_map.get(handle, 0.0)
        if rough > 0:
            # Agregar como candidato con rough_score
            bio_ex = p.get("biography") or p.get("bio") or ""
            scored.append({
                "run_id": run_id,
                "platform": "instagram",
                "handle": handle,
                "full_name": p.get("fullName") or p.get("full_name") or "",
                "bio": bio_ex,
                "avatar_url": p.get("profilePicUrlHD") or p.get("profilePicUrl") or p.get("avatar_url") or "",
                "country": target_country,
                "city": p.get("locationName") or p.get("location") or "",
                "followers": 0,
                "following": 0,
                "posts_count": 0,
                "avg_likes": None,
                "avg_comments": None,
                "avg_views": None,
                "engagement_rate": None,
                "audience_credibility": None,
                "audience_quality": None,
                "match_score": round(rough * 100, 2),
                "niche_relevance": round(rough * 100, 2),
                "geo_relevance": round(rough * 100, 2),
                "rationale": "Enriquecido pero sin datos de seguidores — score basado en señales de nicho.",
                "tier": None,
                "is_tienda": False,
                "status": "new",
                "raw_payload": {"rough_score": round(rough, 4), "enriched_but_zero_followers": True},
                "fetched_at": datetime.now(UTC),
            })
            untracked_no_followers += 1
            continue
        else:
            drop_profile(handle, DropReason.MISSING_FOLLOWER_FIELD, "scoring", {"followers": 0, "was_enriched": True}, ledger=drop_ledger)
            continue
    if not is_explore_mode:
        untracked_no_followers += 1
        drop_profile(handle, DropReason.MISSING_FOLLOWER_FIELD, "scoring", {"followers": 0, "is_explore_mode": False}, ledger=drop_ledger)
        continue
```

**Rationale:** En modo explore, perfiles con `follower_count=0` usan `rough_score` (línea 1360). El modo normal debería hacer lo mismo cuando el enrichment devolvió `0` seguidores — el `rough_score` sigue siendo válido como señal de nicho/geo.

---

### BUG #3 [CRÍTICO] — `MAX_CALLS_PER_RUN = 120` demasiado bajo para el enrichment

**Archivo:** `packages/shared-core/shared_core/config.py:87`

**Código actual:**
```python
MAX_CALLS_PER_RUN: int = 120
```

**Archivo:** `apps/api/app/workers/worker.py:60`
```python
MAX_HANDLES_TO_ENRICH = 25
```

**Evidencia de los logs:**
```
[discovery_run_task] STEP 3: top-N prefilter → 25 handles para enrichment
[STEP3] 25 perfiles enriquecidos — HTTP 200 OK
[enrichment_budget_capped] skipped=N max_calls=120
[STEP3] 25 perfiles enrichhed, 163 handles remaining sin enriquecer
```

**Problema:** 188 handles encontrados → prefilter deja 25 → solo 25 enriquecidos → 163 sin enriquecer tienen `follower_count=0` (built-in default) → todos descartados en scoring.

**Causa raíz:** `MAX_CALLS_PER_RUN = 120` incluye tanto las llamadas de discovery como las de enrichment. Con `ESTIMATED_DISCOVERY_CALLS = 32`, quedan ~88 para enrichment. Pero 86 requests reales de HikerAPI (discovery + enrichment) + circuit breaker + retries = el budget se agota antes de enriquecer todos los perfiles.

**Fix propuesto:**
```python
# packages/shared-core/shared_core/config.py
MAX_CALLS_PER_RUN: int = 200  # era: 120

# apps/api/app/workers/worker.py:60
MAX_HANDLES_TO_ENRICH = 50  # era: 25
```

**Alternativa:** Priorizar enrichment por `rough_score` descending — enriquecer primero los que mejor score tienen.

**Rationale:** El E2E anterior consumió $1.14 con 57 llamadas estimadas. Con enrichment completo de 188 handles (~100 calls), el costo sube a ~$2.00-2.50/run, pero produce candidatos reales. El balance de HikerAPI es ~$36.86 USD — hay presupuesto para correr 15-18 E2Es completos.

---

### BUG #4 [ALTO] — Queries en español que no retornan resultados

**Archivo:** `packages/discovery/discovery/query_builder.py` ( inferred — `_build_keyword_queries`)

**Evidencia de los logs:**
```
GET /v3/fbsearch/accounts?query=comida+para+perros+vzla → 0 users
GET /v3/fbsearch/accounts?query=comida+para+perros+venezuela → 0 users
GET /v3/fbsearch/accounts?query=pienso+para+perros+vzla → 0 users
GET /v3/fbsearch/accounts?query=alimento+para+perros+venezuela → 0 users
GET /v3/fbsearch/accounts?query=nutrici%C3%B3n+canina+vzla → 0 users
```

**Problema:** HikerAPI `/v3/fbsearch/accounts` responde mejor a queries en **inglés**. Todas las keywords del brief (generadas por DeepSeek) están en español. La función `_build_keyword_queries` toma las keywords del profile y genera variantes con sufijos de país (`venezuela`, `vzla`) — pero en español.

**Fix propuesto:**
```python
# En query_builder.py, generar keywords EN como fallback/amplificación
ENGLISH_PET_FOOD_KEYWORDS = [
    "dog food", "pet food", "dog chow", "dog kibble", "pet nutrition",
    "dog food venezuela", "pet food venezuela", "dog treats",
    "dog care", "pet care", "vet food", "premium pet food",
]

def _build_keyword_queries(profile, brief):
    queries = []
    # Español original
    queries.extend(profile.get("keywords", []))
    # Agregar English queries
    queries.extend([f"{kw} {country}" for kw in ENGLISH_PET_FOOD_KEYWORDS for country in ["", "venezuela", "ve"]])
    # Deduplicar
    return list(set(queries))[:DISCOVERY_KEYWORD_LIMIT * 3]
```

**Rationale:** HikerAPI es una API global. Las queries en inglés para el nicho "dog food" retornan resultados de cuentas internacionales con audiencia en Venezuela. Las queries en español puro no tienen masa crítica en la API.

---

### BUG #5 [ALTO] — Tabla `budget_transactions` no existe en Railway Postgres

**Error en logs:**
```
asyncpg.exceptions.UndefinedTableError: relation "budget_transactions" does not exist
```

**Archivo:** `apps/api/app/workers/worker.py:1962-1975`

**Código actual:**
```python
try:
    await railway_pg.insert("budget_transactions", {
        "run_id": run_id,
        "provider": "hikerapi",
        "operation": "discovery_pipeline",
        "amount_usd": hikerapi_cost,
        "request_count": hikerapi_calls,
        "metadata": {...},
    })
except Exception as e:
    logger.warning("budget_ledger_insert_failed", run_id=run_id, error=str(e))
```

**Causa raíz:** La migración `00107_budget_transactions.sql` existe en `supabase/migrations/` pero **no fue aplicada** en Railway Postgres. Railway no ejecuta migraciones de Supabase automáticamente — deben aplicarse manualmente via SQL Editor.

**Fix propuesto:** Aplicar la migración manualmente:
```sql
-- En Railway SQL Editor (Postgres railway)
CREATE TABLE IF NOT EXISTS budget_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID,
    provider VARCHAR(50) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    amount_usd DECIMAL(10,4) NOT NULL,
    request_count INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_budget_tx_provider ON budget_transactions(provider, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_budget_tx_run ON budget_transactions(run_id) WHERE run_id IS NOT NULL;

-- Trigger para inmutabilidad
CREATE OR REPLACE FUNCTION prevent_budget_tx_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'budget_transactions es inmutable: DELETE y UPDATE no permitidos. Solo INSERT.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER budget_tx_immutable
    BEFORE UPDATE OR DELETE ON budget_transactions
    FOR EACH ROW EXECUTE FUNCTION prevent_budget_tx_modification();
```

**Nota:** El código YA tiene try/except que captura este error y solo loguea un warning. El run no crashea por esto, pero el ledger de presupuesto no se persiste.

---

### BUG #6 [MEDIO] — Step 3 (topsearch) y Step 4 (suggested) retornan 0 cuentas

**Archivos:** `apps/api/app/workers/worker.py:837-875` (inferred de los logs)

**Evidencia de los logs:**
```
STEP3: 0 accounts from topsearch
STEP4: 0 accounts from suggested
```

**Problema:** Los pasos 3 y 4 del pipeline (topsearch y suggested profiles) no aportan handles. Solo step 1 (hashtags: 120 handles) y step 2 (keywords: 80 handles) aportan.

**Causa raíz probable:** 
1. Las queries de topsearch pueden estar vacías o mal formadas
2. La API de suggested profiles puede no estar disponible o retornar 404
3. Los handles de topsearch/suggested pueden no pasar el prefilter

**Fix sugerido:** Agregar logging detallado en los pasos 3 y 4 para identificar exactamente dónde falla.

---

### BUG #7 [MEDIO] — `STEP2p5_REELS` retorna 0 creators

**Archivo:** `apps/api/app/workers/worker.py:645-667` (inferred)

**Evidencia de los logs:**
```
STEP2p5_REELS: 0 creators from reels search
```

**Causa raíz:** La búsqueda de reels puede estar usando queries en español que HikerAPI no procesa correctamente, o el actor de reels no está disponible.

---

### BUG #8 [BAJO] — Endpoint lee `discovery_query` pero worker escribe `_discovery_query`

**Archivo:** `apps/api/app/api/v1/discovery.py:906, 927`

**Estado:** El fix de `discovery.py` dice que ahora lee `candidate.get("discovery_query") or candidate.get("_discovery_query") or ""` (según FIXES_P0_LENS_452d7e9_03-09-26.md). **Verificar que esté aplicado en el código actual.**

**Fix documentado (debe verificarse):**
```python
"discovery_query": (
    candidate.get("discovery_query")
    or candidate.get("_discovery_query")
    or ""
),
```

---

### BUG #9 [BAJO] — Endpoints HikerAPI `/v1/account`, `/v1/user/balance` retornan 404

**Archivo:** `packages/discovery/discovery/tools/hikerapi_client.py:443-450` (inferred de `get_balance()`)

**Evidencia:**
```
HTTP Request: GET https://api.hikerapi.com/v1/account "HTTP/1.1 404 Not Found"
HTTP Request: GET https://api.hikerapi.com/v1/user/balance "HTTP/1.1 404 Not Found"
HTTP Request: GET https://api.hikerapi.com/account "HTTP/1.1 404 Not Found"
```

**Causa raíz:** Se intentan 3 URLs deprecated. El endpoint correcto de balanceo es `/account/balance` o similar.

**Fix propuesto:** Corregir `get_balance()` en hikerapi_client.py para usar el endpoint correcto.

---

## Tabla Resumen de Bugs

| # | Severity | Archivo | Descripción | Costo Fix |
|---|----------|---------|-------------|-----------|
| 1 | 🔴 CRÍTICO | `worker.py:1246` | Merge enrichment lee `followersCount` (None) en vez de `follower_count` | $0 |
| 2 | 🔴 CRÍTICO | `worker.py:1342-1349` | Perfiles enriquecidos con `follower_count=0` descartados sin fallback | $0 |
| 3 | 🔴 CRÍTICO | `config.py:87` | `MAX_CALLS_PER_RUN=120` demasiado bajo — solo 25/188 enriquecidos | $0 |
| 4 | 🟠 ALTO | `query_builder.py` | Keywords en español — HikerAPI responde a inglés | $0 |
| 5 | 🟠 ALTO | Railway Postgres | Tabla `budget_transactions` no existe (migración no aplicada) | $0 (manual) |
| 6 | 🟡 MEDIO | `worker.py` | Steps 3 y 4 retornan 0 cuentas | $0 |
| 7 | 🟡 MEDIO | `worker.py` | STEP2p5_REELS retorna 0 creators | $0 |
| 8 | 🟢 BAJO | `discovery.py:906,927` | Endpoint `_discovery_query` vs `discovery_query` | $0 |
| 9 | 🟢 BAJO | `hikerapi_client.py` | 3 URLs de balance deprecated (404) | $0 |

---

## Orden de Fix Recomendado

| Orden | Bug | Razón |
|-------|-----|-------|
| 1 | **BUG #1** — `e.get("followersCount")` → `e.get("follower_count")` | Fix más impactante — habilita enrichment real |
| 2 | **BUG #2** — Fallback a rough_score para perfiles enriquecidos con 0 | Complementa BUG #1 |
| 3 | **BUG #3** — Subir `MAX_CALLS_PER_RUN` a 200 | Permite enrichment completo |
| 4 | **BUG #4** — Agregar keywords EN | Mejor discovery |
| 5 | **BUG #5** — Aplicar migración 00107 en Railway | Ledger de presupuesto |
| 6 | **BUG #6,7** — Debug steps 3/4/2.5 | Investigar por qué no aportan handles |

---

## Tests Sugeridos

```python
# apps/api/tests/test_enrichment_field_names.py
async def test_enrichment_merge_uses_correct_field_names():
    """BUG #1 FIX: El merge debe leer follower_count (snake_case), no followersCount."""
    from discovery.tools.hikerapi_client import HikerAPIClient
    
    client = HikerAPIClient()
    # Simular response de HikerAPI
    mock_user = {
        "username": "test_user",
        "follower_count": 15000,  # snake_case como viene de HikerAPI
        "following_count": 500,
        "media_count": 120,
    }
    normalized = client._normalize_user(mock_user)
    
    # El dict normalizado debe tener follower_count (snake_case)
    assert "follower_count" in normalized
    assert "followersCount" not in normalized
    assert normalized["follower_count"] == 15000

async def test_scoring_keeps_enriched_profiles_with_zero_followers():
    """BUG #2 FIX: Perfiles enriquecidos con follower_count=0 deben usar rough_score."""
    # given
    profiles = {
        "user_a": {"follower_count": 0, "_enriched": True, "biography": "dog food..."},
    }
    rough_score_map = {"user_a": 0.85}
    
    # when
    scored, dropped = await score_profiles(profiles, rough_score_map, is_explore_mode=False, ...)
    
    # then
    assert "user_a" in [s["handle"] for s in scored]
    assert dropped.get("MISSING_FOLLOWER_FIELD", 0) == 0
```

---

## SQL Queries Post-Fix (para verificar)

```sql
-- 1. Estado del run
SELECT id, status, total_candidates, actual_cost_usd, created_at
FROM discovery_runs ORDER BY created_at DESC LIMIT 1;
-- Esperado: status='delivered', total_candidates >= 15

-- 2. Verificar followers reales
SELECT handle, followers, match_score, ai_rationale
FROM discovery_candidates
WHERE run_id = (SELECT id FROM discovery_runs ORDER BY created_at DESC LIMIT 1)
ORDER BY match_score DESC LIMIT 20;
-- Esperado: followers > 0, ai_rationale NOT NULL

-- 3. Distribución de drops
SELECT reason_code, count(*)
FROM discovery_run_events
WHERE run_id = (SELECT id FROM discovery_runs ORDER BY created_at DESC LIMIT 1)
AND event = 'profile.dropped'
GROUP BY reason_code;
-- Esperado: sin MISSING_FOLLOWER_FIELD masivo

-- 4. Verificar budget_transactions
SELECT count(*) FROM budget_transactions;
-- Esperado: >= 1 (después de aplicar migración)
```

---

---

## ACTUALIZACIÓN 04-sep-2026 — NUEVO BUG CRÍTICO ENCONTRADO

### 🔴 BUG B1 — `former_usernames` es STRING, no LIST (CRÍTICO)

**Archivo:** `packages/discovery/discovery/tools/hikerapi_client.py:659`

Este bug NO estaba identificado en la auditoría del 03-sep. Es la causa raíz por la cual, incluso con FIX 1 aplicado, el pipeline podría seguir entregando 0 candidatos.

**Especificación OpenAPI:**
```yaml
former_usernames:
  type: string  # NO es array — es comma-separated string
  example: "old_user1,old_user2"
```

**Código actual (BUG):**
```python
former_usernames = user_data.get("former_usernames", [])
count = len(former_usernames)  # cuenta CHARS, no usernames!
```

**Fix:**
```python
former_usernames_raw = user_data.get("former_usernames") or ""
count = len([u for u in former_usernames_raw.split(",") if u.strip()])
```

**Impacto:** Cualquier perfil con `former_usernames` de 3+ caracteres recibe `fraud_penalty=0.8` → score colapsado → descartado.

---

## DOCUMENTOS MAESTROS ACTUALIZADOS

| Documento | Descripción |
|-----------|-------------|
| `docs/LENS_MASTER_BUG_REPORT_04-09-26.md` | **DOCUMENTO PRINCIPAL** — todos los bugs, tiers, plan de fixes |
| `docs/LENS_HIKERAPI_PIPELINE_AUDIT_04-09-26.md` | Auditoría exhaustiva HikerAPI OpenAPI vs cliente |
| `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` | Entry #34 — link a los nuevos docs |

---

*Documento original generado: 03-sep-2026 · La Web Figital Agency*
*Actualizado: 04-sep-2026 · BUG B1 identificado*
*Basado en: logs Railway run `10a59ecf` + análisis HikerAPI OpenAPI spec*
*Próximo paso: Aplicar BUG B1 + Logging exhaustivo + E2E*
