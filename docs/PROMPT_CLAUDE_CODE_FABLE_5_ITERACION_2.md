# PROMPT: CLAUDE CODE FABLE 5 — LENS DISCOVERY ITERATION 2

## Contexto General

Claude Code Fable 5 (Full Stack Senior Engineer), este es tu segundo engagement en el proyecto LENS Discovery. El primero (Iteración 1, commit `bd973c7`) resultó en 16 hitos aplicados + 8 fixes críticos en commit `2446e75`. Este segundo engagement tiene **dos objetivos**:
1. **Aplicar los fixes críticos de frontend** que impiden que el usuario vea candidatos aunque el backend funcione
2. **Preparar y ejecutar la corrida de validación** del pipeline

---

## FUENTE DE VERDAD

Tu fuente de verdad es:
- **Repo:** `https://github.com/ungardev/lawebcore` (rama `main`, commit `2446e75`)
- **Docs actualizados:** `docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md` — LÉELO PRIMERO. Es el documento maestro que acabamos de reescribir con todo el estado actual.
- **Docs de soporte:** listados en la sección "Documentos de Referencia" del PLAN_MAIN

**Regla: si un documento contradice el código, el código prevalece. Lee siempre el código fuente directamente antes de proponer cualquier cambio.**

---

## ESTADO ACTUAL DEL PROYECTO

### Backend: OPERATIVO ✅

El commit `2446e75` ("fix(lens): Hitos 35.1-35.8 — regressions and data integrity") fue aplicado y pusheado. El deploy en Railway fue exitoso (logs muestran "Application startup complete", worker iniciado).

**8 fixes aplicados:**
| Fix | Descripción | Impacto |
|-----|-------------|---------|
| FIX #1+2 | Merge enrichment ahora snake_case only + `_enriched`; scoring distingue MISSING_FOLLOWER_FIELD | **CRÍTICO —恢复 pipeline** |
| FIX #3 | `flush_drop_ledger()` persiste ledger a `discovery_run_events` | Auditoría funcional |
| FIX #4+5 | UPSERT social_accounts + snapshot con `social_account_id` | Integridad de datos |
| FIX #6 | `_derive_tier` → 9 sub-tiers | Clasificación correcta |
| FIX #8 | `_parse_batch_response` usa `_json.loads()` directo | Contrato limpio |

**El pipeline técnico funciona.** Sin embargo, hacer una corrida de validación ahora resultaría en **HTTP 500** porque el frontend no puede procesar la respuesta del backend.

### Frontend: 2 Issues Críticos ❌

Nuestro análisis exhaustivo del frontend (`apps/web/src`) reveló:

#### Issue C-1 🔴 CRÍTICO — RunStatus Enum Mismatch

El worker escribe statuses usando `RunStatus` de `observability.py`:
```python
# Lo que el WORKER escribe (lineas 1787, 1967, 320):
"delivered", "degraded", "aborted_budget", "empty", "inconsistent"
```

Pero el endpoint `GET /runs/{id}` usa `response_model=DiscoveryRunResponse` que tiene Pydantic enum:
```python
# Lo que Pydantic CONOCE (schemas.py:11-19):
"pending", "running", "completed", "failed", "cancelled", "partial", "explored"
```

**5 valores nuevos no existen en el enum Pydantic.** El resultado: **HTTP 500 en toda corrida exitosa.** El polling del frontend nunca completa.

**Fix requerido:** Extender `DiscoveryRunStatus` enum en `packages/discovery/discovery/schemas.py:11-19` con los 5 valores faltantes (`queued`, `delivered`, `degraded`, `empty`, `inconsistent`, `aborted_budget`).

#### Issue C-2 🟡 MEDIA — Influencer.primary_tier Type Mismatch

