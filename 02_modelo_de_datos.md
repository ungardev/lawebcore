# Modelo de Datos — Sistema de Proyección P.I.A.R.

## Entidades existentes en Supabase (La Web Core)

### Clientes

| Campo | Uso en proyección |
|---|---|
| Codigo, Nombre | Identificación |
| **Industria** | Resuelve "sector" — es el fallback cuando una marca no tiene histórico propio suficiente. **Está vacío hoy en los 14 clientes registrados; hay que poblarlo.** |
| Website, Estado | Sin uso en proyección |

### Marcas

| Campo | Uso en proyección |
|---|---|
| Marca, Cliente (FK) | Segmentación principal de la proyección |
| Categoria | Sin uso definido aún |
| Estado | Filtra marcas activas |

### Campañas

| Campo | Uso en proyección |
|---|---|
| Codigo, Nombre | Identificación. Una campaña = "un nuevo proyecto". |
| Marca (FK) | Segmentación |
| Tiers[] | Tag de campaña — puede ser un tier único o **MIX** (varios tiers combinados) |
| Objetivo | Awareness / Conversión / Consideración / Gestión de Crisis. No se usa en el cálculo de proyección en v1, se conserva como dato descriptivo. |
| Status | Pipeline de trabajo (Brief → Contactando → Plan de Cuentas → Campaña Interna → Reporte → Terminada). **No es un KPI de resultado**, es estado operativo. |
| # Influencers, Budget | Contexto de la campaña |
| fecha | Usada para el peso temporal (últimos 6 meses ×1.5, resto ×1.0) |

### Influencers

| Campo | Uso en proyección |
|---|---|
| Nombre, Handle | Identificación, cruce con `Publicaciones` |
| **Tier** | Pieza clave: resuelve el tier real por creador, incluso dentro de campañas etiquetadas MIX |
| País, Nichos, Estado | Sin uso definido en v1 |

**Estado actual: 0 registros.** Esto bloquea cualquier desagregación por tier hasta que se pueble (ver `03_fuente_y_mapeo_de_datos.md`).

## Entidad nueva requerida: `Publicaciones`

No existe todavía en Supabase. Hoy esta información vive solo en las Sheets de detalle por campaña (ej. Dolce Gusto, OREO, La Monserratina).

| Campo propuesto | Origen |
|---|---|
| id | Nuevo |
| campaña_id (FK) | `Campañas.Codigo` |
| influencer_handle (FK) | `Influencers.Handle` |
| fecha_publicacion | De la Sheet de detalle |
| vistas, alcance, likes, comentarios, compartidos, guardados | De la Sheet de detalle / futura API de Instagram |
| er_alcance, er_vistas | Ya se calculan en las Sheets actuales |
| retencion | De la Sheet de detalle |
| sentimiento_comentarios (positivo/negativo/neutro) | **Nuevo.** Requiere clasificación del texto de comentarios (solo disponible con acceso vía API de Instagram) |

## Jerarquía completa del modelo

```
Cliente (Industria = sector)
 └─ Marca
     └─ Campaña (Tiers[], Objetivo, Status, fecha)
         └─ Publicación (por Influencer, con Tier resuelto vía tabla Influencers)
```

## Regla importante sobre valores faltantes

Siguiendo la convención ya establecida en el pipeline de extracción actual: usar `N/A` en vez de `0` para cualquier métrica no disponible. Un `0` real (por ejemplo, cero comentarios) y un dato faltante no son lo mismo, y tratarlos igual distorsiona los promedios ponderados del motor de proyección.

## Documentos relacionados

- `01_objetivo_y_alcance.md`
- `03_fuente_y_mapeo_de_datos.md`
- `04_motor_de_proyeccion.md`
