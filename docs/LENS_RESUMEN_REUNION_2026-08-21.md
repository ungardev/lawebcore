# LENS — Resumen para la reunión

> **Commit revisado:** `4658e7e` · **Saldo HikerAPI:** $43.00 · **Hitos aplicados:** 1-28
> **Parche adjunto:** `hito29_hotfix.patch` — 1 archivo, compilado
> **Lo urgente está en la sección 1. Si sólo hay tiempo para una cosa, es esa.**

---

## 1. 🔴 HAY UNA REGRESIÓN QUE TUMBA TODOS LOS RUNS — Y ES MÍA

**Antes de gastar un dólar de los $43, hay que aplicar el hotfix adjunto.** Si se lanza un run ahora mismo, falla en el primer segundo.

### Qué pasó

Yo recomendé `extra="forbid"` en los schemas para cerrar la familia de bugs de "campo que se pierde en silencio". El equipo lo aplicó en el Hito 28 — correctamente, siguiendo mi indicación — **a los dos schemas**. Y ahí está el problema: no distinguí que esos dos schemas hacen cosas distintas.

```
discovery.py  →  DiscoverySearchRequest(...)         ← entrada de API
memory.py:222 →  brief_parsed = brief.model_dump()   ← incluye max_candidates
                          ↓ se guarda en Postgres
worker.py:324 →  BriefStructured(**brief_parsed)     ← extra="forbid"
                 ValidationError: max_candidates no permitido
```

`DiscoverySearchRequest` tiene `max_candidates`. `BriefStructured` **no lo tiene**. Con `forbid`, el worker revienta al deserializar, antes de la primera llamada HTTP.

### Alcance

`launch_discovery_run` se invoca desde **tres** endpoints (`discovery.py:315, 511, 567`) y su firma recibe `DiscoverySearchRequest`. Los tres caminos —Explorar, Analizar y el chat— guardan el mismo dump.

**Todos los runs fallan.** El producto está caído hasta aplicar el fix. Costo: $0 (falla antes de gastar), pero la demo de hoy no arrancaría.

### La lección, que es la parte útil

La regla que di era incompleta. La correcta:

> **`forbid` va en la frontera de entrada, `ignore` en la deserialización de datos persistidos.**

En la API, `forbid` atrapa typos del cliente y ahí gana. En un schema que lee JSON guardado, `forbid` convierte cualquier evolución del schema en una rotura de todas las filas históricas — y hay 48 runs guardados con campos que ya cambiaron.

El parche hace exactamente eso: `BriefStructured` pasa a `ignore` y gana el campo `max_candidates`; `DiscoverySearchRequest` conserva `forbid`, que es donde sirve.

### Cómo verificarlo en 30 segundos

```bash
psql $DATABASE_URL -c "SELECT brief_parsed ? 'max_candidates' FROM discovery_runs ORDER BY created_at DESC LIMIT 1;"
```

Si devuelve `t`, la regresión está confirmada.

---

## 2. LO QUE SÍ QUEDÓ BIEN EN EL HITO 28

Verificado en código:

| Fix | Estado |
|---|---|
| **A** — Pre-flight consciente del modo (`worker.py:415`) | ✅ Explorar $0.64, Analizar real, Auto $1.14 |
| **B** — DeepSeek omitido en Explorar (`worker.py:1646`) | ✅ El rationale honesto se preserva |
| **27** — `parent_run_id` en `DiscoverySearchRequest` | ✅ Analizar ya no repite el discovery |
| **27** — `platforms` con `default_factory` | ✅ |
| 17 tests nuevos | ✅ |

Los dos fixes que importaban están correctos. La regresión no viene de ellos, viene del tercer cambio.

---

## 3. SOBRE LAS 8 BRECHAS DE LA AUDITORÍA #14

El análisis está bien hecho: las ocho brechas son reales y están bien identificadas. **Pero recomiendo no empezar ninguna todavía**, y el motivo es de secuencia, no de calidad.

### El argumento

Las ocho mejoran **cómo se ordenan** los candidatos. Y hoy seguimos sin saber **cuántos candidatos produce el sistema**: 1 en 48 runs, y el flujo Explorar → Analizar nunca ha corrido con saldo.

Afinar el ranking de una lista cuyo tamaño desconoces es optimizar algo que aún no existe. Si el primer Explorar devuelve 3 handles, ninguna de las ocho brechas importa — el problema sería otro. Si devuelve 25 con buena bio, entonces sí, y además sabrás **cuáles** de las ocho hacen falta en vez de implementarlas todas.

### La excepción

