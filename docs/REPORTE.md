# Reporte — Actividad 7
## Creación del archivo de posting, diccionario de tres columnas y medición de tiempos

| | |
|---|---|
| **Alumno** | Jesús Santiago Velasco |
| **Matrícula** | *(pendiente — ver nota al final)* |
| **Institución** | Universidad Tecmilenio |
| **Sprint** | Sprint 7 |
| **Fecha** | 30 de septiembre de 2026 |
| **Colección procesada** | 505 archivos HTML (11,913,240 bytes) |
| **Repositorio** | `actividad_7_posting_file` |

---

## 1. Objetivo

Extender el indexador construido en los sprints anteriores para que persista el
índice invertido en dos archivos:

1. Un **archivo diccionario** de tres columnas: token, número de documentos que lo
   contienen y posición del primer registro en el archivo de posting.
2. Un **archivo de posting** de dos columnas: nombre del archivo y frecuencia del
   token en ese archivo.

Adicionalmente: desarrollar **tres escenarios posibles** para la creación del archivo
de posting, e instrumentar la **medición de tiempos** por archivo y del proceso
completo en un archivo log `a7_<matrícula>.txt`.

---

## 2. Trabajo de equipo Scrum

La sesión de Sprint Review (cierre del Sprint 6) y Sprint Planning (apertura del
Sprint 7) se celebró el 30 de septiembre de 2026. La minuta completa está en
[`minuta_sprint.md`](minuta_sprint.md).

### 2.1 Resultado del Sprint Review

El incremento del Sprint 6 —diccionario de tokens en memoria— fue **aceptado** por
el Product Owner. De la retroalimentación surgieron seis observaciones, de las
cuales cinco se convirtieron en historias del Sprint 7 y una se registró como deuda
técnica:

| Retroalimentación | Destino |
|---|---|
| El diccionario se pierde al terminar el programa | HU-01 |
| Falta saber en qué documentos y cuántas veces | HU-02 |
| Falta la columna de posición para no recorrer todo el posting | HU-03 |
| Hay varias formas razonables de construir el posting | HU-05 |
| No existe ninguna medición de tiempos | HU-06 |
| El vocabulario incluye ruido (`00pm`, `0100to`) | Deuda técnica DT-01 |

### 2.2 Sprint Goal acordado

> Persistir el índice invertido en dos archivos —un diccionario de tres columnas y
> un archivo de posting de dos columnas— de modo que, dado un token, el sistema
> entregue los documentos que lo contienen y su frecuencia sin recorrer todo el
> posting; y dejar instrumentada la medición de tiempos.

### 2.3 Sprint Backlog

Seis historias, 13 puntos, todas terminadas. El detalle con criterios de aceptación
en formato Gherkin está en [`historias_usuario.md`](historias_usuario.md).

| ID | Historia | Pts | Estado |
|---|---|---|---|
| HU-01 | Generar el archivo diccionario | 2 | Terminada |
| HU-02 | Generar el archivo de posting | 3 | Terminada |
| HU-03 | Posición del primer registro en el diccionario | 3 | Terminada |
| HU-04 | Consultar un token y recuperar sus documentos | 2 | Terminada |
| HU-05 | Evaluar tres escenarios de construcción del posting | 2 | Terminada |
| HU-06 | Medir y registrar los tiempos de proceso | 1 | Terminada |

**Velocidad del Sprint 7: 13 / 13 puntos.**

---

## 3. Arquitectura de la solución

El programa se separó en módulos de responsabilidad única para que el cambio de
estrategia de posting no toque la tokenización ni el formato de salida.

```
Files/ (505 HTML)
     │
     ▼
extraccion.py ──── lectura tolerante → quitar etiquetas → minúsculas →
     │              quitar acentos → segmentar → descartar stopwords
     ▼
     Counter  ───── frecuencia de cada token EN ESE documento
     │
     ▼
estrategias.py ─── ESCENARIO A, B o C: agrupa las ternas por token
     │              (es la única pieza que cambia entre escenarios)
     ▼
escritura.py ───── escribe diccionario y posting EN UNA SOLA PASADA
     │              y calcula los offsets por construcción
     ├──────────────> output/diccionario.txt   (3 columnas)
     └──────────────> output/posting.txt       (2 columnas)

cronometro.py ──── mide cada archivo y cada fase → output/a7_<matrícula>.txt
consulta.py  ───── token → documentos, usando el salto directo del diccionario
```

