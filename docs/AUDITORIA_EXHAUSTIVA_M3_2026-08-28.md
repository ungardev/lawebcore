# Auditoría Exhaustiva M3-Agente — LENS Discovery Pipeline
## 29 de agosto de 2026 · Iteración 9

> **De:** MiniMax M3-Agent (explore subagent)
> **Repo:** `github.com/ungardev/lawebcore`
> **Commit auditado:** `4f87a6b` (HEAD)
> **Método:** Lectura directa del árbol + análisis del pipeline completo
> **Propósito:** Validar que todos los fixes críticos funcionan correctamente antes del E2E del Lunes

---

## §1 — Resumen Ejecutivo

El pipeline LENS está **funcionalmente listo para E2E**. Todos los bugs que bloqueaban ejecución fueron corregidos. Los fixes críticos (BUG #1, BUG #2, Hito 36, Funnel Invariant) abordan los modos de fallo identificados por Lanz.

**Hallazgos pendientes de FASE 1-4 no bloquean el E2E** — son deuda técnica que se valida con datos reales.

---

## §2 — Análisis Paso a Paso del Pipeline

### 2.1 Flujo Completo (worker.py:267 → final)

```
discovery_run_task (267)
├── Budget check (318)
├── FunnelTracker instantiation (291)
├── DropLedger instantiation (290)
├── STEP 0: Location search (470-551)
├── STEP 1: Hashtag + Topsearch (554-777)
├── STEP 2: Keywords + Geo-boost (584-800)
├── STEP 2.5: Reels (645-667)
├── STEP 3: Profile enrichment (1136-1261)
│   ├── funnel.discovered = len(step1_handles) [line 959]
│   ├── funnel.deduped = len(profiles) [line 960]
│   ├── funnel.prefiltered = len(handles_to_enrich) [line 1093]
│   ├── funnel.enriched = 0 [line 1100]
│   └── funnel.enriched = len(enriched_profiles) [line 1205]
├── STEP 4: Scoring (1293-1701)
│   ├── funnel.scored = len(scored) [line 1703]
│   └── exclude_handles filter
├── STEP 5: AI Analysis (1720-1747)
└── STEP 6: Deduplicate + Insert (1811)
    ├── funnel.delivered = total [line 1814]
    ├── funnel_ok = (step1_handles - profiles) == ledger.total() [line 1823]
    └── funnel.summary() logged [line 1840]
```

### 2.2 Puntos Críticos Verificados

| # | Punto | Estado | Detalle |
|---|-------|--------|---------|
| 1 | **BUG #1 fix** (line 1333) | ✅ VERIFIED | Scorer ahora lee `follower_count` primero |
| 2 | **Enrichment merge** (line 1246) | ⚠️ NOTA | Lee `e.get("followersCount")` — funciona si HikerAPI devuelve `followersCount` |
| 3 | **`_enriched` flag** (line 1245) | ✅ VERIFIED | Se setea correctamente antes de leer follower_count |
| 4 | **`drop_profile` calls** (12 sitios) | ✅ VERIFIED | Todos usan `ledger=drop_ledger` |
| 5 | **`flush_drop_ledger`** (line 1960) | ✅ VERIFIED | Se llama al final del run |
| 6 | **FunnelTracker stages** | ✅ VERIFIED | 6 stages asignados en puntos correctos |
| 7 | **Funnel Invariant** (line 1823) | ⚠️ INCOMPLETO | Solo usa `step1_handles` — matemáticamente incompleto |
| 8 | **`step3_degraded`** (line 1217) | ⚠️ PARCIAL | No se setea si some enrichment succeeds |
| 9 | **Generic Exception catch** (line 1221) | ⚠️ RIESGO | Podría tragar errores de programación |

---

## §3 — El Hallazgo de la Invariante del Embudo

### 3.1 El Fix Aplicado (`4f87a6b`)

**Antes (roto):**
```python
final_status = determine_final_status(
    funnel_invariant_ok=True,  # ← CONSTANTE, FALSO
    ...
)
```

**Después (fix):**
```python
funnel_ok = (len(step1_handles) - len(profiles)) == drop_ledger.total()
final_status = determine_final_status(
    funnel_invariant_ok=funnel_ok,  # ← COMPUTADO DE VERDAD
    ...
)
```

### 3.2 Limitación: Solo step1_handles

El cómputo usa solo `step1_handles` (hashtags), pero los perfiles vienen de:
- step1 (hashtags) → `step1_handles`
- step2 (keywords) → `step2_handles`
- step2.5 (reels) → inline en profiles
- step3 (topsearch) → `step3_handles`
- step4 (suggested) → `step4_handles`

**Impacto:** La cuenta `len(step1_handles) - len(profiles)` no representa todos los descubrimientos. Para runs que usan keywords/reels/topsearch/suggested, el invariante probablemente dará `False` incluso sin fuga real.

**Mitigación:** El resultado del invariante solo afecta si `total_candidates == 0` — en ese caso decide entre `EMPTY` e `INCONSISTENT`. Si hay candidatos (`DELIVERED`), el estado no cambia.

**Veredicto:** No bloquea E2E. Una vez tengamos datos reales, refinamos la fórmula.

---

## §4 — El Merge de Enrichment (line 1246)

### 4.1 Lo que dice el código

```python
profiles[handle].update({
    "_enriched": True,
    "follower_count": e.get("followersCount"),  # ← LEE DE followersCount
    ...
})
```

### 4.2 Lo que pasa en scoring (line 1333)

```python
followers = p.get("follower_count") if "follower_count" in p else p.get("followersCount")
```

### 4.3 Análisis

El merge **escribe** `followersCount` (camelCase) a la key `follower_count`. Es decir:
- `profiles[handle]["follower_count"] = e.get("followersCount")` — donde `e.get("followersCount")` es el valor real de HikerAPI.

Entonces en scoring:
- `"follower_count" in p` → True (sí existe porque el merge la creó)
- `p.get("follower_count")` → devuelve el valor de HikerAPI en `followersCount`
- **El pipeline funciona correctamente si HikerAPI devuelve `followersCount` con el dato real.**

### 4.4 Veredicto

**El pipeline funciona por diseño, no por coincidencia.** El merge crea la key `follower_count` con el valor de `followersCount`. Scoring lee `follower_count` y obtiene el valor correcto. No hay bug.

---

## §5 — Modos de Falla Identificados

### 5.1 Si HikerAPI no devuelve `followersCount`

Si HikerAPI devuelve `follower_count` (snake_case) o no devuelve followers:
1. `e.get("followersCount")` → None/0
2. `profiles[handle]["follower_count"]` → None/0
3. Scoring: `followers = None` → `followers = 0`
4. Todos los perfiles enriquecidos caen como `MISSING_FOLLOWER_FIELD`
5. 0 candidatos

**Síntoma:** Run termina en `EMPTY` o `INCONSISTENT`, todos `reason_code = MISSING_FOLLOWER_FIELD`.

**Verificación:** Post-run query:
```sql
SELECT reason_code, count(*) FROM discovery_run_events
WHERE run_id = '…' AND event = 'profile.dropped'
GROUP BY reason_code;
```

### 5.2 Si DeepSeek falla silenciosamente

1. `candidate_analyzer.py` lanza excepción en `_parse_batch_response`
2. Cae al `except Exception` → `_fallback_scores()`
3. Todos los scores quedan iguales (no hay diferenciación por IA)
4. `ai_rationale` queda NULL para todos

**Síntoma:** Criterio #4 del E2E falla.

**Verificación:** Logs de Railway buscan `ai_batch_analysis_failed_using_fallback`.

---

## §6 — Veredicto: ¿Funciona el Pipeline?

**SÍ, para el happy path.** Después de:
- BUG #1 fix (`1bdacc3`)
- BUG #2 fix (`1bdacc3`)
- Hito 36 completo (`30e5e06`..`c79f375`)
- M3-Agente A/B fixes (`ae0789c`, `65e998c`)
- Logger fixes (`035aafc`)
- Funnel Invariant fix (`4f87a6b`)

**El E2E del Lunes es la fuente de verdad definitiva.**

---

## §7 — Criterios E2E y Qué Verificar

| # | Criterio | Qué revisar si falla |
|---|----------|----------------------|
| 1 | Polling se detiene solo | `POLL_TERMINAL_STATUSES` tiene 10 valores |
| 2 | `total_candidates ≥ 15` | HikerAPI balance, `flush_drop_ledger` |
| 3 | `followers` real (no 0) | ¿HikerAPI devuelve `followersCount`? |
| 4 | **`ai_rationale` not NULL** | DeepSeek logs, `response_format` |

---

## §8 — Pendientes Reales (No Bloquean E2E)

| Prioridad | Item | Costo | Impacto |
|-----------|------|-------|---------|
| 🟡 MEDIA | Dual-names en search steps (~55 refs) | $0 | Debt técnica |
| 🟡 MEDIA | `except Exception` genéricos (17 hot path) | $0 | Podrían tragar bugs |
| 🟡 MEDIA | `brief_parser` response_format (2 sitios) | $0 | JSON malformado |
| 🟢 BAJA | Freshness policy | $0 | Siguiente sprint |
| 🟢 BAJA | Brand exclusion table | $0 | Q1 decisión |

---

## §9 — Consulta SQL Post-Run

```sql
-- 1. Estado del run
SELECT id, status, total_candidates, actual_cost_usd, created_at
FROM discovery_runs ORDER BY created_at DESC LIMIT 1;

-- 2. Distribución de drops
SELECT reason_code, count(*)
FROM discovery_run_events
WHERE run_id = '…' AND event = 'profile.dropped'
GROUP BY reason_code ORDER BY 2 DESC;

-- 3. Followers de candidatos
SELECT handle, followers, ai_rationale
FROM discovery_candidates
WHERE run_id = '…'
ORDER BY followers DESC LIMIT 20;

-- 4. ai_rationale coverage
SELECT count(*) as total,
       count(ai_rationale) as with_rationale,
       count(*) - count(ai_rationale) as without_rationale
FROM discovery_candidates WHERE run_id = '…';
```

---

*Documento creado: 29 de agosto de 2026 por MiniMax M3-Agent (explore subagent)*
*Commit auditado: `4f87a6b` — Funnel Invariant fix + FunnelTracker used*
*E2E pendiente: Lunes 31 de agosto de 2026*
