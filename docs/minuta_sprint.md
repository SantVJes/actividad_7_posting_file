# Minuta de Sprint Review y Sprint Planning

**Proyecto:** Motor de recuperación de información — Actividad 7
**Sprint que cierra:** Sprint 6 — *Diccionario de tokens en memoria*
**Sprint que inicia:** Sprint 7 — *Archivo de posting, diccionario de tres columnas y medición de tiempos*
**Fecha de la sesión:** 30 de septiembre de 2026
**Hora:** 17:00 – 19:00 h (Sprint Review 17:00–17:50, Sprint Planning 18:00–19:00)
**Modalidad:** Híbrida (sala de juntas + videoconferencia)
**Levantó la minuta:** Jesús Santiago Velasco

---

## 1. Asistentes

| Rol | Nombre | Asistencia |
|---|---|---|
| Product Owner | Rocío | Presente |
| Scrum Master | Jesús Santiago Velasco | Presente |
| Developer — extracción y normalización | Equipo de desarrollo (perfil Dev 1) | Presente |
| Developer — estructuras de índice | Equipo de desarrollo (perfil Dev 2) | Presente |
| Developer — pruebas y métricas | Equipo de desarrollo (perfil Dev 3) | Presente |
| Stakeholder (docente / cliente) | Profesor de la asignatura | Invitado, presente en el Review |

> El equipo opera con un solo desarrollador real (Jesús) que asume los tres perfiles
> técnicos. Los perfiles se mantienen en la minuta porque definen las responsabilidades
> de cada historia y hacen explícito qué sombrero se usa en cada tarea.

---

## 2. Parte I — Sprint Review (Sprint 6)

### 2.1 Objetivo del Sprint 6

> Construir en memoria un diccionario de tokens único a partir de la colección de
> documentos HTML, con las palabras normalizadas y sin palabras vacías.

### 2.2 Incremento presentado

Se ejecutó el programa en vivo sobre la colección de 505 archivos HTML.

| Elemento demostrado | Resultado |
|---|---|
| Lectura tolerante de los 505 archivos | 505/505 leídos, 0 errores de codificación |
| Extracción de texto (sin etiquetas, sin `script`/`style`) | Correcta |
| Normalización (minúsculas, sin acentos) | Correcta |
| Eliminación de palabras vacías (es + en) | 313 stopwords aplicadas (174 es + 142 en, 3 compartidas) |
| Diccionario único en memoria | 89,237 tokens únicos |

### 2.3 Revisión del Definition of Done

| Criterio | ¿Cumple? | Observación |
|---|---|---|
| El código corre de principio a fin sin intervención manual | Sí | — |
| Cada módulo tiene una responsabilidad única | Sí | `extraccion.py` quedó aislado del índice |
| Hay pruebas automatizadas de la tokenización | Sí | 7 pruebas de unidad |
| El resultado es reproducible entre corridas | Sí | Orden determinista |
| Documentación mínima en el código | Sí | Docstrings en español |

**Veredicto del Product Owner:** incremento **ACEPTADO**.

### 2.4 Retroalimentación recibida

| # | Quién | Comentario | Acción derivada |
|---|---|---|---|
| R1 | Product Owner | El diccionario en memoria no sirve de nada si se pierde al terminar el programa. Hay que persistirlo. | Entra al Sprint 7 como HU-01 |
| R2 | Product Owner | Saber *qué* palabras existen no basta; se necesita saber *en qué documentos* y *cuántas veces*. | Entra al Sprint 7 como HU-02 |
| R3 | Stakeholder (docente) | El diccionario debe poder llevar a los documentos sin recorrer todo el archivo de posting: hace falta la columna de posición. | Entra al Sprint 7 como HU-03 |
| R4 | Dev 2 | Hay más de una forma razonable de construir el posting; conviene evaluarlas antes de casarse con una. | Entra al Sprint 7 como HU-05 (tres escenarios) |
| R5 | Dev 3 | No hay ninguna medición: no sabemos si el proceso tarda 2 s o 2 min, ni qué archivo es el cuello de botella. | Entra al Sprint 7 como HU-06 |
| R6 | Stakeholder (docente) | Los 89,237 tokens incluyen ruido (`00pm`, `0100to`). No es bloqueante, pero debe quedar documentado. | Se registra como deuda técnica DT-01, no entra al Sprint 7 |

### 2.5 Métricas del Sprint 6

| Métrica | Valor |
|---|---|
| Puntos comprometidos | 13 |
| Puntos completados | 13 |
| Velocidad (velocity) | 13 pts |
| Historias terminadas / comprometidas | 4 / 4 |
| Impedimentos abiertos al cierre | 0 |

---

## 3. Parte II — Sprint Planning (Sprint 7)

### 3.1 Objetivo del Sprint (Sprint Goal)

> **Persistir el índice invertido en dos archivos —un diccionario de tres columnas y
> un archivo de posting de dos columnas— de modo que, dado un token, el sistema
> entregue los documentos que lo contienen y su frecuencia sin recorrer todo el
> posting; y dejar instrumentada la medición de tiempos por archivo y del proceso
> completo.**

### 3.2 Capacidad del Sprint

| Concepto | Valor |
|---|---|
| Duración del Sprint | 1 semana |
| Velocidad histórica (promedio últimos 3 sprints) | 13 pts |
| Capacidad comprometida | 13 pts |
| Días hábiles | 5 |

