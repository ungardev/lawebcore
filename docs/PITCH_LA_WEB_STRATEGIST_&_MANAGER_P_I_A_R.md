# P.I.A.R.

## Plataforma de Proyección de Influencer Marketing

**Hub interno para el área P.I.A.R. de La Web Figital Agency**

v0.1.0 (MVP) · Julio 2026

> *"El cerebro analítico interno para campañas de influencer marketing,
> construido sobre datos 100% propios, sin depender de herramientas externas de pago."*

---

## 1. Resumen ejecutivo

**P.I.A.R.** (Plataforma de Proyección de Influencer Marketing) es la funcionalidad de inteligencia analítica para campañas de influencer marketing, integrada dentro de **La Web Core**, el sistema operativo de La Web Figital Agency. Fue diseñada para que el equipo P.I.A.R. tenga su propio **HypeAuditor interno**: analítica construida exclusivamente sobre datos propios de la agencia, sin suscripciones a herramientas externas como HypeAuditor, Modash o similar.

El producto reemplaza el hub anterior (**Influencer Strategist & Manager — ISM**), cuya auditoría técnica documentada identificó 7 bugs críticos que impedían operar con confianza. P.I.A.R. resuelve cada uno de ellos y añade capacidades que el ISM nunca tuvo: proyección de campañas en 3 escenarios, scoring accionable contra benchmarks propios del mercado venezolano/LATAM, análisis de sentimiento con IA generativa y un asistente conversacional con memoria contextual.

Hoy vive en `https://www.lawebfigitalagency.com/hub` y gestiona datos de **14 clientes, 25 marcas y 32 campañas** con cerca de 1.700 publicaciones migradas del sistema anterior.

---

## 2. El problema que resolvemos

### 2.1 Dependencia de herramientas externas

Antes de P.I.A.R., el equipo de influencer marketing de la agencia dependía de herramientas SaaS pagadas (HypeAuditor, Modash, y similares) para obtener métricas de influencers y benchmarking. Esto implicaba:

- **Costo recurrente** sin control sobre los datos ni la metodología.
- **Metodologías opacas** — los scores y benchmarks eran genéricos, no calibrados al mercado venezolano ni al tipo de campañas que ejecuta la agencia.
- **Datos dispersos** — las métricas de las herramientas externas no se integraban con el CRM ni con el repositorio interno de campañas.

### 2.2 El estado del ISM legacy

El sistema anterior (Influencer Strategist & Manager, el precursor de La Web Core) presentaba fallos que la auditoría técnica de enero 2026 documentó exhaustivamente:

| Bug | Descripción |
|-----|-------------|
| **C-01** | El parser de CSV solo entendía encabezados en inglés y descartaba silenciosamente cualquier CSV en español. |
| **C-02** | `campaign_id` nunca se asignaba al importar publicaciones → miles de registros huérfanos sinCampaign assigned. |
| **C-03** | Los KPIs derivados (ER, V/F ratio, retención) no se calculaban nunca. |
| **C-04** | El campo `raw_data` se guardaba siempre como `{}` vacío. |
| **C-05** | Los gráficos de Recharts recibían width/height negativos y no renderizaban. |
| **C-06** | La pestaña "Performance" del dashboard leía de 3.5M de publicaciones; "Overview", de 0. |
| **C-07** | Los NULL en scoring se reemplazaban por default `0` → score 2.00 inválido para todos los NULL. |

El equipo operaba con datos incompletos, sin poder confiar en las proyecciones ni en los dashboards.

### 2.3 La decisión de construir P.I.A.R.

La auditoría del ISM no era reparable con parches: el schema mismo estaba corrupto y el stack (Vue 2 + Node + monetización) no daba para escalar. Se tomó la decisión de reconstruir desde cero sobre el stack moderno de La Web Core (FastAPI + React + Supabase), con una arquitectura pensada para evolver a producto maduro.

---

