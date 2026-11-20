"""
Interfaz gráfica: un chat tipo WhatsApp con gráficos de emociones arriba.

    python servidor.py        -> abre http://127.0.0.1:5000 en el navegador

Cómo funciona:
  - Flask sirve la página (carpeta web/) y una pequeña API:
        POST /api/mensaje    {"texto": "..."}  -> respuesta + análisis + datos de los gráficos
        POST /api/reiniciar                    -> empieza una conversación nueva
  - El navegador (web/app.js) dibuja el chat y los gráficos con esos datos.
  - Todo es local: el servidor solo escucha en 127.0.0.1 (tu ordenador).
"""

import sys
import threading
import webbrowser
from collections import Counter

from flask import Flask, jsonify, request, send_from_directory

import analizador
import llm
import marcadores as M
import modelos
from analizador import aplicar_contexto, analizar
from lexico import ICONOS, NOMBRES
from respuesta import responder

app = Flask(__name__, static_folder="web", static_url_path="")
sesion = []                      # análisis de la conversación actual
cerrojo = threading.Lock()       # los modelos no se pueden usar desde dos peticiones a la vez


def _emocion(e, pct):
    return {"id": e, "nombre": NOMBRES[e], "icono": ICONOS[e], "pct": round(pct, 1)}


def _datos(a):
    """Lo que necesita el navegador para pintar la burbuja y los gráficos."""
    top = [_emocion(e, p) for e, p in a.porcentajes.items() if p >= 1][:5]

    # Emociones acumuladas en toda la conversación (cada mensaje cuenta lo mismo)
    total = Counter()
    for m in sesion:
        if m.dominante == "neutral":
            continue
        if m.emocion_por_contexto:
            total[m.dominante] += 100          # su emoción viene del contexto
        else:
            total.update({e: p for e, p in m.porcentajes.items() if p > 0})
    suma = sum(total.values()) or 1
    acumulado = [_emocion(e, p / suma * 100) for e, p in total.most_common(6)]

    return {
        "respuesta": a.respuesta,
        "respuesta_de": a.respuesta_de,
        "analisis": {
            "dominante": _emocion(a.dominante, a.porcentajes.get(a.dominante, 0)),
            "por_contexto": a.emocion_por_contexto,
            "emociones": top,
            "valencia": round(a.valencia, 2),
            "activacion": round(a.activacion, 2),
            "estado": a.estado,
            "intensidad": a.nivel_intensidad,
            "senales": [{"nombre": s.nombre, "evidencia": s.evidencias[0]} for s in a.senales],
            "distorsiones": [{"nombre": d.nombre, "evidencia": d.evidencias[0]} for d in a.distorsiones],
            "riesgo": a.riesgo,
            "recursos": M.RECURSOS_AYUDA if a.riesgo != "bajo" else [],
            "fuente": a.fuente,
        },
        "conversacion": {
            "tono": [{"valencia": round(m.valencia, 2), "icono": ICONOS[m.dominante],
                      "emocion": NOMBRES[m.dominante], "texto": m.texto[:60]} for m in sesion],
            "acumulado": acumulado,
        },
    }


@app.get("/")
def inicio():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/mensaje")
def mensaje():
    texto = (request.get_json(silent=True) or {}).get("texto", "").strip()
    if not texto:
        return jsonify({"error": "Mensaje vacío"}), 400
    with cerrojo:
        a = aplicar_contexto(analizar(texto), sesion[-1] if sesion else None)
        responder(a, turno=len(sesion), historial=sesion)
        sesion.append(a)
        return jsonify(_datos(a))


@app.post("/api/reiniciar")
def reiniciar():
    with cerrojo:
        sesion.clear()
    return jsonify({"ok": True})


@app.get("/api/estado")
def estado():
    return jsonify({"modelos": analizador.USAR_MODELOS, "llm": llm.usar(), "modelo_llm": llm.MODELO})


def main():
    # Windows puede usar una codificación antigua (cp1252) que no sabe escribir
    # emojis ni símbolos como ✔: forzamos UTF-8 para no caernos al imprimir.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    print("Preparando el sistema (la primera vez tarda un poco)...")
    if analizador.USAR_MODELOS:
        modelos.precargar()
    if llm.usar():
        print(f"Cargando el LLM local ({llm.MODELO})...")
        llm.precalentar()
    else:
        print("(Sin Ollama: las respuestas se harán con plantillas.)")
    url = "http://127.0.0.1:5000"
    print(f"\n✔ Listo. Abre {url} en el navegador (Ctrl+C para cerrar).\n", flush=True)
    if "--no-abrir" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=5000, threaded=True)


if __name__ == "__main__":
    main()
