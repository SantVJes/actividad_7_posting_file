"""
escritura.py
============
Escritura del archivo DICCIONARIO y del archivo POSTING.

Esta capa es comun a los tres escenarios: recibe los grupos ya ordenados
(token -> [(archivo, frecuencia), ...]) y se encarga de la unica parte
delicada del formato -- el calculo del desplazamiento (offset) de cada
token dentro del archivo de posting.

FORMATO DEL DICCIONARIO (tres columnas, separadas por tabulador)
    Columna 1: TOKEN         la palabra indexada
    Columna 2: NUM_DOCS      numero de documentos distintos que la contienen
    Columna 3: POS_POSTING   posicion del PRIMER registro del token en el
                             archivo de posting (base 0)

FORMATO DEL POSTING (dos columnas, separadas por tabulador)
    Columna 1: ARCHIVO       nombre del archivo del corpus
    Columna 2: FRECUENCIA    repeticiones del token dentro de ese archivo

REGLA DE LAS POSICIONES
    La posicion del primer token es 0. La posicion de cada token siguiente
    es la posicion del token anterior mas su numero de documentos:

        pos(t_0)     = 0
        pos(t_{i+1}) = pos(t_i) + num_docs(t_i)

    Esto reproduce exactamente el ejemplo de la actividad:
        Perro -> 4 docs, posicion 0
        Gato  -> 2 docs, posicion 4   (0 + 4)
        Pato  -> 3 docs, posicion 6   (4 + 2)
        ...                      9   (6 + 3)

    Las posiciones se cuentan en REGISTROS (filas de datos), base 0, sin
    contar la fila de encabezado. Es decir, el registro en la posicion 0 es
    la primera fila despues del encabezado.

ORDEN
    Los tokens se escriben en orden alfabetico ascendente y, dentro de cada
    token, los documentos en orden ascendente de nombre de archivo. El
    ejemplo de la actividad usa un orden ilustrativo; aqui se fija un orden
    determinista para que la salida sea reproducible y comparable entre los
    tres escenarios.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from estrategias import Grupo

ENCABEZADO_DICCIONARIO = ("TOKEN", "NUM_DOCS", "POS_POSTING")
ENCABEZADO_POSTING = ("ARCHIVO", "FRECUENCIA")


@dataclass
class ResumenEscritura:
    """Cifras agregadas de la escritura, usadas en el log y en el reporte."""

    tokens_unicos: int = 0
    registros_posting: int = 0
    ocurrencias_totales: int = 0
    ruta_diccionario: Path | None = None
    ruta_posting: Path | None = None


def escribir_indice(
    grupos: Iterable[Grupo],
    ruta_diccionario: Path,
    ruta_posting: Path,
    con_encabezado: bool = True,
) -> ResumenEscritura:
    """Escribe en una sola pasada el diccionario y el archivo de posting.

    Los dos archivos se escriben simultaneamente para que el offset que se
    anota en el diccionario sea, por construccion, el numero de registros
    ya volcados al posting. Asi es imposible que ambos archivos se
    desincronicen.
    """
    ruta_diccionario.parent.mkdir(parents=True, exist_ok=True)
    ruta_posting.parent.mkdir(parents=True, exist_ok=True)

    resumen = ResumenEscritura(
        ruta_diccionario=ruta_diccionario, ruta_posting=ruta_posting
    )
    # Contador de registros ya escritos en el posting == posicion del
    # siguiente registro. Es el offset que necesita el diccionario.
    posicion = 0

    with (
        ruta_diccionario.open("w", encoding="utf-8", newline="\n") as f_dic,
        ruta_posting.open("w", encoding="utf-8", newline="\n") as f_post,
    ):
        if con_encabezado:
            f_dic.write("\t".join(ENCABEZADO_DICCIONARIO) + "\n")
            f_post.write("\t".join(ENCABEZADO_POSTING) + "\n")

        for token, registros in grupos:
            numero_documentos = len(registros)

            # 1) El diccionario apunta a donde EMPEZARAN los registros.
            f_dic.write(f"{token}\t{numero_documentos}\t{posicion}\n")

            # 2) Se escriben los registros de este token en el posting.
            for archivo, frecuencia in registros:
                f_post.write(f"{archivo}\t{frecuencia}\n")
                resumen.ocurrencias_totales += frecuencia

            # 3) El siguiente token arranca despues de estos registros.
            posicion += numero_documentos

            resumen.tokens_unicos += 1
            resumen.registros_posting += numero_documentos

    return resumen
