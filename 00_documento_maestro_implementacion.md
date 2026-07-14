# Sistema de Proyección P.I.A.R. — Documento Maestro de Implementación

**Para:** Ingeniero de sistemas — La Web Core
**De:** Cristóbal Gallardo León — La Web Figital Agency
**Estado:** Concepto aterrizado, listo para evaluación técnica e implementación
**Documentos de apoyo:** `01_objetivo_y_alcance.md` · `02_modelo_de_datos.md` · `03_fuente_y_mapeo_de_datos.md` · `04_motor_de_proyeccion.md` · `05_funcionalidad_del_sistema.md`

---

## 1. Resumen ejecutivo

El Sistema de Proyección P.I.A.R. es una funcionalidad nueva integrada dentro de **La Web Core** (no una app aparte). Permite:

1. Ver el histórico real de KPIs de cada campaña, segmentado por marca.
2. Generar proyecciones de campañas futuras para una marca, basadas en su propio histórico (o en el histórico del sector, si la marca es nueva).
3. Trackear publicaciones de creadores de forma automática o semi-automática, con desglose de sentimiento de comentarios.

No reemplaza nada de lo que ya existe en La Web Core — se apoya en las entidades `Clientes`, `Marcas`, `Campañas` e `Influencers` que ya están en Supabase, y agrega una entidad nueva: `Publicaciones`.

## 2. Qué existe hoy vs. qué falta

| Pieza | Estado |
|---|---|
| Esquema de `Clientes`, `Marcas`, `Campañas`, `Influencers` | ✅ Existe en Supabase |
| `Clientes.Industria` (= sector) | ⚠️ Campo existe, está vacío |
| `Influencers.Tier` | ⚠️ Campo existe, tabla vacía (0 registros) |
| Tabla `Publicaciones` (métricas por creador/publicación) | ❌ No existe — hoy vive solo en Sheets de detalle |
| Vista de detalle de campaña (gráfico + KPIs completos) | ❌ No existe en la UI actual |
| Motor de proyección | ❌ No implementado — spec completa en `04_motor_de_proyeccion.md`, con prototipo JS de referencia |
| Conexión API de Instagram para tracking de publicaciones | ❌ No implementado — decisión build-vs-buy pendiente |
| Análisis de sentimiento de comentarios | ❌ No implementado — depende de acceso a comentarios vía API |

## 3. Orden de trabajo recomendado

No todo depende de resolver la API de Instagram. Este orden permite avanzar en paralelo:

**Fase 1 — Prerrequisitos de datos (no depende de ninguna decisión de API)**
1. Poblar `Clientes.Industria` (mapeo corto, 14 clientes)
2. Poblar `Influencers` con tier por creador, cruzando contra la base de creadores existente del proyecto de discovery
3. Crear la tabla `Publicaciones` en Supabase (esquema en `02_modelo_de_datos.md`)
4. Migrar el histórico de las Sheets de detalle a `Publicaciones` (requiere acceso al Drive empresarial — ver `03_fuente_y_mapeo_de_datos.md`)

**Fase 2 — Motor de proyección**
5. Implementar el algoritmo de `04_motor_de_proyeccion.md` contra Supabase, usando `piar_modelo_proyeccion.js` como referencia de la lógica
6. Exponer la proyección en la UI dentro del contexto de marca en la sección Campañas (ver `05_funcionalidad_del_sistema.md`)

**Fase 3 — Ficha de campaña con datos en vivo**
7. Construir la vista de detalle de campaña (gráfico + KPIs completos + comentarios)
8. Definir mecanismo de actualización en vivo (polling, webhook, o refresco manual — a decidir según cómo llegue el dato en Fase 4)

**Fase 4 — Automatización de captura (paralela, decisión de negocio pendiente)**
9. Evaluar build vs. buy para la conexión con Instagram
10. Implementar clasificación de sentimiento de comentarios (candidato: Claude API)

## 4. Decisiones ya tomadas (no reabrir sin razón)

- Metodología de proyección: **promedio ponderado por tier + peso temporal**, explícitamente **sin regresión estadística**.
- Salida siempre en **3 escenarios** (conservador ×0.75 / base ×1.0 / optimista ×1.30), nunca un solo número.
- Cero valores hardcodeados dispersos — todas las constantes metodológicas nombradas y centralizadas (ver `04_motor_de_proyeccion.md`).
- El sistema es de **solo lectura** sobre el histórico en v1 — no hay edición manual de datos desde el dashboard.
- Los valores faltantes se representan como `N/A`, nunca como `0`, para no distorsionar los promedios.
- Fuente de verdad: **Supabase**, no Google Sheets en vivo.

## 5. Decisiones abiertas (requieren definición antes de esas fases)

| Decisión | Dónde se define | Bloquea |
|---|---|---|
| API de Instagram: construir vs. pagar proveedor | `01_objetivo_y_alcance.md` | Fase 4 únicamente — no bloquea Fases 1-3 |
| Mapeo exacto Cliente → Industria | `03_fuente_y_mapeo_de_datos.md` | Fase 1, paso 1 |
| Mecanismo de actualización en vivo de la ficha de campaña | `05_funcionalidad_del_sistema.md` | Fase 3, paso 8 |

## 6. Entregables de referencia disponibles

- `piar_modelo_proyeccion.js` — implementación funcional del motor de proyección en JS puro, probada con datos de ejemplo (marca con histórico suficiente + marca con fallback a sector).
- Prototipo visual en React/recharts del panel de proyección (referencia de UX, no de arquitectura final).

## 7. Preguntas para el ingeniero antes de arrancar Fase 1

- ¿Prefieres que la migración de Sheets → `Publicaciones` sea un script de una sola corrida, o un proceso repetible por si aparecen más Sheets de detalle históricas no migradas?
- ¿La tabla `Publicaciones` debería vivir con un `influencer_id` (FK numérico) en vez de `handle` como llave, para mayor integridad referencial? (Recomendado, ajustar si el esquema de `Influencers` ya usa un id propio.)
