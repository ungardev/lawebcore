# La Web Core - Roadmap técnico

## Estado actual

**v0.2.0 (Sprint 1 — "El Ojo que Todo lo Ve" MVP)**
- ✅ Pipeline de 4 capas Apify deployed en Railway (`4b379d4`)
- ✅ LWFA Scoring (4 KPIs exclusivos: ICA, Geo-Foco, Velocity, Business Intent)
- ✅ 28 keywords estratégicas Gemini organizadas en 5 categorías
- ✅ 3 nuevos actores Apify integrados (search, hashtag, engagement analytics)
- ✅ Commit histórico: `feat(discovery): Sprint 1 - 4-layer Apify pipeline + LWFA scoring + Gemini keywords`
- Railway: `https://lawebcore-production.up.railway.app` (200 OK, 7 funciones worker)
- Vercel: `https://lawebcore.vercel.app`
- Supabase (DB + Auth + pgvector)

## Sprint 1 completado (Jul 20 — commit `4b379d4`)

### Arquitectura implementada

```
STEP 1: search_users_by_multiple_keywords (instagram-search-scraper)
         28 keywords Gemini → hasta 250 handles únicos

STEP 2: scrape_hashtags_batch (instagram-hashtag-scraper)
         22 hashtags → ~660 posts con geotags

STEP 3: search_instagram_profiles_batch (instagram-profile-scraper)
         Top 80 handles enriquecidos con followers + country

STEP 4: analyze_profile_engagement (engagement-analytics actor)
         Top 20 × 30 posts → velocity, consistency, content_mix

STEP 5: LWFA Scoring → 4 KPIs + composite 0-100
         ica + geo_foco + velocity + business_intent → match_score
```

### Archivos modificados (6 archivos, +745 -358 líneas)
- `packages/discovery/discovery/tools/apify_client.py` — 6 métodos nuevos + 3 actor IDs
- `packages/discovery/discovery/schemas.py` — +`DiscoveryPlan` schema
- `packages/discovery/discovery/query_builder.py` — 28 keywords Gemini → `DiscoveryPlan`
- `packages/discovery/discovery/result_ranker.py` — 5 funciones LWFA scoring
- `apps/api/app/workers/worker.py` — pipeline 5 pasos refactorizado
- `packages/discovery/discovery/orchestrator.py` — actualizado para `DiscoveryPlan`

### Costos Sprint 1
- **Por campaña:** ~$3.30 (Apify Free tier)
- **Apify Free $5:** ~1.5 campañas completas
- **Apify CEO $25-29:** ~9-10 campañas/mes

## Problemas técnicos identificados

### 1. Deps faltantes en pyproject.toml

Sufrimos un crash en Railway porque `slowapi` se importaba en `app/main.py` pero no estaba declarado en `apps/api/pyproject.toml`. Lo mismo pasaba con muchas deps en `apps/workers/pyproject.toml`.

**Fix aplicado en commit `5303cbc`.**

**Solución a largo plazo (DEFERIDA):** Refactor a `packages/core/` (monorepo package compartido entre apps/api y apps/workers).

### 2. Refactor a paquete compartido `packages/core/`

**Por qué:** Las deps están duplicadas entre `apps/api/pyproject.toml` y `apps/workers/pyproject.toml`.

**Qué se hará:**
1. Crear `packages/core/lawebcore_core/` con:
   - `config.py` (base settings compartidos)
   - `db.py` (SQLAlchemy engine + session)
   - `discovery/` completo (mover desde `packages/discovery/`)
2. Mover esos archivos desde `apps/api/`
3. Reescribir todos los imports
4. Limpiar `pyproject.toml` de ambas apps

**Tiempo estimado:** 3-4 horas
**Riesgo:** Medio-alto
**Prioridad:** Alta

### 3. Tests

Hay tests en `apps/api/tests/` que importan `from app.X`. Habrá que actualizarlos en el refactor a core.

**Tests NO se ejecutan en CI aún** — considerar agregar GitHub Actions en sprint futuro.

## Pendientes funcionales

### Sprint 2 — Próximo (antes del martes 28 julio)
- [ ] End-to-end Purina Dog Chow demo completa
- [ ] Redis cache layer para reducir costo Apify
- [ ] Meta for Developers app setup (App Review — 2-6 semanas)
- [ ] Dashboard de costos por campaña en el frontend

### Sprint 3 — Agosto 4
- [ ] TikTok Research API (post-aprobación 7-15 días)
- [ ] Outreach automation (Resend email)
- [ ] Feedback loop (user accept/dismiss → mejora scoring)
- [ ] Background jobs: re-rank periódico de candidatos top

### Sprint 4 — Agosto 11
- [ ] Multi-bu / multi-tenant prep
- [ ] BI dashboard con Metabase
- [ ] PWA / mobile

### Observabilidad
- [ ] Dashboard Grafana con Prometheus metrics
- [ ] Alerts Sentry para discovery_run failures
- [ ] Tracking de costos por cliente (multi-tenant)

### Auth + multi-tenant
- [ ] Validar que BU filtering funciona en todos los endpoints
- [ ] RLS policies para discovery_* tables (multi-tenant safety)

## Métricas de Sprint 1

| Métrica | Valor |
|---|---|
| Commits en Sprint 1 | ~15 |
| Líneas añadidas (neto) | +387 |
| Actors Apify integrados | 3 |
| Métodos Apify nuevos | 6 |
| KPIs LWFA | 4 |
| Keywords Gemini | 28 |
| Hashtags Gemini | 22 |
| Costo estimado por campaña | $3.30 |
| Pipeline steps | 5 |
