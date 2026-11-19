"""
Léxico emocional.

Formato de cada entrada: (palabra, peso)
  - peso: 1 = suave, 2 = normal, 3 = fuerte.
  - Si termina en '*' es una RAÍZ: 'alegr*' -> alegre, alegría, alegrarse...
  - Si tiene espacios es una EXPRESIÓN: 'echo de menos'.
  - Todo en minúsculas y SIN tildes (el texto también se normaliza así).

Por qué 13 emociones y no 6:
  Un psicólogo distingue matices. "Estoy triste", "me siento sola" y "es culpa
  mía" son cosas distintas y piden respuestas distintas. A esto se le llama
  GRANULARIDAD EMOCIONAL (Lisa Feldman Barrett): cuanto más finamente se
  nombran las emociones, mejor se pueden entender y regular.
  Además de las básicas (alegría, tristeza, ira, miedo, sorpresa, asco)
  añadimos:
    - serenidad, amor, esperanza  -> emociones positivas (no todo es "alegría")
    - soledad                     -> tristeza ligada a la falta de vínculo
    - ansiedad                    -> miedo difuso, a algo que *podría* pasar
    - culpa, vergüenza            -> emociones "autoconscientes": juzgarse a uno mismo
"""

EMOCIONES = {
    "alegria": [
        ("feliz", 2), ("felices", 2), ("felicidad", 2), ("alegr*", 2), ("content*", 2),
        ("encant*", 2), ("genial", 2), ("maravill*", 3), ("fantastic*", 3),
        ("estupend*", 2), ("emocionad*", 2), ("disfrut*", 2), ("divert*", 2),
        ("risa", 1), ("reir", 1), ("riendo", 1), ("sonri*", 1), ("gusta", 1),
        ("perfect*", 2), ("euforic*", 3), ("entusiasm*", 2), ("orgullos*", 2),
        ("bien", 1), ("mejor", 1), ("increible", 1), ("estoy a tope", 2),
        ("happy", 2), ("glad", 2), ("joy*", 2), ("great", 2), ("wonderful", 3),
        ("amazing", 3), ("excited", 2), ("fun", 1),
    ],
    "serenidad": [
        ("tranquil*", 2), ("tranqui", 2), ("calm*", 2), ("relajad*", 2), ("paz", 2), ("en paz", 2),
        ("seren*", 2), ("descansad*", 1), ("a gusto", 2), ("aliviad*", 2), ("alivio", 2),
        ("equilibr*", 1), ("comod*", 1),
        ("relaxed", 2), ("peaceful", 2),
    ],
    "amor": [
        ("amo", 2), ("amor", 2), ("te quiero", 3), ("os quiero", 3), ("le quiero", 2),
        ("la quiero", 2), ("lo quiero", 2), ("quiero mucho", 2), ("carino", 2),
        ("carinos*", 2), ("adoro", 3), ("enamorad*", 3), ("abraz*", 1), ("beso", 1),
        ("besos", 1), ("afecto", 2), ("ternura", 2), ("agradecid*", 2), ("gracias", 1),
        ("love", 2), ("adore", 3), ("grateful", 2),
    ],
    "esperanza": [
        ("esperanz*", 2), ("ilusion*", 2), ("ojala", 1), ("espero", 1),
        ("motivad*", 2), ("optimis*", 2), ("confio", 2), ("confianza", 1),
        ("animad*", 1), ("ganas de", 1), ("saldra bien", 2), ("va a salir bien", 2),
        ("lo conseguire", 2), ("podre", 1), ("seguir adelante", 2),
        # Deseo: "quiero / necesito / me gustaría..." = ganas, motivación
        ("solo quiero", 1), ("quiero un", 1), ("quiero una", 1), ("quiero que", 1),
        ("necesito un", 1), ("necesito una", 1), ("necesito que", 1), ("me gustaria", 1),
        ("me encantaria", 2), ("tengo ganas de", 2),
        ("hope*", 2), ("optimistic", 2),
    ],
    "sorpresa": [
        ("sorpr*", 2), ("asombr*", 2), ("impresionad*", 2), ("inesperad*", 2),
        ("alucin*", 2), ("flip*", 2), ("wow", 2), ("guau", 2), ("vaya", 1),
        ("de repente", 1), ("no me lo puedo creer", 3), ("no me lo creo", 2),
        ("atonit*", 3), ("boquiabiert*", 3),
        ("surpris*", 2), ("shock*", 2), ("unexpected", 2), ("omg", 2),
    ],
    "tristeza": [
        ("triste*", 2), ("tristeza", 2), ("llor*", 2), ("deprimid*", 3), ("depres*", 3),
        ("pena", 2), ("dolor", 2), ("duele", 2), ("sufr*", 2), ("desanim*", 2),
        ("melancol*", 2), ("nostalg*", 1), ("echo de menos", 2), ("extrano", 1),
        ("vacio", 2), ("vacia", 2), ("infeliz", 2), ("desgraci*", 2),
        ("decepcion*", 2), ("lament*", 1), ("destrozad*", 3), ("hundid*", 3),
        ("roto", 2), ("rota", 2), ("desolad*", 3), ("sin ganas", 2), ("apati*", 2),
        # "mal" solo cuenta como emoción cuando describe a la persona
        # ("estoy mal"), no en "me ha salido mal".
        ("cansad*", 1), ("agotad*", 1), ("estoy mal", 2), ("me siento mal", 2),
        ("me encuentro mal", 2), ("fatal", 2),
        ("no puedo mas", 3), ("ya no puedo mas", 3), ("no aguanto mas", 3),
        ("hecho polvo", 2), ("hecha polvo", 2), ("de bajon", 2), ("chof", 1), ("plof", 1),
        ("sad", 2), ("unhappy", 2), ("cry*", 2), ("depress*", 3), ("hurt", 2),
    ],
    "soledad": [
        ("me siento solo", 3), ("me siento sola", 3), ("estoy solo", 2), ("estoy sola", 2),
        ("soledad", 3), ("solitari*", 2), ("aislad*", 2), ("abandonad*", 3),
        ("nadie me entiende", 3), ("nadie me escucha", 3), ("no tengo a nadie", 3),
        ("nadie me quiere", 3), ("excluid*", 2), ("ignorad*", 2), ("invisible", 2),
        ("desconectad*", 1),
        ("lonely", 3), ("alone", 2), ("isolated", 2),
    ],
    "ira": [
        # La FRUSTRACIÓN se incluye aquí: es la ira que aparece cuando algo
        # bloquea lo que queremos conseguir.
        ("enfad*", 2), ("enoj*", 2), ("furi*", 3), ("rabia", 3), ("rabios*", 3),
        ("odio", 3), ("odia", 3), ("odiar", 3), ("odian", 3), ("ira", 3),
        ("molest*", 1), ("irrit*", 2), ("cabread*", 2), ("cabrea*", 2), ("harto", 2),
        ("harta", 2), ("hartaz*", 2), ("indign*", 2), ("injust*", 2), ("frustr*", 2),
        ("impotencia", 2), ("idiota", 2), ("imbecil", 3), ("maldit*", 2),
        ("insoportable", 2), ("me revienta", 3), ("me saca de quicio", 3),
        ("quemad*", 1), ("mosquead*", 2), ("rebotad*", 2),
        ("angry", 2), ("mad", 2), ("hate", 3), ("furious", 3), ("annoy*", 1), ("rage", 3),
    ],
    "miedo": [
        # Miedo = ante una amenaza concreta y presente.
        ("mied*", 2), ("asust*", 2), ("terror*", 3), ("aterr*", 3), ("panico", 3),
        ("pavor", 3), ("temo", 2), ("temer*", 2), ("temor", 2), ("horror*", 2),
        ("espant*", 2), ("peligro*", 2), ("amenaz*", 2),
        ("afraid", 2), ("scared", 2), ("fear*", 2), ("terrified", 3), ("panic", 3),
    ],
    "ansiedad": [
        # Ansiedad = miedo difuso, anticipando algo que *podría* pasar.
        ("ansiedad", 3), ("ansios*", 2), ("angusti*", 3), ("agobi*", 2), ("estres*", 2),
        ("nervios*", 1), ("preocup*", 1), ("inquiet*", 1), ("intranquil*", 2),
        ("tens*", 1), ("presion", 1), ("bloquead*", 1), ("no puedo dormir", 2),
        ("rayad*", 2), ("rallad*", 2), ("me raya", 2), ("me rayo", 2),
        ("sin dormir", 2), ("estoy a tope de trabajo", 2), ("estoy a tope de curro", 2),
        ("a tope de trabajo", 2), ("a tope de curro", 2),
        ("insomnio", 2), ("no paro de pensar", 2), ("ataque de ansiedad", 3),
        ("anxious", 2), ("anxiety", 3), ("worried", 1), ("stress*", 2), ("nervous", 1),
        ("overwhelm*", 2),
    ],
    "culpa": [
        # Culpa = "he hecho algo malo" (se centra en la ACCIÓN).
        ("culpa", 2), ("culpable", 3), ("remordimiento*", 3), ("arrepent*", 2),
        ("me arrepiento", 3), ("deberia haber", 2), ("no deberia haber", 2),
        ("lo siento", 1), ("perdon", 1),
        ("guilty", 3), ("guilt", 3), ("regret*", 2),
    ],
    "verguenza": [
        # Vergüenza = "soy malo/a" (se centra en la PERSONA). Es más dañina que
        # la culpa porque ataca la identidad (Brené Brown, June Tangney).
        ("verguenza", 3), ("avergonzad*", 3), ("humill*", 3), ("ridicul*", 2),
        ("me da corte", 2), ("patetic*", 2), ("fracasad*", 2), ("inutil", 2),
        ("no valgo", 3), ("no valgo nada", 3), ("inferior", 2),
        ("ashamed", 3), ("embarrass*", 2), ("humiliat*", 3), ("worthless", 3),
    ],
    "asco": [
        ("asco", 3), ("asquer*", 3), ("repugn*", 3), ("repuls*", 3), ("nausea*", 2),
        ("vomit*", 2), ("puaj", 2), ("desagrad*", 2), ("podrid*", 2), ("apest*", 2),
        ("grima", 2), ("me da asco", 3),
        ("disgust*", 3), ("gross", 2), ("yuck", 2),
    ],
}

