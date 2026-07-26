# Arquitectura - La Web Core

## Vision

La Web Core es el producto interno central de La Web Figital Agency. Reemplaza y extiende el Excel `HISTORIAL DE CAMPAÑAS - LA WEB.xlsx` con un portal web con roles, operaciones ricas, KPIs, integraciones e IA.

## Diagrama logico

```
                  ┌──────────────────────────────────────┐
                  │  Frontend (React + Vite + shadcn/ui) │
                  │  Vercel                               │
                  └────────────────┬─────────────────────┘
                                   │ HTTPS REST + WebSocket
                                   ▼
                  ┌──────────────────────────────────────┐
                  │  FastAPI Backend (Python 3.12 async)  │
                  │  Railway (lawebcore-production)        │
                  │  - Auth (Supabase JWT)                │
                  │  - SQLAlchemy 2.0 + asyncpg          │
                  │  - DeepSeek-V3 (LLM)                  │
                  └────┬─────────────────────┬───────────┘
                       │                     │
                       ▼                     ▼
              ┌─────────────────┐    ┌─────────────────┐
              │  Supabase Cloud │    │  ARQ + Redis    │
              │  - Postgres 16  │    │  - Workers      │
              │  - Auth         │    │  - Jobs async   │
              │  - Storage      │    │  - Cron jobs    │
              │  - Realtime     │    │  - 7 funciones  │
              │  - pgvector     │    │    activas      │
              │  - RLS policies │    └─────────────────┘
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────────────────────────────┐
              │  Servicios externos                      │
              │  - OpenAI / Anthropic (LLM)              │
              │  - HypeAuditor (metricas influencers)    │
              │  - Canva / Google Drive / Trello         │
              │  - Slack / Email                         │
              └─────────────────────────────────────────┘
```

## Modelo de datos (Postgres)

Ver `supabase/migrations/` para el detalle. Resumen de las ~30 tablas:

### Identidad y permisos (multi-BU, 100+ usuarios)
- `business_units`, `users`, `roles`, `permissions`, `user_roles`, `teams`, `team_members`

### Jerarquia comercial
- `clients` (corporate) → `brands` → `brand_contacts`, `client_contracts`

### Campanas (entidad principal)
- `campaigns`, `campaign_status_history`, `campaign_influencers`, `campaign_links`, `campaign_documents`

### Influencers
- `influencers`, `influencer_social_accounts`, `influencer_metrics_snapshot`

### KPIs
- `kpi_definitions`, `campaign_kpi_values`, `benchmarks`, `insights`, `winning_formats`

### Operaciones
- `budgets`, `budget_items`, `tasks`, `forms`, `form_submissions`, `automations`, `automation_logs`

### IA / Knowledge
- `ai_prompts`, `documents`, `document_chunks` (pgvector), `ai_conversations`, `ai_messages`, `ai_jobs`

### Analytics, auditoria, integraciones
- `dashboards`, `widgets`, `scheduled_reports`, `audit_logs`, `integrations`, `webhooks`, `exports`

## Seguridad: defensa en profundidad

1. **Supabase Auth** maneja sign-in/sign-up/JWT
2. **RLS** en cada tabla filtra por `business_unit_id`, `client_id`, `team_id`, `role`
3. **Backend** verifica JWT y aplica checks adicionales (own resources, ownership, etc.)
4. **Audit log** automatico registra toda mutacion
5. **Soft deletes** en entidades criticas (`deleted_at`)

### Roles definidos

| Code | Nombre | Alcance |
|---|---|---|
| `admin_general` | Administrador General | Total |
| `director_bu` | Director de BU | Su BU |
| `project_manager` | Project Manager | Campanas asignadas |
| `account_manager` | Account Manager | Clientes/Marcas |
| `analista` | Analista | KPIs, reportes, benchmarks |
| `creativo` | Creativo | Assets, campanas (read + upload) |
| `influencer_liaison` | Influencer Liaison | Influencers + campanas |
| `finance` | Finanzas | Budgets, contratos, margenes |
| `cliente_externo` | Cliente Externo | Solo lectura de sus marcas |
| `viewer` | Visualizador | Read-only global |

