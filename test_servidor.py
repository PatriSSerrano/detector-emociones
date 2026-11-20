"""
Tests de la interfaz gráfica (la API que usa el chat). Ejecutar con:
    python -m unittest test_servidor -v

Usa el cliente de pruebas de Flask: hace peticiones sin abrir el navegador.
Solo reglas y plantillas, para que sea rápido y siempre dé lo mismo.
"""

import json
import unittest

import analizador
import llm
import servidor

analizador.USAR_MODELOS = False
llm.USAR = False


class TestServidor(unittest.TestCase):
    def setUp(self):
        self.cliente = servidor.app.test_client()
        self.cliente.post("/api/reiniciar")

    def eventos(self, texto, **extra):
        """La respuesta llega en streaming: un JSON por línea."""
        r = self.cliente.post("/api/mensaje", json={"texto": texto, **extra})
        self.assertEqual(r.status_code, 200)
        return [json.loads(l) for l in r.get_data(as_text=True).splitlines() if l.strip()]

    def mandar(self, texto):
        evs = self.eventos(texto)
        self.assertEqual(evs[-1]["tipo"], "fin")
        return evs[-1]

    def test_streaming_por_eventos(self):
        tipos = [e["tipo"] for e in self.eventos("estoy muy contenta")]
        self.assertIn("analisis", tipos)
        self.assertEqual(tipos[-1], "fin")

    def test_pagina(self):
        r = self.cliente.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Emotion Analysis", r.data)

    def test_mensaje_devuelve_respuesta_y_graficos(self):
        d = self.mandar("estoy hasta el coño")
        self.assertTrue(d["respuesta"])
        self.assertEqual(d["analisis"]["dominante"]["id"], "ira")
        self.assertEqual(len(d["conversacion"]["tono"]), 1)
        self.assertEqual(d["conversacion"]["acumulado"][0]["id"], "ira")

    def test_la_conversacion_se_acumula(self):
        self.mandar("estoy hasta el coño")
        d = self.mandar("todo bro, no hay quesitos en clase")
        self.assertTrue(d["analisis"]["por_contexto"])
        self.assertEqual(len(d["conversacion"]["tono"]), 2)

    def test_reiniciar(self):
        self.mandar("estoy triste")
        self.cliente.post("/api/reiniciar")
        d = self.mandar("estoy feliz")
        self.assertEqual(len(d["conversacion"]["tono"]), 1)

    def test_riesgo(self):
        d = self.mandar("a veces pienso que quiero morirme")
        self.assertEqual(d["analisis"]["riesgo"], "alto")
        self.assertIn("024", d["respuesta"])
        self.assertTrue(d["analisis"]["recursos"])

    def test_tarta_sin_ruido(self):
        self.mandar("estoy hasta el coño")
        d = self.mandar("estoy muy feliz con mis amigos")
        total = sum(e["pct"] for e in d["conversacion"]["acumulado"])
        self.assertAlmostEqual(total, 100, delta=1)
        self.assertTrue(all(e["pct"] >= 5 for e in d["conversacion"]["acumulado"]))

    def test_nombre_del_chat(self):
        self.assertEqual(self.eventos("hola", nombre="  Luna \n ")[-1]["tipo"], "fin")

    def test_mensaje_vacio(self):
        r = self.cliente.post("/api/mensaje", json={"texto": "   "})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
