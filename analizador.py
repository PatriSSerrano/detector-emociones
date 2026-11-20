"""
Motor de análisis emocional.

analizar(texto) -> Analisis

Pasos:
  1. TextBlob divide el texto en ORACIONES y PALABRAS.
  2. Puntuación emocional palabra a palabra con el léxico (lexico.py) y reglas:
       negación, intensificadores, MAYÚSCULAS, '!', emojis y contraste "pero".
  3. Porcentajes, emoción dominante y secundarias, intensidad.
  4. Estado afectivo en el modelo circumplejo (valencia x activación).
  5. Marcadores lingüísticos, distorsiones cognitivas y riesgo (marcadores.py).
"""

import os
import re
from dataclasses import dataclass, field

from textblob import TextBlob

import llm
import marcadores as M
import modelos
from estilo import Estilo, detectar_estilo
from utils import expandir_abreviaturas, normalizar
from lexico import (CIRCUMPLEJO, CONTRASTE, EMOCIONES, EMOJIS, INTENSIFICADORES,
                    NEGACIONES, NEGATIVAS, OPUESTOS, POSITIVAS)

# --- Configuración del sistema híbrido -------------------------------------
# Se pueden desactivar los modelos con la variable de entorno EMOCIONES_SOLO_REGLAS=1
USAR_MODELOS = os.environ.get("EMOCIONES_SOLO_REGLAS") != "1" and modelos.disponible()
PESO_REGLAS = 0.5      # cuando las reglas encuentran pruebas explícitas, hay que fiarse de ellas
PESO_MODELOS = 0.5     # los modelos entienden más, pero explican menos
UMBRAL_IRONIA = 0.9    # alto: el modelo de ironía da falsos positivos fuera de Twitter
UMBRAL_NEUTRAL = 0.9   # pysentimiento da 98-99 % "sin emoción" a los textos neutros y <70 % a los emocionales
PESO_JUEZ = 0.65       # cuánto pesa el LLM al decidir qué siente QUIEN ESCRIBE (la fuente más fiable
                       # en las pruebas: el zero-shot solo confundía culpa con amor, por ejemplo)
PESO_JUEZ_OTRAS = 0.85 # ...y aún más si la emoción del texto es de otra persona

PALABRAS_ES = {"el", "la", "los", "las", "de", "que", "y", "en", "es", "estoy", "me",
               "un", "una", "muy", "por", "con", "lo", "se", "mi", "pero", "esta"}
PALABRAS_EN = {"the", "is", "i", "am", "and", "you", "to", "of", "it", "my", "very",
               "this", "that", "are", "was", "not", "but", "so", "feel", "im"}


# ---------------------------------------------------------------------------
# Estructuras de datos del resultado
# ---------------------------------------------------------------------------
@dataclass
class Senal:
    id: str
    nombre: str
    explicacion: str
    evidencias: list
    pregunta: str = ""          # solo las distorsiones traen pregunta de reformulación


@dataclass
class Analisis:
    texto: str
    idioma: str
    n_palabras: int
    puntos: dict                 # emoción -> puntos brutos
    porcentajes: dict            # emoción -> %, ordenado de mayor a menor
    dominante: str
    secundarias: list
    intensidad: float            # puntos emocionales por palabra
    nivel_intensidad: str        # baja / media / alta
    valencia: float              # -1 desagradable ... +1 agradable
    activacion: float            # -1 baja energía ... +1 alta energía
    estado: str                  # cuadrante del modelo circumplejo
    senales: list = field(default_factory=list)
    distorsiones: list = field(default_factory=list)
    riesgo: str = "bajo"         # bajo / moderado / alto
    evidencias_riesgo: list = field(default_factory=list)
    disparadores: dict = field(default_factory=dict)   # emoción -> palabras que la activaron
    traza: list = field(default_factory=list)          # explicación paso a paso
    polaridad_textblob: float = None                   # solo inglés
    subjetividad_textblob: float = None                # solo inglés
    estilo: Estilo = None                              # cómo se expresa (estilo.py)
    apoyo_explicito: bool = False                      # "me escuchó", "hablé con..."
    fuente: str = "reglas"                             # "reglas" o "híbrido (reglas + modelos)"
    modelo: dict = None                                # salida de modelos.analizar_ml()
    # Conversación
    es_respuesta: bool = False                         # contesta a la pregunta anterior
    emocion_por_contexto: bool = False                 # la emoción viene del mensaje anterior
    pregunta_hecha: str = ""                           # la pregunta con la que respondió el sistema
    pregunta_tipo: tuple = (None, -1)                  # (emoción, índice) de esa pregunta
    otras_personas: list = field(default_factory=list) # [{"quien": "mi hermano", "emocion": "ira"}]
    respuesta: str = ""                                # lo que le contestó el sistema
    respuesta_de: str = ""                             # "plantillas", "LLM (gemma3:4b)" o "seguridad"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _preparar_lexico():
    exactas, raices, frases = {}, [], []
    for emocion, entradas in EMOCIONES.items():
        for palabra, peso in entradas:
            palabra = normalizar(palabra)
            if " " in palabra:
                frases.append((tuple(palabra.split()), emocion, peso))
            elif palabra.endswith("*"):
                raices.append((palabra[:-1], emocion, peso))
            else:
                exactas.setdefault(palabra, []).append((emocion, peso))
    raices.sort(key=lambda r: len(r[0]), reverse=True)   # la raíz más específica primero
    frases.sort(key=lambda f: len(f[0]), reverse=True)   # la expresión más larga primero
    return exactas, raices, frases


