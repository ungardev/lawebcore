# LENS · Verificación BUG B1 \+ Logging \+ Endpoints dormidos

### HEAD `a67ad72` · 04-09-26 · Claude Fable 5 — Full Stack Engineer Senior

**Método:** lectura directa del código en `github.com/ungardev/lawebcore` vía GitHub API, ref `a67ad72`. Cero inferencia sobre archivos no leídos. **Archivos leídos:** `packages/discovery/discovery/tools/hikerapi_client.py` (864 líneas), `apps/api/app/workers/worker.py` (2.387 líneas), `apps/api/tests/test_enrichment_field_names.py` (106 líneas), árbol completo del repo.

---

## 1\. Tabla de veredictos

| \# | Afirmación del reporte de bugs | Veredicto | Severidad real |
| :---- | :---- | :---- | :---- |
| B1-a | `former_usernames` se cuenta con `len()` sin type guard (`hikerapi_client.py:659-662`) | ✅ **CONFIRMADO** | P1 |
| B1-b | "Cualquier string ≥3 chars activa `fraud_penalty = 0.80`" | ⚠️ **CONFIRMADO EN MECÁNICA, REFUTADO EN IMPACTO** | Latente, no activo |
| B1-c | "HikerAPI devuelve un string, no una lista" | ✗ **NO VERIFICABLE** — no tengo API key. El fix no debe depender de esta premisa | — |
| F1 | FIX 1 (merge snake\_case) pendiente de aplicar | ✗ **REFUTADO — ya está en `a67ad72`** | Sin acción |
| F3-a | `search_followers_of` (:605) existe y nunca se llama | ✅ **CONFIRMADO** — 0 referencias en worker.py | P2 |
| F3-b | `web_profile_info` (:625) existe y nunca se llama | ✅ **CONFIRMADO** — 0 referencias en worker.py | P2 |
| F3-c | `HIKERAPI_INCLUDE_ABOUT` está "dormido" / sin cablear | ✗ **REFUTADO** — cableado en :75 y consumido en :1157. Está *apagado por default*, no desconectado | Config, no código |
| F3-d | `HIKERAPI_STEP0_LOCATION` está "dormido" / sin cablear | ✗ **REFUTADO** — cableado en :470 y consumido en :472-513. Apagado por default | Config, no código |

**Lectura:** de los 5 puntos accionables del prompt, **2 ya están resueltos** (FIX 1 y su guard test), **2 están mal diagnosticados** (los env flags están cableados, solo apagados) y **1 es real pero con severidad sobreestimada** (B1 es latente). El trabajo neto es menor al planteado, pero aparecieron **4 defectos nuevos que nadie reportó** y uno de ellos es peor que B1 (ver §5).

---

## 2\. BUG B1 — cadena completa verificada

### 2.1 El código real

`packages/discovery/discovery/tools/hikerapi_client.py:637-665`

async def get\_user\_about(self, user\_id: int | str) \-\> dict\[str, Any\] | None:

    """GET /v1/user/about — fraud detection signals for a user.

    ...

    \- former\_usernames: list of previous usernames (bots frequently change username)

    ...

    Cost: $0.0006 per call. Call for top 20 ranked candidates per run.

    """

    resp \= await self.\_get("/v1/user/about", params={"id": str(user\_id)}, cache\_ttl=86400)

    if not resp:

        logger.warning("hikerapi\_user\_about\_not\_found", user\_id=user\_id)

        return None

    user\_data \= resp.get("user", {}) or resp

    if not user\_data.get("pk") and not user\_data.get("id"):

        logger.warning("hikerapi\_user\_about\_no\_pk", user\_id=user\_id)

        return None

    former\_usernames \= user\_data.get("former\_usernames", \[\]) or \[\]   \# ← :659

    return {

        "former\_usernames": former\_usernames,

        "former\_usernames\_count": len(former\_usernames),             \# ← :662  DEFECTO

        "account\_age\_days": user\_data.get("account\_age\_days") or user\_data.get("account\_age") or 0,

        "country": user\_data.get("country") or "",

    }

`apps/api/app/workers/worker.py:1454, 1513-1522`

about \= p.get("about") or {}                                          \# :1454

...

former\_usernames\_count \= about.get("former\_usernames\_count", 0\) or 0  \# :1513

account\_age\_days \= about.get("account\_age\_days", 0\) or 0              \# :1514

fraud\_penalty \= 1.0

