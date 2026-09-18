"""
Motor de generación de imágenes de noticias a partir de plantillas PNG.

No contiene nada específico de Discord: recibe texto/bytes y devuelve
la ruta del archivo PNG final. Así se puede reutilizar o probar por
separado del bot.
"""

import io
import os
import tempfile
import uuid

from PIL import Image, ImageDraw, ImageFont, ImageOps

from engine.config import TEMPLATES


class PlantillaNoExisteError(Exception):
    """La plantilla solicitada no está configurada."""


class ImagenInvalidaError(Exception):
    """El archivo enviado por el usuario no es una imagen válida."""


def _wrap_text_por_ancho(draw, text, font, max_width):
    """Divide `text` en líneas que quepan en `max_width`, midiendo
    el ancho real de cada línea con la fuente dada (no por cantidad
    de caracteres, sino en píxeles)."""
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if width <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_title(draw, text, font_path, box, max_size, min_size, line_spacing):
    """Busca el tamaño de fuente más grande posible (entre min_size y
    max_size) tal que el texto, ya dividido en líneas, quepa dentro
    de `box`. Si ni con el tamaño mínimo cabe, recorta líneas
    sobrantes y agrega "…" al final."""
    left, top, right, bottom = box
    max_width = right - left
    max_height = bottom - top

    size = max_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        lines = _wrap_text_por_ancho(draw, text, font, max_width)
        ascent, descent = font.getmetrics()
        line_height = int((ascent + descent) * line_spacing)
        total_height = line_height * len(lines)
        if total_height <= max_height:
            return font, lines, line_height
        size -= 2

    # Ni con el tamaño mínimo cabe completo: se trunca con "…".
    font = ImageFont.truetype(font_path, min_size)
    lines = _wrap_text_por_ancho(draw, text, font, max_width)
    ascent, descent = font.getmetrics()
    line_height = int((ascent + descent) * line_spacing)
    max_lines = max(1, max_height // line_height)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=font)[2] > max_width:
            last = last[:-1].rstrip()
        lines[-1] = (last + "…") if last else "…"

    return font, lines, line_height


def _fit_single_line(draw, text, font_path, max_width, max_size, min_size):
    """Igual que _fit_title pero para una sola línea (usado en la
    fecha): reduce el tamaño hasta que el texto quepa en max_width."""
    size = max_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        width = draw.textbbox((0, 0), text, font=font)[2]
        if width <= max_width:
            return font
        size -= 1
    return ImageFont.truetype(font_path, min_size)


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Recorte tipo "cover": mantiene proporción, recorta lo
    necesario centrado, sin deformar, y ajusta exactamente al
tamaño destino."""
    img = ImageOps.exif_transpose(img)  # respeta la orientación de fotos de celular
    img = img.convert("RGB")

    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # La imagen fuente es relativamente más ancha: recorta a los costados.
        new_w = max(1, round(src_h * target_ratio))
        x0 = (src_w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, src_h))
    else:
        # La imagen fuente es relativamente más alta: recorta arriba/abajo.
        new_h = max(1, round(src_w / target_ratio))
        y0 = (src_h - new_h) // 2
        img = img.crop((0, y0, src_w, y0 + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def generate_noticia(template_key: str, date_text: str, title_text: str,
                      image_bytes: bytes, output_dir: str | None = None) -> str:
    """Genera la imagen final de la noticia y devuelve la ruta del
    archivo PNG resultante.

    Lanza PlantillaNoExisteError o ImagenInvalidaError si corresponde;
    cualquier otro error de Pillow se propaga tal cual para que quien
    llame lo registre en el log."""

    cfg = TEMPLATES.get(template_key)
    if cfg is None:
        raise PlantillaNoExisteError(template_key)

    try:
        user_img = Image.open(io.BytesIO(image_bytes))
        user_img.load()
    except Exception as exc:
        raise ImagenInvalidaError(str(exc)) from exc

    bg = Image.open(cfg["background"]).convert("RGB")
    draw = ImageDraw.Draw(bg)

    # 1) Imagen de la noticia (recorte cover + pegado)
    ix1, iy1, ix2, iy2 = cfg["image_box"]
    fitted = _cover_crop(user_img, ix2 - ix1, iy2 - iy1)
    bg.paste(fitted, (ix1, iy1))

    # 2) Fecha (se borra el marcador "FECHA" y se escribe la real)
    draw.rectangle(cfg["date_erase_box"], fill=cfg["bg_color"])
    date_font = _fit_single_line(
        draw, date_text, cfg["date_font_path"],
        cfg["date_max_width"], cfg["date_max_size"], cfg["date_min_size"],
    )
    draw.text(cfg["date_position"], date_text, font=date_font,
               fill=cfg["date_color"], anchor="lm")

    # 3) Título (se borra el texto de ejemplo y se escribe el real,
    #    con autoajuste de tamaño y salto de línea)
    draw.rectangle(cfg["title_box"], fill=cfg["bg_color"])
    title_font, lines, line_height = _fit_title(
        draw, title_text, cfg["title_font_path"], cfg["title_box"],
        cfg["title_max_size"], cfg["title_min_size"], cfg["title_line_spacing"],
    )
    x, y = cfg["title_box"][0], cfg["title_box"][1]
    for line in lines:
        draw.text((x, y), line, font=title_font, fill=cfg["title_color"])
        y += line_height

    # 4) Se limpia el texto de ejemplo del resumen breve (no se usa
    #    todavía en esta versión; ver config.py -> summary_box).
    draw.rectangle(cfg["summary_erase_box"], fill=cfg["bg_color"])

    out_dir = output_dir or tempfile.gettempdir()
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"noticia_{uuid.uuid4().hex}.png")
    bg.save(out_path, "PNG")
    return out_path