### 3.1 La decisión de diseño que importa

El riesgo central de esta actividad es que el diccionario y el posting se
**desincronicen**: si la columna 3 apunta a un registro equivocado, la consulta
devuelve documentos de otra palabra y el error es silencioso.

La solución fue no calcular el offset como un paso aparte, sino **escribir ambos
archivos en la misma pasada**, de forma que el offset *es* el contador de registros
ya volcados al posting:

```python
posicion = 0
for token, registros in grupos:
    f_dic.write(f"{token}\t{len(registros)}\t{posicion}\n")   # apunta a donde EMPEZARÁN
    for archivo, frecuencia in registros:
        f_post.write(f"{archivo}\t{frecuencia}\n")            # se escriben aquí
    posicion += len(registros)                                # el siguiente arranca después
```

Con esto la desincronización no se previene con cuidado, se vuelve
**estructuralmente imposible**.

---

## 4. Formato de los archivos generados

### 4.1 Archivo diccionario — `output/diccionario.txt`

Tres columnas separadas por tabulador:

| Columna | Nombre | Contenido |
|---|---|---|
| 1 | `TOKEN` | La palabra indexada, normalizada |
| 2 | `NUM_DOCS` | Número de documentos que contienen esa palabra |
| 3 | `POS_POSTING` | Posición del primer registro en el archivo de posting |

**Regla de las posiciones:** `pos(t₀) = 0` y `pos(tᵢ₊₁) = pos(tᵢ) + num_docs(tᵢ)`.
Las posiciones se cuentan en registros base 0, sin contar la fila de encabezado.

### 4.2 Archivo de posting — `output/posting.txt`

Dos columnas separadas por tabulador:

| Columna | Nombre | Contenido |
|---|---|---|
| 1 | `ARCHIVO` | Nombre del archivo del corpus |
| 2 | `FRECUENCIA` | Repeticiones del token dentro de ese archivo |

### 4.3 Reproducción exacta del ejemplo del enunciado

Para poder demostrar el comportamiento con los tokens del enunciado —que están en
español y no existen en esta colección en inglés— se construyó el corpus de
demostración `demo/corpus_figura/` con cuatro documentos: `004.html`, `009.html`,
`412.html` y `444.html`.

```
$ python src/a7_indexador.py --corpus demo/corpus_figura \
      --salida demo/salida_figura --orden aparicion --matricula DEMO
```

**Diccionario generado:**

| TOKEN | NUM_DOCS | POS_POSTING | Verificación de la aritmética |
|---|---|---|---|
| perro | 4 | 0 | primer token → 0 |
| gato | 2 | 4 | 0 + 4 |
| pato | 3 | 6 | 4 + 2 |
| canario | 1 | 9 | 6 + 3 |

**Posting generado:**

| # | ARCHIVO | FRECUENCIA | Pertenece a |
|---|---|---|---|
| 0 | 004.html | 2 | perro |
| 1 | 009.html | 2 | perro |
| 2 | 412.html | 4 | perro |
| 3 | 444.html | 8 | perro |
| 4 | 004.html | 1 | gato |
| 5 | 412.html | 1 | gato |
| 6 | 004.html | 3 | pato |
| 7 | 412.html | 6 | pato |
| 8 | 444.html | 2 | pato |
| 9 | 009.html | 1 | canario |

Esto reproduce **las dos** afirmaciones del enunciado:

- *«el token perro debe entregar como resultado los documentos 004, 009, 412 y 444»* ✓
- `perro` → 4 docs en posición 0, 16 repeticiones; `gato` → 2 docs en posición 4,
  2 repeticiones; `pato` → 3 docs en posición 6, 11 repeticiones; el siguiente token
  en la posición 9 (6 + 3) ✓

---

## 5. Los tres escenarios de creación del posting