# Añadimos las expresiones idiomáticas del español (expresiones.py)
from expresiones import expresiones_expandidas  # noqa: E402

for _emocion, _lista in expresiones_expandidas().items():
    EMOCIONES[_emocion].extend(_lista)

# ---------------------------------------------------------------------------
# Modelo circumplejo de Russell (1980): toda emoción se puede situar en dos ejes
#   VALENCIA  (-1 desagradable ... +1 agradable)
#   ACTIVACIÓN (-1 apagado/baja energía ... +1 agitado/alta energía)
# Ej: la ira y la tristeza son ambas negativas, pero la ira "activa" y la
# tristeza "apaga". Un psicólogo distingue eso enseguida.
# ---------------------------------------------------------------------------
CIRCUMPLEJO = {
    #              valencia  activación
    "alegria":     (0.8,     0.5),
    "serenidad":   (0.6,    -0.6),
    "amor":        (0.8,     0.2),
    "esperanza":   (0.6,     0.1),
    "sorpresa":    (0.1,     0.8),
    "tristeza":    (-0.7,   -0.4),
    "soledad":     (-0.6,   -0.3),
    "ira":         (-0.6,    0.8),
    "miedo":       (-0.7,    0.7),
    "ansiedad":    (-0.6,    0.6),
    "culpa":       (-0.6,    0.1),
    "verguenza":   (-0.7,    0.3),
    "asco":        (-0.7,    0.3),
}

