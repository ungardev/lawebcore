**INFORME DE ALINEACIÓN TÉCNICA — LENS DISCOVERY**

**Para:** Ignacio Chacón — líder del área P.I.A.R., La Web Figital Agency

**Copia:** Ungar Villamizar — desarrollo del módulo LENS

**De:** Santiago Lanz — asesoría técnica independiente

**Fecha:** 24 de agosto de 2026 · v1.2

**Alcance:** módulo LENS Discovery del monorepo lawebcore, revisado sobre el código fuente en el commit 81db353 del 21 de agosto de 2026\. Todos los números de línea de este informe corresponden a ese commit.

# **En una página**

48 ejecuciones, 1 candidato producido. La causa no fue el saldo: cuando el proveedor devuelve un perfil sin el número de seguidores, el sistema lo anota como cero seguidores y lo descarta, sin registrar en ninguna parte que lo descartó. Ese mecanismo lo encontró el propio equipo el 18 de agosto. Lo que agrego es que sigue en pie, y que el instrumento con el que se mide el resultado no puede separar «no traje el dato» de «el enriquecimiento falló».

Debajo hay una decisión repetida en todo el código: ante un error, producir un valor plausible y continuar. Por eso cada arreglo de los últimos meses se validó contra un instrumento que informa éxito en los dos casos.

Segundo: cada perfil se paga, se usa una vez y vence a las 24 horas. La base de datos maestra existe desde el arranque del proyecto y sí recibe candidatos, pero por un camino que guarda el nombre y la bio y deja afuera las métricas que se compraron.

Tercero, y es el techo de la calidad: el sistema arma un plan de búsqueda de 30 hashtags y 20 palabras clave, y ejecuta tres y tres. El resto no se consulta nunca, y no es por presupuesto — quedan unas 88 llamadas sin usar por corrida dentro del tope ya configurado. La metadata de la corrida, mientras tanto, registra 30 y 20\. Ningún ajuste de puntaje rescata a un influencer que nunca entró a la lista.

Cuarto, y es lo que hace barata la corrección: las cuatro prácticas que le faltan a LENS ya están escritas y andando en este mismo repositorio, para el otro subsistema del producto. No falta capacidad ni falta trabajo: falta que el estándar valga para todo el producto.

La única decisión que no es técnica está en la §7, punto 5\.

# **1\. Qué es este informe y cómo se hizo**

Revisé el código del repositorio lawebcore — no la documentación del proyecto, sino el código que corre. Cada afirmación de este informe cita el archivo y la línea donde se verifica. Donde no pude verificar algo, lo digo.

Este informe no es una lista de bugs. Los bugs se van arreglando uno por uno y no cambian el resultado. Lo que documento acá son **tres decisiones de arquitectura** que hacen que el sistema no pueda decir la verdad sobre sí mismo, y una observación final que es la más importante de todas: **las prácticas que le faltan a LENS ya existen, escritas y adoptadas, en este mismo repositorio.**

El problema no es de capacidad del equipo. Es de estándar no aplicado. Eso se corrige declarando un estándar, no escribiendo más código.

**Lo que no cubre este informe:** no ejecuté el sistema ni tuve acceso a producción, no revisé el frontend en profundidad, y no evalué el subsistema P.I.A.R./ISM más allá de lo necesario para las comparaciones de la §6.

# **2\. El resultado del negocio tiene una causa mecánica, y no es la que dice la documentación**

El historial del sistema es de 48 ejecuciones y 1 candidato producido. Ese censo no es mío: es el de la novena auditoría interna del equipo, con datos de producción al 19 de agosto de 2026 (docs/LENS\_AUDIT9\_2026-08-19.md:52-54), y no tuve acceso a la base para reverificarlo. Esa misma auditoría atribuye el resultado al agotamiento de saldo durante el enriquecimiento de perfiles. Antes de seguir hay que decir algo: la séptima auditoría, tres días anterior (docs/LENS\_AUDIT7\_2026-08-18.md §1), ya había llegado más lejos. Nombra la cadena completa —ninguna fuente de búsqueda devuelve seguidores, los perfiles llegan con followers \= 0, mueren en el primer filtro del scoring—, cita las mismas líneas de código que documento abajo y refuta el diagnóstico anterior con el log del propio run. Ese trabajo está hecho y está bien hecho. **Lo que sigue no lo contradice: lo extiende en un punto que ese análisis no cubre.** El cero se leyó como consecuencia del 402\. También ocurre sin 402, y el sistema no tiene forma de distinguir los dos casos.

## **2.1 La cadena que descarta candidatos**

En apps/api/app/workers/worker.py:1280-1282, y el descarte en la línea 1346:

followers \= p.get("followersCount") or p.get("follower\_count") or 0   \# 1280  
if followers \== 0:                                                     \# 1281  
    untracked\_no\_followers \+= 1                                        \# 1282  
    if is\_explore\_mode:  
        ...                                                            \# se conserva con puntaje aproximado  
        continue  
    continue                                                           \# 1346 — se descarta

