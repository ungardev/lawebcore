# LENS · FIXES FRONTEND — Paridad de estados y UX del wizard
## B-FE-7/B-FE-15 desbloqueados · 04-sep-2026 · La Web Figital Agency

> **HEAD base:** `567b050` (04-sep-2026 — batch N-1..N-4 backend)
> **Origen:** dictamen "¿una prueba vía UI con el BriefWizard entregará buenos resultados?" — respuesta: backend SÍ entrega, pero la UI **jamás mostraba los candidatos**.

---

## VEREDICTO PREVIO AL FIX (trazado completo del flujo UI)

```
BriefWizard "Buscar candidatos"
  → handleWizardSubmit serializaba el brief a JSON y lo mandaba como MENSAJE DE CHAT
  → orchestrator parseaba (DeepSeek) y pedía confirmación — 2do turno manual obligatorio
  → API creaba el run (discovery.py:309-336) → discovery_run_id → useRunPolling
  → useRunPolling paraba el polling SOLO en completed/partial/failed/cancelled
  → el worker emite delivered/degraded/empty/... → polling infinito, candidatos nunca fetcheados
  → loadConversation tenía el mismo filtro → ni recargando la página se veían resultados
```

**Único estado compartido FE↔BE: `failed`.** El tipo `DiscoveryRunStatus` del frontend ya incluía los estados reales — los hooks nunca se actualizaron (regresión del Hito 30, catalogada como B-FE-7 CRÍTICA).

---

## FIXES APLICADOS

### 1. `useRunPolling.ts` — source of truth de estados (P0)
- `TERMINAL_RUN_STATUSES = ['delivered','degraded','empty','inconsistent','aborted_budget','failed']` — polling se detiene en los 6 estados terminales reales.
- `CANDIDATE_RUN_STATUSES = ['delivered','degraded']` — fetch de candidatos (top 20).
- Expone `runStatus` y `runError` para la capa de conversación.
- Constantes exportadas = fuente única (nada de literales sueltos).

### 2. `useDiscoveryConversation.ts` (P0)
- `loadConversation` fetchea candidatos vía `CANDIDATE_RUN_STATUSES` (antes: literales legacy que jamás llegaban).
- **Auto-reload:** cuando el polling termina SIN candidatos (empty/failed/aborted_budget), recarga el chat para mostrar el mensaje honesto del worker ("⚠️ Esta vez no encontré candidatos... Motivo principal: X perfiles son de otro país...") en vez de un spinner congelado.

### 3. Wizard de un click (P1-UX)
- Nueva `startWizardSearch(brief)` en el hook: crea conversación con el brief JSON, **envía la confirmación automáticamente** ("Confirmo el brief. Buscar ahora." — "confirmo" ∈ `_AFFIRMATIVE_KEYWORDS` del orquestador), pone el run en polling y recarga mensajes.
- `LensChatPage.handleWizardSubmit` la usa — el botón "Buscar candidatos" ahora cumple lo que dice: un click → run encolado → progreso → candidatos en el chat.

### 4. Honestidad de plataformas (P1-UX)
- TikTok/YouTube en el wizard: deshabilitados con badge **"Próximamente"** — el pipeline es Instagram-only (HikerAPI); antes se seleccionaban y el run los ignoraba silenciosamente mientras el mensaje decía "Voy a buscar en Instagram y TikTok".
- `handleSubmit` filtra a plataformas disponibles (fallback `['instagram']`); `togglePlatform` con guard.

### 5. Test de contrato FE↔BE (`test_status_enum_parity.py`, +3 tests)
- `test_frontend_terminal_statuses_match_backend`: el set de parada del hook ≡ estados terminales de `RunStatus` (lee el TS con regex, compara contra el enum Python). Cualquier drift futuro rompe CI.
- `test_frontend_candidate_fetch_statuses_are_valid`: los estados de fetch existen en el backend y contienen `delivered`.
- `test_conversation_hook_reuses_polling_constants`: `useDiscoveryConversation` importa las constantes (prohibidos literales legacy `'completed'`/`'partial'`/`'explored'`/`'cancelled'`).

---

## VERIFICACIÓN

| Check | Resultado |
|---|---|
| `pytest apps/api/tests` | **197 passed**, 7 failed = idénticos al baseline pre-cambios (deuda documentada), 3 skipped |
| `tsc --noEmit` (apps/web) | ✅ limpio |
| `eslint` (4 archivos modificados) | ✅ 0 errores |
| `ruff` (test modificado) | ✅ passed |

## LO QUE SIGUE — E2E vía UI

Con backend (N-1..N-4) + frontend (este batch) alineados, la prueba UI mascotas/VE debe:
1. Wizard → un click → progreso en vivo (step1...step5) en el chat.
2. `preflight_balance_ok` en logs (N-1).
3. `hikerapi_user_medias_done` + `posts_fetched>0` (N-3, ER real).
4. `funnel_invariant_check funnel_ok=True` (N-4).
5. Status final `delivered` (o `empty` con causa honesta) → **candidatos visibles en el chat** con ER real.

Pendientes de calidad conocidos (no bloquean): `min_followers=5000` default (nanos fuera), filtro tienda agresivo ("whatsapp"/"envíos"), prefilter a ciegas con bios vacías.

---

*Documento generado: 04-sep-2026 · La Web Figital Agency · GLM 5.3 Flash (opencode)*
