# P.I.A.R. Discovery — Arquitectura del Módulo de Descubrimiento Conversacional IA

> **Versión:** 1.0.0 — Plan de implementación
> **Proyecto:** La Web Strategist & Manager (P.I.A.R.)
> **Fecha:** Julio 2026
> **Repo:** `github.com/ungardev/lawebcore`

---

## 1. Visión del producto

### 1.1 Qué es P.I.A.R. Discovery

Un **módulo conversacional inteligente** dentro de La Web Strategist & Manager que permite al equipo (y eventualmente a clientes) describir un brief de campaña en lenguaje natural y recibir una lista curada de los mejores influencers para ejecutarla.

El equipo describe en español, en cualquier nivel de detalle:
> *"Necesito 5 influencers en Venezuela para una marca de café premium, mujeres 25-35, tono aspiracional, Caracas y Valencia, presupuesto $3.000"*

Y el sistema devuelve prospectos verificados con match score, metrics, audience breakdown, rate cards estimados y ROI esperado.

### 1.2 Posicionamiento único

| Competidor | Qué hacen | Qué hacemos nosotros |
|---|---|---|
| HypeAuditor | Filtros estáticos + datos genéricos | **Lenguaje natural + data local VE/LATAM + math en tiempo real** |
| Modash | Dashboard de métricas | **Cerebro conversacional con contexto de campaña** |
| Metricool | Analytics de cuentas propias | **Discovery de cuentas nuevas + analytics propio** |
| Apify (standalone) | Scraping puro | **Scraping + scoring + razonamiento IA** |

### 1.3 Diferenciadores clave

- **Conversación natural en español** — el equipo piensa en voz alta y el sistema interpreta
- **Cálculo aritmético en tiempo real** — ROI estimado, engagement proyectado, reach ajustado
- **Datos específicos Venezuela/LATAM** — benchmarks propios de LWFA, no genéricos globales
- **Memoria contextual** — recuerda campañas anteriores, precedentes de pricing, preferencias de marca
- **Costo operativo bajo** — ~$60-110/mes en APIs externas, mucho menor que suscripciones SaaS

---

## 2. Arquitectura del sistema

### 2.1 Stack tecnológico

| Componente | Tecnología | Notas |
|---|---|---|
| **LLM Conversacional** | DeepSeek-chat | $0.14/$0.28 per 1M tokens, contexto 64K |
| **LLM Razonamiento** | DeepSeek-R1 | Para decisiones multi-step del orchestrator |
| **Orquestador** | LangGraph | State machine, memoria persistente |
| **Vector DB** | Supabase pgvector | Ya existe, cero costo extra |
| **Cola async** | ARQ + Redis | Ya existe, solo implementar jobs |
| **HTTP Client** | httpx async | Ya existe |
| **Scraping** | Apify | Instagram/TikTok scrapers oficiales |
| **APIs oficiales** | Meta Business, TikTok Research, YouTube Data | Gratuitas hasta límites |
| **Analytics** | Metricool API | Plan Agency |
| **Rate limiting** | slowapi | Middleware FastAPI |
| **Retry** | tenacity | Reactivado de deps |
| **Cost tracking** | Tabla `api_costs` + middleware | Custom |
| **Email** | Resend | Solo para outreach |

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
│  /discovery/conversations  /discovery/search                    │
│  /discovery/runs/{id}      /discovery/candidates/{id}           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│              LANGGRAPH ORCHESTRATOR (Cerebro)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  State Machine: [brief] → [refining] → [searching] →    │  │
│  │                  [ranking] → [candidates_review] → [done] │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌────────────┐ ┌─────────────┐ ┌──────────────────────────┐   │
│  │ BriefParser│ │QueryBuilder│ │   ResultRanker            │   │
│  │ (DeepSeek) │ │ (Python)   │ │ (DeepSeek + math)        │   │
│  └────────────┘ └─────────────┘ └──────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                  TOOL LAYER (Plugins)                          │
│  ┌────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐   │
│  │ Apify  │ │Meta Graph │ │ TikTok │ │YouTube │ │ Metricool│   │
│  │Client  │ │  API     │ │Research│ │ Data   │ │  API     │   │
│  └────────┘ └──────────┘ └────────┘ └────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│               SUPABASE (Postgres + pgvector)                   │
│  discovery_runs | discovery_candidates | discovery_conversations │
│  discovery_messages | api_costs | integration_credentials        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    ARQ WORKERS (Redis)                         │
│  discovery_run_task | embed_document_task | sync_influencer     │
│  scheduled_reports_cron | metricool_sync_task                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Schema de base de datos