if former\_usernames\_count \>= 3:

    fraud\_penalty \= 0.80

elif former\_usernames\_count \== 2 or account\_age\_days \> 0 and account\_age\_days \< 90:

    fraud\_penalty \= 0.90

if fraud\_penalty \< 1.0:

    score\_val \= round(score\_val \* fraud\_penalty, 1\)

    logger.debug("fraud\_penalty\_applied", handle=handle, ...)

### 2.2 El defecto es real

`len()` se aplica a un campo de una API externa **sin verificar su tipo**. Las cuatro formas plausibles que puede devolver HikerAPI y lo que produce cada una:

| Lo que devuelve la API | `len()` da | Penalización resultante |
| :---- | :---- | :---- |
| `["viejo1", "viejo2"]` (lo asumido) | 2 | 0,90 ✅ correcto |
| `"viejo1,viejo2"` (string) | 13 | 0,80 ✗ falso positivo |
| `"eli"` (un solo username) | 3 | 0,80 ✗ falso positivo |
| `[{"username": "x", "changed_at": ...}]` | 1 | 1,00 ✅ correcto por accidente |
| `None` | `or []` → 0 | 1,00 ✅ |

Con un string, **el umbral de 3 deja de medir "cambios de username" y pasa a medir "largo de texto"**. Un handle de Instagram tiene mínimo 1 carácter y en la práctica ≥3. El resultado sería una penalización universal de −20% al score de todo perfil con payload `about`.

**No estoy afirmando que la API devuelva un string** — no tengo forma de verificarlo sin key. Lo que sí afirmo: el código no tiene defensa contra ninguno de los tres escenarios erróneos, y el docstring de la línea 641 documenta una asunción que nunca se valida. El fix debe ser **type-agnostic**, no diseñado contra un tipo específico.

### 2.3 Por qué el impacto está sobreestimado

`worker.py:75`

ENRICHMENT\_INCLUDE\_ABOUT \= os.getenv("HIKERAPI\_INCLUDE\_ABOUT", "false").lower() \== "true"

`worker.py:1157`

if profile and profile.get("pk") and ENRICHMENT\_INCLUDE\_ABOUT and hasattr(instagram\_source, "get\_user\_about"):

    ...

    profile\["about"\] \= about\_data   \# :1161

Con el default `false`, `get_user_about()` **nunca se llama**, `profile["about"]` nunca se asigna, y en :1454 `about = p.get("about") or {}` resuelve a `{}`. Entonces `former_usernames_count = 0` → `fraud_penalty = 1.0` → el bloque completo es no-op.

**Consecuencia práctica:** B1 **no está corrompiendo los scores de los runs actuales** — salvo que `HIKERAPI_INCLUDE_ABOUT=true` esté seteado en las variables de entorno de Railway. Eso no lo puedo leer desde el repo.

> ⚠️ **Bloqueante de verificación \#1:** Ungar o Cris tienen que confirmar el valor de `HIKERAPI_INCLUDE_ABOUT` en Railway (producción y staging).  
> 

> - Si está en `false` → B1 es **P1 latente**: hay que arreglarlo *antes* de encender el flag, no hay data histórica corrupta.  
> - Si está en `true` → B1 es **P0 activo**: todo run desde que se encendió tiene scores potencialmente deflactados −20%, y hay que decidir si se re-scorean los runs afectados.

Esta distinción cambia si la respuesta es "arreglamos y seguimos" o "arreglamos y auditamos histórico". No la resuelvo yo.

---

## 3\. FIX 1 — ya está aplicado, sin acción

El bloque de merge en `worker.py:1239-1259` ya lee snake\_case, exactamente como se especificó en `FIXES_RUN_10a59ecf_LENS_03-09-26.md`:

for e in enriched\_profiles:                                  \# :1239

    handle \= e.get("username", "")

    if not handle or handle not in profiles:

        continue

    about\_data \= e.get("about")

    profiles\[handle\].update({

        "\_enriched": True,

        "follower\_count": e.get("follower\_count"),            \# ✅ snake\_case

        "following\_count": e.get("following\_count"),

        "posts\_count": e.get("posts\_count"),

        "is\_business": e.get("is\_business", False),

        "is\_verified": e.get("is\_verified", False),

        "bio": e.get("biography", profiles\[handle\].get("bio", "")),

        "full\_name": e.get("full\_name", profiles\[handle\].get("full\_name", "")),

        "avatar\_url": e.get("avatar\_url") or profiles\[handle\].get("avatar\_url", ""),

        "country": e.get("country", ""),

        "is\_private": e.get("is\_private", profiles\[handle\].get("is\_private", False)),

        "location": e.get("location\_name", profiles\[handle\].get("location", "")),

    })

    if about\_data:

        profiles\[handle\]\["about"\] \= about\_data

