# La Web Core

> Plataforma interna de **La Web Figital Agency** para gestion integral de campanas de marketing, KPIs, operaciones de marca y producto, e Inteligencia Artificial.

**El corazon y nucleo operativo de la agencia, todo en un solo producto.**

---

## Stack

- **Frontend:** React 19 + Vite + TypeScript + shadcn/ui + Tailwind + TanStack Query + Zustand
- **Backend:** FastAPI (Python 3.12 async) + SQLAlchemy 2.0 + Pydantic v2
- **DB / Auth / Storage:** Supabase (Postgres 16 + Auth + Storage + Realtime + pgvector)
- **Jobs async:** ARQ sobre Redis
- **IA:** LangChain + OpenAI / Anthropic + pgvector para RAG
- **Hosting:** Vercel (FE) + Railway (API + workers + Redis) + Supabase Cloud (DB)
- **Monorepo:** pnpm workspaces

---

## Estructura del monorepo

```
lawebcore/
├── apps/
│   ├── web/          # React + Vite SPA (shadcn/ui)
│   ├── api/          # FastAPI backend
│   └── workers/      # ARQ workers (jobs async, IA, integraciones)
├── packages/
│   ├── shared-types/ # Tipos TS generados desde OpenAPI
│   └── ui/           # Componentes compartidos
├── supabase/
│   ├── migrations/   # SQL migrations versionadas (1-11)
│   ├── functions/    # Edge Functions (Deno)
│   ├── seed.sql      # Roles, permisos, BUs, KPIs, prompts IA
│   └── seed_excel_data.sql  # Datos del Excel "HISTORIAL DE CAMPAÑAS"
├── docs/             # Documentacion (ARCHITECTURE, DOMAIN, RUNBOOK)
├── scripts/
│   └── etl_excel.py  # Convierte el Excel historico en SQL seed
└── .github/workflows # CI/CD
```

---

## Quickstart (desarrollo local)

### 1. Prerrequisitos
- Node >= 20, pnpm >= 9
- Python >= 3.12
- Docker (para Postgres + Redis locales)

### 2. Levantar servicios locales
```bash
docker compose up -d           # Postgres + Redis en localhost
```

### 3. Aplicar migraciones y seed
```bash
psql "postgresql://postgres:postgres@localhost:5432/lawebcore" -f supabase/migrations/00000000000001_extensions.sql
# ... aplicar 02 al 11 en orden ...
psql "postgresql://postgres:postgres@localhost:5432/lawebcore" -f supabase/seed.sql
psql "postgresql://postgres:postgres@localhost:5432/lawebcore" -f supabase/seed_excel_data.sql
```

O con Supabase CLI:
```bash
cd supabase
supabase start
supabase db reset
```

### 4. ETL del Excel historico
```bash
python3 scripts/etl_excel.py
# Genera supabase/seed_excel_data.sql con 14 clientes, 25 marcas, 32 campanas
```

### 5. Backend (FastAPI)
```bash
cd apps/api
pip install -e ".[dev]"
cp ../../.env.example .env       # editar valores
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/api/docs
```

### 6. Frontend (React)
```bash
cd apps/web
pnpm install
pnpm dev
# App: http://localhost:5173
```

### 7. Workers (ARQ)
```bash
cd apps/workers
pip install -e ../api
arq app.worker.WorkerSettings
```

---

## Variables de entorno

Copia `.env.example` a `.env` y rellena:

| Variable | Descripcion |
|---|---|
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | Credenciales de Supabase |
| `SUPABASE_JWT_SECRET` | Para verificar tokens en el backend |
| `DATABASE_URL` | Connection string asyncpg |
| `REDIS_URL` | Para ARQ workers |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Proveedores LLM |
| `HYPEAUDITOR_API_KEY`, etc. | Integraciones externas |

---

## Migracion del Excel historico

`scripts/etl_excel.py` parsea `HISTORIAL DE CAMPAÑAS - LA WEB.xlsx` (37 filas) y genera SQL idempotente con:

- 14 clientes unicos (NESTLE, PEPSICO, POLAR, MOVILNET, etc.)
- 25 marcas unicas (OREO, RUFFLES, DOLCE GUSTO, SOLERA, etc.)
- 32 campanas con sus KPIs (reach, engagement, retention, etc.)
- Links externos (Canva, Drive, HypeAuditor, Trello) inferidos por URL
- Insights y formatos ganadores cuando hay datos

Re-corre el script cada vez que el Excel cambie.

---

## Deploy

### Railway (API + workers + Redis)
- Conectar el repo en [railway.app](https://railway.app)
- Crear servicio `api` apuntando a `apps/api/Dockerfile`
- Crear servicio `workers` (mismo Dockerfile, comando: `arq app.worker.WorkerSettings`)
- Agregar Redis como add-on
- Configurar variables de entorno

### Vercel (Frontend)
- Conectar el repo en [vercel.com](https://vercel.com)
- Root directory: `apps/web`
- Framework preset: Vite
- Configurar env vars: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

### Supabase Cloud (DB)
- Crear proyecto en [supabase.com](https://supabase.com)
- Aplicar migraciones (SQL Editor o CLI)
- Aplicar seed (roles, permisos, BUs)
- Aplicar `seed_excel_data.sql`

---

## Roadmap

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para el plan completo.

- **Fase 0** (actual): Cimientos + scaffolds + ETL del Excel ✅
- **Fase 1** (siguiente): MVP funcional (auth + CRUD + Kanban + dashboard)
- **Fase 2**: Workflows + integraciones + reportes auto
- **Fase 3**: IA completa (RAG + generadores + forecast + matchmaking)
- **Fase 4**: Escala + SSO + BI + multi-tenant

---

## Licencia

Propietario - La Web Figital Agency. Todos los derechos reservados.