"""Funciones pequeñas compartidas por varios módulos."""

import re
import unicodedata


def normalizar(texto):
    """'Alegría' -> 'alegria' (minúsculas y sin tildes).
    No cambia la longitud del texto, así las posiciones de un texto normalizado
    sirven para recortar el original."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


ABREVIATURAS = {
    "q": "que", "k": "que", "pq": "porque", "xq": "porque", "tb": "también",
    "tmb": "también", "x": "por", "toy": "estoy", "dnd": "dónde", "bn": "bien",
    "xfa": "por favor", "mñn": "mañana",
}


def expandir_abreviaturas(texto):
    """'seguro q suspendo' -> 'seguro que suspendo', para que los patrones funcionen."""
    return re.sub(r"\b(" + "|".join(map(re.escape, ABREVIATURAS)) + r")\b",
                  lambda m: ABREVIATURAS[m.group(1).lower()], texto, flags=re.IGNORECASE)


def patron(expresion):
    """Convierte una entrada de léxico en regex: 'rayad*' -> raíz, 'en plan' -> literal."""
    if expresion.endswith("*"):
        return r"\b" + re.escape(expresion[:-1]) + r"\w*"
    return r"\b" + re.escape(expresion) + r"\b"


def buscar(expresiones, texto_original, texto_normal=None):
    """Devuelve los fragmentos del texto ORIGINAL que coinciden con alguna expresión."""
    if texto_normal is None:
        texto_normal = normalizar(texto_original)
    fuente = texto_original if len(texto_original) == len(texto_normal) else texto_normal
    encontrados = []
    for e in expresiones:
        for m in re.finditer(patron(e), texto_normal):
            frag = fuente[m.start():m.end()]
            if frag.lower() not in (x.lower() for x in encontrados):
                encontrados.append(frag)
    return encontrados
