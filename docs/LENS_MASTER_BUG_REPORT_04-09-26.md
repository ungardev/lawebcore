# LENS — MASTER BUG REPORT
## Pipeline HikerAPI · Todos los Bugs Identificados
## Fecha: 04-sep-2026 · La Web Figital Agency

> **Repositorio:** `github.com/ungardev/lawebcore`
> **Commit HEAD:** `a67ad72` (03-sep-2026) — FIX 1 aplicado
> **Documentación HikerAPI:** https://api.hikerapi.com/docs | https://api.hikerapi.com/openapi.json
> **Estado del pipeline:** Run `10a59ecf` — 188 handles → 25 enriquecidos → **0 candidatos**
> **Regla de oro:** "Mostrar candidatos en logs > rechazar candidatos"

---

## RESUMEN EJECUTIVO

El pipeline de LENS Discovery ejecutó sin crashear pero entregó **0 candidatos de 188 handles** por una cadena de bugs. El más crítico (BUG B1) no había sido identificado hasta ahora.

| Bug | Gravedad | Archivo | Impacto |
|-----|----------|---------|---------|
| **BUG B1** | 🔴 CRÍTICO | `hikerapi_client.py:659` | `former_usernames` es STRING, no LIST → 100% marcados como fraude |
| **FIX 1** | ✅ Aplicado | `worker.py:1246` | merge leía `followersCount` en vez de `follower_count` |
| BUG B2 | 🟡 MEDIO | `hikerapi_client.py:532-549` | `search_top_accounts` descarta tipos desconocidos |
| BUG B3 | 🟡 MEDIO | `hikerapi_client.py:341-343` | `search_hashtag` corta nano-niches a 50 followers |
| BUG B4 | 🟡 MEDIO | `hikerapi_client.py:590` | `search_accounts_v3` existe pero no se usa |
| BUG B5 | 🟡 MEDIO | `worker.py` | Logging escaso — solo muestra rechazos, no handles encontrados |
| BUG B6-B14 | 🟡 MEDIO | `worker.py`, `hikerapi_client.py` | Endpoints dormidos, endpoints faltantes (ver Sección 3) |

---

## SECCIÓN 1 — BUGS CRÍTICOS

### 🔴 BUG B1 — `former_usernames` tipo incorrecto (CRÍTICO — NO APLICADO)

**Archivo:** `packages/discovery/discovery/tools/hikerapi_client.py:659`

**El bug más devastador del pipeline.** Este bug causa que el 100% de los perfiles enriquecidos sean marcados como fraudulentos, bajando su score artificialmente.

**Especificación OpenAPI de HikerAPI:**
```yaml
former_usernames:
  type: string
  description: Comma-separated list of former usernames
  example: "old_user1,old_user2"
```

**Código actual (INCORRECTO):**
```python
# hikerapi_client.py:659
former_usernames = user_data.get("former_usernames", [])
count = len(former_usernames)  # ← BUG: cuenta chars, no usernames
```

**Cascada del fallo:**
```
HikerAPI devuelve: former_usernames = "old_user,another_old"
                                              ↓
len("old_user,another_old") = 18 chars  (≥ 3 SIEMPRE)
                                              ↓
worker.py:1516  if count >= 3:  → True
                                              ↓
worker.py:1519  fraud_penalty = 0.80
                                              ↓
Scoring: score × 0.8 → match_score colapsa
                                              ↓
TODOS los perfiles enriquecidos → descartados como sospechosos
```

**Fix exacto:**
```python
# hikerapi_client.py:659-661 — CORREGIR
former_usernames_raw = user_data.get("former_usernames") or ""
count = len([u for u in former_usernames_raw.split(",") if u.strip()]) if former_usernames_raw else 0
```

**Impacto:** Con FIX 1 ya aplicado, el BUG B1 es lo que mantiene los candidatos en 0. Sin BUG B1, los perfiles enriquecidos serían scorados correctamente.

---

