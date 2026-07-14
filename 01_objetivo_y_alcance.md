# Objetivo y Alcance — Sistema de Proyección P.I.A.R.

## Qué es

Funcionalidad de proyección de campañas integrada dentro de **La Web Core** (no es una aplicación aparte). Está pensada para que el equipo P.I.A.R. tenga su propio HypeAuditor interno: analítica de influencers construida sobre datos 100% propios, sin depender de herramientas externas de pago.

## Qué hace

1. Consolida el histórico de KPIs por marca y por tier de creador (nano → mega).
2. Genera proyecciones de campañas nuevas usando promedio ponderado por tier + peso temporal + fallback a sector + 3 escenarios (conservador / base / optimista).
3. Deja auditable el origen de cada número (histórico propio de la marca vs. fallback al histórico del sector).
4. Sirve como fuente de gráficos y datos para armar presentaciones a cliente. El equipo extrae manualmente lo que necesita — el sistema no genera el reporte de cliente automáticamente en v1.

## Para quién

Uso interno del equipo P.I.A.R. La salida (gráficos, cifras, proyecciones) se usa después como insumo para presentaciones de cliente armadas por fuera del sistema. El sistema en sí no es cliente-facing.

## Fuera de alcance v1

- No reemplaza el motor de scoring individual de creadores (sistema aparte, ya existente).
- No incluye el discovery de influencers vía Apify (proyecto pausado, separado).
- Cero regresión estadística — la metodología es explícitamente promedio ponderado, por diseño (ver 04_motor_de_proyeccion.md).
- Sin exportación automática a PDF/reporte de cliente.
- Sin edición manual de datos históricos desde el dashboard.

## Requisito nuevo identificado: análisis de sentimiento de comentarios

La ficha de campaña debe mostrar, además del gráfico de KPIs, el desglose de comentarios por sentimiento (positivo / negativo / neutro). Esto depende de tener acceso al texto de los comentarios (vía API de Instagram) y de un paso de clasificación (candidato natural: Claude API sobre el texto de cada comentario).

## Dependencia crítica: API de Instagram

El flujo objetivo completo (ver más abajo) depende de trackear publicaciones automáticamente vía conexión a Instagram, en vez del flujo actual de captura manual + Google Form.

**Esta decisión sigue abierta:** construir una integración propia contra la Meta Graph API vs. pagar un proveedor externo que ya dé ese acceso. Mientras se resuelve:

- **v1 puede lanzar con datos cargados manualmente** (flujo actual: Form + capturas → Sheets → migración a Supabase), y migrar a la API de Instagram en paralelo, sin cambiar el modelo de datos ni el motor de proyección.
- El motor de proyección es agnóstico a la fuente: consume lo que exista en la tabla `Publicaciones` de Supabase, sin importar cómo llegó ahí.
- Importante: si se decide que la API es prerrequisito de lanzamiento (no en paralelo), esto empuja la fecha de v1 — es una decisión de negocio, no solo técnica.

## Flujo completo del sistema (visión objetivo)

1. **Influencers** — se conecta la cuenta de Instagram del creador (vía API), y sus publicaciones se etiquetan con el # de campaña correspondiente.
2. El sistema trae las métricas de esas publicaciones automáticamente: likes, comentarios, vistas, alcance, etc.
3. Se calculan métricas derivadas: ER, alcance, y sentimiento de comentarios (positivo/negativo/neutro).
4. Esa información se asocia a la campaña correspondiente y se muestra en su ficha (gráfico + info completa), actualizándose en vivo a medida que entran publicaciones nuevas.
5. Cuando una marca acumula varias campañas con datos reales, esos datos alimentan la proyección de campañas futuras para esa misma marca.

## Documentos relacionados

- `02_modelo_de_datos.md`
- `03_fuente_y_mapeo_de_datos.md`
- `04_motor_de_proyeccion.md`
- `05_funcionalidad_del_sistema.md`
- `00_documento_maestro_implementacion.md`
