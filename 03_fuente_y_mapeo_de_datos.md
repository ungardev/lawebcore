# Fuente y Mapeo de Datos Reales

## Arquitectura objetivo

Supabase es la fuente de verdad de todo el sistema. El módulo de proyección **no lee Google Sheets en vivo** — lee de Supabase, igual que el resto de La Web Core (Clientes, Marcas, Campañas, Influencers).

## Pasos de migración necesarios (trabajo de una sola vez, no recurrente)

1. **Poblar `Clientes.Industria`** — mapeo corto, son 14 clientes registrados. Ejemplo de criterio:
   - Nestlé, Nescafé, Dolce Gusto → Alimentos y Bebidas
   - Movilnet → Telecomunicaciones
   - Polar, Solera, Cervezería → Bebidas / Cervecería
   - Pepsico, Ruffles → Alimentos

2. **Poblar `Influencers`** — extraer la lista de creadores únicos (Usuario IG) de todas las Sheets de detalle históricas y asignarles tier. Fuente ideal: la base de creadores por tier que ya existe del proyecto de discovery pausado (estructurada en 5 hojas: Nano, Micro, Mid, Macro, Mega). Donde no haya match contra esa base, el tier queda pendiente de asignación manual.

3. **Crear la tabla `Publicaciones`** en Supabase con el esquema definido en `02_modelo_de_datos.md`.

4. **Migrar el histórico** de las Sheets de detalle (Dolce Gusto, OREO, La Monserratina, y las que sigan apareciendo bajo el patrón `Metricas_Campana_Insights_*`) a `Publicaciones`, enlazando cada fila:
   - Por **Campaña** — usando el Código de campaña del índice maestro "HISTORIAL DE CAMPAÑAS - LA WEB" como referencia
   - Por **Influencer** — usando el Usuario IG (Handle)

## Nota sobre la cuenta de Google

Las Sheets de trabajo real (índice maestro + detalle por campaña) viven en el correo empresarial del equipo, no en la cuenta personal conectada en las sesiones de este chat. La migración deberá ejecutarse con acceso a esa cuenta — vía el ingeniero de sistemas, o conectando ese Drive específico en una sesión de trabajo aparte.

## Estructura de origen ya identificada

**Índice maestro** ("HISTORIAL DE CAMPAÑAS - LA WEB"): una fila = una campaña completa. Columnas relevantes: Fecha, Cliente, Marca, Nombre, INF-TYPE (tier o MIX), Objetivo, Status, KPIs Total agregados (Videos, Reach, Engagement, ER X, Views X, Retención X).

**Sheets de detalle** (una por campaña, ej. `Metricas_Campana_Insights_Dolce_Gusto`): una fila = un creador en una publicación. Columnas: fecha, nombre, usuario IG, email, alcance, vistas, likes, comentarios, compartidos, guardados, tiempo de retención, ER Alcance %, ER Vistas %. **No incluyen seguidores ni tier** — de ahí la necesidad del cruce contra la base de creadores (paso 2 arriba).

## Fuente futura (post-decisión de API de Instagram)

Una vez resuelta la decisión de build-vs-buy de la integración con Instagram (ver `01_objetivo_y_alcance.md`), la tabla `Publicaciones` se alimenta automáticamente por publicación etiquetada con el # de campaña, sin pasar por Sheets. El esquema de la tabla no cambia — solo cambia el mecanismo que la llena.

## Documentos relacionados

- `01_objetivo_y_alcance.md`
- `02_modelo_de_datos.md`