El documento completo, con diagramas y análisis de complejidad, está en
[`escenarios_posting.md`](escenarios_posting.md). Resumen:

| | **Escenario A** | **Escenario B** | **Escenario C** |
|---|---|---|---|
| **Nombre** | Índice invertido en memoria | Dos pasadas con orden externo | Acumulación en SQLite |
| **Mecanismo** | `dict[token][archivo]` en RAM, ordenado al final | Bloques ordenados en disco, mezclados con `heapq.merge` | Tabla con índice B-tree, recuperada con `ORDER BY` |
| **Memoria** | O(V + P) — 37.8 MB medidos | O(tamaño de bloque) | O(caché de páginas) |
| **Disco extra** | ninguno | O(T) temporal | O(T) persistente |
| **Tiempo total** | **6.14 s** | 6.77 s (+10.2 %) | 6.72 s (+9.4 %) |
| **Ventaja clave** | El más rápido y simple | Único que escala más allá de la RAM | Índice consultable con SQL |
| **Desventaja clave** | No escala | El más lento | Depende de un motor externo |

**Verificación de equivalencia:** los tres escenarios producen diccionario y posting
**idénticos byte a byte**. No es una afirmación de confianza: la comprueba la prueba
automatizada `test_los_tres_escenarios_producen_la_misma_salida` y el modo
`--comparar`, que termina con código de salida distinto de cero si alguno divergiera.

```
======================================================================
COMPARATIVA DE ESCENARIOS
======================================================================
ESC     TOTAL (s)  ARCHIVOS (s)    TOKENS   REGISTROS
----------------------------------------------------------------------
A          6.1421        5.8255    89,237     311,531
B          6.7707        6.2832    89,237     311,531
C          6.7181        5.9033    89,237     311,531
----------------------------------------------------------------------
Escenario A: identico a A
Escenario B: identico a A
Escenario C: identico a A

OK: los tres escenarios producen salidas identicas byte a byte.
```

### 5.1 Hallazgo del análisis comparativo

La diferencia entre los tres escenarios es de apenas 10 %. El desglose por fase
explica por qué: **la lectura y tokenización de los HTML consume el 96 % del tiempo
total**, mientras que el ordenamiento del índice y la escritura de los dos archivos
—lo único que distingue a los escenarios— pesa menos del 4 %.

> La conclusión práctica es que optimizar la estrategia de posting en esta colección
> sería optimizar el 4 % del problema. El cuello de botella real es el parseo de HTML
> con BeautifulSoup. Elegir el escenario A no es solo elegir el más rápido: es
> reconocer que aquí la simplicidad no cuesta rendimiento.

**Escenario adoptado para la entrega: A.** Cambiar a B o C ante un corpus mayor
cuesta un argumento de línea de comandos, no una reescritura.

---

## 6. Medición de tiempos — archivo log

El archivo log se genera en `output/a7_<matrícula>.txt`. Contiene cuatro secciones:
encabezado de identificación, detalle por archivo, resumen de tiempos y desglose por
fase.

### 6.1 Encabezado del log

```
==============================================================================
ACTIVIDAD 7 - CREACION DEL ARCHIVO DE POSTING Y DICCIONARIO
LOG DE MEDICION DE TIEMPOS
==============================================================================
Alumno            : Jesus Santiago Velasco
Matricula         : <matrícula>
Fecha y hora      : 2026-09-30 19:33:43
Escenario usado   : A - Indice invertido completo en RAM [orden: alfabetico]
Carpeta del corpus: .../actividad_7_posting_file/Files
Python            : 3.11.15
Plataforma        : Linux-6.18.44-fc-v50-x86_64-with-glibc2.39
==============================================================================
```

### 6.2 Detalle por archivo (extracto de las 505 filas)

```
DETALLE POR ARCHIVO
------------------------------------------------------------------------------
   #  ARCHIVO            BYTES   TOKENS  UNICOS   TIEMPO (s)
------------------------------------------------------------------------------
   1  002.html          26,751    2,197     988     0.016305
   2  003.html           2,474       73      40     0.003489
   3  004.html           3,286      156     111     0.003785
   4  005.html          28,379    2,018   1,094     0.004599
   5  006.html           1,503       35      28     0.001369
   6  007.html          39,680    3,400   1,235     0.008948
   7  008.html           3,874      219     162     0.002389
   8  009.html          13,503    1,150     752     0.003587
   9  010.html           3,973      291     207     0.001651
  10  011.html          11,563      978     461     0.003373
 ...
 505  simple.html          271       16      14     0.000301
------------------------------------------------------------------------------
```