## 3. Qué es P.I.A.R.

### 3.1 Definición

P.I.A.R. es la funcionalidad de **proyección e inteligencia de campañas de influencer marketing** integrada dentro de La Web Core. No es un producto standalone: es el módulo analítico del hub operativo de la agencia.

Su nombre se trata como un acrónimo de 4 letras (proper-noun) y no se expande formalmente. Su tagline interna: *"El hype auditor interno de la agencia."*

### 3.2 Diferenciadores clave

| Diferenciador | Qué significa en la práctica |
|---|---|
| **Datos 100% propios** | Toda la analítica se calcula sobre publications ingestadas por el equipo. No se compra ni se依赖于 herramientas externas para los números que importan. |
| **Benchmarks LWFA** | Los scores de influencers se comparan contra 9 sub-tiers del mercado venezolano/LATAM, calibrados por La Web Figital Agency, no contra promedios genéricos de la industria. |
| **Motor de proyección 3 escenarios** | Por primera vez, el equipo puede presentar a un cliente una proyección de alcance/engagement en modo conservador, base y optimista, con la metodología completa auditable. |
| ** scoring accionable** | Cada influencer recibe una decisión: ESCALAR, OPTIMIZAR, DESCARTAR o DATOS_INSUFICIENTES. No más scores vagos. |
| **IA generativa integrada** | Sentiment analysis sobre comentarios (DeepSeek) + asistente conversacional con RAG sobre la base de conocimiento de la agencia. |

### 3.3 Arquitectura de datos

```
Publications (CSV/JSON/Sheets)
        ↓
  ETL Pipeline (normalización)
        ↓
  ┌─────┴─────┐
  │  P.I.A.R. Engine   │
  │ - Proyección       │
  │ - Scoring          │
  │ - Sentiment        │
  │ - AI Assistant     │
  └──────────┬─────────┘
             ↓
       Supabase DB
       (Postgres 16 + pgvector)
             ↓
       Dashboard (React)
```

---

## 4. Funcionalidades del MVP

El MVP (`v0.1.0`) cubre el flujo completo desde la ingestión de datos hasta la proyección y el scoring. Las funcionalidades están agrupadas en 8 áreas:

### 4.1 Dashboard ejecutivo

**Propósito:** dar visibilidad al equipo sobre el estado de todas las campañas.

- 11 KPIs operativos: reach, engagement, ER, vistas, retención, V/F ratio, coste por engagement, etc.
- 2 gráficos interactivos (tendencia de engagement y comparativa de performance por campaña).
- Filtros por cliente, marca y rango de fechas.
- Tabs "Performance" y "Overview" ahora leen de la misma fuente de datos (bug C-06 resuelto).

### 4.2 Proyección de campañas — El corazón de P.I.A.R.

**Propósito:** generar proyecciones de alcance y engagement para nuevas campañas, con 3 escenarios, antes de presentar la propuesta al cliente.

**Metodología:**

1. El equipo ingresa la cantidad de posts planeados por cada tier (NANO / MICRO / MID / MACRO).
2. El motor busca el histórico de la marca en la base de datos.
3. **Si la marca tiene ≥3 campañas previas** → usa su propio histórico (más preciso).
4. **Si tiene menos de 3 campañas** → hace **fallback automático al sector industrial** de la marca (metodología aprobada por el equipo).
5. Calcula un promedio ponderado por tiempo: peso 1.5 para campañas <6 meses de antigüedad, peso 1.0 para las más antiguas.
6. Genera **3 escenarios automáticamente**:

| Escenario | Factor | Cuándo usarlo |
|---|---|---|
| **Conservador** | ×0.75 | Cliente conservador o mercado inestable |
| **Base** | ×1.0 | Projection neutra |
| **Optimista** | ×1.30 | Cliente optimista o fecha previa a fecha peak |

Cada número del output es **auditable**: se puede rastrear hasta el histórico específico o el benchmark de sector que lo generó.

