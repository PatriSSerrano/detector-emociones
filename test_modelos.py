"""
Tests del sistema HÍBRIDO (reglas + modelos). Ejecutar con:
    python -m unittest test_modelos -v

Usan frases que NO están en ninguna lista del léxico: si las entiende, es
gracias a los modelos. Se saltan si pysentimiento/transformers no están instalados.
"""

import unittest

import llm
import modelos
from analizador import POSITIVAS, analizar

llm.USAR = False      # aquí se prueban los modelos (pysentimiento + zero-shot), sin el LLM


@unittest.skipUnless(modelos.disponible(), "pysentimiento/transformers no instalados")
class TestHibrido(unittest.TestCase):
    def sin_reglas(self, texto):
        """Comprueba que las reglas solas NO detectan nada (la frase no está en las listas)."""
        self.assertEqual(analizar(texto, usar_modelos=False).dominante, "neutral", texto)

    def test_tristeza_sin_palabras_de_la_lista(self):
        texto = "Desde que se fue mi abuela la casa se me hace enorme y silenciosa"
        self.sin_reglas(texto)
        a = analizar(texto, usar_modelos=True)
        self.assertIn(a.dominante, {"tristeza", "soledad"})

    def test_ira_sin_palabras_de_la_lista(self):
        texto = "Me han vuelto a cobrar dos veces la factura y nadie del servicio técnico me coge el teléfono"
        a = analizar(texto, usar_modelos=True)
        self.assertEqual(a.dominante, "ira")

    def test_alegria_sin_palabras_de_la_lista(self):
        texto = "Por fin he aprobado el carnet de conducir a la primera"
        self.sin_reglas(texto)
        self.assertIn(analizar(texto, usar_modelos=True).dominante, {"alegria", "esperanza"})

    def test_neutral_sigue_siendo_neutral(self):
        self.assertEqual(analizar("El autobús sale a las ocho y cuarto", usar_modelos=True).dominante,
                         "neutral")

    def test_ironia(self):
        a = analizar("Genial, otra vez lunes y lloviendo, qué maravilla de vida", usar_modelos=True)
        self.assertNotIn(a.dominante, POSITIVAS)

    def test_el_riesgo_lo_siguen_decidiendo_las_reglas(self):
        a = analizar("a veces pienso que quiero morirme", usar_modelos=True)
        self.assertEqual(a.riesgo, "alto")

    def test_el_informe_muestra_la_opinion_del_modelo(self):
        from informe import generar_informe
        informe = generar_informe(analizar("Estoy muy preocupada por mi madre", usar_modelos=True))
        self.assertIn("pysentimiento", informe)
        self.assertIn("zero-shot", informe)


if __name__ == "__main__":
    unittest.main()