EXACTAS, RAICES, FRASES = _preparar_lexico()


def _buscar_palabra(palabra):
    if palabra in EXACTAS:
        return EXACTAS[palabra]
    encontradas = {}
    for raiz, emocion, peso in RAICES:
        if palabra.startswith(raiz) and emocion not in encontradas:
            encontradas[emocion] = peso
    if encontradas:
        return list(encontradas.items())
    # Superlativo en -ísimo: "tristísima" -> "triste" con más fuerza (x1.5)
    m = re.match(r"(\w+?)(c)?isim[oa]s?$", palabra)
    if m:
        base = m.group(1) + ("z" if m.group(2) else "")          # "felicísima" -> "feliz"
        for candidata in (base, base + "e", base + "o", base + "a"):
            hallazgos = _buscar_palabra(candidata) if candidata != palabra else []
            if hallazgos:
                return [(e, p * 1.5) for e, p in hallazgos]
    return []


def _buscar_frase(tokens, i):
    for frase, emocion, peso in FRASES:
        if tuple(tokens[i:i + len(frase)]) == frase:
            return len(frase), [(emocion, peso)]
    return None


def _tokenizar(oracion):
    """Palabras originales + normalizadas + PAUSAS (posiciones de las palabras que van
    justo después de una coma u otro signo). Une 'sin embargo' en un solo token para
    que el 'sin' no se tome como negación."""
    piezas = list(oracion.tokens)                # a diferencia de .words, conserva los signos
    o, t, pausas = [], [], set()
    pausa, i = False, 0
    while i < len(piezas):
        pieza = piezas[i]
        if not any(c.isalnum() for c in pieza):  # signo de puntuación (o emoji)
            pausa = True
            i += 1
            continue
        if pausa and o:
            pausas.add(len(o))
        pausa = False
        n = normalizar(pieza)
        if n == "sin" and i + 1 < len(piezas) and normalizar(piezas[i + 1]) == "embargo":
            o.append(f"{pieza} {piezas[i + 1]}")
            t.append("sin_embargo")
            i += 2
        else:
            o.append(pieza)
            t.append(n)
            i += 1
    return o, t, pausas


def _detectar_idioma(palabras):
    es = sum(p in PALABRAS_ES for p in palabras)
    en = sum(p in PALABRAS_EN for p in palabras)
    return "en" if en > es else "es"


def _buscar_patrones(patrones, texto_original, texto_normal):
    """Devuelve los fragmentos del texto ORIGINAL que encajan con los patrones.
    Como normalizar() no cambia la longitud del texto (cada 'á' pasa a 'a'),
    las posiciones coinciden y podemos citar las palabras tal cual se escribieron."""
    misma_longitud = len(texto_original) == len(texto_normal)
    hallazgos = []
    for patron in patrones:
        for m in re.finditer(patron, texto_normal):
            fuente = texto_original if misma_longitud else texto_normal
            frag = fuente[m.start():m.end()].strip()
            if frag and frag.lower() not in (h.lower() for h in hallazgos):
                hallazgos.append(frag)
    return hallazgos


