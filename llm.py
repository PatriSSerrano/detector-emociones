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

from expresiones import ESPEJO_TACOS
from lexico import NOMBRES

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO = os.environ.get("OLLAMA_MODELO", "gemma3:4b")
TIEMPO_MAXIMO = 120          # segundos; si tarda más, se usa la respuesta de plantillas

SYSTEM_PROMPT = """Eres un psicólogo que conversa por chat con una persona. Es una simulación \
educativa: no diagnostiques ni des tratamientos.

Cómo respondes:
1. Habla EXACTAMENTE con el estilo de la persona: su mismo registro (formal o coloquial), tú o \
usted, sus expresiones, sus vocativos (bro, tía, tío...), sus despedidas (xoxo, besis...) y sus \
emojis. Si dice tacos, tú también puedes decirlos con naturalidad.
2. No copies su negatividad: nunca repitas insultos (ni hacia ella ni hacia otros), no uses \
palabras absolutas como "siempre", "nunca", "nada" o "nadie", no exageres su malestar y no uses \
emojis tristes o de enfado.
3. Sé objetivo: básate en lo que ha dicho, separa los hechos de las suposiciones y no des falsos \
ánimos ("seguro que todo irá bien"). No des consejos que no te ha pedido.
4. Entiende la conversación entera. Si te contesta a una pregunta, recoge su respuesta. Si hace \
una broma, puedes seguirla sin perder el hilo.
5. Sé breve, como en un chat: de 1 a 3 frases, con una longitud parecida a la de su mensaje. \
Termina con UNA sola pregunta abierta que no hayas hecho ya.
6. Si cambia de tema o quita importancia con una broma, puedes seguirle la broma, pero vuelve con \
tacto a lo que te contó antes.
7. Escribe solo tu respuesta, sin comillas, sin explicaciones y sin mencionar las notas.

Ejemplos de cómo responder:

Persona: uf bro estoy hasta los huevos del curro
Tú: Uf, bro, normal que estés hasta los huevos si el curro te tiene así. ¿Qué es lo que más te está quemando?

Persona: Buenas tardes. Le escribo porque últimamente me siento muy cansada.
Tú: Buenas tardes, gracias por escribirme. Por lo que me cuenta, lleva un tiempo muy cansada. ¿Desde cuándo lo nota?

Persona: tía mi novio me ha dejado 😭
Tú: Ay, tía, lo siento mucho. Que te dejen duele, y es normal que estés así. ¿Cómo ha sido? 🫂

Persona (antes había dicho que estaba hasta el coño): pues nada bro, que no hay quesitos en clase jaja
Tú: Jaja, vale, bro, lo de los quesitos tiene delito. Pero antes estabas hasta el coño, ¿es solo eso o hay algo más?

Persona: me han dado la beca!! estoy flipando xoxo
Tú: ¡Qué pasada, enhorabuena! Normal que estés flipando. ¿Qué es lo primero que has pensado? xoxo"""

# Emojis que nunca debe usar (la persona puede, el sistema no: no se amplifica el malestar)
EMOJIS_NEGATIVOS = set("😭😢😞😔💔😡😠🤬😨😰😱🤢🤮😖😩😫☹🙁😿")
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
    if e.emojis:
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
    texto = "".join(c for c in texto if c not in EMOJIS_NEGATIVOS)     # nunca emojis tristes
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


def responder(a, historial=()):
    """Respuesta del LLM, o None si no está disponible / falla / no pasa el control.
    historial: análisis anteriores, cada uno con su .texto y su .respuesta."""
    if a.riesgo == "alto":
        return None                            # la seguridad la deciden las reglas
    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
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
