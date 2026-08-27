# VERIFICACIÓN DE ESTADO — LENS DISCOVERY

## Cierre de C-1 en frontend · Contradicciones del índice · Gap abierto

> **Repositorio:** `github.com/ungardev/lawebcore` **Commit verificado:** `1cbe613` (27-08-26 04:10) — HEAD **Método:** lectura directa del árbol y de la API de GitHub Actions. Solo lectura, ningún archivo modificado **Fuente de verdad:** el código y el estado real de CI. Donde un documento contradice al código, prevalece el código **Documento que corrige:** `PROMPT_CLAUDE_CODE_ANALYSIS.md` (índice de auditorías, actualizado 27-08-26) **Fecha:** 27-08-26 **Dirección técnica:** Claude Fable 5 · Full Stack Engineer Senior

---

## RESUMEN EJECUTIVO

| Punto | Veredicto |
| :---- | :---- |
| CI verde | ✅ **Confirmado empíricamente** — el índice lo dice bien en el encabezado |
| «CI lint bloquea deploy» en Bugs Abiertos | ❌ **Desactualizado** — contradice el encabezado del mismo documento |
| Frontend C-1 completo | ⚠️ **Casi** — 2 de 3 archivos completos, 1 incompleto |
| `LensSearchPage.tsx` | 🔴 **Faltan `inconsistent` y `aborted_budget`** |
| Hallazgo 2 del índice (crítica a Fable 5\) | ✅ **Justo. Asumido** — ver §4 |

**Una sola línea de código bloquea la corrida de validación.**

---

## 1\. Estado real de CI — verificado, no asumido

Consulta a la API de GitHub Actions sobre `ungardev/lawebcore`:

| Commit | Workflow | Estado | Conclusión | Fecha |
| :---- | :---- | :---- | :---- | :---- |
| `1cbe613` | CI | completed | ✅ **success** | 27-08 04:10 |
| `e5e17b6` | CI | completed | ✅ **success** | 27-08 01:46 |
| `9c67aa2` | CI | completed | ❌ failure | 27-08 01:43 |
| `35bd72e` | CI | completed | ❌ failure | 27-08 01:41 |
| `2566a82` | CI | completed | ❌ failure | 27-08 01:37 |
| `233ab7f` | CI | completed | ❌ failure | 27-08 01:33 |

**CI está verde desde `e5e17b6`.** Cuatro intentos fallaron y el quinto pasó. El bloqueo de despliegue está resuelto.

### Contradicción interna del índice

El documento `PROMPT_CLAUDE_CODE_ANALYSIS.md` afirma tres cosas incompatibles entre sí:

| Sección | Qué dice | ¿Correcto? |
| :---- | :---- | :---- |
| Encabezado (línea 5\) | *«CI verde ✅ · Railway desplegado con C-0/C-1/C-2 ✅»* | ✅ Sí |
| Bugs Abiertos (línea 137\) | *«CI lint bloquea deploy — 197 errores — 🔴 CRÍTICA — Railway no puede desplegar commits nuevos»* | ❌ Obsoleto |
| Bugs Abiertos (línea 138\) | *«Issue C-1: Frontend TypeScript — 🔴 CRÍTICA — código aplicado en `29d7ba6` pero frontend no desplegado»* | ❌ Obsoleto en su mayor parte |
| Pendiente (línea 217\) | *«\[ \] Railway deploy del código con C-1/C-2 (bloqueado por lint CI)»* | ❌ Obsoleto |

El encabezado se actualizó y el cuerpo no. **Riesgo concreto:** alguien que lea la sección de Bugs Abiertos va a creer que el despliegue sigue bloqueado y va a repetir trabajo ya hecho, o a postergar la corrida de validación sin motivo.

**Acción recomendada:** limpiar las líneas 137, 138 y 217 del índice antes de que se use para tomar decisiones.

---

## 2\. Frontend C-1 — verificación archivo por archivo

El Hallazgo 2 del índice identifica tres archivos de frontend que necesitaban los nuevos estados. Verificados los tres en `1cbe613`:

| Archivo | Estados presentes | Veredicto |
| :---- | :---- | :---- |
| `apps/web/src/features/lens/types/discovery.ts` | pending, running, completed, failed, cancelled, partial, explored, queued, delivered, degraded, empty, inconsistent, aborted\_budget — **13 de 13** | ✅ **Completo** |
| `apps/web/src/features/lens/pages/LensRunsListPage.tsx` | los mismos **13 de 13** en `STATUS_CONFIG` | ✅ **Completo** |
| `apps/web/src/features/lens/pages/LensSearchPage.tsx` | explored, completed, partial, delivered, degraded, failed, empty — **7 de 13** | 🔴 **Incompleto** |

