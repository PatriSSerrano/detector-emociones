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

from expresiones import (ESPEJO_TACOS, EUFEMISMOS, REFLEJABLES_EXPR, VERBOS_ESPEJO, VULGARES,
                         expresiones_expandidas)
from utils import buscar, normalizar

COLOQUIALISMOS = [
    "tio", "tia", "colega", "en plan", "mazo", "flip*", "rayad*", "ralla*", "movida", "chung*",
    "guay", "mola", "finde", "bro", "jaj*", "jej*", "xd", "porfa", "uf", "buf", "buah", "osea",
    "o sea", "a tope", "de bajon", "hecho polvo", "hecha polvo", "curro", "insti", "peli",
    "ostras", "madre mia", "jo", "vaya tela", "un monton", "fatal", "tranqui", "vale",
]
ABREVIATURAS = {"q", "k", "pq", "xq", "tb", "tmb", "xfa", "dnd", "bn", "x", "toy", "ta"}
# Vocativos: cómo llama la persona a quien le escucha. Se devuelven tal cual.
VOCATIVOS = [
    "bro", "bra", "broder", "brother", "tio", "tia", "tronco", "tronca", "colega", "macho",
    "nena", "nene", "neno", "cari", "carino", "amiga", "amigo", "hermano", "hermana", "mano",
    "manito", "crack", "chaval", "chavala", "maquina", "guapa", "guapo", "reina", "rey",
    "chiqui", "cielo", "primo", "prima", "socio", "compi", "wey", "guey", "pana", "parce",
    "che", "boludo", "boluda", "mi amor", "amor", "bebe", "cuqui", "titi", "peque", "man",
]
# Despedidas y coletillas finales. También se devuelven.
CIERRES = [
    "xoxo", "besis", "besitos", "besos", "besazo", "un besazo", "bss", "bsos", "bsts",
    "un abrazo", "abrazos", "un abrazote", "muak", "mua", "chao", "bye", "xd", "jaja*", "jeje*",
    "<3", "un saludo", "saludos",
]
_PREVIO_VOC = (r"(?:^|[,.!?¡¿;:]\s*|\b(?:uf|buf|jo|joder|ay|oye|mira|hola|ey|eh|buah|ostras|"
               r"hostia|vale|gracias|jaj\w*|jej\w*)\s+)")
_ALT_VOC = "|".join(sorted(map(re.escape, VOCATIVOS), key=len, reverse=True))
RE_VOCATIVO = re.compile(_PREVIO_VOC + r"(" + _ALT_VOC + r")(?=[\s,.!?…]|$)")
RE_VOCATIVO_FINAL = re.compile(r"[\s,]+(" + _ALT_VOC + r")\s*[.!?…]*\s*$")

# Todas las expresiones idiomáticas de varias palabras (para no tomar sus
# palabras como "temas": en "hasta la polla", "la polla" NO es un tema)
_EXPR = sorted({e for lista in expresiones_expandidas().values() for e, _ in lista
                if " " in e and not e.endswith("*")}, key=len, reverse=True)
RE_EXPRESION = re.compile(r"\b(" + "|".join(map(re.escape, _EXPR)) + r")\b")
_AUTODESC_EXPR = sorted(set(REFLEJABLES_EXPR) | set(EUFEMISMOS), key=len, reverse=True)

FORMALES = [
    "usted", "ustedes", "disculpe", "perdone", "cordialmente", "atentamente", "estimad*",
    "quisiera", "le agradeceria", "le escribo", "me dirijo", "les escribo", "un saludo",
]
MARCAS_USTED = ["usted", "ustedes", "disculpe", "perdone", "le escribo", "le agradeceria", "me dirijo"]

INTERJECCIONES = ["uf", "buf", "buah", "jo", "joder", "hostia", "ostia", "ay", "ostras",
                  "madre mia", "jaja*", "jeje*", "wow", "guau"]

