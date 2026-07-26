# Contexto para Fable 5 — Estado Sprint 1 (Julio 2026)

> Este documento le da a un agente IA (Claude Code Fable 5) todo lo que necesita para entender el proyecto y contribuir productivamente.

---

## TL;DR

**La Web Core** es el núcleo operativo de La Web Figital Agency — una plataforma para gestión de campañas de influencer marketing en Venezuela/LATAM. **El Ojo que Todo lo Ve** es el módulo de discovery, que usa Apify para extraer datos reales de Instagram y un scoring propietario (LWFA) con 4 KPIs exclusivos. El sistema está deployado y funcionando en Railway (`https://lawebcore-production.up.railway.app`).

---

## Lo deployed hoy

| Componente | URL/Estado |
|---|---|
| **Railway API** | `https://lawebcore-production.up.railway.app` — 200 OK |
| **Railway Workers** | 7 funciones activas, Redis 8.2.1 |
| **Vercel Frontend** | `https://lawebcore.vercel.app` |
| **Supabase** | Postgres + Auth + pgvector |
| **Health check** | `GET /api/v1/health` → `200 OK` |

---

## Lo que cambió en Sprint 1

**Commit `4b379d4`** — `feat(discovery): Sprint 1 - 4-layer Apify pipeline + LWFA scoring + Gemini keywords`

6 archivos modificados, +745 líneas netas:

```
packages/discovery/discovery/tools/apify_client.py  +269 líneas
packages/discovery/discovery/query_builder.py       -73/+319 líneas
packages/discovery/discovery/result_ranker.py       +109 líneas
packages/discovery/discovery/schemas.py             +9 líneas
apps/api/app/workers/worker.py                     +314/-150 líneas
packages/discovery/discovery/orchestrator.py        -83/+22 líneas
```

---

## Dónde está la lógica core

| Qué | Dónde | Notas |
|---|---|---|
| Pipeline de discovery | `apps/api/app/workers/worker.py:64` | Función `discovery_run_task` |
| Apify client (6 métodos) | `packages/discovery/discovery/tools/apify_client.py` | 3 actores: search-scraper, hashtag-scraper, engagement-analytics |
| LWFA scoring (4 KPIs) | `packages/discovery/discovery/result_ranker.py:67-180` | `calculate_lwfa_composite()` |
| Keywords Gemini | `packages/discovery/discovery/query_builder.py:10-58` | 5 categorías, 28 keywords |
| DiscoveryPlan schema | `packages/discovery/discovery/schemas.py` | `class DiscoveryPlan` |
| Orchestrator | `packages/discovery/discovery/orchestrator.py` | LangGraph state machine |

---

## Decisiones técnicas cerradas (NO reabrir sin coordinación)

| Decisión | Valor | Fecha |
|---|---|---|
| Source de datos | **Apify** (único, no Excel, no mockup) | Sprint 1 |
| LLM | **DeepSeek-V3** únicamente | Sprint 1 |
| Plataforma inicial | **Instagram únicamente** | Sprint 1 |
| Meta for Developers | **Diferido a Sprint 2** (2-6 semanas approval) | Sprint 1 |
| TikTok | **Diferido a Sprint 3** | Sprint 1 |
| Mockup data | **DEPRECATED** — stats from real system | Sprint 1 |
| Costo por campaña | **~$3.30** (Apify Free tier) | Sprint 1 |

---

## Arquitectura del sistema

```
Frontend (React 19 + Vite) ──→ FastAPI (Railway) ──→ Supabase (DB + pgvector)
                                   │
                                   ▼
                              ARQ Workers (Redis)
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              discovery_run   embed_document  sync_metricool
                  task            task            task
```

**Pipeline de Discovery (5 pasos):**
1. `search_users_by_multiple_keywords()` → handles por keyword
2. `scrape_hashtags_batch()` → posts con geotags
3. `search_instagram_profiles_batch()` → profiles enriquecidos
4. `analyze_profile_engagement()` → velocity, consistency
5. `calculate_lwfa_composite()` → score 0-100

---

## Documentación clave

| Documento | Qué describe |
|---|---|
| [README.md](../README.md) | Punto de entrada, stack, quickstart |
| [docs/DISCOVERY_ARCHITECTURE.md](DISCOVERY_ARCHITECTURE.md) | Arquitectura completa del módulo Discovery v2.0 |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | Arquitectura general del sistema |
| [docs/ROADMAP.md](ROADMAP.md) | Roadmap Sprint 1-4, problemas conocidos |
| [MONOREPO.md](../MONOREPO.md) | Estructura del monorepo y rules de imports |
| [docs/PITCH_LA_WEB_STRATEGIST_&_MANAGER_P_I_A_R.md](PITCH_LA_WEB_STRATEGIST_&_MANAGER_P_I_A_R.md) | Pitch para clientes |

---

## Branch actual

- **Branch:** `main`
- **HEAD:** `4b379d4` — `feat(discovery): Sprint 1 - 4-layer Apify pipeline + LWFA scoring + Gemini keywords`
- **Estado:** Production deploy exitoso, 200 OK

---

## Para contribuir (hoja de ruta para Fable 5)

### Sprint 2 prioridades (antes del martes 28 julio):
1. **End-to-end Purina Dog Chow demo** — correr el pipeline completo con un brief real
2. **Redis cache layer** — guardar resultados intermedios para reducir costo Apify
3. **Meta for Developers setup** — crear app, submit para App Review
4. **Tests** — agregar tests para el pipeline de discovery

### Reglas de contribución:
- **NO usar** `print()` — usar `logger.info/warning/error` de structlog
- **NO hardcodear** URLs ni tokens — usar `settings` de `shared_core.config`
- **NO tocar** `docs/CREDENCIALES_Y_SUSCRIPCIONES.md` (contenido sensible)
- Antes de hacer `git push`, verificar con `python3 -m py_compile` los archivos Python modificados
- Si cambias imports, verificar que el código compila antes de commit

### Testing local del pipeline:
```bash
# Levantar servicios
docker compose up -d

# Correr un discovery run manualmente
cd apps/workers
pip install -e ../api
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

---

## Errores conocidos

1. **`apify/instagram-scraper`** (el viejo actor de hashtags) puede retornar 0 posts para algunos hashtags — el nuevo pipeline usa `instagram-search-scraper` para keywords y `instagram-hashtag-scraper` para posts
2. **Apify Free tier** tiene límite de 2 profiles/run para el actor de engagement analytics — el CEO tier es necesario para uso pesado
3. **Meta for Developers** tarda 2-6 semanas en aprobarse — no bloquear Sprint 2 por esto

---

*Última actualización: Julio 20, 2026 — Commit `4b379d4`*
