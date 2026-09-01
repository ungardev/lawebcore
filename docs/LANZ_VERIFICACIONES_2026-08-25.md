# Verificaciones Lanz §8 + H-2 — Resultado

**Fecha:** 2026-08-26
**Último commit verificado:** `bd973c7` (Hitos 30-34 aplicados)
**Commit verificado originalmente para V0:** `81db353`

| # | Pregunta | Respuesta | Evidencia | Bloquea |
|---|----------|-----------|-----------|---------|
| V0 | TIER_MIN_FOLLOWERS ¿filtro duro? | **NO** | `worker.py:54` definido pero NO usado como filtro. Filtro real = `plan.min_followers` del brief | Ninguno ✅ |
| V1 | ¿Qué modelo de IA en Railway? | **Por verificar** | Requiere acceso al panel Railway | Hito 34 |
| V2 | deepseek-v4-flash ¿resuelve? | **✅ Sí** | `config.py:55` actualizado a `deepseek-v4-flash` (era `deepseek-chat` retired) | Hito 34 |
| V3 | PITR activado | **Por verificar** | Panel Railway → Postgres → Backups | Riesgo DB |
| V4 | Redis eviction policy | **Por verificar** | Panel Railway → Redis → Settings | Contadores |

## V0 Detalle

`TIER_MIN_FOLLOWERS = 500` en `worker.py:64`:
- **Definido** pero **nunca usado** como filtro directo (grep confirma: 0 refs más allá de la definición)
- El filtro real es `plan.min_followers` (línea 1347) que viene del brief
- `TIER_MAX_FOLLOWERS = 50_000` se usa como `max_followers_cap` (línea 1271) pero es overridable por `brief.influencer_preferences.max_followers`
- Los 4 tiers (NANO/MICRO/MID/MACRO) se usan solo para distribución en `_rerank_diversified` (línea 119-136), no para filtrar

**Conclusión V0:** H-2 NO es bloqueante. El sistema NO excluye NANO por diseño de constants. El tier que genera 80-85% de views (NANO) está disponible si el brief lo pide. Valor corregido de 5_000 → 500 según código real en `worker.py:64`.

## V1-V4

Requieren acceso al panel de Railway. Son verificaciones operacionales, no bloquean código.

## Conclusión General

**Hitos 30-34 aplicados** (commit `bd973c7`). Pendientes: Hitos #0 (regresión merge), #1-#10 según plan detallado.

Las verificaciones V1-V4 son operacionales y no bloquean código. Deben ejecutarse en Railway cuando sea posible.
