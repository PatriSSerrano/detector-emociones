"""
Genera la respuesta a la persona: OBJETIVA y adaptada a SU forma de expresarse.

Principios (lo que haría un buen psicólogo):
  1. ACOMPASAR LA FORMA, NO EL MALESTAR
     - Mismo registro (formal, neutro, cercano, coloquial), tú o usted, emojis
       si los usa y una longitud parecida a la de su mensaje.
     - Reutiliza su autodescripción ("estoy rayada" -> "estás rayada").
     - Pero NUNCA copia: palabrotas, insultos hacia uno mismo, palabras
       absolutistas ("siempre", "nunca", "nada") ni intensificadores del malestar.
  2. OBJETIVIDAD
     - Se basa en lo que la persona ha dicho ("Por lo que cuentas...").
     - Separa HECHOS de INTERPRETACIONES ("todavía no ha pasado, así que no
       sabemos cómo va a salir").
     - Nada de falsos ánimos ("seguro que todo irá bien"): no son objetivos.
  3. UNA SOLA PREGUNTA al final, para invitar a seguir hablando.
"""

import re
import unicodedata

from utils import normalizar

# Conjugaciones para tú / usted. Se usan con .format(**CONJ[tratamiento])
CONJ = {
    "tu": {"te": "te", "cuentas": "cuentas", "estas": "estás", "tienes": "tienes",
           "sientes": "sientes", "dices": "dices"},
    "usted": {"te": "le", "cuentas": "cuenta", "estas": "está", "tienes": "tiene",
              "sientes": "siente", "dices": "dice"},
}

# ---------------------------------------------------------------------------
# 1. Apertura: según la valencia del mensaje y el registro
# ---------------------------------------------------------------------------
APERTURAS = {
    "positiva": {
        "formal": ["Me alegra saberlo."],
        "neutro": ["Me alegra leerlo.", "Qué buena noticia."],
        "cercano": ["¡Qué bien!", "¡Qué buena noticia!"],
        "coloquial": ["¡Qué guay!", "¡Qué bien!"],
    },
    "negativa": {
        "formal": ["Gracias por contármelo.", "Entiendo lo que me {cuentas}."],
        "neutro": ["Entiendo.", "Gracias por contarlo."],
        "cercano": ["Vale, {te} entiendo.", "Vaya, entiendo."],
        "coloquial": ["Uf, vale.", "Vaya tela."],
    },
    "neutral": {
        "formal": ["Entendido."],
        "neutro": ["De acuerdo."],
        "cercano": ["Vale."],
        "coloquial": ["Vale, {te} sigo."],
    },
}

# ---------------------------------------------------------------------------
# 2. Reflejo de la emoción, en lenguaje moderado (sin intensificar).
#    (frase tú/usted, frase coloquial, conector para el tema)
#    conector: "con" -> "... con lo del examen" · "" -> "... lo del examen" · None -> sin tema
# ---------------------------------------------------------------------------
REFLEJOS = {
    "alegria":   ("{te} ha alegrado", "{te} ha alegrado un montón", ""),
    "serenidad": ("{estas} en calma", "{estas} tranqui", "con"),
    "amor":      ("se nota el cariño", "se nota el cariño", "por"),
    "esperanza": ("{tienes} ilusión", "{tienes} ganas", "con"),
    "sorpresa":  ("no {te} esperabas", "{te} ha pillado por sorpresa", ""),
    "tristeza":  ("{estas} pasando un momento triste", "{estas} de bajón", "con"),
    "soledad":   ("echas en falta a alguien con quien contar",
                  "{te} falta gente con la que hablar", None),
    "ira":       ("{te} ha molestado", "{te} ha sentado mal", ""),
    "miedo":     ("{te} da miedo", "{te} da miedo", ""),
    "ansiedad":  ("{tienes} bastante preocupación", "{tienes} un buen agobio", "con"),
    "culpa":     ("{te} {sientes} responsable", "{te} {sientes} culpable", "con"),
    "verguenza": ("{te} {estas} juzgando con mucha dureza",
                  "{te} {estas} juzgando con mucha dureza", None),
    "asco":      ("{te} ha producido rechazo", "{te} ha dado mucho rechazo", ""),
}
# Corrección para usted: "echas en falta" no lleva pronombre
REFLEJOS_USTED = {"soledad": "echa en falta a alguien con quien contar"}
# Cuando no hay tema, algunas frases quedan cojas ("te ha alegrado."): alternativas
SIN_TEMA = {
    "alegria": ("se nota la alegría", "{estas} a tope"),
    "sorpresa": ("no {te} lo esperabas", "{te} ha pillado por sorpresa"),
    "ira": ("se nota el enfado", "{te} ha sentado mal"),
    "miedo": ("hay algo que {te} da miedo", "hay algo que {te} da miedo"),
    "asco": ("hay algo que {te} produce rechazo", "hay algo que {te} da mucho rechazo"),
}

