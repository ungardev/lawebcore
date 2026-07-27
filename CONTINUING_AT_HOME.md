# Continuar en Casa — La Web Core

**Última actualización:** lunes 21 julio 2026, ~01:00 VET
**PC:** Casa
**Repo:** commit `1251292` (todo Sprint 1 — listo para Fable 5)
**Usuario:** Dainer Ungar — CEO, La Web Figital Agency

---

## Lo que se hizo en la sesión de oficina (lunes 21 julio)

### Sprint 1 completado ✅

**Commit `4b379d4`** — Pipeline de 4 capas Apify + LWFA Scoring + Gemini keywords:
- 6 métodos Apify nuevos (search-scraper, hashtag-scraper, engagement-analytics)
- LWFA Scoring con 4 KPIs exclusivos (ICA, Geo-Foco, Velocity, Business Intent)
- 28 keywords Gemini organizadas en 5 categorías
- worker.py reescrito con pipeline de 5 pasos
- Deployado en Railway: `https://lawebcore-production.up.railway.app`

**Commit `1251292`** — Documentación para Fable 5:
- README.md reescrito completo
- DISCOVERY_ARCHITECTURE.md reescrito v2.0
- ARCHITECTURE.md actualizado con Discovery Module
- ROADMAP.md reescrito (cerrado Sprint 1)
- CONTEXT_FOR_FABLE5.md creado (guía para el agente)
- STRATEGIC_BRIEF.md creado (contexto de negocio)
- ENGINEERING_STATE.md creado (estado real del sistema)
- CONTINUING_AT_HOME.md viejo archivado en docs/historical/

### Redis ✅

- **Funciona perfectamente** — no hay que cambiarlo
- Versión: 8.2.1, saves exitosos cada ~60 segundos
- `clients_connected=4` — API + workers conectados
- Health: `curl https://lawebcore-production.up.railway.app/api/v1/health` → `200 OK`

---

## Antes de empezar en casa

### 1. Hacer git pull

```bash
cd ~/proyectos/lawebcore
git pull origin main
```

Después del pull，你应该 tener:
- `STRATEGIC_BRIEF.md` en la raíz
- `ENGINEERING_STATE.md` en la raíz
- `docs/CONTEXT_FOR_FABLE5.md` existir
- `docs/DISCOVERY_ARCHITECTURE.md` reescrito
- `CONTINUING_AT_HOME.md` en la raíz (este archivo actualizado)

### 2. Verificar que todo funciona

```bash
# Health check
curl https://lawebcore-production.up.railway.app/api/v1/health
# Debe responder: {"status":"ok","service":"lawebcore-api","version":"0.1.0"}
```

### 3. Si tienes problemas de conexión

El health endpoint funciona desde cualquier red. Si no responde:
- Verificar que no estés bloqueando peticiones HTTPS
- Probar desde el navegador: `https://lawebcore-production.up.railway.app/api/v1/health`

---

## Estructura del repo (lo que te interesa)

```
lawebcore/
├── README.md                          ← Empieza aquí
├── STRATEGIC_BRIEF.md                ← Contexto de negocio para Fable 5
├── ENGINEERING_STATE.md               ← Estado real del sistema
├── CONTINUING_AT_HOME.md              ← Este archivo
├── docs/
│   ├── DISCOVERY_ARCHITECTURE.md     ← Arquitectura del pipeline
│   ├── CONTEXT_FOR_FABLE5.md         ← Guía para Fable 5
│   ├── ROADMAP.md                    ← Estado Sprint 1-4
│   ├── ARCHITECTURE.md               ← Arquitectura general
│   └── historical/
│       └── CONTINUING_AT_HOME_2026-07-19.md  ← Sesión vieja (archivo)
├── packages/discovery/discovery/
│   ├── tools/apify_client.py          ← Los 6 métodos nuevos
│   ├── result_ranker.py              ← LWFA scoring
│   ├── query_builder.py              ← Gemini keywords
│   ├── schemas.py                    ← DiscoveryPlan schema
│   └── orchestrator.py               ← LangGraph state machine
└── apps/api/app/workers/worker.py    ← Pipeline de 5 pasos
```

---

## Próximos pasos (Sprint 2 — antes del martes 28 julio)

