"""
estrategias.py
==============
Los TRES ESCENARIOS posibles para la creacion del archivo de posting.

Los tres escenarios resuelven el mismo problema -- agrupar los pares
(token, documento, frecuencia) por token y entregarlos en orden -- pero con
compromisos distintos de memoria, disco y tiempo. Los tres son
intercambiables porque implementan la misma interfaz `EstrategiaPosting`
y, por contrato, deben producir salidas identicas byte a byte
(esto se verifica en tests/test_escenarios.py).

    Escenario A - Indice invertido en memoria (diccionario de diccionarios)
        Acumula todo en RAM y ordena al final.
        + Mas rapido, codigo mas simple.
        - La memoria crece con tokens x documentos; no escala a corpus
          que no quepan en RAM.

    Escenario B - Dos pasadas con ordenamiento externo en disco
        Pasada 1: emite ternas (token, archivo, frecuencia) a archivos
        temporales ordenados por bloques. Pasada 2: mezcla los bloques con
        heapq.merge y entrega los grupos en flujo.
        + Memoria acotada por el tamano de bloque, no por el corpus.
        - Mas lento por la E/S y el costo del ordenamiento externo.

    Escenario C - Acumulacion en SQLite (indice persistente y consultable)
        Inserta las ternas en una tabla con indice y las recupera con
        ORDER BY.
        + El indice queda persistido y consultable con SQL; tolera
          reinicios y permite consultas que los archivos planos no.
        - Depende de un motor externo y paga el costo del indice B-tree.

Interfaz comun:
    iniciar()                               -> prepara recursos
    agregar_documento(archivo, frecuencias) -> acumula un documento
    recorrer()                              -> itera (token, [(archivo, frec), ...])
                                               en orden alfabetico de token y,
                                               dentro del token, por nombre de archivo
    cerrar()                                -> libera recursos
"""

from __future__ import annotations

import heapq
import shutil
import sqlite3
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

# Tipo del grupo que consume el escritor: token + lista de (archivo, frecuencia)
Grupo = tuple[str, list[tuple[str, int]]]


class EstrategiaPosting(ABC):
    """Contrato que deben cumplir los tres escenarios."""

    nombre: str = "sin-nombre"
    descripcion: str = ""
    # Ordenes de salida que el escenario sabe producir.
    ordenes_soportados: tuple[str, ...] = ("alfabetico",)

    def iniciar(self) -> None:
        """Prepara los recursos necesarios (opcional)."""

    @abstractmethod
    def agregar_documento(self, archivo: str, frecuencias: dict[str, int]) -> None:
        """Acumula las frecuencias de un documento ya tokenizado."""

    @abstractmethod
    def recorrer(self) -> Iterator[Grupo]:
        """Entrega los grupos token -> [(archivo, frecuencia), ...] ordenados."""

    def cerrar(self) -> None:
        """Libera recursos (opcional)."""


# ---------------------------------------------------------------------------
# ESCENARIO A: indice invertido completo en memoria
# ---------------------------------------------------------------------------
class EscenarioAMemoria(EstrategiaPosting):
    """Diccionario de diccionarios: {token: {archivo: frecuencia}}.

    Es el unico escenario que soporta `orden="aparicion"`, porque los
    diccionarios de Python preservan el orden de insercion: el orden de
    primera aparicion sale gratis. Los escenarios B y C ordenan por clave y
    no tienen esa informacion sin mantener un mapa global token -> rango,
    que es justamente lo que intentan evitar.
    """

    nombre = "A-memoria"
    descripcion = (
        "Indice invertido completo en RAM (diccionario de diccionarios); "
        "ordenamiento al final"
    )
    ordenes_soportados = ("alfabetico", "aparicion")

    def __init__(self, orden: str = "alfabetico") -> None:
        self.orden = orden
        self._indice: dict[str, dict[str, int]] = {}

    def agregar_documento(self, archivo: str, frecuencias: dict[str, int]) -> None:
        for token, frecuencia in frecuencias.items():
            # setdefault evita una busqueda doble en el caso comun.
            self._indice.setdefault(token, {})[archivo] = frecuencia

    def recorrer(self) -> Iterator[Grupo]:
        if self.orden == "aparicion":
            # Orden de primera aparicion, tanto de tokens como de documentos.
            for token, documentos in self._indice.items():
                yield token, list(documentos.items())
        else:
            for token in sorted(self._indice):
                yield token, sorted(self._indice[token].items())

    def cerrar(self) -> None:
        self._indice.clear()


