# SÉPTIMA AUDITORÍA — LENS Discovery Module (Post-Hito 22)

> **Audiencia:** Claude Code Opus 5 (o cualquier senior full-stack developer)
> **Contexto:** Proyecto La Web Core — LENS Discovery Module
> **Repositorio:** https://github.com/ungardev/lawebcore
> **Stack:** FastAPI + React 19 + PostgreSQL + Redis + HikerAPI "Start" ($0.02/req) + DeepSeek

> **Nota para Opus 5:** Esta es una auditoría de seguimiento. Los bugs 1-3 de la auditoría anterior YA FUERON RESUELTOS por el equipo (Hito 22). Esta auditoría documenta 3 bugs NUEVOS descubiertos en el test run real post-Hito 22.

---

## CONTEXTO — QUÉ PASÓ

### Hito 22 aplicado (commit `7e4a99b`)

Después de la Sexta Auditoría, el equipo aplicó Hito 22 con los fixes de los 3 bugs críticos:
- Bug 1: `PARTIAL = "partial"` añadido al enum Pydantic ✅
- Bug 2: Método `get_run_calls()` en `budget_fuse.py` + worker actualiza `actual_cost_usd` ✅
- Redeploy en Railway — worker recargó código ✅

### Test Run Real Hito 22 (Run ID: `0c44ea23-53f6-42a8-8a9c-c6ec85359d2e`)

**Fecha:** 2026-08-18, 19:50:56 → 19:52:40 UTC (110 segundos)

**Brief:**
```json
{
  "product_name": "Test Hito 22",
  "industry": "belleza",
  "niches": ["makeup", "skincare", "haircare", "nails", "beauty blogger", "belleza Venezuela"],
  "platforms": ["instagram"],
  "audience_countries": ["VE"],
  "exclude_stores": true,
  "analyze_with_ai": true
}
```

**Pipeline logs:**
```
[discovery_run_task] START run_id=0c44ea23-53f6-42a8-8a9c-c6ec85359d2e
[STEP1] 60 posts from hashtags source=hikerapi
[STEP2] 66 users from keywords source=hikerapi
[STEP1_RECENT] 40 posts from recent hashtag search
[STEP2p5_REELS] 0 creators from reels search
[STEP3] 0 accounts from topsearch
[STEP4] 0 accounts from suggested
[DIAG] unique_handles=133
[STEP 3] Profile enrichment (HTTP 402 Payment Required — balance agotado)
[SCORING] 0 scored → 0 score≥5 → 0 qualified (tienda_excluded=True)
[discovery_run_task] DONE total_candidates=0
```

**Resultados verificados:**

| Indicador | Resultado | Análisis |
|-----------|-----------|----------|
| `status` | `partial` | ✅ 200 OK — no más 500 Error |
| `actual_cost_usd` | **$1.64** | ✅ Cost tracking funcionando |
| `api_costs` insertado | **82 calls × $0.02** | ✅ Registro correcto |
| `total_unique_handles` | **133** | ✅ Discovery efectivo |
| `total_candidates` | **0** | ❌ Todos filtrados por `exclude_stores=true` |
| `step3_degraded` | `true` | ✅ Flag correcto (402 mid-enrichment) |

**Redis confirmadas:**
```
lens:budget:hikerapi:2026-08 = "1.64"
lens:budget:run:0c44ea23-53f6-42a8-8a9c-c6ec85359d2e = 82
```

---

## ESTADO DE BUGS ANTERIORES

| Bug # | Descripción | Estado |
|-------|-------------|--------|
| 1 | Pydantic enum sin `partial` | ✅ **RESUELTO** — `PARTIAL = "partial"` añadido |
| 2 | `actual_cost_usd = 0` (silos de costo) | ✅ **RESUELTO** — `$1.64` grabado correctamente |
| 3 | Balance insuficiente ($5 agotados rápido) | ⚠️ **PERSISTE** — HikerAPI balance = $0 remaining |

---

## 3 BUGS NUEVOS PARA OPUS 5

---

### BUG N1 — `exclude_stores` elimina 100% de handles en VE (🔴 CRÍTICA)

**Severidad:** 🔴 CRÍTICA — Bloquea producción de candidatos en Venezuela.

