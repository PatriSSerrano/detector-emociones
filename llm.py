"""
Respuesta redactada por un LLM local (Ollama).

Por qué: las reglas y los clasificadores saben QUÉ emoción hay, pero no
entienden lo que la persona quiere decir (humor, contexto, de qué habla de
verdad) y las plantillas suenan a máquina. Un LLM (modelo de lenguaje grande)
entiende la conversación entera y REDACTA como una persona.

Reparto de papeles:
  - El sistema ANALIZA (emoción, distorsiones, estilo, riesgo).
  - El LLM HABLA: recibe unas instrucciones fijas (system prompt), la
    conversación y unas notas con el análisis del último mensaje.
  - La SEGURIDAD la deciden las reglas: si hay riesgo alto no se pregunta al
    LLM. Y si el LLM falla, tarda demasiado o dice algo que no debe, se usa la
    respuesta de plantillas.

Todo es local: Ollama corre en tu ordenador (http://localhost:11434) y los
mensajes no salen de él.
"""

import json
import os
import re
import urllib.error
import urllib.request

import unicodedata

from expresiones import ESPEJO_EMOJIS, ESPEJO_TACOS
from lexico import NOMBRES

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO = os.environ.get("OLLAMA_MODELO", "gemma3:4b")
TIEMPO_MAXIMO = 120          # segundos; si tarda más, se usa la respuesta de plantillas

SYSTEM_PROMPT = """Eres un psicólogo que conversa por chat con una persona. Es una simulación \
educativa: no diagnostiques ni des tratamientos.

Cómo respondes:
1. Habla EXACTAMENTE con el estilo de la persona: su mismo registro (formal o coloquial), tú o \
usted, sus expresiones, sus vocativos (bro, tía, tío...) y sus despedidas (xoxo, besis...). Si \
dice tacos, tú también puedes decirlos con naturalidad. No uses emojis.
2. No copies su negatividad: nunca repitas insultos (ni hacia ella ni hacia otros), no uses \
palabras absolutas como "siempre", "nunca", "nada" o "nadie" y no exageres su malestar.
3. Sé objetivo: básate en lo que ha dicho, separa los hechos de las suposiciones y no des falsos \
ánimos ("seguro que todo irá bien"). No des consejos que no te ha pedido.
4. Entiende la conversación entera. Si te contesta a una pregunta, recoge su respuesta. Si hace \
una broma, puedes seguirla sin perder el hilo.
5. Sé breve, como en un chat: de 1 a 3 frases, con una longitud parecida a la de su mensaje. \
Termina con UNA sola pregunta abierta que no hayas hecho ya.
6. Si cambia de tema o quita importancia con una broma, puedes seguirle la broma, pero vuelve con \
tacto a lo que te contó antes.
7. No supongas si es hombre o mujer. Si no lo ha dejado claro (por ejemplo, "estoy rayada"), usa \
formas neutras: "estás con mucha frustración", no "estás frustrada" ni "estás frustrado".
8. Escribe solo tu respuesta, sin comillas, sin explicaciones y sin mencionar las notas.

Ejemplos de cómo responder:

Persona: estoy hasta el coño
Tú: Uf, vale, se nota que estás hasta el coño. ¿Qué ha pasado para que llegues a este punto?

Persona: uf bro estoy hasta los huevos del curro
Tú: Uf, bro, normal que estés hasta los huevos si el curro te tiene así. ¿Qué es lo que más te está quemando?

Persona: Buenas tardes. Le escribo porque últimamente me siento muy cansada.
Tú: Buenas tardes, gracias por escribirme. Por lo que me cuenta, lleva un tiempo muy cansada. ¿Desde cuándo lo nota?

Persona: tía mi novio me ha dejado 😭
Tú: Ay, tía, lo siento mucho. Que te dejen duele, y es normal que estés así. ¿Cómo ha sido?

Persona (antes había dicho que estaba hasta el coño): pues nada bro, que no hay quesitos en clase jaja
Tú: Jaja, vale, bro, lo de los quesitos tiene delito. Pero antes estabas hasta el coño, ¿es solo eso o hay algo más?

Persona: me han dado la beca!! estoy flipando xoxo
Tú: ¡Qué pasada, enhorabuena! Normal que estés flipando. ¿Qué es lo primero que has pensado? xoxo"""

# Emojis que nunca debe usar (la persona puede, el sistema no: no se amplifica el malestar)
EMOJIS_NEGATIVOS = set("😭😢😞😔💔😡😠🤬😨😰😱🤢🤮😖😩😫☹🙁😿")


