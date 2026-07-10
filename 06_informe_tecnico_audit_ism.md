# INFORME TÉCNICO — Correcciones y Recomendaciones para el Hub de Influencer Marketing

La Web Figital Agency · Área P.I.A.R.
Consolidado a partir de la auditoría técnica en vivo de la plataforma Influencer Strategist & Manager (ISM) — Supabase inspeccionado con token autenticado — más el formato de reporte estandarizado ya definido para alimentar el hub.

| Campo | Detalle |
|---|---|
| Fecha | 10-07-26 |
| Preparado para | Ingeniero de sistemas del equipo P.I.A.R. (y su IA de procesamiento) |
| Preparado por | Ignacio Chacón · La Web Figital Agency |
| Alcance | Diagnóstico técnico confirmado + correcciones priorizadas + data contract recomendado para cualquier hub de influencer marketing que construya el equipo |

---

## 1. Resumen ejecutivo

Este documento reúne, en un solo lugar, todo lo que ya se investigó y corrigió sobre el hub de influencer marketing de LWFA (Influencer Strategist & Manager, ISM), para que sirva de referencia al construir o corregir cualquier versión del hub — incluida la que está en desarrollo actualmente.

El diagnóstico se hizo con evidencia directa: inspección en vivo de la base de datos (Supabase, proyecto pnhzcglosnfktzbsnjhn) con el token de sesión autenticado, más el Excel de benchmarks propios de la agencia y el PDF real de reportes de campaña (MOVILNET, #PorFinIlimitados). No son inferencias — son hallazgos confirmados en los datos almacenados.

Diagnóstico en una línea: el importador de CSV del ISM solo guarda la columna views y descarta silenciosamente likes, comments, shares, saves y campaign_id porque el Google Form exporta encabezados en español y el parser espera inglés. El esquema de base de datos (46 columnas en influencer_historical_data) está bien diseñado — el problema es exclusivamente el mapeo de columnas al importar. Corregir esto resuelve ~90% de los problemas visibles en dashboard, scoring y reportes.

Para evitar que el próximo hub repita el mismo error, la Sección 8 de este informe incluye el data contract (formato JSON) que LWFA ya usa para entregar reportes de campaña — con nombres de campo snake_case que calzan 1:1 contra el schema de Supabase, para que ningún parser tenga que adivinar mapeos de español a inglés nunca más.

---

## 2. Arquitectura de referencia (ISM auditado)

Válida como benchmark de diseño para cualquier hub nuevo — el esquema de datos es sólido y debe preservarse.

**Stack confirmado:**

| Capa | Detalle |
|---|---|
| Frontend | React + Vite + React Router |
| Base de datos | Supabase (PostgreSQL) — proyecto pnhzcglosnfktzbsnjhn.supabase.co |
| Gráficos | Recharts |
| Autenticación | Supabase Auth con JWT — permisos por email en hub_tool_permissions |
| Hosting | lawebfigitalagency.com — PWA (manifest.json retornaba 404) |
| Acceso a datos | REST API de Supabase con políticas RLS |

**Tablas confirmadas:**

| Tabla | Estado en la auditoría | Descripción |
|---|---|---|
| influencer_historical_data | ⚠️ Incompleta | Tabla principal de publicaciones vía CSV. 46 columnas. 1,698 registros con views, engagement = NULL en todos. |
| influencer_profiles | ✅ Funcional | 951 perfiles: handle, plataforma, tier, seguidores, nicho, país. engagement_rate = 0 en todos (consecuencia del bug de arriba). |
| influencer_campaigns | ✅ Funcional | 2 campañas registradas: #PorFinIlimitados (MOVILNET) y EVENTO RUFFLES. |
| campaign_influencers | ✗ Vacía | Tabla de relación campaña↔influencer con KPIs calculados. 0 registros — nunca fue usada. |
| hub_tool_permissions | ✅ Funcional | Control de acceso por email. |

**Columnas de influencer_historical_data (46, confirmadas):**

```
id, campaign_name, influencer_name, platform, followers_at_time, views, reach,
engagement_rate, retention_avg, virality_index, content_type, content_format,
hook_effectiveness, video_length_seconds, published_at, cost, roi, notes,
raw_data, created_at, uploaded_by, campaign_id, likes, comments, shares, saves,
reposts, total_watch_time_seconds, engagement_total, er_views, er_reach,
views_followers_ratio, views_reach_ratio, save_rate, share_rate, comment_rate,
consumption_intensity, depth_index, tier, classification_views,
classification_engagement, classification_depth, classification_retention,
content_url, group_label, data_quality_flags
```

**Conclusión sobre el esquema:** está bien diseñado, con columnas para todo lo que se necesita. El problema es el importador, no el modelo de datos — cualquier hub nuevo puede replicar este esquema con confianza.

---

## 3. Causa raíz — confirmada en base de datos

Query ejecutado directamente sobre el influencer @mnakary (263,869 views, el de mayor alcance del sistema):

```
views:            263,869   ← SE GUARDÓ ✓
likes:            null      ← NO SE GUARDÓ ✗
comments:         null      ← NO SE GUARDÓ ✗
shares:           null      ← NO SE GUARDÓ ✗
saves:            null      ← NO SE GUARDÓ ✗
engagement_total: null      ← NO SE GUARDÓ ✗
er_views:         null      ← NO SE GUARDÓ ✗
retention_avg:    null      ← NO SE GUARDÓ ✗
campaign_id:      null      ← SIN CAMPAÑA ✗
```

**Por qué falla:** el Google Form de campaña (confirmado con el PDF de MOVILNET) exporta columnas en español. El parser del ISM tiene un mapeo hardcodeado que solo reconoce inglés:

| Columna real del CSV (Google Form) | Campo esperado en Supabase | ¿Se mapea? |
|---|---|---|
| Nombre de usuario | influencer_name | ✓ Sí |
| Vistas | views | ✓ Sí (parcial/coincidencia) |
| Me Gusta | likes | ✗ No — NULL |
| Comentarios | comments | ✗ No — NULL |
| Compartidos | shares | ✗ No — NULL |
| Guardados | saves | ✗ No — NULL |
| Reposts | reposts | ✗ No — NULL |
| Alcanzadas | reach | ✗ No — NULL |
| Total segundos | total_watch_time_seconds | ✗ No — NULL |
| [campaña actual] | campaign_id | ✗ No — NULL |
| raw_data (respaldo) | raw_data | ✗ Guarda {} vacío |

**Hallazgo adicional crítico:** raw_data — el campo pensado para respaldar la fila cruda del CSV — se guarda como {} vacío en todos los registros. No hay forma de recuperar el dato original sin pedir que el usuario resuba el archivo.

**Volumen afectado:**

| Métrica | Valor |
|---|---|
| Registros con views ≠ null | 1,698 publicaciones |
| Registros con campaign_id ≠ null | 0 — todos huérfanos |
| Registros con likes ≠ null | 0 |
| Registros en campaign_influencers | 0 |
| Perfiles en influencer_profiles | 951 |
| Views visibles en Dashboard | 3,533,113 (suma de los 1,698 registros) |

**Consecuencia en cascada:** sin engagement, er_views siempre da 0%, y el score del sistema (ver Sección 4) cae al valor por defecto de 2.00 para todos los perfiles — invalidando toda clasificación de Escalar/Optimizar/Descartar. Además, como campaign_id nunca se asigna, los módulos ROI Analytics y CRM Pipeline (que dependen de campaign_influencers) quedan completamente vacíos.

---

## 4. Sistema de scoring — metodología real y su falla

**Fórmula oficial** (1 a 3 puntos por dimensión, no 0-10):

```
Score Final = (Score_Retención + Score_Engagement + Score_Viralidad) / 3
```

**Score_Retención** (segundos promedio por vista):
- > 10s → 3 pts | 6–10s → 2 pts | < 6s → 1 pt

**Score_Engagement** (ER sobre views):
- ER > 10% → 3 pts | ER 5–10% → 2 pts | ER < 5% → 1 pt

**Score_Viralidad** (Views/Followers, V/F):
- V/F > 1.5 → 3 pts | V/F 0.8–1.5 → 2 pts | V/F < 0.8 → 1 pt

**Decisión automática:** Score ≥ 2.5 → Escalar | 1.8–2.5 → Optimizar | < 1.8 → Descartar

**Por qué el score da 2.00 (o 1.67) para todos:** con engagement, retención y V/F en NULL, el sistema no puede calcular las tres dimensiones y asigna 2 pts por defecto a cada una → (2+2+2)/3 = 2.00 → "Optimizar". Pero 176 perfiles aparecen como "Descartar": esto sugiere que cuando er_views se calcula como 0% (en vez de quedar NULL), el sistema sí asigna 1pt de Engagement → (2+1+2)/3 = 1.67 → "Descartar". Es decir, el mismo problema (falta de datos) produce dos clasificaciones distintas según si el campo llegó como NULL o como 0 — una inconsistencia que hay que corregir explícitamente.

**Ejemplo de verificación manual** (con datos reales del PDF de MOVILNET, influencer @edualvrz, publicación del 11/12/2025):

```
views: 22,722 · likes: 1,100 · comments: 15 · shares: 5 · saves: 10 · reposts: 1
retención acumulada: 102,864 segundos (28h34min) — es TOTAL, no promedio por vista
followers (según dashboard): ≈285,000

engagement_total = 1,100 + 15 + 5 + 10 = 1,130
er_views = (1,130 / 22,722) × 100 = 4.97% → Score Engagement = 1pt (ER < 5%)
retención promedio real = 102,864 / 22,722 = 4.53s por vista → Score Retención = 1pt (< 6s)
V/F = 22,722 / 285,000 = 0.08x → Score Viralidad = 1pt (V/F < 0.8)

Score = (1+1+1)/3 = 1.00 → Descartar
```

**Hallazgo importante sobre retención:** el campo "Total segundos" del Google Form es tiempo de reproducción acumulado de todas las vistas, no un promedio. Cualquier hub que reciba este dato debe dividirlo entre views antes de compararlo contra los umbrales de segundos — de lo contrario, todos los videos parecerán tener retenciones absurdamente altas.

**Otro hallazgo relevante:** el sistema no acumula publicaciones por perfil para el score — evalúa post por post. Cualquier hub nuevo debería decidir explícitamente si el score es por publicación, por wave, o acumulado por creador — y documentarlo.

---

## 5. Mapa de módulos — estado real (referencia de QA para el hub nuevo)

| Módulo | Estado en ISM auditado | Nota para el hub nuevo |
|---|---|---|
| Dashboard — Performance | ⚠️ Views correctas (3.5M), resto en 0 por el bug de engagement | Verificar que engagement/ER no dependan de un cálculo roto |
| Dashboard — Overview | ⚠️ Muestra 0 views (lee de campaign_influencers, vacía) mientras Performance muestra 3.5M | No usar dos pestañas que lean de fuentes distintas para el mismo KPI |
| Campañas | ⚠️ CSV falla en engagement; 94 fallos, 0 procesados en cargas de Ruffles | El feedback de error debe ser por fila, no un fallo silencioso genérico |
| Descubrimiento | ⚠️ 951 perfiles, pero engagement_rate = 0 por el mismo bug | Los perfiles no deben depender de datos de campaña para existir, pero sí para su score |
| CRM Pipeline | ✗ Vacío — campaign_influencers sin uso | Diseñar el flujo de asignación influencer↔campaña desde el día 1 |
| ROI Analytics | ✗ Vacío — depende de campaign_influencers | Buena interfaz, sin datos — priorizar que la tabla de vínculo se llene siempre al importar |
| Comparador de Campañas | ⚠️ Funcional sin datos para comparar | — |
| Histórico | ⚠️ 1,698 registros pero todos "Sin campaña" (campaign_id NULL) | campaign_id debe ser obligatorio en el insert, nunca opcional |
| Strategy AI / Creative Lab | ✅ Funcionan, pero desconectados de datos reales del perfil | Alto potencial: conectar el score y el historial real del influencer al prompt de estos módulos |

**Bugs técnicos adicionales confirmados:**
- Gráficos Recharts con width/height = -1 (6 warnings idénticos en consola) → gráficos vacíos o diminutos. Fix: usar `<ResponsiveContainer width="100%" height={300}>` con contenedor de minHeight explícito.
- manifest.json retorna 404 → la PWA no es instalable.

---

## 6. Benchmarks propios de LWFA

El ISM auditado tenía una tabla hardcodeada de solo 4 categorías (Nano/Micro/Mid/Macro). LWFA ya tiene un Excel propio, más granular (18 rangos), construido con criterio de mercado venezolano/LATAM real. Recomendación: cualquier hub nuevo debe usar esta tabla, no una genérica.

| Categoría | Seguidores | V/F esperado | ER% esperado | CPV ideal ($) | Rol en campaña |
|---|---|---|---|---|---|
| NANO bajo | 500–5K | 1.2x–2.5x | 10%–15% | $0.005 | Volumen + viralidad orgánica |
| NANO alto | 5K–10K | 0.9x–1.5x | 8%–12% | $0.008 | Distribución orgánica |
| MICRO bajo | 10K–30K | 0.9x–1.8x | 8%–13% | $0.010 | Engagement + conversión |
| MICRO medio | 30K–60K | 0.8x–1.8x | 6%–11% | $0.011 | Balance performance |
| MICRO alto | 60K–100K | 0.7x–1.5x | 5%–10% | $0.012 | Escala + validación |
| MID bajo | 100K–250K | 0.5x–1.0x | 4%–8% | $0.015 | Credibilidad |
| MID alto | 250K–500K | 0.3x–0.8x | 3%–7% | $0.017 | Awareness + branding |
| MACRO bajo | 500K–750K | 0.4x–1.5x | 3%–6% | $0.021 | Amplificación masiva |
| MACRO alto | 750K–1M | 0.2x–0.9x | 2%–5% | $0.024 | Top awareness |

**Cómo debe usarse:** al importar datos de un influencer, el hub debe ubicar su categoría según seguidores, comparar ER real vs. rango esperado, V/F real vs. rango esperado y CPV real vs. CPV ideal, y mostrar un semáforo (verde = dentro de benchmark, amarillo = por debajo, rojo = muy por debajo). El Score_Engagement debería calibrarse por categoría, no con un umbral único.

---

## 7. Correcciones técnicas priorizadas (fichas C-01 a C-07)

| Ficha | Corrección | Esfuerzo | Prioridad |
|---|---|---|---|
| C-01 | Mapeo de columnas CSV español → campos Supabase | 2 días | 🔴 Crítico |
| C-02 | Asignar campaign_id automáticamente al importar | 1 día | 🔴 Crítico |
| C-03 | Calcular campos derivados post-insert (ER, V/F, retención) | 2 días | 🔴 Crítico |
| C-04 | Guardar raw_data completo (hoy guarda {}) | 0.5 días | 🔴 Crítico |
| C-05 | Fix bug Recharts — gráficos con width/height = -1 | 0.5 días | 🟠 Alto |
| C-06 | Unificar fuente de datos Performance ↔ Overview | 1 día | 🟠 Alto |
| C-07 | Manejo correcto de NULL vs 0 en el sistema de scoring | 1 día | 🔴 Crítico |

**C-01 — Mapeo de columnas CSV (español → Supabase)**
```javascript
const COLUMN_MAP = {
  // Español (Google Form)
  'vistas': 'views',
  'me gusta': 'likes',
  'comentarios': 'comments',
  'compartidos': 'shares',
  'guardados': 'saves',
  'reposts': 'reposts',
  'alcanzadas': 'reach',
  'nombre de usuario': 'influencer_name',
  'total segundos': 'total_watch_time_seconds',
  'nombre y apellido': 'display_name',
  'grupo asignado': 'group_label',
  'fecha de publicación': 'published_at',
  'agrega el enlace de tu publicación': 'content_url',
  // Inglés (Metricool y otras fuentes)
  'views': 'views', 'likes': 'likes', 'comments': 'comments',
  'shares': 'shares', 'saves': 'saves', 'reach': 'reach',
};
```

**C-02 — Asignar campaign_id al importar**
```javascript
const row = {
  ...mappedFields,
  campaign_id: currentCampaignId,      // ← obligatorio, nunca implícito
  campaign_name: currentCampaignName,
  uploaded_by: currentUser.email,
  created_at: new Date().toISOString(),
};
```

**C-03 — Calcular campos derivados post-insert**
```javascript
engagement_total = (likes||0) + (comments||0) + (shares||0) + (saves||0);
er_views = views > 0 ? (engagement_total / views) * 100 : null;
er_reach = reach > 0 ? (engagement_total / reach) * 100 : null;
views_followers_ratio = followers_at_time > 0 ? views / followers_at_time : null;

// "Total segundos" del form es ACUMULADO, no promedio — dividir siempre entre views:
retention_avg = (total_watch_time_seconds && views > 0)
  ? total_watch_time_seconds / views
  : null;

save_rate = views > 0 ? (saves / views) * 100 : null;
share_rate = views > 0 ? (shares / views) * 100 : null;
depth_index = views > 0 ? ((saves + shares) / views) * 100 : null;
```

**C-04 — Guardar raw_data completo**
```javascript
// Antes: raw_data = {} (vacío, sin utilidad)
raw_data = { ...originalCsvRow };  // fila original completa, para poder reprocesar sin re-upload
```

**C-05 — Fix gráficos Recharts**
```jsx
// Antes: contenedor sin altura definida → width/height = -1
<div className="chart-container" style={{ minHeight: '300px', width: '100%' }}>
  <ResponsiveContainer width="100%" height={300}>
    <PieChart>...</PieChart>
  </ResponsiveContainer>
</div>
```

**C-06 — Unificar Performance ↔ Overview**
Ambas pestañas deben leer de la misma fuente. Si campaign_influencers está vacía, Overview debe hacer fallback a influencer_historical_data — nunca mostrar 0 en una pestaña y 3.5M en la otra para el mismo KPI.

**C-07 — Manejo correcto de NULL vs 0 en el scoring**
```javascript
if (engagement_total === null || views === null) {
  score = null;
  decision = 'Datos insuficientes';   // nunca defaultear a 2pts ni a "Descartar"
} else {
  // calcular score normalmente
}
```

---

## 8. Data contract recomendado — formato de reporte para alimentar el hub

Para que ningún hub futuro repita el bug de C-01, LWFA ya estandarizó el formato en que P.I.A.R. entrega los datos de campaña, alineado 1:1 con los nombres de columna reales de Supabase.

**Reglas:**
- Salida en JSON, nunca en tablas markdown con "K"/"M" o comas decimales — números crudos siempre (45200, no "45.2K").
- snake_case en inglés, calzando con las columnas reales de la base (views, likes, comments, shares, saves, engagement_total, er_views, retention_avg, virality_index, campaign_id).
- campaign_id obligatorio en cada fila — nunca implícito ni null por omisión.
- data_quality_flags en vez de defaultear valores faltantes.
- raw_data con la fila original sin transformar, en cada registro.

**Ejemplo de estructura (una publicación):**
```json
{
  "username": "usuario1",
  "followers": 12300,
  "campaign_id": "id real del hub o null",
  "post_date": "DD-MM-AA",
  "post_url": "https://instagram.com/p/xxxx",
  "views": 5600,
  "likes": 410,
  "comments": 22,
  "saves": 9,
  "shares": 5,
  "engagement_total": 446,
  "er_views": 7.96,
  "virality_index": 0.46,
  "retention_avg": null,
  "data_quality_flags": ["retention_missing"],
  "raw_data": { "...": "fila original tal cual llegó de la fuente" }
}
```

**Checklist previo a cada reporte (Paso 0):**
1. Confirmar la campaña exacta
2. Confirmar la fecha de corte
3. Listar fuentes a combinar (con prioridad si hay conflicto)
4. ¿HypeAuditor disponible? (en nuestro caso: NO — usamos clones propios)
5. ¿Hay capturas de retención?
6. ¿Qué perfiles del pull realmente publicaron?

**Trigger de ejecución:** "Ejecuta el reporte HUB de [Campaña]" → dispara el checklist, el QC de coherencia y la generación del JSON + el análisis textual.

---

## 9. Flujo operativo — actual (roto) vs. ideal

**Actual:**
1. Se crea la campaña. 2. Influencers reportan por Google Form. 3. Se exporta CSV e intenta importar. 4. El parser falla en columnas en español → 0 procesados. 5. Los registros que sí entran tienen views pero engagement NULL. 6. campaign_id NULL → huérfanos. 7. Dashboard muestra ER 0%, score 2.00. 8. El equipo abandona la plataforma y vuelve a Excel.

**Ideal (post-corrección):**
1. Se crea la campaña con presupuesto, KPIs objetivo y fechas. 2. Se asignan influencers confirmados desde Descubrimiento o CRM Pipeline. 3. Los influencers reportan (Form o interfaz directa futura). 4. Se importa el CSV con mapeo de columnas asistido (y plantilla reutilizable). 5. El sistema calcula automáticamente engagement, ER, retención, V/F, depth_index, asigna campaign_id y guarda raw_data completo. 6. El Dashboard muestra KPIs reales y una clasificación accionable. 7. El equipo valida y exporta el reporte para el cliente. 8. Los datos quedan vinculados a campaña y perfil para futuras decisiones.

---

## 10. Roadmap priorizado

| Fase | Tarea | Esfuerzo | Impacto |
|---|---|---|---|
| 1 | Mapeo de columnas CSV español/inglés (COLUMN_MAP) | 2 días | 🔴 Crítico |
| 1 | Asignar campaign_id al importar desde una campaña | 1 día | 🔴 Crítico |
| 1 | Calcular campos derivados post-insert (engagement, ER, V/F, retención) | 2 días | 🔴 Crítico |
| 1 | Guardar raw_data completo (no {}) | 0.5 días | 🟠 Alto |
| 1 | Manejar NULL vs 0 — marcar "Datos insuficientes" | 1 día | 🔴 Crítico |
| 1 | Fix Recharts con ResponsiveContainer + minHeight | 0.5 días | 🟠 Alto |
| 2 | Interfaz de mapeo de columnas con plantillas guardadas | 4 días | 🟠 Alto |
| 2 | Unificar fuente de datos Performance ↔ Overview | 1 día | 🟠 Alto |
| 2 | Reporte de errores CSV por fila, exportable | 2 días | 🟠 Alto |
| 2 | Integrar benchmarks propios (18 rangos) en comparación automática | 3 días | 🟡 Medio |
| 2 | Fix manifest.json para PWA | 0.5 días | 🟡 Medio |
| 3 | Extracción de tarifas desde media kits (PDF) | 7 días | 🟠 Alto |
| 3 | Conectar Strategy AI / Creative Lab a datos reales del perfil | 5 días | 🟡 Medio |
| 3 | Exportación de reportes PDF/Excel por campaña | 5 días | 🟡 Medio |
| 4 | Interfaz directa de reporte para influencers (reemplaza Google Form) | 12 días | 🟡 Medio |
| 4 | Integración API Instagram/TikTok para pull automático de métricas | 15 días | 🟡 Medio |

**Fase 1 completa: ~6.5 días de desarrollo** para que el hub procese correctamente el CSV, calcule todos los KPIs, vincule registros a campañas y muestre datos reales. Con esto se resuelve ~90% de lo observado en la auditoría.

---

## 11. Qué preservar vs. qué corregir de inmediato

**Preservar (ya está bien diseñado):**
- El esquema de base de datos de 46 columnas — no necesita cambios estructurales.
- La arquitectura React + Supabase — moderna, escalable, mantenible.
- Los módulos Strategy AI y Creative Lab como interfaces — son diferenciales de valor una vez conectados a datos reales.
- El módulo de Descubrimiento con sus 951 perfiles y filtrado funcional.
- Los benchmarks propios de LWFA (Sección 6) — activo de inteligencia de mercado único, no reemplazar por tablas genéricas.

**Corregir de inmediato:**
- El parser de CSV (C-01) — bug más crítico, bloquea todo lo demás.
- La asignación de campaign_id (C-02) — sin esto, los datos importados son invisibles para el 80% de los módulos.
- El cálculo de campos derivados post-import (C-03).
- El manejo de NULL vs 0 (C-07) — nunca clasificar un perfil con datos insuficientes como si tuviera un score real.

---

## 12. Conclusión y siguiente paso recomendado

El hub tiene todos los ingredientes para ser una herramienta de clase profesional: arquitectura sólida, módulos bien pensados, benchmarks propios de mercado venezolano/LATAM e IA integrada. La brecha entre lo que existe y lo que debería funcionar es específica, está mapeada campo por campo, y es corregible en menos de dos semanas de trabajo enfocado (Fase 1 en ~6.5 días).

El activo de largo plazo no es el código — son los datos que el hub acumulará una vez que funcione correctamente. Para asegurar que esos datos entren limpios desde el día uno, cualquier reporte que el equipo P.I.A.R. entregue al hub debe seguir el data contract de la Sección 8: JSON, snake_case, campaign_id obligatorio, data_quality_flags en vez de valores por defecto, y raw_data siempre presente.

**Recomendación operativa inmediata:** compartir este informe con el ingeniero de sistemas y confirmar si el hub nuevo va a recibir los reportes de campaña como archivo .json o si prefiere un endpoint/API.

---

*Documento generado por La Web Figital Agency · 10-07-26 · Uso interno*