**Problema:** El default `exclude_stores=true` del wizard elimina prácticamente TODOS los handles cuando el nicho es belleza en Venezuela. En este mercado, el ecosistema de "influencers" de belleza es casi 100% tiendas online que venden productos.

**Handles enriquecidos en el run (TODOS fueron filtrados como tiendas):**
```
shopmarianazambrano.ve — tienda
tashashop.ccs — tienda
canaimashop_ve — tienda
najustoreve — tienda
productosdebellezavenezuela — tienda
aleacosmetics.vzla — tienda
sakuracarevzla — tienda
fiorellacosmetics.vzla — tienda
mtc.productos_de_belleza_vnzla — tienda
```

**Mensaje real del worker:**
```
[SCORING] 0 scored → 0 score≥5 → 0 qualified (tienda_excluded=True)
```

**Pero el mensaje al usuario dice:**
> *"Escaneé 133 perfiles y 0 pasaron el filtro geográfico, pero ninguno califica en nicho o calidad (las tiendas y perfiles genéricos fueron filtrados)"*

Esto dice "filtro geográfico" — lo cual es ENGañOSO. Fue "filtro de tiendas".

**Causa raíz:** `scoring.py` función `is_tienda_signal()` detecta señales de tienda (bio con "shop", "tienda", "$", " venta", hashtags comerciales) + `exclude_stores=True` en el brief.

**Fix requerido (elegir uno):**

**Opción A — Toggle en BriefWizard (recomendado para VE/AR/MX):**
```python
# En el wizard, para nichos de belleza en mercados LATAM:
# "Incluir tiendas?" → toggle default=True
# El brief se construye con exclude_stores=False para estos casos
```

**Opción B — Scoring más inteligente:**
```python
# Solo excluir si tienda Y niche_relevance < 0.3
# Una tienda con alto match de nicho es un lead válido
if is_tienda and niche_relevance < 0.3:
    tienda_excluded = True
```

**Opción C — Score penalty en vez de exclude hard:**
```python
# No exclude hard — penalizar el score
if is_tienda:
    match_score -= 20  # penalty pero no hard exclude
```

---

### BUG N2 — Mensaje al usuario engañoso (⚠️ MEDIA)

**Severidad:** ⚠️ MEDIA — No bloquea producción pero confunde al usuario.

**Problema:** El mensaje final dice "filtro geográfico" cuando la causa real fue "filtro de tiendas". El usuario no entiende qué pasó.

**Fix sugerido:**
```python
# En worker.py, al reportar resultados:
if tienda_excluded_count > 0 and total_candidates == 0:
    message = (
        f"⚠️ {tienda_excluded_count} cuentas fueron identificadas como tiendas "
        f"y excluidas del resultado. En Venezuela la mayoría de perfiles de "
        f"belleza son tiendas. ¿Querés incluir tiendas en la búsqueda?"
    )
else:
    message = f"⚠️ 0 candidatos que califiquen. Ajustá el brief..."
```

---

### BUG N3 — Geolocalización sin validación post-enrichment (⚠️ MEDIA)

**Severidad:** ⚠️ MEDIA — Afecta calidad de candidatos en mercados ambiguous.

**Problema:** Los `geo_indicators` (31 términos VE: caracas, maracaibo, vzla, 🇻🇪, chamo, panas, etc.) se generan en el profile fingerprint y se usan en scoring, pero NO se validan contra la bio del perfil después del enrichment.

**Escenario de riesgo:** Un handle de México o Colombia cuyo bio dice "skincare venezuela" (keyword stuff) podría rankear alto sin ser realmente de Venezuela.

**Fix sugerido:**
```python
# En scoring.py, después del enrichment:
def validate_geo_signal(profile, geo_indicators):
    bio = profile.bio.lower()
    location = (profile.location or "").lower()

    matches = sum(1 for g in geo_indicators if g.lower() in bio or g.lower() in location)
    if matches < 2:
        return False  # No enough geo signal
    return True

# En lens_score:
if not validate_geo_signal(profile, geo_indicators):
    geo_score *= 0.5  # 50% penalty
```

---

## CONTEXTO ECONÓMICO (Importante)

```
COSTO POR RUN (confirmado con datos reales):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Discovery (31 calls):    $0.62
Enrichment 50 handles:  $1.00
─────────────────────────
Total típico:           $1.62 / run

Con AI analysis:        +$0.05 = $1.67 / run
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HIKERAPI BALANCE:       $0 remaining ⚠️
PARA 5 RUNS NECESITAS:  $10-15 USD mínimo
PARA 10 RUNS/MES:       $20-30 USD
```