### 3.1 Nuevas tablas

#### `discovery_runs`
Job de búsqueda. Un run puede ejecutarse en background (worker ARQ) y tomar varios minutos.

```sql
CREATE TABLE discovery_runs (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  bu_id                 UUID REFERENCES business_units(id),
  created_by            UUID REFERENCES users(id),
  brief_text            TEXT NOT NULL,
  brief_parsed          JSONB,
  product_name          TEXT,
  brand_id              UUID REFERENCES brands(id),
  industry              TEXT,
  niches                TEXT[],
  audience_gender       TEXT,
  audience_age_min      INTEGER,
  audience_age_max      INTEGER,
  audience_countries    TEXT[],
  audience_cities      TEXT[],
  budget_usd            NUMERIC(12,2),
  tone                  TEXT,
  platforms             TEXT[],
  status                TEXT DEFAULT 'pending',
  total_candidates      INTEGER DEFAULT 0,
  accepted              INTEGER DEFAULT 0,
  estimated_cost_usd    NUMERIC(10,4),
  actual_cost_usd       NUMERIC(10,4),
  started_at            TIMESTAMPTZ,
  completed_at          TIMESTAMPTZ,
  error                 TEXT,
  metadata              JSONB,
  created_at            TIMESTAMPTZ DEFAULT NOW()
);
```

#### `discovery_candidates`
Candidatos encontrados por un run. Antes de aprobarse como influencer real.

```sql
CREATE TABLE discovery_candidates (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  run_id                UUID REFERENCES discovery_runs(id) ON DELETE CASCADE,
  platform              TEXT NOT NULL,
  platform_user_id      TEXT,
  handle                TEXT NOT NULL,
  url                   TEXT,
  full_name             TEXT,
  bio                   TEXT,
  avatar_url            TEXT,
  country               TEXT,
  city                  TEXT,
  language_primary      TEXT,
  followers             BIGINT,
  following             BIGINT,
  posts_count           INTEGER,
  avg_likes             INTEGER,
  avg_comments          INTEGER,
  avg_views             BIGINT,
  engagement_rate       NUMERIC(8,6),
  audience_credibility  NUMERIC(5,2),
  audience_quality      NUMERIC(5,2),
  audience_gender_split JSONB,
  audience_age_buckets  JSONB,
  audience_top_countries JSONB,
  audience_top_cities   JSONB,
  audience_interests    TEXT[],
  match_score           NUMERIC(5,2),
  niche_relevance       NUMERIC(5,2),
  geo_relevance         NUMERIC(5,2),
  audience_relevance    NUMERIC(5,2),
  content_quality       NUMERIC(5,2),
  rationale             TEXT,
  status                TEXT DEFAULT 'new',
  saved_as_influencer_id UUID REFERENCES influencers(id),
  contact_email         TEXT,
  contact_phone         TEXT,
  source_actor_run_id   TEXT,
  raw_payload           JSONB,
  fetched_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (run_id, platform, handle)
);
```

#### `discovery_conversations`
Conversaciones del chat de discovery. Gestionada por LangGraph.

```sql
CREATE TABLE discovery_conversations (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  user_id               UUID REFERENCES users(id),
  bu_id                 UUID REFERENCES business_units(id),
  state                 JSONB NOT NULL DEFAULT '{}'::jsonb,
  current_step          TEXT,
  discovery_run_id       UUID REFERENCES discovery_runs(id),
  accumulated_brief     TEXT,
  message_count         INTEGER DEFAULT 0,
  started_at            TIMESTAMPTZ DEFAULT NOW(),
  last_message_at       TIMESTAMPTZ DEFAULT NOW(),
  status                TEXT DEFAULT 'active'
);
```

#### `discovery_messages`
Mensajes individuales dentro de una conversación.

