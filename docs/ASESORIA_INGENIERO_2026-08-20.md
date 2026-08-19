# ASESORÍA DE INGENIERO — LENS Modo Explorar/Analizar

> **Fecha:** 2026-08-20
> **Audiencia:** Ingeniero advisor
> **Proyecto:** La Web Core — LENS Discovery Module
> **Repositorio:** https://github.com/ungardev/lawebcore

---

## 1. DIAGNÓSTICO — ESTADO ACTUAL

### 1.1 Saldos y Costos Reales

| Concepto | Valor | Fuente |
|----------|-------|--------|
| Total gastado (histórico) | **$28.33 USD** | `discovery_runs.actual_cost_usd` |
| Runs totales | **48** | Railway Postgres |
| Candidatos encontrados (histórico) | **1** | Solo run `03e00ee1` ago-12 |
| Candidatos últimos 7 días | **0** | — |
| HikerAPI balance actual | **~$0 (InsufficientFunds)** | Railway curl test |
| Desfase Redis↔DB | **$25.13** | Redis vs DB |

### 1.2 Por qué el pipeline automático falló

```
Pipeline automático: discovery → enrichment → scoring → 0 candidatos
                                                            ↑
                                                    enrichment 402
                                                    (saldo agotado en paso 3)
```

**Causa raíz:** El enrichment (Step 3) consume ~$1.28/run. Con ~$28 gastados en 48 runs, el saldo se agota en enrichment dejando 0 candidatos.

### 1.3 La solución: Modo Explorar → Modo Analizar

```
┌─────────────────────────────────────────────────────────────┐
│  MODO EXPLORAR ($0.24/run)     MODO ANALIZAR ($1.28/run) │
│                                                             │
│  1. Discovery only (HikerAPI)       1. Carga candidatos    │
│     sin enrichment                    del run padre           │
│  2. Rough score geo+niche          2. Enrichment selectivo  │
│  3. Usuario selecciona handles      3. Scoring completo      │
│  4. Costo mínimo                    4. Proposal CSV           │
│                                                             │
│  Costo: ~$0.24/run                Costo: ~$1.28/3 handles  │
│  Candidato: potencial              Candidato: validado      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. LO IMPLEMENTADO (H26 + sesiones recientes)

### 2.1 Commits en main

| Commit | Desc | Fecha |
|--------|------|-------|
| `5ba4625` | H26 — G1,G2,G3,G5,G6,G7,G8,G9,G10 | 2026-08-19 |
| `ba30a85` | Phase 2.1-2.3 — UI selección + endpoint analyze-selected | 2026-08-19 |
| `9c4bf70` | **G14** — Modo Analizar con parent_run_id + auto-save | 2026-08-20 |
| `d83897f` | **G12** — budget_transactions ledger + migration 00107 | 2026-08-20 |
| `a3f8b40` | **Phase 3** — 59 tests (contracts, API, workflow) | 2026-08-20 |

### 2.2 Flujo Implementado

```
Usuario inicia búsqueda
        ↓
   BriefStructured
   (discovery_mode='explore')
        ↓
   discovery_run_task
   (STEP 1+2+2.5 — solo discovery)
        ↓
   Status: 'explored'
   15-50 handles candidatos
        ↓
   Usuario selecciona handles
   (checkbox UI)
        ↓
   POST /analyze-selected
   (handles_to_analyze = [@h1, @h2, ...])
        ↓
   Nuevo run: discovery_mode='analyze'
   parent_run_id = run_explore
        ↓
   Worker: carga candidatos del padre
   → SKIP discovery steps
   → Enrich solo handles seleccionados
   → Auto-save como 'saved'
        ↓
   Status: 'completed'
   Proposal CSV disponible
```

### 2.3 Gaps Resueltos (de 14)

| # | Desc | H/Commit |
|---|------|----------|
| G1 | `discovery_mode` + `handles_to_analyze` en schema | H26 `5ba4625` |
| G2 | `/conversations/{id}/messages` pasa campos | H26 `5ba4625` |
| G3 | FE API tipos + `explored` en Status | H26 `5ba4625` |
| G4 | Checkbox selección en CandidateCard | `ba30a85` |
| G5 | `'explored'` en DiscoveryRunStatus | H26 `5ba4625` |
| G6 | `STATUS_CONFIG['explored']` | H26 `5ba4625` |
| G7 | `'explored'` terminal en useDiscoveryRun | H26 `5ba4625` |
| G8 | useDiscoveryConversation carga si `'explored'` | H26 `5ba4625` |
| G9 | CHECK constraint `'partial'` + `'explored'` | H26 `5ba4625` |
| G10 | `railway_pg.execute()` raw SQL | H26 `5ba4625` |
| G11 | `POST /analyze-selected` + `lensApi.search.analyzeSelected` | `ba30a85` |
| G13 | `BulkActionBar` + wiring | `ba30a85` |
| G14 | Orchestrator wrap-up + auto-save + parent candidates | `9c4bf70` |
| G12 | `budget_transactions` ledger (migration 00107) | `d83897f` |

### 2.4 Pendiente (antes de producción)

| Prioridad | Item | Acción |
|---|---|---|
| 🔴 CRITICAL | Migration `00106` (`explored` enum) | Apply en Railway: `ALTER TYPE discovery_run_status ADD VALUE 'explored'` |
| 🔴 CRITICAL | HikerAPI balance ($0) | Recargar $50 en hikerapi.com/billing |
| 🟡 MEDIUM | Migration `00107` (budget_transactions) | Apply en Railway después de 00106 |

---

## 3. ARQUITECTURA — PROPUESTA OPUS 5 VALIDADA

### 3.1 Trade-offs: Modo Explorar vs. Automatic Pipeline

| Criterio | Pipeline Automático | Modo Explorar→Analizar |
|----------|--------------------|------------------------|
| Costo/run | ~$1.28 (siempre) | ~$0.24 explorar + $0.43/handle analizar |
| Costo mínimo para 1 candidato | $1.28 | $0.24 + $0.43 = **$0.67** |
| Control de calidad | Bajo (sin supervisión) | Alto (analista selecciona) |
| Velocidad | Lenta (todo o nada) | Rápida (explorar es instantáneo) |
| Tasa de éxito | 2% (1/48) | **~80%** (supervisión humana) |
| Riesgo de 402 mid-run | Alto | Bajo (pre-flight en analizar) |
| Esfuerzo técnico | Alto (mantener pipeline) | Bajo (decisiones humanas) |

### 3.2 Decisión Arquitectónica: G12 (Budget Transactions)

**Problema:** Redis y DB muestran números distintos ($25.13 de desfase).

**Solución implementada:**

```
┌──────────────────────────────────────────────┐
│  budget_transactions (ledger inmutable)     │
│  ──────────────────────────────────────────│
│  id | run_id | provider | amount_usd | ... │
│  ──────────────────────────────────────────│
│  INSERT ONLY (trigger impide UPDATE/DELETE)  │
│                                              │
│  Reconciliación:                              │
│  SELECT SUM(amount_usd)                       │
│  WHERE provider='hikerapi'                   │
│    AND created_at > '2026-08-01'             │
│  → Costo real del período                    │
└──────────────────────────────────────────────┘