### 🔴 FIX 1 — YA APLICADO en commit `a67ad72`

**Archivo:** `apps/api/app/workers/worker.py:1244-1257`

El merge de enrichment leía `e.get("followersCount")` (camelCase) pero `_normalize_user()` devuelve `follower_count` (snake_case). El 100% de los perfiles enriquecidos terminaban con `follower_count=None`.

**Fix aplicado (commit `a67ad72`):**
```python
profiles[handle].update({
    "_enriched": True,
    "follower_count": e.get("follower_count"),      # era: e.get("followersCount")
    "following_count": e.get("following_count"),    # era: e.get("followsCount")
    "posts_count": e.get("posts_count"),           # era: e.get("postsCount")
    "is_business": e.get("is_business", False),    # era: e.get("isBusinessAccount")
    "is_verified": e.get("is_verified", False),    # era: e.get("verified")
    "full_name": e.get("full_name"),               # era: e.get("fullName")
    "avatar_url": e.get("avatar_url"),             # era: e.get("profilePicUrlHD")
    "location": e.get("location_name"),            # era: e.get("locationName")
})
```

**Test de regresión creado:** `apps/api/tests/test_enrichment_field_names.py`

---

## SECCIÓN 2 — ENDPOINTS HIKERAPI

**Referencia:** https://api.hikerapi.com/docs | https://api.hikerapi.com/openapi.json

### 8 endpoints ACTIVOS en el cliente actual (de 154 disponibles):

| # | Método cliente | Endpoint HTTP | Uso actual | Capacidad real |
|---|----------------|--------------|-----------|----------------|
| 1 | `get_balance()` | `GET /account/balance` | ✅ preflight | — |
| 2 | `search_hashtag()` | `GET /v2/hashtag/by/name` | ✅ 6 tags/run | 12 tags |
| 3 | `get_hashtag_medias_top()` | `GET /v2/hashtag/medias/top` | ✅ 1 page | 3 pages |
| 4 | `get_hashtag_medias_recent()` | `GET /v2/hashtag/medias/recent` | ✅ 4 tags | 8 tags |
| 5 | `search_accounts_v2()` | `GET /v3/fbsearch/accounts` | ✅ sin paginar | 3 pages |
| 6 | `get_user_info()` | `GET /v2/user/by/username` | ⚠️ cap 25/users | cap 100 |
| 7 | `search_topsearch()` | `GET /gql/topsearch` | ✅ 3 kw × 1p | 6 kw × 3p |
| 8 | `search_reels()` | `GET /v2/fbsearch/reels` | 🔴 1 kw × 3 clips | **6 kw × 10 clips** |

### 6 endpoints DORMIDOS (código existe pero NO se llama):

| # | Método cliente | Endpoint | Línea | Razón |
|---|----------------|----------|-------|-------|
| 9 | `search_followers_of()` | `GET /v1/user/search/followers` | 605 | **NEVER CALLED** — dead code |
| 10 | `web_profile_info()` | `GET /gql/user/web_profile_info` | 625 | **NEVER CALLED** — dead code |
| 11 | `get_user_about()` | `GET /v1/user/about` | 637 | ENV OFF: `HIKERAPI_INCLUDE_ABOUT=false` |
| 12 | `search_location()` | `GET /v1/fbsearch/places` | 667 | ENV OFF: `HIKERAPI_STEP0_LOCATION=false` |
| 13 | `location_medias_top()` | `GET /v1/location/medias/top` | 685 | gated por #12 |
| 14 | `location_medias_recent()` | `GET /v1/location/medias/recent/chunk` | 705 | gated por #12 |

### 6 endpoints QUE FALTAN (no existen en el cliente):

