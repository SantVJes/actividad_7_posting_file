# Historias de usuario — Sprint 7

Backlog refinado en la sesión de Sprint Planning del 30 de septiembre de 2026.
Estimación en puntos de historia con sucesión de Fibonacci (1, 2, 3, 5, 8).
Criterios de aceptación en formato Gherkin (Dado / Cuando / Entonces).

**Persona principal:** *Ana*, analista de información que necesita localizar,
en una colección de cientos de documentos, cuáles contienen una palabra dada
y con qué intensidad, sin abrir los documentos uno por uno.

---

## Resumen del Sprint Backlog

| ID | Título | Pts | Prioridad | Estado |
|---|---|---|---|---|
| HU-01 | Generar el archivo diccionario | 2 | Must | Terminada |
| HU-02 | Generar el archivo de posting | 3 | Must | Terminada |
| HU-03 | Posición del primer registro en el diccionario | 3 | Must | Terminada |
| HU-04 | Consultar un token y recuperar sus documentos | 2 | Must | Terminada |
| HU-05 | Evaluar tres escenarios de construcción del posting | 2 | Should | Terminada |
| HU-06 | Medir y registrar los tiempos de proceso | 1 | Must | Terminada |
| **Total** | | **13** | | |

---

## HU-01 — Generar el archivo diccionario

> **Como** Ana, analista de información,
> **quiero** que el vocabulario de la colección quede guardado en un archivo
> **para** no tener que volver a procesar los 505 documentos cada vez que necesito consultarlo.

**Puntos:** 2 · **Prioridad:** Must · **Responsable:** Dev 2

### Criterios de aceptación

```gherkin
Escenario: El diccionario se escribe en disco
  Dado una carpeta con 505 archivos HTML
  Cuando ejecuto el programa indicando esa carpeta como corpus
  Entonces se crea el archivo "output/diccionario.txt"
  Y el archivo contiene una fila por cada token único de la colección
  Y las filas están separadas por salto de línea y las columnas por tabulador

Escenario: El diccionario no contiene duplicados
  Dado el archivo diccionario ya generado
  Cuando reviso la columna de tokens
  Entonces ningún token aparece dos veces

Escenario: El diccionario está ordenado de forma determinista
  Dado que ejecuto el programa dos veces sobre el mismo corpus
  Cuando comparo los dos archivos diccionario resultantes
  Entonces son idénticos byte a byte
```

### Notas de implementación
`src/escritura.py` → `escribir_indice()`. Orden alfabético ascendente por omisión.

---

## HU-02 — Generar el archivo de posting

> **Como** Ana,
> **quiero** saber en qué documentos aparece cada palabra y cuántas veces en cada uno
> **para** priorizar la lectura de los documentos donde la palabra pesa más.

**Puntos:** 3 · **Prioridad:** Must · **Responsable:** Dev 2

### Criterios de aceptación

```gherkin
Escenario: El posting tiene exactamente dos columnas
  Dado una colección de documentos HTML
  Cuando ejecuto el programa
  Entonces se crea el archivo "output/posting.txt"
  Y la columna 1 de cada registro es el nombre del archivo
  Y la columna 2 de cada registro es la frecuencia del token en ese archivo

Escenario: La frecuencia cuenta repeticiones, no presencias
  Dado un documento que contiene la palabra "perro" ocho veces
  Cuando se genera el posting
  Entonces el registro de ese documento para "perro" tiene frecuencia 8
  Y no frecuencia 1

Escenario: Un documento no se repite dentro del mismo token
  Dado el archivo de posting generado
  Cuando reviso los registros de cualquier token
  Entonces ningún nombre de archivo aparece dos veces en ese bloque

Escenario: El total de registros coincide con el diccionario
  Dado el diccionario y el posting generados
  Cuando sumo la columna NUM_DOCS de todo el diccionario
  Entonces el resultado es igual al número de registros del posting
```

### Notas de implementación
`src/escritura.py`. La frecuencia la produce `collections.Counter` sobre la lista de
tokens del documento, que conserva repeticiones por diseño.

---

## HU-03 — Posición del primer registro en el archivo de posting

> **Como** Ana,
> **quiero** que el diccionario me diga en qué posición del posting empiezan los documentos de cada palabra
> **para** que la consulta salte directo a esos registros en lugar de recorrer todo el archivo.

**Puntos:** 3 · **Prioridad:** Must · **Responsable:** Dev 2

### Criterios de aceptación

```gherkin
Escenario: El diccionario tiene tres columnas
  Dado el archivo diccionario generado
  Cuando leo cualquier fila de datos
  Entonces tiene exactamente tres columnas
  Y la columna 1 es el token
  Y la columna 2 es el número de documentos que contienen esa palabra
  Y la columna 3 es la posición del primer registro en el archivo de posting

Escenario: El primer token arranca en la posición cero
  Dado el archivo diccionario generado
  Cuando leo la primera fila de datos
  Entonces su columna 3 vale 0

Escenario: Las posiciones son acumulativas
  Dado dos tokens consecutivos T1 y T2 en el diccionario
  Cuando T1 tiene posición P1 y N1 documentos
  Entonces la posición de T2 es exactamente P1 + N1

Escenario: La cadena de posiciones reproduce la tabla del enunciado
  Dado el corpus de demostración "demo/corpus_figura"
  Cuando ejecuto el programa con el orden de aparición
  Entonces "perro" tiene 4 documentos en la posición 0
  Y "gato" tiene 2 documentos en la posición 4
  Y "pato" tiene 3 documentos en la posición 6
  Y el token siguiente arranca en la posición 9
```

### Notas de implementación
El offset no se calcula aparte: es el contador de registros ya escritos en el posting
en el momento de escribir la fila del diccionario. Ambos archivos se escriben en la
misma pasada, lo que elimina por construcción el riesgo de desincronización (decisión D1).

