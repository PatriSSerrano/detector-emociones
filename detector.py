"""
Detector de emociones en texto (español e inglés).

Idea general:
  1. TextBlob divide el texto en ORACIONES y luego en PALABRAS.
  2. Cada palabra se busca en un léxico de emociones (lexico.py).
  3. Se aplican reglas de contexto: negaciones, intensificadores,
     mayúsculas, exclamaciones y emojis.
  4. Se suman los puntos de cada emoción y se convierten en porcentajes.
  5. Además se calcula la POLARIDAD (-1 negativo ... +1 positivo):
     en inglés la da TextBlob; en español la estimamos a partir de las emociones.

Uso:
    python detector.py            -> modo interactivo
    python detector.py --demo     -> analiza frases de ejemplo
"""

import sys
import unicodedata

from textblob import TextBlob

from lexico import EMOCIONES, EMOJIS, NEGACIONES, INTENSIFICADORES, OPUESTOS

NOMBRES = {
    "alegria": "Alegría 😊", "tristeza": "Tristeza 😢", "ira": "Ira 😡",
    "miedo": "Miedo 😱", "sorpresa": "Sorpresa 😮", "asco": "Asco 🤢",
}

# Palabras muy frecuentes de cada idioma, para adivinar el idioma del texto
PALABRAS_ES = {"el", "la", "los", "las", "de", "que", "y", "en", "es", "estoy", "me",
               "un", "una", "muy", "por", "con", "lo", "se", "mi", "pero", "esta"}
PALABRAS_EN = {"the", "is", "i", "am", "and", "you", "to", "of", "it", "my", "very",
               "this", "that", "are", "was", "not", "but", "so", "feel", "im"}


