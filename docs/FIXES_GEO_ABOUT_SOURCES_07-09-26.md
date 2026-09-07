# LENS · BATCH — Geo real (about.country) + fuentes dormidas + prefilter v2
## 07-09-2026 · La Web Figital Agency

> **Contexto:** Run 4 (`3d952d25`, $1.84) validó el Prompt v2 (5× entregados, keywords de identidad de creador) pero los 5 candidatos tenían "vzla/venezuela" en el username. Causa: el filtro geo es **basado en texto** (bio/username/location) — un creador venezolano sin "vzla" en el nombre es eliminado. Este batch lo resuelve con **verificación por país de registro** + despierta 3 fuentes dormidas.

---

## CAMBIOS

### B1 — Topsearch desbloqueado (fuente dormida)
`/gql/topsearch` con `flat=true` devuelve **items planos** — `__typename` y `user` al tope del item, sin wrapper `.data`. El parser viejo buscaba `row.data.__typename` → `typename=""` → **todo descartado → 0 accounts en TODOS los runs**. Fix: usar el item directo cuando no tenga `.data` + log de diagnóstico.

### B2 — Reels + suggested: diagnóstico de forma
Ambos devolvían 0 consistentemente. Agregados logs `hikerapi_user_medias_unknown_shape`-style (keys reales + preview) para diagnosticar con 1 corrida de `scripts/test_discovery_sources.py`.

### B3 — About `date` → edad real de cuenta
El schema About trae `date` (creación de cuenta), NO `account_age_days` — por eso el fraude por cuenta nueva (<90 días → penalty 0.90) **nunca aplicaba**. Ahora se parsea `date` → edad en días.

### B4 — Prefilter v2: señal de engagement (gratis)
`_post_likers_count` (likes del post que descubrió al perfil) ya se capturaba pero **se perdía** al construir el dict de profiles. Ahora se preserva (hashtag + recent) y multiplica el rough score: ≥300 ×1.35, ≥100 ×1.15, <30 ×0.8, sin señal → neutro. Los 25 slots de enrichment se llenan con creadores cuyo contenido funciona.

### B5 — Exclusión brand-own + geo por registro (Run 4 validó)
- `@dogchowve` (cuenta de la marca) auto-excluida por `_brand_tokens` (bigrams ≥6: "dogchow" — sin falso positivo "chow")
- `HIKERAPI_INCLUDE_ABOUT=true` (tú la creaste en Railway): `about.country` fluye al scoring → `if about_country == "VE": geo = max(geo, 0.85)` — **creador venezolano sin "vzla" en el nombre pasa por país de registro**

## RUN 4 vs RUN 3 (evidencia que motivó este batch)

| Métrica | Run 3 (prompt v1) | Run 4 (prompt v2) |
|---|---|---|
| Keywords ejecutadas | "comida para perros"... (buy-intent) | "veterinario", "dog mom"... (identidad) |
| Usuarios por keywords | 43 | **101 (2.3×)** |
| Entregados | 1 | **5** |
| ER real | 1.4% | 1.4-5.3% (5 candidatos) |

## VERIFICACIÓN

- **263 passed** (+16), 7 failed = baseline intacto, ruff sin errores nuevos en archivos nuevos

## RUN 5 — expectativa

Con `HIKERAPI_INCLUDE_ABOUT=true` (ya en Railway) + fuentes desbloqueadas:
- Candidatos **SIN "vzla" en el username** verificados venezolanos por `about.country`
- Topsearch/reels/suggested aportando (si las formas requieren ajuste, los logs de diagnóstico lo dicen)
- Volumen ≥ 5 entregados

## PENDIENTE POST-RUN 5 (tuning con datos)

- `min_followers=5000` mató 12-18/run — knob de producto
- `MAX_HANDLES_TO_ENRICH=25` — subir a 40 = +$0.45/run
- Filtro tienda vs creadores profesionales (veterinarios ≠ influencers)

---

*GLM 5.3 Flash (opencode) · 07-sep-2026*
