# LAWEBCORE — Project Status
> **Last updated:** 2026-07-30
> **Version:** Sprint 1 Complete · Sprint 2 In Progress
> **Repository:** `github.com/ungardev/lawebcore`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision](#2-product-vision)
3. [Architecture](#3-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Database Schema](#5-database-schema)
6. [Integrations](#6-integrations)
7. [Lens — Discovery Engine](#7-lens--discovery-engine)
8. [Apify Pipeline & LWFA Scoring](#8-apify-pipeline--lwfa-scoring)
9. [Cost Optimization](#9-cost-optimization)
10. [UI/UX & Design System](#10-uiux--design-system)
11. [Tech Debt](#11-tech-debt)
12. [Roadmap](#12-roadmap)
13. [Known Issues & Inconsistencies](#13-known-issues--inconsistencies)

---

## 1. Executive Summary

**La Web Core** is the internal platform of **La Web Figital Agency** (Venezuela) — a marketing campaign management + AI-powered influencer discovery system.

**Flagship module:** **Lens** (renamed from "Influencer Lens" by CEO on 2026-07-30). The vision is a super elite top-tier tool that appears to be made by Apple.

**Demo target:** Nestlé Venezuela / Purina Dog Chow — Jul 28, 2026
**Current focus:** Sprint 2 — Demo E2E + Redis cache + Meta setup + Cost dashboard

### Production URLs

| Service | URL |
|---|---|
| API | `https://lawebcore-production.up.railway.app` |
| Web | `https://lawebcore.vercel.app` |
| Database | `https://sdrsxeweobcnnqdxqhjb.supabase.co` |
| Repo | `github.com/ungardev/lawebcore` |

### Key Metrics

| Metric | Value |
|---|---|
| Cost per campaign (no cache) | ~$3.30 |
| Cost per campaign (with cache) | ~$0.30 |
| Monthly operational budget | $250 USD ($200 APIs + $50 infra) |
| Active campaigns seeded | 32 |
| Clients seeded | 14 |
| Brands seeded | 25 |

---

## 2. Product Vision

### The Problem

Agencies in LATAM spend thousands on low-quality influencers with no real engagement data, no precise geolocation filtering, and no proprietary scoring tools.

### The Solution — Lens

1. **4-layer Apify pipeline** → Official Instagram data (not estimates)
2. **LWFA Scoring** → 4 proprietary KPIs (ICA, Geo-Foco Real, Engagement Velocity, Business Intent)
3. **Conversational AI** (DeepSeek-V3) → User describes brand in natural language, system executes
4. **Local VE/LATAM data** → 9-tier benchmarks, 15 niche groups, 14 VE-specific keywords
5. **Ultra-low cost** → $0.30–$3.30 per campaign

### Positioning

| Competitor | What they do | What Lens does |
|---|---|---|
| HypeAuditor | Static filters + generic data | 4-layer pipeline + LWFA local |
| Modash | Metrics dashboard | Conversational brain + official IG data |
| Metricool | Own-account analytics | New-account discovery + real engagement |
| Apify standalone | Pure scraping | Scraping + LWFA + AI reasoning |

---

## 3. Architecture

### Monorepo Structure

```
lawebcore/
├── apps/
│   ├── api/                  # FastAPI backend (Python 3.12) → Railway
│   │   └── app/
│   │       ├── api/v1/      # Routes: auth, users, clients, brands, campaigns,
│   │       │                  #   influencers, kpis, dashboard, ai, projections,
│   │       │                  #   publicaciones, imports, scoring, sentiment,
│   │       │                  #   discovery, lens, admin
│   │       ├── core/         # security, logging, rate_limiter, cost_tracker,
│   │       │                  #   worker_enqueuer, piar_*
│   │       ├── models/       # SQLAlchemy 2.0 models
│   │       ├── schemas/      # Pydantic ingest/import schemas
│   │       ├── services/     # AI service, proposal generator
│   │       └── workers/      # ARQ worker + discovery_run_task (821 lines)
│   │
│   └── web/                  # React 19 + Vite → Vercel
│       └── src/
│           ├── features/     # Feature-sliced (auth, campaigns, lens, etc.)
│           ├── components/   # data-table, layout, ui (shadcn)
│           ├── hooks/        # Shared hooks
│           └── lib/          # API clients, supabase, format, utils
│
├── packages/
│   ├── discovery/            # ★ LangGraph orchestrator + Apify + LWFA
│   ├── shared-core/           # Config, DB, Supabase REST
│   ├── shared-ai/             # DeepSeek + fastembed embeddings
│   ├── shared-types/          # TS stubs
│   └── ui/                   # UI stubs
│
├── supabase/
│   ├── migrations/            # 32 SQL files + Railway batch 0091-0098
│   ├── seed.sql              # Roles, permissions, BUs, KPIs
│   ├── seed_excel_data.sql   # 14 clients, 25 brands, 32 campaigns
│   └── schema.sql            # Consolidated (960 lines)
│
├── docs/                      # 10+ markdown documentation files
├── scripts/                   # 7 utility scripts (ETL, Apify extraction)
└── .github/workflows/ci.yml  # CI: API + web + DB jobs
```

### Railway Ecosystem

| Service | Config | Notes |
|---|---|---|
| `lawebcore` | `railway.toml` | Main API + spawns ARQ worker as child process |
| `lawebcore-redis` | — | Redis 8.2.1, ARQ queue + Apify cache |
| PostgreSQL DB | Railway Postgres | Separate from Supabase for specific workloads |

> **Note:** The ARQ worker can run as a **standalone Railway service** (`STANDALONE_WORKER=true`) or as a **child process** of the API (current default via `multiprocessing.spawn`).

### Deployment Flow

```
GitHub (main) → GitHub Actions CI → Success → Railway redeploy (API) + Vercel redeploy (Web)
                                                              ↓
                                               Supabase migrations applied automatically
```

---

## 4. Technology Stack

### Backend

| Component | Technology |
|---|---|
| Runtime | Python 3.12 (slim Docker) |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async + asyncpg) |
| Validation | Pydantic v2 |
| Async queue | ARQ + Redis |
| Logging | structlog |
| Rate limit | slowapi |
| Monitoring | Prometheus (`/metrics`), Sentry |
| Auth | bcrypt + python-jose (HS256 JWT custom) |
| Worker | ARQ (spawned as child process of API) |

### Frontend

| Component | Technology |
|---|---|
| Framework | React 19 |
| Bundler | Vite 6 |
| Language | TypeScript 5.7 |
| Styling | Tailwind 3.4 + CSS vars + shadcn patterns |
| UI primitives | Radix UI |
| Data fetching | TanStack Query 5 |
| HTTP | Axios |
| Forms | react-hook-form + Zod |
| Tables | @tanstack/react-table |
| Charts | Recharts |
| Toasts | Sonner |
| Icons | Lucide React |
| DnD | @dnd-kit (Kanban) |
| Routing | React Router 7 |
| State global | Zustand |

### Packages

| Package | Purpose |
|---|---|
| `discovery` | LangGraph orchestrator + tools (Apify, Meta, TikTok, YouTube, Metricool) + LWFA |
| `shared-core` | Settings Pydantic + async DB session + Supabase REST |
| `shared-ai` | DeepSeek-V3 (cache mode) + fastembed `all-MiniLM-L6-v2` |

### Database

| Component | Technology |
|---|---|
| Primary DB | PostgreSQL 16 (Supabase Cloud) |
| Extensions | pgvector (384-dim embeddings) |
| Auth backend | Supabase Auth (schema only — not primary auth) |
| Storage | Supabase Storage |
| Realtime | Supabase Realtime |

### Hosting

| Service | Provider | Est. Cost |
|---|---|---|
| Frontend | Vercel | Free |
| API + Worker + Redis | Railway | ~$20/mo |
| DB Postgres + pgvector | Supabase Cloud | Free tier |

---

## 5. Database Schema

### Enum Types

Defined in `supabase/migrations/0002_enums.sql`:
- `user_status`, `campaign_status`, `campaign_objective`, `influencer_tier`
- `campaign_influencer_status`, `campaign_link_type`
- `kpi_category`, `kpi_source`, `task_status`, `task_priority`
- `integration_provider` (HYPEAUDITOR, CANVA, GOOGLE_DRIVE, TRELLO, SLACK, META, TIKTOK, YOUTUBE, OPENAI, ANTHROPIC)
- `ai_job_status`, `ai_job_type` (EMBEDDING, RAG_QUERY, BRIEF_GENERATION, POST_MORTEM_GENERATION, INSIGHT_GENERATION, FORECAST, MATCHMAKING, SENTIMENT_ANALYSIS)
- `audit_action`
- **Discovery enums:** `candidate_status`, `discovery_run_status`, `conversation_step`

### Key Tables

#### Identity & Permissions (migration 0003)
- `business_units` — BU catalog
- `users` — FK to `auth.users`, email, full_name, primary_bu_id, status, locale=es-VE
- `roles` — admin_general, director_bu, project_manager, analyst, viewer
- `permissions`, `role_permissions`, `user_roles` (BU-scoped), `teams`, `team_members`

#### Commercial Hierarchy (migration 0004)
- `clients` — 14 seeded: NESTLE, PEPSICO, POLAR, MOVILNET, OREO, FLIPS, etc.
- `brands` — FK client_id, UNIQUE(client_id, code)
- `brand_contacts`, `client_contracts`

#### Campaigns (migration 0006)
- `campaigns` — code CAMP-2026-001, FK client_id, brand_id, objective, status, budget_total
- `campaign_status_history` — trigger `log_campaign_status_change`
- `campaign_influencers` — FK campaign_id, influencer_id, agreed_fee, deliverables JSONB, status
- `campaign_links`, `campaign_documents`

#### Influencers (migration 0005 + 0019 + 0024)
- `influencers` — full_name, primary_tier, primary_handle, content_niches[], languages, **discovery fields**: gender, age_range, lat/lng, audience_demographics, is_discoverable, discovered_at, discovery_query, discovery_confidence
- `influencer_social_accounts` — platform (instagram/tiktok/youtube/x/facebook), handle, is_verified, UNIQUE(platform, handle)
- `influencer_metrics_snapshot` — UNIQUE(influencer, social_account, snapshot_date, source)

#### KPIs & Benchmarks (migration 0007, 0016)
- `kpi_definitions`, `campaign_kpi_values`, `benchmarks`, `insights`, `winning_formats`, `tier_benchmarks`

#### Operations (migration 0008)
- `budgets` → `budget_items`, `tasks`, `forms`, `form_submissions`, `automations`, `automation_logs`

#### AI / RAG (migration 0009, 0023)
- `ai_prompts`, `documents`, `document_chunks` — **vector(384)** pgvector, `match_document_chunks()` SQL function
- `ai_conversations`, `ai_messages` (tokens, cost_usd, latency_ms), `ai_jobs`, `notifications`

#### Analytics / Audit (migration 0010)
- `dashboards`, `widgets`, `scheduled_reports` (cron), `audit_logs`, `integrations` (encrypted JSONB), `webhooks`, `exports`

#### P.I.A.R. Foundation (migration 0015)
- `publicaciones` — per-publication metrics: vistas, alcance, likes, comentarios, er_alcance, er_vistas, retencion, source=SHEETS/API_IG/MANUAL
- `comentarios` — text + classified sentiment

#### Discovery Foundation (migrations 0019–0028, 0091–0098)

| Table | Purpose |
|---|---|
| `discovery_runs` | brief_text, brief_parsed JSONB, status, total_candidates, actual_cost_usd, started_at, completed_at, metadata JSONB |
| `discovery_candidates` | UNIQUE(run_id, platform, handle) — 30+ columns: match_score, niche_relevance, geo_relevance, audience_relevance, content_quality, rationale, tier, is_tienda, audience_demographics, top_countries, top_cities, interests, raw_payload |
| `discovery_conversations` | LangGraph state JSONB, current_step, accumulated_brief, message_count |
| `discovery_messages` | role user/assistant/tool, tool_calls JSONB, tool_results JSONB, reasoning, cost_usd, latency_ms |
| `api_costs` | provider, operation, entity_id, cost_usd, tokens_in/out, occurred_at |
| `integration_credentials` | encrypted with pgcrypto, per provider × business_unit_id |

**Discovery RPC:** `discovery_runs_merge_metadata(p_run_id, p_metadata)` — atomic JSONB merge (migration 0026)

**Discovery RLS:** Enabled on all discovery tables with policies based on `auth.uid()` + `current_user_bu_ids()` (migration 0027)

---

## 6. Integrations

### Active

| Service | File | Status |
|---|---|---|
| **Apify** (Instagram) | `packages/discovery/discovery/tools/apify_client.py` | ✅ Active — 5 actors + Redis cache |
| **DeepSeek-V3** | `packages/shared-ai/shared_ai/deepseek_client.py` | ✅ Active — cache mode enabled |
| **Supabase** | `packages/shared-core/shared_core/supabase_rest.py` | ✅ Active |
| **Redis** (ARQ + cache) | `apps/api/app/workers/worker.py` | ✅ Active |
| **fastembed** `all-MiniLM-L6-v2` | `packages/shared-ai/shared_ai/embeddings.py` | ✅ Active |
| **Prometheus** | `apps/api/app/main.py` | ✅ `/metrics` |
| **Vercel** | `apps/web/vercel.json` | ✅ Deployed |
| **Railway** | `railway.toml` + `Dockerfile` | ✅ API + Worker |

### Implemented but Deferred

| Service | Why Deferred |
|---|---|
| **Meta Graph API v21.0** (`meta_client.py`) | Sprint 2 — 2-6 week approval |
| **TikTok Research API** (`tiktok_client.py`) | Sprint 3 — needs approval |
| **YouTube Data API v3** (`youtube_client.py`) | Sprint 3 |
| **HypeAuditor** | Explicitly skipped — building LWFA in-house |
| **Metricool** (`metricool_client.py`) | ✅ Cron job active, optional |

### Explicitly Skipped

| Tool | Normal Cost | Reason |
|---|---|---|
| HypeAuditor | $99-500/mo | Replaced by proprietary LWFA |
| Metricool | $12-25/mo | Optional post-publish |
| Canva API | $13+/mo | Not needed |
| Intercom | $74+/mo | Built in-house |

---

## 7. Lens — Discovery Engine

### State Machine (Orchestrator)

```
START → BRIEF → REFINING → SEARCHING → RANKING → CANDIDATES_REVIEW → DONE
```

The orchestrator (`packages/discovery/discovery/orchestrator.py`, 598 lines) does NOT call Apify directly. It:
1. Parses brief → `BriefStructured`
2. Confirms with user
3. Sets `pending_discovery: True`
4. API layer enqueues `discovery_run_task` to ARQ Redis

Actual 4-step pipeline runs in `apps/api/app/workers/worker.py`.

### Brief Structured Schema

```python
class BriefStructured(BaseModel):
    product_name: str
    industry: str                           # e.g. "mascotas", "moda", "belleza"
    niches: list[str]                      # e.g. ["mascotas", "perros", "pet_care"]
    platforms: list[Platform]               # [instagram, tiktok]
    audience_gender: AudienceGender         # female/male/all
    audience_age_min: int = 18
    audience_age_max: int = 65
    audience_countries: list[str]          # e.g. ["VE"]
    audience_cities: list[str] = []        # e.g. ["Caracas", "Maracaibo"]
    budget_usd: float = 0
    tone: list[str] = []
    hashtags: list[str] = []               # user-provided or generated
    exclude_handles: list[str] = []        # for "dame otros 15"
```

### Query Builder Defaults (VE/Pet vertical)

**23 Hashtags:**
```
purinaVE, dogchowVE, amorporruno, mascotasVE, perrosVE,
mascotasVenezuela, dogChow, purina, petlovers, doglover,
vzla, venezuela, adopcionvzla, rescateanimalvzla,
mascotasvzla, perrosdevzla, cachorrosVE, perrosVenezuela,
tiendademascotasVE, veterinariaVenezuela, adoptaVE, perritosVE,
amigosde4patasVE, petloversVE
```

**8 Keywords:**
```
PurinaVE, DogChowVE, purina dog chow venezuela,
mascotasVE, perrosVenezuela, amantesdelosperros,
mascotas caracas, perrosvzla
```

---

## 8. Apify Pipeline & LWFA Scoring

### Apify Actors

| Actor | ID | Purpose |
|---|---|---|
| Instagram Hashtag Scraper | `apify~instagram-hashtag-scraper` | Posts by hashtag |
| Instagram Scraper | `apify~instagram-scraper` | General scraping |
| Instagram Search Scraper | `apify~instagram-search-scraper` | User/hashtag search by keyword |
| Instagram Profile Scraper | `apify~instagram-profile-scraper` | Profile enrichment |
| Engagement Analytics | `easyapi~instagram-profile-engagement-analytics` | Advanced engagement metrics |
| TikTok Scraper | `clockworks~tiktok-scraper` | TikTok hashtag search |

### 4-Step Pipeline

```
STEP 1: scrape_hashtags_all_sync()
  → INSTAGRAM_HASHTAG_SCRAPER
  → Cache TTL: 30min (namespaced by run_id)

STEP 2: search_users_by_keywords_sync()
  → INSTAGRAM_SEARCH_SCRAPER
  → Cache TTL: 30min

STEP 3: enrich_profiles_sync() (top 150 handles)
  → INSTAGRAM_PROFILE_SCRAPER
  → Cache TTL: 1h

STEP 4: country_boost() >= 1.0 (VE filter) + composite_score()
  → Dedupe exclude_handles
  → Filter followers >= 1,000
  → Compute ER from latestPosts
  → Score + sort by match_score desc
  → Top 15 → discovery_candidates DB
```

### LWFA Scoring — 4 KPIs

**KPI #1 — ICA (Índice de Conversión Aparentada)**
```python
# 0-100: comments with buy intent / total comments
BUY_INTENT_KEYWORDS = ["precio", "donde", "link", "comprar", "tienda",
  "oferta", "disponible", "envio", "pedido", "orden", "carrito",
  "$", "bs", "bolivares", "coupon", "descuento", "promo", "stock"]
```

**KPI #2 — Geo-Foco Real**
```python
# 0-1: cross-reference geotags + caption language + bio
VE_GEO_INDICATORS = ["caracas", "venezuela", "vzla", "valencia",
  "maracaibo", "san cristobal", "barquisimeto", "merida",
  "puerto la cruz", "la guaira", "catia", "petare",
  "guarenas", "guatire"]
```

**KPI #3 — Engagement Velocity**
```python
# (likes + comments) / posts_count / days_since_first_post
```

**KPI #4 — Business Intent**
```python
# externalUrl(0.4) + facebookPage(0.4) + isBusiness(0.2) + isVerified(0.1)
```

### Scoring Formulas

**Lens formula (currently used by worker.py):**
```
Composite = ER×100 + GEO×30 + Business×20 + Verified×10 + Nicho×25
```

**LWFA formula (canonical in result_ranker.py, NOT currently used):**
```
LWFA = 0.25*ER + 0.18*BI + 0.15*ICA + 0.12*Velocity + 0.12*Geo
     + 0.10*Clips + 0.08*Consistency
```

> ⚠️ **Inconsistency:** These two formulas differ. The worker uses the Lens formula. The canonical LWFA from `result_ranker.py` is not wired up.

### 9-Tier Benchmarks

| Tier | Followers | ER Range |
|---|---|---|
| NANO_BAJO | 500–2K | 8–15% |
| NANO_ALTO | 2K–10K | 6–12% |
| MICRO_BAJO | 10K–30K | 4–10% |
| MICRO_MEDIO | 30K–100K | 3–8% |
| MICRO_ALTO | 100K–500K | 2–6% |
| MID_BAJO | 500K–1M | 1.5–5% |
| MID_ALTO | 1M–5M | 1–4% |
| MACRO_BAJO | 5M–10M | 0.5–2% |
| MACRO_ALTO | 10M+ | 0.3–1% |

### Niche Keyword Groups (15)

```
moda, belleza, fitness, tecnologia, comida, viajes, lifestyle,
mama, negocios, entretenimiento, cafe, deportes, arte, gaming,
mascotas (62 keywords), mascotas_viral, hogar
```

---

## 9. Cost Optimization

### Current Cost Per Campaign

| Step | Free Tier | With Cache |
|---|---|---|
| 1. Keyword search (28 kw × 30) | $1.30 | ~$0.05 |
| 2. Hashtag posts (23 ht × 30) | $1.43 | ~$0.05 |
| 3. Profile enrichment (80 profiles) | $0.21 | ~$0.05 |
| 4. Engagement analytics (20×30 posts) | $0.36 | ~$0.15 |
| **Total** | **$3.30** | **~$0.30** |

### Monthly Projections

| Scenario | Campaigns/mo | Apify | DeepSeek | **Total** |
|---|---|---|---|---|
| No cache | 5 | $16.50 | $2.50 | **$19** |
| With cache | 5 | $1.50 | $2.50 | **$4** |
| Scaled (cache) | 20 | $6.00 | $10.00 | **$16** |
| Scaled (cache) | 50 | $15.00 | $25.00 | **$40** |

**Budget cap:** $250 USD/mo ($200 APIs + $50 infra)

### Active Optimizations

- **Redis cache** with differentiated TTLs (1h profiles, 30min search)
- **run_id-namespaced cache keys** for fresh data per discovery run
- **DeepSeek prompt caching** (`extra_body={"cache": {"mode": "enabled"}}`)
- **`APIFY_SEMAPHORE = asyncio.Semaphore(3)`** concurrency cap
- **`MAX_HANDLES_TO_ENRICH = 150`** cap
- **`TARGET_CANDIDATES = 15`** final cap
- **`_run_sync` timeout 300s** + retry exponential 3 attempts
- **ARQ cron jobs:** `scheduled_reports_cron` (9 AM) + `sync_metricool_task` (2 AM)

---

## 10. UI/UX & Design System

### Current Design Tokens

**Colors (CSS vars in `apps/web/src/index.css`):**

| Token | Light Mode | Dark Mode |
|---|---|---|
| `--primary` | Purple `#a855f7` | Blue `#3b82f6` |
| `--brand-pink` | `#ec4899` | — |
| `--brand-purple` | `#a855f7` | — |
| `--brand-blue` | `#3b82f6` | — |
| `--background` | White | Dark `#0f0f12` |
| `--foreground` | Near-black | Near-white |
| `--surface-0` | `#f4f4f5` (sunken) | — |
| `--surface-1` | White (panel) | — |
| `--surface-2` | `#f4f4f5` (raised) | — |
| `--divider` | `#e4e4e7` | — |
| `--success` | `#22C55E` | — |
| `--warning` | `#F59E0B` | — |

> **Note:** Brand gradient `linear-gradient(135deg, pink → purple → blue)` is marked as "legacy" in CSS. Preferred style is flat with low-alpha colored backgrounds.

### Typography

| Role | Font | Loaded |
|---|---|---|
| Sans | Inter | ✅ via Google Fonts |
| Display | Instrument Serif | ✅ via Google Fonts |
| Display (tailwind) | Montserrat | ❌ Declared in `tailwind.config.js` but NOT imported |

> **Inconsistency:** `tailwind.config.js` references Montserrat as `font-display` but only Instrument Serif is imported. `.font-display` class is defined in CSS but unused in codebase.

### Shadows

| Name | Definition | Usage |
|---|---|---|
| `card` | `0 2px 8px rgba(0,0,0,0.04)` | Default card |
| `card-hover` | `0 4px 16px rgba(0,0,0,0.08)` | Hover state |
| `elevated` | `0 12px 48px rgba(0,0,0,0.12)` | Dialogs, modals |
| `soft` | `0 2px 8px rgba(0,0,0,0.04)` | Legacy |
| `elevated2` | `0 8px 32px rgba(0,0,0,0.08)` | Alternate |
| `glow` | `0 0 24px rgba(168,85,247,0.25)` | Purple glow |

### Radii

| Token | Value | Tailwind key |
|---|---|---|
| `--radius` | `0.75rem` (12px) | `lg` |

### Sidebar

- **Width:** 240px expanded / 64px collapsed
- **Logo:** `logo-laweb.png` (11322×4617 px, 528KB) or `logo-laweb-collapsed.png` (1.18MB)
- **Navigation groups:** Workspace (4 items), Inteligencia (2 items), Footer (1 item)
- **AI badge:** Purple `AI` chip on Influencer Lens item

### Gaps Toward Apple-Grade

1. **No formal design token system** — tokens scattered in CSS vars
2. **Montserrat dead code** — declared but never imported
3. **Gradients marked "legacy"** — no clear preferred direction
4. **Minimal animations** — only `accordion-down/up` defined
5. **Glass/Aurora effects declared but unused**
6. **Sidebar at 240px** — Apple uses ~280px with more whitespace
7. **No polished empty states** for critical flows
8. **No skeleton loaders** for async content
9. **Minimal micro-interactions**
10. **Dark mode has abrupt color swap** (purple → blue on primary)

---

## 11. Tech Debt

### High Priority

| # | Issue | Impact | Effort |
|---|---|---|---|
| 1 | **No tests** — no unit, integration, or CI tests | HIGH — regressions undetected | 4–8h |
| 2 | **Duplicate deps in 2 pyproject.toml** — caused Railway crash | HIGH — production risk | 3–4h |
| 3 | **Orchestrator state in-memory** — lost on worker restart | MED — conversation state lost | 2–3h |
| 4 | **Scoring formula inconsistency** — Lens vs LWFA | MED — incorrect scoring | 2–3h |

### Medium Priority

| # | Issue | Impact | Effort |
|---|---|---|---|
| 5 | **RLS policies incomplete** — INSERT open to all on discovery tables | MED — multi-tenant risk | 2–3h |
| 6 | **Cost tracking not aggregated** by campaign/run_id | LOW — no visibility | 2h |
| 7 | **No feedback loop** — saved/dismissed doesn't improve scoring | MED — quality ceiling | 6–8h |

### Low Priority

| # | Issue | Effort |
|---|---|---|
| 8 | Streaming chat responses | 4h |
| 9 | Background re-rank | 3–4h |
| 10 | Metabase BI dashboard | 4–6h |
| 11 | Sentry alerts | 2h |
| 12 | Prometheus metrics polish | 3–4h |

---

## 12. Roadmap

### Sprint 1 ✅ DONE (Jul 20)
- 4-layer Apify pipeline
- LWFA Scoring
- Gemini keywords (28 in 5 categories)
- **Commits:** ~15 | **Lines added:** +387 net

### Sprint 2 🟡 IN PROGRESS (Target: Jul 28)
- End-to-end Purina Dog Chow demo
- Redis cache layer
- Meta for Developers setup
- Cost dashboard per campaign
- **Fix:** Chat empty after wizard, Redis same-candidates bug, wizard paste/comma issues

### Sprint 3 🔲 BACKLOG (Aug 4)
- TikTok Research API integration
- Outreach automation (Resend email)
- Feedback loop (accept/dismiss → improves scoring)
- Background re-rank of top candidates

### Sprint 4 🔲 BACKLOG (Aug 11)
- Multi-BU / multi-tenant prep
- Metabase BI dashboard
- PWA / mobile

### Observability (any sprint)
- [ ] Grafana + Prometheus metrics
- [ ] Sentry alerts for discovery_run failures
- [ ] Cost tracking per client (multi-tenant)

### Auth + Multi-tenant (Sprint 4)
- [ ] BU filtering on all endpoints
- [ ] Rate limits per BU
- [ ] Per-BU config (keywords, hashtags)

---

## 13. Known Issues & Inconsistencies

### ⚠️ Critical

1. **Scoring formula mismatch** — `worker.py` uses Lens formula; `result_ranker.py` has different LWFA canonical formula. Unify.

2. **Orchestrator state in-memory** — `DiscoveryOrchestrator.state` dict is lost on worker restart.

3. **Cache key race condition** — `_build_cache_key` uses `run_id` salt for fresh data, but same brief across runs still hits cache if run_id not passed.

### ⚡ Medium

4. **Montserrat dead code** — `tailwind.config.js` declares `font-display: Montserrat` but it's never imported. Instrument Serif is imported and `.font-display` is defined in CSS but unused.

5. **Duplicate color declarations** — `success`, `warning`, `info` declared twice in Tailwind config (HSL vars then hex overrides). Hex wins.

6. **Gradient marked "legacy"** — `bg-gradient-brand` explicitly labeled "no longer preferred" but no alternative established.

7. **RLS INSERT open** — discovery tables INSERT policies allow all authenticated users (not BU-filtered).

8. **`exclude_handles` added but Apify client not wired** — feature in schema + orchestrator but not passed to Apify calls.

### ℹ️ Low

9. **No dedicated design-system file** — design tokens in `index.css` + `tailwind.config.js` only.

10. **Dark mode abrupt** — primary switches purple→blue with no transition.

11. **Instrument Serif unused** — declared in CSS but `.font-display` class never used in source.

12. **Cities comma input bug** — trailing comma disappears on re-render in `BriefWizard.tsx`.

---

*Document generated: 2026-07-30*
*Maintained by: La Web Figital Agency*
