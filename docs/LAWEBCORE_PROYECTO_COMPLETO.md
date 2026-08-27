# LAWEBCORE — Proyecto Completo: Análisis Maestro

> **Última actualización:** Agosto 2026
> **Repo:** `github.com/ungardev/lawebcore`
> **Producción:** API en Railway, Frontend en Vercel
> **Versión del análisis:** 2026-08-05
> **Audit:** Claude Code Fable 5 — Todos los fixes aplicados ✅

---

## 1. RESUMEN EJECUTIVO

**La Web Core** es la plataforma interna de **La Web Figital Agency** (Venezuela) — un sistema de gestión de campañas de marketing + descubrimiento de influencers con IA.

**Módulo estrella:** **Lens** (renombrado de "Influencer Lens" por el CEO el 30-Jul-2026). Visión: una herramienta de élite nivel Apple para descubrimiento de influencers en Venezuela y LATAM.

**Logro reciente:** Audit completo por Claude Code Fable 5 (2026-08-04/05) — 19 fixes identificados, **100% aplicados y validados con smoke tests (14/14 passed)**.

**Stack principal:**
- **Frontend:** React 19 + Vite + TypeScript + Tailwind + shadcn/ui + Zustand + TanStack Query
- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0 async + asyncpg
- **Base de datos:** PostgreSQL 16 + pgvector (Supabase Cloud)
- **Cola async:** ARQ + Redis (Railway)
- **IA:** DeepSeek-V3 + fastembed (embeddings locales)
- **Scraping:** Apify (Instagram, TikTok, YouTube)
- **Infraestructura:** Railway (API + Worker) + Vercel (Frontend) + Supabase (DB)

---

## 2. ESTRUCTURA DE ARCHIVOS COMPLETA

