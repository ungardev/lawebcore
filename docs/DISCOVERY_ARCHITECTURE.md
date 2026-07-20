# Discovery Module — "El Ojo que Todo lo Ve"

> **Versión:** 2.0.0 — Sprint 1
> **Proyecto:** La Web Strategist & Manager (P.I.A.R.)
> **Fecha:** Julio 2026
> **Repo:** `github.com/ungardev/lawebcore`
> **Deployed:** `https://lawebcore-production.up.railway.app`

---

## 1. Visión del producto

### 1.1 Qué es "El Ojo que Todo lo Ve"

Un **módulo de descubrimiento de influencers** dentro de La Web Strategist & Manager que permite al equipo describir un brief de campaña en lenguaje natural y recibir una lista curada de los mejores perfiles para ejecutarla, con scoring basado en 4 KPIs propietarios: **LWFA Scoring**.

El equipo describe en español:
> *"Necesito influencers en Venezuela para Purina Dog Chow, mujeres 25-45, tono aspiracional, Caracas y Valencia, presupuesto $3.000"*

Y el sistema devuelve prospectos verificados con LWFA composite score, metrics oficiales de Instagram, y ROI esperado.

### 1.2 Posicionamiento único

| Competidor | Qué hacen | Qué hacemos nosotros |
|---|---|---|
| HypeAuditor | Filtros estáticos + datos genéricos | **Pipeline 4 capas Apify + LWFA scoring local** |
| Modash | Dashboard de métricas | **Cerebro conversacional + data oficial Instagram** |
| Metricool | Analytics de cuentas propias | **Discovery de cuentas nuevas + engagement real** |
| Apify (standalone) | Scraping puro | **Scraping + LWFA + razonamiento IA** |

### 1.3 Diferenciadores clave

- **Pipeline 4 capas Apify** — datos oficiales de Instagram, no estimaciones
- **LWFA Scoring** — 4 KPIs exclusivos (ICA, Geo-Foco, Velocity, Business Intent)
- **Keywords Gemini** — 28 hashtags estratégicos organizados en 5 categorías
- **Datos locales VE/LATAM** — benchmarks propios, no genéricos globales
- **Costo ultra-bajo** — ~$3.30 por campaña con Apify Free tier

---

## 2. Arquitectura del sistema

### 2.1 Stack tecnológico

| Componente | Tecnología | Notas |
|---|---|---|
| **LLM Conversacional** | DeepSeek-chat (DeepSeek-V3) | $0.14/$0.28 per 1M tokens, contexto 64K |
| **Embeddings** | fastembed `all-MiniLM-L6-v2` | Via pgvector en Supabase |
| **Orquestador** | LangGraph | State machine, memoria persistente |
| **Vector DB** | Supabase pgvector | Cero costo extra |
| **Cola async** | ARQ + Redis | Workers en Railway |
| **Scraping** | Apify (3 actores Instagram) | Instagram search/hashtag/profile/engagement |
| **Analytics** | Metricool API | Métricas de redes propias |
| **Rate limiting** | slowapi | Middleware FastAPI |
| **Cost tracking** | Tabla `api_costs` + middleware | Custom |

### 2.2 Arquitectura de capas

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                            │
│  DiscoveryChatPage          DiscoverySearchPage                 │
│  [Chat IA con tarjetas      [Búsqueda directa con              │
│   de candidatos inline]      filtros por plataforma]           │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP / WebSocket
┌─────────────────────────────▼───────────────────────────────────┐
│                     FASTAPI BACKEND                            │
│  /api/v1/discovery/conversations  /api/v1/discovery/search    │
│  /api/v1/discovery/runs/{id}     /api/v1/discovery/candidates │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│              LANGGRAPH ORCHESTRATOR (packages/discovery/)       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  State Machine: [start] → [brief] → [refining] →       │  │
│  │  [searching] → [candidates_review] → [done]             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌────────────┐ ┌─────────────┐ ┌──────────────────────────┐   │
│  │BriefParser │ │QueryBuilder│ │   ResultRanker            │   │
│  │(DeepSeek)  │ │(DiscoveryPlan) │  (LWFA KPIs + math)     │   │
│  └────────────┘ └─────────────┘ └──────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                  TOOL LAYER (packages/discovery/tools/)         │
│  ┌──────────────────┐ ┌────────────┐ ┌──────────────────────┐  │
│  │  ApifyClient     │ │MetaClient │ │   MetricoolClient    │  │
│  │  (4 actores IG)  │ │(deferred) │ │   (redes propias)    │  │
│  └──────────────────┘ └────────────┘ └──────────────────────┘  │
│  ┌──────────────────┐ ┌────────────┐ ┌──────────────────────┐  │
│  │  TikTokClient    │ │YouTubeClient│ │                      │  │
│  │  (deferred)      │ │(deferred)  │ │                      │  │
│  └──────────────────┘ └────────────┘ └──────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│               SUPABASE (Postgres + pgvector)                   │
│  discovery_runs | discovery_candidates | discovery_conversations  │
│  discovery_messages | api_costs | integration_credentials         │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    ARQ WORKERS (Railway)                        │
│  discovery_run_task | embed_document_task | generate_insight_task│
│  sync_metricool_task | scheduled_reports_cron                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Pipeline de 4 Capas (Discovery + Enrichment + Analytics + Scoring)

