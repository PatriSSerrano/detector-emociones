"""
Tests del sistema. Ejecutar con:   python -m unittest -v

Cada test comprueba UNA regla. Si al ampliar el léxico algo se rompe,
sabrás exactamente qué.
"""

import unittest

import analizador
from informe import generar_informe, informe_sesion

# Estos tests comprueban las REGLAS, que son deterministas. Los modelos tienen
# sus propios tests en test_modelos.py.
analizador.USAR_MODELOS = False
analizar = analizador.analizar
import llm  # noqa: E402
llm.USAR = False          # y las respuestas con plantillas (el LLM no es determinista)


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


class TestEstilo(unittest.TestCase):
    def test_formal_y_usted(self):
        e = analizar("Buenas tardes. Le escribo porque me siento preocupada por mi trabajo.").estilo
        self.assertEqual(e.registro, "formal")
        self.assertEqual(e.tratamiento, "usted")

    def test_coloquial(self):
        e = analizar("tia estoy mazo rayada en plan fatal xd").estilo
        self.assertEqual(e.registro, "coloquial")
        self.assertEqual(e.autodescripcion, "rayada")

    def test_tacos_marcan_coloquial(self):
        e = analizar("joder qué mierda de día").estilo
        self.assertTrue(e.vulgaridad)
        self.assertEqual(e.registro, "coloquial")

    def test_abreviaturas_se_entienden(self):
        a = analizar("seguro q suspendo el examen")
        self.assertIn("adivinacion", {d.id for d in a.distorsiones})


class TestRespuesta(unittest.TestCase):
    # Los tacos SÍ se pueden copiar (es su registro). Lo que nunca se copia son los
    # insultos y el pensamiento absolutista (eso es negatividad, no registro).
    PROHIBIDAS = {"gilipollas", "fracasado", "desastre", "inutil", "imbecil",
                  "siempre", "nunca", "nadie", "nada", "todo", "mazo"}

    def respuesta(self, texto):
        from respuesta import generar_respuesta
        from utils import normalizar
        r = generar_respuesta(analizar(texto))
        return r, set(normalizar(r).replace(",", " ").replace(".", " ").split())

    def test_no_copia_negatividad(self):
        for texto in ["joder estoy de puta pena, mi jefe es un gilipollas y todo me sale mal, soy un desastre",
                      "Siempre me pasa lo mismo, soy un fracasado, nadie me quiere",
                      "tia estoy mazo rayada, nada me sale bien"]:
            _, palabras = self.respuesta(texto)
            self.assertEqual(palabras & self.PROHIBIDAS, set(), texto)

    def test_copia_tacos_si_la_persona_los_usa(self):
        r, _ = self.respuesta("estoy hasta la polla de mi jefe")
        self.assertIn("hasta la polla de tu jefe", r)

    def test_expresiones_idiomaticas(self):
        casos = {"estoy hasta el moño": "ira", "estoy más sola que la una": "soledad",
                 "me cago de miedo": "miedo", "la he cagado con mi novia": "culpa",
                 "me lo he pasado bomba": "alegria", "me he quedado a cuadros": "sorpresa",
                 "voy con el agua al cuello": "ansiedad", "qué bajón": "tristeza",
                 "estoy colada por Marta": "amor", "qué corte": "verguenza",
                 "estoy tristísima": "tristeza"}
        for texto, emocion in casos.items():
            self.assertEqual(analizar(texto).dominante, emocion, texto)

    def test_expresion_no_es_tema(self):
        r, _ = self.respuesta("estoy hasta la polla")
        self.assertNotIn("lo de la polla", r)

    def test_vocativo_y_cierre(self):
        r, _ = self.respuesta("tía me han dado el trabajo!! estoy de puta madre xoxo")
        self.assertIn("tía", r)
        self.assertTrue(r.endswith("xoxo"))

    def test_mi_tia_no_es_vocativo(self):
        self.assertIsNone(analizar("he ido a ver a mi tía y estoy contenta").estilo.vocativo)

    def test_refleja_su_expresion(self):
        r, _ = self.respuesta("tia estoy mazo rayada con lo del examen")
        self.assertIn("rayada con lo del examen", r)

    def test_usted_en_formal(self):
        r, _ = self.respuesta("Buenas tardes. Le escribo porque me siento preocupada por mi trabajo.")
        self.assertIn("su trabajo", r)
        self.assertIn("me cuenta", r)        # "cuenta", no "cuentas"
        self.assertNotIn(" te ", f" {r} ")

    def test_coloquial_responde_cercano(self):
        r, _ = self.respuesta("uf tio estoy hecho polvo con el curro")
        self.assertTrue(r.startswith("Uf"))
        self.assertIn("hecho polvo", r)

    def test_objetiva_con_adivinacion(self):
        r, _ = self.respuesta("Mañana tengo el examen y seguro que suspendo, no voy a poder")
        self.assertIn("todavía no ha pasado", r)

    def test_el_sistema_no_usa_emojis(self):
        r, _ = self.respuesta("Estoy muy feliz 🎉😍")
        self.assertFalse(any(ord(c) > 0x2100 and c not in "¿¡" for c in r), r)

    def test_no_usa_emojis_negativos(self):
        r, _ = self.respuesta("estoy fatal 😭😭")
        self.assertNotIn("😭", r)

    def test_riesgo_prioriza_seguridad(self):
        r, _ = self.respuesta("jajaja tio a veces pienso q quiero morirme")
        self.assertIn("024", r)
        self.assertNotIn("Jaja", r)


