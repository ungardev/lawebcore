# Engineering State — La Web Core

> **Para:** Claude Code Fable 5 — Análisis y Plan de Desarrollo
> **Fecha:** Julio 2026
> **Autor:** Dainer Ungar — CEO, La Web Figital Agency

---

## 1. Estado General del Sistema

### 1.1 Lo que está funcionando ✅

| Componente | Estado | Detalle |
|---|---|---|
| Railway API | ✅ 200 OK | `https://lawebcore-production.up.railway.app` |
| Railway Workers | ✅ 7 funciones activas | discovery_run_task, embed_document_task, etc. |
| Redis | ✅ 8.2.1, saves exitosos | `clients_connected=4`, sin errores |
| Supabase | ✅ Connectado | Postgres + Auth + pgvector |
| Health endpoint | ✅ `{"status":"ok"}` | `GET /api/v1/health` |
| Vercel Frontend | ✅ Deployado | `https://lawebcore.vercel.app` |

### 1.2 Lo que está deployado (Sprint 1) ✅

**Commit:** `4b379d4` — `feat(discovery): Sprint 1 - 4-layer Apify pipeline + LWFA scoring + Gemini keywords`

**Pipeline de 4 capas:**
```
STEP 1: search_users_by_multiple_keywords() — instagram-search-scraper
STEP 2: scrape_hashtags_batch() — instagram-hashtag-scraper
STEP 3: search_instagram_profiles_batch() — instagram-profile-scraper
STEP 4: analyze_profile_engagement() — engagement-analytics actor
STEP 5: calculate_lwfa_composite() — 4 KPIs → score 0-100
```

**LWFA Scoring:**
- ICA (Index de Conversión Aparentada)
- Geo-Foco Real (geotags × idioma)
- Engagement Velocity (interacciones/día)
- Business Intent (multilink + fb page + business account)

**Keywords Gemini:** 28 keywords en 5 categorías (brand_competition, lifecycle_health, consumer_personas, market_trends, nicho_ve)

### 1.3 Lo que NO está funcionando aún ⚠️

| Componente | Estado | Notas |
|---|---|---|
| Meta for Developers | ⚠️ No iniciado | 2-6 semanas de approval runway |
| TikTok Research API | ⚠️ No solicitado | Pendiente Meta approval primero |
| Outreach automation | 🔲 En backlog | Email con Resend |
| Historical learning | 🔲 En backlog | Feedback loop: accept/dismiss → mejora scoring |

---

## 2. Arquitectura Actual

```
Frontend (React 19 + Vite) ──→ FastAPI (Railway) ──→ Supabase
                                   │
                                   ▼
                              ARQ Workers (Redis)
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              discovery_run   embed_document  sync_metricool
                  task            task            task
```

### 2.1 Estructura del monorepo

```
packages/
├── shared-core/        # Config, DB, Supabase REST
├── shared-ai/         # DeepSeek client, embeddings
├── discovery/          # ★ El Ojo que Todo lo Ve
│   └── discovery/
│       ├── brief_parser.py
│       ├── orchestrator.py     # LangGraph state machine
│       ├── query_builder.py    # Gemini keywords → DiscoveryPlan
│       ├── result_ranker.py    # LWFA scoring
│       ├── schemas.py           # BriefStructured, DiscoveryPlan
│       └── tools/
│           └── apify_client.py  # 6 métodos nuevos
apps/
├── api/               # FastAPI ( Railway)
├── workers/           # ARQ worker (Railway)
└── web/               # React (Vercel)
```

### 2.2 Stack tecnológico

| Componente | Tecnología | Notas |
|---|---|---|
| **LLM** | DeepSeek-V3 | Único LLM usado, no OpenAI/Anthropic |
| **Embeddings** | fastembed `all-MiniLM-L6-v2` | Via pgvector en Supabase |
| **Scraping** | Apify (3 actores) | search-scraper, hashtag-scraper, engagement-analytics |
| **Workers** | ARQ + Redis | 7 funciones activas |
| **DB** | Supabase Postgres 16 | RLS + pgvector |
| **Infra** | Railway + Vercel | ~$20/mes Railway |

