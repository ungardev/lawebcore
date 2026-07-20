# Strategic Brief — La Web Core & "El Ojo que Todo lo Ve"

> **Para:** Claude Code Fable 5 — Análisis y Plan de Desarrollo
> **Fecha:** Julio 2026
> **Autor:** Dainer Ungar — CEO, La Web Figital Agency

---

## 1. El Problema de Mercado

### 1.1 Cómo se selecciona hoy en Venezuela

En Venezuela, la selección de influencers para campañas de marca se hace de tres maneras:

1. **"A ojo"** — El equipo de la agencia ve cuentas en Instagram/TikTok y confía en la intuición. No hay datos, solo impresión visual.

2. **Excel básico** — Se abre una hoja de cálculo y se apuntan handles, seguidores aproximados, y el costo que pide el influencer. Sin métricas reales, sin engagement rate verificado, sin audience breakdown.

3. **Herramientas internacionales (HypeAuditor, Modash)** — Estas herramientas existen pero:
   - No tienen data local validada de Venezuela/LATAM
   - Los benchmarks son globales (un 3% de ER significa algo distinto en VE que en USA)
   - Los precios son altos ($50-500/mes) para agencias boutique
   - No se integran con el flujo de trabajo de la agencia

**El resultado:** campañas donde el influencer "parecía bien" pero entregó 200K menos reach del esperado, o donde el engagement rate real era 0.8% cuando se creía 4%.

### 1.2 El costo del error

| Error | Consecuencia |
|---|---|
| Seleccionar por followers (no por ER) | Pagar $2,000 por un perfil con 500K followers pero 0.5% ER → alcance efectivo de 2,500 personas |
| No verificar geo-audiencia | Perfil con 80% de audiencia en Colombia/México para marca que solo vende en Caracas |
| No detectar fake followers | Perfil inflado con 30% de followers falsos → metrics de engagement distorsionadas |
| Escoger por precio bajo | El "influencer barato" termina costando más en reach/engagement que uno 2x más caro pero con datos reales |

**Una mala selección de influencer puede perder 30-70% del budget de la campaña.**

### 1.3 La realidad del mercado VE

- **Presupuestos limitados:** $3,000-$15,000 USD por campaña es el rango típico
- **Cada peso cuenta:** no hay margen para errores de selección
- **Data escasa:** no existe un benchmark real de engagement rate en VE por nicho
- **Timing es crítico:** las campañas de producto tienen ventana de 2-3 semanas
- **Competencia internacional:** marcas globales entran al mercado VE con más recursos

---

## 2. La Oportunidad

### 2.1 Por qué esto es único en Venezuela

**Ningún competidor en el mercado venezolano tiene:**

- Un pipeline de discovery automatizado con datos reales de Instagram
- Scoring propietario que combine engagement, geo-focus, y business intent
- Benchmarks propios de VE (no globales)
- Un sistema que aprenda de cada campaña ejecutada

### 2.2 El timing

El mercado influencer en Venezuela está en un punto de inflexión:

- **Crecimiento explosivo de Instagram/TikTok en VE** (2024-2026)
- **Marcas internacionales entrando** (Purina, Nike, Coca-Cola) → la competencia por influencers buenos se intensifica
- **Agencias boutique con tecnología propia** = la única manera de competir contra agencias con budget 10x mayores
- **Apify como democratizador** — lo que antes requería $10K/mes en data ahora cuesta $3/campaña

### 2.3 La visión

> **"En 12 meses, La Web Figital Agency va a poder decirle a cualquier marca en Venezuela: 'Te doy los 10 influencers perfectos para tu campaña, verificados, con match score, y garantizados — en 5 minutos."**

Esto no existe en ningún otro lugar de LATAM.

---

## 3. Unit Economics

### 3.1 Costo actual por campaña (Sprint 1)

| Recurso | Costo/campaña | Plan |
|---|---|---|
| Apify (Instagram data) | ~$3.30 | Free tier ($5 credit) |
| DeepSeek (LLM) | ~$0.05 | Pay-per-use |
| Railway (infra) | ~$0.50 | Compartido entre campañas |
| **Total** | **~$3.85/campaña** | |

### 3.2 Valor de una campaña

| Tipo de campaña | Budget típico marca | Revenue agencia (15-25%) |
|---|---|---|
| Micro-influencer (5-10 perfiles) | $3,000-$5,000 | $450-$1,250 |
| Mid-tier (3-5 perfiles) | $5,000-$10,000 | $750-$2,500 |
| Macro (1-3 perfiles + contenido) | $10,000-$25,000 | $1,500-$6,250 |

### 3.3 ROI del sistema

- **Sin sistema:** 1 de cada 3 campañas tiene ROI negativo por mala selección de influencer
- **Con sistema:** 9 de cada 10 campañas deberían entregar lo proyectado

**ROI del investment en el sistema: 50-100x**

---

## 4. Ventaja Competitiva Documentada

### 4.1 Lo que tenemos y nadie más tiene en VE