# ---------------------------------------------------------------------------
# 3. Hechos frente a interpretaciones (reencuadres objetivos)
#    id de distorsión o señal -> (tú, usted)
# ---------------------------------------------------------------------------
REENCUADRES = {
    "minimizacion": ("Dices que estás bien, aunque no parece que del todo.",
                     "Dice que está bien, aunque no parece que del todo."),
    "minimizacion_igual": ("Dices que te da igual, aunque por cómo lo cuentas parece que sí te importa.",
                           "Dice que le da igual, aunque por cómo lo cuenta parece que sí le importa."),
    "generalizacion_personas": (
        "Sentirte así ahora no quiere decir que no haya personas que puedan entenderte.",
        "Sentirse así ahora no quiere decir que no haya personas que puedan entenderle."),
    "desesperanza": ("Ahora cuesta ver la salida, pero eso es una sensación del momento, no una certeza.",
                     "Ahora cuesta ver la salida, pero eso es una sensación del momento, no una certeza."),
    "adivinacion": ("Eso todavía no ha pasado, así que no sabemos cómo va a salir.",
                    "Eso todavía no ha pasado, así que no sabemos cómo va a salir."),
    "catastrofismo": ("En caliente es normal verlo muy negro, pero eso es cómo lo vives ahora, "
                      "no necesariamente lo que va a pasar.",
                      "En caliente es normal verlo muy negro, pero eso es cómo lo vive ahora, "
                      "no necesariamente lo que va a pasar."),
    "generalizacion": ("Que te haya pasado varias veces no quiere decir que te pase cada vez.",
                       "Que le haya pasado varias veces no quiere decir que le pase cada vez."),
    "etiquetado": ("Que algo no haya salido bien no te define como persona.",
                   "Que algo no haya salido bien no le define como persona."),
    "personalizacion": ("En lo que pasó influyeron más cosas, no solo tú.",
                        "En lo que pasó influyeron más cosas, no solo usted."),
    "lectura_mente": ("Lo que piensa la otra persona no lo sabes seguro: es lo que te imaginas.",
                      "Lo que piensa la otra persona no lo sabe seguro: es lo que se imagina."),
    "deberias": ("Te estás exigiendo bastante.", "Se está exigiendo bastante."),
    "dicotomico": ("Entre que salga perfecto y que no salga hay muchos puntos intermedios.",
                   "Entre que salga perfecto y que no salga hay muchos puntos intermedios."),
    "descalificar_positivo": ("Lo que has conseguido también tiene que ver con lo que tú has hecho.",
                              "Lo que ha conseguido también tiene que ver con lo que usted ha hecho."),
    "preocupacion": ("Te estás adelantando a cosas que todavía no han pasado.",
                     "Se está adelantando a cosas que todavía no han pasado."),
    "rumiacion": ("Darle vueltas a lo que pasó es normal, aunque no suele ayudar a resolverlo.",
                  "Darle vueltas a lo que pasó es normal, aunque no suele ayudar a resolverlo."),
    "somatizacion": ("Además lo estás notando en el cuerpo, y eso también cuenta.",
                     "Además lo está notando en el cuerpo, y eso también cuenta."),
}
# Orden de prioridad: lo más importante primero
PRIORIDAD = ["minimizacion", "desesperanza", "etiquetado", "adivinacion", "catastrofismo",
             "personalizacion", "lectura_mente", "generalizacion", "dicotomico", "deberias",
             "descalificar_positivo", "preocupacion", "rumiacion", "somatizacion"]

