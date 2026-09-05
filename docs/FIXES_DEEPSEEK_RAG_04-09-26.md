# LENS · FIXES LLM + RAG — DeepSeek-V4-Flash coherente y eficiente
## Auditoría de integración DeepSeek + RAG · 04-sep-2026 · La Web Figital Agency

> **HEAD base:** `312f68d` (04-sep-2026)
> **Pregunta que origina esta auditoría:** ¿DeepSeek-V4-Flash está conectado correctamente y funcionando de manera coherente?
> **Respuesta corta:** Conectado SÍ; coherente PARCIAL — 2 críticos (brief truncado en silencio, análisis IA apagado por default) + RAG mono-turno por un bug. Todos corregidos aquí.

---

## HALLAZGOS Y FIXES

### Críticos

**D-1 — `brief_parser` con `max_tokens=300`: JSON truncado → brief degradado en silencio · FIXED**
El parser pide un JSON de ~25 campos (producto, industria, nichos, hashtags, audiencia, países, ciudades, tono, KPIs, fechas, competidores...). Una salida fiel necesita ~600-900 tokens: con 300 el JSON llegaba truncado → `ValueError` → el orquestador caía al brief heurístico **sin avisar**, perdiendo hashtags/ciudades/tono del wizard. Con N-1..N-4 desbloqueada la prueba UI, este era el siguiente cuello de botella de calidad.
- Fix: `max_tokens` 300 → **1200** (chat) y 800 → **1500** (document parser) + truncation-retry del cliente (D-5) + guard test.

**D-2 — `ENABLE_AI_ANALYZER=False` default: STEP 5 de IA era no-op silencioso · DOCUMENTADO + VISIBLE**
El análisis DeepSeek de candidatos (content_quality, audience_quality, brand_fit, summary) estaba apagado por default — los runs salían con esas columnas vacías sin que nadie lo supiera (`ai_analyzer_disabled_skipping` a nivel info).
- Fix: warning explícito por run (`ai_analyzer_globally_disabled` con hint) + documentado en `.env.example` con costo (~$0.10-0.30/run). **Decisión de encenderlo = Railway, sin deploy.**

### Coherencia / eficiencia (medios)

| ID | Hallazgo | Fix |
|---|---|---|
| **D-3** | Cliente ChatOpenAI reconstruido EN CADA llamada (sin pool de conexiones) + `asyncio.to_thread(sync invoke)` bloqueando un hilo del pool por llamada | Cliente cacheado (lazy singleton) + `ainvoke` nativo |
| **D-4** | Retries sobre 4xx determinísticos (401 auth, 400) — 3 intentos con sleeps sobre errores que fallarán siempre | `_is_retryable()`: solo 429/5xx/timeout/conn se reintentan; 4xx = fail-fast |
| **D-5** | `complete_json` reintentaba el mismo string truncado 3× y su "arreglo" era appendear `'"}'` (casi nunca JSON válido) | Detección `finish_reason="length"` → 1 reintento con `max_tokens×2` + parser simplificado |
| **D-6** | Prompt del analyzer pedía "JSON array" pero `response_format=json_object` exige objeto raíz — el modelo podía responder `{"result": [...]}` y el batch completo caía a fallback scores | Prompt pide explícitamente `{"scores": [...]}` (el parser ya lo soportaba) |
| **D-7** | `app/ai/llm.py::get_llm()` — dead code (0 usos) que construía ChatOpenAI **SIN thinking disabled**: mina de quema de tokens | Eliminado |
| **R-1** | `rag_engine.generate_with_context` construía `messages[]` con historial y **lo tiraba a la basura** — llamaba `complete(prompt, system)` sin historial → RAG mono-turno, follow-ups incoherentes ("¿y el segundo mejor?" perdía todo contexto). `ai_service.py` sí lo incluía — dos caminos inconsistentes | Nuevo parámetro `history` en `complete()` (roles validados, system no inyectable) + `rag_engine` lo usa |
| **R-2** | `embed_texts` devolvía `[0.0]*384` en fallo → vectores cero insertados en `document_chunks` (filas muertas contadas como embebidas) | Fallback `None` + `indexer` salta chunks sin embedding (`indexing_partial` log) |

### ✅ Verificado sano (sin cambios)

- Modelo `deepseek-v4-flash` en config; thinking OFF + cache ON vía `extra_body` (Hito 36) — **ahora con test que lo protege**.
- Costo por llamada con pricing V4-Flash ($0.44/1M in, $1.32/1M out) — con test de exactitud.
- Batching del analyzer (10/llamada, ≤5 concurrentes) + fallback scores por batch + cost callback al run tracker.
- Infra RAG: pgvector 384d, ivfflat lists=100, chunking 800/100, upsert `(document_id, chunk_index)`, umbrales 0.65/0.7.

---

## ARCHIVOS MODIFICADOS

| Archivo | Cambio |
|---|---|
| `packages/shared-ai/shared_ai/deepseek_client.py` | Cliente cacheado + `ainvoke` + `_is_retryable` + truncation-retry + `history` param + `finish_reason` en LLMResponse |
| `packages/discovery/discovery/brief_parser.py` | max_tokens 300→1200 / 800→1500 con justificación |
| `packages/discovery/discovery/candidate_analyzer.py` | Prompt `{"scores": [...]}` (SYSTEM + batch prompt) |
| `apps/api/app/ai/llm.py` | **Eliminado** (dead code con thinking ON) |
| `apps/api/app/ai/rag_engine.py` | Historial real al LLM vía `history=` (muerto el `messages[]` decorativo) |
| `packages/shared-ai/shared_ai/embeddings.py` | Fallback `None` (adiós vectores cero) |
| `apps/api/app/ai/indexer.py` | Skip de chunks sin embedding + log `indexing_partial` |
| `apps/api/app/workers/worker.py` | Warning `ai_analyzer_globally_disabled` cuando el gate esté OFF |
| `.env.example` | `ENABLE_AI_ANALYZER` documentado con costo + hint del smoke test |
| `apps/api/scripts/test_deepseek.py` | **Nuevo** — smoke contra producción: JSON mode, métricas/finish_reason, memoria multi-turno |
| `apps/api/tests/test_deepseek_client.py` | **Nuevo** — 10 tests: fail-fast 401, retry 429, truncation retry ×2 tokens, history en orden + anti-inyección, cache del cliente, costo, scores wrapper, guard max_tokens del parser, guard prompt del analyzer |

## VERIFICACIÓN

- **207 passed** (10 nuevos), 7 failed = idénticos al baseline pre-cambios, 3 skipped — **cero regresiones**.
- **Ruff:** limpio en todos los archivos del batch.

## CÓMO VERIFICAR LA CONEXIÓN REAL (producción)

```bash
cd apps/api
DEEPSEEK_API_KEY=sk-... ../../.venv/bin/python -m scripts.test_deepseek
```
Verifica: auth, JSON mode, tokens/costo/finish_reason, y memoria multi-turno (~$0.001 por corrida).

## DECISIONES ABIERTAS

1. **`ENABLE_AI_ANALYZER=true` en Railway?** — ~$0.10-0.30/run, produce las 3 columnas IA + summary. Recomendado: encender y validar en el próximo E2E.
2. (P2, diferido) Consolidar los 2 motores RAG paralelos (`rag_engine.py` y `ai_service.py`) en una sola implementación con prompts compartidos.
3. (P3) Pricing off-peak de DeepSeek en el cálculo de costo (hoy peak fijo, conservador).

---

*Documento generado: 04-sep-2026 · La Web Figital Agency · GLM 5.3 Flash (opencode)*