class TestConversacion(unittest.TestCase):
    """Un psicólogo recuerda lo que se ha dicho: las respuestas se leen en contexto."""

    def conversar(self, mensajes):
        from analizador import aplicar_contexto
        from respuesta import generar_respuesta
        sesion, respuestas = [], []
        for m in mensajes:
            a = aplicar_contexto(analizar(m), sesion[-1] if sesion else None)
            respuestas.append(generar_respuesta(a, turno=len(sesion), historial=sesion))
            sesion.append(a)
        return sesion, respuestas

    def test_recoge_la_respuesta_a_su_pregunta(self):
        sesion, r = self.conversar(["estoy hasta el coño", "todo bro, no hay quesitos en clase"])
        self.assertEqual(sesion[1].dominante, "ira")             # la emoción sigue ahí
        self.assertTrue(sesion[1].emocion_por_contexto)
        self.assertIn("lo que más te ha molestado es que no hay quesitos en clase", r[1])
        self.assertIn("bro", r[1])

    def test_no_repite_preguntas(self):
        sesion, _ = self.conversar(["estoy hasta el coño", "no hay quesitos", "pues eso", "ya"])
        preguntas = [a.pregunta_hecha for a in sesion]
        self.assertEqual(len(preguntas), len(set(preguntas)))

    def test_pasa_a_segunda_persona(self):
        _, r = self.conversar(["tía me siento fatal", "pues que mi novio me ha dejado"])
        self.assertIn("tu novio te ha dejado", r[1])

    def test_desde_cuando(self):
        _, r = self.conversar(["tía me siento fatal", "desde el lunes"])
        self.assertIn("llevas así desde el lunes", r[1])

    def test_no_lo_se(self):
        _, r = self.conversar(["estoy muy triste", "no lo sé"])
        self.assertIn("No pasa nada si no lo sabes", r[1])

    def test_deseo_no_se_duplica(self):
        _, r = self.conversar(["estoy hasta el coño", "no hay quesitos", "yo solo quiero un buen bicep"])
        self.assertIn("solo quieres un buen bicep", r[2])
        self.assertNotIn("gustaría es que", r[2])

    def test_mantiene_usted(self):
        sesion, r = self.conversar(["Buenas tardes. Le escribo porque estoy preocupada por mi hijo.",
                                    "Que no come bien."])
        self.assertEqual(sesion[1].estilo.tratamiento, "usted")
        self.assertIn("le preocupa", r[1])


class TestTemas(unittest.TestCase):
    def test_adjetivo_delante_del_sustantivo(self):
        temas = [t.sust for t in analizar("necesito un buen bicep").estilo.temas]
        self.assertIn("buen bicep", temas)

    def test_cierre_en_mitad_del_mensaje(self):
        self.assertEqual(analizar("no se xoxo, yo solo quiero dormir").estilo.cierre, "xoxo")

    def test_vocativo_en_mitad(self):
        self.assertEqual(analizar("todo bro, no hay quesitos").estilo.vocativo, "bro")


class TestSesion(unittest.TestCase):
    def test_tendencia_mejora(self):
        sesion = [analizar("Estoy muy triste"), analizar("Me siento fatal"),
                  analizar("Hoy estoy mejor"), analizar("Estoy feliz y tranquila")]
        self.assertIn("Mejora", informe_sesion(sesion))


if __name__ == "__main__":
    unittest.main()