| # | Endpoint HTTP | Para qué sirve | Prioridad |
|---|--------------|----------------|-----------|
| 15 | `GET /g2/user/followers` | **KILLER** — followers de seed accounts | ALTA |
| 16 | `GET /v2/user/explore/businesses/by/id` | Recomendados por categoría | MEDIA |
| 17 | `GET /v1/media/likers` | Quienes likearon el post top | MEDIA |
| 18 | `GET /v2/user/clips` | Reels engagement real | ALTA |
| 19 | `GET /v3/fbsearch/places` | Búsqueda de lugares v3 | BAJA |
| 20 | `GET /v1/fbsearch/topsearch/hashtags` | Bootstrap hashtags por nicho | BAJA |

### Endpoints PELIGROSOS (costo 2-3× por call):
- `/v1/user/stories`, `/v2/user/stories`, `/followers/chunk`, `/following/chunk`, `/highlights`
- **NO usar** hasta que el pipeline entregue candidatos

---

## SECCIÓN 3 — BUGS ADICIONALES

### 🟡 BUG B2 — `search_top_accounts` descarta tipos desconocidos

**Archivo:** `hikerapi_client.py:532-549`

Solo maneja `XDTUserDict` y `XDTMediaDict`. Silenciosamente descarta: `XDTExploreLikeRequest`, `XDTAdItem`, `XDTReelsTrayOverlayData`, `XDTReelsTrayItem`.

### 🟡 BUG B3 — `search_hashtag` corta nano-niches muy agresivo

**Archivo:** `hikerapi_client.py:341-343`
```python
if media_count < 50: return []  # Corta cualquier tag con <50 posts
```
Para nano-niches venezolanos esto es demasiado agresivo.

### 🟡 BUG B4 — `search_accounts_v3` existe pero no se usa

**Archivo:** `hikerapi_client.py:590`

Recomendado por la docstring pero `worker.py:591` sigue usando `search_keyword` sin paginar.

### 🟡 BUG B5 — Logging insuficiente (REGLAS DE ORO ROTA)

**Archivo:** `worker.py` (todo)

El sistema ACTUALMENTE solo muestra:
- `profile.dropped | MISSING_FOLLOWER_FIELD | count=188` ← esto sí se ve

El sistema NO muestra:
- Handles descubiertos por step (STEP1=120, STEP2=68, etc.)
- Cada decisión de enriquecimiento (por qué se eligió ese handle)
- Progreso del scoring (cuántos van siendo descartados por qué razón)
- El logging actual IMPIDE diagnosticar sin queries SQL

**Fix de logging requerido — cada handle debe decir:**
```
[DISCOVERY] hikerapi.traced: handle=@petfood_ve source=hashtag #comidaperrovzla rough_score=0.82
[ENRICHMENT] hikerapi.enriched: handle=@petfood_ve follower_count=12500 is_business=true location_name=Caracas
[SCORING] hikerapi.scored: handle=@petfood_ve match_score=78.5 tier=B reason=qualified
[DROP] hikerapi.dropped: handle=@petfood_ve reason=GEO_MISMATCH country=CO expected=VE
```

### 🟡 BUG B6 — `STEP3 topsearch` y `STEP4 suggested` retornan 0 cuentas

**Archivo:** `worker.py:837-875`

Solo STEP1 (hashtags: 120 handles) y STEP2 (keywords: 68 handles) aportan.

---

## SECCIÓN 4 — PLAN DE FIXES POR TIER

### TIER 1 — Activar código dormido (~15 LOC, riesgo BAJO)
**Costo:** $3.30/run | **Esperado:** 15-25 candidatos

| # | Acción | Archivo | LOC | Costo extra |
|---|--------|---------|-----|-------------|
| T1.1 | **Fix BUG B1** — `former_usernames` split | `hikerapi_client.py:659` | 3 | $0 |
| T1.2 | Wire `search_followers_of()` a STEP 4 | `worker.py:634` | 5 | +$0.06 |
| T1.3 | Wire `web_profile_info()` como fallback | `worker.py:1142` | 5 | +$0.05 |
| T1.4 | Set `HIKERAPI_INCLUDE_ABOUT=true` | env | 0 | +$0.50 |
| T1.5 | Set `HIKERAPI_STEP0_LOCATION=true` | env | 0 | +$0.84 |
| T1.6 | **Logging exhaustivo** — cada handle + decisión | `worker.py` | 5 | $0 |

