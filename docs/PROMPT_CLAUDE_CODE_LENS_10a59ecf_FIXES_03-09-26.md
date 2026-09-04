# PROMPT COMPLETO PARA CLAUDE CODE — LENS Discovery Fix
## Run `10a59ecf` · 03-sep-2026 · La Web Figital Agency

---

## CONTEXTO CRÍTICO

**El E2E del 03-sep-2026 FALLÓ.** Run `10a59ecf` descubrió 188 handles pero produjo **0 candidatos** porque el 100% fueron descartados en scoring con `MISSING_FOLLOWER_FIELD`.

Los 4 P0 de Fable 5 (`452d7e9`) YA ESTABAN APLICADOS en `4ffa62e`. El problema son **4 bugs adicionales** que no estaban en esa auditoría.

**HikerAPI balance:** ~$35.14 USD restantes
**Archivos de referencia:**
- `docs/LENS_BUG_REPORT_10a59ecf_03-09-26.md` — Bug report completo con todos los detalles
- `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` — Índice de auditorías (actualizado con entry #32)
- `docs/FIXES_P0_LENS_452d7e9_03-09-26.md` — P0 de Fable 5 aplicados + aviso de bugs nuevos
- `docs/MASTER_OPTIMIZATION_PROMPT.md` — Con bloqueadores actuales agregados

---

## TU MISIÓN

Analizá exhaustivamente el repositorio `github.com/ungardev/lawebcore` y corregí los bugs en el siguiente orden. Leé todos los archivos relevantes mencionados abajo ANTES de hacer cualquier cambio.

---

## ORDEN DE FIXES (prioridad CRÍTICA → BAJO)

### 🔴 FIX 1 — Campo incorrecto en merge de enrichment
**Bug:** `worker.py:1246` lee `e.get("followersCount")` pero HikerAPI devuelve `follower_count` (snake_case).
**Impacto:** 100% de perfiles enriquecidos terminan con `follower_count=None` → descartados como `MISSING_FOLLOWER_FIELD`.

**Archivo a modificar:** `apps/api/app/workers/worker.py:1246`

**Cambio:**
```python
# LÍNEA 1246 — CORREGIR de:
"follower_count": e.get("followersCount"),
# A:
"follower_count": e.get("follower_count"),
# Y lo mismo para following_count y posts_count:
"following_count": e.get("following_count"),
"posts_count": e.get("posts_count"),
```

**Verificación:** Después del fix, corré `scripts/test_lens_mascotas_ve.py` y verificá que los candidatos tengan `followers > 0`.

---

### 🔴 FIX 2 — Scoring sin fallback a rough_score para follower_count=0
**Bug:** `worker.py:1342-1349` descarta perfiles enriquecidos con `follower_count=0` (cuenta privada/eliminada) sin usar `rough_score` como fallback.
**Impacto:** Perfiles válidos con cuenta privada o sin datos de followers son descartados.

**Archivo a modificar:** `apps/api/app/workers/worker.py:1342-1349`

**Cambio:** Cuando `was_enriched=True` y `followers == 0`, usar `rough_score` como fallback (mismo patrón que modo explore en líneas 1360-1412).

---

### 🔴 FIX 3 — MAX_CALLS_PER_RUN demasiado bajo
**Bug:** `config.py:87` tiene `MAX_CALLS_PER_RUN = 120`, lo que causa que solo 25 de 188 handles sean enriquecidos.
**Impacto:** 163 handles sin enriquecer = `follower_count=0` = descartados.

**Archivos a modificar:**
- `packages/shared-core/shared_core/config.py:87`: `MAX_CALLS_PER_RUN: int = 200` (era 120)
- `apps/api/app/workers/worker.py:60`: `MAX_HANDLES_TO_ENRICH = 50` (era 25)

---

### 🟠 FIX 4 — Keywords en español para HikerAPI
**Bug:** Las queries de búsqueda están en español (`comida para perros vzla`) y HikerAPI responde mejor a inglés.
**Impacto:** Steps 1 y 2 encuentran 0 resultados útiles.

**Archivo a modificar:** `packages/discovery/discovery/query_builder.py` (inferred — función `_build_keyword_queries`)

**Cambio:** Agregar keywords en inglés como fallback:
```python
ENGLISH_PET_FOOD_KEYWORDS = [
    "dog food", "pet food", "dog chow", "dog kibble", "pet nutrition",
    "dog food venezuela", "pet food venezuela",
]

def _build_keyword_queries(profile, brief):
    queries = []
    queries.extend(profile.get("keywords", []))  # Español original
    queries.extend([f"{kw} venezuela" for kw in ENGLISH_PET_FOOD_KEYWORDS])  # English
    return list(set(queries))[:DISCOVERY_KEYWORD_LIMIT * 3]
```

---

### 🟠 FIX 5 — Aplicar migración 00107_budget_transactions en Railway
**Bug:** Tabla `budget_transactions` no existe en Railway Postgres — migración 00107 no aplicada.
**Impacto:** El ledger de presupuesto no se persiste, pero el código ya tiene try/except que lo maneja.

**Acción requerida:** **NO es un fix de código.** Debe ejecutarse manualmente en Railway SQL Editor:
```sql
-- Archivo: supabase/migrations/00107_budget_transactions.sql
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
CREATE INDEX idx_budget_tx_provider ON budget_transactions(provider, created_at DESC);
CREATE INDEX idx_budget_tx_run ON budget_transactions(run_id) WHERE run_id IS NOT NULL;
```

**Esto es un paso MANUAL que el usuario debe ejecutar en Railway.**

---

### 🟡 FIX 6 (investigación) — Steps 3 y 4 retornan 0 cuentas
**Bug:** `STEP3: 0 accounts from topsearch` y `STEP4: 0 accounts from suggested`
**Impacto:** Solo steps 1 y 2 aportan handles (120 + 80 = 200 de los cuales 12 son duplicados = 188 únicos).

**Acción:** Agregar logging detallado en `worker.py` para los pasos 3 y 4 para entender por qué no aportan handles. No tocar código hasta entender la causa raíz.

---

## ARCHIVOS PARA LEER ANTES DE EMPEZAR

1. `apps/api/app/workers/worker.py` — Líneas 1240-1260 (enrichment merge), 1330-1430 (scoring)
2. `packages/shared-core/shared_core/config.py` — Líneas 85-92 (budget config)
3. `packages/discovery/discovery/tools/hikerapi_client.py` — Líneas 486-510 (enrich_profile), 825-860 (_normalize_user)
4. `packages/discovery/discovery/query_builder.py` — Función `_build_keyword_queries`
5. `docs/LENS_BUG_REPORT_10a59ecf_03-09-26.md` — Bug report completo

---

## TESTS A ESCRIBIR/ACTUALIZAR

```python
# apps/api/tests/test_enrichment_field_names.py (CREAR)
async def test_enrichment_merge_uses_follower_count_not_followersCount():
    """El merge debe leer follower_count (snake_case) del resultado de HikerAPI."""
    # given: mock de response de HikerAPI enrich_profile
    mock_enriched = {
        "username": "test_user",
        "follower_count": 15000,  # snake_case - así viene de HikerAPI
        "following_count": 500,
        "posts_count": 120,
    }
    # when: se hace el merge en worker.py
    # then: profiles[handle]["follower_count"] == 15000

async def test_scoring_uses_rough_score_when_enriched_followers_zero():
    """BUG #2: Perfiles enriquecidos con follower_count=0 deben usar rough_score."""
    profiles = {
        "user_a": {"follower_count": 0, "_enriched": True, "biography": "dog food..."},
    }
    rough_score_map = {"user_a": 0.85}
    # when: se scorifica
    # then: "user_a" debe estar en scored, no en dropped
```

---

## VERIFICACIÓN POST-FIX

Después de aplicar los fixes 1-4, ejecutar:
```bash
API_BASE_URL=https://lawebcore-production.up.railway.app python scripts/test_lens_mascotas_ve.py
```

**Criterios de éxito:**
1. `total_candidates >= 15`
2. `followers > 0` para todos los candidatos
3. `ai_rationale NOT NULL`
4. Sin `MISSING_FOLLOWER_FIELD` masivo en `discovery_run_events`

**Query SQL de verificación:**
```sql
SELECT status, total_candidates, actual_cost_usd FROM discovery_runs
ORDER BY created_at DESC LIMIT 1;
-- Esperado: status='delivered', total_candidates >= 15, actual_cost_usd < 3.00
```

---

## CONSTRAINTS

- NO rompas el monorepo (apps/api, apps/web, packages/*)
- NO cambies el contrato de BriefStructured
- NO agregues campos nuevos a DiscoverySearchRequest
- NO modifiques la lógica de scoring fuera de los fixes descritos
- SIEMPRE ejecutá `npm run lint` y `npm run typecheck` (o el equivalente) después de cambios de código
- SIEMPRE escribí tests para cada fix

---

## COMANDO FINAL

Después de aplicar todos los fixes y tests, commiteá con:
```
git add -A && git commit -m "fix(lens): 4 critical bugs from run 10a59ecf

- FIX BUG #1: e.get('followersCount') → e.get('follower_count') in merge
- FIX BUG #2: rough_score fallback for enriched profiles with follower_count=0
- FIX BUG #3: MAX_CALLS_PER_RUN=200, MAX_HANDLES_TO_ENRICH=50
- FIX BUG #4: add English keywords for HikerAPI queries

Refs: docs/LENS_BUG_REPORT_10a59ecf_03-09-26.md"
git push
```

---

*Prompt generado: 03-sep-2026 · La Web Figital Agency*
*Para: Claude Code · Análisis y fix exhaustivo del repositorio lawebcore*
