"""
Normalización de texto: convierte las formas "disfrazadas" de una palabra a su forma
estándar para que el detector no se deje engañar.

    P3ND3J0       -> pendejo
    p.e.n.d.e.j.o -> pendejo
    p e n d e j o -> pendejo
    idiotaaaaa    -> idiotaa   (las repeticiones de 3+ letras se reducen a 2)
    estúpido      -> estupido
"""

import re
import unicodedata

# Números y símbolos que se usan en lugar de letras
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

# Un "token" es una palabra que puede llevar símbolos intercalados: p.e.n-d_e*j·o
_LETRA = r"0-9A-Za-zÀ-ÖØ-öø-ÿ@$"
TOKEN_RE = re.compile(rf"[{_LETRA}]+(?:[.\-_*·'´`]+[{_LETRA}]+)*")
_REPETIDAS = re.compile(r"(.)\1{2,}")


def quitar_acentos(texto: str) -> str:
    sin = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def normalizar_token(token: str) -> str:
    t = quitar_acentos(token.lower())
    if any(c.isalpha() for c in t):          # "5" solo sigue siendo número
        t = t.translate(LEET)
    t = re.sub(r"[^a-z]", "", t)
    return _REPETIDAS.sub(r"\1\1", t)


def tokenizar(texto: str):
    """
    Devuelve una lista de (palabra_normalizada, inicio, fin) con la posición de la
    palabra en el texto ORIGINAL, para después poder censurarla en su lugar.
    Las letras sueltas separadas por espacios ("p e n d e j o") se unen en una palabra.
    """
    crudos = [(normalizar_token(m.group()), m.start(), m.end()) for m in TOKEN_RE.finditer(texto)]
    crudos = [c for c in crudos if c[0]]
    salida, i = [], 0
    while i < len(crudos):
        j = i
        while j < len(crudos) and len(crudos[j][0]) == 1:
            j += 1
        if j - i >= 3:  # tres o más letras sueltas seguidas -> una sola palabra
            palabra = "".join(c[0] for c in crudos[i:j])
            salida.append((palabra, crudos[i][1], crudos[j - 1][2]))
            i = j
        else:
            salida.append(crudos[i])
            i += 1
    return salida


def normalizar_texto(texto: str) -> str:
    """Texto completo normalizado (es lo que ve el modelo de IA)."""
    return " ".join(p for p, _, _ in tokenizar(texto))
