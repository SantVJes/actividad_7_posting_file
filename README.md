# Actividad 7 — Archivo de posting y diccionario de tres columnas

Indexador invertido sobre una colección de 505 documentos HTML. Genera un
**archivo diccionario** de tres columnas y un **archivo de posting** de dos
columnas, implementa **tres escenarios** alternativos para construir el posting, y
**cronometra** cada archivo y el proceso completo en un log `a7_<matrícula>.txt`.

**Alumno:** Jesús Santiago Velasco · **Universidad Tecmilenio** · Sprint 7

---

## Inicio rápido

```bash
# 1. Dependencias
pip install -r requirements.txt

# 2. Construir el índice (escenario A, por omisión)
python src/a7_indexador.py --corpus Files --matricula TU_MATRICULA

# 3. Consultar un token
python src/a7_indexador.py --salida output --consultar encryption privacy

# 4. Comparar los tres escenarios
python src/a7_indexador.py --corpus Files --matricula TU_MATRICULA --comparar

# 5. Pruebas
python tests/test_escenarios.py
python tests/verificar_contra_fuerza_bruta.py --muestra 300
```

### Reproducir la figura del enunciado

```bash
python src/a7_indexador.py --corpus demo/corpus_figura \
    --salida demo/salida_figura --orden aparicion --matricula DEMO
cat demo/salida_figura/diccionario.txt
```

```
TOKEN     NUM_DOCS  POS_POSTING
perro     4         0
gato      2         4
pato      3         6
canario   1         9
```

---

## Qué genera

| Archivo | Columnas | Contenido |
|---|---|---|
| `output/diccionario.txt` | `TOKEN` · `NUM_DOCS` · `POS_POSTING` | 89,237 tokens únicos |
| `output/posting.txt` | `ARCHIVO` · `FRECUENCIA` | 311,531 registros |
| `output/a7_<matrícula>.txt` | — | Log con el tiempo de cada uno de los 505 archivos y del proceso completo |

### Regla de las posiciones

```
pos(t₀)     = 0
pos(tᵢ₊₁)   = pos(tᵢ) + num_docs(tᵢ)
```

Las posiciones se cuentan en **registros, base 0**, sin contar la fila de
encabezado. Es la aritmética del enunciado: `perro` 4 docs → 0, `gato` 2 docs → 4,
`pato` 3 docs → 6, siguiente → 9.

---

## Los tres escenarios

| Clave | Escenario | Memoria | Tiempo | Cuándo usarlo |
|---|---|---|---|---|
| `A` | Índice invertido en memoria | O(V+P) — 37.8 MB | **6.14 s** | Por omisión; la colección cabe en RAM |
| `B` | Dos pasadas con orden externo | O(tamaño de bloque) | 6.77 s | La colección **no** cabe en RAM |
| `C` | Acumulación en SQLite | O(caché) | 6.72 s | El índice debe consultarse con SQL |

Los tres producen salidas **idénticas byte a byte**; lo verifica
`--comparar` y una prueba automatizada. Análisis completo en
[`docs/escenarios_posting.md`](docs/escenarios_posting.md).

---

## Opciones de línea de comandos

```
--corpus RUTA       carpeta con los archivos HTML (por omisión: Files)
--salida RUTA       carpeta de salida (por omisión: output)
--escenario {A,B,C} estrategia de construcción del posting (por omisión: A)
--orden {alfabetico,aparicion}
                    orden de las filas del diccionario. 'aparicion' solo en el
                    escenario A; reproduce el orden de la figura del enunciado
--matricula TEXTO   nombra el log como a7_<matrícula>.txt
--alumno TEXTO      nombre que aparece en el log
--comparar          corre los tres escenarios y verifica que coincidan
--consultar TOKEN...  consulta tokens sobre un índice ya construido
```

---

## Estructura del repositorio

```
actividad_7_posting_file/
├── Files/                      505 documentos HTML de la colección
├── src/
│   ├── a7_indexador.py         programa principal y CLI
│   ├── extraccion.py           HTML → tokens normalizados
│   ├── stopwords.py            palabras vacías (español + inglés)
│   ├── estrategias.py          LOS TRES ESCENARIOS
│   ├── escritura.py            diccionario + posting y cálculo de offsets
│   ├── consulta.py             token → documentos, y verificación de integridad
│   └── cronometro.py           medición de tiempos y generación del log
├── tests/
│   ├── test_escenarios.py      17 pruebas (unidad, integración, equivalencia)
│   └── verificar_contra_fuerza_bruta.py   verificación independiente
├── demo/
│   ├── corpus_figura/          4 HTML que reproducen la figura del enunciado
│   └── salida_figura/          salida correspondiente
├── docs/
│   ├── REPORTE.md              ← REPORTE DE LA ACTIVIDAD
│   ├── minuta_sprint.md        minuta de Sprint Review y Sprint Planning
│   ├── historias_usuario.md    6 historias con criterios Gherkin
│   └── escenarios_posting.md   análisis de los tres escenarios
└── output/                     diccionario, posting y log generados
```

---

## Resultados medidos

| Métrica | Valor |
|---|---|
| Archivos procesados | 505 (11.9 MB) |
| Tokens únicos | 89,237 |
| Registros de posting | 311,531 |
| Ocurrencias totales | 637,372 |
| Tiempo total | 6.198 s |
| Promedio por archivo | 11.75 ms |
| Lectura + tokenización | 95.97 % del tiempo |
| Ordenamiento + escritura | 3.83 % del tiempo |

El hallazgo que cambió la prioridad del siguiente sprint: **el parseo de HTML es el
96 % del costo**, no la construcción del índice. Detalles en
[`docs/REPORTE.md`](docs/REPORTE.md).

---

## Verificación

Tres niveles independientes:

1. **Invariantes en cada corrida** — orden, cadena de offsets, consistencia
   diccionario↔posting, sin documentos duplicados. Si algo falla, el programa
   termina con código 1.
2. **17 pruebas automatizadas** — tokenización, reproducción de la figura del
   enunciado, equivalencia de los tres escenarios.
3. **Recálculo por fuerza bruta** — releer y retokenizar los 505 archivos desde
   cero y comparar; contrastado además contra `grep`.

## Requisitos

- Python 3.11 o superior
- `beautifulsoup4` y `lxml` (ver `requirements.txt`)

`sqlite3` (escenario C) forma parte de la biblioteca estándar.
