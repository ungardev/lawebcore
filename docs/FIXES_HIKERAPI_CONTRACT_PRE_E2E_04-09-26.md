# LENS · FIXES PRE-E2E — Alineación del cliente HikerAPI al OpenAPI spec
## Auditoría exhaustiva del pipeline · 04-sep-2026 · La Web Figital Agency

> **HEAD base:** `370443c` (04-sep-2026)
> **Método:** lectura completa de `worker.py` (2,415 líneas), `hikerapi_client.py` (914), `orchestrator.py`, `lens_score.py`, `query_builder.py`, `profile_generator.py`, `geo_boost.py`, `observability.py`, `brief_parser.py`, `supabase/schema.sql` + **verificación endpoint por endpoint contra el OpenAPI spec oficial** (`https://api.hikerapi.com/openapi.json`, v1.8.1, 154 paths).
> **Pregunta que origina esta auditoría:** ¿el pipeline LENS entregará influencers hoy?

---

## VEREDICTO

**SÍ entregará candidatos en modo AUTO (probabilidad alta)** — la cadena discovery → enrichment → merge → scoring → insert está mecánicamente sana tras los fixes de `a67ad72`/`644c513`. Pero esta auditoría encontró **2 bugs que impedían la entrega en otros caminos** (pre-flight muerto, modo Explorar entregando 0), 1 palanca de calidad muerta (ER real), y 1 contabilidad de funnel mentirosa. Todos arreglados aquí.

---

## HALLAZGOS NUEVOS (N-1 a N-5) — verificados contra OpenAPI spec

### N-1 — `get_balance()` usaba 3 paths INEXISTENTES → pre-flight muerto · P0 · FIXED
- El cliente probaba `/v1/account`, `/v1/user/balance`, `/account`. **Ninguno existe en el spec** (0 ocurrencias). El único endpoint real es **`GET /sys/balance`** — gratis, retorna `{requests, rate, currency, amount}`.
- Consecuencia: `get_balance()` retornaba `None` SIEMPRE → el pre-flight del Hito 23 nunca se ejecutaba → un run con saldo $0 quemaba ~$0.60 de discovery antes de morir con 402 en enrichment.
- El HITO 25 documentaba un contrato `{state: false}` que no existe en el spec — diagnóstico nunca verificado contra la fuente.
- **Fix:** `get_balance()` ahora llama `/sys/balance` y parsea `amount` (dinero USD). Saldo 0 → `0.0` → el pre-flight del worker aborta antes de gastar.
- Irónico: `scripts/test_run5_validation.py` ya usaba `/sys/balance` correctamente — el path real era conocido pero nunca se portó al cliente.

### N-2 — Modo EXPLORAR entregaba 0 candidatos SIEMPRE · P0 · FIXED
- Sin enrichment, los perfiles llegan con `followers=0` y la mayoría **sin bio** (los posts de hashtags/reels traen `UserShort`, que no incluye `biography`) → `geo=0`, `niche=0` → `rough=0` → `match_score=0` → el umbral fijo `min_match_score=5` los eliminaba a TODOS.
- El modo diseñado para "mostrar barato" (~$0.24/run) violaba la regla de oro *"mostrar candidatos > rechazar candidatos"*.
- **Fix:** nuevo helper `_min_match_score_for_mode()` — umbral `0` en Explorar, `5` en Auto/Analizar. En Explorar el analista decide; el pipeline no filtra por score.

### N-3 — ER real = 0 para todos los candidatos · P0 · FIXED
- El spec confirma: `/v2/user/by/username` **NO devuelve posts** (`latestPosts`: 0 ocurrencias en todo el spec). El peso más grande del Lens Score (**38.9%** — `tier_normalized_er`) estaba muerto; `expected_engagement=0`; el filtro anti-bot de ER no opinaba; `avg_likes`/`avg_comments` = NULL.
- **Fix (3 piezas):**
  1. `HikerAPIClient.get_user_medias()` — nuevo, `GET /gql/user/medias` (1 request), extractores `_extract_posts()`/`_post_engagement()` type-agnostic (maneja `data.user.edge_owner_to_timeline_media.edges[].node`, `items[]`, `like_count`/`edge_liked_by.count`/`edge_media_preview_like.count`).
  2. `worker._enrich_one()` — tras el enrichment, fetch de 12 posts por perfil (gated por `HIKERAPI_FETCH_MEDIAS`, default ON, ~+$0.25/run).
  3. Merge de enrichment ahora copia `latestPosts` al perfil → el cálculo existente `(likes_avg + comments_avg) / followers` produce **ER real**.

