# MASTER PROMPT — Claude Code Fable 5: Análisis de Oportunidades de Mejora

> **Para:** Claude Code (Fable 5 o cualquier agente de análisis de código)
> **Proyecto:** La Web Core — La Web Figital Agency
> **Fecha:** 2026-08-04
> **Repo:** `github.com/ungardev/lawebcore`
> **Producción:** Railway (API) + Vercel (Frontend) + Supabase (DB)

---

## 1. CONTEXTO DEL PROYECTO

### ¿Qué es La Web Core?

**La Web Core** es la plataforma interna de **La Web Figital Agency** (Venezuela). Su producto estrella es **Lens** ("El Ojo que Todo lo Ve") — un sistema de descubrimiento de influencers con IA que:

1. Recibe briefs en lenguaje natural (ej: "influencers en Venezuela para Purina Dog Chow, mujeres 25-45")
2. Ejecuta un pipeline de 4 capas usando Apify para obtener datos oficiales de Instagram
3. Aplica scoring LWFA (4 KPIs exclusivos: ICA, Geo-Foco Real, Engagement Velocity, Business Intent)
4. Analiza candidatos con DeepSeek-V3 (content_quality, audience_quality, brand_fit)
5. Devuelve una lista curada de los mejores perfiles para la campaña

### Stack tecnológico
- **Frontend:** React 19 + Vite + TypeScript + Tailwind + shadcn/ui + Zustand + TanStack Query
- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0 async + asyncpg
- **DB:** PostgreSQL 16 + pgvector (Supabase Cloud) + Redis (Railway)
- **IA:** DeepSeek-V3 + fastembed (embeddings locales)
- **Scraping:** Apify (Instagram actors)
- **Infra:** Railway (API + Worker) + Vercel (Frontend)

### Arquitectura del Discovery/Lens

```
Brief (lenguaje natural)
    ↓
BriefParserAgent (DeepSeek) → BriefStructured
    ↓
ProfileGenerator (DeepSeek) → DiscoveryProfile (hashtags, keywords, geo_indicators, elite_data)
    ↓
QueryBuilder → DiscoveryPlan
    ↓
Worker (ARQ):
  STEP 1: Hashtag search (Apify) → handles
  STEP 2: Keyword search (Apify) → handles
  STEP 3: Enrich profiles (Apify) → enriched data
  STEP 4: Scoring (geo_score + lens_score + niche_relevance + anti_bot)
  STEP 5: AI Analysis (DeepSeek) → content_quality + audience_quality + brand_fit
    ↓
Top Candidates → DB (discovery_candidates)
```

### Sistema ELITE (implementado Agosto 2026)

El `profile_generator.py` ahora genera un JSON completo por brief incluyendo:
- hashtags, keywords, niche_keywords, geo_indicators, buy_intent_keywords
- **elite_data** (JSONB con 9 subcampos):
  - content_themes, audience_behavior, competitor_intel, local_slang
  - credibility_signals, niche_benchmarks, anti_bot_signals
  - geo_local_signals, query_variations

---

## 2. OBJETIVOS DEL ANÁLISIS

Analiza el proyecto completo (`/mnt/c/Users/Dainer/Documents/proyectoslaweb/lawebcore/`) y genera:

### A) OPORTUNIDADES DE MEJORA

Para cada categoría, identifica:
1. **Problemas específicos** (con archivos y líneas de código)
2. **Impacto** (alto/medio/bajo)
3. **Esfuerzo estimado** (horas)
4. **Recomendación concreta** (qué hacer)

### B) ESTABILIDAD

1. **Edge cases no manejados** — crashes potenciales, data races, excepciones no capturadas
2. **Errores de concurrencia** — race conditions, deadlocks, mutex/async issues
3. **Manejo de errores** — fallback insuficientes, errores silenciosos, logging inadecuado
4. **Tests faltantes** — qué funciones críticas no tienen cobertura

### C) EFICIENCIA

1. **N+1 queries** — selects en loops, queries innecesarias
2. **Memoria leaks** — objetos no liberados, caches sin TTL, conexiones no cerradas
3. **APIs externas** — llamadas innecesarias, falta de cache, retries mal configurados
4. **Algoritmos** — complejidad innecesaria, sorting ineficiente, filtros en lugar de índices

### D) REDUCCIÓN DE COSTOS

1. **Apify** — calls que se pueden eliminar, cache que se puede optimizar
2. **DeepSeek** — prompts que se pueden shorten, calls batching
3. **DB queries** — queries costosas que se pueden optimizar
4. **Redis** — cache misses, TTLs incorrectos

---

## 3. ARCHIVOS PRIORITARIOS PARA ANALIZAR

### Backend (Python) — Alta prioridad
```
apps/api/app/workers/worker.py          # Pipeline principal, 1018 líneas
packages/discovery/discovery/
  ├── profile_generator.py              # Elite generator, 569 líneas
  ├── candidate_analyzer.py             # AI scoring, 427 líneas
  ├── orchestrator.py                  # State machine, 632 líneas
  ├── brief_parser.py                  # Brief parsing, 370 líneas
  ├── tools/apify_client.py           # Apify client, 857 líneas
  ├── tools/geo_boost.py              # Geo scoring, 201 líneas
  └── scoring/lens_score.py            # Lens score, 95 líneas
packages/shared-core/shared_core/
  ├── supabase_rest.py                 # DB client, 434 líneas
  └── db.py                           # Session management, 80 líneas
apps/api/app/services/ai_service.py   # RAG + DeepSeek, ~400 líneas
```

