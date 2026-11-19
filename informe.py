"""
Genera el informe "tipo psicólogo" a partir de un Analisis.

Técnicas que imita:
  - REFLEJO EMPÁTICO (escucha activa, Carl Rogers): devolver a la persona lo que
    siente usando sus propias palabras, para que se sienta comprendida.
  - VALIDACIÓN: transmitir que la emoción tiene sentido en su situación.
  - PREGUNTAS SOCRÁTICAS (terapia cognitiva): en vez de dar consejos, hacer
    preguntas que ayuden a la persona a explorar y cuestionar sus pensamientos.
  - SEGUIMIENTO: en una sesión, observar cómo evoluciona el estado emocional.
"""

import re
from collections import Counter

from lexico import ICONOS, NOMBRES
import marcadores as M

# Reflejo + validación para cada emoción. {cita} = palabras de la persona.
REFLEJOS = {
    "alegria": "Transmites alegría{cita}. Qué bien que lo estés viviendo así.",
    "serenidad": "Se percibe calma y tranquilidad{cita}. Es un estado valioso, merece la pena notarlo.",
    "amor": "Hablas con cariño y afecto{cita}. Se nota que esa conexión es importante para ti.",
    "esperanza": "Hay esperanza en lo que cuentas{cita}: ganas de que las cosas vayan bien.",
    "sorpresa": "Algo te ha pillado por sorpresa{cita}. Es normal necesitar un tiempo para asimilarlo.",
    "tristeza": "Lo que cuentas suena a tristeza{cita}. Es lógico sentirse así cuando algo duele.",
    "soledad": "Parece que te sientes sin compañía o sin nadie que te entienda{cita}, y eso pesa mucho.",
    "ira": "Se percibe enfado o frustración{cita}. Suele aparecer cuando algo se vive como injusto "
           "o cuando se cruza un límite importante.",
    "miedo": "Hay miedo en lo que dices{cita}. Ante algo que se vive como una amenaza es una reacción natural.",
    "ansiedad": "Transmites preocupación y tensión{cita}, como si la mente no pudiera parar.",
    "culpa": "Parece que cargas con culpa por lo que pasó{cita}.",
    "verguenza": "Noto una mirada muy dura hacia ti{cita}. La vergüenza duele porque ataca cómo "
                 "nos vemos a nosotros mismos.",
    "asco": "Hay rechazo o desagrado ante lo que describes{cita}.",
}

PREGUNTAS = {
    "alegria": ["¿Qué ha hecho que te sientas así?", "¿Cómo podrías tener más momentos como este?"],
    "serenidad": ["¿Qué te está ayudando a estar así?", "¿Qué podrías hacer para cuidar esta calma?"],
    "amor": ["¿Qué significa esa persona para ti?", "¿Se lo has podido expresar?"],
    "esperanza": ["¿Qué pasos te acercan a eso que esperas?", "¿Qué te da esa esperanza?"],
    "sorpresa": ["¿Cómo te sientes ahora que ha pasado?", "¿Qué cambia esto para ti?"],
    "tristeza": ["¿Desde cuándo te sientes así?", "¿Qué es lo que más te duele de esta situación?"],
    "soledad": ["¿Hay alguien con quien te sientas a gusto hablando?",
                "¿Cuándo empezaste a sentirte así?"],
    "ira": ["¿Qué es lo que sientes que no es justo?", "¿Qué necesitarías que cambiara?"],
    "miedo": ["¿Qué es exactamente lo que temes que pase?", "¿Qué te ayudaría a sentir más seguridad?"],
    "ansiedad": ["¿En qué momentos del día lo notas más?",
                 "¿Lo notas también en el cuerpo (sueño, respiración, estómago)?"],
    "culpa": ["¿Qué crees que hiciste mal?",
              "¿Lo juzgarías igual si le hubiera pasado a otra persona?"],
    "verguenza": ["¿Qué temes que piensen los demás?",
                  "¿Le hablarías así a alguien a quien quieres?"],
    "asco": ["¿Qué es lo que te produce más rechazo?", "¿Cómo te afecta esta situación?"],
    "neutral": ["¿Cómo te sientes con lo que me cuentas?",
                "Si tuvieras que ponerle nombre a lo que sientes ahora, ¿cuál sería?"],
}

PREGUNTAS_SENAL = {
    "desesperanza": "¿Ha habido algún momento, aunque sea pequeño, en que esto se haya sentido menos pesado?",
    "minimizacion": "Dices que estás bien, pero el resto suena distinto. ¿Cómo estás de verdad?",
    "rumiacion": "Cuando le das vueltas a lo que pasó, ¿te ayuda a encontrar soluciones o te hace sentir peor?",
    "preocupacion": "De todo lo que te preocupa, ¿qué depende de ti y qué no?",
    "somatizacion": "¿Cómo estás durmiendo y comiendo últimamente?",
    "vaguedad": "Cuando dices que estás 'mal', ¿se parece más a tristeza, a enfado, a miedo o a cansancio?",
    "apoyo_social": "¿Qué papel tienen esas personas en lo que estás viviendo?",
    "ambivalencia": "Parece que sientes varias cosas a la vez. ¿Cuál pesa más ahora mismo?",
    "autofoco": "¿Cómo crees que ven la situación las otras personas implicadas?",
}