### 1. Esperar análisis de Fable 5

El repo está listo para que Fable 5 lo analice y produzca el mejor plan de desarrollo. Lee los documentos en orden:

1. **`STRATEGIC_BRIEF.md`** — el problema de mercado y la visión
2. **`README.md`** — entry point técnico
3. **`ENGINEERING_STATE.md`** — lo que funciona, lo que no, deudas
4. **`docs/CONTEXT_FOR_FABLE5.md`** — guía rápida para Fable 5
5. **`docs/DISCOVERY_ARCHITECTURE.md`** — arquitectura del pipeline

### 2. Demo Purina end-to-end

Cuando Fable 5 dé el plan, el primer objetivo es correr el pipeline completo con un brief real de Purina Dog Chow.

```bash
# Test rápido del pipeline localmente
cd apps/workers
python3 -c "
import asyncio
from discovery.tools import apify_client
from discovery.query_builder import query_builder
from discovery.schemas import BriefStructured

brief = BriefStructured(
    product_name='Purina Dog Chow',
    niches=['mascotas', 'perros'],
    audience_countries=['VE'],
    platforms=['instagram'],
)
plan = query_builder.build(brief)
print(f'Plan: {len(plan.keyword_queries)} keywords, {len(plan.hashtag_queries)} hashtags')
"
```

### 3. Implementar Redis cache layer

**Prioridad alta** — reduce costo por campaña de $3.30 a ~$0.30.

---

## Comandos útiles de desarrollo

### Levantar servicios localmente

```bash
# API FastAPI
cd apps/api
pip install -e ".[dev]"  # si no está instalado
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/api/docs

# Workers ARQ
cd apps/workers
pip install -e ../api
arq app.workers.worker.WorkerSettings

# Frontend React
cd apps/web
pnpm install  # si hay cambios
pnpm dev
```

### Ver logs del worker en Railway

1. Ir a [railway.app](https://railway.app) → proyecto `lawebcore`
2. Click en el servicio `workers`
3. Pestaña "Deployments" → ver logs del último deploy

### Test del health endpoint

```bash
# Desde cualquier terminal
curl https://lawebcore-production.up.railway.app/api/v1/health
```

---

## Notas importantes

- **No cambiar Redis** — funciona perfectamente, no hay que tocarlo
- **El código del pipeline está en:** `packages/discovery/discovery/`
- **La documentación clave:** `README.md`, `STRATEGIC_BRIEF.md`, `ENGINEERING_STATE.md`
- **Fable 5 análisis:** el repo está listo — los docs le dan todo el contexto
- **Railway URL nueva:** `https://lawebcore-production.up.railway.app` (no la vieja `lawebcore-api-production`)

---

## Checklist antes de dormir (si seguiste trabajando en casa)

- [ ] Hiciste `git pull origin main`
- [ ] El health endpoint responde `200 OK`
- [ ] Viste que los docs nuevos están (`STRATEGIC_BRIEF.md`, `ENGINEERING_STATE.md`)
- [ ] El worker está corriendo en Railway (7 funciones activas)

---

## Posibles problemas y soluciones

### `git pull` falla por conflictos

```bash
git stash
git pull origin main
git stash pop
# Resuelve conflictos manualmente si es necesario
```

### No puedes hacer curl al health endpoint

- Verificar conexión a internet
- Probar desde el navegador: `https://lawebcore-production.up.railway.app/api/v1/health`
- Si Railway redeployó, esperar 2-3 minutos

### El worker no está corriendo en Railway

1. Ir a railway.app → proyecto `lawebcore`
2. Servicio `workers` → "Redeploy"
3. Esperar ~2-3 minutos

---

## Roadmap rápido

| Sprint | Fecha | Objetivo |
|---|---|---|
| Sprint 1 ✅ | Jul 20 | Pipeline 4 capas + LWFA + Gemini |
| Sprint 2 | Jul 28 | Demo Purina end-to-end + Cache + Meta app |
| Sprint 3 | Ago 4 | TikTok Research API + Outreach |
| Sprint 4 | Ago 11 | Multi-tenant prep + BI dashboard |

---

*La Web Figital Agency — Julio 2026*
