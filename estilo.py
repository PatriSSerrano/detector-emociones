"""
Detección del ESTILO con el que se expresa la persona.

Base: SINCRONÍA DE ESTILO LINGÜÍSTICO (Language Style Matching, Ireland y
Pennebaker, 2010). Cuando dos personas hablan con un estilo parecido, aumenta
la sensación de conexión y de "me entiende". Un buen terapeuta adapta su forma
de hablar (registro, cercanía, longitud) a la de la persona, SIN copiar su
malestar.

Qué se mide:
  - registro:     formal / neutro / cercano / coloquial
  - tratamiento:  tú o usted
  - emojis, exclamaciones, interjecciones ("uf", "jaja")
  - longitud del mensaje (para responder con una extensión parecida)
  - autodescripción: cómo se describe la persona ("estoy rayada") para
    poder reflejarlo con SUS palabras
  - temas: de qué habla ("el examen", "mi jefe")
"""

import re
import unicodedata
from dataclasses import dataclass, field

from textblob import TextBlob

from utils import buscar, normalizar

COLOQUIALISMOS = [
    "tio", "tia", "colega", "en plan", "mazo", "flip*", "rayad*", "ralla*", "movida", "chung*",
    "guay", "mola", "finde", "bro", "jaj*", "jej*", "xd", "porfa", "uf", "buf", "buah", "osea",
    "o sea", "a tope", "de bajon", "hecho polvo", "hecha polvo", "curro", "insti", "peli",
    "ostras", "madre mia", "jo", "vaya tela", "un monton", "fatal", "tranqui", "vale",
]
ABREVIATURAS = {"q", "k", "pq", "xq", "tb", "tmb", "xfa", "dnd", "bn", "x", "toy", "ta"}
VULGARES = [
    "joder", "mierda", "puta", "puto", "hostia*", "cojon*", "cono", "gilipolla*", "cabron*",
    "me cago", "follar", "capull*",
]
FORMALES = [
    "usted", "ustedes", "disculpe", "perdone", "cordialmente", "atentamente", "estimad*",
    "quisiera", "le agradeceria", "le escribo", "me dirijo", "les escribo", "un saludo",
]
MARCAS_USTED = ["usted", "ustedes", "disculpe", "perdone", "le escribo", "le agradeceria", "me dirijo"]

INTERJECCIONES = ["uf", "buf", "buah", "jo", "ostras", "madre mia", "jaja*", "jeje*", "wow", "guau"]

# Autodescripciones que SÍ se pueden reflejar con las palabras de la persona.
# Son descriptivas de un estado. Se excluyen a propósito los insultos a uno mismo
# ("soy un fracasado"), las palabrotas y lo muy negativo ("fatal", "fatal total"):
# esas cosas se reflejan con otras palabras, sin copiar la negatividad.
REFLEJABLES = [
    "rayad*", "agobiad*", "de bajon", "hecho polvo", "hecha polvo", "quemad*", "nervios*",
    "estresad*", "cansad*", "agotad*", "emocionad*", "content*", "feliz", "tranquil*", "tranqui",
    "ilusionad*", "motivad*", "flipando", "triste", "preocupad*", "molest*", "enfadad*",
    "cabread*", "harto", "harta", "raro", "rara", "bloquead*", "perdid*", "desanimad*",
    "a tope", "genial", "de buenas", "nervioso", "nerviosa",
]

INTENSIF = r"(?:un poco |muy |bastante |super |mazo |algo |tan |tope de |re |muy muy )?"
ADJ = r"(?:de [a-z]+|hech[oa] polvo|a tope(?! de)|[a-z]+)"
# "estoy (muy) rayada" · "me siento cansada y (muy) preocupada" · "estoy más tranqui"
# "muy" se quita (no amplificar), pero "más/menos" se conserva: indica un CAMBIO
# ("estoy más tranqui" = ha mejorado) y eso sí hay que reflejarlo.
RE_AUTODESC = re.compile(
    r"\b(?:estoy|me siento|ando|me noto|voy|toy|sigo|me encuentro)\s+" + INTENSIF +
    r"((?:mas |menos )?" + ADJ + r")(?:\s+y\s+" + INTENSIF + r"(" + ADJ + r"))?\b")

# Palabras que no son "temas" aunque vayan detrás de un artículo
NO_TEMAS = {
    "verdad", "vez", "veces", "gente", "cosa", "cosas", "vida", "mismo", "misma", "mismos",
    "noche", "noches", "hora", "horas", "manana", "tarde", "forma", "manera", "parte", "mejor",
    "peor", "primer", "primera", "ultimo", "ultima", "culpa", "pena", "semana", "cabeza",
    "mundo", "todo", "nada", "otra", "otro", "otros", "otras", "suerte", "momento", "tiempo",
    "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
}