Y el guard test existe en `apps/api/tests/test_enrichment_field_names.py`, derivando las claves válidas del normalizador en runtime (no hardcodeadas):

normalizer\_output \= HikerAPIClient().\_normalize\_user({"username": "x"})   \# :50

valid\_keys \= set(normalizer\_output.keys())                                 \# :51

invalid \= read\_keys \- valid\_keys \- known\_extra\_keys                        \# :58

**Nota de corrección propia:** en la propuesta original del 03-09 incluí `"engagement_rate": e.get("engagement_rate")` en el merge. Eso habría sido un bug mío. Verificado en `_normalize_user()` (`hikerapi_client.py:846-860`), el normalizador emite **13 claves** y `engagement_rate` no está entre ellas. Quien aplicó el fix hizo bien en omitirla, y el guard test la habría rebotado. El ER real se calcula en `worker.py:1438`:

p\["engagement\_rate"\] \= er if has\_engagement\_data else None

que respeta NULL≠0 correctamente. Bien ahí.

---

## 4\. FIX 3 — dos de cuatro están mal diagnosticados

Grep exhaustivo sobre las 2.387 líneas de `worker.py`:

| Símbolo | Referencias en worker.py | Estado real |
| :---- | :---- | :---- |
| `search_followers_of` | **0** | Dormido de verdad |
| `web_profile_info` | **0** | Dormido de verdad |
| `HIKERAPI_INCLUDE_ABOUT` | :75 (lectura env), :1157 (uso) | **Cableado**, default `false` |
| `HIKERAPI_STEP0_LOCATION` | :470 (lectura env), :472-545 (uso completo con `search_location` \+ `location_medias_*`) | **Cableado**, default `false` |
| `suggested_profiles` | :634 | **Activo** |
| `search_location` | :472, :483 | **Cableado** vía STEP0 |

Los dos flags no requieren código. Requieren una decisión de presupuesto: encenderlos suma requests por run y hay un `MAX_CALLS_PER_RUN = 120` de por medio. Encender `HIKERAPI_INCLUDE_ABOUT` a $0,0006/llamada sobre 20 candidatos top \= **$0,012 por run**, despreciable. Encender `HIKERAPI_STEP0_LOCATION` sí pesa: agrega búsqueda de location \+ medias top \+ medias recent por cada ciudad del brief.

**Y el orden importa:** encender `HIKERAPI_INCLUDE_ABOUT` **antes** de aplicar el fix B1 es exactamente lo que convierte un bug latente en corrupción de scores. Si alguien lo enciende esta semana sin el patch, cada perfil con `about` se lleva −20% de score.

---

## 5\. Hallazgos nuevos (no estaban en ningún reporte)

### B2 — `country` fabricado como `"VE"` en el path TikTok · **P0, peor que B1**

`worker.py:2192-2199`

elif platform \== Platform.TIKTOK:

    return {

        "handle": author.get("uniqueId", raw.get("handle", "")),

        "followers": stats.get("followerCount"),

        "posts\_count": stats.get("videoCount"),

        "avg\_views": raw.get("videoView"),

        "engagement\_rate": 0.05,                       \# ← fabricado

        "country": raw.get("region", "VE"),            \# ← fabricado

        "url": raw.get("shareUrl", ""),

    }

Dos violaciones directas de la regla NULL≠0, y la segunda es la grave: **todo perfil de TikTok sin `region` en el payload se marca como venezolano**. El filtro geo de LENS (`DropReason.GEO_MISMATCH`, :1468) lo deja pasar. Es un falso positivo silencioso que mete perfiles no-VE en shortlists de campaña venezolana — el error más caro que puede cometer esta herramienta, porque no se detecta hasta que un cliente pregunta por qué le recomendamos un creador colombiano.

El `engagement_rate: 0.05` fijo es igual de tóxico: 5% de ER es un valor plausible, así que pasa desapercibido, y cae dentro de todos los benchmarks de tier. Ningún filtro lo va a marcar como sospechoso.

### B3 — `audience_credibility` y `audience_quality` hardcodeados en 50