### 3.3 Sprint Backlog seleccionado

| ID | Historia de usuario | Pts | Responsable |
|---|---|---|---|
| HU-01 | Generar el archivo diccionario | 2 | Dev 2 |
| HU-02 | Generar el archivo de posting | 3 | Dev 2 |
| HU-03 | Añadir la tercera columna (posición en el posting) | 3 | Dev 2 |
| HU-04 | Consultar un token y recuperar sus documentos | 2 | Dev 3 |
| HU-05 | Evaluar tres escenarios de construcción del posting | 2 | Dev 2 + Dev 3 |
| HU-06 | Medir y registrar los tiempos en `a7_<matrícula>.txt` | 1 | Dev 3 |
| | **Total comprometido** | **13** | |

El detalle de cada historia, con criterios de aceptación en formato Gherkin, está en
[`historias_usuario.md`](historias_usuario.md).

### 3.4 Decisiones técnicas acordadas en la planeación

| # | Decisión | Justificación |
|---|---|---|
| D1 | Los dos archivos se escriben en **una sola pasada simultánea**. | El offset que se anota en el diccionario es, por construcción, el número de registros ya volcados al posting. Vuelve imposible que los archivos se desincronicen. |
| D2 | Formato **TSV con fila de encabezado**. | Separador inequívoco (ningún token contiene tabulador) y legible tanto por humanos como por Excel. Las posiciones se cuentan en registros base 0, sin contar el encabezado. |
| D3 | Orden por omisión: **alfabético de token**, y por nombre de archivo dentro de cada token. | Hace la salida determinista y permite comparar los tres escenarios byte a byte. |
| D4 | Se añade un modo `--orden aparicion` para reproducir la figura del enunciado. | El enunciado presenta las filas en orden de aparición (perro, gato, pato). Se soporta como modo explícito, no como comportamiento por omisión. |
| D5 | Los tres escenarios se implementan **detrás de la misma interfaz** y se exige que produzcan salidas idénticas. | Convierte la comparación en una prueba automatizada en lugar de una opinión. |
| D6 | La deuda técnica DT-01 (ruido en los tokens) **no entra** a este Sprint. | No afecta el Sprint Goal; se documenta y se prioriza en el refinamiento del Sprint 8. |

### 3.5 Riesgos identificados

| # | Riesgo | Impacto | Mitigación acordada |
|---|---|---|---|
| G1 | El diccionario y el posting se desincronizan y las posiciones apuntan a registros equivocados. | Alto | Decisión D1 + prueba automatizada de la cadena de offsets (`pos(t+1) = pos(t) + n(t)`). |
| G2 | El escenario en memoria no escala a colecciones mayores que la RAM. | Medio | Se implementa el escenario B (ordenamiento externo) como alternativa ya probada. |
| G3 | La medición de tiempos se contamina con la escritura a consola. | Bajo | El cronómetro usa `perf_counter()` y se detiene antes de imprimir; el avance se reporta cada 100 archivos. |
| G4 | El corpus en inglés no permite probar los ejemplos del enunciado (perro, gato, pato). | Medio | Se construye un corpus de demostración en `demo/corpus_figura/` que reproduce la figura exactamente. |

### 3.6 Definition of Done del Sprint 7

Una historia está terminada cuando:

1. El código corre de principio a fin sin intervención manual.
2. Existe al menos una prueba automatizada que falla si la historia se rompe.
3. La verificación de integridad del índice pasa sin reportar problemas.
4. Los tres escenarios siguen produciendo salidas idénticas.
5. El comportamiento queda documentado en el docstring del módulo y en `docs/`.
6. El cambio está en el repositorio con un mensaje de commit descriptivo.

---

## 4. Acuerdos y compromisos

| # | Acuerdo | Responsable | Fecha |
|---|---|---|---|
| A1 | Implementar HU-01 a HU-03 (diccionario + posting + offsets) | Dev 2 | Día 2 del Sprint |
| A2 | Implementar los tres escenarios y la prueba de equivalencia | Dev 2 / Dev 3 | Día 3 |
| A3 | Implementar la consulta token → documentos y el corpus de demostración | Dev 3 | Día 4 |
| A4 | Instrumentar el cronómetro y generar `a7_<matrícula>.txt` | Dev 3 | Día 4 |
| A5 | Entregar el reporte con el log y la comparativa | Scrum Master | Día 5 |
| A6 | Registrar DT-01 en el Product Backlog para refinamiento del Sprint 8 | Product Owner | Día 1 |

## 5. Deuda técnica registrada

| ID | Descripción | Prioridad |
|---|---|---|
| DT-01 | El corpus produce tokens con ruido (`00pm`, `0100to`, cadenas concatenadas) por falta de separadores en el HTML original. Candidatos: exigir al menos una letra, stemming, lista negra. | Media — Sprint 8 |
| DT-02 | El modo `--orden aparicion` solo está disponible en el escenario A. Documentado como limitación inherente al ordenamiento externo, no como defecto. | Baja — no se planea corregir |

## 6. Próxima sesión

**Sprint Review y Planning del Sprint 8** — 7 de octubre de 2026, 17:00 h.
Temas anticipados: refinamiento de DT-01 y construcción del módulo de consulta booleana (AND / OR / NOT) sobre el índice ya persistido.

---

*Minuta cerrada a las 19:00 h del 30 de septiembre de 2026.*