### 6.3 Resumen de tiempos

| Métrica | Valor |
|---|---|
| Archivos procesados | 505 |
| Bytes leídos | 11,913,240 |
| Tokens indexados (con repeticiones) | 637,372 |
| Tiempo sumado de los archivos | 5.935494 s |
| Tiempo promedio por archivo | 0.011753 s (11.75 ms) |
| Archivo más lento | `421.html` — 0.188059 s |
| Archivo más rápido | `simple.html` — 0.000301 s |

### 6.4 Tiempo por fase del proceso

| Fase | Tiempo | % del total |
|---|---|---|
| 1. Procesamiento de archivos (lectura + tokenización) | 5.948484 s | 95.97 % |
| 2. Ordenamiento del índice + escritura de salidas | 0.237544 s | 3.83 % |
| **TIEMPO TOTAL DEL PROCESO** | **6.198461 s** | **100.00 %** |

### 6.5 Resumen del índice generado

| Métrica | Valor |
|---|---|
| Tokens únicos en el diccionario | 89,237 |
| Registros en el archivo de posting | 311,531 |
| Ocurrencias totales de tokens | 637,372 |

### 6.6 Nota metodológica

Se usa `time.perf_counter()` —reloj monótono de alta resolución— en lugar de
`time.time()`, porque este último puede retroceder si el sistema ajusta la hora
durante la corrida y arruinaría la medición. El avance en consola se imprime
**fuera** del intervalo medido para no contaminar el tiempo con E/S de terminal.

La diferencia entre el *tiempo sumado de los archivos* (5.935 s) y el *tiempo de la
fase 1* (5.948 s) son los 13 ms del recorrido del directorio y la administración del
ciclo. Se reportan por separado en lugar de ocultarse en un solo número.

---

## 7. Verificación de resultados

### 7.1 Invariantes internas (automáticas en cada corrida)

Al terminar, el programa ejecuta `verificar_integridad()`, que comprueba:

1. El diccionario está en orden alfabético ascendente.
2. La cadena de offsets es acumulativa y sin huecos: `pos(tᵢ₊₁) = pos(tᵢ) + n(tᵢ)`.
3. El número de registros del posting es exactamente la suma de la columna `NUM_DOCS`.
4. Ningún token declara cero documentos.
5. Ningún token repite el mismo documento en su bloque de posting.

Resultado: `Integridad : OK (offsets acumulativos y posting consistente)`.

### 7.2 Suite de pruebas

```
$ python tests/test_escenarios.py
  ...
  17/17 pruebas exitosas
```

17 pruebas en tres niveles: unidad (tokenización), integración (reproducción de la
figura del enunciado) y equivalencia (los tres escenarios).

### 7.3 Verificación independiente contra fuerza bruta

Las pruebas anteriores confirman que el índice es *coherente consigo mismo*, pero un
índice puede ser coherente y estar equivocado: si la tokenización perdiera palabras,
los tres escenarios perderían las mismas y nadie lo notaría.

Para cerrar ese hueco, `tests/verificar_contra_fuerza_bruta.py` recalcula el índice
desde cero —releyendo y retokenizando los 505 archivos— y compara contra el índice
generado:

```
$ python tests/verificar_contra_fuerza_bruta.py --muestra 300

OK: el vocabulario coincide (89,237 tokens).
Verificando 310 tokens contra la referencia...
OK: ocurrencias totales coinciden (637,372).

RESULTADO: OK. 310 tokens verificados sin discrepancias.
El indice coincide con el recalculo independiente de la coleccion.
```

### 7.4 Verificación contra una herramienta externa

Como tercera comprobación, independiente del código propio, se contrastaron dos
tokens contra `grep`:

| Token | Documentos según el índice | Documentos según `grep -ril` | Coincide |
|---|---|---|---|
| `privacy` | 15 | 15 | Sí |
| `encryption` | 5 | 5 | Sí |

### 7.5 Ejemplo de consulta sobre la colección real

```
$ python src/a7_indexador.py --salida output --consultar encryption

TOKEN: encryption
  Documentos            : 5
  Posicion en el posting: 87284
  Frecuencia total      : 38
  Registros leidos del posting:
    [  87284] 043.html            2
    [  87285] 150.html            4
    [  87286] 159.html           30
    [  87287] 171.html            1
    [  87288] 501.html            1
```

La consulta leyó exactamente 5 registros a partir de la posición 87,284. **No
recorrió los 311,531 registros del posting** — ese es precisamente el valor de la
tercera columna del diccionario.

---

## 8. Deuda técnica registrada

| ID | Descripción | Prioridad |
|---|---|---|
| DT-01 | El vocabulario incluye ruido (`00pm`, `0100to`, cadenas concatenadas) porque algunos HTML del corpus no separan palabras con espacios. Candidatos de solución: exigir al menos una letra por token, aplicar stemming, o una lista negra. No afecta el Sprint Goal. | Media — Sprint 8 |
| DT-02 | El modo `--orden aparicion` solo está disponible en el escenario A. Es una limitación inherente al ordenamiento externo, no un defecto: producir orden de primera aparición requiere un mapa global token → rango, que es la estructura en memoria que los escenarios B y C existen para evitar. | Baja — no se planea corregir |

---

## 9. Conclusiones

1. **El objetivo se cumplió.** El programa genera el diccionario de tres columnas y
   el archivo de posting de dos columnas, con la cadena de posiciones acumulativa que
   pide el enunciado, y lo demuestra reproduciendo la figura exactamente en el corpus
   de demostración.

2. **La desincronización se eliminó por diseño, no por cuidado.** Escribir ambos
   archivos en la misma pasada vuelve estructuralmente imposible que la columna de
   posiciones apunte a registros equivocados.

3. **Los tres escenarios valen por la opción, no por la velocidad.** La diferencia
   medida es de 10 %, pero el escenario B permite indexar colecciones que no caben en
   RAM y el C deja un índice consultable con SQL. Cambiar entre ellos cuesta un
   argumento de CLI porque los tres viven detrás de la misma interfaz, y la
   equivalencia de sus salidas está respaldada por una prueba automatizada.

4. **La medición cambió la prioridad de optimización.** Antes de medir, el equipo
   asumía que la construcción del posting era el costo dominante. El log mostró que
   es el 4 % y que el 96 % está en el parseo de HTML. Sin la instrumentación de HU-06,
   el Sprint 8 habría optimizado la parte equivocada.

5. **Tres niveles de verificación independientes.** Invariantes internas en cada
   corrida, 17 pruebas automatizadas, y un recálculo por fuerza bruta contrastado
   además contra `grep`. La corrección del índice no depende de que una sola pieza de
   código esté bien.

---

## 10. Nota sobre la matrícula

El archivo log se nombra con el patrón `a7_<matrícula>.txt` tomado del argumento
`--matricula`. La corrida incluida en este repositorio se generó con el valor
provisional `MATRICULA`. Para regenerarlo con la matrícula definitiva:

```bash
python src/a7_indexador.py --corpus Files --matricula 1234567
```

Esto produce `output/a7_1234567.txt` con todas las mediciones.

---

## Anexos

| Archivo | Contenido |
|---|---|
| [`minuta_sprint.md`](minuta_sprint.md) | Minuta completa de Sprint Review y Sprint Planning |
| [`historias_usuario.md`](historias_usuario.md) | Las 6 historias con criterios de aceptación en Gherkin |
| [`escenarios_posting.md`](escenarios_posting.md) | Análisis detallado de los tres escenarios |
| `output/a7_MATRICULA.txt` | Archivo log completo con las 505 filas de detalle |
| `output/diccionario.txt` | Diccionario de 89,237 tokens |
| `output/posting.txt` | Posting de 311,531 registros |
| `demo/salida_figura/` | Salida que reproduce la figura del enunciado |
