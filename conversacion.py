"""
Un turno de la conversación, de principio a fin. Lo usan la interfaz web
(servidor.py) y la terminal (main.py).

  1. analizar()        -> reglas + modelos (rápido: menos de 1 s)
  2. heredar_estilo()  -> una respuesta corta mantiene el registro de antes
  3. Respuesta:
       - riesgo alto  -> mensaje de seguridad fijo (las reglas mandan)
       - con LLM      -> UNA llamada que devuelve el juicio de perspectiva (qué siente
                         quien escribe) y la respuesta, en streaming
       - sin LLM      -> plantillas
  4. aplicar_juez() + aplicar_contexto() -> análisis final

Callbacks (opcionales), para ir mostrando las cosas según están listas:
  al_analizar(a): el análisis final ya está (antes de que empiece la respuesta)
  al_escribir(trozo): un trozo nuevo de la respuesta
"""

import llm
from analizador import aplicar_contexto, aplicar_juez, analizar, heredar_estilo
from respuesta import responder


def procesar(texto, sesion=(), nombre=None, al_analizar=None, al_escribir=None, usar_llm=None):
    anterior = sesion[-1] if sesion else None
    a = analizar(texto)
    heredar_estilo(a, anterior)
    usar = llm.usar() if usar_llm is None else usar_llm

    def final(juez=None):
        if juez is not None:
            aplicar_juez(a, juez)
        aplicar_contexto(a, anterior)
        if al_analizar:
            al_analizar(a)

    if a.riesgo == "alto" or not usar:
        final()
        respuesta(a, sesion, nombre, usar)
        return a

    analizado = []
    resultado = llm.conversar(a, sesion, nombre,
                              al_analizar=lambda juez: (final(juez), analizado.append(True)),
                              al_escribir=al_escribir)
    if resultado is None:                      # el LLM ha fallado: análisis sin él
        if not analizado:
            final()
        respuesta(a, sesion, nombre, usar=False)
        return a
    if not analizado:
        final(resultado)
    if resultado["respuesta"]:
        a.respuesta, a.respuesta_de = resultado["respuesta"], f"LLM ({llm.MODELO})"
    else:
        # No ha pasado el control de calidad: se pide de nuevo (con corrección) o plantillas
        a.traza.append(f"respuesta descartada: {resultado['problema']}")
        respuesta(a, sesion, nombre, usar)
    return a


def respuesta(a, sesion, nombre, usar):
    """Respuesta sin la llamada combinada: seguridad, LLM solo-respuesta o plantillas."""
    responder(a, turno=len(sesion), historial=sesion, nombre=nombre,
              usar_llm=usar and a.riesgo != "alto")
