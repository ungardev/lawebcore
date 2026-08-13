# Análisis para Senior Full-Stack Developer — LENS Discovery Bottleneck

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Problema:** Cuello de botella crítico en costos, performance y arquitectura del pipeline de descubrimiento de influencers
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI + DeepSeek

---

## 🎯 OBJETIVO DEL ANÁLISIS

Necesito que analices la arquitectura completa de nuestro sistema de descubrimiento de influencers (LENS) y nos des un **plan de acción como senior full-stack developer** para resolver:

1. **Costos insostenibles**: $50-72 USD consumidos en 2 días con HikerAPI
2. **Pipeline no retorna candidatos útiles**: 0 candidatos en últimas ejecuciones
3. **Bugs encontrados en endpoints de HikerAPI** durante integración
4. **Falta de observabilidad** del consumo real por step
5. **Arquitectura de fallback incompleta**: Apify configurado pero deshabilitado

**Necesito que seas brutalmente honesto** sobre:
- Qué está mal arquitectado
- Qué buenas prácticas estamos violando
- Qué soluciones propondrías (corto, mediano, largo plazo)
- Cómo evitar que esto vuelva a pasar

---

## 📂 ESTRUCTURA DEL PROYECTO

### Monorepo

```
lawebcore/
├── apps/
│   ├── api/                          # FastAPI backend (Railway)
│   │   └── app/
│   │       ├── api/v1/              # 40+ endpoints
│   │       ├── core/                # security, metrics, rate_limiter
│   │       ├── models/              # SQLAlchemy ORM
│   │       ├── services/            # AI services
│   │       └── workers/             # ARQ worker entry point
│   └── web/                         # React 19 frontend (Vercel)
├── packages/
│   ├── discovery/                   # ★ LENS Discovery Module
│   │   └── discovery/
│   │       ├── orchestrator.py
│   │       ├── brief_parser.py
│   │       ├── profile_generator.py
│   │       ├── candidate_analyzer.py
│   │       ├── query_builder.py
│   │       ├── memory.py
│   │       ├── result_ranker.py
│   │       ├── scoring/
│   │       │   ├── lens_score.py
│   │       │   └── niche.py
│   │       └── tools/
│   │           ├── hikerapi_client.py
│   │           ├── apify_client.py
│   │           ├── apify_instagram_source.py
│   │           ├── instagram_source.py
│   │           ├── source_registry.py
│   │           ├── geo_boost.py
│   │           └── metricool_client.py
│   ├── shared-core/
│   └── shared-ai/
├── supabase/
│   ├── migrations/
│   ├── schema.sql
│   └── seed*.sql
└── docs/
    └── ARQUITECTURA_LENS.md         # Documentación completa
```

---

## 🚨 PROBLEMAS CONOCIDOS

### 1. Costos HikerAPI (CRÍTICO)

**Síntoma:**
- $50-72 USD consumidos en 2 días
- Balance actual: -717 requests, $0.0 USD
- Cuenta agotada (`InsufficientFunds 402`)

**Causa raíz:**
```python
MAX_HANDLES_TO_ENRICH = 500  # ⚠️ ESTO ES EL PROBLEMA
```

Cada perfil enriquecido invoca:
- 1× `enrich_profile()` → `/v1/user/by/username`
- 1× `get_user_about()` → `/v1/user/about`

= **2 calls × 500 perfiles = 1000 calls por run**

**Math del costo:**
```
Precio HikerAPI: $0.0006 USD/call
Costo por run (cold cache): 1000 × $0.0006 = $0.60 USD
Si ejecutamos 80 tests en 2 días: 80 × $0.60 = $48 USD ✓ matches reality
```

### 2. Pipeline retorna 0 candidatos

**Síntoma:** Última ejecución: 0 candidatos en 10 segundos, sin error visible.

**Causas posibles:**
- `get_user_about()` retornaba 422 (todos los perfiles sin `country` → descartados)
- STEP 0 location search no encuentra perfiles (endpoint incorrecto)
- Hashtags B2B (`dogchowve`) → no retornan creators
- Scoring demasiado estricto: `min_match_score = 10` eliminaba 254 profiles → 0

