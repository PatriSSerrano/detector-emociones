"""
Emotion Analysis System — programa de terminal.

Modos:
    python main.py                         consulta interactiva (varios mensajes)
    python main.py --texto "Me siento..."  analiza un solo texto
    python main.py --sesion archivo.txt    analiza cada línea como un mensaje de una sesión
    python main.py --demo                  ejemplos
    Añade --traza para ver cómo se ha calculado cada punto.
"""

import argparse
import sys

import analizador
import modelos
from analizador import analizar, aplicar_contexto
from informe import generar_informe, informe_sesion
import llm
from lexico import NOMBRES
from conversacion import procesar

EJEMPLOS = [
    "¡Hoy me han dado la beca! Estoy muy feliz y con muchas ganas de empezar 🎉",
    "Estoy bien, pero la verdad es que ya no puedo más. Siempre me pasa lo mismo, soy un fracasado.",
    "Mañana tengo el examen y ¿y si suspendo? Seguro que sale mal, llevo dos noches sin dormir.",
    "Me siento sola, nadie me entiende. Echo de menos a mi madre.",
    "Estoy HARTO de que mi jefe me grite delante de todos, es injusto!!",
    "Discutí con mi hermana y fue culpa mía, debería haber estado callada. No paro de pensar en ello.",
    "Hoy he paseado por el parque, estoy tranquila y en paz.",
    "Mañana tengo una reunión a las diez.",
]


def _descartar_teclas():
    """Si se pulsan teclas mientras cargan los modelos, se descartan para que no
    lleguen como un mensaje vacío."""
    try:
        import msvcrt          # solo Windows
        while msvcrt.kbhit():
            msvcrt.getwch()
    except ImportError:
        pass


def consulta_interactiva(traza):
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            EMOTION ANALYSIS SYSTEM — consulta            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    if llm.usar() and llm.arrancar_servidor_gpu():
        print("Usando la gráfica integrada (Vulkan) para el LLM.")
    if analizador.USAR_MODELOS:
        print("Cargando los modelos de lenguaje (la primera vez se descargan, tarda un poco)...")
        modelos.precargar(zero_shot=not llm.usar())
    else:
        print("(Modo solo reglas: instala pysentimiento para el modo híbrido.)")
    if llm.usar():
        print(f"Cargando el LLM local ({llm.MODELO}) para redactar las respuestas...")
        llm.precalentar()
    else:
        print("(Respuestas con plantillas. Para que las redacte un LLM local: instala Ollama y "
              f"ejecuta 'ollama pull {llm.MODELO}'.)")
    _descartar_teclas()
    print("✔ Listo.\n")
    print("Cuéntame cómo estás.")
    print("Comandos: /informe (análisis del último mensaje), /resumen (evolución), /salir")
    sesion = []
    while True:
        try:
            texto = input("\n> ").strip().lstrip("﻿")
        except (EOFError, KeyboardInterrupt):
            texto = "/salir"
        if not texto:
            continue
        if texto.lower() in {"/salir", "salir", "exit"}:
            if len(sesion) >= 2:
                print(informe_sesion(sesion))
            print("\nGracias por compartir. Cuídate.")
            break
        if texto.lower() == "/resumen":
            print(informe_sesion(sesion))
            continue
        if texto.lower() == "/informe":
            print(generar_informe(sesion[-1], mostrar_traza=traza) if sesion else "Aún no hay mensajes.")
            continue
        # Respuesta en streaming (se escribe según la genera el LLM) + una línea de análisis
        print("\n💬 ", end="", flush=True)
        escrito = []
        a = procesar(texto, sesion, al_escribir=lambda t: (escrito.append(t), print(t, end="", flush=True)))
        if "".join(escrito).strip() != a.respuesta:      # plantillas, seguridad o corregida
            print(("\n   (corregida) " if escrito else "") + a.respuesta, end="")
        print()
        sesion.append(a)
        resumen = f"{NOMBRES[a.dominante]}" + (" (por el contexto)" if a.emocion_por_contexto else "")
        if a.secundarias:
            resumen += " + " + ", ".join(NOMBRES[e] for e in a.secundarias)
        extras = len(a.senales) + len(a.distorsiones)
        print(f"   [{resumen} · {a.estado} · {extras} señales · estilo {a.estilo.registro}"
              f" · respuesta: {a.respuesta_de}]")


def main():
    for flujo in (sys.stdout, sys.stderr):        # emojis y tildes en Windows
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

    p = argparse.ArgumentParser(description="Emotion Analysis System")
    p.add_argument("--texto", help="analiza un único texto")
    p.add_argument("--sesion", help="archivo .txt con un mensaje por línea")
    p.add_argument("--demo", action="store_true", help="analiza frases de ejemplo")
    p.add_argument("--traza", action="store_true", help="muestra el cálculo paso a paso")
    p.add_argument("--solo-reglas", action="store_true", help="no usa los modelos de lenguaje")
    p.add_argument("--sin-llm", action="store_true", help="respuestas con plantillas, sin Ollama")
    args = p.parse_args()
    if args.solo_reglas:
        analizador.USAR_MODELOS = False
        llm.USAR = False
    if args.sin_llm:
        llm.USAR = False

    if args.texto:
        print(generar_informe(procesar(args.texto), mostrar_traza=args.traza))
    elif args.sesion:
        with open(args.sesion, encoding="utf-8") as f:
            mensajes = [linea.strip() for linea in f if linea.strip() and not linea.startswith("#")]
        resultados = []
        for m in mensajes:
            resultados.append(procesar(m, resultados))
        if args.traza:
            for a in resultados:
                print(generar_informe(a, mostrar_traza=True))
        print(informe_sesion(resultados))
    elif args.demo:
        for texto in EJEMPLOS:
            print(generar_informe(procesar(texto), mostrar_traza=args.traza))
    else:
        consulta_interactiva(args.traza)


if __name__ == "__main__":
    main()
