# Prompt para Claude Code Opus 5 — Análisis y Ejecución de Apify

## Contexto

Este es el repositorio privado `lawebcore` (https://github.com/ungardev/lawebcore) — una aplicación de influencer marketing para La Web Figital Agency (Venezuela). Tiene un frontend React + Vite + Tailwind v3, un backend FastAPI, y un paquete Python `packages/discovery` que usa DeepSeek y Apify para descubrir influencers.

El sistema ya tiene un discovery flow funcional (mockup) con Purina Dog Chow y Nescafe Dolce Gusto, pero el **flujo real con Apify no está configurado**. La API Key de Apify existe en algún lado de `.env` (no confirmado) y necesitamos hacerla funcionar para **extraer 15-20 perfiles reales de Instagram** que coincidan con la estrategia de campaña.

## Objetivo

1. **Explorar todo el proyecto** en modo "alto" — leer los archivos clave, entender la estructura
2. **Localizar la API Key de Apify** — buscar en `.env`, `.env.example`, configs, código
3. **Hacer funcionar el flujo de Apify** — ejecutar el discovery run real, no el mockup
4. **Extraer 15-20 perfiles reales** de Instagram para:
   - Primer caso: **Busco influencers para Purina Dog Chow en Instagram Venezuela. Perfiles nano, micro y mid. Presupuesto 10K USD.**
   - Segundo caso: **Busco influencers para Nescafe Dolce Gusto en Instagram Venezuela. Perfiles nano, micro y mid.**

## Estado actual relevante

### Estructura clave
- `packages/discovery/discovery/orchestrator.py` — state machine con detección especial para Purina (mockup) y Dolce Gusto (carga desde DB).
- `packages/discovery/discovery/query_builder.py` — construye queries por plataforma (IG, TikTok, YouTube).
- `packages/discovery/discovery/tools/` — clients de Apify, Meta, Metricool, TikTok, YouTube.
- `packages/discovery/discovery/worker.py` — background job que ejecuta queries.
- `packages/shared-core/shared_core/supabase_rest.py` — HTTP client para Supabase REST API.
- `packages/shared-core/shared_core/config.py` — settings (probablemente tiene API keys).

### Bugs conocidos a ignorar (fuera de scope)
- Redis/ARQ no disponible — el orchestrator puede colgarse en "Pensando..." si Redis no está, pero los flujos Purina y Dolce Gusto ya están arreglados con mockup.
- Polling timeout sin UI update — bug del frontend, fuera de scope.

## Tareas específicas

### 1. Análisis del proyecto (HIGH)

Lee y entiende:
- `apps/api/app/api/v1/discovery.py` — endpoints REST
- `apps/api/app/workers/worker.py` — background worker
- `packages/discovery/discovery/orchestrator.py` — orchestrator completo
- `packages/discovery/discovery/tools/apify_client.py` — client de Apify (probablemente ya existe)
- `packages/discovery/discovery/query_builder.py` — cómo construye queries
- `packages/discovery/discovery/result_ranker.py` — scoring
- `supabase/migrations/00000000000021_discovery_recovery.sql` — schema
- `supabase/migrations/00000000000025_import_nescafe_dolce_gusto_influencers.sql` — ejemplo de import

### 2. Localizar API Key de Apify

Busca en:
- `apps/api/.env` — si existe
- `packages/discovery/.env` — si existe
- `.env` en root
- `packages/shared-core/shared_core/config.py` — settings
- `docker-compose.yml` / `docker-compose.yaml`
- Cualquier archivo de config

Si NO encuentras la API Key, pregunta al usuario cómo obtenerla o si debe configurarla en `.env`.

### 3. Hacer funcionar el flujo de Apify

Deberías poder:

a) **Verificar la API Key de Apify** con un test call (ej: `GET https://api.apify.com/v2/users/me`).

b) **Ejecutar un hashtag search** en Instagram Venezuela con hashtags relevantes para Purina Dog Chow:
   - `#purina`
   - `#dogchow`
   - `#mascotasVE`
   - `#perrosVE`
   - `#mascotasvenezuela`
   - `#petlovers`
   - `#doglover`