**Brecha 4 — Tier enforcement (5K-50K)** merece revisarse antes, pero no para implementarla: para **quitarla**. Ese rango es el que dejaba fuera a todo el tier medio y alto. Antes de reforzarlo conviene decidir si sigue teniendo sentido para una campaña de Nestlé.

### Mi propuesta de secuencia

1. Hotfix (§1)
2. Un Explorar real → **medir cuántos handles útiles salen**
3. Un Analizar de 5 handles → medir cuántos enriquecen bien
4. **Con esos dos números**, elegir 2 o 3 de las 8 brechas — las que los datos señalen
5. El resto queda documentado como backlog, no como plan

Las 6.5 horas del roadmap H29-H35 rinden mucho más después del paso 3 que antes.

---

## 4. TRES COSAS QUE CONVIENE SABER ANTES DEL PRIMER RUN

**Explorar devuelve como máximo 25 candidatos, no 133.** El `rough_score_map` sale del prefiltro, que está limitado a `MAX_HANDLES_TO_ENRICH = 25`. No es un bug —25 es una lista razonable para revisar a mano— pero no hay que prometer "descubrimos 133 cuentas" y mostrar 25.

**`get_balance()` sigue sin probarse con saldo positivo.** Sólo se validó con $0. Ahora que hay $43, un `curl` de diez segundos lo cierra:

```bash
curl -s -H "x-access-key: $HIKERAPI_API_KEY" https://api.hikerapi.com/v1/account | jq
```

Si el campo del saldo no está entre `balance`, `balance_usd`, `credits_usd` o `amount`, el pre-flight se omite en silencio y volvemos al comportamiento anterior.

**El worker de ARQ ya se ha quedado dos veces con código viejo en memoria** tras un deploy de Railway. Conviene confirmar en los logs que recargó antes de dar por buena cualquier prueba.

---

## 5. PLAN PARA HOY

| # | Acción | Costo | Tiempo |
|---|---|---|---|
| 1 | Aplicar `hito29_hotfix.patch` | $0 | 2 min |
| 2 | Redeploy Railway + **verificar en logs que el worker recargó** | $0 | 5 min |
| 3 | Verificar el campo de saldo con `curl` | $0.02 | 2 min |
| 4 | **Run de Explorar con el brief real** | ~$0.64 | 3 min |
| 5 | Contar: ¿cuántos handles con bio no vacía? | $0 | 2 min |
| 6 | Analizar con 5 handles seleccionados | ~$0.10 | 3 min |
| 7 | Decidir las 8 brechas **con los números del paso 5** | $0 | — |

**Total: ~$0.76 de $43.** Quedan $42.24.

### El criterio de éxito, escrito antes de correr

**≥15 handles con bio no vacía, de los cuales el analista seleccionaría al menos 5.**

Con el tope de 25, eso significa que más de la mitad de lo mostrado debe ser útil. Conviene fijarlo ahora: sin un criterio escrito de antemano, cualquier resultado se puede racionalizar como progreso.

---

## 6. PARA CONTAR EN LA REUNIÓN

**Dónde estamos:** la infraestructura de control está terminada y es sólida —fusible de presupuesto, circuit breaker, contabilidad por run, pre-flight de saldo, modo replay—. El rediseño Explorar → Analizar está implementado y baja el costo por campaña de $1.28 a ~$0.74. Hay $43 de saldo y 28 hitos aplicados.

**Qué falta:** el sistema todavía no ha entregado su primera lista de candidatos validada. Hoy se puede saber, y cuesta $0.76.

**Qué pido:** aplicar el hotfix antes de cualquier prueba, y **no arrancar el roadmap de las 8 brechas hasta tener el número del paso 5**. Es la diferencia entre invertir 6.5 horas a ciegas o dirigidas.

**La observación de fondo**, y creo que es la más útil para la reunión: nueve auditorías, nueve bugs, y todos de la misma familia — cosas que fallan sin avisar. El de hoy lo introduje yo dando una regla a medias. Eso confirma el diagnóstico en vez de contradecirlo: **el problema no es la falta de cuidado, es que el sistema no avisa cuando algo va mal.** Por eso el paso que más rinde no es corregir bugs más rápido, sino el test end-to-end que los haga visibles antes de producción. Con `extra='forbid'` bien puesto y un test que ejecute Explorar → Analizar de punta a punta, esta regresión habría durado treinta segundos en vez de llegar al día de la demo.

---

*Verificación estática sobre `4658e7e`. El parche compila. No se ejecutó el pipeline ni se consumieron créditos. La cadena de la regresión (§1) es verificable con la consulta SQL indicada.*