def _es_emoji(c):
    return (unicodedata.category(c) == "So" and ord(c) > 0x2100) or c in "️‍"
# Frases que dramatizan
DRAMATIZAR = re.compile(r"\b(qu[eé] horror|horrible|terrible|lo peor|devastador\w*|espantos\w*)\b", re.I)
# Formas de "tú": no pueden aparecer si la persona habla de usted
TUTEO = re.compile(r"\b(te|tú|tu|tus|ti|contigo|estás|tienes|sientes|puedes|quieres|cuentas|"
                   r"dices|has|eres|vas|sabes|crees|necesitas|llevas)\b", re.I)


def _peticion(ruta, datos=None, tiempo=5):
    req = urllib.request.Request(
        OLLAMA_URL + ruta, data=json.dumps(datos).encode() if datos is not None else None,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=tiempo) as r:
        return json.loads(r.read().decode())


def disponible():
    """¿Está Ollama funcionando y tiene el modelo descargado?"""
    try:
        modelos = [m["name"] for m in _peticion("/api/tags").get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        return False
    base = MODELO if ":" in MODELO else MODELO + ":latest"
    return base in modelos


USAR = None        # None = se comprueba la primera vez; True/False = forzado (main, tests)


def usar():
    global USAR
    if USAR is None:
        USAR = os.environ.get("EMOCIONES_SIN_LLM") != "1" and disponible()
    return USAR


def precalentar():
    """Carga el modelo en memoria para que la primera respuesta no tarde de más."""
    try:
        _peticion("/api/generate", {"model": MODELO, "prompt": "", "keep_alive": "30m"},
                  tiempo=TIEMPO_MAXIMO)
    except (urllib.error.URLError, OSError, ValueError):
        pass


# ---------------------------------------------------------------------------
# Notas del análisis para el LLM (lo que el sistema ha visto en el mensaje)
# ---------------------------------------------------------------------------
def notas_del_analisis(a):
    e = a.estilo
    n = []
    emocion = NOMBRES[a.dominante]
    if a.emocion_por_contexto:
        emocion += " (no la dice en este mensaje, viene de lo que contó antes)"
    n.append(f"Emoción principal: {emocion}.")
    if a.secundarias:
        n.append("También: " + ", ".join(NOMBRES[s] for s in a.secundarias) + ".")
    n.append(f"Estado: {a.estado}.")
    for o in a.otras_personas:
        n.append(f"Habla de lo que siente otra persona: {o['quien']} ({NOMBRES[o['emocion']].lower()}). "
                 "Eso NO es lo que siente quien escribe: no lo confundas.")
    for s in a.senales:
        n.append(f"Señal: {s.nombre} («{s.evidencias[0]}»).")
    for d in a.distorsiones:
        n.append(f"Pensamiento distorsionado: {d.nombre} en «{d.evidencias[0]}». Ayúdale a verlo "
                 "con objetividad, sin sermonear.")
    if a.riesgo == "moderado":
        n.append("Hay desesperanza: tómalo en serio y con calma. Si encaja, menciona que puede "
                 "llamar al 024.")

    estilo = [f"registro {e.registro}", "trátale de usted" if e.tratamiento == "usted" else "tutéale"]
    if e.vocativo:
        estilo.append(f"te llama «{e.vocativo}» (puedes usarlo)")
    else:
        # Sin esto, el modelo copia el "bro"/"tía" de los ejemplos del prompt
        estilo.append("no le llames bro, tía, tío ni nada parecido (no lo ha hecho)")
    if e.cierre:
        estilo.append(f"usa «{e.cierre}» (puedes usarlo tú también)")
    if e.vulgaridad:
        estilo.append("dice tacos (puedes decirlos)" if ESPEJO_TACOS else "dice tacos (tú no los digas)")
    if e.emojis and ESPEJO_EMOJIS:
        estilo.append("usa emojis (puedes usar alguno, nunca tristes ni de enfado)")
    else:
        estilo.append("no uses emojis")
    frases = {"corta": "1 o 2 frases", "media": "2 frases", "larga": "3 frases"}[e.longitud]
    estilo.append(f"responde en {frases}")
    n.append("Estilo: " + ", ".join(estilo) + ".")
    return "\n".join(n)


# ---------------------------------------------------------------------------
# Control de calidad de lo que escribe el LLM
# ---------------------------------------------------------------------------
INSULTOS = {"gilipollas", "imbecil", "imbécil", "idiota", "subnormal", "fracasado", "fracasada",
            "inutil", "inútil", "estupido", "estúpido", "estupida", "estúpida", "retrasado"}


def _limpiar(texto):
    texto = texto.strip().strip('"«»').strip()
    texto = re.sub(r"^\s*(psic[oó]logo|terapeuta|respuesta|t[uú])\s*:\s*", "", texto, flags=re.I)
    texto = texto.replace("**", "").replace("*", "")
    if ESPEJO_EMOJIS:
        texto = "".join(c for c in texto if c not in EMOJIS_NEGATIVOS)  # nunca emojis tristes
    else:
        texto = "".join(c for c in texto if not _es_emoji(c))            # ningún emoji
    return re.sub(r"\s+", " ", texto).strip()


def _problema(texto, a):
    """Devuelve qué está mal en la respuesta (para pedir que la corrija), o None si está bien."""
    if not texto:
        return "La respuesta está vacía."
    if len(texto) > 600:
        return "Es demasiado larga: responde en 1 a 3 frases."
    palabras = set(re.findall(r"\w+", texto.lower()))
    if palabras & INSULTOS:
        return "No repitas insultos."
    if re.search(r"([a-záéíóú])\1{3,}", texto, re.I):
        return "Hay una palabra con letras repetidas por error: escríbela bien."
    if DRAMATIZAR.search(texto):
        return "No dramatices: quita expresiones como 'qué horror' o 'terrible'."
    if a.estilo.tratamiento == "usted" and TUTEO.search(texto):
        return "La persona habla de usted: trátale de usted (le, su, usted, está, siente), nunca de tú."
    return None


# ---------------------------------------------------------------------------
# JUEZ DE PERSPECTIVA: ¿qué siente QUIEN ESCRIBE?
# Las reglas y los clasificadores detectan emociones que APARECEN en el texto,
# pero no de quién son: en "mi hermano está muy enfadado conmigo" la ira es del
# hermano; quien escribe siente culpa o preocupación. Eso hay que inferirlo
# entendiendo la situación, que es lo que hace bien un LLM.
# ---------------------------------------------------------------------------
EMOCIONES_JUEZ = ["alegria", "serenidad", "amor", "esperanza", "sorpresa", "tristeza", "soledad",
                  "ira", "miedo", "ansiedad", "culpa", "verguenza", "asco"]

# Formato obligatorio de la respuesta (Ollama lo hace cumplir)
ESQUEMA_JUEZ = {
    "type": "object",
    "properties": {
        # Primero RAZONA (quién siente qué) y después responde: a los modelos pequeños
        # les ayuda mucho pensar antes de dar la respuesta ("chain of thought").
        "analisis": {"type": "string"},
        "emociones": {"type": "array", "maxItems": 3, "items": {
            "type": "object",
            "properties": {"emocion": {"type": "string", "enum": EMOCIONES_JUEZ},
                           "intensidad": {"type": "number", "minimum": 0, "maximum": 1}},
            "required": ["emocion", "intensidad"]}},
        "otras_personas": {"type": "array", "maxItems": 3, "items": {
            "type": "object",
            "properties": {"quien": {"type": "string"},
                           "emocion": {"type": "string", "enum": EMOCIONES_JUEZ}},
            "required": ["quien", "emocion"]}},
    },
    "required": ["analisis", "emociones", "otras_personas"],
}

PROMPT_JUEZ = """Eres un psicólogo. Lee el mensaje y responde en JSON:
- "analisis": UNA frase que diga quién siente qué. Si habla de otra persona, piensa qué siente \
QUIEN ESCRIBE ante eso (por ejemplo, ante el enfado de alguien cercano se suele sentir culpa o \
preocupación, no enfado).
- "emociones": lo que siente LA PERSONA QUE ESCRIBE (de 0 a 3 emociones, con intensidad 0-1).
- "otras_personas": lo que sienten otras personas de las que habla.

Nunca pongas en "emociones" la emoción de otra persona. Si quien escribe solo cuenta un hecho sin \
emoción, deja "emociones" vacío.

Emociones posibles: alegria, serenidad, amor, esperanza, sorpresa, tristeza, soledad, ira, miedo, \
ansiedad (preocupación), culpa, verguenza, asco.

Ejemplos:
"Mi hermano está muy enfadado conmigo" -> {"analisis": "El enfado es del hermano; quien escribe \
se siente responsable y preocupado por la relación.", "emociones": [{"emocion": "culpa", \
"intensidad": 0.6}, {"emocion": "ansiedad", "intensidad": 0.5}], "otras_personas": [{"quien": \
"su hermano", "emocion": "ira"}]}
"Mi padre está muy triste desde que murió mi abuela" -> {"analisis": "La tristeza que describe es \
del padre; quien escribe está preocupado por él y también apenado por la pérdida.", "emociones": \
[{"emocion": "ansiedad", "intensidad": 0.5}, {"emocion": "tristeza", "intensidad": 0.4}], \
"otras_personas": [{"quien": "su padre", "emocion": "tristeza"}]}
"Te odio, no quiero volver a verte" -> {"analisis": "Quien escribe siente rabia hacia la otra \
persona.", "emociones": [{"emocion": "ira", "intensidad": 0.9}], "otras_personas": []}
"Mañana tengo una reunión a las diez" -> {"analisis": "Solo cuenta un hecho.", "emociones": [], \
"otras_personas": []}"""


def juzgar(texto, contexto=None, pistas=()):
    """Qué siente quien escribe y qué sienten los demás, según el LLM. None si falla.
    pistas: emociones que las reglas ya han atribuido a otras personas."""
    mensaje = f'Mensaje: "{texto}"'
    if contexto:
        mensaje = f'Mensaje anterior de la misma persona: "{contexto}"\n' + mensaje
    if pistas:
        mensaje += "\nPista: " + "; ".join(
            f"la emoción «{NOMBRES[p['emocion']].lower()}» es de {p['quien']}, no de quien escribe"
            for p in pistas)
    try:
        r = _peticion("/api/chat", {
            "model": MODELO, "stream": False, "keep_alive": "30m", "format": ESQUEMA_JUEZ,
            "messages": [{"role": "system", "content": PROMPT_JUEZ},
                         {"role": "user", "content": mensaje}],
            "options": {"temperature": 0, "num_predict": 220}}, tiempo=TIEMPO_MAXIMO)
        datos = json.loads(r.get("message", {}).get("content", ""))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None
    # Revisión de lo que ha devuelto (por si acaso no cumple el esquema)
    emociones = [{"emocion": e["emocion"], "intensidad": max(0.0, min(1.0, float(e["intensidad"])))}
                 for e in datos.get("emociones", [])
                 if isinstance(e, dict) and e.get("emocion") in EMOCIONES_JUEZ
                 and isinstance(e.get("intensidad"), (int, float))]
    otras = [{"quien": str(o["quien"])[:40], "emocion": o["emocion"]}
             for o in datos.get("otras_personas", [])
             if isinstance(o, dict) and o.get("emocion") in EMOCIONES_JUEZ and o.get("quien")]
    return {"emociones": emociones, "otras_personas": otras,
            "analisis": str(datos.get("analisis", ""))[:300]}


def responder(a, historial=(), nombre=None):
    """Respuesta del LLM, o None si no está disponible / falla / no pasa el control.
    historial: análisis anteriores, cada uno con su .texto y su .respuesta.
    nombre: cómo ha llamado la persona al chat (el LLM se presenta así)."""
    if a.riesgo == "alto":
        return None                            # la seguridad la deciden las reglas
    sistema = SYSTEM_PROMPT
    if nombre:
        sistema += (f"\n\nTe llamas {nombre}: es el nombre que ha elegido la persona para este "
                    "chat. Si te pregunta cómo te llamas, di ese nombre.")
    mensajes = [{"role": "system", "content": sistema}]
    for h in historial[-10:]:                  # las últimas 10 intervenciones bastan
        mensajes.append({"role": "user", "content": h.texto})
        if h.respuesta:
            mensajes.append({"role": "assistant", "content": h.respuesta})
    mensajes.append({"role": "user", "content":
                     f"{a.texto}\n\n[Notas del análisis, solo para ti:\n{notas_del_analisis(a)}]"})

    # Hasta 2 intentos: si la respuesta incumple una norma, se le pide que la corrija
    for intento in range(2):
        try:
            r = _peticion("/api/chat", {"model": MODELO, "messages": mensajes, "stream": False,
                                        "keep_alive": "30m",
                                        "options": {"temperature": 0.5 if intento == 0 else 0.3,
                                                    "num_predict": 160}},
                          tiempo=TIEMPO_MAXIMO)
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            return None
        texto = _limpiar(r.get("message", {}).get("content", ""))
        problema = _problema(texto, a)
        if problema is None:
            return texto
        mensajes += [{"role": "assistant", "content": texto},
                     {"role": "user", "content": f"[Corrige tu respuesta: {problema} Escribe solo la "
                                                 "respuesta corregida.]"}]
    return None                                # no ha pasado el control: plantillas