```sql
CREATE TABLE discovery_messages (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  conversation_id       UUID REFERENCES discovery_conversations(id) ON DELETE CASCADE,
  role                  TEXT NOT NULL,
  content               TEXT NOT NULL,
  tool_calls            JSONB,
  tool_results          JSONB,
  reasoning             TEXT,
  cost_usd              NUMERIC(10,6),
  latency_ms            INTEGER,
  created_at            TIMESTAMPTZ DEFAULT NOW()
);
```

#### `api_costs`
Tracking de costos de todas las APIs externas.

```sql
CREATE TABLE api_costs (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  provider              TEXT NOT NULL,
  operation             TEXT,
  entity_id             UUID,
  cost_usd              NUMERIC(10,6) NOT NULL,
  request_count         INTEGER DEFAULT 1,
  tokens_input          INTEGER,
  tokens_output         INTEGER,
  metadata              JSONB,
  occurred_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_api_costs_provider ON api_costs(provider, occurred_at);
```

#### `integration_credentials`
Credenciales encriptadas por BU para APIs externas.

```sql
CREATE TABLE integration_credentials (
  id                    UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  provider              integration_provider NOT NULL,
  business_unit_id      UUID REFERENCES business_units(id),
  encrypted_credentials JSONB NOT NULL,
  scopes                TEXT[],
  status                TEXT DEFAULT 'active',
  expires_at            TIMESTAMPTZ,
  last_used_at          TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(provider, business_unit_id)
);
```

### 3.2 Extensiones a tablas existentes

```sql
-- influencers: campos de discovery
ALTER TABLE influencers ADD COLUMN gender TEXT;
ALTER TABLE influencers ADD COLUMN age_range TEXT;
ALTER TABLE influencers ADD COLUMN latitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN longitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN audience_demographics JSONB;
ALTER TABLE influencers ADD COLUMN is_discoverable BOOLEAN DEFAULT TRUE;
ALTER TABLE influencers ADD COLUMN discovered_at TIMESTAMPTZ;
ALTER TABLE influencers ADD COLUMN discovery_query TEXT;
ALTER TABLE influencers ADD COLUMN discovery_confidence NUMERIC(5,2);

-- Enum para status de candidates
ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'new';
ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'saved';
ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'dismissed';
ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'contacted';
ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'replied';
ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'won';
ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'lost';
```

---

## 4. LangGraph Orchestrator

### 4.1 State Machine

```
┌─────────────┐
│   start    │ ← usuario inicia conversación
└──────┬──────┘
       │ brief_text recibido
       ▼
┌─────────────┐
│   brief    │ ← BriefParser agent interpreta el brief
└──────┬──────┘
       │ brief estructurado OK
       ▼
┌─────────────┐
│  refining   │ ← Usuario refine / confirma criterios
└──────┬──────┘
       │ confirmado
       ▼
┌─────────────┐
│  searching  │ ← Workers ejecutan búsquedas en paralelo
└──────┬──────┘
       │ resultados recibidos
       ▼
┌─────────────────┐
│    ranking     │ ← ResultRanker puntúa candidatos
└──────┬────────┘
       │ ranking completado
       ▼
┌─────────────────────┐
│ candidates_review   │ ← Usuario revisa, aprueba, descarta
└──────┬──────────────┘
       │ usuario selecciona → saved
       ▼
┌─────────────┐
│    done    │ ← Prospectos aprobados → influencers
└─────────────┘
```

### 4.2 Agentes

#### BriefParser (DeepSeek)
Interpreta el texto libre del usuario y lo convierte en estructura:

```python
class BriefStructured(BaseModel):
    product_name: str | None
    brand_id: UUID | None
    industry: str | None
    niches: list[str]
    audience_gender: Literal["female", "male", "all"]
    audience_age_min: int
    audience_age_max: int
    audience_countries: list[str]
    audience_cities: list[str]
    budget_usd: float | None
    tone: list[str]
    platforms: list[Literal["instagram", "tiktok", "youtube", "x"]]
    additional_context: str
```

**Prompt del BriefParser:**
> "Eres un planner de influencer marketing con 10 años de experiencia en Venezuela y LATAM. El usuario te describe un brief en lenguaje natural. Extrae todos los datos relevantes y organízalos. Si algo es ambiguo, pregunta. Si falta algo crítico (país, plataforma), pregunta antes de asumir."