### 3. Bugs en endpoints de HikerAPI

| Bug | Endpoint incorrecto | Endpoint correcto |
|-----|---------------------|-------------------|
| `search_location()` | `/v1/location/search` (requiere lat/lng) | `/v1/fbsearch/places` (búsqueda por texto) |
| `get_user_about()` | `/gql/user/about?user_id&safe_int` | `/v1/user/about?id` (sin safe_int) |
| `location_medias_top()` | `?id=...` | `?location_pk=...` |
| `location_medias_recent()` | `?id=...` | `?location_pk=...` |

**Documentación:** https://api.hikerapi.com/docs

### 4. Apify configurado pero deshabilitado

```python
INSTAGRAM_SOURCE = "hikerapi"  # default
```

Apify API key disponible pero:
- Actors retornan 404
- Engagement analytics actor desactivado
- No hay lógica de fallback funcional

### 5. Falta de observabilidad

No sabemos:
- Cuántas calls hace cada step exactamente
- Cuánto cuesta cada step
- Cache hit rate real
- Qué endpoints son más costosos

---

## 📊 ESTADO ACTUAL DEL CÓDIGO

### Pipeline LENS (Steps 0-5)

```
STEP 0: Location Search
  - search_location() por ciudad → encuentra location_pk
  - location_medias_top() + recent() → perfiles geolocalizados
  - API calls: 6 cities × (1 + 3 × 2) = 42 calls
  - Status: ⚠️ Disabled by default

STEP 1: Hashtag Search
  - search_hashtag() top posts + search_hashtag_recent()
  - API calls: 3 + 2 = ~12 calls
  - Status: ✅ Optimizado

STEP 2: Keyword Search
  - search_keyword() con geo suffixes
  - API calls: 3 keywords × 3 variants = 9 calls
  - Status: ✅ Optimizado

STEP 2.5: Reels Search
  - search_reels_by_keyword()
  - API calls: 1 keyword = 1 call

STEP 2.6: Network Expansion
  - suggested_profiles() + search_followers_of()
  - API calls: 1 seed × 1 niche = 2 calls
  - Status: ⚠️ Follower expansion disabled

STEP 3: Profile Enrichment  ★ MAYOR COSTO
  - enrich_profile() por handle
  - get_user_about() (opcional)
  - API calls: 50 × 1 (sin about) = 50 calls
  - Status: ✅ Optimizado (MAX_HANDLES_TO_ENRICH: 500→50)

STEP 4: Scoring
  - geo_score, niche_relevance, lens_score
  - Bot filters (ER > 30% = bot)
  - Cost: $0 (solo DB queries)

STEP 5: AI Analysis (DeepSeek)
  - Optional, controlled by `analyze_with_ai`
  - Cost: ~$0.001/1K tokens
```

### Constantes actuales (worker.py)

```python
MAX_HANDLES_TO_ENRICH = 50
MAX_POSTS_PER_HASHTAG = 20
VE_GEO_SUFFIXES = ["venezuela", "vzla"]
MAX_REELS_PER_QUERY = 3
MAX_FOLLOWER_EXPANSION_PER_SEED = 5
ENRICHMENT_INCLUDE_ABOUT = False  # By default

# Step limits
HASHTAGS_TOP = 3
HASHTAGS_RECENT = 2
KEYWORDS = 3
TOP_SEARCH = 1
SUGGESTED_SEEDS = 1
REELS_KEYWORDS = 1
FOLLOWER_EXPANSION_SEEDS = 1
FOLLOWER_EXPANSION_NICHE_KWS = 0  # Disabled
```

---

## ❓ PREGUNTAS PARA TI (CLAUDE CODE)

### A. Análisis Arquitectónico

1. ¿La separación Discovery ↔ API ↔ Web está bien diseñada o hay acoplamiento problemático?
2. ¿El pipeline de steps 0-5 es el flujo correcto o hay una mejor arquitectura?
3. ¿`BriefStructured → DiscoveryPlan → Candidates` es el patrón correcto?
4. ¿La separación `instagram_source` abstract / `hikerapi_client` concrete es la mejor forma?

