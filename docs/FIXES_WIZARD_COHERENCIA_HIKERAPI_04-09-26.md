# LENS · FIXES WIZARD — Coherencia Nichos/Hashtags ↔ HikerAPI
## 04-09-2026 · La Web Figital Agency

> **HEAD base:** `a8758b6` · Solo frontend (BriefWizard.tsx + HashtagSuggestions.tsx) · tsc + eslint limpios

---

## PROBLEMA

El paso 2 del wizard mostraba *"nichos detectados automáticamente"* — **falso**: eran presets hardcodeados (`NICHE_PRESETS`) auto-rellenados al elegir industria. Peor: varios presets eran incoherentes con la mecánica de discovery y **quemaban llamadas HikerAPI sin resultados**.

### Mecánica real (por qué importan los presets)

| Input del wizard | Viaja a | Endpoint HikerAPI |
|---|---|---|
| Cada nicho | Keyword query + «nicho venezuela» + «nicho vzla» | `GET /v3/fbsearch/accounts` |
| Hashtags (paso 4, van PRIMEROS) | Primeros **6** en Top + primeros **4** en Recientes | `/v2/hashtag/medias/top` + `/recent` |
| Nichos + brief | Contexto del generador DeepSeek (keywords/hashtags del perfil) | — |

### Incoherencias corregidas

| # | Antes | Consecuencia | Fix |
|---|---|---|---|
| 1 | `'pet care'`, `'vet Venezuela'` en inglés | fbsearch devolvía cuentas gringas → muertas por geo filter → **3 llamadas quemadas por nicho** | Presets 100% español con intención de búsqueda de cuentas VE (`veterinaria`, `adiestramiento canino`, `grooming`...) |
| 2 | `'perrosvzla'` como nicho | Como keyword busca *cuentas* llamadas "perrosvzla" (poco fructífero); como hashtag es oro | Los tags viven SOLO en el paso 4 |
| 3 | Solo 7/12 industrias con presets | "Hogar"/"Deportes" → paso 2 vacío | **12/12 industrias** con presets |
| 4 | Label miente ("detectados automáticamente") + espacio inicial | Desconfianza, look tosco | "Nichos de la campaña" + subtítulo que explica la mecánica real |
| 5 | Ícono ✅ Check para QUITAR nicho | Parece confirmar, no quitar | ❌ X (como HashtagChips) |
| 6 | "Sugeridos para mascotas" (value crudo) | Look tosco | "Sugeridos para Mascotas" (label) |
| 7 | HashtagSuggestions solo 3 industrias + tags no alineados al backend | Sugerencias desconectadas de lo que ejecuta el worker | Alineado a `VE_NICHE_HASHTAGS` (query_builder.py), **12 industrias**, grupos "las ejecuta el pipeline" |
| 8 | Cero transparencia de ejecución | El usuario no sabe qué pasará | Paso 4: nota top-6/recent-4 · Paso 6: **Plan de búsqueda real** (keywords×3 variantes, hashtags ejecutados, ~25 enriquecidos, análisis IA) |

## ARCHIVOS

- `apps/web/src/features/lens/components/BriefWizard.tsx` — presets 12 industrias, paso 2 honesto (X, contador «≈ N×3 búsquedas»), nota paso 4, plan de ejecución en paso 6, plataformas con label, imports limpios
- `apps/web/src/features/lens/components/HashtagSuggestions.tsx` — reescrito: alineado a `VE_NICHE_HASHTAGS` (backend), 12 industrias, tags en minúscula (matching con la normalización de HashtagChips)

## VERIFICACIÓN

- `tsc --noEmit` ✅ · `eslint` (2 archivos) ✅

## IMPACTO ESPERADO EN RESULTADOS

Cada nicho en español con intención de cuenta VE (ej: «veterinaria venezuela») devuelve cuentas venezolanas reales de primer golpe — más candidatos por llamada, cero llamadas quemadas. Los hashtags sugeridos son los mismos que el backend auto-agrega → lo que el usuario elige es exactamente lo que el worker ejecuta en Top/Recent.

---

*GLM 5.3 Flash (opencode) · 04-sep-2026*