# ---------------------------------------------------------------------------
# ¿QUIÉN siente la emoción? (el "experimentador")
#   "estoy enfadado"             -> quien escribe
#   "mi hermano está enfadado"   -> su hermano: NO es una emoción de quien escribe
#   "la comida estaba podrida"   -> valoración: expresa el asco de quien escribe
# ---------------------------------------------------------------------------
PRIMERA = {"estoy", "me", "yo", "siento", "senti", "tengo", "soy", "ando", "sigo", "voy",
           "quede", "he", "hemos", "estamos", "nos", "quiero", "odio", "temo"}
TERCERA = {"esta", "estan", "parece", "parecen", "anda", "andan", "siguen", "tiene", "tienen",
           "le", "les", "se", "ella", "ellos", "ellas", "usted", "ustedes"}
AMBIGUOS = {"estaba", "estaban", "quedo", "sentia"}       # 1ª o 3ª persona: depende del sujeto
VERBOS_3A = {"odia", "odian", "llora", "lloran", "sufre", "sufren", "teme", "temen", "adora",
             "adoran", "ama", "aman", "echa", "echan"}
DETERMINANTES = {"mi", "mis", "tu", "tus", "su", "sus", "el", "la", "los", "las"}
CORTES = {"y", "pero", "porque", "que", "cuando", "aunque", "pues", "sin_embargo", "o", "si",
          "como", "mientras"}
# Palabras que VALORAN algo (no describen el estado de nadie): siempre son de quien escribe
VALORACIONES = ("podrid", "asquer", "apest", "desagrad", "repugn", "genial", "maravill",
                "fantastic", "increible", "perfect", "estupend", "injust", "insoportable",
                "maldit", "idiota", "imbecil", "horrible", "guay", "chachi", "mola", "flipante")


EXCLAMATIVOS = {"que", "menudo", "menuda", "vaya", "como"}


def _quien_siente(tokens, originales, i, largo, pausas=()):
    """None si la emoción es de quien escribe; si es de otra persona, quién ('mi hermano')."""
    propias = tokens[i:i + largo]
    verbo_3a = propias[0] in VERBOS_3A            # "mi jefe me ODIA": quien odia es el jefe
    if not verbo_3a and (set(propias) & PRIMERA or propias[0].startswith(VALORACIONES)
                         or propias[0] in EXCLAMATIVOS):   # "¡qué asco!" lo dice quien escribe
        return None
    # Hasta 5 palabras atrás, sin pasar de una pausa (coma...) ni de "y", "que", "pero"...
    ventana, j = [], i - 1
    while j >= 0 and len(ventana) < 5 and tokens[j] not in CORTES and (j + 1) not in pausas:
        ventana.append(j)
        j -= 1
    palabras = {tokens[k] for k in ventana}
    if palabras & PRIMERA and not verbo_3a:
        return None
    sujeto = None
    for k in sorted(ventana):                     # "mi hermano", "la profe", "ella"...
        if tokens[k] in DETERMINANTES and k + 1 < i and tokens[k + 1] not in TERCERA | AMBIGUOS:
            sujeto = f"{originales[k]} {originales[k + 1]}"
            break
        if tokens[k] in {"ella", "ellos", "ellas", "usted", "ustedes"}:
            sujeto = originales[k]
            break
    de_otro = (palabras & TERCERA or verbo_3a or (sujeto and palabras & AMBIGUOS))
    return (sujeto or "otra persona") if de_otro else None