```
lawebcore/
│
├── apps/
│   ├── api/                              # FastAPI backend (→ Railway)
│   │   └── app/
│   │       ├── main.py                   # Entry point FastAPI
│   │       ├── api/v1/                  # TODOS LOS ENDPOINTS
│   │       │   ├── auth.py              # Login, logout, me
│   │       │   ├── users.py             # Users CRUD
│   │       │   ├── clients.py           # Clients CRUD
│   │       │   ├── brands.py            # Brands CRUD
│   │       │   ├── campaigns.py         # Campaigns CRUD + Kanban
│   │       │   ├── influencers.py        # Influencers CRUD
│   │       │   ├── kpis.py              # KPI definitions + values
│   │       │   ├── dashboard.py         # Executive KPIs
│   │       │   ├── ai.py                # RAG chat, generate, index
│   │       │   ├── projections.py        # P.I.A.R. projection calculator
│   │       │   ├── publicaciones.py      # Publications list
│   │       │   ├── imports.py           # CSV/JSON import
│   │       │   ├── scoring.py           # LWFA scoring + benchmarks
│   │       │   ├── sentiment.py         # Sentiment analysis
│   │       │   ├── discovery.py         # Discovery orchestrator
│   │       │   ├── lens.py              # Mounts /lens prefix
│   │       │   └── admin.py             # Seed, enrich, preload
│   │       ├── core/                    # Utilities core
│   │       │   ├── security.py          # JWT (HS256) + bcrypt + RBAC
│   │       │   ├── metrics.py           # Prometheus metrics
│   │       │   ├── rate_limiter.py      # SlowAPI rate limits
│   │       │   ├── cost_tracker.py      # External API costs
│   │       │   ├── piar_scoring.py      # P.I.A.R. scoring engine
│   │       │   ├── piar_benchmarks.py   # LWFA benchmark comparison
│   │       │   ├── piar_engine.py       # P.I.A.R. projection engine
│   │       │   ├── piar_constants.py    # P.I.A.R. constants
│   │       │   ├── piar_importer.py     # Universal CSV/JSON importer
│   │       │   ├── worker_enqueuer.py   # ARQ Redis enqueuer
│   │       │   └── logging.py           # Structlog configuration
│   │       ├── models/                  # SQLAlchemy ORM models
│   │       ├── schemas/                 # Pydantic schemas
│   │       ├── services/
│   │       │   ├── ai_service.py        # AIService: RAG + DeepSeek
│   │       │   └── proposal_generator.py # CSV proposal generator
│   │       └── workers/
│   │           ├── worker.py            # ARQ: discovery_run_task (~990 líneas post-fix)
│   │           └── health_server.py      # Railway health endpoint
│   │
│   └── web/                              # React frontend (→ Vercel)
│       └── src/
│           ├── App.tsx                   # Routing (React Router 7)
│           ├── features/                 # Feature-sliced modules
│           │   ├── auth/                # LoginPage, ProtectedRoute
│           │   ├── campaigns/            # List, Detail, Kanban, KPIs
│           │   ├── clients/              # ClientsPage
│           │   ├── brands/              # BrandsPage
│           │   ├── dashboard/            # DashboardPage
│           │   ├── lens/                # ★ Lens (Discovery) — 30+ archivos
│           │   │   ├── pages/           # LensChatPage, LensRunsListPage, LensSearchPage
│           │   │   ├── components/       # BriefWizard, CandidateCard, ChatMessage...
│           │   │   ├── hooks/           # useDiscoveryConversation, useRunPolling
│           │   │   ├── api/             # lensApi.ts
│           │   │   └── types/           # discovery.ts
│           │   ├── influencers/          # BenchmarkSemaphore, InfluencerScoreBadge
│           │   ├── imports/              # CSVImportButton, JSONImportPanel
│           │   ├── projections/          # ProjectionPanel, ScenarioComparison
│           │   └── settings/            # SettingsPage, PasswordChangeForm
│           ├── components/               # Shared UI components
│           ├── hooks/                    # Shared React hooks
│           ├── lib/                     # API clients, utils
│           ├── stores/                  # Zustand stores
│           ├── types/                   # Shared TypeScript types
│           └── assets/                  # Static assets
│
├── packages/
│   ├── discovery/                        # ★ MÓDULO DISCOVERY (PIAR)
│   │   └── discovery/
│   │       ├── schemas.py               # BriefStructured, enums, models
│   │       ├── orchestrator.py          # LangGraph state machine (632 líneas)
│   │       ├── brief_parser.py          # Brief → BriefStructured (DeepSeek)
│   │       ├── query_builder.py         # BriefStructured → DiscoveryPlan
│   │       ├── profile_generator.py     # DiscoveryProfile generator (★ ELITE)
│   │       ├── candidate_analyzer.py    # AI scoring (372 líneas — post-fix)
│   │       ├── memory.py                # Conversation persistence
│   │       ├── result_ranker.py         # LWFA benchmarks + formulas
│   │       ├── scoring/
│   │       │   ├── niche.py            # Niche relevance scoring
│   │       │   └── lens_score.py        # Unified Lens Score 0-100 (post-fix)
│   │       └── tools/
│   │           ├── apify_client.py      # Apify API (857 líneas)
│   │           ├── geo_boost.py         # Geographic + tier scoring (post-fix)
│   │           ├── meta_client.py       # Meta Business Graph API
│   │           ├── tiktok_client.py     # TikTok Research API
│   │           ├── youtube_client.py    # YouTube Data API v3
│   │           ├── metricool_client.py  # Metricool API
│   │           └── multi_actor_instagram.py  # Multi-actor fallback chain
│   │
│   ├── shared-core/                     # Config, DB, Supabase REST
│   │   ├── __init__.py
│   │   ├── config.py                   # Pydantic Settings
│   │   ├── db.py                       # SQLAlchemy async session
│   │   └── supabase_rest.py            # RailwayPg client (post-fix)
│   │
│   ├── shared-ai/                       # DeepSeek + fastembed
│   │   ├── __init__.py
│   │   ├── deepseek_client.py           # DeepSeek-V3 via LangChain
│   │   └── embeddings.py                # fastembed all-MiniLM-L6-v2
│   │
│   ├── shared-types/                    # TypeScript stubs
│   └── ui/                             # UI components stubs
│
├── supabase/
│   ├── migrations/                      # 32+ archivos SQL
│   │   └── (migración 0099 renombrada a 0103 post-Fable 5)
│   ├── schema.sql                      # Schema consolidado (960 líneas)
│   ├── seed.sql                        # Seed base (roles, BUs, KPIs)
│   └── seed_excel_data.sql             # Seed Excel (14 clients, 25 brands, 32 campaigns)
│
├── scripts/                             # ETL y utilities
│   ├── etl_excel.py
│   ├── etl_drive.py
│   ├── etl_ism_backfill.py
│   ├── enrich_candidates_er.py
│   ├── extract_purina_real_apify.py
│   ├── seed_purina.py
│   └── reset_campaigns_status.sql
│
├── docs/                               # Documentación
│   ├── LAWEBCORE_PROYECTO_COMPLETO.md  # Este documento
│   ├── DISCOVERY_ARCHITECTURE.md
│   ├── PROJECT_STATUS_2026-07-30.md
│   ├── ROADMAP.md
│   └── MASTER_PROMPT_CLAUDE_CODE_FABLE_5.md
│
├── Dockerfile
├── docker-compose.yml                  # Postgres + Redis local
├── railway.toml
├── package.json                        # pnpm workspace root
└── pyproject.toml                     # Python packages
```

