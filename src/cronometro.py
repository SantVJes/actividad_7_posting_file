"""
cronometro.py
=============
Medicion de tiempos y generacion del archivo log a7_<matricula>.txt.

Se usa time.perf_counter() -- reloj monotono de alta resolucion -- porque
time.time() puede retroceder si el sistema ajusta la hora y arruinaria una
medicion.

Se cronometran tres niveles:
    1. Por archivo: lectura + extraccion de texto + tokenizacion + conteo.
    2. Por fase:    procesamiento de archivos, construccion/ordenamiento del
                    indice y escritura de los dos archivos de salida.
    3. Total:       todo el proceso de principio a fin.
"""

from __future__ import annotations

import platform
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class MedicionArchivo:
    """Tiempo y cifras de un unico archivo del corpus."""

    numero: int
    archivo: str
    bytes_leidos: int
    tokens_totales: int
    tokens_unicos: int
    segundos: float


@dataclass
class Cronometro:
    """Acumula las mediciones de una corrida completa."""

    escenario: str = ""
    carpeta_corpus: str = ""
    mediciones: list[MedicionArchivo] = field(default_factory=list)
    fases: dict[str, float] = field(default_factory=dict)
    inicio: float = 0.0
    total: float = 0.0
    sello_tiempo: str = ""

    def arrancar(self) -> None:
        self.inicio = time.perf_counter()
        self.sello_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def detener(self) -> None:
        self.total = time.perf_counter() - self.inicio

    @contextmanager
    def fase(self, nombre: str) -> Iterator[None]:
        """Cronometra un bloque completo del proceso.

        Uso:
            with crono.fase("procesamiento de archivos"):
                ...
        """
        comienzo = time.perf_counter()
        try:
            yield
        finally:
            self.fases[nombre] = self.fases.get(nombre, 0.0) + (
                time.perf_counter() - comienzo
            )

    def registrar_archivo(self, medicion: MedicionArchivo) -> None:
        self.mediciones.append(medicion)

    # --- Estadisticas derivadas -------------------------------------------
    @property
    def tiempo_archivos(self) -> float:
        return sum(m.segundos for m in self.mediciones)

    @property
    def promedio_por_archivo(self) -> float:
        return self.tiempo_archivos / len(self.mediciones) if self.mediciones else 0.0

    @property
    def mas_lento(self) -> MedicionArchivo | None:
        return max(self.mediciones, key=lambda m: m.segundos, default=None)

    @property
    def mas_rapido(self) -> MedicionArchivo | None:
        return min(self.mediciones, key=lambda m: m.segundos, default=None)

    @property
    def tokens_totales(self) -> int:
        return sum(m.tokens_totales for m in self.mediciones)

    @property
    def bytes_totales(self) -> int:
        return sum(m.bytes_leidos for m in self.mediciones)


def _linea(caracter: str = "=", ancho: int = 78) -> str:
    return caracter * ancho


def escribir_log(
    crono: Cronometro,
    ruta_log: Path,
    matricula: str,
    alumno: str,
    resumen_indice: dict[str, int],
) -> Path:
    """Genera el archivo log con el detalle por archivo y los totales."""
    ruta_log.parent.mkdir(parents=True, exist_ok=True)

    with ruta_log.open("w", encoding="utf-8", newline="\n") as log:
        # --- Encabezado ---------------------------------------------------
        log.write(_linea("=") + "\n")
        log.write("ACTIVIDAD 7 - CREACION DEL ARCHIVO DE POSTING Y DICCIONARIO\n")
        log.write("LOG DE MEDICION DE TIEMPOS\n")
        log.write(_linea("=") + "\n")
        log.write(f"Alumno            : {alumno}\n")
        log.write(f"Matricula         : {matricula}\n")
        log.write(f"Fecha y hora      : {crono.sello_tiempo}\n")
        log.write(f"Escenario usado   : {crono.escenario}\n")
        log.write(f"Carpeta del corpus: {crono.carpeta_corpus}\n")
        log.write(f"Python            : {sys.version.split()[0]}\n")
        log.write(f"Plataforma        : {platform.platform()}\n")
        log.write(_linea("=") + "\n\n")

        # --- Detalle por archivo -----------------------------------------
        log.write("DETALLE POR ARCHIVO\n")
        log.write(_linea("-") + "\n")
        log.write(
            f"{'#':>4}  {'ARCHIVO':<14} {'BYTES':>9} {'TOKENS':>8} "
            f"{'UNICOS':>7} {'TIEMPO (s)':>12}\n"
        )
        log.write(_linea("-") + "\n")
        for m in crono.mediciones:
            log.write(
                f"{m.numero:>4}  {m.archivo:<14} {m.bytes_leidos:>9,} "
                f"{m.tokens_totales:>8,} {m.tokens_unicos:>7,} {m.segundos:>12.6f}\n"
            )
        log.write(_linea("-") + "\n\n")

        # --- Resumen de tiempos ------------------------------------------
        log.write("RESUMEN DE TIEMPOS\n")
        log.write(_linea("-") + "\n")
        log.write(f"Archivos procesados                 : {len(crono.mediciones):>12,}\n")
        log.write(f"Bytes leidos                        : {crono.bytes_totales:>12,}\n")
        log.write(f"Tokens indexados (con repeticiones) : {crono.tokens_totales:>12,}\n")
        log.write(
            f"Tiempo sumado de los archivos       : {crono.tiempo_archivos:>12.6f} s\n"
        )
        log.write(
            f"Tiempo promedio por archivo         : {crono.promedio_por_archivo:>12.6f} s\n"
        )
        if crono.mas_lento:
            log.write(
                f"Archivo mas lento                   : "
                f"{crono.mas_lento.archivo} ({crono.mas_lento.segundos:.6f} s)\n"
            )
        if crono.mas_rapido:
            log.write(
                f"Archivo mas rapido                  : "
                f"{crono.mas_rapido.archivo} ({crono.mas_rapido.segundos:.6f} s)\n"
            )
        log.write(_linea("-") + "\n\n")

        # --- Tiempos por fase --------------------------------------------
        log.write("TIEMPO POR FASE DEL PROCESO\n")
        log.write(_linea("-") + "\n")
        for nombre, segundos in crono.fases.items():
            porcentaje = (segundos / crono.total * 100) if crono.total else 0.0
            log.write(f"{nombre:<52} {segundos:>12.6f} s  ({porcentaje:5.2f} %)\n")
        log.write(_linea("-") + "\n")
        log.write(f"{'TIEMPO TOTAL DEL PROCESO':<52} {crono.total:>12.6f} s  (100.00 %)\n")
        log.write(_linea("-") + "\n\n")

        # --- Resumen del indice ------------------------------------------
        log.write("RESUMEN DEL INDICE GENERADO\n")
        log.write(_linea("-") + "\n")
        for clave, valor in resumen_indice.items():
            log.write(f"{clave:<42} {valor:>12,}\n")
        log.write(_linea("=") + "\n")
        log.write("FIN DEL LOG\n")
        log.write(_linea("=") + "\n")

    return ruta_log