### N-4 — Contabilidad de funnel con dobles conteos · P1 · FIXED
- Tres fugas hacían que `deduped == delivered + drops` **nunca cuadrara**:
  1. No seleccionados por el prefilter (~163/188 en el run `10a59ecf`): se dropeaban DOS veces (ENRICHMENT_FAILED en el merge + MISSING_FOLLOWER_FIELD en scoring) o ninguna según el modo.
  2. Filtros de score/tienda sin registro en el ledger.
  3. Corte top-80 de `_rerank_diversified` sin registro.
- **Fix:** `enrichment_targets` como único conjunto de referencia — no seleccionados se dropean UNA vez (`SCORE_BELOW_THRESHOLD`/`prefilter`); el loop de scoring salta no-seleccionados; `enrichment_missing` solo aplica a targets no entregados vía rough score (Explorar); filtros score/tienda/rerank registran sus salidas (`score_filter`, `store_filter`, `rerank_cutoff`).
- Consecuencia directa: con 0 candidatos el status será `EMPTY` (honesto) y no `INCONSISTENT` (mentira).

### N-5 — Cuota real ≠ llamadas contabilizadas · P1 · DOCUMENTADO (sin fix en este batch)
- El spec documenta: `/v2/user/by/username` cuesta **2 requests/llamada** (igual que stories/highlights/followers-chunk); `/sys/balance` es gratis. El `BudgetFuse` cuenta LLAMADAS → un run al tope de 120 llamadas puede quemar ~170 requests de cuota real. `HIKERAPI_COST_PER_CALL_USD=0.02` es un promedio empírico correcto ($1.72/86) pero el techo de presupuesto subestima el consumo. Pendiente: contar requests por endpoint según spec.

---

## CONFIRMACIONES SOBRE AUDITORÍAS PREVIAS (con severidad corregida)

| Claim previa | Veredicto verificado |
|---|---|
| B-NEW-2 "elite_data column missing = CRÍTICA, persist broken 100%" | ⚠️ **MEDIA.** La tabla `discovery_profiles` (schema.sql:922-942) no tiene la columna → el INSERT falla, PERO está en try/except (`profile_persist_error`) y el run continúa con el profile en memoria. Costo: re-generar DeepSeek en cada cache miss (Redis TTL 7d). Sin fix aquí (diferido) |
| B-NEW-1 "`}` en brief_parser crash 100%" | ⚠️ **Real pero scope file-upload.** `brief_parser.py:163` tenía `} }` (espacio → `}` suelto → `ValueError: Single '}'` en `.format()` de la línea 354). Solo afectaba el parseo de documentos subidos (PDF/TXT), no el chat. **FIXED** |
| B-NEW-3 "benchmarks sin coerción" | ⚠️ **Riesgo intermitente real.** `_validate_niche_benchmarks` validaba `isinstance(dict)` pero no tipos: `"min_followers": "5000"` (str del LLM) → `TypeError` en prefilter → run FAILED. **FIXED** con coerción `int()`/`float()` + fallback preservado |
| B-1 `former_usernames` es string | ✅ Spec lo confirma: `type: string`. El fix type-agnostic de `644c513` era correcto |
| Normalizador snake_case | ✅ Spec: `follower_count`/`is_business`/`is_verified` (camelCase: 0 ocurrencias en el spec) |
| Contratos de discovery (hashtags/topsearch/reels/fbsearch/suggested/places/followers) | ✅ Todos los paths y params del cliente existen en el spec con los nombres correctos |

## HALLAZGOS DE CALIDAD (documentados, sin fix en este batch)

