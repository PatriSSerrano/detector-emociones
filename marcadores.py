"""
Marcadores lingüísticos: CÓMO habla la persona, no solo QUÉ emociones nombra.

Un psicólogo presta atención a pistas como estas:

1. ESTILO DEL LENGUAJE (investigación de James Pennebaker con LIWC)
   - Autofoco: abusar de "yo/me/mi" se asocia a malestar y a la depresión,
     porque la atención se queda girando sobre uno mismo.
   - Palabras absolutistas ("siempre", "nunca", "nada", "todo"):
     Al-Mosaiwi y Johnstone (2018) vieron que aparecen mucho más en foros de
     ansiedad, depresión e ideación suicida que en foros de control.
   - Rumiación (dar vueltas al pasado) y preocupación (anticipar el futuro).

2. DISTORSIONES COGNITIVAS (terapia cognitiva de Aaron Beck y David Burns)
   Formas de pensar que deforman la realidad y empeoran cómo nos sentimos.
   El terapeuta las detecta y ayuda a cuestionarlas con preguntas.

3. RIESGO
   Expresiones de ideación suicida o autolesión. Aquí se prefiere
   equivocarse por exceso (falso positivo) antes que dejar pasar un caso real.

Todos los patrones se aplican sobre texto en minúsculas y SIN tildes.
"""

# ---------------------------------------------------------------------------
# 1. Estilo del lenguaje (conteo de palabras)
# ---------------------------------------------------------------------------
PRIMERA_PERSONA = {"yo", "me", "mi", "mis", "conmigo", "mio", "mia", "mios", "mias"}

ABSOLUTISTAS = {
    "siempre", "nunca", "jamas", "todo", "todos", "toda", "todas", "nada", "nadie",
    "ninguno", "ninguna", "completamente", "totalmente", "absolutamente",
    "constantemente", "entero", "entera", "always", "never", "nothing", "everything",
    "nobody", "completely", "totally",
}

# ---------------------------------------------------------------------------
# Los pensamientos generan emociones (principio central de la terapia cognitiva):
# ciertos patrones de pensamiento suman puntos a la emoción que suelen provocar.
#   "¿Y si suspendo?"  -> preocupación -> ansiedad
# ---------------------------------------------------------------------------
PENSAMIENTO_A_EMOCION = {
    "preocupacion": ("ansiedad", 2),
    "adivinacion": ("ansiedad", 2),
    "catastrofismo": ("ansiedad", 2),
    "lectura_mente": ("ansiedad", 1),
    "rumiacion": ("tristeza", 1),
    "desesperanza": ("tristeza", 2),
    "etiquetado": ("verguenza", 2),
    "personalizacion": ("culpa", 2),
}