# ---------------------------------------------------------------------------
# PASO 2: puntuación emocional
# ---------------------------------------------------------------------------
def _puntuar_emociones(texto, blob):
    puntos = {e: 0.0 for e in EMOCIONES}
    disparadores = {e: [] for e in EMOCIONES}
    traza = []
    otras = []                    # emociones de otras personas: [{"quien":..., "emocion":...}]

    for oracion in blob.sentences:
        originales, tokens, pausas = _tokenizar(oracion)
        factor_exclamacion = min(1 + 0.2 * str(oracion).count("!"), 1.6)

        # Contraste: lo que va DESPUÉS del último "pero" pesa más (x1.3)
        # y lo de ANTES pesa menos (x0.7). "Estoy bien, pero no puedo más".
        pos_contraste = max((k for k, t in enumerate(tokens) if t in CONTRASTE), default=None)

        usados = set()
        i = 0
        while i < len(tokens):
            coincidencia = _buscar_frase(tokens, i)
            if coincidencia:
                largo, hallazgos = coincidencia
                usados.update(range(i, i + largo))
                palabra = " ".join(originales[i:i + largo])
            else:
                largo, hallazgos = 1, _buscar_palabra(tokens[i])
                palabra = originales[i]

            # Regla 0 — ¿QUIÉN la siente? Si es otra persona, no es emoción de quien escribe
            quien = _quien_siente(tokens, originales, i, largo, pausas) if hallazgos else None
            if quien:
                for emocion, _ in hallazgos:
                    if all(o["emocion"] != emocion for o in otras):
                        otras.append({"quien": quien, "emocion": emocion})
                    traza.append(f"'{palabra}' -> {emocion} de {quien} (no de quien escribe)")
                hallazgos = []

            if hallazgos:
                # Regla 1 — NEGACIÓN: 3 palabras hacia atrás, sin cruzar un "pero"
                negada = False
                for j in range(i - 1, max(-1, i - 4), -1):
                    if tokens[j] in CONTRASTE:
                        break
                    if j not in usados and tokens[j] in NEGACIONES:
                        negada = True
                        break

                # Regla 2 — INTENSIFICADORES: 2 palabras hacia atrás
                intensidad = 1.0
                for j in range(max(0, i - 2), i):
                    intensidad *= INTENSIFICADORES.get(tokens[j], 1.0)

                # Regla 3 — MAYÚSCULAS (grito)
                grito = 1.3 if originales[i].isupper() and len(originales[i]) > 1 else 1.0

                # Regla 4 — CONTRASTE
                if pos_contraste is None:
                    contraste = 1.0
                else:
                    contraste = 0.7 if i < pos_contraste else 1.3

                for emocion, peso in hallazgos:
                    valor = peso * intensidad * grito * factor_exclamacion * contraste
                    if not negada:
                        puntos[emocion] += valor
                        disparadores[emocion].append(palabra)
                        traza.append(f"'{palabra}' -> {emocion} +{valor:.2f}")
                    elif emocion in OPUESTOS:
                        opuesta = OPUESTOS[emocion]
                        puntos[opuesta] += valor * 0.5
                        disparadores[opuesta].append(f"no … {palabra}")
                        traza.append(f"'{palabra}' NEGADA -> {opuesta} +{valor * 0.5:.2f}")
                    else:
                        traza.append(f"'{palabra}' NEGADA -> {emocion} anulada")
            i += largo

    # Regla 5 — EMOJIS
    for emoji, (emocion, peso) in EMOJIS.items():
        veces = texto.count(emoji)
        if veces:
            puntos[emocion] += peso * veces
            disparadores[emocion].append(emoji)
            traza.append(f"emoji {emoji} x{veces} -> {emocion} +{peso * veces}")

    return puntos, disparadores, traza, otras


# ---------------------------------------------------------------------------
# PASO 4: estado afectivo (modelo circumplejo)
# ---------------------------------------------------------------------------
def _estado_afectivo(puntos):
    total = sum(puntos.values())
    if total == 0:
        return 0.0, 0.0, "Neutro (sin carga emocional clara)"
    valencia = sum(CIRCUMPLEJO[e][0] * p for e, p in puntos.items()) / total
    activacion = sum(CIRCUMPLEJO[e][1] * p for e, p in puntos.items()) / total

    if valencia >= 0.15:
        estado = ("Agradable y con energía (entusiasmo, ilusión)" if activacion >= 0
                  else "Agradable y en calma (serenidad, bienestar)")
    elif valencia <= -0.15:
        estado = ("Desagradable y en tensión (estrés, enfado, miedo)" if activacion >= 0
                  else "Desagradable y con poca energía (desánimo, abatimiento)")
    else:
        estado = "Mixto o ambivalente"
    return valencia, activacion, estado


