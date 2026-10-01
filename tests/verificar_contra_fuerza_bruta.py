"""
verificar_contra_fuerza_bruta.py
================================
Verificacion independiente del indice.

Las pruebas de tests/test_escenarios.py comprueban que el indice es
*internamente* consistente (offsets acumulativos, sin duplicados, los tres
escenarios coinciden). Pero un indice puede ser perfectamente consistente y
aun asi estar equivocado: si la tokenizacion pierde palabras, los tres
escenarios perderan las mismas y nadie se dara cuenta.

Este script cierra ese hueco: toma una muestra de tokens del diccionario y
recalcula sus documentos y frecuencias POR FUERZA BRUTA, volviendo a leer y
tokenizar los 505 archivos desde cero, sin usar el indice. Luego compara.

Es la diferencia entre "el indice es coherente consigo mismo" y "el indice
dice la verdad sobre la coleccion".

Ejecucion:
    python tests/verificar_contra_fuerza_bruta.py
    python tests/verificar_contra_fuerza_bruta.py --muestra 50 --semilla 7
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from consulta import IndiceInvertido          # noqa: E402
from extraccion import tokens_de_archivo      # noqa: E402


def construir_referencia(carpeta: Path) -> dict[str, dict[str, int]]:
    """Recalcula el indice completo por fuerza bruta, sin usar el indice.

    Deliberadamente ingenuo: un solo diccionario anidado construido leyendo
    todo de nuevo. Es lento, y eso esta bien: su unico trabajo es ser obvio
    y por tanto confiable.
    """
    referencia: dict[str, dict[str, int]] = {}
    archivos = sorted(
        ruta for ruta in carpeta.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in (".html", ".htm")
    )
    for numero, ruta in enumerate(archivos, start=1):
        for token, frecuencia in Counter(tokens_de_archivo(ruta)).items():
            referencia.setdefault(token, {})[ruta.name] = frecuencia
        if numero % 100 == 0:
            print(f"  releidos {numero}/{len(archivos)} archivos", flush=True)
    return referencia


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifica el indice contra un recalculo por fuerza bruta."
    )
    parser.add_argument("--corpus", default=str(RAIZ / "Files"))
    parser.add_argument("--salida", default=str(RAIZ / "output"))
    parser.add_argument(
        "--muestra",
        type=int,
        default=200,
        help="cuantos tokens verificar (0 = todos)",
    )
    parser.add_argument("--semilla", type=int, default=42)
    argumentos = parser.parse_args()

    salida = Path(argumentos.salida)
    indice = IndiceInvertido(salida / "diccionario.txt", salida / "posting.txt")
    print(f"Indice cargado: {indice.total_tokens:,} tokens, "
          f"{indice.total_registros:,} registros.\n")

    print("Recalculando el indice por fuerza bruta (esto tarda)...")
    referencia = construir_referencia(Path(argumentos.corpus))
    print(f"Referencia construida: {len(referencia):,} tokens.\n")

    # --- 1. El vocabulario debe ser exactamente el mismo ------------------
    tokens_indice = {t for t in referencia if indice.consultar(t).numero_documentos}
    faltantes = set(referencia) - tokens_indice
    if faltantes:
        print(f"FALLA: {len(faltantes)} tokens de la referencia no estan en el indice.")
        for token in sorted(faltantes)[:10]:
            print(f"  falta: {token}")
        return 1
    if len(referencia) != indice.total_tokens:
        print(
            f"FALLA: el indice tiene {indice.total_tokens:,} tokens pero la "
            f"referencia tiene {len(referencia):,}."
        )
        return 1
    print(f"OK: el vocabulario coincide ({len(referencia):,} tokens).")

    # --- 2. Muestra de tokens: documentos y frecuencias -------------------
    todos = sorted(referencia)
    if argumentos.muestra and argumentos.muestra < len(todos):
        random.seed(argumentos.semilla)
        muestra = random.sample(todos, argumentos.muestra)
        # Se agregan a la fuerza los tokens mas frecuentes: son los que mas
        # registros tienen y donde un error de offset se notaria primero.
        muestra += [r.token for r in indice.mas_frecuentes(10)]
        muestra = sorted(set(muestra))
    else:
        muestra = todos

    print(f"\nVerificando {len(muestra):,} tokens contra la referencia...")
    fallas = 0
    for token in muestra:
        esperado = dict(sorted(referencia[token].items()))
        resultado = indice.consultar(token)
        obtenido = dict(resultado.documentos)

        if obtenido != esperado:
            fallas += 1
            if fallas <= 5:
                print(f"\nFALLA en '{token}':")
                print(f"  esperado: {esperado}")
                print(f"  obtenido: {obtenido}")
        elif resultado.numero_documentos != len(esperado):
            fallas += 1
            print(
                f"\nFALLA en '{token}': NUM_DOCS dice "
                f"{resultado.numero_documentos} pero hay {len(esperado)} documentos."
            )

    # --- 3. La suma total de ocurrencias debe coincidir -------------------
    total_referencia = sum(
        sum(documentos.values()) for documentos in referencia.values()
    )
    total_indice = sum(
        indice.consultar(t).frecuencia_total for t in referencia
    )
    if total_referencia != total_indice:
        print(
            f"\nFALLA: ocurrencias totales. Indice={total_indice:,} "
            f"Referencia={total_referencia:,}"
        )
        fallas += 1
    else:
        print(f"OK: ocurrencias totales coinciden ({total_indice:,}).")

    print()
    print("=" * 70)
    if fallas:
        print(f"RESULTADO: {fallas} discrepancias encontradas.")
        return 1
    print(f"RESULTADO: OK. {len(muestra):,} tokens verificados sin discrepancias.")
    print("El indice coincide con el recalculo independiente de la coleccion.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
