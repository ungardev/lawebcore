# Hito 22 — Desbloquear la producción de candidatos

> **Base:** commit `588c1a3`
> **Parche:** `hito22.patch` — aplicar con `git apply`
> **Archivos:** 3 · **+77 / −13 líneas** · los tres compilan (`py_compile`)
> **Auditoría de origen:** `LENS_AUDIT6_2026-08-17.md`

---

## 0. LA CORRECCIÓN MÁS IMPORTANTE — Y UNA RECTIFICACIÓN

En la sexta auditoría escribí que el pipeline devolvía 0 candidatos *"cuando el enrichment falla"*. **Me quedé corto: falla siempre**, con o sin saldo, con o sin enrichment exitoso.

### La prueba

`latestPosts` no aparece **en ninguna línea** de `hikerapi_client.py`. `_normalize_user()` no lo produce, y `enrich_profile()` devuelve exactamente `_normalize_user(user)`. El cliente tampoco tiene ningún endpoint de posts de usuario — sólo de hashtag y de ubicación.

Por lo tanto, en `worker.py`:

```python
latest = p.get("latestPosts") or []   # ← SIEMPRE []
er = 0.0
if latest and followers > 0:          # ← NUNCA se cumple
    er = (likes_avg + comments_avg) / followers
```

**`er` es 0.0 para todos los perfiles, siempre.**

Y entonces:

```python
if er < 0.005 and followers > 5000:   # 0.0 < 0.005 → siempre True
    bots_filtered += 1
    continue
```

### El resultado

Cruzando ese filtro con el mínimo (`plan.min_followers = 5.000`, línea 1057):

| Seguidores | Qué pasa |
|---|---|
| < 5.000 | Descartado (línea 1057) |
| **exactamente 5.000** | **Único caso que sobrevive** |
| > 5.000 | Descartado como bot (línea 1078) |

**La ventana de aceptación real del pipeline era `[5.000, 5.000]`.** En la práctica, cero.

No era un problema de calibración, ni de geo, ni de saldo. Los 402 y el balance fueron ruido: aunque el enrichment hubiera funcionado al 100% con saldo de sobra, el resultado habría sido el mismo. **Y explica por qué ninguna de las cinco auditorías anteriores lo detectó: todas buscábamos en el scoring, y el perfil moría antes de llegar ahí.**

---

## 1. CORRECCIONES INCLUIDAS

| # | Corrección | Archivo | Efecto |
|---|---|---|---|
| 1 | `PARTIAL = "partial"` en el enum | `schemas.py:17` | `GET /runs/{id}` deja de dar 500 |
| 2 | **Filtro anti-bot sólo con datos reales** | `worker.py:1064-1090` | **Desbloquea los candidatos** |
| 3 | `actual_cost_usd` desde el contador de BudgetFuse | `worker.py:1488` + `budget_fuse.py` | El costo real se persiste |
| 4 | `above_max_followers` separado de `below_min_followers` | `worker.py:1060, 1318` | El log deja de mentir |
| 5 | Techo de seguidores configurable desde el brief | `worker.py:1049` | Deja de excluir el tier medio |
| 6 | Contador `no_engagement_data` en el diagnóstico | `worker.py:1318` | Mide el agujero de ER |

---

## 2. DETALLE POR CORRECCIÓN

### 2.1 · Filtro anti-bot — la que desbloquea todo

```python
# HITO 22: `latestPosts` sólo existe si alguna fuente lo pobló.
# HikerAPI /v2/user/by/username NO devuelve posts, así que hoy
# `latest` está vacío para todos los perfiles.
has_engagement_data = bool(latest) and followers > 0
if has_engagement_data:
    likes_avg = ...
    er = (likes_avg + comments_avg) / followers

p["engagement_rate"] = er if has_engagement_data else None
p["_has_engagement_data"] = has_engagement_data

# El filtro anti-bot sólo puede opinar cuando hay datos reales.
if has_engagement_data:
    if er > 0.30:
        bots_filtered += 1
        continue
    if er < 0.005 and followers > 5000:
        bots_filtered += 1
        continue
else:
    no_engagement_data += 1
```

Dos decisiones deliberadas:

- **`engagement_rate = None`** en vez de `0.0` cuando no hay datos. Un ER de cero es una afirmación falsa sobre el perfil; `None` dice la verdad: "no lo sabemos". La columna es nullable.
- **El contador `no_engagement_data`** convierte el agujero en una métrica visible. En el próximo run te dirá exactamente cuántos perfiles pasan sin datos de engagement — hoy serán el 100%.

### 2.2 · Costo real persistido

El dato ya existía en el sitio correcto. Desde el hito 21, `lens:budget:run:{run_id}` cuenta las llamadas HTTP reales (los cache hits y el modo replay no lo tocan). Ese contador × precio **es** el costo del run.