Un perfil sin número de seguidores se convierte en **cero seguidores**, y con cero seguidores el candidato se descarta: es el continue sin condición de la línea 1346\. El problema es que "no tengo el dato" y "tiene cero seguidores" son dos cosas distintas que acá se vuelven la misma, y una de ellas es un descarte silencioso.

Esto importa porque el enriquecimiento es hoy la única fuente de seguidores del pipeline. La tabla de endpoints de docs/LENS\_ASESORIA\_INGENIERO\_2026-08-20.md marca las búsquedas por palabra clave como perfil **completo**; la séptima auditoría del propio equipo lo midió al revés (docs/LENS\_AUDIT7\_2026-08-18.md:61-68: *«Instagram devuelve usuario reducido en búsquedas»*). Es una contradicción interna que conviene cerrar, y hasta que se cierre el efecto es el mismo: todo perfil que no pasó por enriquecimiento llega sin el campo. Ese perfil entra a la normalización, sale con cero, y se descarta — sin que el sistema registre en ningún lado que lo que faltó fue el dato y no el seguidor.

## **2.2 Por qué el campo se pierde: no hay un contrato de datos**

El normalizador \_normalize\_user() en packages/discovery/discovery/tools/hikerapi\_client.py:821 devuelve **las métricas y los indicadores de la cuenta dos veces, bajo dos convenciones de nombres a la vez**:

"follower\_count": follower\_count,   "followersCount": follower\_count,  
"following\_count": following\_count, "followsCount": following\_count,  
"posts\_count": media\_count,         "postsCount": media\_count,  
"is\_business": ...,                 "isBusinessAccount": ...,  
"is\_verified": ...,                 "verified": ...,

Un normalizador existe para que cada dato quede con **un solo nombre**. Este los deja con dos a la vez: el nombre que usaba el proveedor anterior (Apify) y el del actual (HikerAPI). El proveedor anterior está marcado como no operativo, pero su convención de nombres quedó fosilizada dentro del contrato de datos del camino en producción, y su cliente sigue en el repositorio con 869 líneas.

La consecuencia se ve aguas abajo: worker.py escribe ese par de claves junto, en el mismo diccionario, en **9 lugares** distintos, y menciona una u otra en **17 y 11 líneas** de código; cada lectura tiene que adivinar defensivamente con una cadena de or. Cada una de esas cadenas termina en or 0, y cada or 0 es otra oportunidad de convertir "no sé" en un número que el sistema toma por verdadero. Ese es el mecanismo por el que un perfil bueno pero incompleto termina contado como un perfil de cero seguidores y descartado sin dejar rastro.

## **2.3 El segundo mecanismo, que el propio equipo encontró después**

En worker.py:1287-1291, en un comentario del equipo:

*"\`upsert\_many\` deriva las columnas de \`records\[0\].keys()\`; claves como \`profile\` o \`rough\_score\` no son columnas de \`discovery\_candidates\` y hacían fallar el INSERT entero → 0 candidatos insertados SIEMPRE"*

Es decir: la capa de carga infiere las columnas de la base a partir de las claves del **primer registro del lote**. Un solo diccionario con una clave de más y el INSERT completo falla. El equipo lo detectó y lo corrigió, y quedó documentado en el código con esas palabras.

Conviene ubicarlo: el bloque donde vive ese comentario es el del modo Explorar, que existe desde el hito 24, así que no explica las 48 ejecuciones anteriores. Lo que muestra es otra cosa: el INSERT entero podía fallar y la ejecución terminaba igual, sin que nada lo dijera — el patrón de la §3 apareciendo en la capa de carga. Y deja el diagnóstico vigente cuando se preparó la documentación externa como **incompleto, no equivocado**: el 402 fue real y está verificado con curl en la novena auditoría (docs/LENS\_AUDIT9\_2026-08-19.md:168). Lo que faltaba es que el cero no necesita un 402 para producirse, y que el sistema no puede decir cuál de las dos cosas pasó.

## **2.4 Por qué el diagnóstico apuntó al lugar equivocado**

Esta es la parte que conviene entender, porque explica por qué el diagnóstico apuntó al saldo y no al dato faltante.

En worker.py:165, el mensaje que el sistema le muestra al usuario cuando no encuentra a nadie:

if step3\_degraded and reasons.get("untracked\_no\_followers", 0\) \>= total\_profiles \* 0.8:  
    return "⚠️ ... el enriquecimiento falló y sin ese paso no tengo seguidores ..."