### 4.3 Scoring accionable de influencers

**Propósito:** evaluar cada creador en 3 dimensiones y producir una decisión clara para el equipo.

**Las 3 dimensiones:**

| Dimensión | Lógica |
|---|---|
| **Retención** | >10s = 3 pts / 6–10s = 2 pts / <6s = 1 pt |
| **Engagement** | Comparado contra benchmark LWFA del sub-tier correspondiente |
| **Viralidad** | Ratio V/F (vistas vs. favoritos) — booleano |

**Score** = promedio de las 3 dimensiones (0–3).

**Decisión:**

| Score | Decisión | Significado |
|---|---|---|
| ≥ 2.5 | **ESCALAR** | Merece más inversión en la campaña |
| 1.8 – 2.5 | **OPTIMIZAR** | Incluir con ajustes (ej. más contenido, target diferente) |
| < 1.8 | **DESCARTAR** | No es el creador adecuado para esta campaña |
| NULL | **DATOS_INSUFICIENTES** | No hay datos para evaluar (no se forza un 0 como el ISM) |

**Benchmarks propios:** 9 sub-tiers del mercado venezolano/LATAM, construidos por LWFA con datos propios. No son genéricos de la industria.

### 4.4 Análisis de sentimiento con IA

**Propósito:** clasificar automáticamente los comentarios de cada publicación en 4 categorías de sentimiento.

**Implementación:** integración con DeepSeek (LLM) a través de una pipeline que:
1. Recibe los comentarios de una publicación.
2. Los envía al LLM con un prompt estructurado.
3. Recibe la clasificación en 4 categorías: `positivo`, `negativo`, `neutral`, `mixto`.
4. Almacena el resultado en la tabla `comentarios_analizados`.

> La categoría se usa luego para calcular el **sentiment score** de cada publicación y de cada campaña. Es el primer paso hacia un reporting que incluye la calidad de la conversación, no solo las métricas de alcance.

### 4.5 Asistente IA conversacional (RAG)

**Propósito:** permitir que cualquier miembro del equipo consulte la base de conocimiento de P.I.A.R. en lenguaje natural.

**Cómo funciona:**
- Un indexador RAG corre periódicamente sobre los documentos de la base de conocimiento de la agencia (migrations, scripts, documentación).
- Los embeddings se almacenan en **pgvector** (Supabase).
- El asistente recibe la pregunta del usuario, busca los chunks más relevantes, y responde con las fuentes citadas.

### 4.6 Ingesta universal de datos

**Propósito:** permitir que el equipo cargue publications desde cualquier fuente sin fricción.

Formatos soportados:
- **CSV en español** — con mapeo de columnas `COLUMN_MAP_ES` (bug C-01 resuelto).
- **CSV en inglés** — con mapeo `COLUMN_MAP_EN`.
- **JSON Data Contract** — schema estricto con `campaign_id` obligatorio (bug C-02 resuelto).
- **Formulario manual** — para entradas ad-hoc.
- **Google Sheets** — importación directa.

Cada fila pasa por `normalizar_fila()`, que calcula automáticamente los KPIs derivados (bug C-03 resuelto) y valida que `raw_data` no venga vacío (bug C-04 resuelto).

### 4.7 Pipeline Kanban

**Propósito:** gestionar el flujo operativo de las campañas con estados definidos.

- 4 columnas: IDEAS / EN PROGRESO / COMPLETADO / CANCELADO.
- Drag-and-drop con **rollback de 5 segundos** si se suelta en la columna incorrecta.
- Filtros por BU y estado.

### 4.8 RBAC granular (control de accesos)

**Propósito:** que cada miembro del equipo vea y pueda actuar solo sobre lo que le corresponde.