```python
hikerapi_calls = await budget_fuse.get_run_calls(run_id)
hikerapi_cost = hikerapi_calls * settings.HIKERAPI_COST_PER_CALL_USD
total_cost = round(hikerapi_cost + cost_summary.get("total_usd", 0.0), 6)
```

Se añade `BudgetFuse.get_run_calls()` (un `GET` sobre la clave del run), se registra la fila en `api_costs`, y se emite el log `run_cost_recorded` con el desglose.

**Por qué así y no conectando `HikerAPIClient` al `DiscoveryCostTracker`:** eso reintroduciría dos canales de contabilidad, que es exactamente el bug de doble conteo que el hito 21 acaba de eliminar. La lectura desde BudgetFuse mantiene un solo punto de verdad.

**Detalle de orden:** `reset_run_counter()` ahora se ejecuta **después** de leer el contador. Antes se leía un contador ya borrado.

### 2.3 · Techo de seguidores desde el brief

```python
max_followers_cap = TIER_MAX_FOLLOWERS          # 50.000 por defecto
if brief.influencer_preferences:
    pref_max = brief.influencer_preferences.get("max_followers")
    if isinstance(pref_max, int) and pref_max > 0:
        max_followers_cap = pref_max
```

La constante `TIER_MAX_FOLLOWERS = 50_000` hacía imposible devolver un perfil mid o macro aunque el cliente lo pidiera. Ahora es el default, no la ley.

### 2.4 · El log deja de mentir

`above_max_followers` era contabilizado en `low_followers_skipped` — la etiqueta decía justo lo contrario de lo que hacía, y por eso el embudo era indiagnosticable. Ahora el diagnóstico emite:

```
untracked_no_followers · below_min_followers · above_max_followers
bots_filtered · no_engagement_data · geo_country_mismatch
geo_no_signal · political_filtered · geo_passed · total_handles
```

Con eso, el próximo run te dice en qué escalón exacto muere cada perfil.

---

## 3. LA DECISIÓN QUE QUEDA ABIERTA — EL ER

Este parche hace que la ausencia de ER **deje de matar candidatos**. No crea el dato. Y el ER pesa **0.389 en `lens_score`** — el componente más grande. Hoy ese 38,9% vale cero para todos por igual: no altera el orden relativo, pero sí hace que el `match_score` sea un número que no significa lo que aparenta.

Tres caminos:

| Opción | Cómo | Costo extra/run | Cuándo |
|---|---|---|---|
| **A** | Dejarlo así: ranking por geo + nicho + business intent | **$0** | Ahora — desbloquea sin gastar |
| **B** | Renormalizar los pesos de `lens_score` cuando falta ER | $0 | Junto con A, para que el score sea honesto |
| **C** | Traer posts vía endpoint de medias para el top N tras los filtros | ~$0.30 (top 15) | Cuando el ranking importe de verdad |

**Recomiendo A + B ahora, y C sólo después de comprobar que el pipeline produce candidatos.** Traer ER para 50 perfiles duplicaría el costo del enrichment antes de saber si el resto funciona.

*(B no está en este parche: toca `lens_score` y prefiero que valides primero que salen candidatos.)*

---

## 4. VERIFICACIÓN SIN GASTAR

**El run `1a1d6128` dejó su dataset en Redis con TTL de 24 h.** Es una ventana gratuita que se cierra pronto.

```bash
git apply hito22.patch
# redeploy en Railway — el worker ARQ NO recarga código solo
```

1. `RUN_MODE=replay`
2. Relanza un run sobre el mismo brief (belleza/skincare/VE)
3. Revisa el log `scoring_diagnostic`

**Qué esperar:**

| Antes | Después |
|---|---|
| `bots_filtered` ≈ todos los que llegaron | `bots_filtered = 0`, `no_engagement_data` = todos |
| `total_candidates = 0` | **> 0** |
| `actual_cost_usd = 0.0` | `0.0` (replay no cobra — correcto) |

Si `total_candidates` sigue en 0, el log ya te dirá en qué filtro mueren, que es justamente lo que antes no se podía ver.

**Después, con saldo:** un run en vivo debe grabar `actual_cost_usd > 0` y `GET /runs/{id}` devolver 200 con `status="partial"`.

---

## 5. LO QUE ESTE PARCHE NO ARREGLA

- **El precio del enrichment (§5 de la auditoría 6).** Tus propios números —`$5.00 → $3.38`— dicen que quedaban $3.38 cuando llegó el 402. Si `/v2/user/by/username` cuesta más de $0.02, tu modelo de costos está mal. **Verifícalo con una sola llamada** y mira el delta en facturación: $0.02 de gasto para cerrar la pregunta más cara del proyecto.
- **El prefiltro ciego** que decide a quién enriquecer con bio vacía (hito 23).
- **Las fuentes de perfil reducido** (hashtag, reels) que cuestan $0.38/run y producen perfiles que ni siquiera llegan al scoring.

---

*Correcciones preparadas sobre `588c1a3`. No se ejecutó código del pipeline ni se consumieron créditos.*
