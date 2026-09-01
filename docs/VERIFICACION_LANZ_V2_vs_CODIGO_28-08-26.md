# VERIFICACIÓN — AUDITORÍA v2 CONTRA EL CÓDIGO REAL

## LENS Discovery · Estado en `ce148e1`

> **Repositorio:** `github.com/ungardev/lawebcore` **Commit verificado:** `ce148e1` (28-08-26 23:47) — HEAD **Documento verificado:** `Auditoria_Lanz_v2_2026-08-27.md` (audita `1bdacc3`) **Método:** lectura directa del árbol vía API de GitHub. Solo lectura, ningún archivo modificado **Fuente de verdad:** el código. Donde un documento contradice al código, prevalece el código **Fecha:** 28-08-26 **Dirección técnica:** Claude Fable 5 · Full Stack Engineer Senior

---

## RESUMEN EJECUTIVO

| Punto | Veredicto |
| :---- | :---- |
| La auditoría v2 está desactualizada | ⚠️ **Sí** — audita `1bdacc3`, el repo va por `ce148e1`, cuatro commits después |
| BUG \#1 (typo `followers_count`) | ✅ **Corregido y verificado** |
| BUG \#2 (columnas de snapshot) | ✅ **Corregido y verificado** |
| FASE 2.1 y 2.3 marcadas pendientes | ✅ **Ya aplicadas** — la auditoría las reporta mal |
| **FASE 2.2 marcada como aplicada** | 🔴 **Falso — el invariante está cableado a `True`** |
| Procedencia del documento | ⚠️ Se titula «Auditoría Lanz v2.0» pero la firma MiniMax |

**Un solo cambio bloquea la corrida de validación: computar el invariante del embudo de verdad.**

---

## 1\. El repositorio se movió respecto de la auditoría

La auditoría v2 declara haber examinado el commit `1bdacc3`. El estado real del repositorio:

| Commit | Fecha | Mensaje |
| :---- | :---- | :---- |
| **`ce148e1`** | 28-08 23:47 | docs: Iteración 8 — Hito 36 completo \+ M3 A/B/C \+ 17 logger fixes |
| `035aafc` | 28-08 22:01 | fix(lens): add exc\_info=True to 17 logger.error calls in hot path |
| `65e998c` | 28-08 21:32 | **fix(lens): Lanz v2.0 FASE 0.4/2.1/2.2/2.4/2.5/3.1 — HikerAPI pipeline fixes** |
| `ae0789c` | 28-08 20:26 | fix(schema): sync schema.sql with migrations — 3 missing tables \+ 4 missing |
| `89caf71` | 28-08 17:17 | feat(web): add discovery\_mode selector \+ error detail visible \+ docs pricing |

**El commit `65e998c` declara haber aplicado seis de las acciones del plan de la propia auditoría.** Por lo tanto el plan de 5 fases de ese documento no puede ejecutarse tal cual: parte del trabajo ya está hecho y una parte está mal reportada.

---

## 2\. Verificación punto por punto en `ce148e1`

| Ítem | Lo que dice la auditoría v2 | Lo que dice el código |
| :---- | :---- | :---- |
| **BUG \#1** · typo `followers_count` en `worker.py:1298` | Corregido en `1bdacc3` | ✅ **Confirmado** — 0 ocurrencias de `followers_count` en todo el archivo |
| **BUG \#2** · columnas de `metrics_snapshot` | Corregido en `1bdacc3` | ✅ **Confirmado** — `discovery.py:973` usa `followers`, `:976` usa `raw_payload` |
| **FASE 2.1** · llamar a `determine_final_status()` | Pendiente · «dead code, nunca llamada» | ✅ **Ya aplicado** — `worker.py:1816` la invoca |
| **FASE 2.3** · flag `budget_aborted` | «No existe» | ✅ **Ya existe** — `worker.py:314, 1185, 1965, 2008` |
| **FASE 2.2** · invariante del embudo | Marcado aplicado en `65e998c` | 🔴 **Falso** — ver §3 |
| **FASE 2.6** · `FunnelTracker` | Pendiente | ❌ Sigue muerto — `worker.py:291`, `# noqa: F841` |
| Cadenas `or 0` en `worker.py` | 21 | **16** — bajando, no cerrado |
| Referencias camelCase en `worker.py` | «6/7 patrones presentes» | **55 referencias** — casi intacto |
| `except Exception` en `worker.py` | 27 | **29** — subió, probablemente por los 17 logger fixes de `035aafc` |
| `determine_final_status` invocaciones | 0 (dead code) | **1** — línea 1816 |

### Detalle de BUG \#2 — corregido con más alcance del reportado