### Frontend (React/TypeScript) — Media prioridad
```
apps/web/src/features/lens/
  ├── pages/LensChatPage.tsx
  ├── pages/LensSearchPage.tsx
  ├── components/BriefWizard.tsx
  ├── components/CandidateCard.tsx
  ├── hooks/useDiscoveryConversation.ts
  └── hooks/useRunPolling.ts
apps/web/src/features/campaigns/
  ├── components/KanbanColumn.tsx
  └── CampaignsListPage.tsx
```

### Base de datos (SQL) — Baja prioridad
```
supabase/migrations/
  # Solo si hay queries lentas o schema issues
```

---

## 4. PREGUNTAS ESPECÍFICAS A RESPONDER

### Estabilidad
1. ¿Qué pasa si Apify devuelve un error? ¿Hay retry? ¿Hay fallback?
2. ¿Qué pasa si DeepSeek falla durante el análisis de candidatos?
3. ¿Qué pasa si Redis está down? ¿El sistema sigue funcionando?
4. ¿Hay race conditions en el worker cuando múltiples runs corren en paralelo?
5. ¿El Orchestrator guarda su estado en memoria? ¿Se pierde en restart?

### Eficiencia
1. ¿Se están haciendo queries innecesarias a Apify? ¿El cache está bien configurado?
2. ¿El prefilter en Step 3 (antes del enrichment) es óptimo o se pueden mejorar los handles seleccionados?
3. ¿Se están usando los índices de Postgres correctamente?
4. ¿Hay N+1 queries en el código?
5. ¿Se están cerrando las conexiones a la DB correctamente?

### Costos
1. ¿Se pueden reducir las llamadas a Apify sin perder calidad?
2. ¿El batching de candidatos para DeepSeek es óptimo (actualmente 10 por batch)?
3. ¿Hay calls a Apify que se pueden cachear por más tiempo?
4. ¿Se están rastreando los costos por campaign/run?

### Scoring
1. ¿La fórmula de scoring en worker.py coincide con la documentación en result_ranker.py?
2. ¿El anti_bot filter está realmente funcionando o es código muerto?
3. ¿El candidate_analyzer está usando realmente el elite_data?

### Frontend
1. ¿Hay memory leaks en los hooks de React (especialmente useRunPolling)?
2. ¿Se están haciendo re-renders innecesarios?
3. ¿El BriefWizard tiene validaciones insuficientes?

---

## 5. FORMATO DE RESPUESTA ESPERADO

```
# Análisis La Web Core — Oportunidades de Mejora

## 1. ESTABILIDAD

### 1.1 Críticos (Alto Impacto)
| # | Problema | Archivo:Línea | Descripción | Impacto | Esfuerzo | Recomendación |
|---|----------|---------------|-------------|---------|----------|---------------|
| 1 | ... | worker.py:347 | ... | Alto | 2h | ... |

### 1.2 Medios
| # | Problema | Archivo:Línea | Descripción | Impacto | Esfuerzo | Recomendación |
|---|----------|---------------|-------------|---------|----------|---------------|

### 1.3 Menores
| # | Problema | Archivo:Línea | Descripción | Impacto | Esfuerzo | Recomendación |
|---|----------|---------------|-------------|---------|----------|---------------|

## 2. EFICIENCIA

### 2.1 Críticos
...

## 3. REDUCCIÓN DE COSTOS

### 3.1 Apify
...

### 3.2 DeepSeek
...

### 3.3 Base de datos
...

## 4. scoring

### 4.1 Inconsistencias
...

## 5. FRONTEND

### 5.1 Memory Leaks
...

### 5.2 Performance
...

## 6. TESTS FALTANTES PRIORITARIOS

| # | Test | Función a probar | Prioridad |
|---|------|------------------|-----------|

## 7. TOP 10 ACCIONES RECOMENDADAS (orden de prioridad)

1. **[Archivo]**: descripción de la acción y por qué mejora el sistema
2. ...

## 8. QUICK WINS (menor esfuerzo, mayor impacto)

1. ...
```

---

## 6. RESTRICCIONES

1. **NO sugieras cambiar el stack tecnológico** (no cambiar a Django, no cambiar a Next.js, no cambiar a PostgreSQL → MySQL, etc.)
2. **NO sugieras rewrite completo de módulos** — solo mejoras incrementales
3. **NO sugieras agregar servicios externos nuevos** (no agregar Sentry si no está, no agregar Datadog, etc.)
4. **SÍ puedes sugerir** agregar tests, cache,índices, mejores manejo de errores, optimizaciones de queries, refactors pequeños
5. **El presupuesto es limitado** — prioriza acciones de alto impacto y bajo esfuerzo

---

## 7. CONTEXTO DE NEGOCIO

- **Usuario principal:** Agencias de marketing en Venezuela/LATAM
- **Caso de uso:** Encontrar influencers para campañas de marketing
- **Presupuesto:** $250 USD/mes ($200 APIs + $50 infra)
- **Meta:** 10-30 discovery runs/mes
- **Apify plan actual:** STARTER ($50/mes) — límite de uso fácilmente alcanzable
- **Meta de costo por campaign:** <$0.30 con cache

---

## 8. INSTRUCCIONES

1. **Lee todo el código relevante** listando en la sección 3
2. **Ejecuta análisis estático** del código
3. **Identifica problemas específicos** con文件名 y número de línea
4. **Estima esfuerzo** en horas-hombre
5. **Prioriza** por impacto × esfuerzo
6. **Genera recomendaciones concretas** que se puedan implementar en 1-2 horas máximo por item
7. **Para cada recomendación**, incluye:
   - Qué cambiar
   - En qué archivo
   - Por qué mejora (estabilidad/eficiencia/costo)
   - Código de ejemplo si es posible

---

*Prompt generado: 2026-08-04*
*Para uso con Claude Code Fable 5 o cualquier agente de análisis de código*
