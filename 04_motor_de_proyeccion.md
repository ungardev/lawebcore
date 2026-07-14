# Motor de Proyección — Especificación Técnica

## Metodología

Definida en el Informe Metodológico P.I.A.R. (jun 2026): promedio ponderado por tier, con peso temporal. **No regresión estadística** — con menos de 10 campañas por marca en la mayoría del portafolio, una regresión da resultados estadísticamente frágiles y crea una ilusión de precisión imposible de defender frente a un cliente que pregunte "¿de dónde salió este número?". El promedio ponderado con celdas/valores visibles se defiende en 30 segundos.

## Query base (para proyectar una Marca + Tier específicos)

```sql
SELECT Publicaciones.*, Campañas.fecha
FROM Publicaciones
JOIN Campañas ON Publicaciones.campaña_id = Campañas.id
JOIN Influencers ON Publicaciones.influencer_handle = Influencers.handle
WHERE Campañas.marca_id = :marca_id
  AND Influencers.tier = :tier
ORDER BY Campañas.fecha DESC
```

## Algoritmo paso a paso

1. **Selección de histórico.** Contar campañas *únicas* resultantes del query (no filas de publicación).
   - Si ≥ 3 campañas → usar hasta las 5 más recientes. Se etiqueta `fuente: 'marca'`.
   - Si < 3 campañas → repetir el query filtrando por `Marcas.cliente_id → Clientes.industria` en vez de por marca específica (pool de sector). Se etiqueta `fuente: 'sector'`.

2. **Peso temporal.** Campañas con `fecha` dentro de los últimos 6 meses → peso 1.5. Más antiguas → peso 1.0.

3. **Promedio ponderado** de `er` (engagement rate) y `vistas` por publicación, ignorando valores `N/A` (nunca tratarlos como 0 — ver regla en `02_modelo_de_datos.md`).

4. **KPIs derivados:**
   - `alcance_proyectado = vistas_proyectadas × 0.70` (punto medio del rango 0.65–0.75 documentado)
   - `engagement_proyectado = alcance_proyectado × er`
   - `posts_virales_esperados = round(num_posts_planeados × 0.10)`

5. **Generación de 3 escenarios** — multiplicar únicamente los campos de **volumen** (vistas, alcance, engagement proyectados):
   - Conservador ×0.75
   - Base ×1.0
   - Optimista ×1.30
   - Las **tasas** (ER, retención) no se escalan entre escenarios — solo el volumen cambia con el escenario.

6. **Auditoría.** Cada resultado por tier se etiqueta con `fuente: 'marca' | 'sector'`, visible en la interfaz, para poder explicarle al cliente de dónde sale cada cifra.

## Constantes del sistema (todas nombradas, cero valores hardcodeados dispersos en el código)

```
MESES_RECIENTE = 6
PESO_RECIENTE = 1.5
PESO_ANTIGUO = 1.0
MIN_CAMPANAS_POR_MARCA = 3
MAX_CAMPANAS_CONSIDERADAS = 5
ESCENARIOS = { conservador: 0.75, base: 1.0, optimista: 1.30 }
FACTOR_ALCANCE = 0.70
TASA_VIRAL_ESPERADA = 0.10
```

## Entradas requeridas para correr una proyección

- Marca objetivo
- Distribución de posts planeados por tier (ej. `{ nano: 10, micro: 4 }`)
- Fecha de referencia (hoy, por defecto)

## Salidas

Por cada tier solicitado: KPIs proyectados en los 3 escenarios + fuente del dato (marca/sector). Más un total agregado de campaña sumando todos los tiers, también en 3 escenarios.

## Prototipo de referencia

Ya existe una implementación funcional en JavaScript puro (`piar_modelo_proyeccion.js`), probada con datos de ejemplo, que el ingeniero puede usar como referencia directa del algoritmo completo. Solo requiere adaptar la función `seleccionarHistorico()` para que consulte Supabase (vía el query de la sección anterior) en vez de un array en memoria — el resto de la lógica (peso temporal, promedios, escenarios) es reutilizable tal cual.

## Documentos relacionados

- `02_modelo_de_datos.md`
- `05_funcionalidad_del_sistema.md`
