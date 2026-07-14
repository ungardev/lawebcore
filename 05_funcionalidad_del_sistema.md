# Funcionalidad del Sistema — Vistas e Interacciones

## Ubicación dentro de La Web Core

No es una sección nueva de navegación aislada — vive integrado en las secciones que ya existen (Dashboard, Campañas, Pipeline, Influencers), siguiendo la lógica de segmentación por marca que ya tiene el sistema.

## Flujo completo por sección

### Dashboard (ya existe — sin cambios estructurales)
Resumen agregado de TODAS las campañas. Las tarjetas que hoy están vacías o en cero (Reach total, ER promedio, Influencers) empiezan a poblarse solas una vez que `Publicaciones` e `Influencers` tengan datos reales — no requiere trabajo adicional de UI.

### Campañas (ya existe, se extiende)

- Segmentado por marca.
- **Crear campaña nueva:** formulario con los campos requeridos (marca, tiers, objetivo, budget, # influencers). Al guardar, se propaga automáticamente a Pipeline e Influencers según la marca correspondiente.
- **Ficha de campaña individual (vista nueva):** hoy la lista de Campañas no tiene detalle al hacer clic. Se necesita una vista que muestre:
  - Gráfico de KPIs de la campaña
  - Info completa: likes, comentarios, desglose de sentimiento de comentarios (positivo/negativo/neutro), visualizaciones totales
  - Actualización en vivo a medida que entran publicaciones nuevas (no es un snapshot estático)
- **Proyección:** dentro del contexto de una marca, los gráficos acumulados de sus campañas pasadas alimentan la proyección de una campaña futura para esa misma marca, aplicando el motor descrito en `04_motor_de_proyeccion.md`. El usuario define cuántos posts planea por tier para la campaña nueva, y el sistema devuelve la banda de 3 escenarios.

### Pipeline (ya existe)
Mismo criterio de segmentación por marca. Sin cambios funcionales adicionales identificados por este proyecto.

### Influencers (ya existe, pieza crítica pendiente)

- Punto donde se conecta la cuenta de Instagram del creador (vía API — decisión build-vs-buy pendiente, ver `01_objetivo_y_alcance.md`).
- Las publicaciones se etiquetan con el # de campaña para que el sistema las asocie automáticamente.
- **Prerrequisito inmediato, independiente de si se resuelve la API:** poblar esta tabla con tier por creador (ver `03_fuente_y_mapeo_de_datos.md`). Sin esto, el motor de proyección no tiene con qué desagregar campañas etiquetadas MIX.

## Fuera de alcance v1 (a evaluar en fases posteriores)

- Exportación de reportes/PDF para cliente directamente desde el sistema.
- Comparativa simultánea multi-marca en una sola vista.
- Edición manual de datos históricos desde el dashboard (v1 es de solo lectura sobre el histórico consolidado).

## Documentos relacionados

- `01_objetivo_y_alcance.md`
- `04_motor_de_proyeccion.md`