`worker.py:2184-2185`

"audience\_credibility": 50,

"audience\_quality": 50,

Mismo patrón. 50 es un valor "neutro" que no dispara ninguna alerta, y se persiste como si fuera medición.

### B4 — `account_age_days ... or 0` duplicado

`hikerapi_client.py:663` y `worker.py:1514`. "Edad desconocida" y "cuenta creada hoy" colapsan al mismo valor. Aquí el guard `account_age_days > 0` de :1518 salva la situación por accidente (0 nunca penaliza), pero el campo se persiste en `fraud_signals` (:1639-1642) como si fuera dato medido.

### B5 — Precedencia sin paréntesis en el `elif`

`worker.py:1518`

elif former\_usernames\_count \== 2 or account\_age\_days \> 0 and account\_age\_days \< 90:

Python evalúa `(count == 2) or (age > 0 and age < 90)`, que es probablemente lo que se quiso. Pero está a un refactor de distancia de convertirse en `(count == 2 or age > 0) and age < 90`. Paréntesis explícitos, gratis.

---

## 6\. Diffs

### FIX B1 — normalización type-agnostic de `former_usernames`

**Archivo:** `packages/discovery/discovery/tools/hikerapi_client.py`

@@ \-655,12 \+655,15 @@ async def get\_user\_about(self, user\_id: int | str) \-\> dict\[str, Any\] | None:

         user\_data \= resp.get("user", {}) or resp

         if not user\_data.get("pk") and not user\_data.get("id"):

             logger.warning("hikerapi\_user\_about\_no\_pk", user\_id=user\_id)

             return None

\-        former\_usernames \= user\_data.get("former\_usernames", \[\]) or \[\]

\+        former\_usernames \= \_coerce\_former\_usernames(

\+            user\_data.get("former\_usernames"), user\_id=user\_id

\+        )

\+        account\_age\_days \= user\_data.get("account\_age\_days")

\+        if account\_age\_days is None:

\+            account\_age\_days \= user\_data.get("account\_age")

         return {

             "former\_usernames": former\_usernames,

             "former\_usernames\_count": len(former\_usernames),

\-            "account\_age\_days": user\_data.get("account\_age\_days") or user\_data.get("account\_age") or 0,

\+            "account\_age\_days": account\_age\_days,   \# None si la API no lo trae — NULL ≠ 0

             "country": user\_data.get("country") or "",

         }

**Helper nuevo, a nivel de módulo (antes de la clase, junto a `_get_breaker()` en :23):**

def \_coerce\_former\_usernames(raw: Any, user\_id: Any \= None) \-\> list\[str\]:

    """Normaliza former\_usernames a list\[str\] sea cual sea la forma que mande HikerAPI.

    El contrato de /v1/user/about no está garantizado. Formas observadas o plausibles:

      \- list\[str\]            → \["viejo1", "viejo2"\]

      \- list\[dict\]           → \[{"username": "viejo1", "changed\_at": ...}\]

      \- str separado por comas → "viejo1,viejo2"

      \- str simple           → "viejo1"

      \- None / ausente       → \[\]

    NUNCA aplicar len() directo sobre \`raw\`: si es str cuenta caracteres y

    convierte el umbral de fraude en una medición del largo del texto.

    """

    if raw is None:

        return \[\]

    if isinstance(raw, str):

        parts \= \[p.strip() for p in raw.split(",") if p.strip()\]

        logger.warning(

            "hikerapi\_former\_usernames\_unexpected\_type",

            user\_id=user\_id,

            received\_type="str",

            parsed\_count=len(parts),

        )

        return parts

    if isinstance(raw, list):

        out: list\[str\] \= \[\]

        for item in raw:

            if isinstance(item, str) and item.strip():

                out.append(item.strip())

            elif isinstance(item, dict):

                name \= item.get("username") or item.get("name") or item.get("value")

                if isinstance(name, str) and name.strip():

                    out.append(name.strip())

        return out

    logger.warning(

        "hikerapi\_former\_usernames\_unexpected\_type",

        user\_id=user\_id,

        received\_type=type(raw).\_\_name\_\_,

    )

    return \[\]

**Consumidor** — `apps/api/app/workers/worker.py`

@@ \-1511,10 \+1511,14 @@

\-            former\_usernames\_count \= about.get("former\_usernames\_count", 0\) or 0

\-            account\_age\_days \= about.get("account\_age\_days", 0\) or 0