Ese contador tiene **un solo lugar donde se incrementa** —la línea 1282, la misma del descarte— y ahí se incrementa por una única condición: que followers haya quedado en cero. No sabe *por qué* quedó en cero. Se incrementa igual si el enriquecimiento falló que si el perfil nunca trajo el campo porque vino de una fuente reducida. El mensaje exige además que step3\_degraded esté en True, así que no se dispara por perfiles reducidos solos; pero cuando el enriquecimiento se degrada aunque sea en parte, le atribuye a esa degradación el 80% de ceros que la condición mide, sin poder decir cuántos de esos ceros venían de fuentes que nunca traen el dato.

Pero el mensaje solo nombra la primera causa y sugiere recargar saldo. El propio docstring de la función, en la línea 163, ancla la explicación en un caso concreto de saldo: *"en el run 0c44ea23 la causa fue que el enrichment falló con 402"*.

**El instrumento no puede separar las dos causas, y el mensaje nombra una sola.** No es un error de criterio: es un error de instrumentación, y sobrevivió a la corrección que el equipo ya le hizo al mensaje — el hito 23 lo derivó del contador que más perfiles descartó, precisamente porque el texto fijo anterior confundía el diagnóstico (worker.py:1788-1791). Mientras un solo contador cubra dos causas distintas, cada ejecución que termine en cero va a admitir dos lecturas y el mensaje va a elegir siempre la misma. El diagnóstico se corrigió a mano, una vez; el instrumento que lo produjo sigue igual.

# **3\. El patrón de fondo: el sistema no distingue funcionar de degradarse en silencio**

Esta es la primera de las tres decisiones de arquitectura, y la que condiciona a las otras dos.

Los hallazgos de la §2 no son casos aislados. Son instancias de una misma decisión repetida en todo el código: **ante un error, producir un valor plausible y continuar.** Tampoco es una lectura mía: está escrito en la documentación del propio equipo (docs/ARQUITECTURA\_LENS.md:1800) — *«Nueve auditorías, nueve bugs, todos de la misma familia — cosas que fallan sin avisar. \[…\] el problema no es la falta de cuidado, es que el sistema no avisa cuando algo va mal.»* El diagnóstico ya está hecho y es correcto. Lo que aporto es la medida de cuán extendido está y por qué es lo primero que hay que corregir.

La medición sobre el repositorio, recorriendo el árbol sintáctico de cada archivo .py y excluyendo dependencias de terceros: **179 manejadores de excepción amplios** —except Exception, except BaseException o except a secas—. No doy un porcentaje de cuántos descartan el error, porque clasificarlo automáticamente no es fiable: en un fusible de gasto, un return False ante el error es lo correcto y un return True es lo contrario, y ningún conteo distingue eso solo.

Lo que importa no es el número: es **dónde** están. Cuatro casos, cada uno leído y verificado a mano:

| Dónde | Qué hace ante el error | Consecuencia |
| :---- | :---- | :---- |
| packages/shared-ai/shared\_ai/embeddings.py:46-58 | Ante dos fallos anidados, guarda un vector de 384 ceros | Es el indexador de documentos, fuera de LENS (apps/api/app/ai/indexer.py:116), y vale como muestra del patrón. El registro queda en la base como si fuera bueno, y el umbral de similitud de rag\_engine.py:91 lo deja afuera siempre: el fragmento existe y no se puede encontrar nunca. Una ausencia anotada como presencia. |
| packages/discovery/discovery/candidate\_analyzer.py:348-382 | Sustituye el análisis de IA por \_fallback\_scores() | Los tres puntajes numéricos quedan iguales a los de un candidato analizado por el modelo. La marca existe y es un hueco: \_fallback\_scores devuelve ai\_summary: None (línea 248\) y ai\_rationale solo se escribe en el camino de IA (línea 380, columna de la migración 00000000000099). Queda en la base y no viaja con el puntaje. |
| worker.py:1280 y otros 32 lugares del mismo archivo —33 cadenas or que terminan en la constante 0— | Convierte campo ausente en 0 | Descrito en la §2.1. |
| apps/api/app/core/budget\_fuse.py:213-222 | can\_make\_call() documenta *"Returns False if this run has hit MAX\_CALLS\_PER\_RUN"* y ante cualquier error **devuelve \`True\`** | Hoy es inerte: no la llama nadie. Su único invocador es check\_run\_limit() (línea 262), que tampoco se invoca desde ningún lado — la propia AUDIT2 del equipo lo anotó el 14 de agosto (docs/LENS\_AUDIT2\_2026-08-14.md:130). El limitador que sí corre es reserve\_and\_record(), dentro de hikerapi\_client.\_get():241, y falla CERRADO. Queda el criterio contrario escrito en una función muerta y todavía documentada como si mandara: se borra, no se arregla. En las líneas 147-149 del mismo archivo, reserve\_and\_record lo deja escrito: *"Fail CLOSED (hito 21). A $0.02/call provider with a broken fuse can burn the whole monthly budget in one run."* |

Y el estado final de la ejecución, en la misma lógica: en worker.py:1751 se decide con "partial" if step3\_degraded else "completed". El número de candidatos no entra en la cuenta, así que una ejecución que enriqueció bien, filtró todo y entregó cero queda en completed, igual que una exitosa. Lo único que las separa es el total\_candidates de la línea 1755, un contador en cero que nadie mira.

El caso del fusible merece una lectura aparte, porque no es un descuido: el criterio correcto ya está aplicado donde importa y con el razonamiento escrito en el código, y el opuesto quedó en la función de al lado. **El estándar existe y está bien pensado. Lo que falta es que valga para las dos.** Es el mismo hallazgo de la §6, en miniatura y dentro de un solo archivo.

Esto es lo que explica que veintinueve hitos de trabajo real no se hayan convertido en resultado. **No es falta de trabajo: el trabajo está y se ve en el repositorio — los hitos 21, 23 y 26 son arreglos correctos de causas correctas.** Es que el sistema no tiene forma de decirle a quien lo construye qué se rompió: cada arreglo se valida contra un instrumento que informa éxito en los dos casos.

Mientras esa propiedad no cambie, cada mejora futura tiene el mismo problema de verificación que tuvieron las anteriores.

Y el patrón tiene una tercera cara, además de tragarse errores y de no distinguir haber entregado: informar de más. La §5.1 documenta el caso que costó más caro — la metadata de cada corrida registra un plan de búsqueda tres veces más ancho que el que se ejecutó.

# **4\. La capa de datos: se compra dos veces lo que ya se tiene**

El sistema paga por cada perfil que consulta al proveedor. Lo que hace con ese perfil después es la segunda de las tres decisiones de arquitectura.

**La tabla de entidades existe, y el descubrimiento la usa a medias.** No es una carencia de diseño: es una desconexión.

En la migración supabase/migrations/00000000000005\_influencers.sql está influencers, con este comentario en la propia base (línea 35): *"Base de datos maestra de influencers. Snapshot de metricas en otra tabla."* Tiene primary\_handle, country, city, content\_niches\[\], primary\_tier, source, source\_id, borrado lógico, e índices para buscar por nicho y por etiqueta. Al lado tiene influencer\_social\_accounts, para las cuentas por plataforma de un mismo influencer, y influencer\_metrics\_snapshot, para los seguidores y el engagement por fecha. Es, exactamente, el modelo de entidades que hace falta — y es una de las primeras migraciones del proyecto.

**El camino que lleva hasta ahí existe, y deja afuera exactamente lo que costó dinero.** POST /candidates/{id}/save (apps/api/app/api/v1/discovery.py:838-887, con el docstring *"Convierte un discovery\_candidate a influencer real"*) inserta en influencers y marca saved\_as\_influencer\_id en el candidato; el botón «Guardar» de la interfaz lo llama (apps/web/src/features/lens/api/lensApi.ts:95). Lo que escribe es nombre, handle, bio, ciudad y avatar. Ni seguidores, ni engagement\_rate, ni avg\_likes — los tres datos por los que se le pagó al proveedor. primary\_tier va fijo en "MICRO" (línea 858\) sin mirar seguidores, mientras el ETL del otro subsistema lo deriva (resolve\_tier\_from\_followers, scripts/etl\_ism\_backfill.py:193). discovery\_query se escribe vacío (línea 864), justo el campo que la migración 00000000000019 creó para registrar qué lo descubrió. No se crea la fila de influencer\_social\_accounts ni una de influencer\_metrics\_snapshot. Y es un INSERT pelado: influencers.primary\_handle no tiene restricción de unicidad en ninguna migración, así que el mismo handle guardado en dos ejecuciones produce dos influencers — el ETL del otro subsistema sí deduplica por handle (crear\_influencer\_si\_no\_existe, scripts/etl\_ism\_backfill.py:208). Fuera de ese camino, la tabla maestra se llena por importaciones masivas desde el panel de administración, y los dos endpoints que la conectan con datos frescos de Instagram (discovery.py:586 y admin.py:362, ambos enrich-influencers) están cableados al proveedor anterior, el que está marcado como no operativo.

Es decir: del influencer que costó dinero descubrir llega a la base maestra la ficha de contacto, y no las métricas que se compraron. Y en modo Analizar el worker marca status \= "saved" sin pasar por ese camino (worker.py:1739-1741): el candidato queda marcado como guardado sin influencer detrás.

**Lo que sí hay es un caché con vencimiento.** En hikerapi\_client.py:16-18:

CACHE\_TTL\_HASHTAG  \= 43200      \# 12 horas  
CACHE\_TTL\_PROFILE  \= 86400      \# 24 horas  
CACHE\_TTL\_LOCATION \= 30 \* 86400  \# 30 días

Un perfil pagado se guarda en Redis y **vence a las 24 horas.** Pasado ese plazo, el mismo perfil vuelve a costar lo mismo que la primera vez. Y ese Redis es la misma instancia que corre la cola de trabajos y los contadores de presupuesto: si tiene una política de desalojo por memoria, el dato pagado se descarta antes de vencer, y el contador de gasto con él.

El resultado combinado: **la ingesta es una función de un solo sentido.** Se consulta el proveedor, se paga, se responde al usuario, y el dato deja de existir en 24 horas salvo como registro histórico de una ejecución particular. Sobre 48 ejecuciones, cada búsqueda que se solape con otra —el mismo nicho, el mismo país, la misma ciudad— vuelve a pagar los mismos perfiles. Cuántas se solapan no lo pude medir sin acceso a la base.

No es una preferencia de diseño. Es un activo que se paga y no se conserva.

**Y no tiene copia.** El proveedor de infraestructura donde vive esa base no activa por defecto la recuperación a un punto en el tiempo: hay que habilitarla desde la pestaña de respaldos del servicio, y mientras esté apagada el propio panel lo señala con un aviso (documentación de PITR (https://docs.railway.com/volumes/point-in-time-recovery)). No verifiqué qué opciones están activadas en la cuenta: es una de las primeras cosas que conviene mirar, y activar la recuperación no cuesta trabajo de desarrollo.

# **5\. La capa de descubrimiento y de IA: se busca en tres lugares, y la semántica que existe no se usa**

Esta es la tercera decisión de arquitectura. Acá hay cuatro cosas separadas, y una decisión que se sigue de ellas. La primera es la que fija el techo de todo lo demás.

## **5.1 El descubrimiento solo mira en tres lugares**

El plan de búsqueda que arma el sistema es amplio: hasta 30 consultas de hashtag y 20 de palabra clave (packages/discovery/discovery/query\_builder.py:161 y :141). Lo que se ejecuta es otra cosa. El worker consume plan.hashtag\_queries\[:3\] (worker.py:534), \[:2\] (:547) —que son prefijo de los mismos tres— y plan.keyword\_queries\[:3\] (:562) y \[:1\] (:585). **Una corrida completa explora tres hashtags distintos y tres palabras.** El resto del plan no se consulta nunca.

No lo limita el presupuesto. Las llamadas de descubrimiento están estimadas en 32 (worker.py:52) contra un tope de 120 por corrida (packages/shared-core/shared\_core/config.py:87): quedan unas 88 llamadas sin usar en cada ejecución, ya contempladas dentro del tope que la propia agencia configuró. Lo que limita el ancho de la búsqueda son cuatro constantes escritas a mano en el worker.

Aguas abajo se nota: el paso de diversificación por tiers pide 80 perfiles (target\_n \= 80, worker.py:1634) sobre un conjunto que no puede pasar de 25 (MAX\_HANDLES\_TO\_ENRICH, worker.py:50). El objetivo es más de tres veces el conjunto, así que las cuotas por tier nunca llegan a morder: ese paso ordena, no selecciona.

**Y esto explica por qué no se había detectado.** La metadata de cada corrida guarda hashtags\_count: 30 y keywords\_count: 20 (worker.py:394-395): el tamaño del plan, no el de la ejecución. Quien mire los datos de una corrida ve una búsqueda ancha que no ocurrió. Es la enfermedad de la §3 en su tercera forma —un instrumento que informa algo distinto de lo que pasó—, y esta vez lo que escondió fue el techo del producto. El mensaje que ve el analista sí usa conteos reales (worker.py:913-917); la cifra inflada vive en la metadata.

**Por qué es lo que más importa para la calidad.** Ningún ajuste de puntaje rescata a un influencer que nunca entró al conjunto. Con tres hashtags y tres palabras el conjunto queda pegado a un vecindario chico de Instagram, y el mismo brief va a devolver aproximadamente la misma gente siempre. Ensanchar la búsqueda es lo único de este informe que sube el techo de calidad, y es barato: son constantes, y las llamadas ya están dentro del tope.

## **5.2 Hay dos capas de IA en el repositorio y están desconectadas**

Existe una infraestructura de búsqueda semántica bien planteada — embeddings de 384 dimensiones con fastembed, almacenamiento en pgvector, búsqueda por similitud de coseno con umbral (apps/api/app/ai/rag\_engine.py:88-95), y un paquete compartido packages/shared-ai/ pensado para que lo use todo el monorepo.

**El módulo LENS no la usa.** No hay una sola referencia a embeddings, vectores o similitud en todo packages/discovery/. La búsqueda semántica sirve a una función de chat sobre documentos; el producto que vende la agencia —emparejar un brief con perfiles de Instagram, que es un problema de similitud semántica por definición— hace ese emparejamiento contando palabras clave.

Es el mismo patrón con el que cierra este informe: la capacidad está construida, adoptada y disponible en el mismo repositorio, y el producto principal no la alcanza.

Dicho eso, y para que no se gaste esfuerzo en el orden equivocado: **conectar las dos capas no es la palanca de la calidad, y conviene saberlo antes de intentarlo.** Tres razones. La selección que fija el entregable es el recorte a 25, y corre *antes* del enriquecimiento (worker.py:1021-1025): en ese momento un handle que vino de hashtag trae usuario y nombre y nada más (\_extract\_user\_from\_post, packages/discovery/discovery/tools/hikerapi\_client.py:807-819), así que no hay texto que vectorizar. Un vector reordena, no recluta: si el techo es quién entra —§5.1—, la semántica no lo mueve. Y el índice que existe no es reutilizable tal cual: apps/api/app/ai/indexer.py vectoriza métricas de campañas ya ejecutadas, no perfiles, así que esto no es conectar dos piezas sino construir una nueva. Va después de ensanchar la búsqueda, no antes, y con esa expectativa.

## **5.3 El modelo se le pide en texto libre y se le extrae con una expresión regular**

El sistema le pide al modelo que devuelva JSON y después lo busca dentro de la respuesta:

data \= \_json.loads(match.group())     \# candidate\_analyzer.py:187

**\`response\_format\` no aparece ni una vez en todo el repositorio.** El proveedor ofrece un modo JSON garantizado y no se está usando. Del lado del esquema está a medias, y la mitad que falta es la que puntúa. La interpretación del brief sí se valida contra una estructura declarada: brief\_parser.py:323 mete la respuesta en BriefStructured, con enumerados y rangos. La puntuación de candidatos no: \_parse\_batch\_response (candidate\_analyzer.py:182-190) exige que haya un array y cada número se recorta a 0-100 (336-338), pero nada declara la forma de cada objeto ni qué campos son obligatorios. Si el modelo devuelve algo distinto, se cae al camino de la §3 y el candidato queda con puntajes de reglas.

Ese es el punto de precisión de la capa de IA, y es más importante que la elección de modelo: hoy la calidad de la puntuación depende de que el modelo decida acertarle a un formato que nadie le está exigiendo.

## **5.4 El repositorio y la producción no dicen lo mismo sobre qué modelo se usa**

En packages/shared-core/shared\_core/config.py:55 y en .env.example:32:

DEEPSEEK\_MODEL \= "deepseek-chat"

Ese identificador fue **discontinuado el 24 de julio de 2026**, anunciado por el proveedor tres meses antes: *"The two legacy API model names, \`deepseek-chat\` and \`deepseek-reasoner\`, will be discontinued in three months (2026-07-24)"* (changelog oficial, entrada del 24-04-2026 (https://api-docs.deepseek.com/updates)). Los modelos vigentes son otros.

**Y sin embargo el sistema funciona.** Lo vi correr el 20 de agosto, casi un mes después de esa fecha. Las dos cosas son ciertas a la vez, y la explicación es que config.py es un Settings de pydantic-settings con env\_file (packages/shared-core/shared\_core/config.py:11-18): ese "deepseek-chat" es un **valor por omisión**, y cualquier variable de entorno lo pisa. O Railway tiene configurado un modelo vigente, o el proveedor todavía resuelve el alias retirado. No sé cuál de las dos, y son consecuencias distintas.

**Ese es el hallazgo, y no es una caída: es que el repositorio no dice qué modelo puntúa a los candidatos.** El valor por omisión del código y el .env.example —las dos cosas que copia quien monta un entorno nuevo— apuntan a un identificador que el proveedor retiró. Leyendo el repositorio no se puede saber con qué se está trabajando; hay que abrir el panel de Railway. Y eso tiene dos consecuencias concretas: el día que el proveedor deje de resolver el alias, o el día que alguien levante un entorno desde el .env.example, se caen a la vez la interpretación del brief, la generación del perfil de búsqueda y la puntuación de candidatos, que son los tres usos del modelo. Se cierra fijando el modelo de forma explícita y quitando el valor por omisión retirado.

Es, otra vez, la forma del informe: el artefacto dice una cosa y la realidad dice otra. Acá el que estaba desactualizado era el repositorio, no el sistema.

La mitad de IA del sistema —interpretación del brief, generación del perfil de búsqueda, puntuación de candidatos— apunta a un identificador retirado. **No verifiqué en producción si hoy devuelve error o si el proveedor mantiene un alias de gracia**; el changelog anuncia la discontinuación y no aclara ese punto. Se comprueba con una llamada.

Que este dato haya pasado desapercibido no es un descuido del equipo: es la consecuencia natural de tener nueve auditorías internas mirando hacia adentro del repositorio. Ningún análisis del propio código puede detectar que un proveedor externo cambió.

Hay además deriva de configuración acumulada, señal de que ninguna de estas piezas tiene un dueño único: el modelo por defecto en apps/api/app/models/ai.py:34-35 es gpt-4o-mini con proveedor openai, de otro proveedor y otra época; y la documentación de ai\_service.py:6 dice que los embeddings se calculan "with OpenAI" cuando en realidad corren localmente con fastembed. Ninguna de las dos rompe nada hoy. Se limpian con el punto 2 de la §7.

## **5.5 Sobre cambiar de modelo**

La conversación sobre qué modelo usar hay que tenerla, porque el que el repositorio declara está retirado y el que corre no está escrito en ninguna parte. Pero conviene tenerla por el motivo correcto.

Para este sistema, **el costo del modelo de lenguaje no es la variable relevante**: las tareas son cortas y el gasto real del producto está en el proveedor de datos de Instagram, en un orden de magnitud distinto. Cambiar de modelo para ahorrar no mueve la aguja, y las opciones más caras que la actual son varias veces más caras. Lo que sí justifica el cambio es lo de la §5.2: salida estructurada garantizada, validación contra esquema y comportamiento estable.

Hay un detalle que es de presupuesto y no de ingeniería: **la elección de modelo y la del plan del proveedor de datos están acopladas.** El plan de datos que la agencia contrate determina cuál de las dos capas domina el costo por búsqueda, y por lo tanto qué modelo es defendible. Tomar una de las dos decisiones sin la otra deja plata sobre la mesa en una de las dos. El orden importa: el plan de datos primero, el modelo después.

# **6\. Lo que ya resuelven en esta misma casa**

Este es el hallazgo central del informe, y es el que hace que todo lo anterior sea barato de corregir.

**Uno.** En la raíz del repositorio está 13\_data\_contract\_hub.md, un contrato de datos formal, versión 1.0, fechado 10-07-26, marcado *"Estándar activo — todos los reportes al hub deben seguir este formato"*. Sus objetivos declarados, textuales:

*"Ningún parser tenga que adivinar mapeos español → inglés nunca más (bug C-01 resuelto)"*

*"\`raw\_data\` siempre esté presente (bug C-04 resuelto)"*

*"NULL vs 0 se maneje correctamente en todo el pipeline (bug C-07 resuelto)"*

El tercero es, palabra por palabra, el defecto que documenté en la §2.1 y que explica el resultado del negocio. **El equipo ya identificó ese problema, escribió la regla que lo resuelve, y la declaró estándar activo — para el subsistema P.I.A.R.** LENS se construyó después y no lo sigue.

**Dos.** Existen procesos de ingesta propiamente escritos —scripts/etl\_drive.py, scripts/etl\_excel.py, scripts/etl\_ism\_backfill.py, con funciones de normalización dedicadas y con carga histórica—. Son para el otro subsistema. La ingesta de LENS no tiene equivalente.

**Tres.** El planificador de tareas periódicas está cableado y registrado en el mismo worker que corre LENS, en worker.py:2238-2241:

cron\_jobs \= \[  
    cron(scheduled\_reports\_cron, hour=9, minute=0),  
    cron(sync\_metricool\_task,     hour=2, minute=0),  
\]

Una de esas dos tareas consulta métricas a un proveedor externo todos los días a las 2 de la mañana: exactamente la forma que le falta a la ingesta de Instagram. **La infraestructura de la ingesta periódica no falta: el planificador, el worker, el cliente del proveedor y el horario ya están puestos, en el mismo archivo que el pipeline de LENS.** Falta el destino. Esa tarea consulta y devuelve el resultado sin escribir una fila (worker.py:2192-2210, el return en la 2207\) y se salta entera si falta el token (2196-2197); el cuerpo del bucle de la otra es un logger.info (2224-2228). Es el andamio de la ingesta, no la ingesta — y que el andamio esté puesto es justamente el punto: lo que falta escribir es el cuerpo, no la infraestructura. No verifiqué si están habilitadas en producción.

**Cuatro.** El modelo de entidades de la §4 —influencers, influencer\_social\_accounts e influencer\_metrics\_snapshot, migración 00000000000005— existe desde el arranque del proyecto. El ETL del otro subsistema lo llena completo: deduplica por handle y deriva el tier de los seguidores. El descubrimiento lo llena a medias: una ficha de contacto, el tier fijo en MICRO, sin cuenta de plataforma y sin una sola fila de métricas.

La conclusión no es sobre nadie en particular. **Este equipo sabe hacer las cuatro cosas que a LENS le faltan, y las tiene escritas y andando a pocos archivos de distancia.** Lo que falta es que el estándar valga para todo el producto y no solo para el subsistema donde se escribió. Eso se declara como norma del producto, no se resuelve en el código: que el contrato de datos que ya existe sea obligatorio para todo módulo nuevo, y que nada se dé por terminado sin poder demostrar que entregó. Es una regla de la casa, no horas de desarrollo.

# **7\. Cómo se alinea el proyecto**

Cinco puntos, en orden. Son la forma de la corrección, no los pasos: el diseño concreto de cada uno depende de decisiones que la agencia todavía no tomó. El primero lo hace el propio ingeniero de la agencia y no necesita presupuesto ni gente de afuera; del lado de la agencia hacen falta dos cosas nada más: que se autorice antes que el resto de la lista, y la decisión del punto 5\.

**1\. Que el sistema pueda fallar en voz alta, antes que cualquier otra cosa.** Mientras un error produzca un valor plausible, ninguna mejora es verificable — ni las que ya se hicieron. Esto es anterior a todo lo demás en esta lista y es la corrección más barata del informe: no requiere reescribir nada, requiere que los caminos de error dejen de inventar valores y que el estado final de una ejecución distinga haber corrido de haber entregado.

**2\. Un contrato de datos único, y la regla ya está escrita.** 13\_data\_contract\_hub.md es el formato con que el equipo P.I.A.R. entrega reportes de campaña al hub, y obliga campaign\_id y raw\_data en cada fila: no aplica tal cual a un perfil de Instagram. Lo que se transporta es la regla —NULL contra 0, y snake\_case en inglés calzando 1:1 con las columnas—, y es la que cierra el hallazgo de la §2. Lo que hay que escribir es corto y no hay que pensarlo desde cero: que el normalizador produzca una sola forma, que la ausencia de un dato no se escriba como cero, y que la convención del proveedor anterior salga del contrato en la misma operación.

**3\. Completar el camino del descubrimiento a la tabla maestra.** No hay que diseñar el modelo de entidades ni el camino: la migración 00000000000005 trae influencer\_social\_accounts e influencer\_metrics\_snapshot con fecha de corte, y discovery.py:838 ya promueve un candidato a influencer. Falta que sirva: que arrastre las métricas que se pagaron en vez de solo el nombre y la bio, que deduplique por handle en vez de insertar a ciegas, que derive el tier de los seguidores —las tres cosas que el ETL del otro subsistema ya hace—, y que exista la política de frescura que decide cuándo hay que volver a consultar un perfil ya guardado y cuándo no. Eso es lo que convierte el gasto en el proveedor de datos de un costo que se repite en un activo que se acumula, y es la diferencia entre una herramienta que cobra por búsqueda y una que tiene algo que no se puede comprar de nuevo.

**4\. Ensanchar la búsqueda, antes de tocar el ranking.** La §5.1 lo documenta: se construyen hasta 30 consultas de hashtag y 20 de palabra clave, se ejecutan tres y tres, y quedan unas 88 llamadas por corrida dentro del tope ya configurado. Subir esas constantes y volver a correr es el cambio más barato de esta lista y el único que sube el techo de la calidad, porque ningún ajuste de puntaje rescata a quien nunca entró al conjunto. Tiene además criterio de parada propio y se resuelve en una sola corrida: si el conjunto de candidatos crece y el resultado sigue igual, entonces el problema sí es de orden y no de alcance — y esa es la pregunta que hoy nadie puede responder. La capa semántica de la §5.2 va después de esto, con la advertencia que está escrita ahí.

**5\. La única decisión que no es técnica: el plan del proveedor de datos de Instagram.** Ese plan fija el costo por llamada, y de ahí se sigue la del modelo de lenguaje —no al revés—, porque determina cuál de las dos capas domina el costo por búsqueda. Para llevar las dos opciones costeadas hacen falta dos cifras que están del lado de la agencia y no del mío: cuántas búsquedas al mes se piensan vender y cuánto puede costar cada una. Si la autorización del gasto no está en el área, esto es lo único del informe que hay que subir. Conviene resolverlo antes de la próxima recarga: el saldo con ese proveedor es prepago y se consume al precio por llamada del plan vigente.

**Lo que yo no recomiendo hacer:** reescribir worker.py. Tiene 2.245 líneas y 17 funciones de nivel superior —unas 132 líneas por función— y sí, concentra demasiadas responsabilidades. Pero un refactor general cambia el código sin cambiar lo que se sabe, y lo que falta acá es saber. Los puntos 1 y 2 se pueden hacer sin tocar su estructura, y una vez que el sistema informe la verdad, qué conviene separar se vuelve una pregunta con datos.

# **8\. Lo que hay que verificar y no pude**

Para que quede constancia de los límites de esta revisión:

* Qué modelo de lenguaje está configurado en las variables de entorno de Railway, y si el alias retirado sigue resolviendo. El sistema corre, así que una de las dos cosas lo explica; no pude ver cuál. Se resuelve abriendo el panel.  
* Qué opciones de respaldo y recuperación están activadas en la base de datos de producción.  
* Si la instancia de Redis tiene política de desalojo por memoria, lo que afectaría tanto al dato pagado como a los contadores de gasto.  
* Contra qué esquema corren las pruebas automatizadas del repositorio.  
* El propio equipo tiene un análisis interno de cobertura del pipeline con ocho brechas identificadas, posterior a la documentación que revisé. No lo evalué.

*Informe elaborado sobre el commit \`81db353\` del repositorio \`lawebcore\`. Todas las referencias son a archivo y línea verificables en ese commit. Las afirmaciones sobre proveedores externos citan su fuente pública.*