# Detector de emociones en texto

Sistema en Python que identifica **emociones** en un texto escrito (en español o inglés) usando
[TextBlob](https://textblob.readthedocs.io/) junto con un léxico de emociones y reglas de contexto.

Reconoce las 6 emociones básicas de Paul Ekman:

| Emoción | Ejemplo |
|---|---|
| 😊 Alegría | *¡Hoy es el mejor día de mi vida, estoy muy feliz!* |
| 😢 Tristeza | *Te echo de menos, me siento sola* |
| 😡 Ira | *Estoy FURIOSO, odio que me mientan!!* |
| 😱 Miedo | *Tengo mucho miedo de quedarme sin trabajo* |
| 😮 Sorpresa | *No me lo puedo creer, ¡me han dado el premio!* |
| 🤢 Asco | *Qué asco, la comida estaba podrida* |

Si no encuentra ninguna, el texto se clasifica como **neutral** 😐.

## Instalación

```bash
pip install -r requirements.txt
python -m textblob.download_corpora lite
```

## Uso

```bash
python detector.py          # modo interactivo: escribe frases y las analiza
python detector.py --demo   # analiza 10 frases de ejemplo
```

También se puede usar desde otro programa:

```python
from detector import analizar

r = analizar("No estoy contento con el resultado.")
print(r["dominante"])     # 'tristeza'
print(r["porcentajes"])   # {'tristeza': 100.0, 'alegria': 0.0, ...}
print(r["polaridad"])     # -1.0
print(r["detalles"])      # ["'contento' NEGADA -> tristeza +1.00"]
```

Ejemplo de salida:

```
Texto: Estoy FURIOSO, odio que me mientan!!
Emoción dominante: Ira 😡
  Ira 😡          ████████████████████ 100.0 %
Polaridad: -1.00 (negativo)
Por qué:
   · 'FURIOSO' -> ira +4.68
   · 'odio' -> ira +3.60
```

## Cómo funciona

TextBlob solo calcula la **polaridad** (positivo/negativo) y la **subjetividad**, y solo en inglés:
con *"Estoy muy feliz"* devuelve polaridad 0. Por eso el sistema es **híbrido**:

1. **TextBlob separa** el texto en oraciones y palabras. Funciona en cualquier idioma.
2. **Normalización**: minúsculas y sin tildes (`Alegría` → `alegria`).
3. **Léxico de emociones** ([`lexico.py`](lexico.py)): cada palabra tiene una emoción y un peso de 1 a 3.
   Las entradas con `*` son raíces (`alegr*` → alegre, alegría, alegrarse…) y también hay
   expresiones de varias palabras (`echo de menos`, `no me lo puedo creer`).
4. **Reglas de contexto**:
   - **Negación** (`no`, `nunca`, `jamás`… en las 3 palabras anteriores): *"no estoy feliz"* → tristeza a
     mitad de fuerza, *"no estoy triste"* → alegría a mitad de fuerza y *"no tengo miedo"* → se anula.
   - **Intensificadores**: `muy` ×1.5, `súper` ×1.7, `extremadamente` ×2, `poco` ×0.5…
   - **MAYÚSCULAS**: ×1.3 (se interpretan como un grito).
   - **Exclamaciones**: +20 % por cada `!` de la oración (máximo +60 %).
   - **Emojis**: 😊 😢 😡 😨 😮 🤢 y más.
5. **Puntuación**: se suman los puntos de cada emoción y se pasan a porcentajes. Gana la mayor, y si la
   segunda está a menos del 80 % de la primera, el texto se marca como **mixto**.
6. **Polaridad**: en inglés la calcula TextBlob. En español se estima como
   `(alegría − negativas) / (alegría + negativas)`.

Cada análisis devuelve en `detalles` la lista de palabras que han sumado puntos, así se puede ver
**por qué** ha decidido cada emoción.

## Limitaciones

- No entiende la **ironía** (*"genial, otra vez lunes"* → alegría).
- Solo conoce las palabras del léxico. Para mejorarlo basta con añadir palabras en `lexico.py`.
- La negación mira solo una ventana de 3 palabras hacia atrás.

Para ir más allá, el siguiente paso sería un modelo entrenado (por ejemplo, un transformer de
Hugging Face para emociones en español).

## Estructura

```
detector.py       # lógica del análisis + programa de terminal
lexico.py         # palabras, emojis, negaciones e intensificadores
requirements.txt
```