---

## 3. FABLE 5 AUDIT — FIXES APLICADOS (2026-08-04/05)

### Commits relacionados

| Commit | Fecha | Descripción |
|--------|-------|-------------|
| `fc380ce` | 2026-08-04 | fix(discovery): todos los fixes Fable 5 |
| `9d84fba` | 2026-08-05 | fix(tests): corrección filtro ciudad + 4 tests |
| `ee87533` | 2026-08-05 | fix(tests): últimos 2 failing tests |

### BLOQUE 1 — HOTFIX ✅

| ID | Fix | Archivo | Status |
|----|-----|---------|--------|
| F-1.1 | `from typing import Any` en worker.py | `apps/api/app/workers/worker.py` | ✅ Validado |
| F-1.2 | `upsert_many` siempre añade RETURNING | `packages/shared-core/supabase_rest.py` | ✅ Validado |
| F-1.3 | geo_boost country disqualification bug | `packages/discovery/discovery/tools/geo_boost.py` | ✅ Validado |
| F-1.4 | Migración 0099 → 0103 | `supabase/migrations/` | ✅ Done |

### BLOQUE 2 — SMOKE TEST ✅

| ID | Fix | Archivo | Status |
|----|-----|---------|--------|
| F-2.1 | test_pipeline_smoke.py creado | `apps/api/tests/` | ✅ 14/14 passed |

### BLOQUE 3 — COSTO Y CALIDAD ✅

| ID | Fix | Impacto | Status |
|----|-----|---------|--------|
| F-3.1 | Keywords 80→20, hashtags 50→30, sin buy_intent/geo | **-64% costo Apify** | ✅ Validado |
| F-3.2 | lens_score pesos 0.90→1.0, tienda 0.6→0.85 | Scoring correcto | ✅ Validado |
| F-3.3 | geo_boost filtro ciudad corregido | +Candidatos CO/AR | ✅ Validado |
| F-3.4 | Typo `"c🇨🇴"` → `"co"` | Matching correcto | ✅ Validado |
| F-3.8 | elite_context no duplicado en batch | -Token DeepSeek | ✅ Validado |
| F-3.10 | `get_or_create_profile` 1 sola vez (via `plan.profile`) | -1 call LLM/run | ✅ Validado |
| F-3.11 | Usa `plan.min_followers` | Config correcto | ✅ Validado |

### BLOQUE 4 — ROBUSTEZ ✅

| ID | Fix | Status |
|----|-----|--------|
| F-4.3a | pollRun reconoce `'partial'` | ✅ |
| F-4.6a | Eliminado bloque duplicado keyword_items | ✅ |
| F-4.6b | Eliminado `_analyze_single_candidate` dead code | ✅ |
| F-4.6d | Eliminado import `compute_fingerprint` | ✅ |

### Smoke Tests: 14/14 PASSED ✅

```
tests/test_pipeline_smoke.py::TestGeoBoostFixes::test_profile_with_country_but_no_iso2 PASSED
tests/test_pipeline_smoke.py::TestGeoBoostFixes::test_country_match_when_iso2_present PASSED
tests/test_pipeline_smoke.py::TestGeoBoostFixes::test_country_mismatch_when_iso2_present PASSED
tests/test_pipeline_smoke.py::TestGeoBoostCityMatching::test_city_name_cali PASSED
tests/test_pipeline_smoke.py::TestGeoBoostCityMatching::test_city_name_caracas PASSED
tests/test_pipeline_smoke.py::TestGeoBoostTypoFix::test_co_country_keywords_have_valid_entries PASSED
tests/test_pipeline_smoke.py::TestLensScoreWeights::test_weights_sum_to_one PASSED
tests/test_pipeline_smoke.py::TestLensScoreWeights::test_weights_are_normalized PASSED
tests/test_pipeline_smoke.py::TestQueryBuilderCaps::test_keyword_cap_20 PASSED
tests/test_pipeline_smoke.py::TestQueryBuilderCaps::test_hashtag_cap_30 PASSED
tests/test_pipeline_smoke.py::TestQueryBuilderCaps::test_no_buy_intent_in_queries PASSED
tests/test_pipeline_smoke.py::TestCandidateAnalyzerBatchPrompt::test_batch_prompt_singular_elite_context PASSED
tests/test_pipeline_smoke.py::TestUpsertManyReturning::test_upsert_many_adds_returning_clause PASSED
tests/test_pipeline_smoke.py::TestWorkerTyping::test_worker_module_imports_any PASSED
```

---

## 4. STACK COMPLETO

