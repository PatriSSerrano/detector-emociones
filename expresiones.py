"""
Expresiones idiomáticas del español (coloquiales y malsonantes).

Por qué hace falta este archivo:
  En una EXPRESIÓN IDIOMÁTICA el significado no sale de sus palabras sueltas.
  "Polla", "moño" o "una" no expresan ninguna emoción, pero "estoy hasta la
  polla", "hasta el moño" o "más sola que la una" sí. Por eso se tratan como
  UNIDADES de significado, no palabra a palabra.

Formato de PLANTILLA: las llaves dan alternativas.
  "hasta {la polla|las narices}"  ->  "hasta la polla", "hasta las narices"
Todo en minúsculas y SIN tildes (ñ -> n: "moño" se escribe "mono").
"""

import itertools
import re


def expandir(plantilla):
    """'hasta {la polla|el mono}' -> ['hasta la polla', 'hasta el mono']"""
    trozos = re.split(r"(\{[^}]*\})", plantilla)
    opciones = [t[1:-1].split("|") if t.startswith("{") else [t] for t in trozos]
    return [re.sub(r"\s+", " ", "".join(c)).strip() for c in itertools.product(*opciones)]


# Partes del cuerpo / palabras que se usan en "estar hasta X" (todas = muy harto/a)
_HASTA_VULGAR = "la polla|las pollas|los huevos|los cojones|las pelotas|el cono|el culo|las tetas|el higo|la madre"
_HASTA_LIMPIO = "las narices|el mono|el gorro|la coronilla|el copete"