AVISO = ("⚠ Esto es una simulación educativa basada en reglas. No es un diagnóstico ni "
         "sustituye a un profesional de la salud mental.")


def _barra(pct, ancho=20):
    return "█" * round(pct / 100 * ancho)


def _eje(valor, izq, der, ancho=21):
    """Dibuja un eje de -1 a +1 con un marcador en el valor: izq ──●── der"""
    pos = round((valor + 1) / 2 * (ancho - 1))
    linea = "".join("●" if k == pos else "─" for k in range(ancho))
    return f"{izq:>12} {linea} {der}"


def _nombre(emocion):
    return f"{ICONOS[emocion]} {NOMBRES[emocion]}"


def _clausula(texto, palabra):
    """Devuelve el trozo de frase (entre signos de puntuación) donde aparece la
    palabra, para citar a la persona con sus propias palabras."""
    from analizador import normalizar
    objetivo = normalizar(palabra.replace("no … ", ""))
    for trozo in re.split(r"[.,;!?¡¿\n]+", texto):
        trozo = trozo.strip()
        if objetivo in normalizar(trozo):
            return trozo if len(trozo) <= 60 else palabra
    return palabra


def reflejo_empatico(a):
    if a.dominante == "neutral":
        return "No encuentro una emoción clara en lo que escribes. A veces cuesta ponerle palabras."
    disparadores = a.disparadores.get(a.dominante, [])
    palabra = next((d for d in disparadores if len(d) > 2), None)
    frase = _clausula(a.texto, palabra) if palabra else None
    cita = f" cuando dices «{frase}»" if frase else ""
    frase = REFLEJOS[a.dominante].format(cita=cita)
    if a.secundarias:
        otras = " y ".join(NOMBRES[e].lower() for e in a.secundarias)
        frase += f" También percibo algo de {otras}."
    if any(s.id == "minimizacion" for s in a.senales):
        frase += " Aunque dices que estás bien, lo que cuentas parece más difícil que eso."
    return frase


def preguntas_sugeridas(a, maximo=4):
    preguntas = list(PREGUNTAS[a.dominante])
    for s in a.senales:
        if s.id in PREGUNTAS_SENAL:
            preguntas.append(PREGUNTAS_SENAL[s.id])
    for d in a.distorsiones:
        preguntas.append(d.pregunta)
    vistas, unicas = set(), []
    for p in preguntas:
        if p not in vistas:
            vistas.add(p)
            unicas.append(p)
    # Prioridad: distorsiones y señales primero (son lo más específico), luego la emoción
    especificas = unicas[len(PREGUNTAS[a.dominante]):]
    return (especificas + unicas[:len(PREGUNTAS[a.dominante])])[:maximo]


def _bloque_riesgo(a):
    if a.riesgo == "alto":
        lineas = ["", "🚨 " + "=" * 56,
                  "   ALERTA: el texto contiene expresiones de posible riesgo",
                  f"   ({', '.join('«' + e + '»' for e in a.evidencias_riesgo)}).",
                  "   Si tú o alguien cercano está pensando en hacerse daño,",
                  "   pide ayuda ahora. No estás solo/a:"]
        lineas += [f"     • {r}" for r in M.RECURSOS_AYUDA]
        lineas.append("🚨 " + "=" * 56)
        return lineas
    if a.riesgo == "moderado":
        return ["", "⚠ Se aprecian señales de desesperanza. Si en algún momento aparecen "
                    "pensamientos de hacerte daño, llama al 024 (España) o al 112."]
    return []