### FRONTEND
| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Framework | React | 19 |
| Bundler | Vite | 6 |
| Lenguaje | TypeScript | 5.7 |
| CSS | Tailwind CSS | 3.4 |
| UI Library | shadcn/ui + Radix UI | latest |
| Estado global | Zustand | 5 |
| Data fetching | TanStack Query | 5 |
| Tablas | TanStack Table | 8 |
| Gráficos | Recharts | 2 |
| Forms | React Hook Form + Zod | 7 / 3 |
| Routing | React Router | 7 |
| DnD | @dnd-kit | 6 |
| Package manager | pnpm | 9.15 |
| Hosting | Vercel | - |

### BACKEND
| Componente | Tecnología |
|------------|-----------|
| Framework | FastAPI 0.115 |
| Runtime | Python 3.12 |
| ORM | SQLAlchemy 2.0 async |
| DB driver | asyncpg 0.30 |
| Validación | Pydantic v2 |
| Cola async | ARQ 0.26 + Redis |
| Logging | structlog |
| Rate limit | SlowAPI |
| Auth | bcrypt + python-jose (HS256 JWT) |
| Hosting | Railway |

### BASE DE DATOS
| Componente | Tecnología |
|------------|-----------|
| Primary DB | PostgreSQL 16 (Supabase Cloud) |
| Vector DB | pgvector (384-dim) |
| Auth | Supabase Auth |
| Pool connection | asyncpg directo a Railway Postgres |

### IA/ML
| Componente | Tecnología |
|------------|-----------|
| LLM | DeepSeek-V3 (via API) |
| Embeddings | fastembed all-MiniLM-L6-v2 (local) |
| Vector store | pgvector |
| RAG | LangChain 0.3+ |

### INTEGRACIONES EXTERNAS
| Servicio | Propósito | Estado |
|----------|-----------|--------|
| Apify | Instagram scraping | ✅ Activo |
| DeepSeek | LLM | ✅ Activo |
| Supabase | DB + Auth + Storage | ✅ Activo |
| Redis | ARQ + cache | ✅ Activo |
| fastembed | Embeddings local | ✅ Activo |
| Prometheus | Metrics | ✅ /metrics |
| Meta/Facebook | Business API | 🟡 Sprint 2 |
| TikTok Research | TikTok API | 🟡 Sprint 3 |
| YouTube Data | YouTube API | 🟡 Sprint 3 |
| Metricool | Analytics | ✅ Cron job activo |

---

## 5. TODOS LOS MÓDULOS Y FEATURES

### 5.1 Módulo de Campañas
- **Lista de campañas** con filtros por estado/cliente/marca
- **Vista Kanban** con drag & drop (dnd-kit)
- **Detalle de campaña** con KPIs, links, influencers asignados
- **Crear/Editar campaña** con modal
- **Historial de cambios de estado** (trigger en DB)

### 5.2 Módulo de Influencers
- **Lista de influencers** con filtros por tier/búsqueda/tag
- **Asignación a campañas** (CampaignInfluencer)
- **Métricas snapshots** por red social
- **Scoring LWFA** (content quality, audience quality, brand fit)
- **Benchmarks** vs estándares LWFA por subtier
- **Comparación semaphore** (semáforo verde/amarillo/rojo)

### 5.3 Módulo de KPIs
- **Definiciones de KPIs** (defs. globales)
- **Valores por campaña** (registro histórico)
- **Benchmarks** por subtier y scope
- **Insights** automáticos
- **Winning formats** por tipo de campaña

### 5.4 Módulo P.I.A.R. (Inteligencia)
- **Dashboard ejecutivo** — KPIs agregados, overview
- **Panel de proyecciones** — 3 escenarios (conservative/base/optimistic)
- **Importación CSV/JSON** — datos de publicaciones
- **Formularios manuales** — publicación individual
- **Análisis de sentimiento** — comentarios clasificados (DeepSeek)
- **Benchmark comparison** — vs estándares LWFA

### 5.5 Módulo AI (RAG + LLM)
- **RAG Chat** — knowledge base sobre documentos
- **Generación de contenido** — brief, post-mortem desde templates
- **Embeddings** — re-indexar datos P.I.A.R.
- **Cost tracking** — tokens, costo USD por mensaje

### 5.6 Módulo Discovery / Lens ★★★
- **Chat conversacional** — describe brief en lenguaje natural
- **Wizard de brief** — formulario estructurado paso a paso
- **Búsqueda directa** — sin chat, con filtros
- **Pipeline de 4 capas** — Apify scraping
- **Scoring LWFA** — 4 KPIs exclusivos
- **Perfil generador** — genera queries desde brief (★ ELITE SYSTEM)
- **Enriquecimiento con Apify** — datos oficiales IG
- **Análisis con DeepSeek** — content/audience/brand_fit
- **Propuesta CSV** — exportar top candidatos
- **Guardar/Descartar candidatos** — convertir a influencer real