# ---------------------------------------------------------------------------
# 4. Recursos de la persona (lo que SÍ tiene a favor), sin falsos ánimos
# ---------------------------------------------------------------------------
RECURSO_APOYO = ("Es bueno que hayas podido apoyarte en alguien.",
                 "Es bueno que haya podido apoyarse en alguien.")
RECURSO_ESPERANZA = ("Y se nota que tienes ganas de que mejore, que es un buen punto de partida.",
                     "Y se nota que tiene ganas de que mejore, que es un buen punto de partida.")

# ---------------------------------------------------------------------------
# 5. Una pregunta final (tú, usted)
# ---------------------------------------------------------------------------
PREGUNTAS = {
    "alegria": ("¿Qué significa esto para ti?", "¿Qué significa esto para usted?"),
    "serenidad": ("¿Qué te está ayudando a estar así?", "¿Qué le está ayudando a estar así?"),
    "amor": ("¿Qué significa esa persona para ti?", "¿Qué significa esa persona para usted?"),
    "esperanza": ("¿Cuál sería el primer paso?", "¿Cuál sería el primer paso?"),
    "sorpresa": ("¿Y cómo te has quedado?", "¿Y cómo se ha quedado?"),
    "tristeza": ("¿Desde cuándo te sientes así?", "¿Desde cuándo se siente así?"),
    "soledad": ("¿Hay alguien con quien te apetezca hablar?",
                "¿Hay alguien con quien le apetezca hablar?"),
    "ira": ("¿Qué es lo que más te ha molestado?", "¿Qué es lo que más le ha molestado?"),
    "miedo": ("¿Qué es lo que más te preocupa que pase?", "¿Qué es lo que más le preocupa que pase?"),
    "ansiedad": ("¿Qué es lo que más te preocupa ahora mismo?",
                 "¿Qué es lo que más le preocupa ahora mismo?"),
    "culpa": ("¿Qué crees que podrías hacer ahora al respecto?",
              "¿Qué cree que podría hacer ahora al respecto?"),
    "verguenza": ("¿Qué le dirías a alguien a quien quieres si le pasara lo mismo?",
                  "¿Qué le diría a alguien a quien aprecia si le pasara lo mismo?"),
    "asco": ("¿Qué es lo que más rechazo te produce?", "¿Qué es lo que más rechazo le produce?"),
    "neutral": ("¿Y cómo te sientes con eso?", "¿Y cómo se siente con eso?"),
}