El commit `801d7a0` («fix(lint): resolve 75 ruff W292/I001 violations \+ frontend C-1 TypeScript») cubrió dos de los tres archivos. El tercero quedó a medias.

---

## 3\. EL GAP ABIERTO — `LensSearchPage.tsx`

### Qué falta

`LensSearchPage.tsx` no contempla dos estados terminales: **`inconsistent` y `aborted_budget`.**

### Por qué importa

Si una corrida termina en cualquiera de esos dos, el `hasResults` no la reconoce y **el polling puede quedar girando sin cerrar nunca.** El usuario ve una búsqueda «en progreso» que ya terminó.

Es el mismo defecto que C-1 original, un nivel más abajo: **un enumerado ampliado en el productor y no en todos los consumidores.** Y hay una ironía operativa que conviene notar: el estado sin cobertura es precisamente `inconsistent`, que el Hito 30 inventó para avisar que el embudo no cuadra. El mecanismo diseñado para detectar fallos silenciosos falla en silencio.

### El fix — y por qué son dos listas, no una

**Archivo destino:** `apps/web/src/features/lens/pages/LensSearchPage.tsx`, donde se define `hasResults` (\~línea 78\)

// Terminal ≠ con resultados. Son dos preguntas distintas.

const TERMINAL\_STATUSES \= \[

  'delivered', 'degraded', 'empty', 'inconsistent', 'aborted\_budget',

  'failed', 'completed', 'partial', 'explored', 'cancelled',

\] as const;

const RESULT\_STATUSES \= \[

  'delivered', 'degraded', 'explored', 'completed', 'partial',

\] as const;

const isTerminal  \= TERMINAL\_STATUSES.includes(run?.status as never);

const hasResults  \= RESULT\_STATUSES.includes(run?.status as never);

**La distinción es la parte importante del fix.** `inconsistent` y `aborted_budget` **son terminales pero no tienen resultados**:

- Meterlos en `hasResults` haría que la vista intente renderizar candidatos que no existen  
- Dejarlos fuera de `isTerminal` deja el polling colgado indefinidamente

Una sola lista no puede cubrir ambos casos. Es el mismo error de fondo que produjo C-1: colapsar dos conceptos en una estructura.

**Commit sugerido:** `fix(lens): cover inconsistent/aborted_budget in LensSearchPage polling` **Riesgo de regresión:** Bajo **Prioridad:** 🔴 Bloqueante de la corrida de validación

---

## 4\. Sobre el Hallazgo 2 del índice — crítica asumida

El índice señala:

> *«Fable 5 No Cubrió Todo el Frontend para C-1. El análisis de Fable 5 (C-1) solo tocó `schemas.py`. Faltaron 3 archivos de frontend.»*

**La crítica es justa y la asumo.**

**Contexto, no excusa:** el prompt de la Iteración 2 nombraba exactamente dos archivos como «archivo a modificar» — `packages/discovery/discovery/schemas.py` y `apps/web/src/types/index.ts` — y el análisis se ciñó a ellos. Pero debí haber barrido todos los consumidores del enumerado en vez de solo los señalados. Es literalmente el patrón que llevo tres iteraciones documentando: **un contrato tiene un productor y varios consumidores, y hay que recorrerlos todos.**

### La consecuencia práctica — la prueba que propuse no habría detectado esto

La prueba de paridad que dejé en el documento anterior compara Python contra Python:

\# apps/api/tests/test\_status\_enum\_parity.py

worker\_states \= {s.value for s in RunStatus}

api\_states \= {s.value for s in DiscoveryRunStatus}

assert worker\_states \<= api\_states

**No cubre el frontend, que es TypeScript.** Hace falta una segunda guardia del lado del cliente.

### Guardia adicional recomendada

**Paso 1 — una sola fuente de verdad en el frontend.** En `apps/web/src/features/lens/types/discovery.ts`, exportar la lista como array y derivar el tipo de ahí:

export const DISCOVERY\_RUN\_STATUSES \= \[

  'pending', 'running', 'completed', 'failed', 'cancelled', 'partial', 'explored',

  'queued', 'delivered', 'degraded', 'empty', 'inconsistent', 'aborted\_budget',

\] as const;