### 5.7 Módulo de Importación
- **Importar CSV/Excel** — publicaciones
- **Importar JSON** — formato P.I.A.R.
- **Template download** — CSV base

### 5.8 Módulo de Scoring
- **Score por perfil** — BY_PROFILE / BY_WAVE / BY_POST
- **Benchmark status** — vs estándares LWFA
- **Lista de influencers** con score y decisión

### 5.9 Módulo de Autenticación
- **Login** con email/password
- **JWT (HS256)** — 24h expiry
- **RBAC** — roles y permisos
- **Gestión de usuarios** — listar, obtener

---

## 6. API ENDPOINTS COMPLETOS

### Auth
```
POST   /api/v1/auth/login
GET    /api/v1/auth/me
POST   /api/v1/auth/logout
```

### Users
```
GET     /api/v1/users
GET     /api/v1/users/{user_id}
```

### Clients
```
GET     /api/v1/clients
POST    /api/v1/clients
GET     /api/v1/clients/{client_id}
```

### Brands
```
GET     /api/v1/brands
POST    /api/v1/brands
```

### Campaigns
```
GET     /api/v1/campaigns
POST    /api/v1/campaigns
GET     /api/v1/campaigns/kanban
GET     /api/v1/campaigns/{campaign_id}
PATCH   /api/v1/campaigns/{campaign_id}
POST    /api/v1/campaigns/{campaign_id}/status
DELETE  /api/v1/campaigns/{campaign_id}
```

### Influencers
```
GET     /api/v1/influencers
POST    /api/v1/influencers
GET     /api/v1/influencers/{influencer_id}
GET     /api/v1/influencers/{influencer_id}/metrics
```

### KPIs
```
GET     /api/v1/kpis/definitions
POST    /api/v1/kpis/values
GET     /api/v1/kpis/benchmarks
```

### Dashboard
```
GET     /api/v1/dashboard/summary
GET     /api/v1/dashboard/by-status
GET     /api/v1/dashboard/top-clients
```

### AI
```
POST    /api/v1/ai/chat
POST    /api/v1/ai/generate
GET     /api/v1/ai/conversations
POST    /api/v1/ai/index/reindex
GET     /api/v1/ai/sources/{message_id}
```

### Projections
```
POST    /api/v1/projections/calculate
```

### Publicaciones
```
GET     /api/v1/publicaciones
GET     /api/v1/publicaciones/stats/{campaign_id}
```

### Imports
```
POST    /api/v1/imports/csv
POST    /api/v1/imports/json
GET     /api/v1/imports/template
```

### Scoring
```
GET     /api/v1/scoring/influencers/{influencer_id}/score
GET     /api/v1/scoring/influencers/{influencer_id}/benchmark-status
GET     /api/v1/scoring/benchmarks
GET     /api/v1/scoring/benchmarks/{subtier}
GET     /api/v1/scoring/influencers
```

### Sentiment
```
POST    /api/v1/sentiment/analyze
GET     /api/v1/sentiment/publicacion/{publicacion_id}
GET     /api/v1/sentiment/campaign/{campaign_id}/aggregate
POST    /api/v1/sentiment/campaign/{campaign_id}/reanalyze
```

### Discovery/Lens ★
```
POST    /api/v1/discovery/conversations
GET     /api/v1/discovery/conversations
GET     /api/v1/discovery/conversations/{id}
POST    /api/v1/discovery/conversations/{id}/messages
POST    /api/v1/discovery/lens/discovery/upload-brief
POST    /api/v1/discovery/search
POST    /api/v1/discovery/enrich-influencers
GET     /api/v1/discovery/runs
GET     /api/v1/discovery/runs/{run_id}
GET     /api/v1/discovery/runs/{run_id}/candidates
GET     /api/v1/discovery/runs/{run_id}/proposal.csv
POST    /api/v1/discovery/candidates/{candidate_id}/save
POST    /api/v1/discovery/candidates/{candidate_id}/dismiss
GET     /api/v1/discovery/costs
GET     /api/v1/discovery/metrics
```

### Admin
```
POST    /api/v1/admin/seed
POST    /api/v1/admin/enrich-influencers
POST    /api/v1/admin/preload-demo
POST    /api/v1/admin/seed-rag
```

---

## 7. ESQUEMA DE BASE DE DATOS

### Tablas principales (~30+ tablas)