c) **Para Dolce Gusto**:
   - `#dolcegusto`
   - `#nescafe`
   - `#caféVE`
   - `#caféencasa`
   - `#momentodepausa`
   - `#cocinaVE`

d) **Filtrar** los resultados por:
   - País: Venezuela
   - Followers: 1K - 500K (cubrir nano, micro, mid)
   - Engagement rate: > 2%

e) **Rankear** con `result_ranker.rank()` aplicando el brief de la campaña.

### 4. Extraer 15-20 perfiles

Para cada uno de los dos casos (Purina y Dolce Gusto), extraer **15-20 influencers reales** de Instagram Venezuela. Los resultados deben:

- Estar en `discovery_candidates` con su `run_id` correspondiente
- Tener `match_score`, `niche_relevance`, `geo_relevance`, `audience_relevance`, `content_quality`
- Tener `rationale` generado
- Tener `avatar_url` real (URL de Instagram)
- Tener `engagement_rate` calculado

### 5. Persistir en la DB

Insertar los resultados en `discovery_candidates` con un `run_id` real (crear un `discovery_run` primero con `brief_parsed` poblado).

Si la DB no está accesible, al menos guardar los resultados en un JSON local en `tmp/apify_results.json` para que sean importables después.

### 6. Verificar el flujo end-to-end

Una vez extraídos los 15-20 perfiles:

- El usuario podrá invocar el flow desde la UI:
  ```
  "Busco influencers para Purina Dog Chow en Instagram Venezuela. Perfiles nano, micro y mid. Presupuesto 10K USD."
  ```
- Pero **bypaseando** el mockup de Purina para que use los datos reales de Apify (no los mockup de `MOCKUP_RUN_ID`).

**OJO**: los mockups de Purina y Dolce Gusto siguen siendo útiles para demos. NO los elimines. En lugar de eso, crea un **modo "real"** distinto para cuando la API Key de Apify esté configurada.

### 7. Estrategia de testing

Si no puedes conectar a Apify directamente (por falta de API Key o por falta de red en sandbox), documenta bien los pasos exactos que el usuario debe ejecutar localmente con su `.env` configurado.

## Plan de implementación sugerido

1. `git clone` (si aplica) o leer el repo público
2. Leer todos los archivos clave
3. Buscar API Key de Apify
4. Test de conexión a Apify
5. Identificar el actor de Apify para Instagram hashtag search (sugerir: `apify/instagram-hashtag-scraper`)
6. Escribir un script standalone `packages/discovery/scripts/extract_purina_apify.py` que:
   - Hace el hashtag search
   - Filtra VE
   - Calcula engagement
   - Inserta en `discovery_candidates`
7. Ejecutar el script
8. Verificar resultados
9. Commit + push

## Entregables

Al final del trabajo, el reporte debe incluir:

- ✅ Estado de la API Key de Apify (encontrada o no)
- ✅ Resultado de la extracción: cuántos perfiles se encontraron para Purina, cuántos para Dolce Gusto
- ✅ Archivos modificados para hacer funcionar el flujo real
- ✅ Un `discovery_runs` creado para cada caso con `run_id` real
- ✅ `discovery_candidates` poblados con 15-20 perfiles por caso
- ✅ Cualquier fix necesario en el orchestrator para que el flujo real funcione

## Consideraciones importantes

- **NO elimines** los mockups de Purina ni Dolce Gusto — son útiles para demos
- **NO commitees** la API Key de Apify al repo
- **USA** `.env` para la API Key, y crea un `.env.example` documentando las variables necesarias
- **DOCUMENTA** cualquier paso manual que el usuario deba ejecutar (ej: configurar Supabase URL, run migrations, etc.)
- **SEPACOMO** los scripts de extracción deben ser idempotentes (re-ejecutables sin duplicar datos)

## Output esperado

Al finalizar, reporta:

1. Resumen ejecutivo (10 líneas)
2. Resultado de la extracción Purina Dog Chow (lista de handles encontrados)
3. Resultado de la extracción Nescafe Dolce Gusto (lista de handles encontrados)
4. Commits realizados con mensajes
5. Próximos pasos / TODOs para el usuario

---

**IMPORTANTE**: El repositorio es privado normalmente pero el usuario lo hará público SOLO durante este análisis. No asumas que va a seguir público.