`_derive_tier` (FIX #6) ahora devuelve 9 sub-tiers (`NANO_BAJO` → `MACRO_ALTO`). Cuando el usuario guarda un candidato, `influencers.primary_tier` se escribe con estos valores.

Pero el tipo TypeScript:
```typescript
// apps/web/src/types/index.ts:43
primary_tier: 'NANO' | 'MICRO' | 'MID' | 'MACRO' | 'MEGA' | 'MIX';
```

**No incluye los 9 sub-tiers.** La lista de influencers guardados y la vista de campañas mostrará "—" para `primary_tier`.

**Fix requerido:** Ampliar el union type en `apps/web/src/types/index.ts:43` para incluir los 9 sub-tiers.

---

## DOCUMENTOS A LEER (en orden de prioridad)

1. **`docs/PLAN_MAIN_ALINEACION_LENS_2026-08-25.md`** — El documento maestro. Léelo completo primero. Tiene todo el estado del proyecto, los issues de frontend, y el plan de acción.

2. **`docs/VERIFICACION_CODIGO_LENS_HITOS_30-35_25-08-26.md`** — Auditoría de Fable 5 sobre commit `18ae963`. Documenta la regresión #0 original.

3. **`packages/discovery/discovery/schemas.py`** — Busca `DiscoveryRunStatus` enum (líneas ~11-19). Este es el archivo a modificar para Issue C-1.

4. **`apps/web/src/types/index.ts`** — Busca `Influencer.primary_tier` (línea ~43). Este es el archivo a modificar para Issue C-2.

5. **`packages/discovery/discovery/schemas.py`** — Busca la clase `DiscoveryRunResponse` y cómo se usa `status`. Para confirmar cómo se relaciona con el enum.

6. **`apps/api/app/workers/worker.py`** — Líneas ~1780-1795 y ~190-330. Para confirmar exactamente qué statuses escribe el worker y en qué momentos.

7. **`apps/api/app/api/v1/discovery.py`** — Líneas ~760-772 (`GET /runs/{run_id}`). Para confirmar el `response_model` y la estructura de respuesta.

---

## TAREAS PARA ESTA ITERACIÓN

### TAREA 1: Fix Issue C-1 — RunStatus Enum Mismatch

**Archivo a modificar:** `packages/discovery/discovery/schemas.py`

**Pasos:**
1. Lee el archivo y encuentra `DiscoveryRunStatus` enum
2. Añade los 5 valores faltantes al enum: `QUEUED`, `DELIVERED`, `DEGRADED`, `EMPTY`, `INCONSISTENT`, `ABORTED_BUDGET` (o verifica que ya estén)
3. Confirma si el enum actual es un `class DiscoveryRunStatus(str, Enum)` o un literal union
4. Verifica que los valores en el enum coincidan exactamente con los que el worker escribe:
   - `"queued"` (worker.py:320)
   - `"delivered"` (worker.py:1787)
   - `"degraded"` (worker.py:1788, 1967)
   - `"aborted_budget"` (worker.py:320)
   - `"empty"` (worker.py)
   - `"inconsistent"` (worker.py)
5. Si falta alguno, agrégalos
6. Verifica que el endpoint `GET /runs/{id}` use `response_model=DiscoveryRunResponse` y que el enum actualizado sea el correcto
7. Haz commit con mensaje: `fix(lens): extend DiscoveryRunStatus enum with delivered/degraded/etc`

**Criterio de éxito:** Después del fix, `GET /runs/{run_id}` retorna status `delivered` sin HTTP 500.

### TAREA 2: Fix Issue C-2 — Influencer.primary_tier Type Mismatch

**Archivo a modificar:** `apps/web/src/types/index.ts`

**Pasos:**
1. Lee el archivo y encuentra `Influencer` type o interface
2. Encuentra la línea con `primary_tier`
3. Cambia el union type de:
   ```typescript
   primary_tier: 'NANO' | 'MICRO' | 'MID' | 'MACRO' | 'MEGA' | 'MIX';
   ```
   A:
   ```typescript
   primary_tier: 'NANO' | 'NANO_BAJO' | 'NANO_ALTO' | 'MICRO' | 'MICRO_BAJO' | 'MICRO_MEDIO' | 'MICRO_ALTO' | 'MID' | 'MID_BAJO' | 'MID_ALTO' | 'MACRO' | 'MACRO_BAJO' | 'MACRO_ALTO' | 'MEGA' | 'MIX';
   ```
4. Verifica si hay otros archivos que referencien `INFLUENCER_TIERS` o `TIERS` con valores 4-tier y actualiza si es necesario:
   - `apps/web/src/lib/utils.ts` (línea ~51: `INFLUENCER_TIERS`)
   - `apps/web/src/features/campaigns/components/NewCampaignModal.tsx` (línea ~30: `TIERS`)
5. Haz commit con mensaje: `fix(lens): widen Influencer.primary_tier to 9 subtiers`

**Criterio de éxito:** TypeScript compila sin errores. Los 9 sub-tiers son tipos válidos.

### TAREA 3: Verificar Alineación Backend-Frontend Post-Fixes

**Después de aplicar Tarea 1 y Tarea 2:**

1. Verifica que no haya otros lugares donde `RunStatus` del worker y `DiscoveryRunStatus` del API se desconecten:
   - `apps/api/app/api/v1/discovery.py` — busca todos los endpoints que retornan `discovery_runs`
   - `apps/api/app/workers/worker.py` — busca todos los lugares donde se escribe `status`

2. Verifica que el tipo `DiscoveryCandidate.tier` en el frontend (`apps/web/src/features/lens/types/discovery.ts`) sea consistente:
   - Los candidatos del worker usan `classify_tier()` (4-tier) que va a `discovery_candidates.tier`
   - Los influencers guardados usan `_derive_tier()` (9 sub-tiers) que va a `influencers.primary_tier`
   - **No cambiar `DiscoveryCandidate.tier`** — eso funciona bien con 4-tier

3. Verifica `getTierColor()` y `getTierLabel()` en `apps/web/src/lib/format.ts`:
   - No es bloqueante, pero documenta qué colores assignar a los 9 sub-tiers
   - Opcional: si decides mantener 4-tier para candidatos, no hay cambio necesario aquí

### TAREA 4: Commit y Push

1. Haz `git add -A` de todos los cambios
2. Commit con mensaje descriptivo
3. Push al remote
4. Confirma que Railway hizo deploy (verifica Railway Deploy Logs)

### TAREA 5: Análisis de后续 Fixes Opcionales

Después de los fixes críticos, analiza y documenta en el PLAN_MAIN cuál sería el approach para:

1. **FP-1: Freshness Policy 7d** — Ya tenemos la base (unique snapshot), falta la lógica en el worker para skip enrichment si existe snapshot <7d. ¿Cuánto esfuerzo requiere?

2. **FP-2: Brand Exclusion Table** — ¿Cuánto esfuerzo requiere la migración y el módulo de exclusions?

3. **SearchProgress PHASES desfasadas** — El frontend no tiene `step5_ai_analysis` y el worker ya no escribe `step2_keyword_search`. ¿Es esto un problema real o solo cosmético?

4. **Fix C-4: getTierColor() para 9 sub-tiers** — ¿Cuánto esfuerzo requiere?

---

## COSTOS Y SALDO

| Concepto | Monto |
|----------|-------|
| Saldo HikerAPI actual | ~$38 USD |
| Corrida de validación (pendiente) | ~$1.14 USD |
| Saldo post-validación | ~$36.86 USD (~32 corridas) |

**Los fixes C-1 y C-2 son $0 de HikerAPI** — solo código.

---

## VERIFICACIONES REQUERIDAS ANTES DE CONFIRMAR "DONE"

Para cada tarea, confirma:
- [ ] El código compila (no hay errores de sintaxis ni tipos)
- [ ] El cambio está alineado con el resto del codebase (mismas convenciones)
- [ ] El commit message sigue el formato: `fix(lens): ...` o `feat(lens): ...`
- [ ] El deploy en Railway fue exitoso
- [ ] Los logs de Railway no muestran errores

---

## FORMATO DE RESPUESTA

Cuando termines, proporciona:

1. **Resumen de lo hecho** (2-3 oraciones)
2. **Commits realizados** (hash y mensaje)
3. **Verificación de Railway deploy** (confirmado o pendientes)
4. **Issues encontrados durante la ejecución** (si hay)
5. **Recomendación** para la corrida de validación (¿procedemos ahora, o hay más cambios necesarios antes?)

---

## FLAGS IMPORTANTES

- **NO uses `cd` en comandos** — usa el parámetro `workdir` en el tool de Bash
- **NO hagas commits vacíos o sin mensaje claro**
- **NO modifiques archivos de migración existentes** — solo crea nuevos si necesitas DB changes
- **SÍ verifica Railway deploy logs** después de cada push
- **SÍ usa el写得 `grep` o `read` tool antes de modificar cualquier archivo**

---

*Prompt generado: 27 de agosto de 2026*
*Basado en: PLAN_MAIN_ALINEACION_LENS_2026-08-25.md actualizado*
*Versión del repo: commit `2446e75`*
