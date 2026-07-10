# Data Contract P.I.A.R. — Formato de Reporte para el Hub

**Versión:** 1.0
**Fecha:** 10-07-26
**Referencia:** Basado en `06_informe_tecnico_audit_ism.md` §8
**Estado:** Estándar activo — todos los reportes al hub deben seguir este formato

---

## 1. Propósito

Este documento estandariza el formato en que el equipo P.I.A.R. entrega datos de campañas al hub de La Web Core. Seguir este formato garantiza que:

1. Ningún parser tenga que adivinar mapeos español → inglés nunca más (bug C-01 resuelto)
2. `campaign_id` sea siempre obligatorio (bug C-02 resuelto)
3. Los campos derivados se calculen automáticamente (bug C-03)
4. `raw_data` siempre esté presente (bug C-04 resuelto)
5. NULL vs 0 se maneje correctamente en todo el pipeline (bug C-07 resuelto)

---

## 2. Reglas del contrato

| Regla | Detalle |
|---|---|
| **Formato** | JSON array de objetos. Nunca markdown, nunca "K" o "M" |
| **Encoding** | UTF-8 sin BOM |
| **Números** | Siempre crudos: `45200`, nunca `"45.2K"` ni `"45,200"` |
| **snake_case** | Todos los keys en inglés, calzando 1:1 con columnas Supabase |
| **campaign_id** | **OBLIGATORIO** en cada fila. UUID válido de Supabase |
| **raw_data** | **OBLIGATORIO** en cada fila — la fila original sin transformar |
| **data_quality_flags** | Array de strings describiendo qué campos faltan. Reemplaza valores por defecto |
| **NULL handling** | Campo faltante → `null` en JSON. Campo con valor 0 → `0`. Nunca mezclarlos |

---

## 3. Estructura de una publicación (schema JSON)

```json
{
  "username": "usuario1",
  "followers": 12300,
  "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
  "campaign_name": "#PorFinIlimitados",
  "post_date": "11-12-2025",
  "post_url": "https://instagram.com/p/xxxx",
  "views": 5600,
  "likes": 410,
  "comments": 22,
  "saves": 9,
  "shares": 5,
  "engagement_total": 446,
  "er_views": 7.96,
  "er_alcance": null,
  "virality_index": 0.46,
  "retention_avg": null,
  "data_quality_flags": ["retention_missing"],
  "raw_data": {
    "Nombre de usuario": "usuario1",
    "Vistas": "5,600",
    "Me Gusta": "410",
    "Comentarios": "22",
    "Guardados": "9",
    "Compartidos": "5",
    "Fecha de publicación": "11/12/2025"
  }
}
```

### Campos

| Campo | Tipo | ¿Obligatorio? | Descripción |
|---|---|---|---|
| `username` | string | ✅ Sí | Handle del influencer sin @ |
| `followers` | int | Recomendado | Seguidores en el momento de la publicación |
| `campaign_id` | UUID | ✅ **OBLIGATORIO** | ID de campaña en Supabase |
| `campaign_name` | string | Recomendado | Nombre de campaña (para auditoría) |
| `post_date` | string | ✅ Sí | Fecha (DD-MM-AA o ISO 8601) |
| `post_url` | URL | Recomendado | URL directa de la publicación |
| `views` | int | Recomendado | Vistas de la publicación |
| `likes` | int | Recomendado | Likes |
| `comments` | int | Recomendado | Comentarios |
| `saves` | int | Recomendado | Guardados / Saves |
| `shares` | int | Recomendado | Compartidos / Shares |
| `engagement_total` | int | Auto | Calculado: likes+comments+saves+shares si se omite |
| `er_views` | float | Auto | (engagement_total / views) × 100 si se omite |
| `er_alcance` | float | Auto | (engagement_total / reach) × 100 si se omite |
| `virality_index` | float | Auto | views / followers si se omite |
| `retention_avg` | float | Recomendado | **Segundos promedio por vista**, no total acumulado |
| `data_quality_flags` | array | ✅ Sí | Banderas de campos faltantes |
| `raw_data` | object | ✅ **OBLIGATORIO** | Fila original sin transformar |

### Flags válidos para `data_quality_flags`

| Flag | Significado |
|---|---|
| `engagement_missing` | Likes, comentarios, guardados o compartidos no disponibles |
| `views_missing` | Vistas no disponibles |
| `reach_missing` | Alcance no disponible |
| `followers_missing` | Seguidores en momento de publicación no disponibles |
| `retention_missing` | Tiempo de reproducción no disponible |
| `no_post_url` | No se proporcionó URL de la publicación |
| `date_estimated` | La fecha es aproximada o inferida |

---

## 4. ⚠️ Regla crítica sobre `retention_avg`