### 3.1 Vista general

```
[BRIEF] → STEP 1 → STEP 2 → STEP 3 → STEP 4 → STEP 5 → [TOP CANDIDATES]
```

| Step | Actor Apify | Método | Input | Output |
|---|---|---|---|---|
| 1 | `instagram-search-scraper` | `search_users_by_multiple_keywords()` | 28 keywords | ~250 handles únicos |
| 2 | `instagram-hashtag-scraper` | `scrape_hashtags_batch()` | 22 hashtags | ~660 posts con geotags |
| 3 | `instagram-profile-scraper` | `search_instagram_profiles_batch()` | top 80 handles | profiles enriquecidos |
| 4 | `engagement-analytics` | `analyze_profile_engagement()` | top 20 handles × 30 posts | velocity, consistency, content_mix |
| 5 | — (Python) | `calculate_lwfa_composite()` | analytics + profiles | score 0-100 por candidato |

### 3.2 STEP 1: Keyword Discovery

**Actor:** `apify/instagram-search-scraper`
**Método:** `search_users_by_multiple_keywords(keywords, limit_per_keyword=30)`

Busca perfiles de Instagram por keywords usando el actor `instagram-search-scraper` con `searchType=users`. Las keywords están organizadas en 5 categorías Gemini:

```python
DISCOVERY_KEYWORDS = {
    "brand_competition": [
        "DogChow", "Purina", "PurinaDogChow", "Pedigree Venezuela",
        "Ganador premium perros", "Dogui alimento perros", "RoyalCanin Venezuela",
    ],
    "lifecycle_health": [
        "cachorros", "nutricion canina", "veterinaria venezuela",
        "perro senior", "salud canina", "veterinario perros",
    ],
    "consumer_personas": [
        "dog mom", "dog dad", "amor perruno", "adopcion perros venezuela",
        "rescate animal venezuela", "adopta no compres",
    ],
    "market_trends": [
        "comida barf perros", "alimento natural perros", "sin grano perros",
    ],
    "nicho_ve": [
        "mascotasvzla", "perrosdevzla", "vzla", "caracas",
        "maracaibo", "valencia venezuela",
    ],
}
```

**Resultado:** hasta 250 handles únicos deduplicados.

### 3.3 STEP 2: Hashtag Deep Dive

**Actor:** `apify/instagram-hashtag-scraper`
**Método:** `scrape_hashtags_batch(hashtags, results_per_hashtag=30)`

Obtiene posts de hashtags estratégicos con geotags y engagement. Actor dedicado que soporta `locationName` para geo-filtro:

```python
HASHTAGS_GEMINI = [
    # Brand & Competition
    "#DogChow", "#Purina", "#Pedigree", "#Cachorros", "#PerroSenior",
    # Consumer Personas
    "#DogMom", "#DogDad", "#AmorPerruno", "#AdoptaNoCompres",
    # Nicho VE
    "#mascotasvzla", "#perrosdevzla", "#vzla", "#venezuela",
    # Health & Trends
    "#NutricionCanina", "#Veterinaria", "#ComidaBarf", "#SinGrano",
]
```

**Resultado:** ~660 posts con `ownerUsername`, `likesCount`, `commentsCount`, `geotag`.

### 3.4 STEP 3: Profile Enrichment

**Actor:** `apify/instagram-profile-scraper`
**Método:** `search_instagram_profiles_batch(handles)` (batch de 10 en paralelo)

Enriquece los handles únicos con datos oficiales de Instagram:

- `followersCount` — número de seguidores
- `followsCount` — seguidos
- `postsCount` — número de posts
- `isVerified` — cuenta verificada
- `isBusinessAccount` — cuenta de negocio
- `externalUrl` — link en bio
- `about` → `country` — país del perfil (del about section)
- `latestPosts` — últimos posts para cálculo de ER

**Resultado:** profiles enriquecidos, deduplicados por `username`.

### 3.5 STEP 4: Engagement Analytics

**Actor:** `easy_scraper/instagram-profile-engagement-analytics`
**Método:** `analyze_profile_engagement(usernames, posts_to_analyze=30)`

Para los top 20 perfiles (por followers), obtiene métricas avanzadas:

- `avg_engagement_rate_pct` — ER promedio
- `avg_engagement_velocity_per_day` — velocidad de engagement
- `like_to_comment_ratio` — ratio likes/comentarios
- `content_mix_clips_pct` / `carousel` / `image` — distribución de formatos
- `engagement_consistency_score` — consistencia del engagement
- `comment_rate_pct` — tasa de comentarios (precursor ICA)
- `top_geotags` — geotags más usados
- `captions_sample` — muestra de captions

### 3.6 STEP 5: LWFA Scoring

**Función:** `calculate_lwfa_composite()` en `result_ranker.py`

Score compuesto 0-100 basado en 4 KPIs exclusivos:

```python
def calculate_lwfa_composite(
    engagement_rate: float,      # 30% peso
    business_intent: float,      # 20% peso
    velocity_score: float,       # 15% peso (normalizado)
    geo_foco: float,            # 15% peso
    consistency_score: float,   # 10% peso
    clips_pct: float,           # 10% peso (reels)
) -> float:
```

**4 KPIs exclusivos:**

1. **ICA (Index de Conversión Aparentada):**
   ```python
   def calculate_ica(comments: list[str], views: int) -> float:
       matches = sum(1 for c in comments
                     if any(kw in c.lower()
                           for kw in ["precio","donde","link","comprar","tienda"]))
       return (matches / len(comments)) * 100
   ```

2. **Geo-Foco Real:**
   ```python
   def calculate_geo_foco_real(geotags, captions, profile_bio) -> float:
       # Cruza geotags VE (caracas, vzla, maracaibo...)
       # + español en captions + país en bio
       # Score 0-1
   ```

3. **Engagement Velocity:**
   ```python
   def calculate_engagement_velocity(likes, comments, posts, days) -> float:
       return (likes + comments) / max(posts, 1) / max(days, 1)
   ```

4. **Business Intent:**
   ```python
   def calculate_business_intent(profile) -> float:
       return 0.4*has_external_url + 0.4*has_facebook_page + 0.2*is_business
   ```

---

## 4. Schema de base de datos

### 4.1 Tablas principales

#### `discovery_runs`
```sql
CREATE TABLE discovery_runs (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  bu_id                 UUID REFERENCES business_units(id),
  created_by            UUID REFERENCES users(id),
  brief_text            TEXT NOT NULL,
  brief_parsed          JSONB,
  status                TEXT DEFAULT 'pending',
  total_candidates      INTEGER DEFAULT 0,
  actual_cost_usd       NUMERIC(10,4),
  started_at            TIMESTAMPTZ,
  completed_at          TIMESTAMPTZ,
  error                 TEXT,
  metadata              JSONB,  -- step tracking, candidates_found, etc.
  created_at            TIMESTAMPTZ DEFAULT NOW()
);
```

#### `discovery_candidates`
```sql
CREATE TABLE discovery_candidates (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  run_id                UUID REFERENCES discovery_runs(id) ON DELETE CASCADE,
  platform              TEXT NOT NULL,
  handle                TEXT NOT NULL,
  url                   TEXT,
  followers             BIGINT,
  engagement_rate       NUMERIC(8,6),
  match_score           NUMERIC(5,2),  -- LWFA composite 0-100
  -- LWFA KPIs almacenados en raw_payload
  status                TEXT DEFAULT 'new',
  raw_payload           JSONB,
  fetched_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (run_id, platform, handle)
);
```

---

## 5. Estructura de archivos

```
packages/discovery/discovery/
├── __init__.py
├── brief_parser.py      # BriefParser agent (DeepSeek)
├── orchestrator.py      # LangGraph state machine
├── query_builder.py     # Gemini keywords → DiscoveryPlan
│                          DISCOVERY_KEYWORDS (5 categorías, 28 keywords)
│                          build() → DiscoveryPlan
├── result_ranker.py     # LWFA scoring (4 KPIs + composite)
│                          calculate_ica()
│                          calculate_geo_foco_real()
│                          calculate_engagement_velocity()
│                          calculate_business_intent()
│                          calculate_lwfa_composite()
├── schemas.py           # BriefStructured, DiscoveryPlan, CandidateMetrics
└── tools/
    ├── __init__.py
    ├── apify_client.py  # 3 actores + 6 métodos nuevos
    │   INSTAGRAM_PROFILE_SCRAPER = "apify~instagram-profile-scraper"
    │   INSTAGRAM_HASHTAG_SCRAPER = "apify/instagram-hashtag-scraper"
    │   INSTAGRAM_SEARCH_SCRAPER = "apify/instagram-search-scraper"
    │   ENGAGEMENT_ANALYTICS = "easy_scraper/instagram-profile-engagement-analytics"
    │   search_instagram_users_by_keyword()
    │   search_trending_hashtags()
    │   search_users_by_multiple_keywords()
    │   scrape_hashtag_posts()
    │   scrape_hashtags_batch()
    │   analyze_profile_engagement()
    ├── meta_client.py
    ├── tiktok_client.py
    ├── youtube_client.py
    └── metricool_client.py

apps/api/app/workers/worker.py
├── discovery_run_task()  # Pipeline 5 pasos (STEP 1-5)
└── _raw_to_candidate_dict()
```

