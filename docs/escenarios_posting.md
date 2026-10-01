# Tres escenarios para la creación del archivo de posting

Documento de la historia **HU-05**. Resultado del refinamiento del Sprint 7.

---

## 1. El problema que los tres escenarios resuelven

Al procesar la colección, cada documento produce un conjunto de pares
*(token, frecuencia)*. Si se juntan todos los documentos, lo que se tiene es una
lista desordenada de **ternas**:

```
(privacy, 001.html, 12)
(internet, 001.html,  4)
(privacy, 002.html,  7)
(encryption, 001.html, 3)
...
```

Pero el archivo de posting exige lo contrario: los registros del **mismo token**
deben quedar **contiguos**, porque el diccionario solo guarda la posición del
primero y el número de documentos. Si los registros de `privacy` estuvieran
dispersos, la columna 3 del diccionario no serviría para nada.

> **El problema es, por tanto, uno de agrupación y ordenamiento:**
> convertir un flujo de ternas que llega agrupado *por documento* en un archivo
> agrupado *por token*. Esto es una transposición del índice —de orientado a
> documentos a orientado a términos— y es el paso donde se decide si el
> indexador escala o no.

Los tres escenarios son tres maneras distintas de hacer esa transposición.

---

## 2. Escenario A — Índice invertido en memoria

**Clase:** `EscenarioAMemoria` · **Clave CLI:** `--escenario A` *(por omisión)*

### Cómo funciona

Se mantiene una estructura `dict[token][archivo] = frecuencia` en RAM. Cada
documento procesado la actualiza. Al terminar, se ordenan las claves y se
escribe.

```
documento 1 ─┐
documento 2 ─┤──> dict{ privacy: {001:12, 002:7},
documento 3 ─┤         internet:{001: 4} }      ──> sorted() ──> escritura
   ...      ─┘            (todo en RAM)
```

### Complejidad

| Recurso | Costo |
|---|---|
| Tiempo | O(T) para acumular + O(V log V) para ordenar los tokens |
| Memoria | **O(V + P)** — todo el índice vive en RAM |
| Disco adicional | ninguno |

donde T = ocurrencias totales, V = tokens únicos, P = registros de posting.

### Ventajas
- El más rápido de los tres: una sola estructura, sin serialización intermedia.
- El más simple de leer y mantener (≈15 líneas de lógica real).
- Los diccionarios de Python preservan el orden de inserción, así que el **orden
  de primera aparición sale gratis** — es el único escenario que soporta
  `--orden aparicion`.

### Desventajas
- **La memoria crece con el producto tokens × documentos.** Medido con
  `tracemalloc` sobre esta colección: **37.8 MB** de estructura viva, con un pico
  de 47.2 MB. Con una colección cien veces mayor dejaría de caber.
- Si el proceso se interrumpe, se pierde todo el trabajo.

### Cuándo elegirlo
Colecciones que caben cómodamente en RAM. **Es el escenario elegido para esta
entrega:** 505 documentos son holgadamente manejables y el costo de las
alternativas no se justifica.

---

## 3. Escenario B — Dos pasadas con ordenamiento externo

**Clase:** `EscenarioBOrdenExterno` · **Clave CLI:** `--escenario B`

### Cómo funciona

**Pasada 1 (dispersión).** Las ternas se acumulan en un búfer de tamaño fijo. Cuando
el búfer se llena, se ordena y se vuelca a un archivo temporal. Cada archivo
temporal queda internamente ordenado; el conjunto, no.

**Pasada 2 (mezcla).** Los bloques se mezclan con `heapq.merge`, que mantiene en
memoria solo un registro por bloque abierto. La salida de la mezcla está
globalmente ordenada, así que los registros de cada token llegan contiguos y se
pueden escribir en flujo.

```
ternas ──> búfer (200k) ──> bloque_0000.tsv (ordenado)
                       ──> bloque_0001.tsv (ordenado)
                       ──> bloque_0002.tsv (ordenado)
                              │
                              └──> heapq.merge ──> flujo ordenado ──> escritura
                                   (memoria O(k))
```

Es el algoritmo clásico de *ordenamiento por mezcla externa*, el mismo que usan
`sort` de Unix y los indexadores de producción (SPIMI / BSBI).

### Complejidad