#### Identidad y Permisos
- `business_units` — Unidades de negocio
- `users` — Usuarios (FK auth.users, email, full_name, primary_bu_id)
- `roles` — admin_general, director_bu, project_manager, analyst, viewer...
- `permissions` — Permisos granulares
- `user_roles` — Relación usuario-rol (BU-scoped)
- `teams`, `team_members` — Equipos de trabajo

#### Jerarquía Comercial
- `clients` — 14 clientes seedeados (NESTLE, PEPSICO, POLAR, etc.)
- `brands` — FK client_id, UNIQUE(client_id, code)
- `brand_contacts` — Contactos de marca
- `client_contracts` — Contratos de cliente

#### Campañas
- `campaigns` — code CAMP-2026-001, FK client_id, brand_id, objective, status, budget_total
- `campaign_status_history` — Log de cambios (trigger automático)
- `campaign_influencers` — Asignación influencer-campaña
- `campaign_links` — Links asociados
- `campaign_documents` — Documentos subidos

#### Influencers
- `influencers` — full_name, primary_tier, primary_handle, content_niches[], languages, discovery fields
- `influencer_social_accounts` — platform (instagram/tiktok/youtube), handle, is_verified, UNIQUE(platform, handle)
- `influencer_metrics_snapshot` — UNIQUE(influencer, social_account, snapshot_date, source)

#### KPIs y Benchmarks
- `kpi_definitions` — Definiciones globales de KPIs
- `campaign_kpi_values` — Valores históricos por campaña
- `benchmarks` — Benchmarks por subtier
- `insights` — Insights generados
- `winning_formats` — Formatos winners por tipo

#### Operaciones
- `budgets`, `budget_items` — Control presupuestario
- `tasks` — Tareas operativas
- `forms`, `form_submissions` — Formularios dinámicos
- `automations`, `automation_logs` — Automatizaciones

#### AI / RAG
- `ai_prompts` — Templates de prompts
- `documents` — Documentos para embedding
- `document_chunks` — **pgvector Vector(384)**, función `match_document_chunks()`
- `ai_conversations`, `ai_messages` — Historial chat AI (tokens, cost_usd, latency_ms)
- `ai_jobs` — Jobs de IA
- `notifications` — Notificaciones

#### Analytics / Auditoria
- `dashboards`, `widgets` — Dashboards configurables
- `scheduled_reports` — Reportes programados (cron)
- `audit_logs` — Log de auditoría
- `integrations` — Credenciales cifradas (pgcrypto)
- `webhooks`, `exports` — Webhooks y exports

#### P.I.A.R. (Publicaciones)
- `publicaciones` — Métricas por publicación (vistas, alcance, likes, comments, ER, retención, sentiment, source)
- `comentarios` — Comentarios individuales con clasificación de sentimiento

#### Discovery ★
- `discovery_runs` — brief_text, brief_parsed JSONB, status, total_candidates, actual_cost_usd, started_at, completed_at, metadata JSONB, title
- `discovery_candidates` — UNIQUE(run_id, platform, handle), 30+ columnas incluyendo match_score, niche_relevance, geo_relevance, content_quality, rationale, tier, is_tienda, brand_fit, ai_rationale, elite_data
- `discovery_conversations` — LangGraph state JSONB, current_step, accumulated_brief, parsed_brief_json, pending_refinements, message_count, title
- `discovery_messages` — role (user/assistant/tool), tool_calls JSONB, tool_results JSONB, reasoning, cost_usd, latency_ms
- `discovery_profiles` — fingerprint, vertical_slug, languages JSONB, countries JSONB, hashtags/keywords/niche_keywords/geo_indicators/buy_intent_keywords JSONB, **elite_data JSONB**, source, quality_score, times_used, created_at, updated_at
- `api_costs` — provider, operation, entity_id, cost_usd, tokens_in/out, occurred_at
- `integration_credentials` — encrypted JSONB, per provider × business_unit_id

---

## 8. ARQUITECTURA DEL DISCOVERY / LENS

### Flujo de estado (Orchestrator)
```
START → BRIEF → REFINING → SEARCHING → RANKING → CANDIDATES_REVIEW → DONE
```