# ---------------------------------------------------------------------------
# 2. Señales detectadas con expresiones regulares
#    Cada señal: id -> (nombre, [patrones], explicación)
# ---------------------------------------------------------------------------
SENALES = {
    "rumiacion": (
        "Rumiación sobre el pasado",
        [r"\bsi (no )?hubiera\b", r"\b(no )?deberia haber\b", r"\btendria que haber\b",
         r"\bojala (no )?hubiera\b", r"\bno (dejo|paro) de pensar\b",
         r"\bno puedo dejar de pensar\b", r"\b(le )?doy vueltas\b", r"\bdandole vueltas\b"],
        "Dar vueltas a lo que pasó o a lo que se pudo hacer mejor. Mantiene la tristeza "
        "y la culpa activas sin llevar a soluciones.",
    ),
    "preocupacion": (
        "Preocupación anticipatoria",
        [r"\by si\b", r"\bque (va a pasar|pasara)\b", r"\bme preocupa que\b",
         r"\btengo miedo de que\b", r"\bme da miedo que\b", r"\bno se que va a pasar\b"],
        "La mente se adelanta a posibles problemas futuros. Es el núcleo de la ansiedad.",
    ),
    "desesperanza": (
        "Desesperanza",
        [r"\bno tengo esperanza\b", r"\bno hay salida\b", r"\bnada va a cambiar\b",
         r"\bnunca va a cambiar\b", r"\bno tiene sentido\b", r"\bno sirve de nada\b",
         r"\bpara que seguir\b", r"\bya no puedo mas\b", r"\bno puedo mas\b",
         r"\bno aguanto mas\b", r"\btodo da igual\b", r"\bnada importa\b",
         r"\btodo me da igual\b", r"\bme da todo igual\b", r"\bme la suda todo\b",
         r"\bno levanto cabeza\b", r"\bhe tocado fondo\b"],
        "Creer que las cosas no van a mejorar. Beck la señaló como uno de los "
        "indicadores más importantes de riesgo emocional.",
    ),
    "minimizacion": (
        "Posible minimización",
        [r"\bestoy bien\b", r"\bno pasa nada\b", r"\bda igual\b", r"\bno importa\b",
         r"\bno es nada\b", r"\bno es para tanto\b", r"\btampoco es para tanto\b",
         r"\bme la (suda|pela|trae floja|refanfinfla|sopla)\b",
         r"\bme importa (una mierda|un pimiento|un bledo|un carajo|un pito|tres pepinos|un huevo)\b"],
        "Quitar importancia a lo que se siente mientras el resto del mensaje expresa "
        "malestar. A veces es una forma de protegerse o de no preocupar a los demás.",
    ),
    "apoyo_social": (
        "Menciona personas cercanas",
        [r"\bamig[oa]s?\b", r"\bfamilia\b", r"\b(mi|mis) (madre|padre|padres|mama|papa)\b",
         r"\bherman[oa]s?\b", r"\b(mi )?pareja\b", r"\bnovi[oa]\b", r"\bcompaner[oa]s?\b",
         r"\bhable con\b", r"\bme (apoya|apoyan|ayuda|ayudan|escucha|escuchan)\b"],
        "Aparecen otras personas en su relato. Pueden ser una red de apoyo (uno de los "
        "factores que más protege la salud emocional) o parte del conflicto: vale la pena "
        "explorarlo.",
    ),
    "somatizacion": (
        "Síntomas físicos",
        [r"\bno (puedo )?duermo\b", r"\bno puedo dormir\b", r"\binsomnio\b", r"\bno como\b",
         r"\bsin hambre\b", r"\bdolor de (cabeza|estomago|pecho)\b", r"\bme duele el pecho\b",
         r"\bpalpitaciones\b", r"\bnudo en (el estomago|la garganta)\b",
         r"\bme falta el aire\b", r"\bno puedo respirar\b", r"\bagotad[oa]\b"],
        "Las emociones también se expresan en el cuerpo (sueño, apetito, tensión). "
        "Un psicólogo siempre pregunta por ello.",
    ),
    "vaguedad": (
        "Dificultad para nombrar la emoción",
        [r"\bno se (que|lo que) me pasa\b", r"\bno se como me siento\b",
         r"\bno se explicarlo\b",
         r"\b(estoy|me siento|me encuentro|ando) (un poco |muy |bastante |algo )?"
         r"(mal|fatal|rar[oa]|regular|rayad[oa]|chung[oa])\b"],
        "Expresiones vagas como 'estoy mal' o 'estoy raro'. Ayudar a poner nombre "
        "concreto a lo que se siente ya ayuda a regularlo (granularidad emocional).",
    ),
}