| Recurso | Costo |
|---|---|
| Tiempo | O(T log B) por bloque + O(T log k) en la mezcla |
| Memoria | **O(B + k)** — B = tamaño de bloque, k = número de bloques |
| Disco adicional | O(T) temporal, liberado al cerrar |

### Ventajas
- **La memoria no depende del tamaño de la colección**, sino del tamaño de bloque
  elegido. Es el único de los tres que indexa una colección más grande que la RAM.
- `tamano_bloque` es una perilla explícita para negociar memoria contra E/S.
- Tolerante a colecciones de crecimiento imprevisible.

### Desventajas
- El más lento de los tres en esta colección: paga serialización, escritura y
  relectura de todas las ternas (**+10 % de tiempo total** frente a A).
- Más código y más puntos de falla (archivos temporales, limpieza).
- **No puede producir el orden de primera aparición** sin mantener un mapa global
  token → rango, que es exactamente la estructura en memoria que este escenario
  busca evitar. La limitación es inherente, no un defecto (registrada como DT-02).

### Cuándo elegirlo
Cuando la colección no cabe en memoria, o cuando no se sabe cuánto va a crecer.

---

## 4. Escenario C — Acumulación en SQLite

**Clase:** `EscenarioCSQLite` · **Clave CLI:** `--escenario C`

### Cómo funciona

Las ternas se insertan en una tabla `ocurrencia(token, archivo, frecuencia)`. Al
terminar la inserción se crea el índice y se recuperan las filas con
`ORDER BY token, archivo`; el motor se encarga del ordenamiento.

```
ternas ──> INSERT en ocurrencia ──> CREATE INDEX ──> SELECT ... ORDER BY ──> escritura
                (SQLite)              (B-tree)         (cursor en flujo)
```

**Detalle de implementación:** el índice se crea **después** de insertar, no antes.
Crearlo antes obliga a SQLite a mantener el B-tree en cada `INSERT` y
aproximadamente duplica el tiempo de la carga.

### Complejidad

| Recurso | Costo |
|---|---|
| Tiempo | O(T) inserción + O(T log T) construcción del índice |
| Memoria | O(caché de páginas) — configurable, no proporcional a la colección |
| Disco adicional | O(T) persistente (o en memoria si se usa `:memory:`) |

### Ventajas
- **El índice queda persistido y consultable con SQL.** Permite preguntas que los
  archivos planos no responden sin código nuevo: *¿qué tokens aparecen en más de
  100 documentos?*, *¿qué comparten dos documentos?*
- Tolera reinicios: si el proceso muere, lo insertado sigue ahí.
- Delega la corrección del ordenamiento a un motor probado por millones de usuarios.
- `sqlite3` es parte de la biblioteca estándar: cero dependencias nuevas.

### Desventajas
- Paga el costo del B-tree y de la capa SQL (**+9 % de tiempo total** frente a A).
- Introduce un componente externo que hay que entender para depurar.
- Requiere desactivar `journal_mode` y `synchronous` para ser competitivo, lo que
  sacrifica las garantías de durabilidad que justificaban usar una base de datos.

### Cuándo elegirlo
Cuando el índice va a consultarse de formas que no se conocen de antemano, o
cuando se necesita que sobreviva al proceso que lo creó.

---

## 5. Comparativa medida

Corpus: 505 archivos HTML, 13 MB, 89,237 tokens únicos, 311,531 registros de posting.
Medición con `python src/a7_indexador.py --corpus Files --comparar`.

| Escenario | Tiempo total | Tiempo archivos | Sobrecosto vs. A | Memoria | Soporta `aparicion` |
|---|---|---|---|---|---|
| **A** — memoria | **6.14 s** | 5.83 s | — | O(V + P) | Sí |
| **B** — orden externo | 6.77 s | 6.28 s | +10.2 % | O(bloque) | No |
| **C** — SQLite | 6.72 s | 5.90 s | +9.4 % | O(caché) | No |

**Salida:** los tres escenarios producen diccionario y posting **idénticos byte a
byte**. Esto no es una afirmación de confianza: lo verifica la prueba
`test_los_tres_escenarios_producen_la_misma_salida` y el modo `--comparar`, que
falla con código de salida distinto de cero si alguno divergiera.

### Lectura de los números