1. **`min_followers=5000` default** (query_builder tier "micro" → `plan.min_followers`): los nanos 1K-5K quedan fuera SIEMPRE. Respuesta definitiva al bloqueante #2 de Fable 5.1: **SÍ es filtro duro**, vía query_builder, no vía `TIER_MIN_FOLLOWERS=500` del worker (esa constante no se usa para filtrar).
2. **Filtro tienda sobre-agresivo**: `tienda_keywords_hard` incluye `"whatsapp"`, `"envíos"`, `"link en bio"` + `exclude_stores=True` default → creadores legítimos con "📦 Envíos | WhatsApp: ..." en bio serán excluidos como tiendas.
3. **Prefilter a ciegas**: el top-25 se elige con rough scores calculados sobre bios vacías (UserShort sin biography) → selección casi arbitraria de a quién enriquecer. Mejora futura: pre-bio via `/gql/user/web_profile_info` o usar señales de posts (likes del post que lo descubrió).
4. **Hashtags muertos**: `"cocina Latina"` (espacio) → FIXED a `"cocinalatina"`; `"hogartzla"` (typo) → FIXED a `"hogarvzla"`.
5. **Orquestador dead-code**: `orchestrator._execute_discovery` (línea 499) llama `query_builder.build()` SIN `await` (build es async) — crashearía si se llamara, pero nadie lo llama (el SEARCHING step es estático). Limpieza futura.
6. **`country` no viene del user object**: el spec no tiene `country`/`country_code` en el User schema → el filtrado geo por país depende de `/v1/user/about` (flag OFF) + señales bio/TLD/geo_score. Encender `HIKERAPI_INCLUDE_ABOUT=true` es seguro ahora (B1 fixed) y aporta `about.country` real.

---

## ARCHIVOS MODIFICADOS

| Archivo | Cambio |
|---|---|
| `packages/discovery/discovery/tools/hikerapi_client.py` | N-1 `get_balance()` → `/sys/balance`; N-3 `get_user_medias()` + `_extract_posts()` + `_post_engagement()` |
| `apps/api/app/workers/worker.py` | N-2 `_min_match_score_for_mode()`; N-3 flag `ENRICHMENT_FETCH_MEDIAS` + fetch medias en `_enrich_one` + `latestPosts` en merge; N-4 `enrichment_targets` + drops de prefilter/score/tienda/rerank + `enrichment_missing` solo targets |
| `packages/discovery/discovery/profile_generator.py` | B-NEW-3 coerción `int()`/`float()` en `_validate_niche_benchmarks` |
| `packages/discovery/discovery/brief_parser.py` | B-NEW-1 `} }` → `}}` (línea 163) |
| `packages/discovery/discovery/query_builder.py` | hashtags `"cocinalatina"`, `"hogarvzla"` |
| `apps/api/tests/test_hikerapi_balance.py` | NUEVO — 6 tests (path, amount, saldo 0, non-200, sin amount, never-raises) |
| `apps/api/tests/test_user_medias_extraction.py` | NUEVO — 12 tests (extractores + normalización + cap + vacío) |
| `apps/api/tests/test_explore_mode_threshold.py` | NUEVO — 2 tests |
| `apps/api/tests/test_niche_benchmarks_coercion.py` | NUEVO — 6 tests |
| `apps/api/tests/test_enrichment_field_names.py` | `latestPosts` agregado a `known_extra_keys` con justificación |

## VERIFICACIÓN

- **Tests:** 194 passed, 7 failed (pre-existentes idénticos al baseline vía `git stash`), 3 skipped — **cero regresiones**.
- **Ruff:** 30 errores, todos pre-existentes (baseline: 31 — se removió 1).
- **Fallos pre-existentes (deuda documentada, no de este batch):** `test_budget_fuse` ×3 (flakiness de event loop), `test_dual_names_guard` ×2 (deuda dual-names), `test_funnel_invariant` ×2 (identidad del ledger).

## PRÓXIMO PASO — E2E de validación

1. **E2E EXPLORAR primero** (~$0.24): valida entrega completa sin enrichment — debe entregar los perfiles prefiltrados con match_score = rough×100.
2. **E2E AUTO después** (~$1.45 con medias): valida ER real, bot filter activo, funnel cuadrado, status DELIVERED/EMPTY honesto.
3. Logs a verificar: `preflight_balance_ok` (NUEVO — antes nunca aparecía), `hikerapi_user_medias_done` (NUEVO), `enrichment_merged` con `posts_fetched>0`, `funnel_invariant_check funnel_ok=True`, `scoring_diagnostic` con `no_engagement_data=0`.

---

*Documento generado: 04-sep-2026 · La Web Figital Agency*
*Auditor: GLM 5.3 Flash (opencode) · Verificación contra OpenAPI spec v1.8.1 (154 paths)*