EXPRESIONES = {
    "ira": [
        ("hasta {" + _HASTA_VULGAR + "|" + _HASTA_LIMPIO + "}", 3),
        ("me {toca|tocan|toco} {las narices|los huevos|los cojones|las pelotas|la moral|las narices}", 3),
        ("me {saca|sacan|saco} de {quicio|mis casillas}", 3),
        ("me {pone|ponen} de los nervios", 2),
        ("me {pone|ponen} {negro|negra|enfermo|enferma|de mala leche|de mala hostia|de mala ostia}", 3),
        ("de mala {leche|hostia|ostia|uva}", 2),
        ("{estoy|esta|estaba} que {muerdo|echo humo|trino|exploto|reviento}", 3),
        ("echando humo", 2), ("me subo por las paredes", 3),
        ("me cago en {todo|la leche|la puta|dios|tu madre|la madre que|sus muertos|la hostia}", 3),
        ("me cago en", 2),
        ("me {jode|jodio|joden|jodieron}", 2), ("que le den", 2), ("que les den", 2),
        ("a la mierda", 2), ("vete a la mierda", 3),
        ("que {putada|faena|cabronada|morro|jeta|rabia|coraje}", 2),
        ("{tiene|tienen} {un morro|mucho morro|mucha cara|una jeta}", 2),
        ("me cae {fatal|como el culo|como una patada}", 2), ("le tengo mania", 2),
        ("no {lo|la|los|las|le|les} {soporto|aguanto|trago}", 2),
        ("me tiene {frito|frita|harto|harta|negro|negra|hasta las narices}", 3),
        ("estoy mosca", 2), ("me hierve la sangre", 3), ("me lleva el demonio", 3),
        ("me llevan los demonios", 3),
    ],
    "tristeza": [
        ("de {bajon|bajona|capa caida}", 2), ("{que|menudo|vaya} {bajon|bajona|palo|chasco}", 2),
        ("depre", 2), ("deprimidisim*", 3),
        ("de puta pena", 3), ("hech{o|a} {una mierda|mierda|trizas|un trapo|una pena|un asco|polvo}", 3),
        ("por los suelos", 3), ("con la moral por los suelos", 3),
        ("jodido", 2), ("jodida", 2), ("estoy {tocado|tocada}", 2),
        ("en la mierda", 2), ("en el pozo", 2), ("{he tocado|tocar|toque} fondo", 3),
        ("se me {cae|ha caido|cayo} el mundo {encima|a los pies}", 3),
        ("con el corazon {roto|partido}", 3), ("{me|se me} {parte|rompe} el {alma|corazon}", 3),
        ("que {pena|lastima}", 2), ("un nudo en la garganta", 2), ("sin fuerzas", 2),
        ("no levanto cabeza", 3), ("no tengo ganas de nada", 3),
        ("{echando|echaba|echo} de menos", 2), ("llorando como una magdalena", 3),
        ("hundid{o|a} en la miseria", 3), ("hecho polvo", 2), ("chafad{o|a}", 2),
        ("no puedo con mi alma", 3), ("{un|menudo|vaya} dia de perros", 2),
        ("no puedo con mi vida", 3),
    ],
    "miedo": [
        ("me cago de miedo", 3), ("{cagado|cagada|muerto|muerta} de miedo", 3),
        ("{acojonado|acojonada|acojona|acojonan|acojone}", 3), ("me da acojone", 3),
        ("estoy {cagado|cagada}", 2), ("canguelo", 2),
        ("me da {cosa|yuyu|repelus|mal rollo}", 1),
        ("se me {pone|ponen} los pelos de punta", 2), ("con el corazon en un puno", 2),
        ("me tiembla todo", 2), ("con el miedo en el cuerpo", 3),
    ],
    "ansiedad": [
        ("hasta arriba", 2), ("con el agua al cuello", 3), ("de los nervios", 2),
        ("histeric{o|a}", 2),
        ("{me como|comiendome|me estoy comiendo|me comia} {la cabeza|el coco|la olla|el tarro}", 2),
        ("comida de {cabeza|coco|olla|tarro}", 2), ("comedera de cabeza", 2),
        ("un nudo en el estomago", 2), ("con el estomago encogido", 2),
        ("no doy abasto", 2), ("como pollo sin cabeza", 2), ("{voy|ando} de culo", 2),
        ("se me cae la casa encima", 2), ("me ahogo", 2), ("{un|en un} sinvivir", 3),
        ("sin vivir", 2), ("me estoy rallando", 2), ("me estoy rayando", 2),
        ("rayadisim*", 3), ("agobiadisim*", 3), ("taquicardia", 2),
        ("mal rollo", 1),
    ],
    "alegria": [
        ("de {puta madre|pm|perlas|fabula|maravilla}", 3), ("de lujo", 2),
        ("como {unas castanuelas|un nino con zapatos nuevos|una moto|una rosa}", 3),
        ("no quepo en mi de {alegria|felicidad|gozo}", 3), ("en el septimo cielo", 3),
        ("en una nube", 2),
        ("mola {mazo|mogollon|un monton|cantidad|un huevo}", 2), ("mola", 1), ("molan", 1),
        ("guay", 2), ("chachi", 2), ("chuli*", 2), ("flipante", 2), ("ilu", 1),
        ("que {guay|ilu|chulo|pasada|gozada|maravilla|alegria|suerte|bien}", 2),
        ("una {pasada|gozada|maravilla}", 2), ("es la leche", 2), ("buen rollo", 2),
        ("{me lo he pasado|lo he pasado|me lo pase|lo pase|pasarlo|me lo paso|pasandolo} "
         "{bomba|pipa|genial|de lujo|en grande|de miedo|teta|de puta madre}", 3),
        ("felicisim*", 3), ("que te cagas", 2), ("de la hostia", 1),
        # La sorpresa es de quien la recibe; quien la prepara siente ilusión
        ("{le he dado|le di|le voy a dar|darle|le he preparado|le prepare|le preparo} una sorpresa", 2),
        ("fiesta sorpresa", 1),
    ],
    "serenidad": [
        ("en la gloria", 2), ("{estoy|me siento|vivo|estamos} como dios", 2),
        ("{me he quedado|me quede|quede|me quedo|te quedas} como {dios|nuevo|nueva|un rey|una reina}", 3),
        ("de relax", 2), ("de chill", 2),
        ("{me he quitado|me quite|quitado|quitarme} un peso de encima", 3),
        ("mas ancho que largo", 2), ("tan pancho", 2), ("tan pancha", 2),
    ],
    "amor": [
        ("{colado|colada|pillado|pillada|loco|loca} por", 3),
        ("mariposas en el estomago", 3), ("mi media naranja", 2), ("te quiero mazo", 3),
        ("{te|os} quiero un monton", 3), ("tq", 2), ("tqm", 3), ("tkm", 3),
    ],
    "esperanza": [
        ("cruzo los dedos", 2), ("{crucemos|cruzando} los dedos", 2), ("tengo fe", 2),
        ("con ganas", 1), ("con mucha ilusion", 2),
    ],
    "sorpresa": [
        ("me he quedado {loco|loca|flipando|de piedra|a cuadros|muerto|muerta|pasmado|pasmada|"
         "de pasta de boniato|planchado|planchada|sin palabras}", 3),
        ("a cuadros", 2), ("de piedra", 2), ("flipando en colores", 3),
        ("alucinando pepinillos", 3), ("acojonante", 2), ("que fuerte", 2),
        ("no me jodas", 2), ("anda ya", 2), ("madre mia", 1), ("ostras", 1),
    ],
    "asco": [
        ("{me da|da|que} {asco|grima|repelus|arcadas|pota}", 3),
        ("me {revuelve|revuelven} el estomago", 3), ("potar", 2), ("guarr*", 2),
        ("cerdada", 2), ("me da mal cuerpo", 2),
    ],
    "verguenza": [
        ("{que|menudo|vaya} {corte|bochorno|apuro}", 2), ("me muero de verguenza", 3),
        ("tragame tierra", 3), ("{rojo|roja} como un tomate", 2), ("pasar apuro", 2),
        ("bochorno", 2), ("me quiero morir de verguenza", 3),
        ("me queria morir de verguenza", 3),
    ],
    "culpa": [
        ("me siento fatal por", 3), ("me siento mal por", 3),
        ("{la he cagado|la cague|la hemos cagado|la cagamos}", 3),
        ("{la he liado|la lie|la he liado parda}", 2),
        ("{meti|he metido|metido|metimos} la pata", 3), ("mea culpa", 2),
        ("cargo de conciencia", 3), ("no me lo perdono", 3), ("me remuerde la conciencia", 3),
        ("no puedo mirar{la|lo|le|los|las|te} a la cara", 3), ("se me cae la cara de verguenza", 3),
    ],
    "soledad": [
        ("mas {solo|sola} que la una", 3), ("{solo|sola} como un perro", 3),
        ("{pasan|pasa|pasais} de mi", 3), ("nadie me hace caso", 3),
        ("me {dejan|dejais|dejaron} de lado", 3), ("me {ignoran|ignorais}", 3),
        ("me {han dejado|dejaron} {tirado|tirada}", 3), ("me {han dado|dieron} de lado", 3),
        ("me siento un bicho raro", 2),
    ],
}