# Preguntas de SEGUIMIENTO: para avanzar en la conversación sin repetirse
SEGUIMIENTO = {
    "alegria": [("¿Con quién lo vas a celebrar?", "¿Con quién lo va a celebrar?"),
                ("¿Cómo te sientes ahora mismo?", "¿Cómo se siente ahora mismo?")],
    "serenidad": [("¿Qué podrías hacer para mantenerlo?", "¿Qué podría hacer para mantenerlo?")],
    "amor": [("¿Se lo has dicho?", "¿Se lo ha dicho?")],
    "esperanza": [("¿Qué necesitarías para conseguirlo?", "¿Qué necesitaría para conseguirlo?"),
                  ("¿Qué te lo está poniendo difícil?", "¿Qué se lo está poniendo difícil?")],
    "sorpresa": [("¿Qué vas a hacer ahora?", "¿Qué va a hacer ahora?")],
    "tristeza": [("¿Qué es lo que más te pesa?", "¿Qué es lo que más le pesa?"),
                 ("¿Qué te ayudaría un poco ahora mismo?", "¿Qué le ayudaría un poco ahora mismo?")],
    "soledad": [("¿Con quién te gustaría estar ahora?", "¿Con quién le gustaría estar ahora?"),
                ("¿Desde cuándo te sientes así?", "¿Desde cuándo se siente así?")],
    "ira": [("¿Y qué te gustaría que pasara?", "¿Y qué le gustaría que pasara?"),
            ("¿Qué podrías hacer tú al respecto?", "¿Qué podría hacer usted al respecto?")],
    "miedo": [("¿Qué parte de eso depende de ti?", "¿Qué parte de eso depende de usted?"),
              ("¿Qué te ayudaría a sentir más seguridad?", "¿Qué le ayudaría a sentir más seguridad?")],
    "ansiedad": [("¿Qué parte de eso depende de ti?", "¿Qué parte de eso depende de usted?"),
                 ("¿Qué es lo peor que crees que podría pasar?", "¿Qué es lo peor que cree que podría pasar?")],
    "culpa": [("¿Has podido hablarlo con esa persona?", "¿Ha podido hablarlo con esa persona?"),
              ("¿Qué le dirías a alguien que hubiera hecho lo mismo?",
               "¿Qué le diría a alguien que hubiera hecho lo mismo?")],
    "verguenza": [("¿Qué crees que piensan los demás?", "¿Qué cree que piensan los demás?")],
    "asco": [("¿Qué te gustaría hacer al respecto?", "¿Qué le gustaría hacer al respecto?")],
    "neutral": [("¿Hay algo más que quieras contarme?", "¿Hay algo más que quiera contarme?"),
                ("¿Y eso cómo te hace sentir?", "¿Y eso cómo le hace sentir?")],
}

# Cómo encajar la RESPUESTA de la persona en la pregunta que se le hizo.
# Clave: (emoción, índice de la pregunta). "{x}" = lo que ha dicho, en 2ª persona.
MARCOS = {
    ("ira", 0): "lo que más {te} ha molestado es que {x}",
    ("ira", 1): "lo que {te} gustaría es que {x}",
    ("ansiedad", 0): "lo que más {te} preocupa es que {x}",
    ("miedo", 0): "lo que más {te} preocupa es que {x}",
    ("asco", 0): "lo que más rechazo {te} produce es que {x}",
}

# Paso a 2ª persona: "yo solo quiero" -> "tú solo quieres"
SEGUNDA_PERSONA = {
    "tu": {"yo": "tú", "me": "te", "mi": "tu", "mí": "ti", "mis": "tus", "conmigo": "contigo",
           "estoy": "estás", "tengo": "tienes", "soy": "eres", "he": "has", "quiero": "quieres",
           "puedo": "puedes", "siento": "sientes", "voy": "vas", "hago": "haces", "sé": "sabes",
           "creo": "crees", "pienso": "piensas", "necesito": "necesitas", "odio": "odias",
           "echo": "echas", "estaba": "estabas", "tenía": "tenías", "fui": "fuiste",
           "hice": "hiciste", "dije": "dijiste", "aguanto": "aguantas", "soporto": "soportas",
           "gusta": "gusta", "llevo": "llevas", "sigo": "sigues", "veo": "ves", "digo": "dices"},
    "usted": {"yo": "usted", "me": "le", "mi": "su", "mí": "usted", "mis": "sus",
              "conmigo": "con usted", "estoy": "está", "tengo": "tiene", "soy": "es", "he": "ha",
              "quiero": "quiere", "puedo": "puede", "siento": "siente", "voy": "va", "hago": "hace",
              "sé": "sabe", "creo": "cree", "pienso": "piensa", "necesito": "necesita",
              "odio": "odia", "echo": "echa", "estaba": "estaba", "tenía": "tenía", "fui": "fue",
              "hice": "hizo", "dije": "dijo", "aguanto": "aguanta", "soporto": "soporta",
              "llevo": "lleva", "sigo": "sigue", "veo": "ve", "digo": "dice"},
}
# Muletillas del principio que no aportan contenido: "todo, ...", "pues...", "no sé, ..."
RE_MULETILLAS = re.compile(
    r"^\s*(?:(?:todo|nada|pues|bueno|es que|mira|nah|na|buah|uf|buf|jo|joder|hostia|ostia|vale|"
    r"hombre|ya|no s[eé])\s*(?:,|\.|!|\s+(?=\w))\s*)+", re.IGNORECASE)

