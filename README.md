# Emotion Analysis System

Sistema en Python que **simula cómo un psicólogo lee las emociones** de una persona a partir de
cómo se expresa por escrito. No solo detecta *qué* emociones nombra: también se fija en **cómo habla**
(estilo del lenguaje, patrones de pensamiento, señales de riesgo), responde con **empatía** y propone
**preguntas** para seguir explorando, como en una consulta.

Usa [TextBlob](https://textblob.readthedocs.io/) para segmentar el texto (y para la polaridad en inglés),
junto con un léxico emocional y reglas basadas en investigación psicológica.

> ⚠ Proyecto **educativo**. Es una simulación basada en reglas: no diagnostica y no sustituye a
> un profesional de la salud mental.

## Ejemplo

```
$ python main.py --texto "Estoy bien, pero ya no puedo más. Siempre me pasa lo mismo, soy un fracasado."

1. EMOCIONES DETECTADAS
   Principal: 😢 Tristeza   ·   Secundarias: 😳 Vergüenza
2. ESTADO AFECTIVO (modelo circumplejo de Russell)
   desagradable ─────●─────────────── agradable
        apagado ─────────●─────────── activado
   → Desagradable y con poca energía (desánimo, abatimiento)
3. CÓMO SE EXPRESA
   • Desesperanza: «ya no puedo más»
   • Posible minimización: «Estoy bien»
4. PATRONES DE PENSAMIENTO
   • Sobregeneralización: «Siempre me pasa»
     ↳ Para reformular: ¿De verdad es *siempre*, *nunca* o *nadie*? ¿Recuerdas alguna excepción?
   • Etiquetarse: «soy un fracasado»
5. RESPUESTA (objetiva y adaptada a su forma de expresarse)
   Estilo detectado: neutro · tú · mensaje media
   💬 Entiendo. Por lo que cuentas, estás pasando un momento triste. Dices que estás bien,
      aunque no parece que del todo. ¿Desde cuándo te sientes así?
```

## Instalación y uso

```bash
pip install -r requirements.txt
python -m textblob.download_corpora lite

python main.py                                   # conversación (/informe, /resumen, /salir)
python main.py --texto "Me siento sola..."       # un texto
python main.py --sesion ejemplos/sesion_ejemplo.txt   # evolución de una sesión
python main.py --demo                            # ejemplos
python main.py --demo --traza                    # muestra cómo se calcula cada punto
python -m unittest -v                            # tests
```

## Qué habilidades del psicólogo simula

| Habilidad | Base teórica | Implementación |
|---|---|---|
| Distinguir matices emocionales | Granularidad emocional (L. Feldman Barrett) | 13 emociones: alegría, serenidad, amor, esperanza, sorpresa, tristeza, soledad, ira, miedo, ansiedad, culpa, vergüenza y asco |
| Notar si alguien está agitado o apagado | Modelo circumplejo (Russell, 1980) | Cada emoción tiene coordenadas de **valencia × activación** y se calcula el estado global |
| Fijarse en *cómo* se habla | Pennebaker (LIWC); Al-Mosaiwi y Johnstone (2018) | Autofoco ("yo/me/mi"), absolutismo ("siempre/nunca"), rumiación, preocupación, síntomas físicos, vaguedad |
| Leer entre líneas | Práctica clínica | Lo que va tras el **"pero"** pesa más; detección de **minimización** ("estoy bien, pero…") y **ambivalencia** |
| Detectar pensamientos que hacen daño | Terapia cognitiva (Beck, Burns) | 9 **distorsiones cognitivas**, cada una con una pregunta socrática para reformularla |
| Entender que los pensamientos generan emociones | Modelo cognitivo (A. Beck) | "¿Y si suspendo?" suma **ansiedad** aunque no aparezca ninguna palabra emocional |
| Hablar "en su idioma" | Sincronía de estilo lingüístico (Ireland y Pennebaker, 2010) | Detecta registro (formal → coloquial), tú/usted, emojis, interjecciones y autodescripciones, y **responde con el mismo estilo** |
| Responder con objetividad | Terapia cognitiva: hechos frente a interpretaciones | La respuesta se basa en lo dicho y separa hechos de suposiciones, sin falsos ánimos |
| Hacer buenas preguntas | Diálogo socrático | Preguntas adaptadas a la emoción, las señales y las distorsiones |
| Seguir la evolución | Seguimiento de la sesión | **Modo sesión**: trayectoria de la valencia, tendencia y patrones repetidos |
| Detectar riesgo y derivar | Cribado de riesgo | **Alerta** ante ideación suicida o autolesión (también en formas indirectas) con recursos: **024** y **112** |

## La respuesta: misma cercanía, sin copiar la negatividad

El sistema adapta **la forma** de responder a cómo escribe la persona, pero **no copia su malestar**:

| Mensaje | Respuesta |
|---|---|
| *tia estoy mazo rayada con lo del examen, en plan q no me entra nada y seguro q suspendo 😭* | Uf, vale. Por lo que dices, estás rayada con lo del examen. Eso todavía no ha pasado, así que no sabemos cómo va a salir. Oye, ¿desde cuándo te sientes así? 🫂 |
| *joder estoy de puta pena, mi jefe es un gilipollas y todo me sale mal, soy un desastre* | Uf, vale. Por lo que dices, estás de bajón con lo de tu jefe. Que algo no haya salido bien no te define como persona. Oye, ¿desde cuándo te sientes así? |
| *Buenas tardes. Le escribo porque últimamente me siento muy cansada y preocupada por mi trabajo.* | Gracias por contármelo. Por lo que me cuenta, está cansada y preocupada por su trabajo. ¿Desde cuándo se siente así? |
| *jajaja hoy he quedado con mis amigos y estoy a tope* | Jaja, ¡qué bien! Por lo que dices, estás a tope con tus amigos. … |

**Qué refleja**: el registro, tú o usted, sus interjecciones ("uf", "jaja") si encajan con el tono, sus
emojis (solo los de apoyo, nunca 😭), su propia forma de describirse ("rayada", "hecho polvo",
"más tranqui") con su misma preposición ("preocupada *por* su trabajo"), y una longitud parecida a
la de su mensaje.

**Qué NO copia**: tacos, insultos hacia sí misma ("soy un desastre"), palabras absolutistas
("siempre", "nada", "nadie"), intensificadores del malestar ("mazo", "muy") ni emojis negativos.

**Objetividad**: se basa en lo que ha dicho ("Por lo que cuentas…"), separa hechos de
interpretaciones ("todavía no ha pasado, así que no sabemos cómo va a salir") y evita los falsos
ánimos como "seguro que todo irá bien".

Ante un **riesgo**, la seguridad va por delante del estilo: el mensaje es claro y directo y da el 024.

## Cómo funciona por dentro

1. **Segmentación (TextBlob)**: oraciones → palabras. Se normaliza (minúsculas, sin tildes).
2. **Puntuación emocional** ([`lexico.py`](lexico.py)): cada palabra o expresión tiene una emoción y
   un peso de 1 a 3. Sobre eso se aplican reglas:
   - **Negación** (3 palabras hacia atrás): *"no estoy feliz"* → tristeza, *"no tengo miedo"* → se anula.
   - **Intensificadores**: `muy` ×1.5, `extremadamente` ×2, `poco` ×0.5…
   - **MAYÚSCULAS** ×1.3, **exclamaciones** +20 % cada una y **emojis**.
   - **Contraste**: antes del "pero" ×0.7 y después ×1.3.
   - **Pensamientos → emociones**: preocupación y catastrofismo suman ansiedad, el etiquetado suma
     vergüenza, etc.
3. **Resultado emocional**: porcentajes, emoción principal y secundarias, e intensidad
   (puntos por palabra).
4. **Estado afectivo**: la media ponderada de las coordenadas da un punto en el plano
   valencia × activación y su cuadrante.
5. **Marcadores y distorsiones** ([`marcadores.py`](marcadores.py)): expresiones regulares y conteos
   que citan las palabras exactas de la persona como evidencia.
6. **Informe** ([`informe.py`](informe.py)): reflejo empático, preguntas, alerta de riesgo y resumen
   de la sesión.

Con `--traza` se ve cada paso del cálculo, por ejemplo:

```
· 'sin dormir' -> ansiedad +2.00
· pensamiento 'preocupacion' (y si) -> ansiedad +2
· pensamiento 'adivinacion' (Seguro que sale mal) -> ansiedad +2
```

## Limitaciones

- Funciona con **reglas y diccionarios**: no entiende la ironía (*"genial, otra vez lunes"*) ni el
  contexto amplio.
- Está pensado para **español**. En inglés reconoce emociones básicas y usa la polaridad de TextBlob,
  pero no los marcadores avanzados.
- Las expresiones de riesgo se detectan por patrones. Se prefiere un falso positivo antes que dejar
  pasar un caso real.
- Siguiente paso posible: un modelo entrenado (por ejemplo, un transformer de Hugging Face para
  emociones en español) combinado con estas reglas, que son explicables.

## Estructura

```
main.py              programa de terminal (consulta, texto, sesión, demo)
analizador.py        motor de análisis -> objeto Analisis
informe.py           informe tipo psicólogo y resumen de sesión
respuesta.py         respuesta objetiva adaptada al estilo de la persona
estilo.py            detección del estilo (registro, tú/usted, expresiones, temas)
lexico.py            emociones, pesos, modelo circumplejo, negaciones, intensificadores
marcadores.py        marcadores lingüísticos, distorsiones cognitivas y riesgo
utils.py             normalización, abreviaturas ("q" -> "que") y búsqueda de expresiones
test_analizador.py   36 tests (python -m unittest -v)
ejemplos/            sesión de ejemplo
```

## Si necesitas ayuda

Si tú o alguien cercano está pasando por un mal momento o tiene pensamientos de hacerse daño:
**024** (Línea de atención a la conducta suicida, España, gratuita, 24 h) · **112** (emergencias) ·
fuera de España: [findahelpline.com](https://findahelpline.com).
