# Prompt para Claude Code Opus 5 — Análisis y Ejecución de Apify Real para Purina Dog Chow

## Contexto

Este es el repositorio `lawebcore` (https://github.com/ungardev/lawebcore) — una aplicación de influencer marketing para La Web Figital Agency (Venezuela). Tiene un frontend React + Vite + Tailwind v3, un backend FastAPI, y un paquete Python `packages/discovery` que usa DeepSeek y Apify para descubrir influencers.

**Estado actual del proyecto**: El orchestrator ya usa la vía real de Apify — no hay mockups. El flujo `pending_discovery: True` encola un job en Redis/ARQ para ejecutar el pipeline completo de 4 capas (keyword discovery → hashtag deep dive → profile enrichment → engagement analytics → LWFA scoring).

El proyecto tiene un caso demo funcionando con **Purina Dog Chow** y se quiere usar este flow real para extraer 15-20 perfiles reales de Instagram Venezuela.

**Todas las environment variables están cargadas en Railway**, incluyendo:
- `APIFY_API_KEY` — disponible
- `DATABASE_URL` — disponible (Supabase)
- `ARQ_REDIS_URL` — **hay que verificar si está disponible** (crítico para el flow)

## Objetivo

1. **Explorar todo el proyecto** en modo "alto" — leer los archivos clave, entender la estructura completa
2. **Diagnosticar Redis/ARQ en Railway** — esto es PRIORIDAD #1. Sin Redis, el flow `pending_discovery` se cuelga 120s.
3. **Ejecutar el pipeline real de Apify** para extraer 15-20 perfiles reales de Instagram Venezuela para Purina Dog Chow
4. **Verificar el flujo end-to-end** — desde el prompt en la UI hasta los candidatos visibles en pantalla

## Estado actual relevante

### Estructura clave
- `packages/discovery/discovery/orchestrator.py` — State machine LangGraph. Cuando el usuario confirma un brief, pone `pending_discovery: True` y el API encola un job en Redis.
- `packages/discovery/discovery/query_builder.py` — Construye `DiscoveryPlan` con keywords y hashtags basados en el brief. Tiene `DISCOVERY_KEYWORDS` pre-configurados para Purina Dog Chow.
- `packages/discovery/discovery/tools/apify_client.py` — Cliente Apify API v2 con cache Redis y retry.
- `packages/discovery/discovery/worker.py` — Worker ARQ con pipeline de 4 capas:
  - Step 1: keyword discovery (`instagram-search-scraper`)
  - Step 2: hashtag deep dive (`instagram-hashtag-scraper`)
  - Step 3: profile enrichment (`instagram-profile-scraper`)
  - Step 4: engagement analytics (actor de engagement)
- `apps/api/app/api/v1/discovery.py` — Endpoint `POST /conversations/{id}/messages`. Si `pending_discovery: True`, encola job con `enqueue_discovery_run()`.
- `apps/api/app/workers/worker_enqueuer.py` — Encola jobs en Redis. Retorna `False` si Redis no está disponible pero el caller ignora el retorno.
- `scripts/extract_purina_real_apify.py` — Script standalone que ejecuta Apify directamente y persiste candidatos. Ya existe, usar como referencia.
- `packages/discovery/discovery/brief_parser.py` — System prompt con contexto de Purina Dog Chow. Tono: emocional, dueños responsables, comunidad de amantes de mascotas.

### Scripts existentes
- `scripts/seed_purina.py` — Seed con 20 influencers demo (NICRO/MID) + publicaciones. Uso: seed inicial de datos demo.
- `scripts/extract_purina_real_apify.py` — Script de extracción Apify real ya creado. Ejecutar este o replicar su lógica en el worker.

### Database (Supabase)
- `discovery_runs` — Guarda el brief parseado + estado del run
- `discovery_candidates` — Candidatos con scores LWFA
- `influencers` + `influencer_social_accounts` + `influencer_metrics_snapshot` — Base de datos de influencers

## PRIORIDAD #1 — Diagnosticar Redis/ARQ en Railway

**Esto es crítico antes de hacer cualquier otra cosa.**

El flow actual depende de que Redis esté corriendo para encolar jobs de ARQ. Si Redis no está disponible:
1. El API llama `enqueue_discovery_run()` → retorna `False` silenciosamente
2. El API retorna `discovery_run_id` al frontend de todas formas
3. El frontend pollpea por 120 segundos sin que el worker nunca se ejecute
4. UI queda en "Pensando..." para siempre

**Pasos a ejecutar primero**:

1. Verificar si Redis/ARQ está configurado en Railway:
   - Buscar en Railway dashboard:是否有 Redis addon configurado?
   - O ejecutar desde la Railway web console (o locally con las vars):
     ```bash
     python -c "import redis; r = redis.from_url('redis://...'); print(r.ping())"
     ```

2. Si Redis NO está disponible, hay dos caminos:
   - **Opción A (recomendada)**: Hacer que el orchestrator detecte si un `discovery_run` ya tiene candidatos en `discovery_candidates` y los retorne directamente, sin depender de Redis. Crear un path "sync" que inserte candidatos directamente.
   - **Opción B**: Agregar Redis al stack de Railway (más complejo, más costo)

3. Si Redis SÍ está disponible: verificar que el worker de ARQ esté corriendo y procesando jobs.

**Reporte esperado**: ¿Redis está disponible? ¿El worker de ARQ está corriendo? Si no, ¿cuál es el plan?

## Tareas específicas

### 1. Análisis del proyecto (HIGH)

Leer y entender todos estos archivos:
- `apps/api/app/api/v1/discovery.py`
- `apps/api/app/workers/worker.py`
- `apps/api/app/workers/worker_enqueuer.py`
- `packages/discovery/discovery/orchestrator.py`
- `packages/discovery/discovery/tools/apify_client.py`
- `packages/discovery/discovery/query_builder.py`
- `packages/discovery/discovery/result_ranker.py`
- `packages/discovery/discovery/memory.py`
- `scripts/extract_purina_real_apify.py`
- `supabase/migrations/00000000000021_discovery_recovery.sql`

### 2. Diagnosticar Redis/ARQ (PRIORIDAD #1)

1. Buscar en Railway dashboard si hay Redis addon
2. Verificar `ARQ_REDIS_URL` en las env vars de Railway
3. Probar conexión Redis
4. Verificar si el worker de ARQ está corriendo
5. Reportar estado y proponer opción A o B

### 3. Hacer funcionar el flujo Apify real

Una vez diagnosticado Redis:

**Si Redis está disponible**:
- El flow ya debería funcionar end-to-end con el worker existente
- Ejecutar el script `scripts/extract_purina_real_apify.py` para poblar la DB con candidatos reales
- O hacer una búsqueda real desde la UI y verificar que el polling traiga candidatos

**Si Redis NO está disponible (Opción A)**:
- Modificar el orchestrator o el endpoint API para que, cuando `pending_discovery: True`:
  1. Cree el `discovery_run` en la DB
  2. Ejecute el pipeline de Apify SINCRONICAMENTE (sin Redis, en el mismo request o con un thread pool)
  3. Inserte los candidatos en `discovery_candidates`
  4. Retorne los candidatos inmediatamente al frontend
  5. No depender de Redis para nada
- O usar el script `extract_purina_real_apify.py` directamente para poblar la DB primero, y luego el flow de la UI puede leerlos con polling normal contra la DB

**Verificar API Key de Apify**:
```bash
curl -H "Authorization: Bearer $APIFY_API_KEY" https://api.apify.com/v2/users/me
```

### 4. Extraer 15-20 perfiles reales de Purina Dog Chow

Hashtags relevantes:
- `#purinaVE`, `#dogchowVE`, `#amorporruno`, `#mascotasVE`, `#perrosVE`
- `#dogChow`, `#purina`, `#petlovers`, `#doglover`

Keywords relevantes:
- `PurinaVE`, `DogChowVE`, `mascotasVE`, `perrosVenezuela`

Filtros:
- País: Venezuela (geotags, bio, username)
- Followers: 1K - 500K (NANO + MICRO + MID)
- Engagement rate: > 2% (de posts recientes)

Scoring:
- LWFA composite score ya existe en `result_ranker.py`
- Calcular engagement rate de `latestPosts` en profile enrichment

### 5. Persistir en la DB

Crear un `discovery_run` con:
- `brief_parsed`: `{product_name: "Purina Dog Chow", niches: ["mascotas", "perros"], audience_countries: ["VE"], platforms: ["instagram"], ...}`
- `status`: `completed`

Insertar `discovery_candidates` con:
- `run_id` del nuevo run
- `handle`, `avatar_url`, `followers`, `engagement_rate`, `match_score`
- `rationale` generado
- `status`: `new`

### 6. Verificar flujo end-to-end

1. Ir a la UI: `/influencer-lens`
2. Enviar: `"Busco influencers para Purina Dog Chow en Instagram Venezuela. Perfiles nano, micro y mid. Presupuesto 10K USD."`
3. Confirmar brief
4. Esperar candidatos (debe completar en < 2 minutos, NO 120s de polling)
5. Verificar que las tarjetas muestren:
   - Avatar real (de Instagram)
   - Handle
   - Followers
   - Engagement rate
   - Score
   - Botones Guardar / Descartar

### 7. Iterar hasta que funcione

Si algo falla:
1. Diagnostica el punto exacto de falla
2. Arregla o reporta
3. Vuelve a ejecutar
4. Repite hasta que el flow completo funcione

## Entregables

Al final del trabajo:

- ✅ Estado de Redis/ARQ (disponible o no, y plan)
- ✅ 15-20 candidatos reales de Instagram Venezuela para Purina Dog Chow en `discovery_candidates`
- ✅ Un `discovery_run` creado y poblado en la DB
- ✅ Flujo end-to-end funcionando desde la UI
- ✅ Archivos modificados
- ✅ Commits con mensajes descriptivos

## Consideraciones importantes

- **USA** el script `scripts/extract_purina_real_apify.py` como referencia para el pipeline Apify
- **EJECUTA** el script o replica su lógica directamente — el objetivo es tener candidatos reales en la DB
- **NO commitees** API keys al repo
- **El flow debe funcionar sin hanging de 120 segundos** — si Redis no está, implementar la Opción A (sync execution)
- **Los candidatos deben tener avatar_url real** — los mockups no tienen avatar (muestran iniciales)
- **El frontend muestra "Pensando..."** cuando `pending_discovery: True` y polling no recibe respuesta — si el run se completa en < 30s con sync execution, el polling recibe los candidatos y la UI responde correctamente

## Output esperado

Al finalizar, reporta:

1. Resumen ejecutivo (10 líneas)
2. Estado de Redis/ARQ + decisión (Opción A o B)
3. Lista de handles encontrados para Purina Dog Chow (15-20)
4. Flujo end-to-end: ¿funciona desde la UI?
5. Archivos modificados + commits
6. Próximos pasos para dejar el proyecto funcionando en producción

---

**IMPORTANTE**: El repositorio es privado pero el usuario lo hará público SOLO durante este análisis. No asumas que va a seguir público.