- **10 roles** preconfigurados.
- **27 permisos granulares** organizados en 7 clusters.
- **Row-Level Security (RLS)** activo en las 40 tablas de la base de datos.
- **Multi-BU** (8 unidades de negocio), incluyendo una BU dedicada a P.I.A.R.
- Cada usuario tiene uno o más roles asignados.

---

## 5. Stack tecnológico

| Componente | Stack | Version |
|---|---|---|
| **Frontend** | React + Vite + TypeScript + Tailwind CSS + shadcn/ui + Recharts | React 19 |
| **Backend** | FastAPI (Python 3.12, async) + SQLAlchemy 2.0 + Pydantic v2 | FastAPI 0.115 |
| **Base de datos** | Supabase (Postgres 16 + Auth + Storage) | Postgres 16 |
| **IA / RAG** | LangChain + pgvector + OpenAI/DeepSeek | pgvector 0.8 |
| **Infraestructura** | Vercel (frontend) + Railway (API + workers + Redis) + Supabase Cloud | — |

**Decisiones de arquitectura destacadas:**
- **Async everywhere:** el backend es 100% async para soportar la cola de jobs (sentiment, RAG indexing).
- **Service role vs. JWT:** Supabase Auth (JWT) para usuarios; service_role solo en backend para operaciones privilegiadas.
- **pgvector para RAG:** embeddings almacenados directamente en Supabase, sin servicio externo.
- **Redis en Railway:** cola de jobs para operaciones pesadas (sentiment analysis, importación masiva).

---

## 6. Modelo operativo

### 6.1 Roles del equipo P.I.A.R.

| Rol | Descripción | Ejemplo de usuarios |
|---|---|---|
| `admin_general` | Acceso total al sistema | Dainer Calderón, Cristóbal Gallardo, Ignacio Chacón |
| `analista` | Lectura de KPIs, reportes, benchmarks | Equipo de datos |
| `project_manager` | Gestión de campañas, flujos | Equipo de proyectos |
| `influencer_liaison` | Gestión de relaciones con creadores | — |
| `account_manager` | Gestión de clientes y marcas | — |
| `viewer` | Solo lectura | Stakeholders externos |
| `creador_contenido` | Creación y edición de contenido | — |
| `soporte` | Soporte técnico nivel 1 | — |
| `marketing` | Acceso a campañas y métricas de marketing | — |
| `finance` | Acceso a métricas financieras de campañas | — |

### 6.2 Flujo operativo típico

```
[ 1. El equipo importa publications ]
        ↓
[ 2. Motor calcula sentiment + scoring automáticamente ]
        ↓
[ 3. Dashboard se actualiza con KPIs ]
        ↓
[ 4. Equipo prepara nueva campaña ]
        ↓
[ 5. Motor genera proyección en 3 escenarios ]
        ↓
[ 6. Proposal lista para presentar al cliente ]
```

### 6.3 Multi-BU

8 unidades de negocio configuradas en el sistema, incluyendo una dedicada al equipo P.I.A.R. Cada BU tiene sus propios permisos y alcance de datos.

---

## 7. Datos y migración desde ISM

### 7.1 Volumen de datos sembrados

| Métrica | Valor |
|---|---|
| Clientes | 14 (Nestlé, PepsiCo, Polar, Mobilnet, OREO, Nescafé, y otros) |
| Marcas | 25 |
| Campañas históricas | 32 |
| Publicaciones migradas del ISM legacy | ~1.698 |
| Unidades de negocio (BU) | 8 |
| Roles configurados | 10 |
| Permisos granulares | 27 |
| Definiciones de KPI | 7 (reach, engagement, ER, vistas, retención, V/F, coste por engagement) |
| Sub-tiers de benchmark LWFA | 9 |

### 7.2 Continuidad operativa

La migración se ejecutó con un script ETL idempotente (`etl_ism_backfill.py`) que:
- Parseaba el dump del ISM (Postgres → JSON → Normalized).
- Validaba cada fila contra el Data Contract actual.
- Insertaba con `ON CONFLICT DO NOTHING` para permitir re-ejecución sin duplicados.

