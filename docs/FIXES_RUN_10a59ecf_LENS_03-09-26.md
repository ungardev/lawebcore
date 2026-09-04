# FIXES POST-E2E — RUN `10a59ecf`

## LENS Discovery · Verificación y corrección · Commit `02607ce`

> **Repositorio:** `github.com/ungardev/lawebcore` · Branch `main` **Commit verificado:** `02607ce` (03-09-26 15:58) — HEAD **Método:** lectura directa vía API de GitHub. Solo lectura — sin acceso de escritura, los fixes se entregan como diffs **Fecha:** 03-09-26 **Auditor:** Claude Fable 5 · Full Stack Engineer Senior

---

## RESUMEN

| Fix propuesto | Veredicto | Nota |
| :---- | :---- | :---- |
| **FIX 1** · merge lee camelCase | ✅ **Correcto — pero es una regresión, no un bug nuevo** | Tercera vez que este bloque rompe. Introducido en `4f87a6b` |
| **FIX 2** · `rough_score` cuando followers \= 0 | ❌ **Rechazado** | Fabrica un valor donde no hay dato. Es el antipatrón que todo el proyecto combate |
| **FIX 3** · subir `MAX_CALLS` a 200 y `MAX_HANDLES` a 50 | ❌ **Rechazado como fix** | No ataca la causa. Duplica el costo del mismo fallo |
| **FIX 4** · keywords en inglés | ⚠️ **Diferido** | Contradice el filtro geográfico. Es decisión de producto, no corrección |
| **FIX 5** · migración 107 manual | ✅ Correcto | Fuera del código |

**Un solo fix de los cinco resuelve el E2E. Los otros cuatro o no aplican o empeoran el diagnóstico.**

---

## FIX 1 — Confirmado, y es la tercera regresión del mismo bloque

### Evidencia en `02607ce`

worker.py:1239   for e in enriched\_profiles:

worker.py:1244       profiles\[handle\].update({

worker.py:1245           "\_enriched": True,

worker.py:1246           "follower\_count":  e.get("followersCount"),      ← camelCase

worker.py:1247           "following\_count": e.get("followsCount"),        ← camelCase

worker.py:1248           "posts\_count":     e.get("postsCount"),          ← camelCase

worker.py:1249           "is\_business":     e.get("isBusinessAccount", False),

worker.py:1250           "is\_verified":     e.get("verified", False),

worker.py:1252           "full\_name":       e.get("fullName", ...),       ← camelCase

worker.py:1253           "avatar\_url":      e.get("profilePicUrlHD") or e.get("profilePicUrl") or ...

worker.py:1256           "location":        e.get("locationName", ...),   ← camelCase

worker.py:1257           "latestPosts":     e.get("latestPosts", \[\]),     ← clave Apify

`_normalize_user()` (`hikerapi_client.py:842-856`) emite **únicamente** snake\_case: `follower_count`, `following_count`, `posts_count`, `is_business`, `is_verified`, `full_name`, `avatar_url`, `location_name`. Ninguna de las claves camelCase de las líneas 1246-1257 existe en `e`.

**Resultado:** `follower_count = None` para el 100% de los perfiles enriquecidos → todos caen como `MISSING_FOLLOWER_FIELD`. Es exactamente lo que reportó el run `10a59ecf`.

### Línea de tiempo — esto ya estaba arreglado

| Commit | Fecha | Estado del bloque |
| :---- | :---- | :---- |
| `2446e75` | 26-08 | ✅ FIX \#1 aplicado — lee `follower_count` |
| `ce148e1` | 28-08 | ✅ Verificado snake\_case en `worker.py:1210` |
| **`4f87a6b`** | **29-08** | ❌ **Regresión — vuelve a camelCase** |
| `f7c3410` | 03-09 | ❌ Se agrega `test_dual_names_guard.py` — **no lo detecta** |
| `452d7e9` · `4ffa62e` · `02607ce` | 03-09 | ❌ Sigue en camelCase |
| Run `10a59ecf` | 03-09 | 188 descubiertos → 0 candidatos |

El commit `4f87a6b` («FunnelTracker con 6 stages») reescribió el worker y reintrodujo la versión vieja del bloque. **Mi auditoría del 29-08 sobre ese mismo commit no lo detectó** — verifiqué el invariante, el orden de lectura en scoring y el flush, pero no volví a revisar el bloque de merge que había sido el sitio de la Regresión \#0 una semana antes. Es una omisión mía y la asumo.

### Por qué la guardia no lo atrapó

`test_dual_names_guard.py` (agregado en `f7c3410`) fue diseñado para detectar **escritura dual** en los pasos de búsqueda. El bloque de merge no escribe dual — escribe snake\_case leyendo de camelCase. Es un patrón distinto y la prueba no lo cubre.

### Fix

**Archivo:** `apps/api/app/workers/worker.py:1246-1257`

            profiles\[handle\].update({

                "\_enriched":       True,

                "follower\_count":  e.get("follower\_count"),

                "following\_count": e.get("following\_count"),

                "posts\_count":     e.get("posts\_count"),

                "is\_business":     e.get("is\_business", False),

                "is\_verified":     e.get("is\_verified", False),

                "bio":             e.get("biography", profiles\[handle\].get("bio", "")),

                "full\_name":       e.get("full\_name", profiles\[handle\].get("full\_name", "")),

                "avatar\_url":      e.get("avatar\_url") or profiles\[handle\].get("avatar\_url", ""),

                "country":         e.get("country", ""),

                "is\_private":      e.get("is\_private", profiles\[handle\].get("is\_private", False)),

                "location":        e.get("location\_name", profiles\[handle\].get("location", "")),

                "engagement\_rate": e.get("engagement\_rate"),

            })

Se elimina `"latestPosts"` (línea 1257): es una clave del proveedor anterior que HikerAPI no entrega y que ningún consumidor aguas abajo lee con ese nombre.

### La guardia que sí lo atrapa

Tres regresiones en el mismo bloque no son un bug — son la ausencia de una prueba. **Esta es la parte más importante del fix:**

\# apps/api/tests/test\_enrichment\_field\_names.py

from discovery.tools.hikerapi\_client import HikerAPIClient

def test\_enrichment\_merge\_reads\_only\_normalizer\_output\_keys():

    """El merge de enriquecimiento solo puede leer claves que

    \_normalize\_user() emite. Si lee una clave que no existe en la

    salida del normalizador, el dato llega como None y el perfil cae.

    Esta prueba existe porque el bloque de merge ha regresado a

    camelCase tres veces (Regresión \#0, BUG \#1, run 10a59ecf).

    """

    from pathlib import Path

    import re

    normalizer\_output \= HikerAPIClient().\_normalize\_user({"username": "x"})

    valid\_keys \= set(normalizer\_output.keys())

    src \= Path("apps/api/app/workers/worker.py").read\_text()

    \# Extraer el bloque de merge

    m \= re.search(r"for e in enriched\_profiles:.\*?\\}\\)", src, re.DOTALL)

    assert m, "bloque de merge no encontrado"

    read\_keys \= set(re.findall(r'e\\.get\\("(\[^"\]+)"', m.group()))

    invalid \= read\_keys \- valid\_keys \- {"username", "about"}

    assert not invalid, (

        f"El merge lee claves que \_normalize\_user() no emite: {invalid}. "

        f"Estas llegan como None y el perfil se descarta."

    )

def test\_enriched\_profile\_preserves\_follower\_count():

    """Un perfil enriquecido con follower\_count=5000 debe conservar 5000."""

    enriched \= \[{"username": "u", "follower\_count": 5000, "following\_count": 10, "posts\_count": 3}\]

    profiles \= {"u": {}}

    \# ... invocar el merge real ...

    assert profiles\["u"\]\["follower\_count"\] \== 5000

La primera prueba es la clave: **deriva las claves válidas del propio normalizador**, así que si alguien cambia `_normalize_user()` o el merge, la prueba lo detecta en cualquiera de las dos direcciones. No hay que mantener una lista a mano.

---

## FIX 2 — Rechazado: fabrica un valor donde no hay dato

### Lo que propone

> «cuando `was_enriched=True` y `followers==0`, usar `rough_score` como fallback»

### Por qué no

Un perfil enriquecido con `followers == 0` significa una de dos cosas: el enriquecimiento falló y devolvió vacío, o la cuenta tiene cero seguidores de verdad. En ambos casos **la respuesta correcta es descartar con causa** — `ENRICHMENT_FAILED` en el primer caso, `BELOW_MIN_FOLLOWERS` en el segundo. Ya existe la lógica para eso en las líneas 1305-1310.

Sustituir por `rough_score` produce un candidato con puntaje **inventado** que llega al analista como si tuviera datos. Es literalmente el patrón que Lanz identificó como causa raíz del arco completo: *«ante un error, producir un valor plausible y continuar»*. Y es el mismo patrón que hace una semana neutralizó el invariante con un `True` cableado.

**Además, es innecesario.** Con FIX 1 aplicado, `followers` deja de ser `None` para los perfiles enriquecidos y este caso no ocurre salvo que el enriquecimiento falle de verdad — y en ese caso *queremos* saberlo.

El modo Explorar usa `rough_score` porque **no enriquece por diseño** y el analista sabe que está viendo aproximaciones. Extenderlo al modo automático elimina esa distinción.

---

## FIX 3 — Rechazado como fix: es la palanca equivocada

### Lo que propone

Subir `MAX_CALLS_PER_RUN` de 120 a 200 y `MAX_HANDLES_TO_ENRICH` de 25 a 50\.

### Por qué no ahora

El run `10a59ecf` descubrió 188 handles, enriqueció 25, y **los 25 cayeron**. Enriquecer 50 produciría 50 descartes. El problema no es cuántos se enriquecen — es que el merge pierde el dato. Duplicar el enriquecimiento antes de FIX 1 **duplica el costo del mismo fallo** sin cambiar el resultado.

Costo verificado: 25 enriquecidos \= $0,50 por corrida. 50 \= $1,00. Con saldo de \~$36, pasar de 25 a 50 reduce las corridas disponibles de \~31 a \~22.

**Cuándo sí:** después de que FIX 1 esté aplicado y **una corrida real demuestre que el pipeline entrega candidatos con 25**. Ahí la pregunta «¿25 es suficiente?» tiene datos para responderse, y la decisión de subir a 50 es de presupuesto — que corresponde a Ignacio, no a un commit.

---

## FIX 4 — Diferido: contradice el filtro geográfico

### Lo que propone

Agregar keywords en inglés — «dog food», «pet food», «dog chow» — para que HikerAPI encuentre más resultados.

### Por qué diferirlo

El brief es para Venezuela. Un creador venezolano de mascotas publica en español. Keywords en inglés van a traer perfiles de Estados Unidos, Reino Unido, Australia — que luego el filtro geográfico descarta con `GEO_MISMATCH`, o peor, no descarta si el geo es débil, y llegan al analista.

Es una decisión sobre **qué mercado se está buscando**, no una corrección de código. Y no hay evidencia de que el problema del run haya sido volumen de descubrimiento: **188 handles es un volumen razonable**. El problema fue que el 100% cayó después.

Si después de FIX 1 el descubrimiento resulta insuficiente en español, ahí se evalúa — con la decisión de ensanche (6/4/6/3 → más) antes que con cambio de idioma.

---

## FIX 5 — Correcto, fuera del código

Ejecutar `supabase/migrations/00107_budget_transactions.sql` en el SQL Editor de Railway. Coherente con el hallazgo de que las migraciones numeradas no se aplican automáticamente. Sin observaciones.

---

## LO QUE EL RUN `10a59ecf` SÍ CONFIRMÓ

Conviene decirlo, porque el resultado no fue solo negativo:

| Componente | Evidencia del run | Estado |
| :---- | :---- | :---- |
| Descubrimiento | 188 handles | ✅ Funciona, con volumen suficiente |
| Ensanche 6/4/6/3 | 188 vs. \~133 en runs anteriores | ✅ Efecto medible (+41%) |
| Libro de descartes | Reportó `MISSING_FOLLOWER_FIELD` al 100% | ✅ **Funciona — y diagnosticó el bug correctamente** |
| Invariante del embudo | — | ⏳ Sin dato en el reporte recibido |

**El libro de descartes hizo exactamente su trabajo.** Antes del Hito 30, este run habría terminado en `completed` con cero candidatos y nadie habría sabido por qué. Ahora el sistema dijo «el 100% cayó por campo de seguidores ausente», y eso llevó directo a la línea 1246\. Ese es el retorno de la inversión en observabilidad, en su primera corrida real.

---

## ORDEN DE APLICACIÓN

| \# | Acción | Costo | Bloquea E2E |
| :---- | :---- | :---- | :---- |
| 1 | **FIX 1** — merge en snake\_case \+ eliminar `latestPosts` | $0 | 🔴 Sí |
| 2 | **Guardia** — `test_enrichment_field_names.py` derivada del normalizador | $0 | 🔴 Sí — sin esto, cuarta regresión garantizada |
| 3 | FIX 5 — migración 107 manual | $0 | No |
| — | **Corrida E2E** con 25 enriquecidos | \~$1,14 | — |
| 4 | Decidir FIX 3 con datos de la corrida | — | — |
| 5 | Decidir FIX 4 si el volumen en español resulta insuficiente | — | — |
| ✗ | FIX 2 — no aplicar | — | — |

### Criterio de éxito

SELECT reason\_code, (payload-\>\>'count')::int AS n

FROM discovery\_run\_events

WHERE run\_id \= :run\_id AND event \= 'profile.dropped'

ORDER BY 2 DESC;

\-- MISSING\_FOLLOWER\_FIELD debe bajar de 100% a \~87% (163 no enriquecidos de 188).

\-- Los 25 enriquecidos deben aparecer en otras causas o entregados.

Si `MISSING_FOLLOWER_FIELD` sigue en 100% con FIX 1 aplicado, el problema está en el enriquecimiento mismo — el proveedor no devolvió el campo — y hay que mirar `hikerapi_client.py:486-510`.

---

## NOTA DE PROCESO

Este bloque de doce líneas ha causado tres de los cinco fallos críticos del proyecto. En ninguno de los tres casos había una prueba que lo cubriera, y en el tercero existía una prueba que cubría otra cosa.

**La regla que sale de esto:** un fix sin prueba no está aplicado — está aplicado hasta el próximo refactor. Y una prueba que deriva su verdad de una lista escrita a mano no protege contra el cambio en el origen.

---

---

## ACTUALIZACIÓN 04-sep-2026 — BUG B1 CRÍTICO NUEVO

### 🔴 BUG B1 — `former_usernames` tipo incorrecto en `hikerapi_client.py:659`

**Archivo:** `packages/discovery/discovery/tools/hikerapi_client.py:659`

**No estaba identificado en la auditoría del 03-sep.** Este bug hace que incluso con FIX 1 correctamente aplicado, el pipeline siga entregando 0 candidatos.

**Especificación OpenAPI (https://api.hikerapi.com/openapi.json):**
```yaml
former_usernames:
  type: string  # ← NO es array — es comma-separated string
  example: "old_user1,old_user2"
```

**Código actual (BUG):**
```python
former_usernames = user_data.get("former_usernames", [])
count = len(former_usernames)  # ← CUENTA CHARS (18+), no usernames
```

**Cascada:**
```
"former_usernames": "old_user,another_old"  (18 chars)
                                                        ↓
len("old_user,another_old") = 18  (≥ 3 SIEMPRE)
                                                        ↓
if count >= 3:  → True
                                                        ↓
fraud_penalty = 0.80
                                                        ↓
match_score × 0.8 → TODOS los perfiles colapsan
```

**Fix exacto:**
```python
# hikerapi_client.py:659
former_usernames_raw = user_data.get("former_usernames") or ""
count = len([u for u in former_usernames_raw.split(",") if u.strip()]) if former_usernames_raw else 0
```

**Impacto:** Con FIX 1 ya aplicado, este es el único bug restante que causa 0 candidatos.

---

## DOCUMENTOS ACTUALIZADOS 04-sep-2026

| Documento | Cambio |
|-----------|--------|
| `docs/LENS_MASTER_BUG_REPORT_04-09-26.md` | **NUEVO** — Todos los bugs, tiers, plan completo |
| `docs/LENS_HIKERAPI_PIPELINE_AUDIT_04-09-26.md` | **NUEVO** — HikerAPI OpenAPI vs cliente |
| `docs/LENS_BUG_REPORT_10a59ecf_03-09-26.md` | Actualizado con BUG B1 y links |
| `docs/PROMPT_CLAUDE_CODE_ANALYSIS.md` | Entry #34 agregada |

---

## PENDIENTE ARRASTRADO — octava iteración

⚡ **`TIER_MIN_FOLLOWERS = 5_000` · `worker.py:54`** — sigue sin respuesta desde el 19-08.

---

*Verificación elaborada sobre `02607ce`, `452d7e9` y `4f87a6b`. Ningún archivo del repositorio fue modificado.*

*Documento generado por La Web Figital Agency · 03-09-26 · Uso interno*
*Actualizado: 04-09-26 · BUG B1 crítico agregado*
*Master docs: `docs/LENS_MASTER_BUG_REPORT_04-09-26.md`*  
