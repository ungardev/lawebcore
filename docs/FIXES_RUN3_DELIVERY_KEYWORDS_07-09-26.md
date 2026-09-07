# LENS · FIXES RUN 3 — Entrega final + keywords inteligentes
## 07-09-2026 · La Web Figital Agency

> **Run analizado:** `75855ad1` (07-sep 15:52 UTC, $1.56 + $0.001 DeepSeek) — llegó al ÚLTIMO paso: 3 candidatos calificados con brand_fit del análisis IA, y murió en el INSERT. Este batch elimina ese bloqueador y mejora la inteligencia de discovery.

---

## LO QUE ESTE RUN DEMOSTRÓ (antes del fallo final)

Worker vivo ✅ · wizard un-click ✅ · pre-flight saldo ✅ · 167 handles ✅ · 25 enriquecidos con medias ✅ · **scoring sin crash (guard anterior funcionó)** ✅ · **STEP 5 IA por primera vez** (brand_fit=78) ✅ · drop ledger + costo exactos ✅ · mensaje honesto de 0 entregados ✅ (aunque contradictorio — ver F4)

## FIXES

### F1 — 🔴 BLOQUEADOR: `discovery_query` no existe en producción
La migración numerada 111 que crea la columna **jamás se aplicó manualmente** (arquitectura conocida: migraciones numeradas = manual). Todo INSERT de candidatos fallaba (batch + los 3 de respaldo) → 0 entregados → INCONSISTENT.
**Fix:** columnas `discovery_query TEXT` y `brand_fit INTEGER` garantizadas por la **migración auto-aplicada al startup** (`migrate_discovery_conversations_schema` extendida — patrón idempotente existente). Deploy = aplicada.

### F2 — 🔴 ER real no aterriza: forma de `/gql/user/medias` no reconocida
El run mostró `gql/user/medias` × 25 OK pero `posts_analyzed: 0` en todos → el extractor no matcheaba la forma real (probablemente la moderna `xdt_api__v1__feed__user_timeline_graphql_connection`).
**Fix:** extractor v2 soporta la forma xdt (en `data` y bajo `user`) + **log de diagnóstico** (`hikerapi_user_medias_unknown_shape` con keys reales) + script `scripts/test_user_medias.py` para verificar contra la API real en WSL (~$0.06) antes de quemar otro run.

### F3 — 🔴 NULL≠0 en candidatos persistidos
- `engagement_rate: 0.0` persistido sin posts → ahora **NULL** cuando no hay datos
- `following: 0` / `posts_count: 0` — los zeros camelCase del discovery **tapaban** los valores reales del merge → ahora se prefiere el valor enriquecido
- `expected_engagement: 0` → NULL sin datos
- `rationale`: "ER 0.0%" (parece cuenta muerta) → "ER sin datos (posts no analizados)"

### F4 — 🟡 Mensajes contradictorios en el chat
Run 75855ad1 mostró "✅ 3 creadores calificados" Y LUEGO "ninguno califica". **Fix:** si hay calificados pero el insert falla → "Encontré N candidatos que calificaron, pero falló el guardado..." (verdad, no contradicción).

### F5 — 🧠 Keywords inteligentes (fin del enclosure vzla/VE)
**Diagnóstico con datos del run:** las keywords buy-intent ("croquetas para perros", "donde comprar dog chow") trajeron tiendas/farmacias/la marca — no creadores. Ejecutadas como búsquedas de cuentas = desalineación de paradigma.

1. **Prompt v2** (`profile_generator`): keywords = **frases de IDENTIDAD DE CREADOR** ("dog mom caracas", "adiestrador canino", "groomer") — PROHIBIDO product-intent y país/ciudades dentro de la keyword (el sistema agrega geo aparte). Las frases de compra viven solo en `buy_intent_keywords` (intel, no búsqueda).
2. **`additional_context` del cliente entra al prompt** ("Solo creadores, no tiendas..." guía TODA la generación).
3. **Geo condicional en worker**: keyword que ya trae "venezuela"/"vzla" no genera variante duplicada → menos llamadas quemadas, menos enclosure.
4. **Exclusión brand-own**: tokens del producto/marca (`_brand_tokens`: palabras ≥5 + bigrams consecutivos ≥6 — "purina", "dogchow" — sin el falso positivo "chow" de la raza) → `@dogchowve` ya no se entrega como creador (EXCLUDED_BRAND_OWN).

## VERIFICACIÓN

- **242 passed** (+14), 7 failed = baseline intacto, ruff sin errores nuevos
- Tras deploy, la migración F1 se auto-aplica (log: `[migration] Ensured column discovery_query on discovery_candidates`)

## RECOMENDACIÓN OPERATIVA

1. Deploy Railway → verificar `[migration] Ensured column discovery_query` en logs
2. **Opcional (30s):** `HIKERAPI_API_KEY=... python -m scripts.test_user_medias ecoanimalistadevenezuela` en WSL — si el extractor reconoce la forma, el ER real aterriza en el Run 3; si no, el log de diagnóstico nos da las keys exactas para ajustar en minutos
3. **Run 3 vía UI** — mismo brief. Expectativa: candidatos INSERTADOS y visibles en el chat con ER real (o el diagnóstico preciso si la forma de medias requiere otro ajuste menor)

## TUNING POST-ENTREGA (con datos del Run 3)

- `min_followers=5000` mató 12/25 enriquecidos (48%) — decidir si el default baja para nichos nano-ricos como mascotas VE
- Cap `TIER_MAX_FOLLOWERS=50K` mató 2 — el benchmark IA decía "ideal 10k-100k"
- `reels=0`, `topsearch=0`, `suggested=0` — tres fuentes dormidas a investigar
- Filtro tienda + `is_business` dan ventaja a empresas sobre creadores — revisar pesos tras ver entregas reales

---

## 🔄 CORRECCIÓN F2 (07-sep, noche): endpoint de medias cambiado a /v2/user/medias

El shape test en Railway console (2 corridas, ~$0.12) reveló la verdad completa:

1. **`/gql/user/medias` es un stub NO FULFILLIDO**: el envelope `stream_rows` trae solo `{is_fulfilled__(name: "XDTProfileFeedDict"): true}` — **cero posts**, sin importar cuánto se refiné el extractor. La spec lo recomienda, pero en la práctica no entrega.
2. **`/v2/user/medias` (REST) es perfecto**: `{response: {items: [12 posts directos]}}` — cada item ES el post con `pk`/`like_count`/`comment_count` al tope (verificado con @ecoanimalistadevenezuela: like_count=26, comment_count=1). Sin wrapper edges/node.

**Fix aplicado:**
- `get_user_medias()` → endpoint `/v2/user/medias` (docstring documenta la evidencia empírica vs spec)
- `_extract_posts()` → forma `response.items[*]` PRIMERO (post directo, sin node); todas las formas gql/legacy quedan como fallback
- `scripts/test_user_medias.py` → ahora end-to-end (enrich → get_user_medias → posts con likes + ER estimado)

**Lección registrada:** la spec describía el endpoint pero no su comportamiento real con esta cuenta/tipo de perfil — el dump empírico (walk recursivo de claves + dump JSON completo) resolvió en una iteración lo que la adivinación no resolvió en dos.

---

*GLM 5.3 Flash (opencode) · 07-sep-2026*