## Discovery Module — "El Ojo que Todo lo Ve"

El módulo de Discovery vive en `packages/discovery/` y se despliega como parte del worker ARQ en Railway. Ver [DISCOVERY_ARCHITECTURE.md](DISCOVERY_ARCHITECTURE.md) para documentación completa.

### Stack
- **LLM:** DeepSeek-V3 (no OpenAI/Anthropic)
- **Scraping:** Apify (3 actores Instagram)
- **Embeddings:** fastembed `all-MiniLM-L6-v2` via pgvector

### Pipeline de 4 capas
```
Keyword Discovery (instagram-search-scraper)
    → Hashtag Deep Dive (instagram-hashtag-scraper)
    → Profile Enrichment (instagram-profile-scraper)
    → Engagement Analytics (engagement-analytics actor)
    → LWFA Scoring (4 KPIs exclusivos)
```

### LWFA Scoring
Score 0-100 compuesto por 4 KPIs propietarios:
1. **ICA** — Index de Conversión Aparentada (buy intent en comentarios)
2. **Geo-Foco Real** — geotags × idioma captions VE
3. **Engagement Velocity** — interacciones/día
4. **Business Intent** — multilink + fb page + business account

## Patrones tecnicos

- **API contract-first**: OpenAPI auto-generado por FastAPI → tipos TS
- **Realtime Kanban**: Supabase Realtime subscriptions (sin websockets custom)
- **Multi-tenant ready**: campo `agency_id` preparado aunque arranque single-tenant
- **Soft deletes + audit log** en entidades criticas
- **AI cost guardrails**: rate limits, modelos chicos por default, cache, fallback

## Decisiones clave

### ¿Por que FastAPI sobre Django?
- Async nativo (mejora para IA, integraciones concurrentes, websockets)
- OpenAPI auto-generado = SDK TS gratis
- Supabase provee UI admin equivalente a Django Admin
- Mejor ecosistema IA (LangChain, LlamaIndex)

### ¿Por que Supabase sobre Firebase?
- Postgres real (vs NoSQL)
- pgvector para RAG sin servicio extra
- RLS para seguridad empresarial
- Storage con signed URLs

### ¿Por que Vercel + Railway?
- Vercel: mejor DX para React/Vite, edge network, gratis al inicio
- Railway: soporta Docker + servicios multiples (API + workers + Redis), pricing predecible

## Roadmap (16+ semanas)

### Fase 0 — Cimientos (Sem 1-2) ✅
- Repo monorepo + CI/CD
- Migraciones Supabase (1-11)
- Seed: roles, permisos, BUs, KPIs
- ETL Excel → 14 clientes, 25 marcas, 32 campanas
- Scaffold FastAPI + React+Vite + shadcn
- Workers ARQ base

### Fase 1 — MVP funcional (Sem 3-6)
- Auth + login
- CRUD Clientes/Marcas/Campanas
- Pipeline Kanban con drag&drop
- CRUD Influencers + asignacion
- KPIs manuales con historico
- Dashboard ejecutivo

### Fase 2 — Operacion rica (Sem 7-10)
- Workflows configurables
- Formularios dinamicos
- Notificaciones
- Integraciones: HypeAuditor, Canva, Drive, Trello
- Reportes automaticos

### Fase 3 — Inteligencia (Sem 11-16)
- RAG sobre documentos
- Generadores LLM (brief, post-mortem, propuesta)
- Detector de anomalias + benchmarks auto
- Forecast de KPIs pre-campana
- Matchmaking influencer ↔ campana

### Fase 4 — Escala (Sem 17+)
- PWA / mobile
- SSO corporativo
- BI avanzado
- Multi-tenant (si crece a otras agencias)