El dato más revelador es que la diferencia entre los tres escenarios es de apenas
un 10 %. La razón está en el desglose por fase del log: **la lectura y
tokenización de los HTML consume el 96.5 % del tiempo total**. El ordenamiento del
índice y la escritura de los dos archivos —lo único que distingue a los tres
escenarios— pesa **3.4 %** (0.21 s de 6.33 s).

> **Conclusión de ingeniería:** optimizar la estrategia de posting en esta
> colección sería optimizar el 3.4 % del problema. El cuello de botella real es el
> parseo de HTML con BeautifulSoup. Elegir el escenario A no es solo elegir el más
> rápido: es reconocer que aquí la simplicidad no cuesta rendimiento, y que la
> optimización que de verdad importaría es cambiar el parser, no la estructura del
> índice.

---

## 6. Decisión del equipo

| | |
|---|---|
| **Escenario adoptado para la entrega** | **A — Índice invertido en memoria** |
| **Razón** | La colección cabe holgadamente en RAM; es el más rápido, el más simple y el único que reproduce el orden de la figura del enunciado. |
| **Alternativa si la colección crece** | **B** — ya implementado y probado; el cambio es un solo argumento de línea de comandos. |
| **Alternativa si el índice debe consultarse con SQL** | **C** — ya implementado; deja la base en disco. |

El valor de haber implementado los tres no es el 10 % de diferencia: es que el
cambio de estrategia ante un corpus mayor cuesta un argumento de CLI en lugar de
una reescritura, y que la equivalencia de salidas está respaldada por una prueba
automatizada.

---

## 7. Escenarios de validación (pruebas sobre el ejemplo del enunciado)

Más allá de los tres escenarios de *construcción*, el equipo definió tres
escenarios de *validación* sobre el corpus de demostración `demo/corpus_figura/`,
construido para reproducir exactamente la figura del enunciado.

### Validación 1 — El token `perro` devuelve los documentos esperados

```
$ python src/a7_indexador.py --salida demo/salida_figura --consultar perro

TOKEN: perro
  Documentos            : 4
  Posicion en el posting: 0
  Frecuencia total      : 16
  Registros leidos del posting:
    [      0] 004.html            2
    [      1] 009.html            2
    [      2] 412.html            4
    [      3] 444.html            8
```

Cumple el ejemplo literal del enunciado: *«el token perro debe entregar como
resultado los documentos 004, 009, 412 y 444»*.
Prueba: `test_figura_token_perro_devuelve_los_cuatro_documentos`.

### Validación 2 — La cadena de posiciones es acumulativa

Diccionario generado con `--orden aparicion`:

| TOKEN | NUM_DOCS | POS_POSTING | Verificación |
|---|---|---|---|
| perro | 4 | 0 | primer token → 0 |
| gato | 2 | 4 | 0 + 4 |
| pato | 3 | 6 | 4 + 2 |
| canario | 1 | 9 | 6 + 3 |

Reproduce la aritmética del enunciado, incluido el `6 + 3 = 9` de la última
figura. Prueba: `test_figura_cadena_de_offsets_es_acumulativa`.

### Validación 3 — Casos límite

| Caso | Comportamiento esperado | Prueba |
|---|---|---|
| Token inexistente (`elefante`) | 0 documentos, sin excepción | `test_token_inexistente` |
| Token en mayúsculas (`PERRO`) | Mismo resultado que minúsculas | `test_consulta_es_insensible_a_mayusculas` |
| Escenario B con bloques de 3 ternas | Mezcla de varios bloques, resultado correcto | `test_escenario_b_con_bloques_pequenos_sigue_siendo_correcto` |
| Escenario C con base en disco | Base persistida y consultable con SQL | `test_escenario_c_persiste_la_base` |

---

## 8. Invariantes verificadas automáticamente

`IndiceInvertido.verificar_integridad()` comprueba, al final de cada corrida, que:

1. El diccionario está en orden alfabético ascendente *(cuando se usa ese orden)*.
2. La cadena de offsets es acumulativa y sin huecos: `pos(t₍ᵢ₊₁₎) = pos(tᵢ) + n(tᵢ)`.
3. El número de registros del posting es exactamente la suma de la columna `NUM_DOCS`.
4. Ningún token declara cero documentos.
5. Ningún token repite el mismo documento en su bloque de posting.

Si alguna falla, el programa lo reporta y termina con código de salida 1.
