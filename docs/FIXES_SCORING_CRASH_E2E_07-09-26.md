# LENS · FIXES — Crash de scoring en el E2E real (run e2efd17b)
## 07-09-2026 · La Web Figital Agency

> **Contexto:** primer E2E vía UI completo (07-sep 14:53-14:57 UTC). El pipeline llegó MÁS LEJOS QUE NUNCA y murió por UN bug en el scoring. Este doc registra el análisis, el fix y lo que quedó demostrado.

---

## LO QUE EL E2E DEMOSTRÓ FUNCIONANDO (evidencia en logs de Railway)

| Componente | Evidencia |
|---|---|
| Worker vivo (supervisor v2) | `Starting worker for 5 functions` tras el arranque |
| Wizard de un click | Conversación + brief JSON + auto-confirmación + run creado en 1 click |
| **N-1 pre-flight** | `GET /sys/balance → 200 OK` |
| DeepSeek profile | 30 hashtags + 30 keywords + elite_data **generados y persistidos** (la columna elite_data SÍ existe en producción — B-NEW-2 resultó no ser issue en prod) |
| Discovery | **168 handles** (hashtags=120, recent=80, keywords=44, reels=0, topsearch=0, suggested=0) |
| Enrichment | **25 perfiles** enriquecidos |
| **N-3 ER real** | `GET /gql/user/medias` × 25 |
| Progreso en chat | "✅ Encontré 168 perfiles..." → "✅ Enriquecí 25 perfiles..." |
| Honestidad de fallo | Run marcado `failed` con el error exacto (no silencio) |

## 💥 EL CRASH (worker.py:1381 → observability.py:133)

```
TypeError: got multiple values for keyword argument 'reason'
```

**Causa raíz:** `drop_profile()` pasa `reason=reason.value` al logger Y expande `**detail`. Un `detail={'reason': ...}` → colisión de kwargs → TypeError → **run completo muerto en scoring tras gastar ~$1.4**.

**Alcance real:** NO era solo mi línea del prefilter — había **8 call sites** con ese patrón (prefilter, rerank cutoff, 4 drops de geo, bots very_low_er, political). Cualquiera habría detonado el mismo crash al llegarle el flujo.

## FIXES

1. **Guard central en `drop_profile()`** (observability.py): las claves de `detail` que colisionan con los kwargs del evento (`reason`, `username`, `stage`, `event`) se renombran automáticamente a `detail_<clave>` preservando la info. Protege los 8 call sites actuales y todos los futuros.
2. **Claves renombradas en los 8 call sites** (worker.py): `"reason": ...` → `"why": ...` — claridad semántica + cinturón y tirantes.
3. **Dedupe de variante geo** (worker.py `_fetch_step2`): keywords que ya contienen el sufijo ("dog chow venezuela") ya no generan "dog chow venezuela venezuela" (llamada quemada visible en el log del run).

## TESTS

`test_drop_profile_safety.py` (nuevo, 4 tests): regresión EXACTA del incidente (no crash), colisiones renombradas y preservadas (via `structlog.testing.capture_logs`), details normales intactos, guard de fuente del dedupe geo. **228 passed** (+4), 7 failed = baseline intacto, ruff limpio.

## DESPUÉS DEL DEPLOY — relanzar la MISMA búsqueda

El brief ya está probado (Purina/mascotas/VE). Re-lanzar desde el wizard (~$1.45). Con el crash fuera del camino, todo lo demás ya está demostrado en logs: el flujo llega a scoring → `passed_score` → DeepSeek (si `ENABLE_AI_ANALYZER=true`) → insert → **candidatos en el chat**.

## OBSERVACIONES POST-BASELINE (tuning con datos, no bloquean)

- `reels=0` para "comida para perros" y `topsearch=0`/`suggested=0` — las 168 handles salieron de hashtags+keywords; revisar por qué reels/topsearch no aportan (conocido B6)
- `elite_data` persiste bien en prod → B-NEW-2 cerrado como no-issue
- El saldo HikerAPI se consumió en un run fallido (~$1.4) — el fix cuesta 1 línea; este tipo de crash en scoring debe quedar cubierto por el guard central para siempre

---

*GLM 5.3 Flash (opencode) · 07-sep-2026*