APERTURA_SEGUIMIENTO = {"formal": ["Entiendo.", "Comprendo."], "neutro": ["Entiendo.", "Ya veo."],
                        "cercano": ["Vale.", "Ya veo."], "coloquial": ["Vale.", "Ya veo."]}

RESPUESTA_RIESGO = (
    "Gracias por contarlo. Lo que dices es importante y no tienes por qué pasarlo a solas: "
    "puedes llamar ahora al 024, es gratis y te atienden a cualquier hora (si es una emergencia, "
    "al 112). ¿Estás a salvo en este momento?",
    "Gracias por contármelo. Lo que dice es importante y no tiene por qué pasarlo a solas: "
    "puede llamar ahora al 024, es gratuito y atienden a cualquier hora (si es una emergencia, "
    "al 112). ¿Está a salvo en este momento?",
)

EMOJI_POSITIVO, EMOJI_APOYO, EMOJI_NEUTRO = "😊", "🫂", "🙂"
EMOJIS_POSITIVOS = set("😀😃😄😁😊🙂😂🎉😍🥰❤💕🤞😌")


# ---------------------------------------------------------------------------
def _posesivo(det, tratamiento):
    """'mi' (de la persona) -> 'tu' / 'su' (desde quien responde)."""
    if det in ("mi", "mis"):
        return {"mi": "tu", "mis": "tus"}[det] if tratamiento == "tu" else {"mi": "su", "mis": "sus"}[det]
    return det


def _lo_de(tema, tratamiento):
    """Tema -> 'lo de tu jefe' · 'lo del examen'"""
    det = _posesivo(tema.det, tratamiento)
    if det in ("lo del", "lo de"):
        return f"{det} {tema.sust}"
    if det == "el":
        return f"lo del {tema.sust}"
    return f"lo de {det} {tema.sust}"


def _como_lo_dijo(tema, tratamiento):
    """Usa la preposición de la persona: 'preocupada por mi trabajo' -> 'por su trabajo'."""
    det = _posesivo(tema.det, tratamiento)
    frase = f"{tema.prep} {det} {tema.sust}"
    return frase.replace("de el ", "del ")


def _elegir_tema(a):
    """El tema más cercano a donde aparece la emoción ('agobiada con EL CURRO')."""
    temas = a.estilo.temas
    if not temas:
        return None
    normal = normalizar(a.texto)
    ref = a.estilo.pos_autodescripcion
    if ref < 0:
        for d in a.disparadores.get(a.dominante, []):
            ref = normal.find(normalizar(d))
            if ref >= 0:
                break
    if ref < 0:
        return temas[0]
    # El tema suele ir DETRÁS de la emoción, así que penalizamos los de delante
    return min(temas, key=lambda t: (t.pos - ref) if t.pos >= ref else (ref - t.pos) * 1.5)


def _valencia(a):
    if a.dominante == "esperanza":
        return "neutral"      # un deseo ("necesito un buen bíceps") no es una "buena noticia"
    return "positiva" if a.valencia > 0.15 else "negativa" if a.valencia < -0.15 else "neutral"


def _con_vocativo(frase, vocativo):
    """'Uf, vale.' + 'tía' -> 'Uf, vale, tía.'  ·  '¡Qué bien!' + 'bro' -> '¡Qué bien, bro!'"""
    if not vocativo:
        return frase
    final = frase[-1] if frase[-1] in ".!?" else ""
    cuerpo = frase[:-1] if final else frase
    return f"{cuerpo}, {vocativo}{final or '.'}"