# Autodescripciones que SÍ se pueden reflejar con las palabras de la persona.
# Son descriptivas de un estado. Se excluyen a propósito los insultos a uno mismo
# ("soy un fracasado"), las palabrotas y lo muy negativo ("fatal", "fatal total"):
# esas cosas se reflejan con otras palabras, sin copiar la negatividad.
REFLEJABLES = [
    "rayad*", "agobiad*", "de bajon", "hecho polvo", "hecha polvo", "quemad*", "nervios*",
    "estresad*", "cansad*", "agotad*", "emocionad*", "content*", "feliz", "tranquil*", "tranqui",
    "ilusionad*", "motivad*", "flipando", "trist*", "preocupad*", "molest*", "enfadad*",
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
    "suda", "pela", "trae", "refanfinfla",          # "me la suda", "me la pela"...
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
    autodescripcion: str = None         # p. ej. "rayada" o "hasta la polla"
    pos_autodescripcion: int = -1
    expresion_me: str = None            # "me toca los huevos" -> se devuelve como "te toca..."
    vocativo: str = None                # "tía", "bro"...
    cierre: str = None                  # "xoxo", "besis"...
    temas: list = field(default_factory=list)   # [Tema(...)]

    def resumen(self):
        partes = [self.registro, "usted" if self.tratamiento == "usted" else "tú",
                  f"mensaje {self.longitud}"]
        if self.emojis:
            partes.append("usa emojis " + "".join(self.emojis[:3]))
        if self.coloquialismos:
            partes.append("expresiones: " + ", ".join(f"«{c}»" for c in self.coloquialismos[:4]))
        if self.vulgaridad:
            partes.append("usa tacos (se reflejan)" if ESPEJO_TACOS else "usa tacos (no se copian)")
        if self.autodescripcion:
            partes.append(f"se describe como «{self.autodescripcion}»")
        if self.vocativo:
            partes.append(f"te llama «{self.vocativo}»")
        if self.cierre:
            partes.append(f"cierra con «{self.cierre}»")
        return " · ".join(partes)


ADJ_PRENOMINALES = {
    "buen", "buena", "buenos", "buenas", "mal", "mala", "malos", "malas", "gran", "grande",
    "nuevo", "nueva", "nuevos", "nuevas", "viejo", "vieja", "mejor", "mejores", "peor", "peores",
    "pequeno", "pequena", "mucho", "mucha", "muchos", "muchas", "poco", "poca", "pocos", "pocas",
    "otro", "otra", "otros", "otras", "primer", "primera", "ultimo", "ultima", "segundo", "segunda",
    "puto", "puta", "maldito", "maldita", "dichoso", "dichosa", "pobre", "querido", "querida",
    "antiguo", "antigua", "verdadero", "verdadera", "unico", "unica", "mismo", "misma",
}


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


RE_VERBO_ESTADO = re.compile(
    r"\b(?:estoy|me siento|ando|me noto|voy|toy|sigo|me encuentro)\s+" + INTENSIF +
    r"(mas |menos )?")


def _autodescripcion(texto, normal):
    fuente = texto if len(texto) == len(normal) else normal

    # 1) Expresiones idiomáticas: "estoy hasta la polla", "estoy de bajón", "estoy colada por Marta"
    for m in RE_VERBO_ESTADO.finditer(normal):
        resto = normal[m.end():]
        for expr in _AUTODESC_EXPR:
            if re.match(re.escape(expr) + r"(?!\w)", resto):
                ini, fin = m.end(), m.end() + len(expr)
                if expr.endswith(" por"):                 # "colada por Marta": incluir a quién
                    sig = re.match(r"\s*\w+", normal[fin:])
                    fin += sig.end() if sig else 0
                if expr in EUFEMISMOS and not ESPEJO_TACOS:
                    desc = EUFEMISMOS[expr]
                else:
                    desc = fuente[ini:fin]                # tal cual lo dijo, tacos incluidos
                cambio = fuente[m.start(1):m.end(1)] if m.group(1) else ""
                return cambio + desc, m.start(1) if m.group(1) else ini

    # 2) Adjetivos: "estoy rayada", "me siento cansada y preocupada"
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


def _expresion_me(texto, normal):
    """'me toca los huevos' -> se puede devolver como 'te toca los huevos'."""
    fuente = texto if len(texto) == len(normal) else normal
    for m in RE_EXPRESION.finditer(normal):
        palabras = m.group(1).split()
        if len(palabras) >= 2 and palabras[0] == "me" and palabras[1] in VERBOS_ESPEJO:
            return fuente[m.start():m.end()]
    return None


_NO_VOC_ANTES = {"mi", "tu", "su", "mis", "tus", "sus", "el", "la", "los", "las", "un", "una",
                 "del", "al", "de", "a", "con", "para", "por", "esa", "ese", "esta", "este"}


def _vocativo(texto, normal):
    fuente = texto if len(texto) == len(normal) else normal
    m = RE_VOCATIVO.search(normal) or RE_VOCATIVO_FINAL.search(normal)
    if not m:
        # En mitad del mensaje, seguido de coma: "todo bro, no hay quesitos".
        # Pero no si va detrás de un determinante: "a mi tía, que..." no es vocativo.
        for m2 in re.finditer(r"\b(" + _ALT_VOC + r")(?=\s*[,!?])", normal):
            previa = normal[:m2.start()].split()[-1:]
            if not previa or previa[0] not in _NO_VOC_ANTES:
                m = m2
                break
    return fuente[m.start(1):m.end(1)] if m else None


CARINOS = ["xoxo", "besis", "besitos", "muak", "mua", "<3", "un besazo", "besazo"]


def _cierre(texto, normal):
    """Coletilla: 'xoxo', 'besis', 'un abrazo'... Los cariños ('xoxo', 'besis')
    cuentan aunque vayan en mitad del mensaje; el resto, solo al final."""
    fuente = texto if len(texto) == len(normal) else normal
    for c in CARINOS:
        m = re.search(r"(?<!\w)" + re.escape(c) + r"(?!\w)", normal)
        if m:
            return fuente[m.start():m.end()]
    cola = normal[-30:]
    desplazamiento = len(normal) - len(cola)
    mejor = None
    for c in CIERRES:
        for m in re.finditer(r"(?<!\w)" + (re.escape(c[:-1]) + r"\w*" if c.endswith("*")
                                           else re.escape(c)) + r"(?!\w)", cola):
            if mejor is None or m.start() > mejor[0]:
                mejor = (m.start(), m.end())
    if mejor is None:
        return None
    # tiene que ir al final de verdad (solo puede seguir puntuación o emojis)
    resto = normal[desplazamiento + mejor[1]:]
    if re.search(r"\w", resto):
        return None
    return fuente[desplazamiento + mejor[0]:desplazamiento + mejor[1]]


def _temas(texto, spans_expresiones=()):
    bajo = texto.lower()
    temas = []
    patron = (r"\b(?:(con|por|de|en|sobre)\s+)?"
              r"(mis|mi|el|la|los|las|un|una|lo del|lo de|del|al)\s+([a-záéíóúüñ]{4,})")
    for m in re.finditer(patron, bajo):
        prep, det, sust = m.group(1), m.group(2), m.group(3)
        if det in ("del", "al"):                # "del curro" = "de" + "el curro"
            prep, det = {"del": "de", "al": "a"}[det], "el"
        n = normalizar(sust)
        if n in NO_TEMAS or n.endswith(("ando", "iendo", "mente")):
            continue
        # "soy un fracasado", "es un gilipollas": es un ATRIBUTO (a menudo un insulto),
        # no un tema. Si lo usáramos, copiaríamos la negatividad.
        if re.search(r"\b(soy|eres|es|son|somos|estoy|parezco|me siento)\s*$", bajo[:m.start()]):
            continue
        # Dentro de una expresión idiomática ("hasta LA POLLA", "con EL AGUA al cuello")
        if any(ini <= m.start(2) < fin for ini, fin in spans_expresiones):
            continue
        det = {"un": "el", "una": "la"}.get(det, det)    # "una reunión" -> "la reunión"
        # Adjetivos que van DELANTE del sustantivo: "un BUEN bíceps", "la NUEVA casa".
        # El tema es el sustantivo de detrás, así que lo añadimos: "buen bíceps".
        if n in ADJ_PRENOMINALES:
            siguiente = re.match(r"\s+([a-záéíóúüñ]{3,})", bajo[m.end():])
            if not siguiente:
                continue
            sust = f"{sust} {siguiente.group(1)}"
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
    vocativo, cierre = _vocativo(texto, normal), _cierre(texto, normal)

    informal = (len(coloq) + len(abrev) + 2 * len(vulgares) + (1 if emojis else 0)
                + (1 if vocativo else 0) + (1 if cierre else 0)
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
        expresion_me=_expresion_me(texto, normal),
        vocativo=vocativo,
        cierre=cierre,
        temas=_temas(texto, [(m.start(), m.end()) for m in RE_EXPRESION.finditer(normal)]),
    )