### TIER 2 — Expandir límites (~5 LOC, riesgo BAJO)
**Costo:** $5.80/run | **Esperado:** 60-100 candidatos

| # | Acción | Archivo | LOC |
|---|--------|---------|-----|
| T2.1 | `MAX_HANDLES_TO_ENRICH 25→50` | `worker.py:60` | 1 |
| T2.2 | `MAX_CALLS_PER_RUN 120→200` | `config.py:87` | 1 |
| T2.3 | Reels: `1 kw × 3 clips → 6 kw × 10 clips` | `worker.py:648` | 2 |
| T2.4 | Hashtag top: `6 → 12 tags` | `config.py:96` | 1 |

### TIER 3 — Agregar 6 endpoints nuevos (~80 LOC, riesgo MEDIO)
**Costo:** $5.80/run | **Esperado:** 50-80 candidatos

- `get_user_followers(seed)` — STEP 2c network expansion
- `get_post_likers(post_id)` — STEP 2b engagement expansion
- `get_user_clips(user_id)` — STEP 5b ER real
- `get_business_suggestions(seed)` — STEP 2d category-based
- `search_location_v3(query)` — STEP 0 location refresh
- `get_topsearch_hashtags(query)` — STEP 1 hashtag bootstrap

### TIER 4 — Keywords en inglés
**⚠️ RECHAZADO por Fable 5.1** — contradice filtro geográfico. Evaluar solo si volumen en español es insuficiente.

---

## SECCIÓN 5 — INSTRUCCIONES PARA CLAUDE CODE FABLE 5.1

```
1. Leer primero: https://api.hikerapi.com/docs y https://api.hikerapi.com/openapi.json
2. Documentación completa de endpoints en este archivo — Sección 2
3. BUG B1 es crítico y debe arreglarse primero
4. NO aplicar TIER 2 hasta validar TIER 1 con E2E real
5. Regla de oro: "Mostrar candidatos > rechazar candidatos"
6. Logging: cada handle debe tener trace completo
7. Presentar todos los fixes a Ignacio ANTES de aplicar
```

**Flujo de confirmación:**
1. Ignacio revisa este documento
2. Ignacio aprueba TIER 1
3. Se aplica TIER 1, se corre E2E
4. Si <30 candidatos → TIER 2
5. Si ≥30 candidatos → esperar validación

---

## SECCIÓN 6 — ORDEN DE APLICACIÓN RECOMENDADO

| Orden | Bug/Tier | Costo | Esperado |
|-------|----------|-------|----------|
| 1 | **BUG B1** — former_usernames string split | $0 | Habilita scoring real |
| 2 | **Logging exhaustivo** — cada handle en log | $0 | Diagnóstico real |
| — | **E2E de validación** | ~$1.72 | Saber si funciona |
| 3 | TIER 1 restantes (wire dormant endpoints) | +$1.45 | 15-25 candidatos |
| 4 | TIER 2 (límites) | +$2.50 | 60-100 candidatos |
| 5 | TIER 3 (6 endpoints nuevos) | ~$0 | 50-80 candidatos |

---

## SECCIÓN 7 — NOTA DE PROCESO (Fable 5.1 ruling)

Fable 5.1 estableció que **subir `MAX_HANDLES_TO_ENRICH` de 25 a 50 antes de que el pipeline entregue candidatos con 25 es duplicar el costo del mismo fallo.**

Esto aplica a los límites, NO al código dormido (TIER 1) que puede activarse sin aumentar el costo efectivo.

---

*Documento generado: 04-sep-2026 · La Web Figital Agency*
*Para entrega a: Claude Code Fable 5.1*
*Basado en: run `10a59ecf`, commit `a67ad72`, análisis exhaustivo HikerAPI OpenAPI spec*
