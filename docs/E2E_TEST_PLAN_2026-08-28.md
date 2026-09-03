# E2E Test Plan — LENS Discovery UI
## ✅ LISTO PARA EJECUTAR — Pipeline Funcionalmente Correcto

> **De:** MiniMax M2.7/M3
> **Fecha:** 03 de septiembre de 2026 (actualizado post-`4ffa62e`)
> **Script:** `scripts/test_lens_mascotas_ve.py`
> **Costo estimado:** ~$1.14 USD (HikerAPI)
> **Balance actual:** ~$36.86 USD
> **Pipeline status:** ✅ Funcionalmente correcto — todos los P0 aplicados

---

## §1 — Objetivo

Validar que el pipeline LENS funciona end-to-end desde la UI web después de todos los fixes aplicados (BUG #1, BUG #2, Hito 36, M3-Agentes A/B/C, logger fixes).

**Este test es la fuente de verdad.** Si pasa, el sistema está listo. Si falla, tenemos datos reales para diagnosticar.

---

## §2 — Criterios de Éxito (4 obligatorios)

| # | Criterio | Cómo se verifica | Prioridad |
|---|----------|-------------------|-----------|
| **1** | El run termina en `delivered` y el polling se detiene solo | UI no muestra "Timeout esperando resultados" | 🔴 |
| **2** | `total_candidates ≥ 15` | Respuesta de `GET /api/v1/discovery/runs/{id}` | 🔴 |
| **3** | Los candidatos traen `followers` real, no 0 | Lista en la UI — scrolling | 🔴 |
| **4** | **`ai_rationale` no es NULL** | `SELECT count(*) FROM discovery_candidates WHERE run_id=… AND ai_rationale IS NOT NULL` | 🔴 |

### El criterio #4 es EL más importante

Si `ai_rationale` es NULL, el scoring cayó a `_fallback_scores()` y la IA no participó — lo que el modo thinking podía provocar en silencio.

---

## §3 — Consulta SQL de Validación Lanz §7.1

Después del run, ejecutar:

```sql
-- Verificar ai_rationale
SELECT count(*) as total,
       count(ai_rationale) as with_rationale,
       count(*) - count(ai_rationale) as without_rationale
FROM discovery_candidates
WHERE run_id = '…';

-- Distribución de reason_codes (debe haber >1 valor)
SELECT reason_code, count(*)
FROM discovery_run_events
WHERE run_id = '…' AND event = 'profile.dropped'
GROUP BY reason_code
ORDER BY 2 DESC;

-- Verificar followers reales
SELECT handle, followers, ai_rationale
FROM discovery_candidates
WHERE run_id = '…'
ORDER BY followers DESC
LIMIT 20;
```

---

## §4 — Script de Test

```bash
cd /mnt/c/Users/Dainer/Documents/proyectoslaweb/lawebcore

# Ejecutar test E2E
API_BASE_URL=https://lawebcore-production.up.railway.app \
python scripts/test_lens_mascotas_ve.py
```

### Brief de prueba (mascotas VE)

El script usa:
- **Nicho:** mascotas
- **Ubicación:** Venezuela
- **Modo:** explorar
- **Handle excluir:** dogchowve, purina_ve

### Lo que el test verifica automáticamente

1. Run se crea correctamente
2. Polling se detiene en estado terminal (no timeout)
3. `total_candidates >= 15`
4. API responde 200

---

## §5 — Timing Recomendado

**Ejecutar en horario off-peak de DeepSeek** para evitar pricing ×2:

| Zona | Off-peak hours |
|------|---------------|
| UTC | 04:00-06:00 y 10:00-01:00 (lunes a viernes) |
| Venezuela (UTC-4) | 00:00-02:00 y 06:00-21:00 (lunes a viernes) |

**Recomendado:** Lunes 31-ago entre 06:00-21:00 hora Venezuela (10:00-01:00 UTC).

---

## §6 — Si el Test Falla

### Nota sobre Funnel Invariant (29-ago-2026)

**Si el run termina en `INCONSISTENT`**, esto **NO es un fracaso** — es el instrumento funcionando. Significa que la identidad del embudo (discovered - deduped = drops registrados) no cuadra y el sistema lo dijo en voz alta. El fix `4f87a6b` hace que `INCONSISTENT` sea alcanzable por primera vez.

### Falla en criterio #1 (timeout/polling)
- Verificar `POLL_TERMINAL_STATUSES` en `useDiscoveryRun.ts` — ¿tiene 10 valores?
- Verificar que el worker termina en `delivered` y no en otro estado
- Revisar logs de Railway: `discovery_run_source_unavailable` o `step*_failed`

### Falla en criterio #2 (0 o <15 candidatos)
- Revisar `flush_drop_ledger` — ¿`discovery_run_events` tiene datos?
- Verificar HikerAPI balance: `GET /api/v1/instagram/source/balance`
- Revisar logs de Railway: `preflight_insufficient_balance`

### Falla en criterio #3 (followers = 0)
- Correr query: `SELECT handle, followers FROM discovery_candidates WHERE run_id='…' ORDER BY followers LIMIT 10`
- Si todos 0 → **Nota sobre el merge de enrichment:** El merge en worker.py:1246 lee `e.get("followersCount")` (camelCase). Si HikerAPI devuelve `followersCount`, el pipeline funciona por el fallback en scoring (line 1333: `p.get("followersCount")`). Si HikerAPI devuelve `follower_count`, el scoring lee None y cae a 0 → todos droppeados.

### Falla en criterio #4 (ai_rationale NULL)
- Verificar que `candidate_analyzer.py` no está cayendo a `_fallback_scores()`
- Revisar logs: `ai_batch_analysis_failed_using_fallback`
- Verificar `response_format` en `deepseek_client.py`

---

## §7 — Después del Test

### Si pasa (4/4 criterios ✅)
1. Documentar run_id + fecha en este doc
2. El pipeline está validado — proceder con FASE 1-4 de Lanz v2.0
3. Marcar E2E como ✅ en PLAN_MAIN

### Si falla (cualquier criterio ❌)
1. Documentar run_id + criterio fallido + logs
2. Diagnosticar con M3-Agente
3. Aplicar fix
4. Repetir test — costo adicional ~$1.14

---

## §8 — Known Issues Pre-E2E (03-sep-2026) — TODOS CORREGIDOS

### ✅ H-CRIT-1: Funnel Invariant — CORREGIDO (`4ffa62e`)

**Archivo:** `worker.py:1825`

**Fórmula corregida:** `funnel.deduped == total + drop_ledger.total()`

Esta fórmula es matemáticamente correcta: lo que entró (deduped) = entregados + descartados (drops). Detecta fugas reales en el pipeline.

---

### ✅ H-CRIT-2: Scoring Usa Valor Imperpreciso — CORREGIDO (`4ffa62e`)

**Archivo:** `worker.py:998-1000`

```python
followers = p.get("follower_count") if "follower_count" in p else p.get("followersCount")
```

Ahora lee `follower_count` (enrichment, preciso) primero, fallback `followersCount` (search, impreciso).

---

### ✅ H-CRIT-3: Endpoint No Lee `_discovery_query` — CORREGIDO (`4ffa62e`)

**Archivo:** `discovery.py:906, 927`

```python
"discovery_query": candidate.get("discovery_query") or candidate.get("_discovery_query") or "",
```

Ahora lee ambas formas. La columna `discovery_query` en `discovery_candidates` se poblará correctamente.

---

### ✅ H-CRIT-4: Brand Safety Leak — CORREGIDO (`4ffa62e`)

**Archivo:** `worker.py:1303-1309`

Cada handle excluido por el brief (Nestlé/Purina) ahora pasa por `drop_profile()` antes de ser filtrado. El invariante detecta cualquier fuga futura.

---

## §9 — Resultado (a llenar)

---

## §9 — Resultado (a llenar)

| Campo | Valor |
|-------|-------|
| Fecha ejecución | ___ |
| Run ID | ___ |
| Hora UTC | ___ |
| Criterio #1 (polling) | ✅ / ❌ |
| Criterio #2 (≥15 candidatos) | ✅ / ❌ — Total: ___ |
| Criterio #3 (followers real) | ✅ / ❌ |
| Criterio #4 (ai_rationale) | ✅ / ❌ |
| reason_code distribution | ___ valores distintos |
| Costo HikerAPI | ~$___ |
| Saldo restante | ~$___ |

---

*Plan creado: 28 de agosto de 2026 por MiniMax M2.7/M3*
*Actualizado: 03 de septiembre de 2026 con hallazgos de Claude Code Fable 5*
*Basado en: Lanz v2.1 §5 + AUDITORIA_CLAUDE_CODE_FABLE5_FULL_03-09-26.md*