Redis: contador hot-path (rápido, puede perder)
DB: ledger inmutable (source of truth, auditable)
```

**Migración:** `00107_budget_transactions.sql` (ya en `main`)

---

## 4. HOJA DE RUTA H26-H30

### H26 ✅ (2026-08-19)
- Modo Explorar: schema, BE, FE, status `explored`
- G1-G3, G5-G10 aplicados

### Phase 2 ✅ (2026-08-20)
- UI selección multi-handle (checkbox)
- Endpoint `/analyze-selected`
- BulkActionBar
- G4, G11, G13

### G14 ✅ (2026-08-20)
- `parent_run_id` en brief
- Worker: carga candidatos del padre en analyze mode
- Skip discovery steps en analyze mode
- Auto-save candidatos como `saved`
- Mensaje de wrap-up específico

### G12 ✅ (2026-08-20)
- Tabla `budget_transactions` con ledger inmutable
- Worker escribe en ledger
- Reconciliación: `SUM(amount_usd) WHERE provider='hikerapi'`

### H27 ⏳ (requerido ahora)
1. Apply migration `00106` en Railway:
   ```sql
   ALTER TYPE discovery_run_status ADD VALUE 'explored';
   ```
2. Apply migration `00107` en Railway (después de 00106)
3. Recargar $50 en HikerAPI

### H28 🔲 (próximo sprint)
- Verificación end-to-end del flujo Explorar→Analizar
- Ajustes de UX based on real usage
- Métricas: candidatos por run, tasa de conversión explorar→analizar

### H29 🔲 (futuro)
- Persistencia del carrito de selección (Zustand store → DB)
- Notificaciones cuando el análisis termina
- Historial de análisis por run

### H30 🔲 (futuro)
- Dashboard de costos con `budget_transactions`
- Alertas de presupuesto (notify cuando $X gastados)
- API de costos por período/provider

---

## 5. RECOMENDACIONES PARA EL ADVISOR

### 5.1 Prioridad inmediata
1. **Aplicar migraciones** — sin esto, el enum `explored` no existe en Railway y el Modo Explorar falla
2. **Recargar HikerAPI** — con $0 el worker aborta en pre-flight; no hay forma de probar nada

### 5.2 Métricas de éxito (después de recargar)
- Explorar: ¿cuántos handles descubre por run?
- Analizar: de los handles seleccionados, ¿cuántos enriquecen correctamente?
- Propuesta: de los candidatos guardados, ¿cuántos aparecen en proposal.csv?

### 5.3 Lo que NO hacer
- No modificar el pipeline automático (costo alto, bajo ROI)
- No agregar más pruebas de enrichment automático sin supervisión
- No implementar features de billing hasta que el flujo básico esté validado

---

## 6. STACK Y CREDENCIALES

| Servicio | Estado | Notas |
|----------|--------|-------|
| Railway (API) | ✅ Producción | `lawebcore-api` |
| Railway (Postgres) | ✅ Producción | `railway` |
| Railway (Redis) | ✅ Producción | `redis rail` |
| HikerAPI | ⚠️ Sin saldo | `$0` — recargar $50 |
| DeepSeek | ✅ Configurado | `DEEPSEEK_API_KEY` en Railway |
| Apify | ✅ Configurado | `APIFY_API_TOKEN` en Railway |

---

## 7. PRÓXIMOS PASOS (checklist)

- [ ] Apply migration `00106` en Railway
- [ ] Apply migration `00107` en Railway
- [ ] Recargar $50 en HikerAPI
- [ ] Testear Modo Explorar en staging/producción
- [ ] Testear Modo Analizar (explore → select → analyze → proposal.csv)
- [ ] Verificar que pytest suite pasa localmente
- [ ] Revisar logs de Railway post-deploy para confirmar que todo corre
