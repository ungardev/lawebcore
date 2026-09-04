# LENS — AUDITORÍA EXHAUSTIVA DEL PIPELINE HIKERAPI
## HikerAPI OpenAPI Spec vs Código Cliente · 04-sep-2026

> **Documentación oficial:** https://api.hikerapi.com/docs | https://api.hikerapi.com/openapi.json
> **Repositorio:** `github.com/ungardev/lawebcore`
> **Cliente actual:** `packages/discovery/discovery/tools/hikerapi_client.py` (863 líneas)
> **Auditor:** MiniMax M2.7/M3

---

## RESUMEN EJECUTIVO

| Métrica | Valor |
|---------|-------|
| Endpoints en OpenAPI spec | **154** |
| Endpoints envueltos en cliente | **17** |
| Endpoints usados activamente | **8** |
| Endpoints dormidos (dead code) | **3** |
| Endpoints faltantes (no existen) | **6+** |
| Endpoints con bugs de tipo | **1 (BUG B1 — crítico)** |

---

## MAPA COMPLETO DE ENDPOINTS

### ENDPOINTS ACTIVOS (8/154)

#### 1. `GET /account/balance` ✅
- **Cliente:** `get_balance()` → `hikerapi_client.py:443`
- **Uso:** preflight antes de cada run
- **Bug:** El código prueba 3 URLs deprecated antes de la correcta
- **Fix:** Ya identificado — verificar que esté funcionando

#### 2. `GET /v2/hashtag/by/name` ✅
- **Cliente:** `search_hashtag()` → `hikerapi_client.py:330`
- **Uso:** STEP 1 — bootstrap por hashtags
- **Capacidad real:** 12 tags/run | **Usando:** 6 tags/run
- **Bug conocido:** Corta nano-niches con `media_count < 50` (BUG B3)

#### 3. `GET /v2/hashtag/medias/top` ✅
- **Cliente:** `get_hashtag_medias_top()` → `hikerapi_client.py:367`
- **Uso:** Extraer top posts de cada hashtag
- **Capacidad real:** 3 pages | **Usando:** 1 page
- **Bug conocido:** Sin paginación

#### 4. `GET /v2/hashtag/medias/recent` ✅
- **Cliente:** `get_hashtag_medias_recent()` → `hikerapi_client.py:395`
- **Uso:** Posts recientes por hashtag
- **Capacidad real:** 8 tags | **Usando:** 4 tags

#### 5. `GET /v3/fbsearch/accounts` ✅
- **Cliente:** `search_accounts_v2()` → `hikerapi_client.py:555`
- **Uso:** STEP 2 — búsqueda por keywords
- **Capacidad real:** 3 pages | **Usando:** sin paginar
- **Bug conocido:** Sin paginación (BUG B4)

#### 6. `GET /v2/user/by/username` ✅
- **Cliente:** `get_user_info()` → `hikerapi_client.py:486`
- **Uso:** Enrichment de cada handle
- **Capacidad real:** 100 users/run | **Usando:** 25 users/run
- **Bug conocido:** Cap bajo

#### 7. `GET /gql/topsearch` ✅
- **Cliente:** `search_topsearch()` → `hikerapi_client.py:570`
- **Uso:** STEP 3 — búsqueda global
- **Capacidad real:** 6 keywords × 3 pages | **Usando:** 3 kw × 1 page
- **Bug conocido:** Sin paginación

#### 8. `GET /v2/fbsearch/reels` 🔴
- **Cliente:** `search_reels()` → `hikerapi_client.py:606`
- **Uso:** STEP 2.5 — Reels discovery
- **Capacidad real:** 6 keywords × 10 clips + paginación | **Usando:** 1 kw × 3 clips
- **Bug conocido:** Severamente subutilizado (BUG principal de volumen)

---

### ENDPOINTS DORMIDOS (6/154)

#### 9. `GET /v1/user/search/followers` ❌ NEVER CALLED
- **Cliente:** `search_followers_of()` → `hikerapi_client.py:605`
- **Estado:** Definido pero **nunca invocado** en todo el codebase
- **Potencial:** STEP 4 — network expansion desde seed accounts
- **Costo estimado:** ~$0.06/llamada
- **Acción:** Wire a `worker.py:634` en TIER 1

#### 10. `GET /gql/user/web_profile_info` ❌ NEVER CALLED
- **Cliente:** `web_profile_info()` → `hikerapi_client.py:625`
- **Estado:** Definido pero **nunca invocado**
- **Potencial:** Fallback en enrichment si `get_user_info()` falla
- **Costo:** ~$0.05/llamada
- **Acción:** Wire a `worker.py:1142` en TIER 1

#### 11. `GET /v1/user/about` ⚠️ ENV OFF
- **Cliente:** `get_user_about()` → `hikerapi_client.py:637`
- **Estado:** Cableado pero desactivado por `HIKERAPI_INCLUDE_ABOUT=false`
- **Potencial:** Bio extendida, información adicional de perfil
- **Costo:** ~$0.50/run si se activa
- **Acción:** Set `HIKERAPI_INCLUDE_ABOUT=true` en TIER 1