POSITIVAS = {e for e, (v, _) in CIRCUMPLEJO.items() if v > 0.3}
NEGATIVAS = {e for e, (v, _) in CIRCUMPLEJO.items() if v < -0.3}

NOMBRES = {
    "alegria": "Alegría", "serenidad": "Serenidad", "amor": "Amor/afecto",
    "esperanza": "Esperanza", "sorpresa": "Sorpresa", "tristeza": "Tristeza",
    "soledad": "Soledad", "ira": "Ira/frustración", "miedo": "Miedo",
    "ansiedad": "Ansiedad", "culpa": "Culpa", "verguenza": "Vergüenza", "asco": "Asco",
    "neutral": "Neutral",
}

ICONOS = {
    "alegria": "😊", "serenidad": "😌", "amor": "🥰", "esperanza": "🌱", "sorpresa": "😮",
    "tristeza": "😢", "soledad": "🫥", "ira": "😠", "miedo": "😨", "ansiedad": "😰",
    "culpa": "😔", "verguenza": "😳", "asco": "🤢", "neutral": "😐",
}

# Emojis -> (emoción, peso)
EMOJIS = {
    "😀": ("alegria", 2), "😃": ("alegria", 2), "😄": ("alegria", 2), "😁": ("alegria", 2),
    "😊": ("alegria", 2), "🙂": ("alegria", 1), "😂": ("alegria", 2), "🎉": ("alegria", 2),
    ":)": ("alegria", 1), "😌": ("serenidad", 2), "😍": ("amor", 3), "🥰": ("amor", 3),
    "❤": ("amor", 2), "💕": ("amor", 2), "🙏": ("amor", 1), "🤞": ("esperanza", 2),
    "😢": ("tristeza", 2), "😭": ("tristeza", 3), "😞": ("tristeza", 2), "😔": ("tristeza", 2),
    "💔": ("tristeza", 3), ":(": ("tristeza", 1),
    "😠": ("ira", 2), "😡": ("ira", 3), "🤬": ("ira", 3),
    "😨": ("miedo", 2), "😱": ("sorpresa", 2), "😰": ("ansiedad", 2), "😟": ("ansiedad", 1),
    "😮": ("sorpresa", 2), "😲": ("sorpresa", 2), "🤯": ("sorpresa", 2),
    "😳": ("verguenza", 2), "🤢": ("asco", 3), "🤮": ("asco", 3),
}