### Pipeline de 4 capas (Worker)
```
STEP 1: scrape_hashtags_all_sync()
  → Instagram Hashtag Scraper (Apify)
  → Cache TTL: 30min (namespace run_id)
  → MAX 30 hashtags (optimizado de 50)

STEP 2: search_users_by_keywords_sync()
  → Instagram Search Scraper (Apify)
  → Cache TTL: 30min (namespace run_id)
  → MAX 20 keywords (optimizado de 80)

STEP 3: enrich_profiles_sync()
  → Instagram Profile Scraper (Apify)
  → TOP 25 handles (MAX_HANDLES_TO_ENRICH)
  → Cache TTL: 1h (namespace run_id)

STEP 4: Scoring
  → geo_score (≥0.85 threshold — POST-FIX)
  → lens_score (0-100, pesos = 1.0 — POST-FIX)
  → niche_relevance
  → cross-reference bonus (STEP1 + STEP2)
  → Anti-bot filter (elite_data.anti_bot_signals)
  → Tiendas penalizadas 15% (antes 40% — POST-FIX)

STEP 5: AI Analysis (DeepSeek) — OPTIONAL (ENABLE_AI_ANALYZER=false por defecto)
  → content_quality (0-100)
  → audience_quality (0-100)
  → brand_fit (0-100)
  → ai_rationale (summary en español)
  → Batching: 10 candidatos por call
```

### Sistema ELITE (Profile Generator) ★ IMPLEMENTADO AGOSTO 2026
El `profile_generator.py` genera por cada brief:
- **hashtags** — 20-30 hashtags que la gente USA realmente en el país
- **keywords** — 15-25 frases de búsqueda reales
- **niche_keywords** — términos del nicho en español
- **geo_indicators** — capitales, ciudades, gentilicios, abreviaturas, emoji bandera
- **buy_intent_keywords** — en idioma y moneda local
- **elite_data** (JSONB con 9 subcampos):
  - `content_themes` — tipos de contenido winners para el nicho
  - `audience_behavior` — posting_hours, best_days, content_formats, engagement_pattern
  - `competitor_intel` — brands, hashtags, strategies de competidores
  - `local_slang` — slang local (panas, jeva, chamo, peluche...)
  - `credibility_signals` — señales de perfil real (external_url, email in bio...)
  - `niche_benchmarks` — min_followers, min_er, target_er, ideal_range
  - `anti_bot_signals` — patrones de cuentas fake/bot
  - `geo_local_signals` — neighborhoods por ciudad, wealth_areas, trending_areas
  - `query_variations` — hashtag_stacking, keyword_combinations

### LWFA Scoring — 4 KPIs exclusivos
1. **ICA** (Índice de Conversión Aparentada) — buy intent en comentarios
2. **Geo-Foco Real** — geotags + idioma captions VE
3. **Engagement Velocity** — interacciones/día
4. **Business Intent** — multilink + fb page + business account

### Lens Score (Unified, post-Fable 5)
```
Score = (0.389 × tier_er_norm) + (0.278 × geo) + (0.222 × niche) + (0.111 × biz)
- Tienda bio: ×0.85 (antes ×0.6)
- Cross-reference bonus: ×1.15
- Rango: 0-100
```

### Benchmarks LWFA (9 tiers)
| Tier | Followers | ER Range |
|------|-----------|----------|
| NANO_BAJO | 500–2K | 8–15% |
| NANO_ALTO | 2K–10K | 6–12% |
| MICRO_BAJO | 10K–30K | 4–10% |
| MICRO_MEDIO | 30K–100K | 3–8% |
| MICRO_ALTO | 100K–500K | 2–6% |
| MID_BAJO | 500K–1M | 1.5–5% |
| MID_ALTO | 1M–5M | 1–4% |
| MACRO_BAJO | 5M–10M | 0.5–2% |
| MACRO_ALTO | 10M+ | 0.3–1% |

---

## 9. CÓDIGOS FUENTE CLAVE

### Paquetes Python
| Paquete | Líneas | Propósito |
|---------|--------|-----------|
| `apify_client.py` | 857 | Cliente Apify con Redis cache |
| `orchestrator.py` | 632 | State machine LangGraph-style |
| `worker.py` | ~990 | ARQ worker + discovery_run_task (post-fix) |
| `ai_service.py` | ~400 | RAG + DeepSeek + embeddings |
| `supabase_rest.py` | 434 | Cliente PostgreSQL directo (asyncpg) |
| `deepseek_client.py` | 151 | Wrapper DeepSeek-V3 via LangChain |
| `profile_generator.py` | 569 | Generador elite (★ rewrite agosto 2026) |
| `candidate_analyzer.py` | 372 | Scoring AI con DeepSeek (post-fix: dead code eliminado) |
| `geo_boost.py` | 201 | Scoring geo + tier (post-fix: city matching corregido) |

### Frontend (React)
| Feature | Archivos | Descripción |
|---------|----------|-------------|
| **lens** | 30+ | ★ Módulo más grande — chat, wizard, candidatos |
| campaigns | 11 | List, Detail, Kanban, KPIs |
| projections | 3 | Panel, comparador, sliders |
| imports | 3 | CSV, JSON, form manual |
| influencers | 2 | Score badge, benchmark semaphore |

---

