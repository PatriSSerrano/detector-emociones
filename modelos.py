"""
Modelos de lenguaje entrenados (aprendizaje automático).

Por qué: una lista de palabras nunca cubre todo el español. Estos modelos
han aprendido el SIGNIFICADO a partir de millones de textos reales:
  - Convierten cada frase en vectores de números (embeddings) donde frases
    con significado parecido quedan cerca: "estoy hasta el moño" y "no aguanto
    más esto" se parecen aunque no compartan palabras.
  - Son TRANSFORMERS: leen la frase entera con su contexto, así que distinguen
    "me mato a estudiar" de "me quiero matar", y pueden detectar ironía.

Dos modelos, organizados como lo haría un psicólogo, de lo general a lo concreto:

1. pysentimiento (RoBERTuito, entrenado con tuits en español, con jerga y tacos)
   -> la FAMILIA de la emoción: alegría, tristeza, ira, miedo, sorpresa, asco u
      "otros" (sin emoción). También detecta la IRONÍA.

2. Clasificación ZERO-SHOT (mDeBERTa multilingüe entrenado en NLI)
   NLI = Natural Language Inference: decidir si una hipótesis SE DEDUCE de un
   texto. Le damos el texto y la hipótesis "En este texto, la persona siente
   culpa." y nos dice la probabilidad. Sirve para CUALQUIER etiqueta sin
   entrenar nada.
   -> el MATIZ dentro de la familia: dentro de "tristeza", ¿es tristeza,
      soledad, culpa o vergüenza?

Si las librerías no están instaladas, el sistema sigue funcionando solo con reglas.
"""

import os
import sys
from functools import lru_cache

# Silenciar avisos técnicos de Hugging Face en Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

