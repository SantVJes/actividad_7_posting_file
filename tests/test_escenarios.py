"""
test_escenarios.py
==================
Pruebas de los tres escenarios de creacion del archivo de posting y de los
criterios de aceptacion de las historias de usuario.

Ejecucion:
    python -m pytest tests/ -v
    python tests/test_escenarios.py        # sin pytest instalado

Las pruebas cubren tres niveles:
    1. Unidad      -- tokenizacion y normalizacion.
    2. Integracion -- el corpus de demostracion debe reproducir EXACTAMENTE
                      la tabla del enunciado (perro 4@0, gato 2@4, pato 3@6,
                      canario 1@9).
    3. Equivalencia-- los tres escenarios deben producir salidas identicas
                      byte a byte sobre el mismo corpus.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from a7_indexador import construir_indice           # noqa: E402
from consulta import IndiceInvertido                # noqa: E402
from estrategias import ESCENARIOS                  # noqa: E402
from extraccion import quitar_acentos, tokenizar    # noqa: E402

CORPUS_FIGURA = RAIZ / "demo" / "corpus_figura"

# Valores exigidos por el enunciado para el corpus de demostracion.
# (token, numero de documentos, posicion en el posting, frecuencia total,
#  documentos esperados en orden)
ESPERADO_FIGURA = [
    ("perro",   4, 0, 16, ["004.html", "009.html", "412.html", "444.html"]),
    ("gato",    2, 4,  2, ["004.html", "412.html"]),
    ("pato",    3, 6, 11, ["004.html", "412.html", "444.html"]),
    ("canario", 1, 9,  1, ["009.html"]),
]


# ---------------------------------------------------------------------------
# 1. Pruebas de unidad: tokenizacion
# ---------------------------------------------------------------------------
def test_quitar_acentos():
    assert quitar_acentos("informacion") == "informacion"
    assert quitar_acentos("información") == "informacion"
    assert quitar_acentos("Niño Águila") == "Nino Aguila"


def test_tokenizar_pasa_a_minusculas():
    assert tokenizar("PERRO Perro perro") == ["perro", "perro", "perro"]


def test_tokenizar_descarta_tokens_de_una_letra():
    # "a" y "y" son de longitud 1 (y ademas stopwords).
    assert tokenizar("a perro y gato") == ["perro", "gato"]


def test_tokenizar_descarta_numeros_puros():
    assert tokenizar("perro 1996 gato 404") == ["perro", "gato"]


def test_tokenizar_descarta_stopwords():
    assert tokenizar("the dog and the cat") == ["dog", "cat"]
    assert tokenizar("el perro con el gato") == ["perro", "gato"]


def test_tokenizar_conserva_repeticiones_y_orden():
    # La frecuencia por documento depende de que NO se deduplique aqui.
    assert tokenizar("perro gato perro") == ["perro", "gato", "perro"]


def test_tokenizar_separa_por_puntuacion():
    assert tokenizar("perro,gato;pato.perro") == ["perro", "gato", "pato", "perro"]


# ---------------------------------------------------------------------------
# 2. Integracion: el corpus de demostracion reproduce la figura del enunciado
# ---------------------------------------------------------------------------
def _construir_figura(tmp: Path, escenario: str = "A", orden: str = "aparicion"):
    """Construye el indice del corpus de demostracion y lo devuelve cargado."""
    diccionario = tmp / "diccionario.txt"
    posting = tmp / "posting.txt"
    construir_indice(
        CORPUS_FIGURA, escenario, diccionario, posting, orden=orden, verboso=False
    )
    return IndiceInvertido(diccionario, posting)


def test_figura_posiciones_y_conteos(tmp_path):
    """ESCENARIO DE VALIDACION 1: la tabla del enunciado, fila por fila."""
    indice = _construir_figura(tmp_path)

    for token, n_docs, posicion, frecuencia, documentos in ESPERADO_FIGURA:
        resultado = indice.consultar(token)
        assert resultado.numero_documentos == n_docs, f"{token}: numero de documentos"
        assert resultado.posicion_posting == posicion, f"{token}: posicion en posting"
        assert resultado.frecuencia_total == frecuencia, f"{token}: frecuencia total"
        assert resultado.nombres == documentos, f"{token}: documentos devueltos"


def test_figura_token_perro_devuelve_los_cuatro_documentos(tmp_path):
    """El ejemplo explicito del enunciado: perro -> 004, 009, 412, 444."""
    indice = _construir_figura(tmp_path)
    resultado = indice.consultar("perro")
    assert resultado.nombres == ["004.html", "009.html", "412.html", "444.html"]


def test_figura_cadena_de_offsets_es_acumulativa(tmp_path):
    """pos(t_{i+1}) = pos(t_i) + num_docs(t_i), incluido el 6 + 3 = 9."""
    indice = _construir_figura(tmp_path)
    acumulado = 0
    for token, n_docs, posicion, _, _ in ESPERADO_FIGURA:
        resultado = indice.consultar(token)
        assert resultado.posicion_posting == acumulado, (
            f"{token}: se esperaba la posicion {acumulado}"
        )
        acumulado += n_docs
    assert acumulado == indice.total_registros


def test_figura_solo_contiene_los_cuatro_tokens(tmp_path):
    indice = _construir_figura(tmp_path)
    assert indice.total_tokens == 4
    assert indice.total_registros == 10        # 4 + 2 + 3 + 1


def test_integridad_sin_problemas(tmp_path):
    indice = _construir_figura(tmp_path)
    assert indice.verificar_integridad(exigir_orden_alfabetico=False) == []


def test_token_inexistente(tmp_path):
    """ESCENARIO DE VALIDACION 3: un token ausente no rompe la consulta."""
    indice = _construir_figura(tmp_path)
    resultado = indice.consultar("elefante")
    assert resultado.numero_documentos == 0
    assert resultado.documentos == []
    assert "no aparece" in resultado.describir()


def test_consulta_es_insensible_a_mayusculas(tmp_path):
    indice = _construir_figura(tmp_path)
    assert indice.consultar("PERRO").nombres == indice.consultar("perro").nombres


# ---------------------------------------------------------------------------
# 3. Equivalencia de los tres escenarios
# ---------------------------------------------------------------------------
def test_los_tres_escenarios_producen_la_misma_salida(tmp_path):
    """ESCENARIO DE VALIDACION 2: A, B y C son intercambiables."""
    salidas: dict[str, tuple[str, str]] = {}
    for clave in sorted(ESCENARIOS):
        carpeta = tmp_path / clave
        carpeta.mkdir()
        diccionario = carpeta / "diccionario.txt"
        posting = carpeta / "posting.txt"
        construir_indice(
            CORPUS_FIGURA,
            clave,
            diccionario,
            posting,
            orden="alfabetico",
            verboso=False,
        )
        salidas[clave] = (
            diccionario.read_text(encoding="utf-8"),
            posting.read_text(encoding="utf-8"),
        )

    referencia = salidas["A"]
    for clave, contenido in salidas.items():
        assert contenido == referencia, (
            f"El escenario {clave} produjo una salida distinta a la del escenario A"
        )


def test_escenario_b_con_bloques_pequenos_sigue_siendo_correcto(tmp_path):
    """El ordenamiento externo debe ser correcto con multiples bloques.

    Se fuerza un tamano de bloque minimo para que el escenario B tenga que
    mezclar varios archivos temporales en lugar de uno solo.
    """
    from estrategias import EscenarioBOrdenExterno
    from escritura import escribir_indice
    from extraccion import tokens_de_archivo
    from collections import Counter

    estrategia = EscenarioBOrdenExterno(tamano_bloque=3)   # bloques diminutos
    estrategia.iniciar()
    try:
        for ruta in sorted(CORPUS_FIGURA.iterdir()):
            frecuencias = Counter(tokens_de_archivo(ruta))
            estrategia.agregar_documento(ruta.name, dict(frecuencias))
        diccionario = tmp_path / "diccionario.txt"
        posting = tmp_path / "posting.txt"
        escribir_indice(estrategia.recorrer(), diccionario, posting)
    finally:
        estrategia.cerrar()

    indice = IndiceInvertido(diccionario, posting)
    assert indice.verificar_integridad() == []
    assert indice.consultar("perro").nombres == [
        "004.html", "009.html", "412.html", "444.html",
    ]


def test_escenario_c_persiste_la_base(tmp_path):
    """El escenario C puede dejar un indice SQLite consultable en disco."""
    import sqlite3
    from collections import Counter

    from escritura import escribir_indice
    from estrategias import EscenarioCSQLite
    from extraccion import tokens_de_archivo

    ruta_bd = tmp_path / "indice.sqlite"
    estrategia = EscenarioCSQLite(ruta_bd=ruta_bd)
    estrategia.iniciar()
    try:
        for ruta in sorted(CORPUS_FIGURA.iterdir()):
            frecuencias = Counter(tokens_de_archivo(ruta))
            estrategia.agregar_documento(ruta.name, dict(frecuencias))
        escribir_indice(
            estrategia.recorrer(), tmp_path / "diccionario.txt", tmp_path / "posting.txt"
        )
    finally:
        estrategia.cerrar()

    assert ruta_bd.exists(), "la base de datos debio quedar en disco"
    conexion = sqlite3.connect(ruta_bd)
    try:
        total = conexion.execute(
            "SELECT SUM(frecuencia) FROM ocurrencia WHERE token = 'perro'"
        ).fetchone()[0]
        assert total == 16
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Ejecucion directa sin pytest
# ---------------------------------------------------------------------------
def _correr_sin_pytest() -> int:
    """Ejecuta las pruebas con un tmp_path artesanal si no hay pytest."""
    import inspect
    import tempfile
    import traceback

    pruebas = [
        (nombre, funcion)
        for nombre, funcion in sorted(globals().items())
        if nombre.startswith("test_") and callable(funcion)
    ]

    fallidas = 0
    for nombre, funcion in pruebas:
        with tempfile.TemporaryDirectory() as temporal:
            try:
                if "tmp_path" in inspect.signature(funcion).parameters:
                    funcion(Path(temporal))
                else:
                    funcion()
                print(f"  OK    {nombre}")
            except Exception:
                fallidas += 1
                print(f"  FALLA {nombre}")
                traceback.print_exc()

    print()
    print(f"{len(pruebas) - fallidas}/{len(pruebas)} pruebas exitosas")
    return 1 if fallidas else 0


if __name__ == "__main__":
    raise SystemExit(_correr_sin_pytest())
