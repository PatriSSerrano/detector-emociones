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

from analizador import analizar
from informe import generar_informe, informe_sesion
from lexico import NOMBRES
from respuesta import generar_respuesta

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


def consulta_interactiva(traza):
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            EMOTION ANALYSIS SYSTEM — consulta            ║")
    print("╚══════════════════════════════════════════════════════════╝")
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
        a = analizar(texto)
        sesion.append(a)
        # Respuesta conversacional + una línea de análisis
        print(f"\n💬 {generar_respuesta(a, turno=len(sesion) - 1)}")
        resumen = f"{NOMBRES[a.dominante]}"
        if a.secundarias:
            resumen += " + " + ", ".join(NOMBRES[e] for e in a.secundarias)
        extras = len(a.senales) + len(a.distorsiones)
        print(f"   [{resumen} · {a.estado} · {extras} señales · estilo {a.estilo.registro}]")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # emojis y tildes en Windows
    except AttributeError:
        pass

    p = argparse.ArgumentParser(description="Emotion Analysis System")
    p.add_argument("--texto", help="analiza un único texto")
    p.add_argument("--sesion", help="archivo .txt con un mensaje por línea")
    p.add_argument("--demo", action="store_true", help="analiza frases de ejemplo")
    p.add_argument("--traza", action="store_true", help="muestra el cálculo paso a paso")
    args = p.parse_args()

    if args.texto:
        print(generar_informe(analizar(args.texto), mostrar_traza=args.traza))
    elif args.sesion:
        with open(args.sesion, encoding="utf-8") as f:
            mensajes = [linea.strip() for linea in f if linea.strip() and not linea.startswith("#")]
        resultados = [analizar(m) for m in mensajes]
        if args.traza:
            for a in resultados:
                print(generar_informe(a, mostrar_traza=True))
        print(informe_sesion(resultados))
    elif args.demo:
        for texto in EJEMPLOS:
            print(generar_informe(analizar(texto), mostrar_traza=args.traza))
    else:
        consulta_interactiva(args.traza)


if __name__ == "__main__":
    main()