\+            former\_usernames\_count \= about.get("former\_usernames\_count")

\+            account\_age\_days \= about.get("account\_age\_days")

             fraud\_penalty \= 1.0

\-            if former\_usernames\_count \>= 3:

\+            if former\_usernames\_count is not None and former\_usernames\_count \>= 3:

                 fraud\_penalty \= 0.80

\-            elif former\_usernames\_count \== 2 or account\_age\_days \> 0 and account\_age\_days \< 90:

\+            elif former\_usernames\_count \== 2 or (

\+                account\_age\_days is not None and 0 \< account\_age\_days \< 90

\+            ):

                 fraud\_penalty \= 0.90

Esto resuelve B1, B4 y B5 en el mismo patch. `None` deja de significar "cero" y deja de penalizar; el `>= 3` ahora opera sobre un conteo real de usernames.

### FIX B2/B3 — eliminar valores fabricados

**Archivo:** `apps/api/app/workers/worker.py`

@@ \-2182,8 \+2182,8 @@

\-                "audience\_credibility": 50,

\-                "audience\_quality": 50,

\+                "audience\_credibility": None,   \# no medido — NULL ≠ 50

\+                "audience\_quality": None,

@@ \-2191,9 \+2191,9 @@

     elif platform \== Platform.TIKTOK:

         author \= raw.get("author", {})

         stats \= raw.get("stats", {})

\+        region \= raw.get("region")

         return {

             "handle": author.get("uniqueId", raw.get("handle", "")),

             "full\_name": author.get("nickname", ""),

             "followers": stats.get("followerCount"),

             "posts\_count": stats.get("videoCount"),

             "avg\_views": raw.get("videoView"),

\-            "engagement\_rate": 0.05,

\+            "engagement\_rate": None,   \# TikTok no expone ER; se calcula aguas abajo o queda NULL

             "country": region.upper()\[:2\] if isinstance(region, str) and region else None,

             "url": raw.get("shareUrl", ""),

         }

Aplicar el mismo criterio al bloque YouTube (`engagement_rate: 0.02`, :2211).

> ⚠️ Este patch **va a hacer caer perfiles** que hoy pasan el filtro geo. Eso es el fix funcionando, no una regresión: son perfiles que nunca debieron pasar. Espera una caída en el conteo de candidatos TikTok del primer run post-deploy, con incremento correspondiente en `DropReason.GEO_MISMATCH`. Si el conteo **no** cambia, el patch no está activo.

### FIX Logging — observabilidad por handle, sin romper structlog

El prompt pedía líneas tipo `[hikerapi.enrichment] handle=@x enriched=true follower_count=12500`. **No lo voy a implementar así**, y esta es la razón:

El repo ya usa structlog con eventos nombrados y kwargs (`logger.info("hikerapi_profile_enriched", username=..., followers=...)` en `hikerapi_client.py:509`). Meter f-strings con prefijo entre corchetes crea una segunda convención de logging: rompe el parseo estructurado, no es grepeable por campo, y contradice el diseño del Hito 30 que costó armar. El mismo objetivo — trazabilidad por handle — se consigue con eventos estructurados.

**El hueco real** es que cuando `enrich_profile()` devuelve `None`, el perfil se queda sin enriquecer y **nadie registra el drop**. Eso sí hay que arreglarlo:

@@ \-1239,6 \+1239,7 @@

\+        enriched\_handles \= {e.get("username", "") for e in enriched\_profiles if e.get("username")}

         for e in enriched\_profiles:

             handle \= e.get("username", "")

             if not handle or handle not in profiles:

\+                logger.warning("enrichment\_orphan\_handle", handle=handle, stage="step3\_merge")

                 continue

             about\_data \= e.get("about")

@@ \-1257,6 \+1258,20 @@

             if about\_data:

                 profiles\[handle\]\["about"\] \= about\_data

\+            logger.info(

\+                "enrichment\_merged",

\+                handle=handle,

\+                follower\_count=profiles\[handle\].get("follower\_count"),

\+                has\_about=bool(about\_data),

\+                country=profiles\[handle\].get("country") or None,

\+            )

\+

\+        for handle in list(profiles):

\+            if handle in enriched\_handles:

\+                continue

\+            logger.warning("enrichment\_missing", handle=handle, stage="step3\_merge")

\+            profiles\[handle\]\["\_enriched"\] \= False