@dataclass
class Estilo:
    registro: str                       # formal / neutro / cercano / coloquial
    tratamiento: str                    # tu / usted
    longitud: str                       # corta / media / larga
    emojis: list = field(default_factory=list)
    exclamaciones: bool = False
    interjeccion: str = None
    coloquialismos: list = field(default_factory=list)
    vulgaridad: bool = False
    autodescripcion: str = None         # p. ej. "rayada" o "cansada y preocupada"
    pos_autodescripcion: int = -1
    temas: list = field(default_factory=list)   # [Tema(...)]

    def resumen(self):
        partes = [self.registro, "usted" if self.tratamiento == "usted" else "tú",
                  f"mensaje {self.longitud}"]
        if self.emojis:
            partes.append("usa emojis " + "".join(self.emojis[:3]))
        if self.coloquialismos:
            partes.append("expresiones: " + ", ".join(f"«{c}»" for c in self.coloquialismos[:4]))
        if self.vulgaridad:
            partes.append("tacos (no se copian)")
        if self.autodescripcion:
            partes.append(f"se describe como «{self.autodescripcion}»")
        return " · ".join(partes)


@dataclass
class Tema:
    prep: str      # preposición que usó la persona ("con", "por"...) o None
    det: str       # "mi", "el", "lo del"...
    sust: str      # "examen", "jefe"...
    pos: int       # posición en el texto (para elegir el tema más cercano a la emoción)


def _es_emoji(c):
    return unicodedata.category(c) == "So" and ord(c) > 0x2100


def _reflejable(palabra):
    return any(re.fullmatch(re.escape(r[:-1]) + r"\w*" if r.endswith("*") else re.escape(r),
                            palabra) for r in REFLEJABLES)


def _autodescripcion(texto, normal):
    fuente = texto if len(texto) == len(normal) else normal
    for m in RE_AUTODESC.finditer(normal):
        if not _reflejable(re.sub(r"^(mas|menos) ", "", m.group(1))):
            continue
        fin = m.end(1)
        if m.group(2) and _reflejable(m.group(2)):
            fin = m.end(2)              # "cansada y preocupada"
        desc = fuente[m.start(1):fin]
        desc = re.sub(r"\s+y\s+" + INTENSIF, " y ", desc)   # quitar "muy" del 2º adjetivo
        return desc, m.start(1)
    return None, -1


def _temas(texto):
    bajo = texto.lower()
    temas = []
    patron = (r"\b(?:(con|por|de|en|sobre)\s+)?"
              r"(mis|mi|el|la|los|las|un|una|lo del|lo de)\s+([a-záéíóúüñ]{4,})")
    for m in re.finditer(patron, bajo):
        prep, det, sust = m.group(1), m.group(2), m.group(3)
        n = normalizar(sust)
        if n in NO_TEMAS or n.endswith(("ando", "iendo", "mente")):
            continue
        # "soy un fracasado", "es un gilipollas": es un ATRIBUTO (a menudo un insulto),
        # no un tema. Si lo usáramos, copiaríamos la negatividad.
        if re.search(r"\b(soy|eres|es|son|somos|estoy|parezco|me siento)\s*$", bajo[:m.start()]):
            continue
        det = {"un": "el", "una": "la"}.get(det, det)    # "una reunión" -> "la reunión"
        if all(t.sust != sust for t in temas):
            temas.append(Tema(prep, det, sust, m.start()))
    return temas


def detectar_estilo(texto):
    normal = normalizar(texto)
    palabras = [normalizar(w) for w in TextBlob(texto).words]
    n = len(palabras)

    coloq = buscar(COLOQUIALISMOS, texto, normal)
    abrev = [p for p in palabras if p in ABREVIATURAS]
    vulgares = buscar(VULGARES, texto, normal)
    formales = buscar(FORMALES, texto, normal)
    emojis = [c for c in texto if _es_emoji(c)]

    informal = (len(coloq) + len(abrev) + 2 * len(vulgares) + (1 if emojis else 0)
                + (1 if re.search(r"[!?]{2,}", texto) else 0)
                + (1 if texto.strip()[:1].islower() else 0))
    formal = 2 * len(formales)

    if formal >= 2 and informal <= 1:
        registro = "formal"
    elif informal >= 3 or vulgares:
        registro = "coloquial"
    elif informal >= 1:
        registro = "cercano"
    else:
        registro = "neutro"

    interj = buscar(INTERJECCIONES, texto, normal)
    autodesc, pos_autodesc = _autodescripcion(texto, normal)
    return Estilo(
        registro=registro,
        tratamiento="usted" if buscar(MARCAS_USTED, texto, normal) else "tu",
        longitud="corta" if n < 12 else "media" if n < 40 else "larga",
        emojis=emojis,
        exclamaciones="!" in texto,
        interjeccion=interj[0] if interj else None,
        coloquialismos=[c for c in coloq if normalizar(c) not in {"vale"}],
        vulgaridad=bool(vulgares),
        autodescripcion=autodesc,
        pos_autodescripcion=pos_autodesc,
        temas=_temas(texto),
    )
