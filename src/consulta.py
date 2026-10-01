"""
consulta.py
===========
Consulta del indice ya construido: token -> documentos.

Es la prueba de que el diccionario y el posting estan bien formados. El
flujo es exactamente el que describe la actividad:

    1. Se busca el token en el DICCIONARIO y se leen sus dos numeros:
       cuantos documentos lo contienen (n) y en que posicion del POSTING
       empieza su primer registro (p).
    2. Se leen n registros del POSTING a partir de la posicion p.
    3. Esos n registros son los documentos que contienen el token, con su
       frecuencia.

Nunca se recorre el posting completo: el diccionario da el salto directo.

Ejemplo de la actividad:
    perro -> 4 documentos, posicion 0
          -> se leen 4 registros desde la posicion 0 del posting
          -> 004.html, 009.html, 412.html, 444.html
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from escritura import ENCABEZADO_DICCIONARIO, ENCABEZADO_POSTING


@dataclass
class EntradaDiccionario:
    """Una fila del diccionario."""

    token: str
    numero_documentos: int
    posicion_posting: int


@dataclass
class Resultado:
    """Respuesta de una consulta de un token."""

    token: str
    numero_documentos: int
    posicion_posting: int
    documentos: list[tuple[str, int]]

    @property
    def frecuencia_total(self) -> int:
        """Repeticiones del token en toda la coleccion."""
        return sum(frecuencia for _, frecuencia in self.documentos)

    @property
    def nombres(self) -> list[str]:
        return [archivo for archivo, _ in self.documentos]

    def describir(self) -> str:
        """Redacta el resultado con la misma narrativa del enunciado."""
        if self.numero_documentos == 0:
            return f"El token '{self.token}' no aparece en la coleccion."

        detalle = ", ".join(
            f"{archivo} con {frec} "
            f"{'repeticion' if frec == 1 else 'repeticiones'}"
            for archivo, frec in self.documentos
        )

        uno = self.numero_documentos == 1
        docs = "1 documento diferente" if uno else f"{self.numero_documentos} documentos diferentes"
        arranque = "el cual empieza" if uno else "los cuales empiezan"
        veces = "1 vez" if self.frecuencia_total == 1 else f"{self.frecuencia_total} veces"
        en_docs = "1 documento" if uno else f"{self.numero_documentos} documentos"

        return (
            f"La palabra '{self.token}' existe en {docs}, {arranque} desde la "
            f"posicion {self.posicion_posting} del archivo posting. Los "
            f"documentos son: {detalle}. Por lo tanto, '{self.token}' se "
            f"encuentra repetido {veces} en {en_docs} de la coleccion."
        )


class IndiceInvertido:
    """Carga diccionario y posting en memoria y resuelve consultas."""

    def __init__(self, ruta_diccionario: Path, ruta_posting: Path) -> None:
        self.ruta_diccionario = Path(ruta_diccionario)
        self.ruta_posting = Path(ruta_posting)
        self._diccionario: dict[str, EntradaDiccionario] = {}
        self._posting: list[tuple[str, int]] = []
        self._cargar()

    # --- Carga -------------------------------------------------------------
    def _cargar(self) -> None:
        self._diccionario = self._cargar_diccionario()
        self._posting = self._cargar_posting()

    def _cargar_diccionario(self) -> dict[str, EntradaDiccionario]:
        entradas: dict[str, EntradaDiccionario] = {}
        with self.ruta_diccionario.open("r", encoding="utf-8") as archivo:
            for numero_linea, linea in enumerate(archivo):
                campos = linea.rstrip("\n").split("\t")
                if numero_linea == 0 and tuple(campos) == ENCABEZADO_DICCIONARIO:
                    continue                     # se omite el encabezado
                if len(campos) != 3:
                    continue
                token, numero_documentos, posicion = campos
                entradas[token] = EntradaDiccionario(
                    token=token,
                    numero_documentos=int(numero_documentos),
                    posicion_posting=int(posicion),
                )
        return entradas

    def _cargar_posting(self) -> list[tuple[str, int]]:
        registros: list[tuple[str, int]] = []
        with self.ruta_posting.open("r", encoding="utf-8") as archivo:
            for numero_linea, linea in enumerate(archivo):
                campos = linea.rstrip("\n").split("\t")
                if numero_linea == 0 and tuple(campos) == ENCABEZADO_POSTING:
                    continue                     # se omite el encabezado
                if len(campos) != 2:
                    continue
                registros.append((campos[0], int(campos[1])))
        return registros

    # --- Consulta ----------------------------------------------------------
    def consultar(self, token: str) -> Resultado:
        """Resuelve un token usando el salto directo que da el diccionario."""
        clave = token.strip().lower()
        entrada = self._diccionario.get(clave)
        if entrada is None:
            return Resultado(clave, 0, -1, [])

        inicio = entrada.posicion_posting
        fin = inicio + entrada.numero_documentos
        documentos = self._posting[inicio:fin]
        return Resultado(
            token=clave,
            numero_documentos=entrada.numero_documentos,
            posicion_posting=inicio,
            documentos=documentos,
        )

    # --- Verificaciones de integridad --------------------------------------
    def verificar_integridad(self, exigir_orden_alfabetico: bool = True) -> list[str]:
        """Comprueba las invariantes del par diccionario/posting.

        Devuelve la lista de problemas encontrados; vacia significa que el
        indice es consistente.

        `exigir_orden_alfabetico` se desactiva cuando el indice se construyo
        con `--orden aparicion`: ahi el orden de las filas es el de primera
        aparicion, no el alfabetico, pero la cadena de offsets debe seguir
        siendo acumulativa.
        """
        problemas: list[str] = []

        tokens = list(self._diccionario)
        if exigir_orden_alfabetico and tokens != sorted(tokens):
            problemas.append("El diccionario no esta en orden alfabetico ascendente.")

        # La cadena de offsets debe ser acumulativa y sin huecos:
        # pos(t_{i+1}) = pos(t_i) + num_docs(t_i)
        esperada = 0
        for token in tokens:
            entrada = self._diccionario[token]
            if entrada.posicion_posting != esperada:
                problemas.append(
                    f"Offset incorrecto en '{token}': se esperaba {esperada}, "
                    f"se encontro {entrada.posicion_posting}."
                )
            esperada += entrada.numero_documentos

        # El posting debe tener exactamente la suma de num_docs del diccionario.
        if esperada != len(self._posting):
            problemas.append(
                f"El posting tiene {len(self._posting)} registros pero el "
                f"diccionario suma {esperada}."
            )

        # Ningun token puede repetir documento ni declarar 0 documentos.
        for token in tokens:
            resultado = self.consultar(token)
            if resultado.numero_documentos <= 0:
                problemas.append(f"'{token}' declara {resultado.numero_documentos} documentos.")
            if len(set(resultado.nombres)) != len(resultado.nombres):
                problemas.append(f"'{token}' tiene documentos repetidos en el posting.")

        return problemas

    # --- Utilidades --------------------------------------------------------
    @property
    def total_tokens(self) -> int:
        return len(self._diccionario)

    @property
    def total_registros(self) -> int:
        return len(self._posting)

    def mas_frecuentes(self, cuantos: int = 10) -> list[Resultado]:
        """Tokens presentes en mas documentos (util para el reporte)."""
        ordenados = sorted(
            self._diccionario.values(),
            key=lambda e: (-e.numero_documentos, e.token),
        )[:cuantos]
        return [self.consultar(entrada.token) for entrada in ordenados]