export type DiscoveryRunStatus \= typeof DISCOVERY\_RUN\_STATUSES\[number\];

Así la lista existe una vez y el tipo se deriva, en vez de mantener dos copias que se desincronizan.

**Paso 2 — prueba de cobertura:**

// apps/web/src/features/lens/\_\_tests\_\_/status-parity.test.ts

import { DISCOVERY\_RUN\_STATUSES } from '../types/discovery';

import { STATUS\_CONFIG } from '../pages/LensRunsListPage';

import { TERMINAL\_STATUSES } from '../pages/LensSearchPage';

test('todo status conocido tiene entrada en STATUS\_CONFIG', () \=\> {

  const faltantes \= DISCOVERY\_RUN\_STATUSES.filter(s \=\> \!(s in STATUS\_CONFIG));

  expect(faltantes).toEqual(\[\]);

});

test('todo status terminal del backend está cubierto en el polling', () \=\> {

  const terminales \= DISCOVERY\_RUN\_STATUSES.filter(s \=\> s \!== 'pending' && s \!== 'running' && s \!== 'queued');

  const faltantes \= terminales.filter(s \=\> \!TERMINAL\_STATUSES.includes(s as never));

  expect(faltantes).toEqual(\[\]);

});

Requiere exportar `STATUS_CONFIG` y `TERMINAL_STATUSES` desde sus módulos. Con esas dos pruebas, agregar un estado al backend sin cubrirlo en el frontend rompe el build antes de llegar a producción.

---

## 5\. RECOMENDACIÓN

### Antes de la corrida de validación

| \# | Acción | Costo | Bloqueante |
| :---- | :---- | :---- | :---- |
| 1 | Fix de `LensSearchPage.tsx` — dos listas de estados | $0 | 🔴 Sí |
| 2 | Deploy en Vercel y confirmación | $0 | 🔴 Sí |
| 3 | Limpiar líneas 137, 138 y 217 del índice de auditorías | $0 | No, pero evita retrabajo |
| 4 | Guardias de paridad TypeScript (§4) | $0 | No — recomendado para no repetir el ciclo |
| — | **Corrida de validación** | **\~$1,14** | — |

**Con el estado actual, una corrida que termine en `inconsistent` te dejaría sin señal y sin saber por qué** — que es exactamente el escenario que el Hito 30 existe para eliminar.

### Criterio de éxito de la corrida — sin cambios respecto al documento anterior

\-- 1\. El estado terminal se escribió

SELECT id, status, total\_candidates, actual\_cost\_usd

FROM discovery\_runs ORDER BY created\_at DESC LIMIT 1;

\-- Debe devolver 'delivered' o 'empty'. Si dice 'running', algo del acople falló.

\-- 2\. El libro de descartes tiene más de una causa

SELECT reason\_code, (payload-\>\>'count')::int AS n

FROM discovery\_run\_events

WHERE run\_id \= :run\_id AND event \= 'profile.dropped'

ORDER BY 2 DESC;

\-- Si MISSING\_FOLLOWER\_FIELD sigue en \~100%, el problema no era el merge.

---

## 6\. PENDIENTE ARRASTRADO — cuarta iteración sin respuesta

⚡ **A-5 · `TIER_MIN_FOLLOWERS = 5_000` en `worker.py:54`**

No aparece en ninguna de las 23 entradas del índice de auditorías. Tampoco en el PLAN\_MAIN ni en la lista de Bugs Abiertos.

Si esa constante actúa como filtro duro y no como parámetro de reparto por tiers, el sistema excluye por diseño el tramo **NANO bajo (500–5K)**, que según la metodología propia de la agencia aporta entre el **80% y el 85% de las views** de una campaña.

De ser así, **ninguno de los fixes aplicados hasta hoy cambia el resultado del producto**, y la corrida de $1,14 que está por ejecutarse mediría un motor estructuralmente incapaz de encontrar el tipo de creador que sostiene las campañas de La Web.

**Se responde leyendo los usos de esa constante en `worker.py`. Cuesta cero dólares, cero riesgo, y sigue sin respuesta desde la primera auditoría.**

---

*Verificación elaborada sobre el commit `1cbe613` del repositorio `lawebcore` y sobre la API de GitHub Actions. Todas las referencias son verificables en ese commit. Ningún archivo del repositorio fue modificado durante esta auditoría.*

*Documento generado por La Web Figital Agency · 27-08-26 · Uso interno*  
