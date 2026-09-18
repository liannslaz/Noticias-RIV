"""
Configuración centralizada de todas las plantillas de noticias.

Cada entrada en TEMPLATES define TODO lo necesario para generar una
noticia con esa plantilla: fondo, colores, fuentes y coordenadas.

Para agregar una nueva plantilla (plantilla2, plantilla3, ...) en el
futuro, NO hay que tocar el bot ni el generador de imágenes:

    1. Coloca el archivo de imagen en plantillas/plantillaN.png
    2. Copia el bloque "plantilla1" de aquí abajo, cámbiale la clave
a "plantilla2" y ajusta las coordenadas a la nueva plantilla.
    3. Listo. El comando "!crear noticia-plantilla2" funcionará solo,
       porque main.py busca la plantilla en este diccionario.

Todas las coordenadas están en píxeles, sobre el lienzo original de
la imagen de fondo (para plantilla1: 1024x1536 px).
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
PLANTILLAS_DIR = os.path.join(BASE_DIR, "plantillas")

# Color de fondo real de la plantilla (blanco ligeramente hueso).
# Se usa para "borrar" los textos de ejemplo antes de escribir los
datos reales, sin dejar residuos del texto de muestra.
_BG_COLOR = (249, 250, 250)

TEMPLATES = {
    "plantilla1": {
        # --- Fondo ---
        "background": os.path.join(PLANTILLAS_DIR, "plantilla1.png"),
        "canvas_size": (1024, 1536),
        "bg_color": _BG_COLOR,

        # --- Imagen de la noticia (recorte tipo "cover") ---
        # Rectángulo exacto del recuadro oscuro de la plantilla.
        "image_box": (549, 314, 975, 707),  # left, top, right, bottom

        # --- Fecha ---
        # La plantilla trae la palabra "FECHA" como marcador de
        # posición; esa zona se borra y se escribe la fecha real ahí.
        "date_position": (104, 267),  # ancla izquierda-medio (anchor "lm")
        "date_erase_box": (98, 250, 860, 285),
        "date_max_width": 756,
        "date_font_path": os.path.join(FONTS_DIR, "Poppins-Bold.ttf"),
        "date_color": (10, 10, 10),
        "date_max_size": 34,
        "date_min_size": 16,

        # --- Título ---
        # Caja donde debe caber el título (se autoajusta tamaño/línea).
        "title_box": (65, 340, 528, 592),  # left, top, right, bottom
        "title_font_path": os.path.join(FONTS_DIR, "LiberationSerif-Bold.ttf"),
        "title_color": (10, 10, 10),
        "title_max_size": 110,
        "title_min_size": 34,
        "title_line_spacing": 1.08,
        "title_max_chars": 140,  # límite razonable de entrada

        # --- Resumen breve ---
        # La plantilla trae una frase de ejemplo en esta zona. Por
        # ahora el bot NO pide un resumen (solo pide fecha, título e
        # imagen, tal como se especificó), así que esta zona
        # simplemente se borra para dejarla en blanco y limpia.
        "summary_erase_box": (40, 598, 540, 705),

        # Reservado para cuando se agregue la pregunta de "resumen"
        # en una futura versión (ya con coordenadas listas):
        "summary_box": (65, 605, 528, 700),
        "summary_font_path": os.path.join(FONTS_DIR, "LiberationSerif-Bold.ttf"),

        # Reservado para cuando se agregue la pregunta de "texto de
        # la noticia" (cuerpo completo) en una futura versión:
        "body_box": (60, 795, 968, 1370),
        "body_font_path": os.path.join(FONTS_DIR, "LiberationSerif-Bold.ttf"),
    },
}