---

## HU-04 — Consultar un token y recuperar sus documentos

> **Como** Ana,
> **quiero** escribir una palabra y obtener la lista de documentos que la contienen con su frecuencia
> **para** resolver mi búsqueda sin abrir los archivos.

**Puntos:** 2 · **Prioridad:** Must · **Responsable:** Dev 3

### Criterios de aceptación

```gherkin
Escenario: Consulta del token de ejemplo del enunciado
  Dado el índice construido sobre el corpus de demostración
  Cuando consulto el token "perro"
  Entonces obtengo los documentos 004.html, 009.html, 412.html y 444.html
  Y la suma de sus frecuencias es 16

Escenario: La consulta lee solo los registros necesarios
  Dado un token con N documentos y posición P en el diccionario
  Cuando consulto ese token
  Entonces se leen exactamente N registros del posting a partir de la posición P
  Y no se recorre el archivo de posting completo

Escenario: Token que no existe en la colección
  Dado el índice construido
  Cuando consulto un token que no aparece en ningún documento
  Entonces obtengo cero documentos
  Y el programa no falla

Escenario: La consulta no distingue mayúsculas
  Dado el índice construido
  Cuando consulto "PERRO" y luego "perro"
  Entonces ambas consultas devuelven los mismos documentos
```

### Notas de implementación
`src/consulta.py` → `IndiceInvertido.consultar()`. El rebanado
`self._posting[inicio:inicio + n]` es la traducción literal del salto directo.

---

## HU-05 — Evaluar tres escenarios de construcción del posting

> **Como** equipo de desarrollo,
> **queremos** implementar y comparar tres formas distintas de construir el archivo de posting
> **para** elegir con datos, y no por intuición, la que conviene a esta colección y poder cambiar de estrategia si la colección crece.

**Puntos:** 2 · **Prioridad:** Should · **Responsable:** Dev 2 + Dev 3

### Criterios de aceptación

```gherkin
Escenario: Existen tres escenarios seleccionables
  Dado el programa instalado
  Cuando consulto la ayuda de la línea de comandos
  Entonces puedo elegir el escenario A, B o C

Escenario: Los tres escenarios son equivalentes
  Dado el mismo corpus
  Cuando construyo el índice con el escenario A, luego con B y luego con C
  Entonces los tres diccionarios son idénticos byte a byte
  Y los tres archivos de posting son idénticos byte a byte

Escenario: El ordenamiento externo funciona con varios bloques
  Dado el escenario B configurado con un tamaño de bloque de 3 ternas
  Cuando construyo el índice del corpus de demostración
  Entonces se generan varios bloques temporales
  Y el resultado sigue siendo correcto

Escenario: El escenario C deja un índice consultable con SQL
  Dado el escenario C con una ruta de base de datos en disco
  Cuando termina la construcción del índice
  Entonces la base de datos existe
  Y una consulta SQL sobre el token "perro" devuelve frecuencia total 16

Escenario: Se reporta el tiempo de cada escenario
  Dado el modo de comparación
  Cuando ejecuto el programa con la opción de comparar
  Entonces obtengo una tabla con el tiempo total de cada escenario
```

### Notas de implementación
`src/estrategias.py`. Los tres escenarios implementan la interfaz
`EstrategiaPosting`; el detalle de los compromisos de cada uno está en
[`escenarios_posting.md`](escenarios_posting.md).

---

## HU-06 — Medir y registrar los tiempos de proceso

> **Como** Scrum Master,
> **quiero** un registro del tiempo que tarda cada archivo y el proceso completo
> **para** saber dónde está el cuello de botella y poder justificar las decisiones de optimización ante el Product Owner.

**Puntos:** 1 · **Prioridad:** Must · **Responsable:** Dev 3

### Criterios de aceptación

```gherkin
Escenario: Se genera el archivo log
  Dado que ejecuto el programa indicando la matrícula
  Cuando termina el proceso
  Entonces se crea el archivo "output/a7_<matrícula>.txt"

Escenario: El log detalla cada archivo
  Dado el archivo log generado
  Cuando reviso la sección de detalle
  Entonces hay una fila por cada archivo procesado
  Y cada fila indica bytes leídos, tokens, tokens únicos y tiempo en segundos

Escenario: El log reporta los totales del proceso
  Dado el archivo log generado
  Cuando reviso la sección de resumen
  Entonces aparece el tiempo total del proceso
  Y el tiempo promedio por archivo
  Y el archivo más lento y el más rápido
  Y el desglose de tiempo por fase con su porcentaje

Escenario: La medición no se contamina con la salida a consola
  Dado el cronómetro del proceso
  Cuando se mide el tiempo de un archivo
  Entonces se usa un reloj monótono de alta resolución
  Y el avance en consola se imprime fuera del intervalo medido
```

### Notas de implementación
`src/cronometro.py`. Se usa `time.perf_counter()` en lugar de `time.time()` porque
este último puede retroceder si el sistema ajusta la hora y arruinaría la medición.

---

## Historias no seleccionadas (quedan en el Product Backlog)

| ID | Título | Pts | Razón de exclusión |
|---|---|---|---|
| HU-07 | Limpiar el ruido del vocabulario (DT-01) | 3 | No afecta el Sprint Goal; se refina en el Sprint 8 |
| HU-08 | Consulta booleana AND / OR / NOT sobre el índice | 5 | Depende de que HU-04 esté terminada; siguiente sprint |
| HU-09 | Ponderación TF-IDF de los resultados | 8 | Sin refinar; falta definir la fórmula con el Product Owner |
| HU-10 | Índice incremental (agregar documentos sin reconstruir) | 5 | Sin refinar |