### B. Estrategia de Costos

5. ¿Cuál es la mejor estrategia para mantener el pipeline útil pero económico?
   - ¿Reducir más las llamadas?
   - ¿Implementar modo "dry run" con cache agresivo?
   - ¿Migrar de HikerAPI a otra solución?
6. ¿Cómo evitar el "burn rate" cuando hay errores que disparan retries?
7. ¿Vale la pena re-habilitar Apify como fallback?

### C. Calidad de Candidatos

8. ¿Por qué retornamos 0 candidatos aunque encontremos 254 profiles?
9. ¿El scoring está bien calibrado o necesita reentrenamiento?
10. ¿Cómo encontrar creators reales y no tiendas/B2B en Instagram VE?

### D. Observabilidad

11. ¿Qué métricas mínimas deberíamos trackear?
12. ¿Cómo construir un dashboard de costos por step/run/campaign?

### E. Arquitectura de Fallback

13. Si HikerAPI falla (como ahora), ¿cuál debería ser la estrategia?
14. ¿Apify vale la pena arreglarlo o deberíamos buscar otra solución?
15. ¿Vale la pena explorar Meta Business API / TikTok Research API?

### F. Refactor

16. ¿Qué partes del código worker.py están "smelly" y necesitan refactor?
17. ¿Cómo manejar mejor el "freshness" de los datos?
18. ¿La lógica de scoring está mezclada con lógica de pipeline? ¿Vale la pena separar?

---

## 🎯 LO QUE ESPERO DE TI

Dame un **plan de acción estructurado** con:

### Corto plazo (esta semana)
- [ ] Fixes críticos para desbloquear pipeline
- [ ] Tests que validen el flujo end-to-end
- [ ] Monitoreo básico de costos

### Mediano plazo (este mes)
- [ ] Refactor arquitectónico de las áreas problemáticas
- [ ] Implementación de cache inteligente
- [ ] Dashboard de observabilidad

### Largo plazo (próximo trimestre)
- [ ] Estrategia multi-fuente (HikerAPI + Apify + Meta + TikTok)
- [ ] Auto-scaling del pipeline
- [ ] Mejoras de calidad de candidatos

---

## 📚 RECURSOS

### Documentación Oficial
- HikerAPI: https://api.hikerapi.com/docs
- FastAPI: https://fastapi.tiangolo.com
- ARQ: https://arq-docs.helpmanual.io

### Archivos Clave para Revisar
1. `apps/api/app/workers/worker.py` (1759 líneas) - Pipeline completo
2. `packages/discovery/discovery/tools/hikerapi_client.py` (727 líneas) - Cliente HikerAPI
3. `packages/discovery/discovery/scoring/lens_score.py` - Scoring
4. `packages/discovery/discovery/brief_parser.py` - Parsing de brief con DeepSeek
5. `packages/discovery/discovery/query_builder.py` - Query building
6. `docs/ARQUITECTURA_LENS.md` - Documentación completa

### Información del Proyecto
- **Cliente actual:** Nestlé Venezuela / Purina Dog Chow
- **Caso de uso:** Encontrar influencers de mascotas en VE
- **Budget mensual objetivo:** < $10 USD/mes
- **Performance target:** Run completa en < 3 min, < 100 API calls

---

## 🚀 CÓMO EMPEZAR

1. Lee `docs/ARQUITECTURA_LENS.md` primero
2. Después `apps/api/app/workers/worker.py` (líneas 150-900 son el pipeline)
3. Después `packages/discovery/discovery/tools/hikerapi_client.py`
4. Identifica problemas arquitectónicos
5. Propón soluciones concretas con código

**Sé directo, brutal en honestidad, y enfócate en soluciones prácticas.**

---

*Documento generado: 2026-08-13*
*Para: Claude Code Opus 5 / Senior Full-Stack Developer*