⚠️ **El costo de $1.50-3.00 por run es elevado.** Con $10 de saldo solo se hacen ~5-6 runs completos.

**Recomendación adicional:** Reducir `MAX_HANDLES_TO_ENRICH` de 50 a 20 para cortar enrichment cost a ~$0.40 y permitir ~15 runs con $10.

---

## PLAN DE VERIFICACIÓN POST-FIX

Después de que Opus 5 aplique los fixes de N1, N2, N3:

1. **Fix N1 (exclude_stores):** Recargar HikerAPI, re-run con `exclude_stores=false`, verificar `total_candidates > 0`
2. **Fix N2 (mensaje):** Leer mensaje del assistant — debe mencionar "filtro tiendas" explícitamente
3. **Fix N3 (geo validación):** Verificar que profiles enriquecidos tienen bio con geo_indicators

---

## CÓMO PROCEDER

1. **Opus 5:** Aplica fixes N1, N2, N3
2. **Nosotros:** Redeploy en Railway
3. **Nosotros:** Recargar HikerAPI (mínimo $10)
4. **Nuevo test run** con `exclude_stores=false`
5. **Verificar:** `total_candidates > 0`, mensaje claro, geo_score > threshold

---

## INFRAESTRUCTURA ACTUAL

```
Repositorio:    https://github.com/ungardev/lawebcore
Repo actual:    commit 7e4a99b (Hito 22 aplicado)
Backend:        Railway — lawebcore-production
Frontend:       Vercel — lawebcore.vercel.app
PostgreSQL:     Railway (postgres.railway.internal:5432/railway)
Redis:          Railway (ARQ + cache + budget)
API:            https://lawebcore-production.up.railway.app/api/v1
HikerAPI:       Balance $0 — necesita recarga
```

**Credenciales en localStorage (`laweb_token`):**
```
ungar.villamizar@hacemosloquenosgusta.com
Rol: admin_general
```

---

## ARQUITECTURA WORKER.PY ACTUAL

```
DeepSeek → BriefStructured → QueryBuilder → DiscoveryPlan
                                              ↓
                          ┌─ STEP 1: Hashtag Top (3×)     → usuario REDUCIDO
                          ├─ STEP 1_recent (2×)           → usuario REDUCIDO
                          ├─ STEP 2: Keyword (3×3)         → usuario COMPLETO
                          ├─ STEP 2p5: Reels (1×)          → usuario REDUCIDO
                          ├─ STEP 3: Topsearch (1×2)      → usuario COMPLETO
                          └─ STEP 4: Suggested (1×)       → usuario COMPLETO
                                                    ↓
                                PREFILTRO (top 50 por rough score)
                                                    ↓
                                ENRICHMENT (hasta 50 handles)
                                                    ↓
                                SCORING (geo + niche + lens_score)
                                                    ↓
                                INSERT → discovery_candidates
```

---

## LO QUE NECESITAMOS DE OPUS 5

**Sé brutalmente honesto. El sistema tiene 22 hitos aplicados pero 0 candidatos producción en VE (el mercado más importante). Necesitamos:**

1. **Fix N1 (exclude_stores VE) — 30-60 min:** Diseñar e implementar la solución para que el pipeline funcione en mercados donde "influencer de belleza" ≈ "tienda". Opcional: reducir MAX_HANDLES_TO_ENRICH para bajar costo.

2. **Fix N2 (mensaje engañoso) — 10 min:** Cambiar el mensaje final del worker para que diga "filtro tiendas" en vez de "filtro geográfico".

3. **Fix N3 (geo post-enrichment validation) — 30 min:** Implementar validación de geo_indicators contra bio del perfil después del enrichment.

4. **Cualquier otro bug** que encuentres en el código mientras investigas.

**La recompensa:** El pipeline de discovery más caro y complejo que hemos construido, funcionando en producción por primera vez con candidatos reales en VE.

---

*Documento generado: 2026-08-18 — Séptima auditoría LENS post-Hito-22-test-run-real (3 bugs nuevos N1-exclude_stores, N2-mensaje, N3-geo_validation)*