Y en el bloque de fraude, subir el nivel y agregar el caso "no penalizado" para poder auditar la cobertura del flag:

@@ \-1520,7 \+1524,15 @@

             if fraud\_penalty \< 1.0:

                 score\_val \= round(score\_val \* fraud\_penalty, 1\)

\-                logger.debug("fraud\_penalty\_applied", handle=handle, ...)

\+                logger.info(

\+                    "fraud\_penalty\_applied",

\+                    handle=handle,

\+                    former\_usernames\_count=former\_usernames\_count,

\+                    account\_age\_days=account\_age\_days,

\+                    penalty=fraud\_penalty,

\+                    score\_before=round(score\_val / fraud\_penalty, 1),

\+                    score\_after=score\_val,

\+                )

`debug` no se emite con el nivel de log de producción. Un penalty que mueve el score y no aparece en los logs es exactamente el tipo de cosa que nos hizo perder tres iteraciones con el merge de camelCase.

### FIX Endpoints — solo dos son reales

`search_followers_of` y `web_profile_info` están sin llamar. **Recomiendo no cablearlos en este patch.** Razones:

- `search_followers_of` es expansión de red: cambia la topología del funnel y rompe la invariante `funnel.deduped == total + drop_ledger.total()` si no se instrumenta una etapa nueva en `FunnelTracker`. Eso es un hito propio, no un fix.  
- `web_profile_info` es un reemplazo de `enrich_profile`, no un agregado. Su docstring (:628-630) dice que `/v1/user/web_profile_info` falla \~90% desde feb-2026 y que la versión `/gql/` es la recomendada. Si eso es cierto, es una **migración** de `enrich_profile()` — con su propio normalizador, porque el payload GraphQL trae `edge_followed_by` en vez de `follower_count`. Meterla junto a un fix de fraude es cómo se rompen los pipelines.

Los dos flags de env no necesitan código, solo la decisión de encenderlos — **después** del patch B1.

---

## 7\. Tests

**Archivo nuevo:** `apps/api/tests/test_former_usernames_coercion.py`

import pytest

from discovery.tools.hikerapi\_client import \_coerce\_former\_usernames

@pytest.mark.parametrize(

    "raw,expected\_count",

    \[

        (None, 0),

        (\[\], 0),

        ("", 0),

        ("eli", 1),                                   \# BUG B1: antes daba 3

        ("viejo1,viejo2", 2),                          \# BUG B1: antes daba 13

        ("un\_handle\_bastante\_largo", 1),               \# BUG B1: antes daba 24

        (\["viejo1", "viejo2"\], 2),

        (\["viejo1", "", "  ", "viejo2"\], 2),

        (\[{"username": "viejo1"}, {"username": "viejo2"}\], 2),

        (\[{"name": "viejo1"}\], 1),

        (12345, 0),                                    \# tipo inesperado → lista vacía, no crash

        ({"username": "x"}, 0),

    \],

)

def test\_coerce\_never\_counts\_characters(raw, expected\_count):

    assert len(\_coerce\_former\_usernames(raw)) \== expected\_count

def test\_coerce\_always\_returns\_list\_of\_str():

    for raw in \[None, "a,b", \["a"\], \[{"username": "b"}\], 99\]:

        out \= \_coerce\_former\_usernames(raw)

        assert isinstance(out, list)

        assert all(isinstance(x, str) for x in out)

def test\_single\_username\_string\_does\_not\_trigger\_penalty():

    """Regresión B1: un string de 3+ chars no puede cruzar el umbral de fraude."""

    count \= len(\_coerce\_former\_usernames("eli"))

    fraud\_penalty \= 0.80 if count \>= 3 else (0.90 if count \== 2 else 1.0)

    assert fraud\_penalty \== 1.0

**Archivo nuevo:** `apps/api/tests/test_no_fabricated_metrics.py`

import re

from pathlib import Path

WORKER \= Path("apps/api/app/workers/worker.py")

\# Métricas que nunca pueden llevar un literal como default: si no se midió, va None.

FORBIDDEN \= \[

    r'"engagement\_rate"\\s\*:\\s\*0\\.\\d+',

    r'"audience\_credibility"\\s\*:\\s\*\\d+',

    r'"audience\_quality"\\s\*:\\s\*\\d+',

    r'"country"\\s\*:\\s\*raw\\.get\\(\[^)\]\*,\\s\*"VE"\\s\*\\)',

\]