def expresiones_expandidas():
    """{emoción: [(expresión, peso), ...]} con todas las plantillas expandidas."""
    resultado = {}
    for emocion, entradas in EXPRESIONES.items():
        lista = []
        for plantilla, peso in entradas:
            lista += [(e, peso) for e in expandir(plantilla)]
        resultado[emocion] = lista
    return resultado


# ---------------------------------------------------------------------------
# ¿Copiar los tacos de la persona?
#   True  -> "estoy hasta la polla" -> "estás hasta la polla"   (mismo registro)
#   False -> "estoy hasta la polla" -> "estás hasta las narices" (eufemismo)
# Nunca se copian INSULTOS ("soy un desastre", "es un gilipollas"): eso no es
# registro, es negatividad.
# ---------------------------------------------------------------------------
ESPEJO_TACOS = True

# ¿El sistema usa emojis en sus respuestas? (los de la persona se respetan siempre)
ESPEJO_EMOJIS = False

# Eufemismos: misma cercanía y misma idea, sin el taco (si ESPEJO_TACOS = False)
EUFEMISMOS = {}
for _e in expandir("hasta {" + _HASTA_VULGAR + "}"):
    EUFEMISMOS[_e] = "hasta las narices"
EUFEMISMOS.update({
    "de puta pena": "de bajón", "en la mierda": "por los suelos",
    "hecho una mierda": "hecho polvo", "hecha una mierda": "hecha polvo",
    "hecho mierda": "hecho polvo", "hecha mierda": "hecha polvo",
    "jodido": "fastidiado", "jodida": "fastidiada",
    "de mala hostia": "de mala leche", "de mala ostia": "de mala leche",
    "acojonado": "muerto de miedo", "acojonada": "muerta de miedo",
    "cagado": "muerto de miedo", "cagada": "muerta de miedo",
    "cagado de miedo": "muerto de miedo", "cagada de miedo": "muerta de miedo",
    "de puta madre": "genial", "de pm": "genial", "que te cagas": "genial",
})

# Expresiones limpias que se pueden reflejar TAL CUAL ("estoy hasta el moño" -> "estás hasta el moño")
REFLEJABLES_EXPR = (
    expandir("hasta {" + _HASTA_LIMPIO + "}") +
    expandir("de {bajon|bajona|capa caida|buenas|mala leche|los nervios|relax|lujo|diez|maravilla}") +
    expandir("hech{o|a} {polvo|trizas|un trapo}") +
    expandir("{muerto|muerta} de miedo") + expandir("mas {solo|sola} que la una") +
    expandir("{colado|colada|pillado|pillada} por") +
    ["por los suelos", "con la moral por los suelos", "hasta arriba", "con el agua al cuello",
     "en una nube", "en la gloria", "como unas castanuelas", "a cuadros", "de piedra",
     "flipando", "como dios", "a tope", "mosca", "depre", "chafado", "chafada",
     "tan pancho", "tan pancha", "en el septimo cielo", "como una moto"]
)

# Expresiones con "me" + verbo en 3ª persona que se pueden devolver cambiando
# "me" por "te"/"le": "me toca los huevos" -> "te toca los huevos".
VERBOS_ESPEJO = {"toca", "tocan", "saca", "sacan", "pone", "ponen", "jode", "joden", "tiene",
                 "tienen", "cae", "da", "revuelve", "revuelven", "hierve", "lleva", "llevan",
                 "parte", "rompe", "raya", "agobia", "come"}

# Palabras malsonantes (para el estilo: se detectan, nunca se copian)
VULGARES = [
    "joder", "jodid*", "mierda", "puta", "putas", "puto", "putos", "putada", "hostia*", "ostia*",
    "cojon*", "cono", "gilipoll*", "cabron*", "capull*", "me cago", "follar", "polla", "pollas",
    "carajo", "acojon*", "mamon*", "hasta los huevos", "toca los huevos", "tocan los huevos",
    "hasta las pelotas", "hasta el culo", "hasta las tetas", "como el culo", "de culo",
]
