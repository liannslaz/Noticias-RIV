"""
Bot de Discord: generador de imágenes de noticias a partir de
plantillas PNG.

Comando: !crear noticia-plantilla1

Toda la configuración de coordenadas/colores/fuentes vive en
engine/config.py. Toda la lógica de generación de imágenes vive en
engine/generator.py. Este archivo SOLO contiene la lógica de Discord
(conversación guiada, validaciones, permisos, errores).
"""

import asyncio
import os
import traceback

import discord
from discord.ext import commands

from engine.config import TEMPLATES
from engine.generator import (
    ImagenInvalidaError,
    PlantillaNoExisteError,
    generate_noticia,
)

# --------------------------------------------------------------------------
# Configuración general
# --------------------------------------------------------------------------

# Único canal donde se permite usar el comando "!crear".
ALLOWED_CHANNEL_ID = 1550643065151029378

# Tiempo máximo (segundos) que el bot espera cada respuesta del
# usuario antes de cancelar automáticamente una creación abandonada.
QUESTION_TIMEOUT_SECONDS = 180

# Límite razonable de longitud para el título (evita títulos enormes).
MAX_TITLE_CHARS = 140

EXTENSIONES_IMAGEN_VALIDAS = (".png", ".jpg", ".jpeg", ".webp")

# --------------------------------------------------------------------------
# Bot
# --------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True  # necesario para leer "!crear ..." y las respuestas

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Usuarios que en este momento están en medio de una creación de
# noticia (así se ignoran respuestas de otros usuarios y no se puede
# iniciar dos creaciones al mismo tiempo con la misma cuenta).
_sesiones_activas: set[int] = set()


@bot.event
async def on_ready():
    print(f"[OK] Bot conectado como {bot.user} (id={bot.user.id})")
    print(f"[OK] Escuchando el comando !crear en el canal {ALLOWED_CHANNEL_ID}")


@bot.event
async def on_command_error(ctx, error):
    # Evita que discord.py imprima un traceback genérico para errores
    # esperables (comando inexistente, falta de argumentos, etc.)
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await _responder_seguro(ctx, "Uso: `!crear noticia-plantilla1`")
        return
    print(f"[ERROR] Error no manejado en comando: {error!r}")
    traceback.print_exc()
    await _responder_seguro(ctx, "❌ Ocurrió un error inesperado al procesar el comando.")


async def _responder_seguro(ctx, contenido, **kwargs):
    """Envía un mensaje al canal, sin tumbar el bot si faltan permisos."""
    try:
        return await ctx.send(contenido, **kwargs)
    except discord.Forbidden:
        print(f"[ERROR] Sin permisos para enviar mensajes en el canal {ctx.channel.id}")
    except discord.HTTPException as exc:
        print(f"[ERROR] Fallo de Discord al enviar mensaje: {exc!r}")


# --------------------------------------------------------------------------
# Comando principal
# --------------------------------------------------------------------------

@bot.command(name="crear")
async def crear(ctx, plantilla: str = None):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await _responder_seguro(
            ctx,
            "⚠️ Ese comando solamente puede utilizarse en el canal autorizado.",
        )
        return

    if plantilla is None:
        await _responder_seguro(ctx, "Uso: `!crear noticia-plantilla1`")
        return

    plantilla_key = plantilla.strip().lower().removeprefix("noticia-")

    if plantilla_key not in TEMPLATES:
        await _responder_seguro(
            ctx,
            f"❌ La plantilla `{plantilla}` no existe todavía.",
        )
        return

    if ctx.author.id in _sesiones_activas:
        await _responder_seguro(
            ctx,
            "⚠️ Ya tienes una creación de noticia en curso. Termínala o escribe "
            "`cancelar` antes de iniciar una nueva.",
        )
        return

    _sesiones_activas.add(ctx.author.id)
    try:
        await _flujo_creacion(ctx, plantilla_key)
    finally:
        _sesiones_activas.discard(ctx.author.id)


# --------------------------------------------------------------------------
# Flujo guiado (fecha -> título -> imagen -> generación)
# --------------------------------------------------------------------------