> **Hallazgo confirmado en el audit ISM (§4):** el campo "Total segundos" del Google Form es **tiempo de reproducción ACUMULADO** (suma de todas las vistas), **NO un promedio**.

**正确 (correcto):**
```
retention_avg = total_watch_time_seconds / views
```

**❌ Incorrecto (no dividir):**
```
retention_avg = total_watch_time_seconds  → resultados absurdamente altos
```

**Ejemplo real del audit (@edualvrz, MOVILNET):**
```
total_watch_time_seconds: 102,864 (28h34min de reproducción total)
views: 22,722
retention_avg_correcta = 102,864 / 22,722 = 4.53 segundos por vista
```

Si la fuente ya proporciona `retention_avg` ya calculado como promedio, se usa directamente.

---

## 5. Paso 0 — Checklist antes de generar un reporte

**OBLIGATORIO** antes de compilar cualquier reporte. Responder cada punto:

```
REPORTE HUB DE [NOMBRE DE CAMPAÑA]
Fecha de corte: [DD-MM-AAAA]
Generado por: [nombre del operador]

CHECKLIST PRE-REPORTE:

□ 1. Campaña exacta confirmada: [nombre] (ID: [UUID])
□ 2. Fecha de corte confirmada: [DD-MM-AAAA]
□ 3. Fuentes a combinar:
     - [ ] Google Form / CSV manual
     - [ ] Metricool / otra herramienta
     - [ ] HypeAuditor (si disponible — en nuestro hub, NO SE USA)
     - [ ] Meta Graph API / TikTok Display API
     Prioridad si hay conflicto: [definir orden]
□ 4. ¿HypeAuditor disponible? [SÍ/NO]
     (En La Web Core no se usa — usamos los clones propios: AQS, Authenticity, etc.)
□ 5. ¿Capturas de retención disponibles? [SÍ/NO/N/A]
□ 6. Perfiles del pull que realmente publicaron: [N] de [X] en el pull
     (Excluir: perfiles que fueron invitados pero no publicaron)
□ 7. Notas / observaciones:
     [ ]
```

**Este checklist se adjunta como metadata del reporte.**

---

## 6. Canales de entrega

### Canal recomendado: `POST /api/v1/imports/json`

El formato JSON se envía directamente al endpoint REST del hub:

```bash
curl -X POST https://lawebcore-production.up.railway.app/api/v1/imports/json \
  -H "Content-Type: application/json" \
  -H "X-User-Email: operador@laweb.agency" \
  -d @reporte_campana.json
```

Respuesta:
```json
{
  "inserted": 47,
  "updated": 3,
  "skipped": 2,
  "errors": [
    {"row": 12, "reason": "campaign_id '...' no encontrado en la base de datos", "data": {"username": "..."}},
    {"row": 35, "reason": "campaign_id obligatorio según el data contract (C-02)", "data": {"username": "..."}}
  ],
  "total_rows": 52
}
```

### Canal alternativo: CSV Upload

Si el equipo prefiere subir CSV:
1. Descargar la plantilla: `GET /api/v1/imports/template`
2. Llenar las columnas (español o inglés — el sistema detecta automáticamente)
3. Subir: `POST /api/v1/imports/csv` con `campaign_id` como form field

---

## 7. Ejemplo completo de reporte

```json
[
  {
    "username": "mnakary",
    "followers": 285000,
    "campaign_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "campaign_name": "#PorFinIlimitados",
    "post_date": "2025-12-11",
    "post_url": "https://instagram.com/p/CM2kQZHJYdF/",
    "views": 22722,
    "likes": 1100,
    "comments": 15,
    "saves": 10,
    "shares": 5,
    "engagement_total": 1130,
    "er_views": 4.97,
    "er_alcance": null,
    "virality_index": 0.08,
    "retention_avg": null,
    "data_quality_flags": ["retention_missing"],
    "raw_data": {
      "Nombre de usuario": "mnakary",
      "Vistas": "22722",
      "Me Gusta": "1100",
      "Comentarios": "15",
      "Guardados": "10",
      "Compartidos": "5",
      "Fecha de publicación": "11/12/2025",
      "Total segundos": "102864"
    }
  }
]
```

---

## 8. Validación automática

El endpoint `/api/v1/imports/json` valida automáticamente:

1. ✅ `campaign_id` es un UUID válido y existe en Supabase
2. ✅ `raw_data` está presente y es un objeto
3. ✅ `data_quality_flags` se auto-genera si se omiten campos
4. ✅ Los campos derivados se calculan si se omiten
5. ✅ La idempotencia: si `post_url` ya existe → actualiza, no duplica

Si alguna fila falla la validación, se reporta en `errors` con el número de fila + razón específica.

---

*Documento generado por La Web Figital Agency · 10-07-26 · Uso interno*