#### 12. `GET /v1/fbsearch/places` ⚠️ ENV OFF
- **Cliente:** `search_location()` → `hikerapi_client.py:667`
- **Estado:** Cableado pero desactivado por `HIKERAPI_STEP0_LOCATION=false`
- **Potencial:** Bootstrap geolocalizado antes de hashtags
- **Costo:** ~$0.84/run si se activa
- **Acción:** Set `HIKERAPI_STEP0_LOCATION=true` en TIER 1

#### 13. `GET /v1/location/medias/top` ⚠️ GATED
- **Cliente:** `location_medias_top()` → `hikerapi_client.py:685`
- **Estado:** Depende de #12
- **Potencial:** Top posts por location

#### 14. `GET /v1/location/medias/recent/chunk` ⚠️ GATED
- **Cliente:** `location_medias_recent()` → `hikerapi_client.py:705`
- **Estado:** Depende de #12
- **Potencial:** Posts recientes por location

---

### ENDPOINTS QUE FALTAN EN EL CLIENTE (6/154)

#### 15. `GET /g2/user/followers` ⭐ KILLER
- **Qué hace:** Obtiene followers paginados de un usuario específico
- **Por qué es KILLER:** Permite network expansion desde seed accounts
- **Dónde wirear:** STEP 4 (suggested/profiles expansion)
- **Costo:** ~$0.06-0.12 por seed

#### 16. `GET /v2/user/explore/businesses/by/id` ⭐
- **Qué hace:** Recomendaciones de cuentas business por categoría
- **Dónde wirear:** STEP 2d
- **Costo:** ~$0.05 por query

#### 17. `GET /v1/media/likers` ⭐
- **Qué hace:** Lista de usuarios que likearon un post específico
- **Dónde wirear:** STEP 2b (engagement expansion)
- **Costo:** ~$0.05 por post

#### 18. `GET /v2/user/clips` ⭐⭐
- **Qué hace:** Clips/reels de un usuario con engagement real
- **Por qué es importante:** ER real de Reels vs estimated ER
- **Dónde wirear:** STEP 5b (post-enrichment)
- **Costo:** ~$0.05 por usuario

#### 19. `GET /v3/fbsearch/places`
- **Qué hace:** Búsqueda de lugares v3 (más reciente que v1)
- **Dónde wirear:** Reemplaza `search_location()` (#12)

#### 20. `GET /v1/fbsearch/topsearch/hashtags`
- **Qué hace:** Hashtags trending para una query
- **Dónde wirear:** STEP 1 bootstrap

---

## BUGS ESPECÍFICOS DEL CLIENTE HIKERAPI

### BUG B1 — `former_usernames` STRING vs LIST (CRÍTICO)

**Archivo:** `hikerapi_client.py:659`

```python
# INCORRECTO — OpenAPI dice type: string
former_usernames = user_data.get("former_usernames", [])
count = len(former_usernames)  # cuenta chars, no usernames!

# CORRECTO
former_usernames_raw = user_data.get("former_usernames") or ""
count = len([u for u in former_usernames_raw.split(",") if u.strip()])
```

**Impacto:** Todos los perfiles con `former_usernames` de 3+ caracteres son marcados como fraudulentos (fraud_penalty=0.8).

---

### BUG B2 — `search_top_accounts` silencia tipos desconocidos

**Archivo:** `hikerapi_client.py:532-549`

```python
for item in items:
    if isinstance(item, XDTUserDict):
        users.append(item)
    elif isinstance(item, XDTMediaDict):
        medias.append(item)
    # SILENCIOSO: XDTExploreLikeRequest, XDTAdItem, XDTReelsTrayItem descartados
```

---

### BUG B3 — `search_hashtag` muy agresivo para nano-niches

**Archivo:** `hikerapi_client.py:341-343`

```python
if media_count < 50:
    return []  # Corta cualquier hashtag con <50 posts
```

Para nano-niches venezolanos esto descarta tags válidos.

---

## COSTOS ESTIMADOS POR TIER

| Tier | Calls/run | Costo/run | Candidatos esperados |
|------|-----------|-----------|---------------------|
| Actual (sin fixes) | ~86 | $1.72 | 0 |
| TIER 1 (BUG B1 + dormant) | ~110 | $3.30 | 15-25 |
| TIER 2 (+ límites) | ~180 | $5.80 | 60-100 |
| TIER 3 (+ 6 endpoints) | ~180 | $5.80 | 50-80 |

---

## LOGGING REQUERIDO

Cada handle debe producir estos logs:

```
[hikerapi.discovery] handle=@petfood_ve source=hashtag|#comidaperrovzla rough_score=0.82 followers_est=5000
[hikerapi.enrichment] handle=@petfood_ve enriched=true follower_count=12500 is_business=true location_name=Caracas
[hikerapi.scoring] handle=@petfood_ve match_score=78.5 tier=B rationale="Alta afinidad+nicho+geo"
[hikerapi.drop] handle=@somehandle reason=GEO_MISMATCH expected=VE found=CO rough_score=0.45
[hikerapi.funnel] step=STEP2 total=68 deduplicated=12 prefiltered=56 rough_scored=56
```

**NUNCA hacer:** Solo logs de drops. El logging debe mostrar qué se encuentra, no solo qué se pierde.

---

*Auditoría generada: 04-sep-2026 · La Web Figital Agency*
*Para: Claude Code Fable 5.1 · Revisión de pipeline HikerAPI completo*
