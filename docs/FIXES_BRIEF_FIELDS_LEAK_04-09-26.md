# LENS · FIXES — Fuga de campos del brief + verdad en el wizard
## 04-09-2026 · La Web Figital Agency

> **HEAD base:** `dfed86e` · Origen: pregunta de Ungar — "¿el nicho HikerAPI lo maneja? ¿nos sirve o nos empeora la búsqueda?"

---

## DICTAMEN QUE ORIGINÓ ESTE BATCH

**¿Los nichos viajan directos a HikerAPI?** NO en el camino normal. Los nichos alimentan el *fingerprint* del brief → DeepSeek genera 15-25 keywords DESDE esos nichos → esas keywords (no los nichos literales) son las que se ejecutan contra `/v3/fbsearch/accounts` (solo los primeros 6 × 3 variantes geo). El contador "≈ 21 búsquedas de cuentas" del wizard era **falso** — los nichos literales quedan fuera del corte cuando la IA genera keywords.

**¿Nichos primero en las queries?** DECISIÓN: NO por ahora. Los nichos ya moldean indirectamente las keywords vía DeepSeek; reordenar antes del primer E2E es optimizar sin datos (disciplina Fable 5.1). Post-E2E, con la distribución `_discovery_query`, se decide si hay interleave.

## FIX 1 — Fuga de campos del brief (backend, calidad real)

`DiscoverySearchRequest` (extra='forbid', schemas.py) NO tenía estos campos y la construcción del run solo copia los que existen → **se perdían al 100% al crear el run**:

| Campo perdido | Impacto antes del fix |
|---|---|
| `additional_context` ("Solo creadoras, NO tiendas...") | Nunca llegaba al worker |
| `influencer_preferences` (tiers/min_er de PDFs) | Siempre default micro→5000 |
| `competitor_brands` | Nunca alimentaban queries ni intel de DeepSeek |
| budget/kpis/objective/dates/themes/name/source | Solo display; ahora persisten en `brief_parsed` |

**Fix:** campos agregados al schema (todos opcionales → backward compatible con `extra='forbid'`) + pasados en `discovery.py` al construir el run + test de roundtrip BriefStructured→DiscoverySearchRequest→BriefStructured.

## FIX 2 — El wizard dice la verdad (frontend)

| Antes (incoherente) | Ahora (verdad) |
|---|---|
| "Cada nicho se convierte en búsquedas de cuentas reales («nicho venezuela»...)" | "Tus nichos guían al generador IA: los convierte en cuentas y hashtags venezolanos reales, y puntúan la afinidad de cada candidato" |
| Chip falso «≈ 21 búsquedas de cuentas» | Eliminado |
| Plan paso 6: "N nichos → N×3 búsquedas" | "N nichos → contexto del generador IA" + "6 keywords generadas por IA → 18 búsquedas de cuentas (×3 variantes geo)" |

## ARCHIVOS

- `packages/discovery/discovery/schemas.py` — DiscoverySearchRequest +12 campos opcionales
- `apps/api/app/api/v1/discovery.py` — construcción del run pasa los campos
- `apps/api/tests/test_brief_field_persistence.py` — **nuevo**: 3 tests (acepta campos, roundtrip preserva los que se perdían, backward compat)
- `apps/web/src/features/lens/components/BriefWizard.tsx` — copy honesto paso 2, chip eliminado, plan paso 6 real

## VERIFICACIÓN

- **210 passed** (+3), 7 failed = baseline pre-cambios intacto, 3 skipped
- tsc --noEmit ✅ · eslint ✅ · ruff ✅

## PENDIENTE POST-E2E (con datos)

1. ¿Interleave nichos/keywords en las 6 queries ejecutadas? — decidir con distribución `_discovery_query` del primer E2E
2. Tuning de calidad: min_followers=5000 (nanos), filtro tienda agresivo, prefilter a ciegas

---

*GLM 5.3 Flash (opencode) · 04-sep-2026*
