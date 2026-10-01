#!/usr/bin/env python3
"""
a7_indexador.py
===============
Programa principal de la Actividad 7.

Recorre una coleccion de archivos HTML y genera:

    1. output/diccionario.txt  -- tres columnas:
           TOKEN | NUM_DOCS | POS_POSTING
    2. output/posting.txt      -- dos columnas:
           ARCHIVO | FRECUENCIA
    3. output/a7_<matricula>.txt -- log con el tiempo de cada archivo y del
           proceso completo.

La construccion del posting puede hacerse con cualquiera de los tres
escenarios implementados (ver src/estrategias.py y
docs/escenarios_posting.md):

    A  indice invertido en memoria
    B  dos pasadas con ordenamiento externo en disco
    C  acumulacion en SQLite

Ejemplos de uso
---------------
    # Corrida normal con el escenario A
    python src/a7_indexador.py --corpus Files --matricula 1234567

    # Comparar los tres escenarios y verificar que dan la misma salida
    python src/a7_indexador.py --corpus Files --matricula 1234567 --comparar

    # Consultar tokens despues de construir el indice
    python src/a7_indexador.py --corpus Files --consultar perro gato pato
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

# Permite ejecutar el script directamente (python src/a7_indexador.py)
# sin necesidad de instalar el paquete ni fijar PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from consulta import IndiceInvertido                     # noqa: E402
from cronometro import Cronometro, MedicionArchivo, escribir_log  # noqa: E402
from escritura import escribir_indice                    # noqa: E402
from estrategias import ESCENARIOS, crear_escenario      # noqa: E402
from extraccion import extraer_texto, leer_html, tokenizar  # noqa: E402

ALUMNO_POR_DEFECTO = "Jesus Santiago Velasco"
EXTENSIONES = (".html", ".htm")


# ---------------------------------------------------------------------------
# Construccion del indice
# ---------------------------------------------------------------------------
def listar_documentos(carpeta: Path) -> list[Path]:
    """Devuelve los documentos del corpus en orden ascendente de nombre."""
    if not carpeta.is_dir():
        raise SystemExit(f"ERROR: la carpeta del corpus no existe: {carpeta}")
    documentos = sorted(
        ruta
        for ruta in carpeta.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES
    )
    if not documentos:
        raise SystemExit(f"ERROR: no se encontraron archivos HTML en {carpeta}")
    return documentos


def construir_indice(
    carpeta: Path,
    clave_escenario: str,
    ruta_diccionario: Path,
    ruta_posting: Path,
    orden: str = "alfabetico",
    verboso: bool = True,
) -> tuple[Cronometro, dict[str, int]]:
    """Procesa el corpus completo y escribe diccionario y posting.

    Devuelve el cronometro con todas las mediciones y un resumen del indice.
    """
    documentos = listar_documentos(carpeta)
    escenario = crear_escenario(clave_escenario, orden=orden)

    crono = Cronometro(
        escenario=f"{clave_escenario.upper()} - {escenario.descripcion} "
        f"[orden: {orden}]",
        carpeta_corpus=str(carpeta.resolve()),
    )
    crono.arrancar()

    escenario.iniciar()
    try:
        # --- Fase 1: procesamiento de los archivos del corpus -------------
        with crono.fase("1. Procesamiento de archivos (lectura+tokenizacion)"):
            for numero, ruta in enumerate(documentos, start=1):
                comienzo = time.perf_counter()

                html = leer_html(ruta)
                tokens = tokenizar(extraer_texto(html))
                frecuencias = Counter(tokens)
                escenario.agregar_documento(ruta.name, dict(frecuencias))

                transcurrido = time.perf_counter() - comienzo

                crono.registrar_archivo(
                    MedicionArchivo(
                        numero=numero,
                        archivo=ruta.name,
                        bytes_leidos=ruta.stat().st_size,
                        tokens_totales=len(tokens),
                        tokens_unicos=len(frecuencias),
                        segundos=transcurrido,
                    )
                )

                if verboso and (numero % 100 == 0 or numero == len(documentos)):
                    print(
                        f"  procesados {numero:>4}/{len(documentos)} archivos",
                        flush=True,
                    )

        # --- Fases 2 y 3: ordenamiento y escritura ------------------------
        # El generador `recorrer()` ordena de forma perezosa, asi que su
        # costo se contabiliza dentro de la fase de escritura; por eso las
        # dos fases se cronometran juntas y se reporta como tal.
        with crono.fase("2. Ordenamiento del indice + escritura de salidas"):
            resumen = escribir_indice(
                escenario.recorrer(), ruta_diccionario, ruta_posting
            )
    finally:
        escenario.cerrar()

    crono.detener()

    resumen_indice = {
        "Tokens unicos en el diccionario": resumen.tokens_unicos,
        "Registros en el archivo de posting": resumen.registros_posting,
        "Ocurrencias totales de tokens": resumen.ocurrencias_totales,
    }
    return crono, resumen_indice


# ---------------------------------------------------------------------------
# Modos de ejecucion
# ---------------------------------------------------------------------------
def modo_normal(argumentos: argparse.Namespace) -> None:
    """Construye el indice con un escenario y escribe el log."""
    salida = Path(argumentos.salida)
    ruta_diccionario = salida / "diccionario.txt"
    ruta_posting = salida / "posting.txt"

    print(f"Escenario   : {argumentos.escenario.upper()}")
    print(f"Corpus      : {argumentos.corpus}")
    print("Procesando...")

    crono, resumen_indice = construir_indice(
        Path(argumentos.corpus),
        argumentos.escenario,
        ruta_diccionario,
        ruta_posting,
        orden=argumentos.orden,
    )

    ruta_log = salida / f"a7_{argumentos.matricula}.txt"
    escribir_log(
        crono,
        ruta_log,
        matricula=argumentos.matricula,
        alumno=argumentos.alumno,
        resumen_indice=resumen_indice,
    )

    print()
    print(f"Diccionario : {ruta_diccionario}  "
          f"({resumen_indice['Tokens unicos en el diccionario']:,} tokens)")
    print(f"Posting     : {ruta_posting}  "
          f"({resumen_indice['Registros en el archivo de posting']:,} registros)")
    print(f"Log         : {ruta_log}")
    print(f"Tiempo total: {crono.total:.4f} s "
          f"({crono.promedio_por_archivo * 1000:.2f} ms promedio por archivo)")

    # Verificacion de integridad inmediata: si el indice quedo mal formado,
    # se entera aqui y no al momento de consultar.
    indice = IndiceInvertido(ruta_diccionario, ruta_posting)
    problemas = indice.verificar_integridad(
        exigir_orden_alfabetico=(argumentos.orden == "alfabetico")
    )
    if problemas:
        print("\nADVERTENCIA: el indice presenta problemas de integridad:")
        for problema in problemas[:10]:
            print(f"  - {problema}")
        raise SystemExit(1)
    print("Integridad  : OK (offsets acumulativos y posting consistente)")


def modo_comparar(argumentos: argparse.Namespace) -> None:
    """Corre los tres escenarios y verifica que produzcan la misma salida."""
    salida = Path(argumentos.salida)
    comparativa = salida / "comparativa"
    comparativa.mkdir(parents=True, exist_ok=True)

    resultados: list[tuple[str, float, float, dict[str, int]]] = []
    huellas: dict[str, tuple[str, str]] = {}

    for clave in sorted(ESCENARIOS):
        print(f"\n=== Escenario {clave} ===")
        ruta_diccionario = comparativa / f"diccionario_{clave}.txt"
        ruta_posting = comparativa / f"posting_{clave}.txt"

        crono, resumen_indice = construir_indice(
            Path(argumentos.corpus),
            clave,
            ruta_diccionario,
            ruta_posting,
            orden="alfabetico",   # el unico orden que los tres comparten
        )
        resultados.append(
            (clave, crono.total, crono.tiempo_archivos, resumen_indice)
        )
        huellas[clave] = (
            ruta_diccionario.read_text(encoding="utf-8"),
            ruta_posting.read_text(encoding="utf-8"),
        )
        print(f"  tiempo total: {crono.total:.4f} s")

    # --- Verificacion: los tres escenarios deben coincidir ----------------
    print("\n" + "=" * 70)
    print("COMPARATIVA DE ESCENARIOS")
    print("=" * 70)
    print(f"{'ESC':<5} {'TOTAL (s)':>11} {'ARCHIVOS (s)':>13} "
          f"{'TOKENS':>9} {'REGISTROS':>11}")
    print("-" * 70)
    for clave, total, archivos, resumen_indice in resultados:
        print(
            f"{clave:<5} {total:>11.4f} {archivos:>13.4f} "
            f"{resumen_indice['Tokens unicos en el diccionario']:>9,} "
            f"{resumen_indice['Registros en el archivo de posting']:>11,}"
        )
    print("-" * 70)

    referencia = huellas["A"]
    todos_iguales = True
    for clave, contenido in huellas.items():
        iguales = contenido == referencia
        todos_iguales &= iguales
        estado = "identico a A" if iguales else "DIFERENTE DE A"
        print(f"Escenario {clave}: {estado}")

    if not todos_iguales:
        raise SystemExit("ERROR: los escenarios no producen la misma salida.")
    print("\nOK: los tres escenarios producen salidas identicas byte a byte.")

    # Se conserva la salida del escenario elegido como salida oficial.
    elegido = argumentos.escenario.upper()
    (salida / "diccionario.txt").write_text(huellas[elegido][0], encoding="utf-8")
    (salida / "posting.txt").write_text(huellas[elegido][1], encoding="utf-8")
    print(f"Salida oficial tomada del escenario {elegido}.")


def modo_consultar(argumentos: argparse.Namespace) -> None:
    """Consulta tokens sobre un indice ya construido."""
    salida = Path(argumentos.salida)
    ruta_diccionario = salida / "diccionario.txt"
    ruta_posting = salida / "posting.txt"

    if not ruta_diccionario.exists() or not ruta_posting.exists():
        raise SystemExit(
            "ERROR: no hay indice en "
            f"{salida}. Ejecuta primero el programa sin --consultar."
        )

    indice = IndiceInvertido(ruta_diccionario, ruta_posting)
    print(f"Indice cargado: {indice.total_tokens:,} tokens, "
          f"{indice.total_registros:,} registros de posting.\n")

    for token in argumentos.consultar:
        resultado = indice.consultar(token)
        print("=" * 70)
        print(f"TOKEN: {token}")
        print("=" * 70)
        if resultado.numero_documentos == 0:
            print("  No aparece en la coleccion.\n")
            continue
        print(f"  Documentos            : {resultado.numero_documentos}")
        print(f"  Posicion en el posting: {resultado.posicion_posting}")
        print(f"  Frecuencia total      : {resultado.frecuencia_total}")
        print("  Registros leidos del posting:")
        for desplazamiento, (archivo, frecuencia) in enumerate(resultado.documentos):
            posicion = resultado.posicion_posting + desplazamiento
            print(f"    [{posicion:>7}] {archivo:<14} {frecuencia:>6}")
        print(f"\n  {resultado.describir()}\n")


# ---------------------------------------------------------------------------
# Interfaz de linea de comandos
# ---------------------------------------------------------------------------
def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Actividad 7: genera el archivo diccionario (3 columnas) y el "
            "archivo de posting (2 columnas) a partir de una coleccion HTML, "
            "midiendo el tiempo de cada archivo y del proceso completo."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--corpus",
        default="Files",
        help="carpeta con los archivos HTML (por omision: Files)",
    )
    parser.add_argument(
        "--salida",
        default="output",
        help="carpeta donde se escriben diccionario, posting y log",
    )
    parser.add_argument(
        "--escenario",
        default="A",
        choices=sorted(ESCENARIOS) + [c.lower() for c in ESCENARIOS],
        help="escenario de construccion del posting: A, B o C (por omision: A)",
    )
    parser.add_argument(
        "--matricula",
        default="MATRICULA",
        help="matricula del alumno; nombra el log como a7_<matricula>.txt",
    )
    parser.add_argument(
        "--alumno",
        default=ALUMNO_POR_DEFECTO,
        help="nombre del alumno que aparece en el log",
    )
    parser.add_argument(
        "--orden",
        default="alfabetico",
        choices=("alfabetico", "aparicion"),
        help=(
            "orden de las filas del diccionario: 'alfabetico' (por omision, "
            "soportado por los tres escenarios) o 'aparicion' (orden de "
            "primera aparicion, solo escenario A)"
        ),
    )
    parser.add_argument(
        "--comparar",
        action="store_true",
        help="corre los tres escenarios y verifica que den la misma salida",
    )
    parser.add_argument(
        "--consultar",
        nargs="+",
        metavar="TOKEN",
        help="consulta tokens sobre el indice ya construido y termina",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    argumentos = construir_parser().parse_args(argv)

    if argumentos.consultar:
        modo_consultar(argumentos)
    elif argumentos.comparar:
        modo_comparar(argumentos)
    else:
        modo_normal(argumentos)


if __name__ == "__main__":
    main()