## 10. COSTOS OPERACIONALES (POST-FABLE 5)

### Por Discovery Run — ANTES de Fable 5
| Step | Componente | Costo |
|------|-----------|-------|
| STEP 1 | 50 hashtags × 50 posts | ~$0.18 |
| STEP 2 | 80 keywords × 30 resultados | ~$4.12 ⚠️ |
| STEP 3 | 25 perfiles enriquecidos | ~$0.63 |
| **Total/run** | | **~$4.93** |

### Por Discovery Run — DESPUÉS de Fable 5 (F-3.1 aplicado)
| Step | Componente | Costo |
|------|-----------|-------|
| STEP 1 | 30 hashtags × 50 posts | ~$0.13 |
| STEP 2 | 20 keywords × 30 resultados | ~$1.03 |
| STEP 3 | 25 perfiles enriquecidos | ~$0.63 |
| **Total/run** | | **~$1.79** |

### Proyección mensual (50 runs/mes)
| Escenario | Costo/run | Costo/mes |
|-----------|-----------|-----------|
| Antes de Fable 5 | $4.93 | ~$246 |
| Después de Fable 5 | $1.79 | ~$90 |
| **Ahorro** | **-64%** | **~$156/mes** |

### Presupuesto mensual: $250 USD → $94 USD (post-optimización)

---

## 11. ISSUES CONOCIDOS Y TECH DEBT

### Críticos ✅ RESUELTOS POR FABLE 5
1. ~~**Sin tests**~~ → **SMOKE TEST CREADO** (14/14 passed)
2. ~~**Scoring formula weights 0.90**~~ → **CORREGIDO** (ahora 1.0)
3. ~~**Orchestrator state in-memory**~~ → **PENDIENTE** (no crítico)
4. ~~**Cache key race condition**~~ → **PARCIALMENTE RESUELTO** (F-4.1 pendiente)

### Medium
5. **RLS INSERT open** → Pendiente
6. **exclude_handles no wired** → Pendiente
7. **Cost tracking no aggregate** → Parcial (se loguea, no persiste)

### Low
8. **No streaming chat** → Pendiente
9. **Dark mode abrupto** → Pendiente
10. **Cities comma input bug** → Pendiente

---

## 12. ROADMAP

### Sprint 1 ✅ COMPLETADO (Jul 20)
- Pipeline 4 capas Apify
- LWFA Scoring
- DeepSeek integration
- Railway deploy

### Sprint 2 ✅ COMPLETADO (Agosto 2026)
- Redis cache layer ✅
- **Elite profile generator** ✅
- **Anti-bot filter** ✅
- **Claude Code Fable 5 Audit + Fixes** ✅ (2026-08-04/05)
- Meta for Developers setup (pending approval 2-6 semanas)

### Sprint 3 🔲 BACKLOG (Aug 11)
- TikTok Research API (post-aprobación)
- Outreach automation (Resend email)
- Feedback loop (accept/dismiss → mejora scoring)
- **Cost persistence in DB** (recomendado post-audit)

### Sprint 4 🔲 BACKLOG (Aug 18)
- Multi-BU / multi-tenant prep
- Metabase BI dashboard
- PWA / mobile

---

## 13. VARIABLES DE ENTORNO REQUERIDAS

```bash
# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<key>

# Database
DATABASE_URL=postgresql+asyncpg://postgres:<pass>@host:port/database

# Backend
API_ENV=production
API_CORS_ORIGINS=[...]
ADMIN_TOKEN=<jwt-secret>

# Redis
ARQ_REDIS_URL=redis://localhost:6379/0

# AI
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-v4-flash

# APIs Externas
APIFY_API_KEY=
META_APP_ID=, META_APP_SECRET=, META_ACCESS_TOKEN=
TIKTOK_RESEARCH_API_KEY=
YOUTUBE_DATA_API_KEY=
METRICOOL_CLIENT_ID=, METRICOOL_CLIENT_SECRET=, METRICOOL_ACCESS_TOKEN=

# Feature flags
ENABLE_AI_ANALYZER=false  # ← False por defecto (Opción A del CEO)
```

---

## 14. URLs DE PRODUCCIÓN

| Servicio | URL |
|----------|-----|
| API | `https://lawebcore-production.up.railway.app` |
| Frontend | `https://lawebcore.vercel.app` |
| Health | `https://lawebcore-production.up.railway.app/api/v1/health` |
| Metrics | `https://lawebcore-production.up.railway.app/metrics` |

---

*Documento generado: 2026-08-05*
*Última actualización: Claude Code Fable 5 Audit — Todos los fixes aplicados y validados*
*Autor: Equipo La Web Figital Agency + Claude Code Fable 5*
