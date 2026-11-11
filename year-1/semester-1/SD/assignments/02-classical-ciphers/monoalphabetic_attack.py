#!/usr/bin/env python3
"""Decifragem manual da cifra monoalfabética da Questão 1.

Cada entrada tem o formato LETRA_CIFRADA:LETRA_CLARA.
As correspondências foram deduzidas manualmente através de digramas,
trigramas e do contexto do texto em português.
"""

import string
import sys
from collections import Counter
from pathlib import Path

# Esta tabela pode ser preenchida progressivamente durante a análise.
CHAVE = {
    "A": "J", "B": "C", "C": "B", "D": "P", "E": "I",
    "F": "Q", "G": "L", "H": "M", "I": "E", "J": "A",
    "K": "O", "L": "G", "M": "H", "P": "D", "Q": "F",
    "R": "X", "S": "T", "T": "S", "U": "V", "V": "U",
    "W": "Z", "Y": "N", "Z": "R",
}


def decifrar(texto: str) -> str:
    return "".join(CHAVE.get(letra, "_") for letra in texto)


def mostrar_frequencia_letras(texto: str) -> None:
    total = len(texto)
    contagens = Counter(texto)

    print("Frequência das letras no texto cifrado:")
    for letra, quantidade in contagens.most_common():
        percentagem = quantidade / total * 100
        print(f"{letra}: {quantidade:4d} ({percentagem:5.2f}%)")


def main() -> None:
    pasta_do_script = Path(__file__).resolve().parent
    entrada = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else pasta_do_script / "Q1_ciphertext.txt"
    )
    saida = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    texto = "".join(
        letra for letra in entrada.read_text(encoding="utf-8").upper()
        if letra in string.ascii_uppercase
    )
    mostrar_frequencia_letras(texto)
    print()
    claro = decifrar(texto)
    print(claro)
    if saida:
        saida.write_text(claro + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