#### QueryBuilder (Python puro, no LLM)
Transforma el brief estructurado en queries específicas por plataforma.

```python
def build_queries(brief: BriefStructured) -> dict[str, list[Query]]:
    queries = {}
    if "instagram" in brief.platforms:
        queries["instagram"] = build_instagram_queries(brief)
    if "tiktok" in brief.platforms:
        queries["tiktok"] = build_tiktok_queries(brief)
    if "youtube" in brief.platforms:
        queries["youtube"] = build_youtube_queries(brief)
    return queries
```

#### ResultRanker (DeepSeek + matemática)
Puntúa cada candidato con un score de 0-100:

```python
def calculate_match_score(
    candidate: CandidateMetrics,
    brief: BriefStructured,
    brand_historical: BrandBenchmarks | None
) -> MatchScoreResult:
    # Scoring dimensions
    niche_score = calculate_niche_relevance(candidate, brief.niches)
    geo_score = calculate_geo_relevance(candidate, brief.audience_cities)
    audience_score = calculate_audience_relevance(candidate, brief)
    quality_score = candidate.audience_quality / 100

    # Weighted final score
    match_score = (
        niche_score * 0.30 +
        geo_score * 0.25 +
        audience_score * 0.25 +
        quality_score * 0.20
    ) * 100

    # ROI estimado
    estimated_cost = infer_cost_by_tier(candidate.tier)
    expected_reach = candidate.followers * 0.85
    expected_engagement = expected_reach * candidate.engagement_rate
    roi_estimate = (expected_engagement * brand_historical.avg_engagement_value) / estimated_cost if estimated_cost > 0 else None

    return MatchScoreResult(
        match_score=match_score,
        niche_relevance=niche_score * 100,
        geo_relevance=geo_score * 100,
        audience_relevance=audience_score * 100,
        content_quality=quality_score * 100,
        estimated_cost=estimated_cost,
        expected_reach=expected_reach,
        expected_engagement=expected_engagement,
        roi_estimate=roi_estimate,
        rationale=generate_rationale(candidate, brief, match_score)
    )
```

---

## 5. Integraciones externas

### 5.1 Apify

**Scrapers utilizados:**
- `apify/instagram-hashtag-scraper` — busca posts por hashtag
- `apify/instagram-profile-scraper` — obtiene métricas de perfil específico
- `apify/tiktok-hashtag-scraper` — busca por hashtag en TikTok

**Patrón de uso:**
```python
class ApifyClient:
    BASE_URL = "https://api.apify.com/v2"
    TOKEN: str  # APIFY_API_TOKEN

    async def search_by_hashtag(
        self,
        platform: str,
        hashtag: str,
        country: str = "VE",
        min_followers: int = 10000,
        max_followers: int = 1000000
    ) -> list[CandidateData]:
        # Llama al actor de Apify
        # Espera webhook o polling de resultados
        # Parsea y retorna candidatos
```

**Costos:** $0.50-$5 por run según dataset size.

### 5.2 Meta Business API

**Permisos requeridos (App Review):**
- `instagram_basic` — ver perfiles de Instagram Business/Creator
- `pages_read_engagement` — métricas de páginas
- `instagram_graph_user_media` — publicaciones del usuario
- `instagram_insights` — métricas de Instagram (requiere Business o Creator account)

**Patrón de uso:**
```python
class MetaClient:
    APP_ID: str       # META_APP_ID
    APP_SECRET: str   # META_APP_SECRET
    ACCESS_TOKEN: str # Page or User access token

    async def get_instagram_account(self, page_id: str) -> IGAccount: ...
    async def get_media_metrics(self, ig_media_id: str) -> MediaMetrics: ...
    async def get_user_insights(self, ig_user_id: str, metric: str) -> list[Insight]: ...
```

### 5.3 TikTok Research API

**Estado:** Solicitud formal requerida (7-15 días).

**Permisos disponibles:**
- `content.search` — buscar contenido por keyword/hashtag
- `user.info` — información de perfil público
- `video.list` — lista de videos de un usuario

**Nota:** Solo funciona para cuentas públicas. No sirve para scraping de datos privados.

### 5.4 YouTube Data API v3

**Cuota gratuita:** 10,000 units/día.