# Palabras que niegan lo que viene detrás ("no estoy feliz")
NEGACIONES = {"no", "nunca", "jamas", "tampoco", "ni", "sin", "not", "never", "dont"}

# Palabras que modulan la intensidad de la emoción que viene detrás
INTENSIFICADORES = {
    "muy": 1.5, "mucho": 1.5, "muchisimo": 2.0, "super": 1.7, "demasiado": 1.7,
    "tan": 1.5, "tanto": 1.5, "bastante": 1.3, "realmente": 1.4, "totalmente": 1.6,
    "increiblemente": 1.8, "extremadamente": 2.0, "very": 1.5, "so": 1.5, "really": 1.4,
    # coloquiales
    "mazo": 1.6, "mogollon": 1.6, "cantidad": 1.4, "tela": 1.4, "hiper": 1.6, "requete": 1.6,
    "jodidamente": 1.7, "full": 1.5, "re": 1.3, "tope": 1.5,
    "poco": 0.5, "algo": 0.6, "ligeramente": 0.5, "apenas": 0.4, "little": 0.5,
}

# Qué ocurre al negar una emoción:
#   "no estoy feliz"          -> tristeza (a mitad de fuerza)
#   "no tengo esperanza"      -> tristeza (desesperanza)
#   "no estoy tranquila"      -> ansiedad
#   el resto ("no tengo miedo") simplemente se anula.
OPUESTOS = {
    "alegria": "tristeza", "tristeza": "alegria", "esperanza": "tristeza",
    "serenidad": "ansiedad", "ansiedad": "serenidad",
}

# Palabras de CONTRASTE. Lo que va después de "pero" suele ser lo que la persona
# siente de verdad: "Estoy bien, pero no puedo más".
CONTRASTE = {"pero", "sin_embargo", "but"}