MODELO_ZERO_SHOT = os.environ.get("MODELO_ZERO_SHOT", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
# Se pregunta por QUIEN ESCRIBE: con "la persona siente..." el modelo podía responder
# por cualquiera de las personas que aparecen en el texto.
PLANTILLA_HIPOTESIS = "Quien ha escrito este mensaje siente {}."

# pysentimiento -> nuestras emociones
FAMILIA_DE = {"joy": "alegria", "sadness": "tristeza", "anger": "ira", "fear": "miedo",
              "surprise": "sorpresa", "disgust": "asco"}

# Matices de cada familia (los decide el zero-shot)
MATICES = {
    "alegria": ["alegria", "serenidad", "amor", "esperanza"],
    "tristeza": ["tristeza", "soledad", "culpa", "verguenza"],
    "miedo": ["miedo", "ansiedad"],
    "ira": ["ira"],
    "sorpresa": ["sorpresa"],
    "asco": ["asco"],
}

# Cómo se le describe cada emoción al modelo zero-shot. Descripciones concretas
# funcionan mejor que una sola palabra ("amor" a secas hacía que "he aprobado el
# carnet" saliera como amor).
ETIQUETAS = {
    "alegria": "alegría o felicidad", "serenidad": "calma y tranquilidad",
    "amor": "amor o cariño hacia alguien", "esperanza": "esperanza o ilusión por el futuro",
    "sorpresa": "sorpresa por algo inesperado", "tristeza": "tristeza o pena",
    "soledad": "soledad o falta de compañía", "ira": "enfado, rabia o frustración",
    "miedo": "miedo ante un peligro", "ansiedad": "ansiedad o preocupación por lo que pueda pasar",
    "culpa": "culpa por algo que hizo", "verguenza": "vergüenza de sí misma o de sí mismo",
    "asco": "asco o rechazo",
}
# OJO: el zero-shot NO sirve para decidir si hay emoción o no. Probado: responde
# "sí, expresa emociones" con ~100 % incluso para "La reunión es en la sala 3", y
# además tiende a elegir "sorpresa". La neutralidad la decide pysentimiento, que sí
# la distingue bien (98-99 % "sin emoción" en textos neutros). Cada modelo, a lo
# que se le da bien.


def disponible():
    try:
        import pysentimiento  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _aviso(msg):
    print(msg, file=sys.stderr, flush=True)


@lru_cache(maxsize=1)
def _silenciar():
    """Quita barras de progreso y avisos técnicos de Hugging Face de la conversación."""
    try:
        from huggingface_hub.utils import disable_progress_bars
        from huggingface_hub.utils import logging as hf_logging
        disable_progress_bars()
        hf_logging.set_verbosity_error()
    except ImportError:
        pass
    try:
        from transformers.utils import logging as tr_logging
        tr_logging.set_verbosity_error()
        tr_logging.disable_progress_bar()
    except ImportError:
        pass


@lru_cache(maxsize=1)
def _analizador_emociones():
    from pysentimiento import create_analyzer
    _aviso("· Cargando modelo de emociones (pysentimiento)... la primera vez se descarga.")
    return create_analyzer(task="emotion", lang="es")


@lru_cache(maxsize=1)
def _analizador_ironia():
    from pysentimiento import create_analyzer
    _aviso("· Cargando modelo de ironía (pysentimiento)...")
    return create_analyzer(task="irony", lang="es")


@lru_cache(maxsize=1)
def _zero_shot():
    from transformers import pipeline
    _aviso(f"· Cargando modelo zero-shot ({MODELO_ZERO_SHOT})...")
    return pipeline("zero-shot-classification", model=MODELO_ZERO_SHOT)


def precargar():
    """Carga los tres modelos de una vez (para no esperar en el primer mensaje)."""
    _silenciar()
    _analizador_emociones(), _analizador_ironia(), _zero_shot()


# Emociones que los modelos de emociones básicas suelen confundir con otras
# ("le grité a mi madre y no puedo mirarla" suena a ira, pero es culpa/vergüenza).
# Se evalúan SIEMPRE con el zero-shot.
# (La soledad estaba aquí y ganaba casi siempre: el zero-shot la tiene como favorita.
#  Ahora solo compite si la familia es la tristeza.)
SIEMPRE = ["culpa", "verguenza", "ansiedad"]


def analizar_ml(texto):
    """
    Devuelve:
      {
        "familias":   {"tristeza": 0.81, ..., "otros": 0.05},   # pysentimiento
        "matices":    {"culpa": 0.45, ...},                      # zero-shot (compiten: suman 1)
        "emociones":  {"culpa": 0.40, "tristeza": 0.30, ...},    # combinación final
        "neutral":    0.05,                                      # prob. de "sin emoción"
        "ironia":     0.12,
      }
    o None si los modelos no están disponibles.
    """
    if not disponible():
        return None

    # 1) Familia (pysentimiento)
    pred = _analizador_emociones().predict(texto)
    familias = {FAMILIA_DE.get(k, "otros"): float(v) for k, v in pred.probas.items()}
    neutral = familias.get("otros", 0.0)

    # 2) Ironía (pysentimiento)
    pi = _analizador_ironia().predict(texto).probas
    ironia = float(next((v for k, v in pi.items() if "iron" in k and "not" not in k), 0.0))

    # 3) Candidatas para el zero-shot: los matices de las familias probables
    #    + las emociones que se suelen confundir. Menos candidatas = más rápido.
    probables = [f for f, p in familias.items() if f != "otros" and p >= 0.10]
    if not probables:
        probables = [max((f for f in familias if f != "otros"), key=familias.get)]
    candidatas = list(dict.fromkeys([m for f in probables for m in MATICES[f]] + SIEMPRE))

    # multi_label=False: las etiquetas COMPITEN entre sí (softmax). Con multi_label=True
    # el modelo dice "sí" a casi todo (~99 %) y no distingue.
    r = _zero_shot()(texto, candidate_labels=[ETIQUETAS[e] for e in candidatas],
                     hypothesis_template=PLANTILLA_HIPOTESIS, multi_label=False,
                     batch_size=len(candidatas))                  # todas a la vez: más rápido
    por_etiqueta = dict(zip(r["labels"], r["scores"]))
    matices = {e: float(por_etiqueta[ETIQUETAS[e]]) for e in candidatas}
    # Probado y descartado: CALIBRACIÓN CONTEXTUAL (dividir entre lo que el modelo
    # prefiere ante un texto neutro). Ante "Hoy es un día normal" casi nunca elige
    # "soledad" (2-3 %), así que al dividir la soledad se disparaba aún más.

    # 4) Combinación: la mitad viene del reparto jerárquico (la familia de
    #    pysentimiento repartida entre sus matices) y la otra mitad directamente
    #    del zero-shot, que así puede CORREGIR a la familia.
    emociones = {}
    for familia, miembros in MATICES.items():
        presentes = [m for m in miembros if m in matices]
        suma = sum(matices[m] for m in presentes) or 1.0
        for m in presentes:
            jerarquico = familias.get(familia, 0.0) * matices[m] / suma
            emociones[m] = 0.5 * jerarquico + 0.5 * matices[m] * (1 - neutral)

    return {"familias": familias, "matices": matices, "emociones": emociones,
            "neutral": neutral, "ironia": ironia}