# ---------------------------------------------------------------------------
# PASO 1: normalizar texto (minúsculas y sin tildes)
# ---------------------------------------------------------------------------
def normalizar(texto):
    """'Alegría' -> 'alegria'. NFD separa la letra de su tilde y luego
    descartamos las tildes (categoría Unicode 'Mn')."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# PASO 2: preparar el léxico en tres tablas para buscar rápido
# ---------------------------------------------------------------------------
def preparar_lexico():
    exactas = {}   # 'feliz' -> [('alegria', 2)]
    raices = []    # ('alegr', 'alegria', 2)   (palabras terminadas en *)
    frases = []    # (('echo', 'de', 'menos'), 'tristeza', 2)
    for emocion, entradas in EMOCIONES.items():
        for palabra, peso in entradas:
            palabra = normalizar(palabra)
            if " " in palabra:
                frases.append((tuple(palabra.split()), emocion, peso))
            elif palabra.endswith("*"):
                raices.append((palabra[:-1], emocion, peso))
            else:
                exactas.setdefault(palabra, []).append((emocion, peso))
    # Las raíces más largas primero: son más específicas
    raices.sort(key=lambda r: len(r[0]), reverse=True)
    frases.sort(key=lambda f: len(f[0]), reverse=True)
    return exactas, raices, frases


EXACTAS, RAICES, FRASES = preparar_lexico()


def buscar_palabra(palabra):
    """Devuelve la lista de (emoción, peso) que activa una palabra."""
    if palabra in EXACTAS:
        return EXACTAS[palabra]
    encontradas = {}
    for raiz, emocion, peso in RAICES:
        if palabra.startswith(raiz) and emocion not in encontradas:
            encontradas[emocion] = peso
    return list(encontradas.items())


def buscar_frase(tokens, i):
    """¿Empieza en la posición i alguna expresión de varias palabras?"""
    for frase, emocion, peso in FRASES:
        if tuple(tokens[i:i + len(frase)]) == frase:
            return len(frase), [(emocion, peso)]
    return None


def detectar_idioma(texto):
    palabras = [normalizar(w) for w in TextBlob(texto).words]
    es = sum(p in PALABRAS_ES for p in palabras)
    en = sum(p in PALABRAS_EN for p in palabras)
    return "en" if en > es else "es"


# ---------------------------------------------------------------------------
# PASO 3: el análisis
# ---------------------------------------------------------------------------
def analizar(texto):
    puntos = {emocion: 0.0 for emocion in EMOCIONES}
    detalles = []  # explicación de por qué se ha sumado cada punto

    blob = TextBlob(texto)

    # Trabajamos oración por oración para que una negación de una frase
    # no afecte a la siguiente ("No vino. Estoy feliz.")
    for oracion in blob.sentences:
        originales = list(oracion.words)            # tal cual (para ver MAYÚSCULAS)
        tokens = [normalizar(w) for w in originales]

        # Cada '!' en la oración añade un 20 % de intensidad (máximo +60 %)
        factor_exclamacion = min(1 + 0.2 * str(oracion).count("!"), 1.6)

        usados_en_frase = set()   # posiciones ya consumidas por una expresión
        i = 0
        while i < len(tokens):
            coincidencia = buscar_frase(tokens, i)
            if coincidencia:
                largo, hallazgos = coincidencia
                usados_en_frase.update(range(i, i + largo))
                texto_hallado = " ".join(originales[i:i + largo])
            else:
                largo, hallazgos = 1, buscar_palabra(tokens[i])
                texto_hallado = originales[i]

            if hallazgos:
                # --- Regla 1: NEGACIÓN en las 3 palabras anteriores ---
                ventana = [tokens[j] for j in range(max(0, i - 3), i)
                           if j not in usados_en_frase]
                negada = any(t in NEGACIONES for t in ventana)

                # --- Regla 2: INTENSIFICADORES en las 2 palabras anteriores ---
                intensidad = 1.0
                for j in range(max(0, i - 2), i):
                    intensidad *= INTENSIFICADORES.get(tokens[j], 1.0)

                # --- Regla 3: palabra en MAYÚSCULAS = grito = +30 % ---
                gritada = 1.3 if originales[i].isupper() and len(originales[i]) > 1 else 1.0

                for emocion, peso in hallazgos:
                    valor = peso * intensidad * gritada * factor_exclamacion
                    if not negada:
                        puntos[emocion] += valor
                        detalles.append(f"'{texto_hallado}' -> {emocion} +{valor:.2f}")
                    elif emocion in OPUESTOS:
                        opuesta = OPUESTOS[emocion]
                        puntos[opuesta] += valor * 0.5
                        detalles.append(f"'{texto_hallado}' NEGADA -> {opuesta} +{valor * 0.5:.2f}")
                    else:
                        detalles.append(f"'{texto_hallado}' NEGADA -> {emocion} anulada")
            i += largo

    # --- Regla 4: EMOJIS (se buscan en el texto original) ---
    for emoji, (emocion, peso) in EMOJIS.items():
        veces = texto.count(emoji)
        if veces:
            puntos[emocion] += peso * veces
            detalles.append(f"emoji {emoji} x{veces} -> {emocion} +{peso * veces}")

    # ---------------------------------------------------------------------
    # PASO 4: convertir puntos en porcentajes y decidir la emoción dominante
    # ---------------------------------------------------------------------
    total = sum(puntos.values())
    porcentajes = {e: (p / total * 100 if total else 0.0) for e, p in puntos.items()}
    ordenadas = sorted(porcentajes.items(), key=lambda x: x[1], reverse=True)

    if total == 0:
        dominante = "neutral"
    else:
        dominante = ordenadas[0][0]

    # Si la segunda emoción está muy cerca de la primera, es un texto mixto
    mixta = total > 0 and ordenadas[1][1] >= ordenadas[0][1] * 0.8

    # ---------------------------------------------------------------------
    # PASO 5: polaridad
    # ---------------------------------------------------------------------
    idioma = detectar_idioma(texto)
    if idioma == "en":
        polaridad = blob.sentiment.polarity          # TextBlob (solo inglés)
        subjetividad = blob.sentiment.subjectivity
        fuente = "TextBlob"
    else:
        positivo = puntos["alegria"]
        negativo = puntos["tristeza"] + puntos["ira"] + puntos["miedo"] + puntos["asco"]
        polaridad = (positivo - negativo) / (positivo + negativo) if (positivo + negativo) else 0.0
        subjetividad = None
        fuente = "léxico de emociones"

    return {
        "texto": texto,
        "idioma": idioma,
        "dominante": dominante,
        "mixta": mixta,
        "segunda": ordenadas[1][0] if mixta else None,
        "porcentajes": dict(ordenadas),
        "puntos": puntos,
        "polaridad": polaridad,
        "subjetividad": subjetividad,
        "fuente_polaridad": fuente,
        "detalles": detalles,
    }


# ---------------------------------------------------------------------------
# Mostrar el resultado bonito en la terminal
# ---------------------------------------------------------------------------
def mostrar(resultado, explicar=True):
    print("\n" + "=" * 60)
    print(f"Texto: {resultado['texto']}")
    print(f"Idioma detectado: {resultado['idioma']}")
    print("-" * 60)
    if resultado["dominante"] == "neutral":
        print("Emoción dominante: Neutral 😐 (no se encontraron palabras emocionales)")
    else:
        linea = f"Emoción dominante: {NOMBRES[resultado['dominante']]}"
        if resultado["mixta"]:
            linea += f"  (mezclada con {NOMBRES[resultado['segunda']]})"
        print(linea)
        for emocion, pct in resultado["porcentajes"].items():
            if pct > 0:
                barra = "█" * round(pct / 5)
                print(f"  {NOMBRES[emocion]:<14} {barra:<20} {pct:5.1f} %")

    pol = resultado["polaridad"]
    tono = "positivo" if pol > 0.1 else "negativo" if pol < -0.1 else "neutro"
    print(f"Polaridad: {pol:+.2f} ({tono}) — calculada con {resultado['fuente_polaridad']}")
    if resultado["subjetividad"] is not None:
        print(f"Subjetividad: {resultado['subjetividad']:.2f} (0 = objetivo, 1 = opinión)")

    if explicar and resultado["detalles"]:
        print("Por qué:")
        for d in resultado["detalles"]:
            print(f"   · {d}")


EJEMPLOS = [
    "¡Hoy es el mejor día de mi vida, estoy muy feliz!",
    "No estoy contento con el resultado.",
    "Estoy FURIOSO, odio que me mientan!!",
    "Tengo mucho miedo de quedarme sin trabajo, me da pánico.",
    "No me lo puedo creer, ¡me han dado el premio! 😱",
    "Qué asco, la comida estaba podrida 🤢",
    "Te echo de menos, me siento sola 😢",
    "Mañana tengo una reunión a las diez.",
    "I am so happy and excited about this trip!",
    "No tengo miedo.",
]


if __name__ == "__main__":
    # Para que la consola de Windows muestre bien emojis y tildes
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    if "--demo" in sys.argv:
        for frase in EJEMPLOS:
            mostrar(analizar(frase))
    else:
        print("Detector de emociones — escribe un texto (o 'salir' para terminar)")
        while True:
            texto = input("\n> ").strip()
            if texto.lower() in {"salir", "exit", "q"}:
                break
            if texto:
                mostrar(analizar(texto))