**El equipo no perdió histórico.** Las ~1.698 publicaciones están disponibles en P.I.A.R. desde el día 1.

---

## 8. Beneficios operativos vs. ISM

Esta es la tabla que resume, para cada bug del ISM, qué hacía antes y qué hace ahora.

| Bug | Antes (ISM) | Ahora (P.I.A.R.) |
|-----|-------------|------------------|
| **C-01** — Parser CSV | Solo mapeaba encabezados en inglés → descartaba silenciosamente CSVs en español | Mapeo bilingüe automático (`COLUMN_MAP_ES` + `COLUMN_MAP_EN`) |
| **C-02** — campaign_id | `campaign_id` nunca se asignaba → registros huérfanos | `campaign_id` obligatorio en el Data Contract; sin él, la fila se rechaza |
| **C-03** — KPIs derivados | ER, V/F, retención no se calculaban | Calculados automáticamente en `normalizar_fila()` |
| **C-04** — raw_data | Se guardaba siempre como `{}` vacío | Campo obligatorio en el JSON contract |
| **C-05** — Gráficos | Recharts recibía width/height = -1 → no renderizaba | `ResponsiveContainer` bien configurado |
| **C-06** — Consistencia de tabs | "Performance" leía 3.5M pubs; "Overview", 0 | Ambas tabs leen de `publicaciones` (single source of truth) |
| **C-07** — Scoring NULL | NULL → default 0 → score 2.00 inválido para todos | `calcular_decision()` retorna explícitamente `DATOS_INSUFICIENTES` |

---

## 9. Alcance v1 — Lo que P.I.A.R. NO hace (intencionalmente)

| Funcionalidad | Razón |
|---|---|
| Generación automática de reporte a cliente (PDF/PPT) | El reporting a cliente sigue siendo un proceso consultivo y manual; se entrega como propuesta personalizada |
| Discovery de nuevos influencers (scraping Apify) | Proyecto separado, pausado por decisión de scope |
| Edición de histórico desde UI | Los datos de publications son inmutables una vez publicados; mantienen trazabilidad |
| Multi-tenant / SSO empresarial | Fase 4 del roadmap |
| Integración directa con Meta Graph API / TikTok API | Definida en el diseño, no implementada aún |

---

## 10. Seguridad

| Mecanismo | Implementación |
|---|---|
| **Autenticación** | Supabase Auth con JWT; cambio de contraseña self-service vía `/settings` |
| **Autorización** | RBAC con 10 roles y 27 permisos; RLS activo en las 40 tablas |
| **Service role** | Solo en backend; nunca expuesto al cliente |
| **Auditoría** | Tabla `audit_logs` captura logout y cambios de estado de campañas |
| **RLS por BU** | Cada query de Supabase filtra por la BU del usuario autenticado |

---

## 11. Infraestructura y despliegue

### 11.1 Arquitectura de producción

```
Usuario
   ↓
lawebfigitalagency.com/hub
   → Vercel (React, CDN, auto-deploy from main)
   ↓
FastAPI Backend
   → Railway (Docker, auto-restart, escala automáticamente)
   ↓
┌──────┴──────┐
Supabase         Redis
(Postgres 16)    (Railway)
• Auth           • Cola de jobs
• Storage        • Sentiment workers
• pgvector       • RAG indexing
• RLS
```

### 11.2 URLs y entorno

| Entorno | URL |
|---|---|
| Frontend (producción) | `https://www.lawebfigitalagency.com/hub` |
| API (producción) | `https://api.lawebfigitalagency.com` |
| Health check | `/api/v1/health` → `200 OK` |
| Supabase | Proyecto cloud (no local) |

### 11.3 variables de entorno clave