# ---------------------------------------------------------------------------
# ESCENARIO B: dos pasadas con ordenamiento externo
# ---------------------------------------------------------------------------
class EscenarioBOrdenExterno(EstrategiaPosting):
    """Ternas a disco en bloques ordenados y mezcla posterior.

    `tamano_bloque` es el numero de ternas que se mantienen en memoria antes
    de volcarlas ordenadas a un archivo temporal. Es la perilla que acota el
    consumo de RAM independientemente del tamano del corpus.
    """

    nombre = "B-orden-externo"
    descripcion = (
        "Dos pasadas: ternas volcadas a bloques ordenados en disco y "
        "mezcladas con heapq.merge (memoria acotada)"
    )

    def __init__(self, tamano_bloque: int = 200_000) -> None:
        self.tamano_bloque = tamano_bloque
        self._bufer: list[tuple[str, str, int]] = []
        self._bloques: list[Path] = []
        self._directorio: Path | None = None

    def iniciar(self) -> None:
        self._directorio = Path(tempfile.mkdtemp(prefix="a7_posting_"))

    def agregar_documento(self, archivo: str, frecuencias: dict[str, int]) -> None:
        for token, frecuencia in frecuencias.items():
            self._bufer.append((token, archivo, frecuencia))
        if len(self._bufer) >= self.tamano_bloque:
            self._volcar_bloque()

    def _volcar_bloque(self) -> None:
        """Ordena el bufer y lo escribe como un bloque temporal en disco."""
        if not self._bufer or self._directorio is None:
            return
        self._bufer.sort()
        ruta = self._directorio / f"bloque_{len(self._bloques):04d}.tsv"
        with ruta.open("w", encoding="utf-8") as salida:
            for token, archivo, frecuencia in self._bufer:
                salida.write(f"{token}\t{archivo}\t{frecuencia}\n")
        self._bloques.append(ruta)
        self._bufer.clear()

    def recorrer(self) -> Iterator[Grupo]:
        self._volcar_bloque()          # vuelca lo que quedo pendiente
        manejadores = [p.open("r", encoding="utf-8") for p in self._bloques]
        try:
            flujos = (
                ((linea.rstrip("\n").split("\t")) for linea in manejador)
                for manejador in manejadores
            )
            # heapq.merge mezcla k flujos ya ordenados usando O(k) memoria.
            mezcla = heapq.merge(*flujos, key=lambda t: (t[0], t[1]))

            token_actual: str | None = None
            registros: list[tuple[str, int]] = []
            for token, archivo, frecuencia in mezcla:
                if token != token_actual:
                    if token_actual is not None:
                        yield token_actual, registros
                    token_actual, registros = token, []
                registros.append((archivo, int(frecuencia)))
            if token_actual is not None:
                yield token_actual, registros
        finally:
            for manejador in manejadores:
                manejador.close()

    def cerrar(self) -> None:
        if self._directorio and self._directorio.exists():
            shutil.rmtree(self._directorio, ignore_errors=True)
        self._bloques.clear()
        self._bufer.clear()


# ---------------------------------------------------------------------------
# ESCENARIO C: acumulacion en SQLite
# ---------------------------------------------------------------------------
class EscenarioCSQLite(EstrategiaPosting):
    """Tabla (token, archivo, frecuencia) con indice; se lee con ORDER BY.

    Si `ruta_bd` es None se usa una base en memoria; si se indica una ruta,
    el indice queda persistido y consultable con SQL despues de la corrida.
    """

    nombre = "C-sqlite"
    descripcion = (
        "Ternas acumuladas en SQLite con indice; recuperacion con ORDER BY "
        "(indice persistente y consultable)"
    )

    def __init__(self, ruta_bd: Path | None = None) -> None:
        self.ruta_bd = ruta_bd
        self._conexion: sqlite3.Connection | None = None

    def iniciar(self) -> None:
        destino = str(self.ruta_bd) if self.ruta_bd else ":memory:"
        if self.ruta_bd and self.ruta_bd.exists():
            self.ruta_bd.unlink()
        self._conexion = sqlite3.connect(destino)
        # El indice se crea DESPUES de insertar: construirlo antes obliga a
        # SQLite a mantener el B-tree en cada INSERT y duplica el tiempo.
        self._conexion.executescript(
            """
            PRAGMA journal_mode = OFF;
            PRAGMA synchronous = OFF;
            CREATE TABLE ocurrencia (
                token      TEXT    NOT NULL,
                archivo    TEXT    NOT NULL,
                frecuencia INTEGER NOT NULL
            );
            """
        )

    def agregar_documento(self, archivo: str, frecuencias: dict[str, int]) -> None:
        assert self._conexion is not None, "iniciar() no fue invocado"
        self._conexion.executemany(
            "INSERT INTO ocurrencia (token, archivo, frecuencia) VALUES (?, ?, ?)",
            ((token, archivo, frec) for token, frec in frecuencias.items()),
        )

    def recorrer(self) -> Iterator[Grupo]:
        assert self._conexion is not None, "iniciar() no fue invocado"
        self._conexion.commit()
        self._conexion.execute(
            "CREATE INDEX idx_ocurrencia ON ocurrencia (token, archivo)"
        )
        cursor = self._conexion.execute(
            "SELECT token, archivo, frecuencia FROM ocurrencia "
            "ORDER BY token ASC, archivo ASC"
        )
        token_actual: str | None = None
        registros: list[tuple[str, int]] = []
        for token, archivo, frecuencia in cursor:
            if token != token_actual:
                if token_actual is not None:
                    yield token_actual, registros
                token_actual, registros = token, []
            registros.append((archivo, int(frecuencia)))
        if token_actual is not None:
            yield token_actual, registros

    def cerrar(self) -> None:
        if self._conexion is not None:
            self._conexion.close()
            self._conexion = None


# Registro de escenarios disponibles por nombre corto de linea de comandos.
ESCENARIOS: dict[str, type[EstrategiaPosting]] = {
    "A": EscenarioAMemoria,
    "B": EscenarioBOrdenExterno,
    "C": EscenarioCSQLite,
}


def crear_escenario(clave: str, orden: str = "alfabetico") -> EstrategiaPosting:
    """Fabrica el escenario a partir de su clave ('A', 'B' o 'C').

    Falla de forma explicita si se pide un orden que el escenario no sabe
    producir, en lugar de entregar una salida silenciosamente distinta.
    """
    clave = clave.strip().upper()
    if clave not in ESCENARIOS:
        disponibles = ", ".join(sorted(ESCENARIOS))
        raise ValueError(f"Escenario '{clave}' desconocido. Disponibles: {disponibles}")

    clase = ESCENARIOS[clave]
    if orden not in clase.ordenes_soportados:
        soportados = ", ".join(clase.ordenes_soportados)
        raise ValueError(
            f"El escenario {clave} no soporta el orden '{orden}'. "
            f"Ordenes soportados: {soportados}."
        )

    if orden == "aparicion":
        return clase(orden=orden)       # type: ignore[call-arg]
    return clase()