# ---------------------------------------------------------------------------
# PASO 5: marcadores lingüísticos, distorsiones y riesgo
# ---------------------------------------------------------------------------
def _marcadores(texto, normal, palabras, porcentajes):
    senales = []
    n = len(palabras)

    # Autofoco (Pennebaker). Umbral alto porque en español "me" es muy frecuente
    # ("me grita", "me dijo") y no siempre indica foco en uno mismo.
    yo = sum(p in M.PRIMERA_PERSONA for p in palabras)
    if n >= 12 and yo / n >= 0.18:
        senales.append(Senal(
            "autofoco", "Lenguaje muy centrado en uno mismo",
            "Usar mucho 'yo/me/mi' se asocia a malestar: la atención se queda girando "
            "sobre uno mismo (Pennebaker).",
            [f"{yo} de {n} palabras ({yo / n:.0%}) son 'yo', 'me' o 'mi'"]))

    # Absolutismo (Al-Mosaiwi y Johnstone, 2018)
    absolutas = [p for p in palabras if p in M.ABSOLUTISTAS]
    if len(absolutas) >= 2 and len(absolutas) / n >= 0.03:
        senales.append(Senal(
            "absolutismo", "Pensamiento absolutista",
            "Palabras como 'siempre', 'nunca' o 'nada' no dejan matices. Son mucho más "
            "frecuentes en personas con ansiedad o depresión (Al-Mosaiwi y Johnstone, 2018).",
            sorted(set(absolutas))))

    # Señales por patrones
    negativo = sum(porcentajes.get(e, 0) for e in NEGATIVAS)
    positivo = sum(porcentajes.get(e, 0) for e in POSITIVAS)
    for sid, (nombre, patrones, explicacion) in M.SENALES.items():
        evid = _buscar_patrones(patrones, texto, normal)
        if sid == "minimizacion" and negativo < 40:
            continue            # "estoy bien" solo es sospechoso si el resto es negativo
        if evid:
            senales.append(Senal(sid, nombre, explicacion, evid))

    # Ambivalencia: emociones positivas y negativas a la vez.
    # Si hay minimización ("estoy bien, pero..."), lo positivo es una máscara,
    # no una emoción real, así que no lo contamos como ambivalencia.
    minimiza = any(s.id == "minimizacion" for s in senales)
    if positivo >= 25 and negativo >= 25 and not minimiza:
        senales.append(Senal(
            "ambivalencia", "Ambivalencia emocional",
            "Conviven emociones agradables y desagradables. Es muy humano (alegría y pena "
            "a la vez) y suele indicar una situación con varias caras.",
            [f"{positivo:.0f} % emociones agradables / {negativo:.0f} % desagradables"]))

    # Distorsiones cognitivas
    distorsiones = []
    for did, (nombre, patrones, explicacion, pregunta) in M.DISTORSIONES.items():
        evid = _buscar_patrones(patrones, texto, normal)
        if evid:
            distorsiones.append(Senal(did, nombre, explicacion, evid, pregunta))

    # Riesgo
    evid_riesgo = _buscar_patrones(M.RIESGO_ALTO, texto, normal)
    if evid_riesgo:
        riesgo = "alto"
    elif any(s.id == "desesperanza" for s in senales):
        riesgo = "moderado"
    else:
        riesgo = "bajo"

    return senales, distorsiones, riesgo, evid_riesgo