**Endpoints útiles:**
- `search.list` — buscar por keyword, filtro por region (VE)
- `channels.list` — información de canal + subscriberCount
- `videoCategories.list` — categorías de contenido

```python
class YouTubeClient:
    API_KEY: str  # YOUTUBE_DATA_API_KEY

    async def search_channels(
        self,
        query: str,
        region: str = "VE",
        max_results: int = 50
    ) -> list[YouTubeChannelResult]: ...
```

### 5.5 Metricool

**Plan requerido:** Agency ($25/mes) para API completa.

**OAuth2 flow:**
```python
class MetricoolClient:
    CLIENT_ID: str
    CLIENT_SECRET: str
    ACCESS_TOKEN: str  # OAuth2 token

    async def get_analytics(
        self,
        channel: str,  # instagram, tiktok, youtube, twitter
        start_date: date,
        end_date: date
    ) -> ChannelAnalytics: ...
```

---

## 6. API Endpoints

### 6.1 Conversational (chat estilo WhatsApp)

```
POST   /api/v1/discovery/conversations
       → Crea conversación nueva

GET    /api/v1/discovery/conversations
       → Lista conversaciones del usuario

GET    /api/v1/discovery/conversations/{id}
       → Detalle de conversación + mensajes

POST   /api/v1/discovery/conversations/{id}/messages
       Body: { "content": "texto del usuario" }
       → Procesa mensaje con LangGraph, retorna respuesta IA

DELETE /api/v1/discovery/conversations/{id}
       → Abandona conversación
```

### 6.2 Búsqueda directa (sin chat)

```
POST   /api/v1/discovery/search
       Body: BriefStructured (JSON)
       → Crea discovery_run, dispara worker, retorna run_id

GET    /api/v1/discovery/runs/{id}
       → Estado del run (pending/running/completed/failed)

GET    /api/v1/discovery/runs/{id}/candidates
       → Lista de candidatos encontrados

GET    /api/v1/discovery/runs/{id}/candidates/{candidate_id}
       → Detalle de un candidato
```

### 6.3 Gestión de candidatos

```
POST   /api/v1/discovery/candidates/{id}/save
       → Convierte candidate → influencer real

POST   /api/v1/discovery/candidates/{id}/dismiss
       → Descarta candidato

GET    /api/v1/discovery/candidates?run_id=&status=&page=&limit=
       → Lista candidatos con filtros
```

### 6.4 Costos y métricas

```
GET    /api/v1/discovery/costs?provider=&from=&to=
       → Costos agregados por proveedor

GET    /api/v1/discovery/metrics
       → Dashboard: searches/mes, candidates found, avg match score
```

---

## 7. Flujo de implementación

### Fase 0 — Cimientos (1-2 sprints)
- [ ] Migration 0019 (discovery_runs, discovery_candidates, conversations, messages, api_costs, integration_credentials)
- [ ] Extension de influencers (8 columnas nuevas)
- [ ] Config: nuevas API keys (APIFY_API_KEY, META_APP_ID, etc.)
- [ ] Workers: funciones ARQ reales (discovery_run_task)
- [ ] Rate limiting middleware (slowapi)
- [ ] Cost tracking middleware
- [ ] Tests base con mocks de httpx

### Fase 1 — Cerebro IA (2-3 sprints)
- [ ] LangGraph orchestrator + BriefParser agent
- [ ] QueryBuilder (Instagram + TikTok + YouTube)
- [ ] ResultRanker (scoring + math)
- [ ] Memoria conversacional persistente
- [ ] Endpoint: POST /discovery/conversations/{id}/messages
- [ ] DiscoveryChatPage.tsx (UI chat)
- [ ] Mock data para validar UX sin gastar créditos

### Fase 2 — Scraper real (2-3 sprints)
- [ ] ApifyClient (Instagram hashtag scraper)
- [ ] MetaBusinessClient (con App Review completada)
- [ ] YouTubeClient
- [ ] MetricoolClient (OAuth)
- [ ] TikTok Research API (cuando llegue aprobación)
- [ ] DiscoverySearchPage.tsx (alternativa sin chat)
- [ ] Pipeline: candidate → influencer real

### Fase 3 — Outreach + Métricas (2 sprints)
- [ ] Resend integration (email transaccional)
- [ ] Templates de outreach + tracking
- [ ] Dashboard de api_costs
- [ ] Reportes semanales automáticos