def generar_informe(a, mostrar_traza=False):
    L = ["", "═" * 62, "  INFORME DE ANÁLISIS EMOCIONAL", "═" * 62,
         f"Texto: «{a.texto}»"]
    L += _bloque_riesgo(a)      # el riesgo va lo primero, antes que cualquier otra cosa
    L.append("")

    # 1. Emociones
    L.append("1. EMOCIONES DETECTADAS")
    if a.dominante == "neutral":
        L.append("   😐 Neutral: no aparecen palabras con carga emocional.")
    else:
        L.append(f"   Principal: {_nombre(a.dominante)}"
                 + (f"   ·   Secundarias: {', '.join(_nombre(e) for e in a.secundarias)}"
                    if a.secundarias else ""))
        for e, pct in a.porcentajes.items():
            if pct >= 1:
                L.append(f"     {NOMBRES[e]:<16} {_barra(pct):<20} {pct:5.1f} %")
        L.append(f"   Intensidad emocional: {a.nivel_intensidad} ({a.intensidad:.2f} puntos por palabra)")

    # 2. Estado afectivo
    L += ["", "2. ESTADO AFECTIVO (modelo circumplejo de Russell)",
          "   " + _eje(a.valencia, "desagradable", "agradable"),
          "   " + _eje(a.activacion, "apagado", "activado"),
          f"   → {a.estado}"]
    if a.polaridad_textblob is not None:
        L.append(f"   TextBlob (inglés): polaridad {a.polaridad_textblob:+.2f}, "
                 f"subjetividad {a.subjetividad_textblob:.2f}")

    # 3. Cómo se expresa
    L += ["", "3. CÓMO SE EXPRESA (marcadores lingüísticos)"]
    if not a.senales:
        L.append("   Sin señales destacables.")
    for s in a.senales:
        L.append(f"   • {s.nombre}: {', '.join('«' + e + '»' for e in s.evidencias)}")
        L.append(f"     ↳ {s.explicacion}")

    # 4. Pensamientos
    L += ["", "4. PATRONES DE PENSAMIENTO (distorsiones cognitivas)"]
    if not a.distorsiones:
        L.append("   No se detectan distorsiones cognitivas.")
    for d in a.distorsiones:
        L.append(f"   • {d.nombre}: {', '.join('«' + e + '»' for e in d.evidencias)}")
        L.append(f"     ↳ {d.explicacion}")
        L.append(f"     ↳ Para reformular: {d.pregunta}")

    # 5. Respuesta empática
    L += ["", "5. LO QUE DIRÍA UN PSICÓLOGO",
          f"   💬 {reflejo_empatico(a)}",
          "   Preguntas para seguir explorando:"]
    L += [f"     – {p}" for p in preguntas_sugeridas(a)]

    if mostrar_traza and a.traza:
        L += ["", "   [Traza del cálculo]"] + [f"     · {t}" for t in a.traza]

    L += ["", AVISO]
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Modo sesión: varios mensajes seguidos
# ---------------------------------------------------------------------------
def informe_sesion(analisis):
    if not analisis:
        return "No hay mensajes en la sesión."
    L = []
    if any(a.riesgo == "alto" for a in analisis):
        L += ["", "🚨 En la sesión aparecen expresiones de riesgo. Recursos de ayuda:"]
        L += [f"     • {r}" for r in M.RECURSOS_AYUDA]

    L += ["", "═" * 62, f"  RESUMEN DE LA SESIÓN ({len(analisis)} mensajes)", "═" * 62,
          "", "Evolución de la valencia (−1 desagradable … +1 agradable):"]
    for k, a in enumerate(analisis, 1):
        texto = a.texto if len(a.texto) <= 38 else a.texto[:35] + "..."
        L.append(f"  {k:>2}. {_eje(a.valencia, '', '', 15).strip()} {a.valencia:+.2f}  "
                 f"{ICONOS[a.dominante]} {texto}")

    # Tendencia: media de la segunda mitad menos la de la primera
    if len(analisis) >= 2:
        mitad = len(analisis) // 2
        inicio = sum(a.valencia for a in analisis[:mitad]) / mitad
        final = sum(a.valencia for a in analisis[mitad:]) / (len(analisis) - mitad)
        cambio = final - inicio
        if cambio > 0.2:
            tendencia = "📈 Mejora: el tono emocional se vuelve más agradable a lo largo de la sesión."
        elif cambio < -0.2:
            tendencia = "📉 Empeora: el tono emocional se vuelve más desagradable a lo largo de la sesión."
        else:
            tendencia = "➡ Estable: el tono emocional se mantiene parecido."
        L += ["", f"Tendencia: {tendencia} (cambio {cambio:+.2f})"]

    # Emociones acumuladas
    total = Counter()
    for a in analisis:
        total.update(a.puntos)
    suma = sum(total.values())
    if suma:
        L += ["", "Emociones más presentes en la sesión:"]
        for e, p in total.most_common(4):
            if p > 0:
                L.append(f"     {NOMBRES[e]:<16} {_barra(p / suma * 100):<20} {p / suma * 100:5.1f} %")

    # Patrones que se repiten
    patrones = Counter(d.nombre for a in analisis for d in a.distorsiones)
    patrones.update(s.nombre for a in analisis for s in a.senales)
    repetidos = [(n, c) for n, c in patrones.most_common() if c >= 2]
    if repetidos:
        L += ["", "Patrones que se repiten (lo que un psicólogo trabajaría):"]
        L += [f"     • {n} (×{c})" for n, c in repetidos]

    L += ["", AVISO]
    return "\n".join(L)