# ---------------------------------------------------------------------------
# Contexto de la conversación
# ---------------------------------------------------------------------------
def aplicar_contexto(a, anterior):
    """
    Un psicólogo no escucha cada frase por separado: recuerda lo que se ha dicho.
      - Un mensaje corto suele ser la RESPUESTA a la pregunta anterior
        ("¿qué te ha molestado?" -> "no hay quesitos en clase").
      - CONTINUIDAD EMOCIONAL: si ese mensaje no trae una emoción clara, la
        emoción del mensaje anterior sigue ahí. No desaparece de un mensaje a otro.
      - El estilo también se mantiene: una respuesta corta da poca información
        de registro, así que se conserva el de antes.
    """
    if anterior is None:
        return a
    a.es_respuesta = a.n_palabras <= 20 and "?" not in a.texto
    if a.es_respuesta and a.dominante == "neutral" and anterior.dominante != "neutral":
        a.dominante = anterior.dominante
        a.emocion_por_contexto = True
        a.valencia, a.activacion, a.estado = anterior.valencia, anterior.activacion, anterior.estado
        a.traza.append(f"sin emoción clara -> se mantiene la del mensaje anterior ({anterior.dominante})")
    if a.estilo.registro == "neutro" and anterior.estilo.registro in ("cercano", "coloquial", "formal"):
        a.estilo.registro = anterior.estilo.registro
    if a.estilo.tratamiento == "tu" and anterior.estilo.tratamiento == "usted":
        a.estilo.tratamiento = "usted"
    return a


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------
def analizar(texto, usar_modelos=None, usar_juez=None, contexto=None):
    """usar_modelos: None = según USAR_MODELOS; False = solo reglas; True = híbrido.
    usar_juez: None = si Ollama está disponible; False/True = forzado.
    contexto: el mensaje anterior de la persona (ayuda al LLM a entender la situación)."""
    original = texto
    texto = expandir_abreviaturas(texto)      # "q" -> "que", "pq" -> "porque"...
    blob = TextBlob(texto)
    normal = normalizar(texto)
    palabras = [normalizar(w) for w in blob.words]
    n = max(len(palabras), 1)

    puntos, disparadores, traza, otras = _puntuar_emociones(texto, blob)

    # Los pensamientos generan emociones: "¿y si suspendo?" suma ansiedad
    patrones = {**{k: v[1] for k, v in M.SENALES.items()},
                **{k: v[1] for k, v in M.DISTORSIONES.items()}}
    for sid, (emocion, peso) in M.PENSAMIENTO_A_EMOCION.items():
        evid = _buscar_patrones(patrones[sid], texto, normal)
        if evid:
            puntos[emocion] += peso * len(evid)
            disparadores[emocion].extend(evid)
            traza.append(f"pensamiento '{sid}' ({', '.join(evid)}) -> {emocion} +{peso * len(evid)}")

    idioma = _detectar_idioma(palabras)

    # PASO 3a: porcentajes según las REGLAS
    total = sum(puntos.values())
    pct_reglas = {e: (p / total * 100 if total else 0.0) for e, p in puntos.items()}

    # PASO 3b: MODELOS de lenguaje y FUSIÓN con las reglas
    usar = USAR_MODELOS if usar_modelos is None else usar_modelos
    ml = modelos.analizar_ml(texto) if usar and idioma == "es" else None
    if ml:
        top = lambda d, k=3: ", ".join(f"{e} {v:.2f}" for e, v in
                                       sorted(d.items(), key=lambda x: x[1], reverse=True)[:k])
        traza.append(f"modelo pysentimiento (familia): {top(ml['familias'])}")
        traza.append(f"modelo zero-shot (matices): {top(ml['matices'])}")

        no_neutral = 1 - ml["neutral"]
        suma_ml = sum(ml["emociones"].values()) or 1.0
        pct_ml = {e: ml["emociones"].get(e, 0.0) / suma_ml * 100 for e in EMOCIONES}

        # Ironía: solo si el modelo está MUY seguro y además hay palabras positivas
        # literales ("genial", "maravilla"). Entonces esa "alegría" es en realidad
        # frustración: la pasamos a ira (60 %) y tristeza (40 %), en reglas y modelo.
        ironico = (ml["ironia"] >= UMBRAL_IRONIA and sum(pct_reglas[e] for e in POSITIVAS) > 50)
        if ironico:
            for d in (puntos, pct_ml):
                positivo = sum(d.get(e, 0) for e in POSITIVAS)
                for e in POSITIVAS:
                    d[e] = 0.0
                d["ira"] = d.get("ira", 0) + positivo * 0.6
                d["tristeza"] = d.get("tristeza", 0) + positivo * 0.4
            total = sum(puntos.values())
            pct_reglas = {e: (p / total * 100 if total else 0.0) for e, p in puntos.items()}
            traza.append(f"ironía {ml['ironia']:.0%} -> la 'alegría' literal pasa a frustración")

        if total == 0:
            # Las reglas no han encontrado nada (expresión que no está en las listas):
            # decide el modelo, salvo que crea que el texto es neutral.
            if ml["neutral"] >= UMBRAL_NEUTRAL:
                porcentajes = {e: 0.0 for e in pct_reglas}
            else:
                porcentajes = pct_ml
                traza.append("las reglas no encuentran nada -> decide el modelo")
        else:
            # Las dos fuentes opinan: media ponderada. El peso del modelo baja si el
            # propio modelo cree que el texto es neutral.
            w_m = PESO_MODELOS * no_neutral
            porcentajes = {e: (PESO_REGLAS * pct_reglas[e] + w_m * pct_ml.get(e, 0)) / (PESO_REGLAS + w_m)
                           for e in pct_reglas}
        fuente = "híbrido (reglas + modelos)"
    else:
        porcentajes = pct_reglas
        fuente = "reglas"

    # PASO 3c: el LLM como JUEZ DE PERSPECTIVA. Las reglas y los modelos detectan
    # emociones que aparecen en el texto; el LLM entiende la situación y dice qué
    # siente QUIEN ESCRIBE ("mi hermano está enfadado conmigo" -> culpa, preocupación)
    # y qué sienten los demás. Su opinión pesa la mitad.
    juez = None
    # Si las reglas ven que la emoción del texto es de OTRA persona ("mi novia está
    # triste") y ninguna de quien escribe, los modelos están midiendo la emoción de esa
    # otra persona (miden la que transmite el texto): entonces el juez pesa mucho más.
    peso_juez = PESO_JUEZ_OTRAS if (otras and total == 0) else PESO_JUEZ
    if (llm.usar() if usar_juez is None else usar_juez) and idioma == "es":
        juez = llm.juzgar(original, contexto, pistas=otras)
    if juez is not None:
        pct_juez = {e: 0.0 for e in EMOCIONES}
        for item in juez["emociones"]:
            pct_juez[item["emocion"]] += item["intensidad"]
        suma_juez = sum(pct_juez.values())
        traza.append("LLM (quien escribe): " + (", ".join(
            f"{i['emocion']} {i['intensidad']:.1f}" for i in juez["emociones"]) or "sin emoción")
            + f" — «{juez['analisis']}»")
        if suma_juez > 0:
            pct_juez = {e: v / suma_juez * 100 for e, v in pct_juez.items()}
            if sum(porcentajes.values()) == 0:
                porcentajes = pct_juez
            else:
                porcentajes = {e: (1 - peso_juez) * porcentajes[e] + peso_juez * pct_juez[e]
                               for e in porcentajes}
        elif total == 0:
            porcentajes = {e: 0.0 for e in porcentajes}   # nadie ve emoción de quien escribe
        for o in juez["otras_personas"]:
            if all(x["emocion"] != o["emocion"] for x in otras):
                otras.append(o)
        fuente += " + LLM (perspectiva)"

    porcentajes = dict(sorted(porcentajes.items(), key=lambda x: x[1], reverse=True))
    orden = list(porcentajes)
    hay_emocion = sum(porcentajes.values()) > 0
    dominante = orden[0] if hay_emocion else "neutral"
    secundarias = [e for e in orden[1:3] if porcentajes[e] >= 15] if hay_emocion else []

    # Intensidad: densidad de palabras emocionales; si solo ha opinado el modelo,
    # su seguridad de que hay emoción.
    intensidad = total / n
    if total:
        nivel = "baja" if intensidad < 0.15 else "media" if intensidad < 0.4 else "alta"
    elif hay_emocion:
        if juez and juez["emociones"]:
            confianza = max(i["intensidad"] for i in juez["emociones"])
        else:
            confianza = 1 - ml["neutral"] if ml else 0.5
        nivel = "baja" if confianza < 0.6 else "media" if confianza < 0.85 else "alta"
    else:
        nivel = "nula"

    valencia, activacion, estado = _estado_afectivo(porcentajes)
    senales, distorsiones, riesgo, evid_riesgo = _marcadores(texto, normal, palabras, porcentajes)
    if ml and ironico:
        senales.append(Senal(
            "ironia", "Ironía o sarcasmo",
            "Lo que dice no se corresponde con lo que quiere decir ('genial, otra vez lunes'). "
            "Un psicólogo lo nota por el tono; aquí lo detecta un modelo entrenado.",
            [f"probabilidad {ml['ironia']:.0%} según el modelo"]))
    resultado = Analisis(
        texto=texto, idioma=idioma, n_palabras=len(palabras), puntos=puntos,
        porcentajes=porcentajes, dominante=dominante, secundarias=secundarias,
        intensidad=intensidad, nivel_intensidad=nivel, valencia=valencia,
        activacion=activacion, estado=estado, senales=senales, distorsiones=distorsiones,
        riesgo=riesgo, evidencias_riesgo=evid_riesgo,
        disparadores={e: d for e, d in disparadores.items() if d}, traza=traza,
    )
    resultado.texto = original
    resultado.fuente = fuente
    resultado.modelo = ml
    resultado.otras_personas = otras
    resultado.estilo = detectar_estilo(original)    # el estilo, sobre el texto tal cual
    resultado.apoyo_explicito = bool(re.search(
        r"\b(me (apoya|apoyan|apoyo|ayuda|ayudan|ayudo|escucha|escuchan|escucho|entiende)"
        r"|hable con|habl[eo] con|estuvo conmigo|estuvieron conmigo)\b", normal))
    if idioma == "en":   # TextBlob solo sabe calcular sentimiento en inglés
        resultado.polaridad_textblob = blob.sentiment.polarity
        resultado.subjetividad_textblob = blob.sentiment.subjectivity
    return resultado