### Fase 4 — Producción (3+ sprints)
- [ ] Tests E2E completos
- [ ] OAuth para influencer portal
- [ ] BI ejecutivo (Metabase)
- [ ] Plan de contingencia Meta/TikTok API changes

---

## 8. Costos operacionales

| Proveedor | Plan | Costo/mes | Uso estimado |
|---|---|---|---|
| DeepSeek-chat | Pay-per-use | $5-15 | 50 conversaciones/mes |
| OpenAI embeddings | Pay-per-use | $2-5 | RAG, 10K chunks |
| Apify | Team | $249/mes | 50 searches/mes |
| Metricool | Agency | $25/mes | API completa |
| Meta Business API | Free tier | $0 | Hasta 200 calls/hora |
| TikTok Research | Free (si approved) | $0 | Rate limited |
| YouTube Data API | Free tier | $0 | 10K units/día |
| Resend | Free | $0 | 3K emails/mes |
| **Total estimado** | | **~$280-300/mes** | |

A escala 10x: ~$500-700/mes.

---

## 9. Compliance y ToS

| Plataforma | Forma legítima | Riesgo si se viola |
|---|---|---|
| Instagram | Meta Business API (oficial) + Apify (datos públicos) | Baneo de cuenta + acción legal |
| TikTok | TikTok Research API (aprobado) | Baneo de app + IP block |
| YouTube | YouTube Data API v3 (oficial) | API key revocada |
| Facebook | Meta Business API (oficial) | Baneo de página + app |
| Apify | Scraper de datos públicos, consentimiento del usuario | Términos de Apify (bajo) |

**Principio:** NUNCA scraping de datos privados sin consentimiento explícito. Metodología defensiva: APIs oficiales primero, Apify como complemento para data que las APIs no exponen.

---

## 10. Estructura de archivos

```
apps/
├── api/
│   └── app/
│       ├── discovery/                    # NUEVO
│       │   ├── __init__.py
│       │   ├── orchestrator.py          # LangGraph state machine
│       │   ├── brief_parser.py          # BriefParser agent (DeepSeek)
│       │   ├── query_builder.py         # Transforma brief → queries
│       │   ├── result_ranker.py         # Scoring + math
│       │   ├── memory.py                # Estado conversacional
│       │   ├── schemas.py               # Pydantic models
│       │   └── tools/                   # Tool layer
│       │       ├── __init__.py
│       │       ├── apify_client.py
│       │       ├── meta_client.py
│       │       ├── youtube_client.py
│       │       ├── metricool_client.py
│       │       └── tiktok_client.py
│       ├── integrations/                # YA EXISTE
│       │   └── ...
│       ├── core/
│       │   ├── config.py               # MODIFICAR: nuevas keys
│       │   ├── rate_limiter.py         # NUEVO: slowapi middleware
│       │   └── cost_tracker.py         # NUEVO: middleware tracking
│       └── api/v1/
│           └── discovery.py            # NUEVO: routers
├── workers/
│   └── app/
│       └── worker.py                   # MODIFICAR: funciones reales
└── web/
    └── src/
        └── features/
            └── discovery/              # NUEVO
                ├── DiscoveryChatPage.tsx
                └── DiscoverySearchPage.tsx
supabase/
└── migrations/
    └── 00000000000019_discovery_foundation.sql  # NUEVO
.env.example                              # MODIFICAR
```

---

## 11. Decisiones técnicas pendientes

| Decisión | Opciones | Recomendación |
|---|---|---|
| **TikTok Research API** | Solicitar ahora vs. esperar | Solicitar ahora, Apify como fallback |
| **Metricool** | Agency ($25) vs. gratis | Agency desde día 1 para API completa |
| **X/Twitter API** | $100/mes vs. no incluir | No incluir en v1,太高 costo |
| **LangGraph vs. LangChain agents** | LangGraph más controlable | LangGraph, ya tenemos LangChain |
| **DeepSeek-R1** | Usar ahora vs. esperar estabilidad | Esperar hasta que sea estable en producción |

---

*Documento preparado para revisión técnica y aprobación de implementación.*
*Autor: Equipo La Web Figital Agency — Julio 2026*