---

## 3. Deuda Técnica

### 3.1 Alta Prioridad ⚠️

#### No hay tests
- No hay tests unitarios ni de integración
- No se ejecutan en CI
- Cualquier cambio puede romper algo sin feedback automático

**Impacto:** Alto — regressions no se detectan hasta producción
**Esfuerzo:** 4-8 horas para cobertura básica del pipeline de discovery

#### Dependencias duplicadas en 2 pyproject.toml
- `apps/api/pyproject.toml` y `apps/workers/pyproject.toml` tienen deps compartidas duplicadas
- Cualquier módulo compartido requiere sincronizar ambas
- Ya causó un crash en Railway (slowapi faltante)

**Impacto:** Medio — frágil para crecimiento
**Esfuerzo:** 3-4 horas (refactor a `packages/core/`)
**Riesgo:** Medio-alto — toca muchos imports

#### Orchestrator usa memoria in-memory
- `DiscoveryOrchestrator.state` es un dict en memoria
- Se pierde en cada restart del worker
- Conversaciones activas se pierden si el worker se reinicia

**Impacto:** Medio — usuarios pueden perder contexto de conversación
**Esfuerzo:** 2-3 horas para persistir en Supabase
**Riesgo:** Bajo

### 3.2 Media Prioridad ⚠️

#### No hay cache layer para resultados Apify
- Cada discovery run hace llamadas frescas a Apify aunque los datos no hayan cambiado
- Costo: ~$3.30/campaña sin cache
- Si el mismo handle se busca 3 veces, se paga 3 veces

**Impacto:** Costos recurrentes + latency innecesaria
**Esfuerzo:** 2-4 horas (Redis cache con TTL 24h)
**Riesgo:** Bajo

#### RLS policies incompletas
- Tablas `discovery_*` pueden no tener RLS activa
- Multi-tenant safety no verificada

**Impacto:** Seguridad — riesgo de data leak entre BUs
**Esfuerzo:** 2-3 horas para auditar y corregir
**Riesgo:** Medio

#### No hay tracking de costos por campaña
- Los costos de Apify se registran en `api_costs` pero no se agregan por `run_id` o `bu_id`
- No hay dashboard de "cuánto gasté en discovery este mes"

**Impacto:** Operaciones — sin visibilidad de costo real
**Esfuerzo:** 2 horas
**Riesgo:** Bajo

### 3.3 Baja Prioridad 🔲

| Tema | Impacto | Esfuerzo |
|---|---|---|
| Streaming de respuestas en chat | UX | 4h |
| Feedback loop (accept/dismiss → scoring) | Data quality | 6-8h |
| Background re-rank periódico | Data freshness | 3-4h |
| Metabase BI dashboard | Observabilidad | 4-6h |
| Sentry alerts | Debugging | 2h |
| Prometheus metrics | Observabilidad | 3-4h |

---

## 4. Lo que Necesita el Sistema Para ser "Production Ready"

### 4.1 Mínimo para demo Purina (antes del martes 28 julio)

1. **Tests básicos del pipeline** — al menos un test que verifique que `discovery_run_task` no crashea
2. **Cache layer Redis** — reducir costo Apify de $3.30 a ~$0.50 por campaña
3. **Error handling robusto** — si un paso del pipeline falla, no morir todo el run
4. **Logging mejorado** — saber exactamente en qué paso está el pipeline en cada momento

### 4.2 Mínimo para escalar (10+ campañas/mes)

1. **Cost tracking por campaña** — saber cuánto gastamos en cada discovery run
2. **RLS audit** — verificar que no hay data leaks
3. **Redis cache** — obligatorio para reducir costos
4. **Historical learning** — cada campaña aprobada/refutada mejora el scoring

### 4.3 Mínimo para multi-tenant (Sprint 4)