def _apertura_base(a, turno):
    e, val = a.estilo, _valencia(a)
    interj = normalizar(e.interjeccion) if e.interjeccion else None
    # Reflejar su interjección, pero solo si encaja con el tono
    if interj and e.registro != "formal":
        if val == "negativa" and interj in {"uf", "buf", "buah", "jo", "ostras", "joder",
                                            "hostia", "ostia", "ay"}:
            return f"{e.interjeccion.capitalize()}, vale."
        if val == "positiva" and interj.startswith(("jaj", "jej")):
            return "Jaja, ¡qué bien!"
        if val == "positiva" and interj in {"wow", "guau"}:
            return f"¡{e.interjeccion.capitalize()}, qué bien!"
    opciones = APERTURAS[val][e.registro]
    frase = opciones[turno % len(opciones)].format(**CONJ[e.tratamiento])
    if val == "positiva" and not e.exclamaciones:       # no exagerar si la persona no lo hace
        frase = frase.replace("¡", "").replace("!", ".")
    return frase


def _apertura(a, turno):
    return _con_vocativo(_apertura_base(a, turno), a.estilo.vocativo)


def _reflejo(a):
    e, t = a.estilo, a.estilo.tratamiento
    lider = {"formal": "Por lo que me {cuentas}", "coloquial": "Por lo que {dices}"}.get(
        e.registro, "Por lo que {cuentas}").format(**CONJ[t])

    tema = _elegir_tema(a)

    if a.dominante == "neutral" and not e.autodescripcion:
        return f"Me {CONJ[t]['cuentas']} {_lo_de(tema, t)}." if tema else ""

    # Si la persona se ha descrito con una palabra reflejable, usamos SU palabra
    # y SU preposición: "estoy agobiada con el curro" -> "estás agobiada con el curro"
    if e.autodescripcion:
        frase = f"{CONJ[t]['estas']} {e.autodescripcion}"
        ya_tiene_objeto = normalizar(e.autodescripcion).split()[-2:-1] == ["por"]   # "colada por Marta"
        if tema and not ya_tiene_objeto:
            frase += " " + (_como_lo_dijo(tema, t) if tema.prep in ("con", "por", "en", "sobre", "de")
                            else f"con {_lo_de(tema, t)}")
        return f"{lider}, {frase}."

    # Expresión con "me" + verbo: "me toca los huevos" -> "te toca los huevos"
    if e.expresion_me:
        return f"{lider}, {CONJ[t]['te']} {e.expresion_me[3:]}."
    else:
        neutra, coloquial, conector = REFLEJOS[a.dominante]
        if not tema and a.dominante in SIN_TEMA:
            neutra, coloquial = SIN_TEMA[a.dominante]
        frase = coloquial if e.registro == "coloquial" else neutra
        if t == "usted" and a.dominante in REFLEJOS_USTED:
            frase = REFLEJOS_USTED[a.dominante]
        frase = frase.format(**CONJ[t])

    if tema and conector is not None:
        frase += f" {conector} {_lo_de(tema, t)}" if conector else f" {_lo_de(tema, t)}"
    return f"{lider}, {frase}."


def _reencuadres(a, maximo):
    idx = 0 if a.estilo.tratamiento == "tu" else 1
    presentes = {s.id for s in a.senales} | {d.id for d in a.distorsiones}
    frases = []
    for p in PRIORIDAD:
        if p not in presentes:
            continue
        clave = p
        if p == "minimizacion":
            evid = " ".join(s.evidencias[0] for s in a.senales if s.id == p)
            if "bien" not in normalizar(evid):
                clave = "minimizacion_igual"        # "me la suda", "da igual"
        if p == "generalizacion":
            evid = " ".join(d.evidencias[0] for d in a.distorsiones if d.id == p)
            if any(x in normalizar(evid) for x in ("nadie", "todo el mundo")):
                clave = "generalizacion_personas"   # "nadie me entiende"
        frases.append(REENCUADRES[clave][idx])
    return frases[:maximo]


