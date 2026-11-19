"""
Tests del sistema. Ejecutar con:   python -m unittest -v

Cada test comprueba UNA regla. Si al ampliar el léxico algo se rompe,
sabrás exactamente qué.
"""

import unittest

from analizador import analizar
from informe import generar_informe, informe_sesion


class TestEmociones(unittest.TestCase):
    def test_alegria(self):
        self.assertEqual(analizar("Estoy muy feliz hoy").dominante, "alegria")

    def test_neutral(self):
        a = analizar("Mañana tengo una reunión a las diez.")
        self.assertEqual(a.dominante, "neutral")
        self.assertEqual(a.nivel_intensidad, "nula")

    def test_negacion_invierte(self):
        self.assertEqual(analizar("No estoy contento con el resultado").dominante, "tristeza")

    def test_negacion_anula(self):
        self.assertEqual(analizar("No tengo miedo").dominante, "neutral")

    def test_intensificador_suma(self):
        normal = analizar("Estoy feliz").puntos["alegria"]
        intenso = analizar("Estoy muy feliz").puntos["alegria"]
        self.assertGreater(intenso, normal)

    def test_pero_pesa_mas_lo_de_despues(self):
        a = analizar("Estoy contenta, pero muy triste")
        self.assertEqual(a.dominante, "tristeza")

    def test_sin_embargo_no_es_negacion(self):
        a = analizar("Fue difícil, sin embargo estoy feliz")
        self.assertEqual(a.dominante, "alegria")

    def test_soledad_distinta_de_tristeza(self):
        self.assertEqual(analizar("Me siento sola, nadie me entiende").dominante, "soledad")

    def test_mal_en_sale_mal_no_es_tristeza(self):
        self.assertEqual(analizar("El pastel me ha salido mal").puntos["tristeza"], 0)

    def test_pensamiento_genera_ansiedad(self):
        self.assertEqual(analizar("¿Y si suspendo? Seguro que sale mal").dominante, "ansiedad")


class TestEstadoAfectivo(unittest.TestCase):
    def test_ira_es_activacion_alta(self):
        a = analizar("Estoy furioso, me da rabia")
        self.assertLess(a.valencia, 0)
        self.assertGreater(a.activacion, 0)

    def test_tristeza_es_activacion_baja(self):
        a = analizar("Estoy muy triste y deprimido")
        self.assertLess(a.valencia, 0)
        self.assertLess(a.activacion, 0)

    def test_serenidad_es_agradable_y_calmada(self):
        a = analizar("Estoy tranquila y en paz")
        self.assertGreater(a.valencia, 0)
        self.assertLess(a.activacion, 0)


class TestMarcadores(unittest.TestCase):
    def ids(self, texto):
        a = analizar(texto)
        return {s.id for s in a.senales}, {d.id for d in a.distorsiones}

    def test_etiquetado(self):
        self.assertIn("etiquetado", self.ids("Soy un fracasado")[1])

    def test_generalizacion(self):
        self.assertIn("generalizacion", self.ids("Todo me sale mal")[1])

    def test_catastrofismo(self):
        self.assertIn("catastrofismo", self.ids("Esto es lo peor que me podía pasar")[1])

    def test_lectura_mente(self):
        self.assertIn("lectura_mente", self.ids("Seguro que piensa que soy tonta")[1])

    def test_minimizacion_solo_si_hay_malestar(self):
        self.assertIn("minimizacion", self.ids("Estoy bien, pero estoy muy triste y agobiado")[0])
        self.assertNotIn("minimizacion", self.ids("Estoy bien, gracias")[0])

    def test_rumiacion(self):
        self.assertIn("rumiacion", self.ids("Si hubiera estudiado más… no paro de pensar en ello")[0])

    def test_sin_falsos_positivos_en_texto_neutro(self):
        senales, distorsiones = self.ids("Mañana tengo una reunión a las diez.")
        self.assertEqual(senales, set())
        self.assertEqual(distorsiones, set())


class TestRiesgo(unittest.TestCase):
    def test_riesgo_alto(self):
        a = analizar("A veces pienso que quiero morirme")
        self.assertEqual(a.riesgo, "alto")
        self.assertIn("024", generar_informe(a))

    def test_riesgo_moderado_por_desesperanza(self):
        self.assertEqual(analizar("Ya no puedo más, nada va a cambiar").riesgo, "moderado")

    def test_cortarse_el_pelo_no_es_riesgo(self):
        self.assertEqual(analizar("Mañana voy a cortarme el pelo").riesgo, "bajo")


class TestSesion(unittest.TestCase):
    def test_tendencia_mejora(self):
        sesion = [analizar("Estoy muy triste"), analizar("Me siento fatal"),
                  analizar("Hoy estoy mejor"), analizar("Estoy feliz y tranquila")]
        self.assertIn("Mejora", informe_sesion(sesion))


if __name__ == "__main__":
    unittest.main()