discovery.py:968   table="influencer\_metrics\_snapshot",

discovery.py:970       "influencer\_id": influencer\_id,

discovery.py:971       "social\_account\_id": social\_account\_id,

discovery.py:972       "snapshot\_date": datetime.now(UTC).date(),

discovery.py:973       "followers": follower\_count,

discovery.py:974       "engagement\_rate": candidate.get("engagement\_rate"),

discovery.py:975       "avg\_likes": candidate.get("avg\_likes"),

discovery.py:976       "raw\_payload": candidate.get("raw\_payload", {}),

discovery.py:978   on\_conflict=\["influencer\_id", "social\_account\_id", "snapshot\_date"\],

Además de corregir los nombres de columna, se incorporó `social_account_id` (971) y el `on_conflict` sobre la tripleta (978). Eso cierra por completo los GAP \#5 y \#6 documentados en la verificación del 25-08.

---

## 3\. HALLAZGO CRÍTICO — el invariante del embudo está cableado

### Evidencia

worker.py:1816   final\_status \= determine\_final\_status(

worker.py:1818       funnel\_invariant\_ok=True,        ← constante literal

worker.py:1820       budget\_aborted=budget\_aborted,

worker.py:291    funnel \= FunnelTracker()  \# noqa: F841

### Dictamen

`funcional_invariant_ok` se pasa como `True` literal. **El invariante del embudo nunca se computa.**

Como `determine_final_status()` solo devuelve `INCONSISTENT` cuando ese parámetro es falso, **el estado `INCONSISTENT` es inalcanzable por construcción**. Ninguna corrida puede terminar en ese estado, ocurra lo que ocurra con el embudo.

El invariante es la pieza central del Hito 30: la propiedad que hace al sistema autoauditable y que iba a delatar a cualquier filtro nuevo que dejara perfiles sin registrar. **Está desactivada desde adentro.**

Y es exactamente el patrón que el informe original de Lanz identificó como causa raíz de todo el arco de dos meses — *«ante un error, producir un valor plausible y continuar»*. Aquí se aplicó al mecanismo diseñado para detectar ese mismo patrón: **el detector de fallos silenciosos fue neutralizado con un fallo silencioso.**

El agravante de proceso: el commit `65e998c` lista la acción 2.2 entre lo aplicado. El código dice otra cosa. Un plan de fases donde una acción se marca cumplida sin estarlo reproduce el problema de instrumentación que el proyecto viene arrastrando, ahora en la capa de gestión en vez de en la de código.

### FIX — `worker.py:1816-1821`

        \# El invariante se computa, no se afirma. Si la identidad no se cumple,

        \# hay un camino de salida de perfiles que nadie registró.

        funnel\_ok \= (len(step1\_handles) \- len(profiles)) \== ledger.total()

        final\_status \= determine\_final\_status(

            total\_candidates=total,

            step3\_degraded=step3\_degraded,

            funnel\_invariant\_ok=funnel\_ok,

            budget\_aborted=budget\_aborted,

        )

**Sobre `FunnelTracker`:** con la instancia ya creada en la línea 291 y descartada con un `# noqa: F841`, lo correcto es usarla para llevar los conteos por etapa en vez de calcular la identidad con sets locales. Eso cierra FASE 2.2 y FASE 2.6 en el mismo cambio y deja el conteo en un solo lugar.

**Ajustar los nombres de variable a los reales del archivo antes de aplicar** — `step1_handles`, `profiles` y `ledger` son los identificadores que aparecen en el contexto, pero conviene confirmarlos en el punto exacto de inserción.

**Prueba:**

\# apps/api/tests/test\_funnel\_invariant.py

async def test\_unregistered\_drop\_marks\_run\_inconsistent():

    """Si un perfil sale del pipeline sin pasar por drop\_profile(),

    la identidad del embudo no cuadra y la corrida debe quedar INCONSISTENT."""

**Riesgo de regresión:** Bajo · **Prioridad:** 🔴 Bloqueante de la corrida de validación

---

## 4\. Lo que la auditoría v2 sí aportó

Conviene decirlo con la misma claridad que las objeciones. Encontró **dos bugs críticos reales** que nadie había detectado y que efectivamente rompían el pipeline en producción:

- **BUG \#1** — el typo `followers_count` frente a `follower_count`. Es la clase de defecto que ninguna auditoría estática de alto nivel encuentra y que requiere leer la línea. Con él, todo perfil enriquecido caía como `MISSING_FOLLOWER_FIELD` y el mensaje al usuario culpaba al proveedor por un dato que sí había llegado.  
- **BUG \#2** — los nombres de columna inválidos en el UPSERT de snapshot. Rompía el guardado de candidatos en cada click.

Ambos son consecuencia directa de los fixes del Hito 35, y ambos ilustran la misma lección que este proyecto lleva tres iteraciones aprendiendo: **un contrato de datos tiene un productor y varios consumidores, y hay que recorrerlos todos en el mismo cambio.**

---

## 5\. Nota de procedencia

El documento se titula **«Auditoría Lanz v2.0»** pero en su encabezado dice **«De: MiniMax M2.7/M3»**. Santiago Lanz no la escribió; es una refundición de su informe v1.2 más hallazgos nuevos de otro autor.

La distinción no es formal. El informe original de Lanz pesaba porque verificó línea por línea contra el código y acertó en las doce referencias comprobadas. Esta refundición encontró dos bugs reales, pero también marca como aplicada una acción que no lo está y reporta como pendientes dos que sí se hicieron.

**Recomendación:** retitularla como *«Refundición del Informe Lanz v1.2 \+ hallazgos post-Hito 35 · MiniMax · 27-08-26»*. Si en dos semanas alguien discute un hallazgo, tiene que saber a quién preguntarle.

---

## 6\. ORDEN DE APLICACIÓN

| \# | Acción | Archivo | Riesgo | Costo |
| :---- | :---- | :---- | :---- | :---- |
| 1 | **Computar el invariante del embudo** (FASE 2.2 real) | `worker.py:1816-1821` | Bajo | $0 |
| 2 | Usar `FunnelTracker` o eliminarlo (FASE 2.6) | `worker.py:291` | Bajo | $0 |
| 3 | Corregir el registro de FASE 2.2 en el plan y en el índice | docs | — | $0 |
| 4 | Retitular la auditoría v2 con su autoría real | docs | — | $0 |
| — | **Corrida de validación** | — | — | **\~$1,14** |

Los pendientes de deuda técnica de la auditoría v2 —las 16 cadenas `or 0`, las 55 referencias camelCase, los 29 `except Exception`— siguen vigentes y **no bloquean la corrida**. Se atienden después, con datos reales de una corrida instrumentada.

---

## 7\. CRITERIO DE ÉXITO DE LA CORRIDA

\-- 1\. El estado terminal se escribió y es coherente

SELECT id, status, total\_candidates, actual\_cost\_usd

FROM discovery\_runs ORDER BY created\_at DESC LIMIT 1;

\-- 'delivered' o 'empty' → el acople funciona

\-- 'running'              → algo del acople sigue roto

\-- 'inconsistent'         → el invariante YA FUNCIONA y detectó una fuga

\-- 2\. El libro de descartes tiene más de una causa

SELECT reason\_code, (payload-\>\>'count')::int AS n

FROM discovery\_run\_events

WHERE run\_id \= :run\_id AND event \= 'profile.dropped'

ORDER BY 2 DESC;

\-- Si MISSING\_FOLLOWER\_FIELD sigue cerca del 100%, el BUG \#1 no era la causa única

**Nota sobre la lectura de `inconsistent`:** una vez computado el invariante de verdad, que una corrida termine en ese estado **no es un fracaso — es el instrumento funcionando**. Significa que hay un camino de salida de perfiles sin registrar, y el sistema lo dijo en voz alta en vez de entregar un cero sin explicación. Es exactamente lo que el Hito 30 se propuso lograr.

---

## 8\. PENDIENTE ARRASTRADO — cuarta iteración sin respuesta

⚡ **A-5 · `TIER_MIN_FOLLOWERS = 5_000` en `worker.py:54`**

No aparece en los 23 hallazgos de la auditoría v2, ni en las 23 entradas del índice de auditorías, ni en el PLAN\_MAIN.

Si esa constante actúa como filtro duro y no como parámetro de reparto por tiers, el sistema excluye por diseño el tramo **NANO bajo (500–5K)**, que según la metodología propia de la agencia aporta entre el **80% y el 85% de las views** de una campaña.

De ser así, ni los ocho fixes del Hito 35, ni los tres del acople de frontend, ni los dos bugs críticos de esta auditoría cambian el resultado del producto: el motor seguiría sin poder encontrar el tipo de creador que sostiene las campañas de La Web, y la corrida de $1,14 mediría esa limitación en vez del pipeline.

**Se responde leyendo los usos de esa constante en `worker.py`. Cuesta cero dólares, cero riesgo, y sigue sin respuesta desde la primera auditoría del 19-08.**

---

*Verificación elaborada sobre el commit `ce148e1` del repositorio `lawebcore`. Todas las referencias son verificables en ese commit. Ningún archivo del repositorio fue modificado durante esta auditoría.*

*Documento generado por La Web Figital Agency · 28-08-26 · Uso interno*  