def _recursos(a):
    idx = 0 if a.estilo.tratamiento == "tu" else 1
    recursos = []
    if any(s.id == "apoyo_social" and a.apoyo_explicito for s in a.senales):
        recursos.append(RECURSO_APOYO[idx])
    if _valencia(a) == "negativa" and a.porcentajes.get("esperanza", 0) >= 10:
        recursos.append(RECURSO_ESPERANZA[idx])
    return recursos


def _pregunta(a, historial=()):
    """Una pregunta que NO se haya hecho ya en la conversación."""
    e = a.estilo
    idx = 0 if e.tratamiento == "tu" else 1
    hechas = {h.pregunta_hecha for h in historial}
    opciones = [PREGUNTAS[a.dominante]] + SEGUIMIENTO.get(a.dominante, [])
    elegida = next((o for o in opciones if o[idx] not in hechas), None)
    if elegida is None:                              # ya se han hecho todas
        opciones = SEGUIMIENTO["neutral"]
        elegida = next((o for o in opciones if o[idx] not in hechas), opciones[0])
    a.pregunta_hecha = elegida[idx]
    a.pregunta_tipo = (a.dominante, opciones.index(elegida)) if opciones is not SEGUIMIENTO["neutral"] \
        else ("neutral", -1)
    p = elegida[idx]
    if e.registro == "coloquial" and len(historial) % 2 == 0:   # "Oye," sí, pero no siempre
        p = "Oye, " + p[0] + p[1].lower() + p[2:]
    return p


def _parafrasear(a):
    """Lo que ha dicho la persona, en 2ª persona y sin muletillas:
    'no se xoxo, yo solo quiero un buen bicep' -> 'tú solo quieres un buen bicep'"""
    e, t = a.estilo, a.texto
    if "?" in t:
        return None
    for quitar in (e.vocativo, e.cierre):
        if quitar:
            t = re.sub(r"[,\s]*(?<!\w)" + re.escape(quitar) + r"(?!\w)\s*,?", " ", t, count=1)
    t = "".join(c for c in t if not (unicodedata.category(c) == "So" and ord(c) > 0x2100))
    t = RE_MULETILLAS.sub("", t.strip())
    t = re.sub(r"^que\s+", "", t, flags=re.IGNORECASE)
    tabla = SEGUNDA_PERSONA[e.tratamiento]
    t = re.sub(r"\b\w+\b", lambda m: tabla.get(m.group(0).lower(), m.group(0)), t)
    t = re.sub(r"\s+", " ", t).strip(" .,!…")
    if not t or len(t.split()) > 20:
        return None
    return t[0].lower() + t[1:]


RE_NO_SE = re.compile(r"(no (lo )?se|ni idea|no sabria (que )?decir\w*|no estoy segur[oa])"
                      r"(,? la verdad)?")
RE_TIEMPO = re.compile(r"(desde|hace|ayer|anoche|esta (semana|manana|tarde)|este (mes|ano)|"
                       r"un[oa]?s? |dos |tres |varios |varias |un par|el |la )")
RE_DESEO = re.compile(r"(solo )?(quieres|quiere|necesitas|necesita|te gustaria|le gustaria)\b")


def _respuesta_a_pregunta(a, anterior):
    """'¿Qué te ha molestado?' -> 'no hay quesitos' -> 'Así que lo que más te ha
    molestado es que no hay quesitos.'"""
    t = a.estilo.tratamiento
    # "No lo sé" no se repite: se le quita peso (no saberlo también es normal)
    if RE_NO_SE.fullmatch(normalizar(a.texto).strip(" .!,…")):
        return ("No pasa nada si no lo sabes, a veces cuesta verlo." if t == "tu"
                else "No pasa nada si no lo sabe, a veces cuesta verlo.")
    x = _parafrasear(a)
    if not x:
        return None
    if x.startswith("tú "):
        x = x[3:]                                   # "tú solo quieres" -> "solo quieres"
    xn = normalizar(x)
    tipo = anterior.pregunta_tipo
    marco = MARCOS.get(tipo)
    if RE_DESEO.match(xn):
        marco = None                                # ya expresa el deseo: no duplicarlo
    # "¿Desde cuándo te sientes así?" -> "desde el lunes" -> "llevas así desde el lunes"
    if anterior.pregunta_hecha and "desde cuando" in normalizar(anterior.pregunta_hecha) \
            and RE_TIEMPO.match(xn):
        marco = "{llevas} así {x}"
    frase = marco.format(x=x, llevas="llevas" if t == "tu" else "lleva", **CONJ[t]) if marco else x
    return f"Así que {frase}."