# ---------------------------------------------------------------------------
# 3. Distorsiones cognitivas
#    id -> (nombre, [patrones], explicación, pregunta para reformular)
# ---------------------------------------------------------------------------
DISTORSIONES = {
    "generalizacion": (
        "Sobregeneralización",
        [r"\b(siempre|nunca) me (pasa|sale|toca|ocurre)\b", r"\btodo me sale mal\b",
         r"\bnada me sale bien\b", r"\bnunca (hago|hare) nada bien\b",
         r"\bsiempre (lo )?hago (todo )?mal\b", r"\b(nunca|siempre) (es|sera) igual\b",
         r"\bnadie me (quiere|entiende|hace caso|escucha)\b", r"\btodo el mundo me\b"],
        "Sacar una regla general ('siempre', 'nunca') a partir de uno o pocos hechos.",
        "¿De verdad es *siempre*, *nunca* o *nadie*? ¿Recuerdas alguna excepción?",
    ),
    "catastrofismo": (
        "Catastrofismo",
        [r"\blo peor\b", r"\bes (horrible|terrible|un desastre)\b", r"\buna catastrofe\b",
         r"\bno (lo )?voy a (poder )?soportar\b", r"\bno podre soportarlo\b",
         r"\bse (me )?acabo todo\b", r"\bmi vida se acabo\b", r"\bse me cae el mundo\b",
         r"\btodo se (derrumba|hunde)\b", r"\b(va a ser|sera) horrible\b"],
        "Imaginar el peor resultado posible y darlo por hecho.",
        "¿Qué es lo más probable que ocurra (no lo peor)? Y si pasara, ¿cómo lo afrontarías?",
    ),
    "etiquetado": (
        "Etiquetarse",
        [r"\bsoy (un |una )?(fracasad[oa]|fracaso|inutil|idiota|tont[oa]|desastre|"
         r"perdedor|perdedora|estupid[oa]|basura|patetic[oa]|debil|lo peor|horrible)\b",
         r"\bno valgo (nada|para nada)\b"],
        "Definirse por completo con una etiqueta negativa a partir de un error.",
        "¿Le dirías eso a un amigo que ha cometido el mismo error? ¿Qué le dirías?",
    ),
    "personalizacion": (
        "Personalización",
        [r"\b(es|fue|era) (toda )?(culpa mia|mi culpa)\b", r"\bpor mi culpa\b",
         r"\bla culpa es mia\b", r"\btodo es culpa mia\b", r"\bseguro que es por mi\b"],
        "Asumir toda la responsabilidad de algo en lo que influyeron muchos factores.",
        "¿Qué otras personas o circunstancias influyeron en lo que pasó?",
    ),
    "deberias": (
        "Exigencias ('debería')",
        [r"\bdeberia(s)? (ser|estar|poder|saber|haber)\b", r"\btendria que (ser|estar|poder)\b",
         r"\b(debo|tengo que) ser (perfect[oa]|mejor|fuerte)\b", r"\bno deberia sentirme\b"],
        "Reglas rígidas sobre cómo uno 'debería' ser o sentirse. Generan culpa y frustración.",
        "¿Qué pasa si cambias 'debería' por 'me gustaría'? ¿Cambia cómo te sientes?",
    ),
    "lectura_mente": (
        "Lectura de mente",
        [r"\bseguro que (piensa|piensan|cree|creen|me odia|me odian|esta enfadad[oa])\b",
         r"\b(piensa|piensan|cree|creen) que soy\b", r"\btodos (me odian|piensan que)\b",
         r"\bme (odia|odian)\b"],
        "Dar por hecho lo que piensan los demás sin tener pruebas.",
        "¿Qué pruebas tienes de lo que piensa esa persona? ¿Podrías preguntárselo?",
    ),
    "adivinacion": (
        "Adivinar el futuro",
        [r"\b(va a|todo va a) salir mal\b", r"\bsaldra mal\b", r"\bnunca voy a\b",
         r"\bno voy a poder\b", r"\bnunca podre\b", r"\bno lo (voy a conseguir|conseguire)\b",
         r"\bme van a (echar|dejar|rechazar|suspender)\b", r"\bvoy a (suspender|fracasar)\b",
         r"\bseguro que (suspendo|me echan|me dejan|sale mal)\b"],
        "Predecir que algo saldrá mal como si fuera un hecho.",
        "¿Cómo sabes que pasará? ¿Las veces que lo temiste antes, ocurrió de verdad?",
    ),
    "dicotomico": (
        "Pensamiento todo o nada",
        [r"\b(o )?todo o nada\b", r"\bsi no es perfecto\b", r"\bo perfecto o\b",
         r"\bun (completo |total )?fracaso( total)?\b"],
        "Ver las cosas en blanco o negro, sin puntos intermedios.",
        "¿Hay algún punto intermedio entre el éxito total y el fracaso total?",
    ),
    "descalificar_positivo": (
        "Descalificar lo positivo",
        [r"\b(fue|ha sido) (pura |solo )?suerte\b", r"\bno tiene (ningun )?merito\b",
         r"\bcualquiera (lo )?(podria|hubiera)\b", r"\bno es gran cosa\b", r"\beso no cuenta\b"],
        "Quitar valor a los logros o a lo bueno que pasa.",
        "¿Qué parte de ese logro se debe a tu esfuerzo o a tus capacidades?",
    ),
}

# ---------------------------------------------------------------------------
# 4. Riesgo
# ---------------------------------------------------------------------------
RIESGO_ALTO = [
    r"\bsuicid\w*", r"\bquitarme la vida\b", r"\bquiero morir(me)?\b", r"\bme quiero morir\b",
    r"\bno quiero (seguir )?vivir\b", r"\bacabar con (mi vida|todo)\b", r"\bhacerme dano\b",
    r"\bautolesi\w*", r"\bcortarme\b(?! el pelo| las unas| el flequillo)",
    r"\bmejor (estarian|estaria todo|estarian todos) sin mi\b", r"\bojala no despert\w*",
    r"\bdesaparecer para siempre\b", r"\bno vale la pena vivir\b",
    # formas coloquiales (se prefiere un falso positivo a dejar pasar un caso real)
    r"\bme quiero matar\b", r"\bmatarme\b(?! a )", r"\bpegarme un tiro\b",
    r"\btirarme (por (la|una) ventana|por un puente|por el balcon|a las vias)\b",
    r"\bquitarme de en medio\b", r"\bno quiero despertar(me)?\b", r"\bdormirme y no despertar\b",
    r"\bkill myself\b", r"\bwant to die\b", r"\bend my life\b", r"\bself.?harm\b",
]

RECURSOS_AYUDA = [
    "024 — Línea de atención a la conducta suicida (España, gratuita, 24 h)",
    "112 — Emergencias",
    "Fuera de España: el número de emergencias local o findahelpline.com",
]