async def _flujo_creacion(ctx, plantilla_key: str):
    def es_del_autor(mensaje: discord.Message) -> bool:
        # Solo el usuario que ejecutó el comando puede responder;
        # los mensajes de cualquier otra persona se ignoran.
        return mensaje.author.id == ctx.author.id and mensaje.channel.id == ctx.channel.id

    async def preguntar(texto: str):
        """Envía la pregunta y espera la respuesta del autor original.
        Devuelve None si hubo timeout o si el usuario canceló."""
        await _responder_seguro(ctx, texto)
        try:
            mensaje = await bot.wait_for(
                "message", check=es_del_autor, timeout=QUESTION_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            await _responder_seguro(
                ctx, "⌛ Se agotó el tiempo de espera. Creación de noticia cancelada."
            )
            return None

        if mensaje.content.strip().lower() == "cancelar":
            await _responder_seguro(ctx, "❌ Creación de noticia cancelada.")
            return None

        return mensaje

    # --- 1. Fecha ---
    respuesta = await preguntar("📅 ¿Qué fecha tendrá la noticia?")
    if respuesta is None:
        return
    fecha_texto = respuesta.content.strip()
    if not fecha_texto:
        await _responder_seguro(ctx, "❌ Creación de noticia cancelada (fecha vacía).")
        return

    # --- 2. Título ---
    respuesta = await preguntar("📰 ¿Cuál será el título de la noticia?")
    if respuesta is None:
        return
    titulo_texto = respuesta.content.strip()
    if not titulo_texto:
        await _responder_seguro(ctx, "❌ Creación de noticia cancelada (título vacío).")
        return
    if len(titulo_texto) > MAX_TITLE_CHARS:
        await _responder_seguro(
            ctx,
            f"⚠️ El título es demasiado largo (máximo {MAX_TITLE_CHARS} caracteres). "
            f"Creación cancelada, vuelve a intentarlo con `!crear noticia-{plantilla_key}`.",
        )
        return

    # --- 3. Imagen (con reintentos si el archivo no es válido) ---
    imagen_bytes = None
    while imagen_bytes is None:
        respuesta = await preguntar("🖼️ Envía la imagen que quieres utilizar en la noticia.")
        if respuesta is None:
            return

        if not respuesta.attachments:
            await _responder_seguro(
                ctx,
                "⚠️ No enviaste ninguna imagen. Adjunta un archivo PNG, JPG o WEBP "
                "(o escribe `cancelar`).",
            )
            continue

        adjunto = respuesta.attachments[0]
        tipo_ok = (adjunto.content_type or "").startswith("image/")
        extension_ok = adjunto.filename.lower().endswith(EXTENSIONES_IMAGEN_VALIDAS)
        if not (tipo_ok or extension_ok):
            await _responder_seguro(
                ctx,
                "⚠️ El archivo enviado no es una imagen válida. Intenta con PNG, "
                "JPG o WEBP (o escribe `cancelar`).",
            )
            continue

        try:
            imagen_bytes = await adjunto.read()
        except discord.HTTPException:
            await _responder_seguro(
                ctx, "⚠️ No pude descargar la imagen. Intenta enviarla de nuevo."
            )
            continue

    # --- 4. Generación ---
    aviso = await _responder_seguro(ctx, "⏳ Generando la noticia...")

    try:
        ruta_salida = await asyncio.to_thread(
            generate_noticia, plantilla_key, fecha_texto, titulo_texto, imagen_bytes
        )
    except ImagenInvalidaError:
        await _responder_seguro(
            ctx, "⚠️ El archivo no parece ser una imagen válida. Intenta de nuevo con otro archivo."
        )
        return
    except PlantillaNoExisteError:
        await _responder_seguro(ctx, "❌ La plantilla no existe.")
        return
    except Exception as exc:
        print(f"[ERROR] Fallo al generar noticia para {ctx.author} ({ctx.author.id}): {exc!r}")
        traceback.print_exc()
        await _responder_seguro(
            ctx, "❌ Ocurrió un error al generar la imagen de la noticia. Intenta de nuevo más tarde."
        )
        return

    try:
        await ctx.send("✅ Noticia creada correctamente.", file=discord.File(ruta_salida, filename="noticia.png"))
    except discord.Forbidden:
        print(f"[ERROR] Sin permisos para enviar archivos en el canal {ctx.channel.id}")
    except discord.HTTPException as exc:
        print(f"[ERROR] Fallo de Discord al enviar la imagen: {exc!r}")
    finally:
        try:
            os.remove(ruta_salida)
        except OSError:
            pass


# --------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("[ERROR] Falta la variable de entorno DISCORD_TOKEN. "
              "Configúrala antes de iniciar el bot.")
        raise SystemExit(1)

    bot.run(token)


if __name__ == "__main__":
    main()