def _emoji(a):
    e = a.estilo
    if not e.emojis or e.registro == "formal":
        return ""
    val = _valencia(a)
    if val == "positiva":
        propio = next((x for x in e.emojis if x in EMOJIS_POSITIVOS), None)
        return " " + (propio or EMOJI_POSITIVO)
    return " " + (EMOJI_APOYO if val == "negativa" else EMOJI_NEUTRO)


def generar_respuesta(a, turno=0, historial=()):
    """Respuesta objetiva, adaptada al estilo de la persona y sin copiar su negatividad.
    historial: análisis anteriores de la conversación (para no perder el hilo)."""
    e = a.estilo
    if a.riesgo == "alto":
        # Ante el riesgo, la prioridad es la seguridad: mensaje claro y directo.
        a.pregunta_hecha = "riesgo"
        return RESPUESTA_RIESGO[0 if e.tratamiento == "tu" else 1]

    # Longitud parecida a la del mensaje de la persona
    maximo = {"corta": 0, "media": 1, "larga": 2}[e.longitud]
    reencuadres = _reencuadres(a, maximo)
    if not reencuadres and e.longitud == "corta":
        reencuadres = _reencuadres(a, 1)          # aun corta, si hay algo importante, se dice

    # ¿Contesta a la pregunta que le hicimos? Entonces se recoge su respuesta.
    anterior = historial[-1] if historial else None
    recogida = _respuesta_a_pregunta(a, anterior) if anterior and a.es_respuesta else None
    if recogida:
        opciones = APERTURA_SEGUIMIENTO[e.registro]
        apertura = _con_vocativo(opciones[turno % len(opciones)].format(**CONJ[e.tratamiento]),
                                 e.vocativo)
        partes = [apertura, recogida] + reencuadres
    else:
        partes = [_apertura(a, turno), _reflejo(a)] + reencuadres
        if e.longitud != "corta":
            partes += _recursos(a)
    partes.append(_pregunta(a, historial))
    texto = " ".join(p for p in partes if p) + _emoji(a) + _cierre(a)
    return re.sub(r"\s{2,}", " ", texto)


def responder(a, turno=0, historial=(), usar_llm=None):
    """
    Decide QUIÉN responde:
      1. Riesgo alto  -> mensaje de seguridad fijo (las reglas mandan).
      2. LLM local    -> si Ollama está funcionando (entiende y redacta mejor).
      3. Plantillas   -> si no hay LLM, o falla, o su respuesta no pasa el control.
    """
    import llm
    plantilla = generar_respuesta(a, turno, historial)     # siempre: es el plan B
    if a.riesgo == "alto":
        texto, a.respuesta_de = plantilla, "seguridad"
    else:
        usar = llm.usar() if usar_llm is None else usar_llm
        texto = llm.responder(a, historial) if usar else None
        if texto:
            a.respuesta_de = f"LLM ({llm.MODELO})"
        else:
            texto, a.respuesta_de = plantilla, "plantillas"
    a.respuesta = texto
    return texto


def _cierre(a):
    """Devuelve su coletilla final ('xoxo', 'besis'...). Las risas solo si el tono es positivo."""
    c = a.estilo.cierre
    if not c:
        return ""
    if normalizar(c).startswith(("jaj", "jej", "xd")) and _valencia(a) != "positiva":
        return ""
    return " " + c
