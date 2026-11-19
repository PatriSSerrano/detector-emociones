"""
Diccionario (léxico) de emociones.

Cada emoción tiene una lista de (palabra, peso):
  - El peso indica la fuerza de la palabra (1 = suave, 2 = normal, 3 = fuerte).
  - Si la palabra termina en '*' es una RAÍZ: coincide con cualquier palabra que
    empiece así. Ej: 'alegr*' -> alegre, alegría, alegrarse, alegremente...
  - Todo va en minúsculas y SIN tildes (el detector también quita las tildes
    del texto, así 'alegría' y 'alegria' son lo mismo).
"""

EMOCIONES = {
    "alegria": [
        ("feliz", 2), ("felices", 2), ("felicidad", 2), ("alegr*", 2), ("content*", 2),
        ("encant*", 2), ("genial", 2), ("maravill*", 3), ("fantastic*", 3),
        ("increible", 2), ("estupend*", 2), ("emocionad*", 2), ("ilusion*", 2),
        ("disfrut*", 2), ("divert*", 2), ("risa", 1), ("reir", 1), ("riendo", 1), ("sonri*", 1),
        ("amo", 2), ("amor", 2), ("gusta", 1), ("encanta", 2),
        ("bien", 1), ("bueno", 1), ("buena", 1), ("mejor", 1), ("perfect*", 2),
        ("orgullos*", 2), ("agradecid*", 2), ("gracias", 1), ("euforic*", 3),
        # inglés
        ("happy", 2), ("joy*", 2), ("glad", 2), ("love", 2), ("great", 2),
        ("wonderful", 3), ("amazing", 3), ("excited", 2), ("fun", 1),
    ],
    "tristeza": [
        ("triste*", 2), ("tristeza", 2), ("llor*", 2), ("deprim*", 3), ("depresion", 3),
        ("me siento solo", 2), ("me siento sola", 2), ("soledad", 2), ("pena", 2), ("dolor", 2),
        ("duele", 2), ("sufr*", 2), ("desanim*", 2), ("desesper*", 3),
        ("melancol*", 2), ("nostalg*", 1), ("extran*", 1), ("echo de menos", 2),
        ("perdi", 1), ("perdida", 1), ("vacio", 2), ("infeliz", 2), ("desgraci*", 2),
        ("decepcion*", 2), ("lament*", 2), ("destroz*", 3), ("hundid*", 3),
        ("mal", 1), ("fatal", 2),
        # inglés
        ("sad", 2), ("unhappy", 2), ("cry*", 2), ("depress*", 3), ("lonely", 2),
        ("miss", 1), ("hurt", 2),
    ],
    "ira": [
        ("enfad*", 2), ("enoj*", 2), ("furi*", 3), ("rabia", 3), ("odi*", 3),
        ("ira", 3), ("molest*", 1), ("irrit*", 2), ("cabre*", 2), ("harto", 2),
        ("harta", 2), ("indign*", 2), ("injust*", 2), ("idiota", 2), ("estupid*", 2),
        ("imbecil", 3), ("maldit*", 2), ("asqueroso", 1), ("grit*", 1),
        ("insoportable", 2), ("frustr*", 2), ("verguenza", 1),
        # inglés
        ("angry", 2), ("mad", 2), ("hate", 3), ("furious", 3), ("annoy*", 1),
        ("rage", 3),
    ],
    "miedo": [
        ("mied*", 2), ("asust*", 2), ("terror*", 3), ("aterr*", 3), ("panico", 3),
        ("pavor", 3), ("temo", 2), ("temer*", 2), ("temor", 2), ("nervios*", 1),
        ("ansiedad", 2), ("ansios*", 2), ("angusti*", 2), ("preocup*", 1),
        ("inquiet*", 1), ("insegur*", 1), ("peligro*", 2), ("amenaz*", 2),
        ("horror*", 3), ("espant*", 2),
        # inglés
        ("afraid", 2), ("scared", 2), ("fear*", 2), ("terrified", 3), ("anxious", 2),
        ("worried", 1), ("panic", 3),
    ],
    "sorpresa": [
        ("sorpr*", 2), ("asombr*", 2), ("impresion*", 2), ("inesperad*", 2),
        ("increible", 1), ("alucin*", 2), ("flip*", 2), ("wow", 2), ("guau", 2),
        ("vaya", 1), ("de repente", 1), ("no me lo puedo creer", 3),
        ("impact*", 2), ("atonit*", 3), ("boquiabiert*", 3),
        # inglés
        ("surpris*", 2), ("shock*", 2), ("unexpected", 2), ("omg", 2),
    ],
    "asco": [
        ("asco", 3), ("asquer*", 3), ("repugn*", 3), ("repuls*", 3), ("nausea*", 2),
        ("vomit*", 2), ("puaj", 2), ("agg*", 1), ("desagrad*", 2), ("podrid*", 2),
        ("apest*", 2), ("grima", 2), ("horrible", 1), ("cerdo", 1),
        # inglés
        ("disgust*", 3), ("gross", 2), ("yuck", 2),
    ],
}

# Emojis -> (emoción, peso)
EMOJIS = {
    "😀": ("alegria", 2), "😃": ("alegria", 2), "😄": ("alegria", 2), "😁": ("alegria", 2),
    "😊": ("alegria", 2), "🙂": ("alegria", 1), "😍": ("alegria", 3), "🥰": ("alegria", 3),
    "😂": ("alegria", 2), "❤": ("alegria", 2), "🎉": ("alegria", 2), ":)": ("alegria", 1),
    "😢": ("tristeza", 2), "😭": ("tristeza", 3), "😞": ("tristeza", 2), "😔": ("tristeza", 2),
    "💔": ("tristeza", 3), ":(": ("tristeza", 1),
    "😠": ("ira", 2), "😡": ("ira", 3), "🤬": ("ira", 3), "💢": ("ira", 2),
    "😨": ("miedo", 2), "😰": ("miedo", 2), "😟": ("miedo", 1),
    # 😱 es "cara de terror", pero en la práctica se usa sobre todo como "¡qué fuerte!"
    "😱": ("sorpresa", 2),
    "😮": ("sorpresa", 2), "😲": ("sorpresa", 2), "🤯": ("sorpresa", 3), "😯": ("sorpresa", 1),
    "🤢": ("asco", 3), "🤮": ("asco", 3), "😖": ("asco", 1),
}

# Palabras que niegan lo que viene detrás ("no estoy feliz")
NEGACIONES = {"no", "nunca", "jamas", "tampoco", "ni", "nada", "sin", "not", "never", "dont", "don't"}

# Palabras que cambian la intensidad de la siguiente emoción
INTENSIFICADORES = {
    "muy": 1.5, "mucho": 1.5, "muchisimo": 2.0, "super": 1.7, "demasiado": 1.7,
    "tan": 1.5, "tanto": 1.5, "bastante": 1.3, "realmente": 1.4, "totalmente": 1.6,
    "increiblemente": 1.8, "extremadamente": 2.0, "very": 1.5, "so": 1.5, "really": 1.4,
    "poco": 0.5, "algo": 0.6, "ligeramente": 0.5, "apenas": 0.4, "little": 0.5,
}

# Qué pasa con una emoción cuando se niega:
#   "no estoy feliz"  -> tristeza (a mitad de fuerza)
#   "no estoy triste" -> alegría  (a mitad de fuerza)
#   el resto (no tengo miedo, no me enfada...) simplemente se anula.
OPUESTOS = {"alegria": "tristeza", "tristeza": "alegria"}