---

## 6. Costos operacionales (Sprint 1)

| Step | Operación | Resultados | Costo Free | Costo CEO |
|---|---|---|---|---|
| 1 | Keyword search (28 keywords × 30 users) | 480 users | $1.30 | $1.10 |
| 2 | Hashtag posts (22 hashtags × 30 posts) | 660 posts | $1.43 | $1.21 |
| 3 | Profile enrichment (80 profiles) | 80 profiles | $0.21 | $0.18 |
| 4 | Engagement analytics (20 × 30 posts) | 600 posts | $0.36 | $0.18 |
| | **TOTAL por campaña** | | **~$3.30** | **~$2.67** |

**Apify Free $5 credit → 1.5 campañas completas**
**Apify CEO tier $25-29 → 9-10 campañas completas**

---

## 7. API Endpoints

### 7.1 Chat conversacional

```
POST   /api/v1/discovery/conversations
       → Crea conversación nueva

GET    /api/v1/discovery/conversations
       → Lista conversaciones del usuario

POST   /api/v1/discovery/conversations/{id}/messages
       Body: { "content": "texto del usuario" }
       → Procesa mensaje con LangGraph

DELETE /api/v1/discovery/conversations/{id}
       → Abandona conversación
```

### 7.2 Búsqueda directa

```
POST   /api/v1/discovery/search
       Body: BriefStructured (JSON)
       → Crea discovery_run, dispara ARQ worker, retorna run_id

GET    /api/v1/discovery/runs/{id}
       → Estado del run (pending/running/completed/failed)

GET    /api/v1/discovery/runs/{id}/candidates
       → Lista de candidatos encontrados

GET    /api/v1/discovery/runs/{id}/candidates/{candidate_id}
       → Detalle de un candidato
```

### 7.3 Gestión de candidatos

```
POST   /api/v1/discovery/candidates/{id}/save
       → Convierte candidate → influencer real

POST   /api/v1/discovery/candidates/{id}/dismiss
       → Descarta candidato

GET    /api/v1/discovery/candidates?run_id=&status=&page=&limit=
       → Lista candidatos con filtros
```

---

## 8. Flujo de implementación

### Sprint 1 ✅ (Jul 20)
- [x] Pipeline 4 capas Apify
- [x] LWFA Scoring (4 KPIs)
- [x] Gemini keywords (28 keywords en 5 categorías)
- [x] Commit `4b379d4`

### Sprint 2 (Jul 28 — **PRÓXIMO**)
- [ ] End-to-end Purina Dog Chow demo
- [ ] Redis cache layer para reducir costo Apify
- [ ] Meta for Developers app setup (App Review)
- [ ] Dashboard de costos por campaña

### Sprint 3 (Ago 4)
- [ ] TikTok Research API (post-aprobación)
- [ ] Outreach automation (Resend email)
- [ ] Feedback loop (user accept/dismiss → mejora scoring)

### Sprint 4 (Ago 11)
- [ ] Multi-bu / multi-tenant prep
- [ ] BI dashboard con Metabase
- [ ] PWA / mobile

---

## 9. Decisiones técnicas cerradas

| Decisión | Valor |
|---|---|
| **Source de datos** | Apify (único, no mockup, no Excel) |
| **LLM** | DeepSeek-V3 únicamente |
| **Embeddings** | fastembed `all-MiniLM-L6-v2` via pgvector |
| **Plataforma inicial** | Instagram únicamente |
| **Meta for Developers** | Diferido a Sprint 2 (2-6 semanas approval) |
| **TikTok** | Diferido a Sprint 3 |
| **Costo/campaña** | ~$3.30 (Free tier) |
| **Mockup data** | DEPRECATED — stats from real system |

---

## 10. Compliance y ToS

| Plataforma | Forma legítima | Riesgo |
|---|---|---|
| Instagram | Apify (datos públicos, consentimiento implícito) | Bajo si datos públicos |
| TikTok | TikTok Research API (pendiente aprobación) | Bajo con API oficial |
| Meta | Meta Business API (diferido Sprint 2) | Bajo con API oficial |
| Apify | Scraper de datos públicos | Términos de Apify |

**Principio:** Apify como source principal para data oficial Instagram. APIs oficiales (Meta Graph, TikTok Research) como complemento cuando estén aprobadas.

---

*Documento preparado para revisión por líder P.I.A.R. — Julio 2026*
*Autor: Equipo La Web Figital Agency*
