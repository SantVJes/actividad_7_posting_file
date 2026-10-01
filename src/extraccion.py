"""
extraccion.py
=============
Capa de extraccion y normalizacion de texto.

Responsabilidad unica: convertir un archivo HTML en una lista de tokens
limpios, listos para ser contados. No sabe nada del diccionario ni del
archivo de posting.

Pipeline de normalizacion (en este orden):
    1. Lectura tolerante del archivo (los HTML del corpus son de 1996 y
       mezclan latin-1 con utf-8).
    2. Eliminacion de <script> y <style> (su contenido no es texto del
       documento).
    3. Extraccion del texto plano con BeautifulSoup + lxml.
    4. Paso a minusculas.
    5. Eliminacion de acentos (NFD + descarte de marcas diacriticas), de
       modo que "accion" y "accion" sean el mismo token.
    6. Segmentacion por cualquier caracter que no sea letra o digito.
    7. Descarte de tokens de longitud 1, tokens puramente numericos y
       palabras vacias (stopwords).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

from stopwords import STOPWORDS

# Un token es una secuencia maximal de letras/digitos. Se separa por
# cualquier otra cosa (espacios, puntuacion, guiones, entidades, etc.).
_SEPARADORES = re.compile(r"[^0-9a-z]+")

# Longitud minima para que un token sea considerado indexable.
LONGITUD_MINIMA_TOKEN = 2


def leer_html(ruta: Path) -> str:
    """Lee el archivo HTML tolerando codificaciones mixtas.

    Intenta utf-8 y cae a latin-1 (que nunca falla) para no perder
    documentos del corpus por un byte invalido.
    """
    datos = ruta.read_bytes()
    for codificacion in ("utf-8", "latin-1"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    # latin-1 no puede fallar, pero dejamos la red de seguridad explicita.
    return datos.decode("utf-8", errors="ignore")


def extraer_texto(html: str) -> str:
    """Devuelve unicamente el texto visible del documento HTML."""
    sopa = BeautifulSoup(html, "lxml")
    for etiqueta in sopa(["script", "style"]):
        etiqueta.decompose()
    return sopa.get_text(separator=" ")


def quitar_acentos(texto: str) -> str:
    """Normaliza a NFD y descarta las marcas diacriticas (categoria Mn)."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def tokenizar(texto: str) -> list[str]:
    """Convierte texto plano en la lista de tokens indexables.

    Conserva el orden de aparicion y las repeticiones, porque la
    frecuencia por documento es justamente la columna 2 del archivo de
    posting.
    """
    texto = quitar_acentos(texto.lower())
    tokens: list[str] = []
    for bruto in _SEPARADORES.split(texto):
        if len(bruto) < LONGITUD_MINIMA_TOKEN:
            continue
        if bruto.isdigit():          # "1996", "404": ruido para este indice
            continue
        if bruto in STOPWORDS:       # palabras vacias es/en
            continue
        tokens.append(bruto)
    return tokens


def tokens_de_archivo(ruta: Path) -> list[str]:
    """Atajo: archivo HTML -> lista de tokens indexables."""
    return tokenizar(extraer_texto(leer_html(ruta)))
