# La Web Core - Roadmap tecnico

## Estado actual

**v0.1.0 (P.I.A.R. MVP + Discovery backend + Frontend Discovery)**
- API FastAPI deployada en Railway
- ARQ workers deployados en Railway
- Supabase (DB + Auth + pgvector)
- Frontend React 19 + Vite en Vercel
- Modulo Discovery con LangGraph + DeepSeek
- Frontend Discovery UI (chat, busqueda directa, historial)

## Problemas tecnicos identificados (Jul 2026)

### 1. Deps faltantes en pyproject.toml

Sufrimos un crash en Railway porque `slowapi` se importaba en `app/main.py` y `app/core/rate_limiter.py` pero no estaba declarado en `apps/api/pyproject.toml`. Lo mismo pasaba con muchas deps en `apps/workers/pyproject.toml` que el worker necesita al ejecutar tareas de Discovery.

**Fix inmediato aplicado en commit `5303cbc`:**
- Agregado `slowapi>=0.1.9` a apps/api
- Duplicadas deps compartidas en apps/workers (structlog, sqlalchemy, supabase, openai, langchain*, httpx, slowapi, etc.)

**Solucion a largo plazo (DEFERIDA):** Refactor a `packages/core/` (monorepo package compartido entre apps/api y apps/workers).

### 2. Refactor a paquete compartido `packages/core/`

**Por que:** Hoy las deps estan duplicadas entre `apps/api/pyproject.toml` y `apps/workers/pyproject.toml`. Cualquier modulo nuevo que se comparta entre API y workers requiere sincronizar dos archivos. Es fragil.

**Que se hara:**
1. Crear `packages/core/lawebcore_core/` con:
   - `config.py` (base settings compartidos: Supabase, AI keys, Redis)
   - `db.py` (SQLAlchemy engine + session)
   - `logging.py`
   - `supabase_rest.py`
   - `cost_tracker.py`
   - `security.py` (JWT helpers)
   - `discovery/` completo (brief_parser, query_builder, result_ranker, orchestrator, memory, schemas, tools/*)
   - `ai/deepseek_client.py` (mover desde apps/api/app/ai/)
   - `models/` con Base, mixins, ApiCost
2. Mover esos archivos desde `apps/api/`
3. Reescribir todos los imports en API y workers de `from app.X` a `from lawebcore_core.X`
4. Limpiar `apps/api/pyproject.toml` y `apps/workers/pyproject.toml` para que solo declaren deps UI-specificas (FastAPI router, routes en API; arq setup en workers) y dependan de `lawebcore-core` como path dep
5. Actualizar Dockerfiles: COPY packages/core antes de pip install
6. Actualizar tests para usar nuevos imports

**Tiempo estimado:** 3-4 horas
**Riesgo:** Medio-alto (toca muchos archivos, riesgo de regresion en PIAR core)
**Prioridad:** Alta - hacerlo antes de que se acumulen mas modulos compartidos

**Decision de diseno necesarias:**
- Donde viven los modelos SQLAlchemy: core/models/ vs API/models/? (Recomendado: los compartidos en core, los PIAR-specific en API)
- Config: settings_base.py en core vs settings.py duplicado? (Recomendado: base en core, API extiende)

### 3. Acoplamiento discovery <-> worker

`memory.py` tenia una linea muerta que importaba `app.worker` (modulo que no existe en API). Reemplazado por:
- `app/core/worker_enqueuer.py`: helper de ARQ pool
- `main.py` lifespan: init/close del pool
- `discovery.py` endpoint `/search`: llama `enqueue_discovery_run()` despues de crear el run

Solucion actual es funcional. El refactor a `packages/core/` la hara mas limpia.

### 4. Tests

Hay tests en `apps/api/tests/` que importan `from app.X`. Habra que actualizarlos en el refactor a core.

Tests NO se ejecutan en CI aun - considerar agregar GitHub Actions en sprint futuro.

## Pendientes funcionales

### P.I.A.R. v0.1.0 polish
- [ ] Verificar end-to-end despues del fix de Railway
- [ ] Documentar API keys requeridas en Railway
- [ ] Capturar screenshots del dashboard y Discovery

### Discovery - siguiente fase
- [ ] Aplicar para Meta Business API App Review (7-15 dias)
- [ ] Aplicar para TikTok Research API (7-15 dias)
- [ ] Implementar persistence layer en orchestrator (hoy solo en memoria)
- [ ] Agregar feedback loop (user accept/dismiss candidates -> mejorar scoring)
- [ ] Implementar streaming de respuestas en el chat
- [ ] Background jobs: re-rank periodico de candidatos top

### Observabilidad
- [ ] Dashboard Grafana con Prometheus metrics
- [ ] Alerts Sentry para discovery_run failures
- [ ] Tracking de costos por cliente (multi-tenant)

### Auth + multi-tenant
- [ ] Validar que BU filtering funciona en todos los endpoints
- [ ] RLS policies para discovery_* tables (multi-tenant safety)
