# Plan de Herramientas y Suscripciones — La Web Figital Agency

> Documento para presentación a directivos.
> Última actualización: 2026-07-14

---

## 1. Resumen ejecutivo

**LaWebCore Discovery** es un sistema de búsqueda de influencers con IA que ya está
desplegado y funcionando a nivel de chat conversacional. Para activar la búsqueda
real de influencers en todas las plataformas, necesitamos acceso a 4 APIs externas.

**Inversión mensual necesaria: $17–27 USD/mes** (básicamente solo el LLM provider).

No hay licencias costosas. No hay subscriptions caras. El sistema de scoring de
audiencia ya lo estamos construyendo internamente — es más potente, ilimitado y
específico que cualquier herramienta de terceros.

---

## 2. Qué tenemos hoy (funcionando)

| Componente | Status |
|---|---|
| Frontend Discovery (React + Vite) | ✅ Desplegado en Vercel |
| API REST (FastAPI) | ✅ Desplegado en Railway |
| Workers (ARQ + Redis) | ✅ Conectados y corriendo |
| Chat conversacional con IA | ✅ Funcionando end-to-end |
| Base de datos (Supabase) | ✅ 100% operativa |
| Auth con JWT (Supabase) | ✅ Registros y login OK |

---

## 3. Lo que necesitamos para activar Discovery real

### 🔴 Apify — Scraping de redes sociales
- **Qué hace:** Extrae datos de Instagram, TikTok y YouTube a escala.
- **Status:** La empresa ya tiene suscripción activa. Solo necesitamos la API key.
- **Costo para la empresa:** $0 (ya cubierto por la suscripción existente).
- **Acción requerida:** Solicitar `APIFY_API_KEY` al administrador de la cuenta Apify.
- **Tiempo:** Inmediato una vez solicitada la key.

### 🔴 Meta for Developers — Instagram Graph API
- **Qué hace:** Acceso oficial a Instagram Business y Creator accounts (métricas,
  búsqueda, datos de perfil verificados).
- **Costo:** $0. La app Standard es gratuita. Solo requiere verificación de empresa
  Meta Business.
- **Acción requerida:**
  1. Crear app en developers.facebook.com/apps/
  2. Solicitar verificación de empresa (1–7 días hábiles).
  3. Vincular cuenta de Instagram Business de la empresa.
  4. Generar User Access Token de larga duración.
- **Variables:** `META_APP_ID`, `META_APP_SECRET`, `META_ACCESS_TOKEN`
- **Tiempo:** 1–2 semanas desde la solicitud.

### 🔴 TikTok Research API
- **Qué hace:** Data oficial de TikTok creators para research (videos, followers,
  hashtags, engagement).
- **Costo:** $0 (con aprobación).
- **⚠️ Aplicar HOY — es el cuello de botella más largo (2–4 semanas de aprobación).**
- **Acción requerida:**
  1. Aplicar en developers.tiktok.com/research/api
  2. Caso de uso: "P.I.A.R. Discovery — influencer matching para campañas de
     marketing en región LATAM."
  3. Una vez aprobado, configurar la key.
- **Variable:** `TIKTOK_RESEARCH_API_KEY`

### 🔴 YouTube Data API v3
- **Qué hace:** Búsqueda y métricas de canales de YouTube.
- **Costo:** $0 — el tier gratuito permite 10,000 unidades/día
  (≈ 100,000 llamadas/día). Suficiente para nuestro volumen.
- **Acción requerida:**
  1. Crear proyecto en console.cloud.google.com
  2. Habilitar YouTube Data API v3.
  3. Crear API key y restringir por IP (opcional).
- **Variable:** `YOUTUBE_DATA_API_KEY`
- **Tiempo:** 10 minutos.

### 🔴 LLM Provider — DeepSeek
- **Qué hace:** Scoring y ranking de candidatos con IA, parsing de briefs,
  respuestas conversacionales del asistente.