| Variable | Qué protege |
|---|---|
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | Acceso a la base de datos |
| `OPENAI_API_KEY` | LLMs (DeepSeek / OpenAI) |
| `REDIS_URL` | Cola de jobs |
| `GH_TOKEN` | Acceso a repo privado en Railway (build time) |

---

## 12. Roadmap

```
✅  Fase 0 — Cimientos
    · Schema de base de datos (40 tablas, 18 migraciones)
    · ETL del Excel histórico del ISM
    · Autenticación + RBAC base

✅  Fase 1 — MVP funcional
    · Dashboard ejecutivo (11 KPIs, 2 gráficos)
    · Proyección de campañas a 3 escenarios
    · Scoring accionable de influencers
    · Análisis de sentimiento con DeepSeek
    · Asistente IA con RAG
    · Ingesta universal (CSV, JSON, Sheets)
    · Pipeline Kanban
    · Settings + cambio de contraseña self-service

▶️  FASE ACTUAL — MVP v0.1.0 (Julio 2026)

⏳  Fase 2 — Workflows + Reportes
    · Reportes automáticos (email/scheduled)
    · Integración con más fuentes de datos
    · Notificaciones proactivas

⏳  Fase 3 — IA completa
    · Forecast predictivo de campañas
    · Matchmaking automático influencer–marca
    · Reporting narrativo con LLM

⏳  Fase 4 — Escala
    · SSO empresarial (SAML/OIDC)
    · Business Intelligence (dashboard executives)
    · Multi-tenant para agencias asociadas
    · API pública para integración con terceros
```

---

## 13. Métricas de éxito del producto

Estas son las métricas que P.I.A.R. reporta internamente para validar su propia utilidad.

| KPI | Meta v1 | Cómo se mide |
|---|---|---|
| Cobertura de sentiment | >80% de publicaciones con sentiment clasificado | `comentarios_analizados` vs. total de `publications` |
| Scoring completo | >70% de influencers con decisión accionable (no DATOS_INSUFICIENTES) | `influencer_scores.decision` no-NULL |
| Tiempo de ingesta | <5 min por carga de CSV (100–500 filas) | Log de duración del ETL |
| Adopción del asistente IA | Queries crecientes mes a mes por BU | Tabla de logs del RAG assistant |
| Cobertura de proyección | 100% de campañas nuevas con proyección generada | `campaign_projections` insertadas |
| Uso del dashboard | DAU/MAU del equipo P.I.A.R. | Analytics del frontend |

---

## 14. Equipo

| Nombre | Rol | Responsabilidad |
|---|---|---|
| **Dainer Calderón** | admin_general | Tech lead, arquitectura, deployment |
| **Cristóbal Gallardo León** | admin_general | Producto, metodología P.I.A.R., relación con clientes |
| **Ignacio Chacón** | admin_general + analista + project_manager | Gestión de campañas, análisis de datos, soporte al equipo |

---

## 15. Próximos pasos para go-live

Checklist de validación con directivos:

- [ ] **Aprobación del posicionamiento de P.I.A.R.** — confirmar que `lawebfigitalagency.com/hub` es la URL oficial del hub de Influencer Marketing de la agencia.
- [ ] **Confirmación del cutover desde ISM** — criterio: estabilidad ≥2 semanas en P.I.A.R. con el equipo operando en producción.
- [ ] **Comunicación interna** — informar al equipo sobre la nueva URL, credenciales y flujos actualizados.
- [ ] **Plan de soporte post-launch** — Dainer Calderón y Cristóbal Gallardo como puntos de referencia interna.
- [ ] **Primera presentación a cliente** — usar la proyección en 3 escenarios en la próxima propuesta formal a un cliente.
- [ ] **Revisión del roadmap** — agendar sesión para priorizar Fase 2 (reportes automáticos y integraciones).

---

*Documento preparado para presentación a directivos de La Web Figital Agency.*
*Versión del producto: v0.1.0 (MVP) — Julio 2026*
*Repo: github.com/ungardev/lawebcore (privado)*