def test\_worker\_does\_not\_fabricate\_metric\_values():

    src \= WORKER.read\_text(encoding="utf-8")

    offenders \= \[\]

    for pattern in FORBIDDEN:

        for m in re.finditer(pattern, src):

            line\_no \= src\[: m.start()\].count("\\n") \+ 1

            offenders.append(f"{WORKER}:{line\_no}  {m.group()}")

    assert not offenders, (

        "Valores de métrica fabricados detectados. Regla LWFA: NULL \!= 0.\\n"

        \+ "\\n".join(offenders)

    )

**Extensión** a `apps/api/tests/test_enrichment_field_names.py`:

def test\_normalizer\_does\_not\_emit\_engagement\_rate():

    """ER no viene de HikerAPI. Si algún día lo emite, el merge tiene que enterarse."""

    from discovery.tools.hikerapi\_client import HikerAPIClient

    out \= HikerAPIClient().\_normalize\_user({"username": "x"})

    assert "engagement\_rate" not in out, (

        "El normalizador ahora emite engagement\_rate: revisar el merge en worker.py:1244 "

        "y el cálculo de ER en worker.py:1438 antes de consumirlo."

    )

---

## 8\. Orden de merge

| Paso | Qué | Bloquea a |
| :---- | :---- | :---- |
| 1 | `_coerce_former_usernames` \+ tests de coerción | Encender `HIKERAPI_INCLUDE_ABOUT` |
| 2 | Consumidor `worker.py:1513-1519` (None-safe \+ paréntesis) | — |
| 3 | Eliminar valores fabricados (B2/B3) \+ `test_no_fabricated_metrics` | Confiar en cualquier shortlist de TikTok |
| 4 | Logging estructurado de merge \+ fraude | Diagnosticar el próximo run |
| 5 | **Recién ahí:** encender `HIKERAPI_INCLUDE_ABOUT=true` en Railway | — |
| — | `search_followers_of` / `web_profile_info` | Hito aparte, no este patch |

---

## 9\. Bloqueantes abiertos

**\#1 — `HIKERAPI_INCLUDE_ABOUT` en Railway.** Determina si B1 es latente (P1) o activo (P0 con auditoría de histórico). Pregunta directa a Ungar/Cris.

**\#2 — A-5, séptima iteración sin respuesta.** `worker.py:54`

TIER\_MIN\_FOLLOWERS \= 5\_000

Sigo sin saber si es un **filtro duro** (descarta todo perfil bajo 5K) o un **piso de bucketing de tier**. La diferencia no es académica: la metodología LWFA sostiene que los nanos aportan **80-85% de las views de campaña**, y buena parte del pool nano venezolano vive entre 1K y 5K seguidores. Si es filtro duro, LENS está ciego justo donde está el volumen — y ninguna de las correcciones de este documento lo arregla, porque el perfil nunca entra al funnel.

Es la única pregunta de este hilo cuya respuesta puede invalidar la premisa del producto. Necesito que alguien la conteste antes de la próxima iteración.

---

## 10\. Recomendación

**Operativa (para mañana):** merge de los pasos 1-4 en un solo PR. Son \~60 líneas, tres archivos, cuatro tests nuevos. No toques los flags de env hasta que ese PR esté en `main`.

**Estratégica:** el patrón que se repite hace siete iteraciones no es "camelCase vs snake\_case" — es **valores fabricados que se hacen pasar por medición**. `or 0`, `, 50`, `0.05`, `"VE"`. Cada uno pasa desapercibido porque produce un número plausible. El test `test_no_fabricated_metrics.py` de §7 es la primera defensa automatizada contra eso; propongo extenderlo a `hikerapi_client.py` y a `discovery.py` en el próximo ciclo, hasta que la regla NULL≠0 esté cubierta por CI y no por revisión manual.

**Alerta priorizada (hoy):** B2 — el default `"VE"` en el path TikTok. Si hay shortlists de TikTok ya entregadas a cliente desde este código, hay que revisarlas manualmente antes de que lo haga el cliente.

---

**Nota de método:** todo lo afirmado en este documento sale de leer el código en `a67ad72`. Lo que no pude verificar — la forma real del payload de HikerAPI, el valor de las env vars en Railway — está marcado como bloqueante, no rellenado con supuestos. No puedo hacer commit ni push; los diffs van para que Ungar los aplique.

---

Documento generado por La Web Figital Agency · 04-09-26 · Uso interno  