| Ventaja | Estado | Qué significa |
|---|---|---|
| **Pipeline 4 capas Apify** | ✅ Deployado | Data oficial de Instagram, no estimaciones |
| **LWFA Scoring** | ✅ Deployado | 4 KPIs propietarios: ICA, Geo-Foco, Velocity, Business Intent |
| **Keywords Gemini** | ✅ 28 keywords validadas | Las keywords exactas que traen perfiles VE relevantes |
| **Benchmarks VE** | 🔲 Por construir | ER promedio por tier en VE, no global |
| **Historical learning** | 🔲 Por construir | Cada campaña mejora el scoring |

### 4.2 Lo que los competidores tienen y nosotros no (todavía)

| Competidor | Ventaja | Nuestro plan |
|---|---|---|
| HypeAuditor | Data de audiencia detallada | Meta for Developers (Sprint 2) |
| Modash | Dashboard de tracking | Metricool integration |
| Metricool | Analytics de cuentas propias | Metricool API (Sprint 3) |
| Buzzumo | Base de datos de influencers | Crawling continuo + DB propia |

---

## 5. El Cliente Ideal (Purina Dog Chow)

### 5.1 Caso de uso: Purina Dog Chow Venezuela

**Brief:** "Necesito influencers en Venezuela para Purina Dog Chow, mujeres 25-45, tono aspiracional, Caracas y Valencia, presupuesto $5,000."

**Sin el sistema:**
- El planner busca "mascotas vzla" en Instagram
- Ve un perfil con 50K followers que "se ve bien"
- Lo selecciona, la marca paga $800
- El perfil tiene 0.8% ER real y 60% de audiencia en Colombia → campaña mediocre

**Con el sistema:**
- El pipeline busca 28 keywords + 22 hashtags Gemini
- Encuentra 150 perfiles potenciales
- Los enriquece con datos reales de Instagram
- Los scorea con LWFA (geo-focus VE, ER real, business intent)
- Entrega los 10 mejores rankeados con match score 0-100
- El planner selecciona de una lista verificada → campaña exitosa

### 5.2 Por qué Purina como primer cliente

- **Mercado grande:** 60%+ de hogares venezolanos tienen mascota
- **Brand awareness alto:** no necesita explicar qué es Dog Chow
- **Tono aspiracional:** encaja con influencers de nicho mascotas/lifestyle
- **Budget disponible:** marca de consumo masivo con presupuesto de marketing

---

## 6. Restricciones del Proyecto

### 6.1 Budget

| Recurso | Límite mensual |
|---|---|
| APIs externas (Apify + DeepSeek) | $200 USD |
| Infraestructura (Railway) | $50 USD |
| **Total** | **$250 USD/mes** |

### 6.2 Equipo

- 1 persona desarrollando (Dainer, CEO + developer)
- 4 horas/día disponibles para desarrollo
- Sin recursos parainfraestructura complex

### 6.3 Compliance

- **NO scraping de datos privados**
- **Solo datos públicos** de Instagram/TikTok/YouTube
- **APIs oficiales** para Meta, TikTok cuando estén aprobadas
- **Apify como fuente primaria** para data de Instagram

### 6.4 Timeline

- **MVP funcional:** Julio 2026 ✅ (Sprint 1)
- **Demo Purina end-to-end:** Julio 28, 2026 (Sprint 2)
- **Escala a 10+ campañas/mes:** Agosto 2026
- **Expansión TikTok + Meta:** Agosto-Septiembre 2026

---

## 7. Por Qué Este Proyecto Va a Cambiar el Juego

### 7.1 El argumento

1. **Venezuela tiene el mercado perfecto** para esto: budgets limitados + data escasa + necesidad de precisión = cada peso debe estar optimizado.

2. **La tecnología existe y es barata:** Apify + DeepSeek = $3/campaña en lugar de $500 en herramientas tradicionales.

3. **La competencia no lo tiene:** ninguna agencia en VE puede ofrecer "10 influencers verificados con match score en 5 minutos."

4. **El modelo es replicable:** lo que construimos para VE se puede llevar a Colombia, Ecuador, Perú — LATAM es el mercado objetivo.

### 7.2 El riesgo si no lo hacemos

Si La Web Figital Agency no construye esto ahora:

- Competidores internacionales (con más budget) van a entrar al mercado VE con herramientas propias
- La agencia queda limitada a "buena intuición" mientras otras ofrecen datos y garantías
- El diferencial competitivo se evapora en 12-18 meses

### 7.3 El payoff

> "En 3 años, La Web Figital Agency va a ser conocida como la agencia que tiene el mejor sistema de selección de influencers en LATAM, y eso empezó en Venezuela en 2026."

---

## 8. Lo Que Fable 5 Necesita Entender

Este no es "un proyecto de software." Es una herramienta de negocio que va a definir cómo se hacen las campañas de influencer marketing en Venezuela.

**El código es el medio. El negocio es el fin.**

Cualquier decisión técnica que Fable 5 proponga debe responder a:
- ¿Esto reduce el costo por campaña?
- ¿Esto mejora la calidad de los candidatos encontrados?
- ¿Esto nos acerca a "10 influencers verificados en 5 minutos"?

Si la respuesta a las tres es "no" o "marginal", probablemente no es la prioridad correcta.

---

*Documento preparado para guiar el análisis de Fable 5.*
*La Web Figital Agency — Julio 2026*