- **Costo:** $0.14/M tokens input, $0.28/M tokens output.
  Para nuestro volumen estimado (≤ 50,000 llamadas de scoring/mes):
  **$5–15 USD/mes.**
- **Por qué DeepSeek y no OpenAI:** 3–4× más económico, calidad comparable para
  nuestro caso de uso. OpenAI costaría $20–50/mes para el mismo volumen.
- **Acción requerida:**
  1. Crear cuenta en platform.deepseek.com
  2. Generar API key.
  3. Cargar saldo inicial de $10 USD.
- **Variables:** `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL=deepseek-v4-flash`

---

## 4. Qué NO necesitamos (y por qué)

| Herramienta | Costo normal | Por qué la skippeamos |
|---|---|---|
| HypeAuditor | $99–500/mes | Estamos construyendo nuestro propio sistema de scoring de audiencia internamente. Es más potente, ilimitado y específico para nuestro caso de uso. |
| Metricool | $12–25/mes | Opcional para métricas post-publish. Podemos agregarlo después si el cliente lo demanda. |
| Canva API | $13+/mes | No es necesario para Discovery.我们可以 agregarlo en la fase de asset generation. |
| Intercom | $74+/mes | El chat conversacional ya lo tenemos-built. |

---

## 5. Inversión total

| Concepto | Costo |
|---|---|
| Apify | $0 (suscripción existente) |
| Meta for Developers | $0 |
| TikTok Research API | $0 |
| YouTube Data API | $0 |
| DeepSeek (LLM) | **$5–15/mes** |
| Slack webhook | $0 |
| **TOTAL** | **$5–15 USD/mes** |

**Compromiso financiero inicial:** ~$10 USD de saldo DeepSeek para empezar.
**Sin contratos. Sin licencias. Pay-as-you-go.**

---

## 6. Variables de entorno a configurar

Una vez obtenidas las credenciales, se configuran en el panel de Railway
(servicios `lawebcore-api` y `lawebcore-workers`):

```
APIFY_API_KEY=
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
TIKTOK_RESEARCH_API_KEY=
YOUTUBE_DATA_API_KEY=
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
DEFAULT_LLM_PROVIDER=deepseek
```

---

## 7. Plan de acción inmediato

| # | Acción | Responsable | Tiempo |
|---|---|---|---|
| 1 | Solicitar `APIFY_API_KEY` al admin de Apify | [Nombre] | Inmediato |
| 2 | Crear app en Meta for Developers | [Nombre] | 10 min |
| 3 | Solicitar verificación empresa Meta | [Nombre] | 1–7 días |
| 4 | Aplicar a TikTok Research API **HOY** | [Nombre] | 10 min |
| 5 | Crear proyecto Google Cloud + YouTube API key | [Nombre] | 10 min |
| 6 | Crear cuenta DeepSeek + cargar $10 | [Nombre] | 10 min |
| 7 | Configurar variables en Railway | [Nombre] | 5 min |
| 8 | Test E2E Discovery con credenciales reales | [Nombre] | 30 min |

---

## 8. URLs de adquisición

| Servicio | URL |
|---|---|
| Apify | console.apify.com/account/integrations |
| Meta | developers.facebook.com/apps/ |
| TikTok | developers.tiktok.com/research/api |
| YouTube | console.cloud.google.com → YouTube Data API v3 |
| DeepSeek | platform.deepseek.com → API Keys |
| Slack | api.slack.com/messaging/webhooks |

---

## 9. Conclusión

**LaWebCore Discovery** es un proyecto AI elite top tier con un costo de operación
mínimo:

- **Inversión inicial: $10 USD** (saldo DeepSeek)
- **Costo mensual recurrente: $5–15 USD** (solo LLM)
- **Costo anual estimado: $60–180 USD**

No hay licencias, no hay subscriptions costosas, no hay contratos de por medio.
El sistema de scoring más sofisticado (que nos diferenciaría de herramientas como
HypeAuditor o Metricool) lo estamos construyendo internamente — ilimitado,
específico y propio.

La única inversión significativa es de tiempo en obtener las API keys, no de dinero.