1. **BU isolation completa** — cada BU ve solo sus candidatos
2. **Rate limits por BU** — evitar que un cliente consuma todo el budget de Apify
3. **Configuración por BU** — cada BU puede tener sus propias keywords, hashtags

---

## 5. Decisiones Técnicas Abiertas

| Decisión | Opciones | Recomendación actual |
|---|---|---|
| **Meta for Developers** | Solicitar ahora vs esperar | Solicitar ahora, 2-6 semanas de approval |
| **TikTok Research API** | Solicitar cuando Meta esté aprobado | Sí — hace falta para TikTok |
| **Caching strategy** | Redis (actual) vs Upstash vs no cache | Redis actual — ya funciona |
| **Historical learning** | Empezar con reglas vs ML | Empezar con reglas (ponderación de scores) |
| **Benchmarks VE** | Recolectar data real vs guess | Recolectar data real de campañas |

---

## 6. Costos Actuales vs Proyectados

### 6.1 Costo por campaña (hoy, sin cache)

| Step | Costo | Con cache |
|---|---|---|
| STEP 1 Keyword search | $1.30 | ~$0.10 |
| STEP 2 Hashtag posts | $1.43 | ~$0.10 |
| STEP 3 Profile enrichment | $0.21 | ~$0.05 |
| STEP 4 Engagement analytics | $0.36 | ~$0.05 |
| **Total** | **~$3.30** | **~$0.30** |

### 6.2 Costo mensual proyectado

| Escenario | Campañas/mes | Costo Apify | Costo DeepSeek | Total APIs |
|---|---|---|---|---|
| Actual (sin cache) | 5 | $16.50 | $2.50 | ~$19 |
| Con cache | 5 | $1.50 | $2.50 | ~$4 |
| Escalado (con cache) | 20 | $6.00 | $10.00 | ~$16 |
| Escalado (con cache) | 50 | $15.00 | $25.00 | ~$40 |

**Conclusión: el cache es crítico para escalar. Sin él, el costo por campaña es 10x mayor.**

---

## 7. Seguridad y Compliance

### 7.1 Datos

- ✅ Solo datos públicos de Instagram (scraping de perfiles públicos)
- ✅ No se almacenan datos privados de usuarios de Instagram
- ✅raw_payload en `discovery_candidates` es JSON con datos públicos

### 7.2 ToS

| Plataforma | Compliance | Notas |
|---|---|---|
| Instagram/Apify | ✅ Bajo riesgo | Datos públicos, consentimiento implícito |
| TikTok | ⚠️ Pendiente | Esperando Research API approval |
| Meta | ⚠️ Pendiente | Esperando App Review |

### 7.3 Rate Limiting

- ✅ slowapi configurado en FastAPI
- ⚠️ No hay rate limit por BU en endpoints de discovery
- ⚠️ No hay circuit breaker si Apify falla

---

## 8. Lo que Fable 5 Debe Saber

### 8.1 Contexto de negocio

- Este no es un proyecto de software — es una herramienta de negocio
- El éxito se mide en: campañas con ROI positivo, costo por campaña bajo, tiempo de selección corto
- El código es el medio; el negocio es el fin

### 8.2 Restricciones

- Budget: $250 USD/mes max en APIs + $50/mes infra
- Equipo: 1 persona, 4h/día
- Timeline: demo Purina antes del martes 28 julio

### 8.3 Prioridades explícitas

1. **Mínimo para mañana:** Demo funcional que demuestre el pipeline end-to-end
2. **Mínimo para escalar:** Cache layer + cost tracking
3. **Mínimo para multi-tenant:** RLS audit + BU isolation

### 8.4 Lo que NO hacer (sin consultar)

- No cambiar la arquitectura general del sistema
- No reemplazar Apify con otra fuente de datos
- No agregar OpenAI/Anthropic como LLM (DeepSeek es suficiente)
- No implementar ML para historical learning antes de tener data real

---

*Documento preparado para guiar el análisis de Fable 5.*
*La Web Figital Agency — Julio 2026*
