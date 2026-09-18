# Noticias RIV — Bot de Discord

Bot en Python (discord.py + Pillow) que genera imágenes de noticias a
partir de plantillas PNG, mediante un flujo guiado por chat.

## 1. Estructura del proyecto

```
/
├── main.py                        # Lógica del bot de Discord (comandos, flujo, errores)
├── requirements.txt                # Dependencias
├── Procfile                        # Indica a Railway cómo iniciar el bot
├── .env.example                    # Ejemplo de variables de entorno
├── .gitignore
├── README.md
├── plantillas/
│   └── plantilla1.png              # Plantilla oficial de la noticia
├── fonts/
│   ├── LiberationSerif-Bold.ttf    # Fuente del título (y la fecha usa Poppins)
│   └── Poppins-Bold.ttf            # Fuente de la fecha
└── engine/
    ├── __init__.py
    ├── config.py                   # TODAS las coordenadas/colores/fuentes por plantilla
    └── generator.py                # Generación de la imagen con Pillow (sin nada de Discord)
```

El código está dividido a propósito en tres capas:

- **`main.py`**: solo Discord (comandos, preguntas, validaciones, permisos).
- **`engine/generator.py`**: solo Pillow (recorte de imagen, texto, autoajuste). No sabe nada de Discord.
- **`engine/config.py`**: solo datos (coordenadas). No tiene lógica.

Así, agregar una plantilla nueva no toca ni una línea de `main.py` ni de `generator.py`.

## 2. Cómo funciona el comando

En el canal autorizado (`1550643065151029378`):

```
!crear noticia-plantilla1
```

1. El bot pregunta la **fecha** → el usuario responde (se usa tal cual la escriba).
2. El bot pregunta el **título** → si es muy largo (más de 140 caracteres) cancela y pide reintentar; si cabe, se autoajusta el tamaño de letra y se reparte en líneas para que nunca se salga del recuadro.
3. El bot pide la **imagen** → debe ser un archivo adjunto PNG/JPG/WEBP; si no es válido, vuelve a pedirla (sin cancelar el proceso).
4. Genera `noticia.png` y lo envía al mismo canal con "✅ Noticia creada correctamente."

En cualquier momento el usuario puede escribir `cancelar` para abortar. Si tarda más de 3 minutos en responder una pregunta, el bot cancela automáticamente. Solo la persona que ejecutó el comando puede responder sus propias preguntas — los mensajes de cualquier otro usuario en el canal se ignoran.

Si el comando se usa en otro canal, el bot responde que solo puede usarse en el canal autorizado y no genera nada.

> **Nota:** la plantilla también tiene espacio para un "resumen breve" y el "texto de la noticia", pero como tu especificación del flujo solo pide fecha, título e imagen, esas dos zonas se dejan en blanco (limpias, sin el texto de ejemplo) en esta versión. Sus coordenadas ya están listas en `engine/config.py` (`summary_box`, `body_box`) para cuando quieras agregar esas preguntas — solo habría que sumar dos preguntas más en `main.py` y dos líneas de `draw.text(...)` en `generator.py`.

## 3. Agregar una plantilla nueva (plantilla2, plantilla3, ...)

1. Pon el archivo en `plantillas/plantilla2.png`.
2. En `engine/config.py`, copia el bloque `"plantilla1": {...}`, pégalo como `"plantilla2": {...}` y ajusta las coordenadas a la nueva imagen (puedes medirlas igual que se hizo con la primera: abriendo la imagen y ubicando los rectángulos de fecha/título/imagen).
3. Ya funciona: `!crear noticia-plantilla2` la encuentra sola, porque `main.py` busca el nombre en el diccionario `TEMPLATES`.

No hay que tocar el bot ni el generador para esto.

## 4. Ejecutarlo localmente (opcional, para probar antes de subirlo)

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DISCORD_TOKEN=tu_token_aqui   # En Windows (PowerShell): $env:DISCORD_TOKEN="tu_token_aqui"
python main.py
```

## 5. Subir a GitHub

Desde la carpeta del proyecto:

```bash
git init
git add .
git commit -m "Bot de noticias RIV: plantilla1"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

El archivo `.gitignore` ya excluye `.env`, así que tu token nunca se sube por accidente.

## 6. Desplegar en Railway

1. En Railway: **New Project → Deploy from GitHub repo** y elige tu repositorio.
2. Ve a la pestaña **Variables** del servicio y agrega:
   - `DISCORD_TOKEN` = tu token del bot (el mismo valor que usarías en `.env`)
3. Railway detecta Python automáticamente e instala `requirements.txt`. Gracias al `Procfile` (`worker: python main.py`), sabe cómo iniciar el bot.
   - Si por algún motivo no lo detecta solo, entra a **Settings → Deploy** y pon manualmente el **Start Command**: `python main.py`.
4. Como este bot no expone un servidor web (no necesita puerto), es normal que Railway no muestre una URL pública — eso no es un error, simplemente no aplica para un bot de Discord.
5. Cuando termine el deploy, revisa la pestaña **Deploy Logs**: debe aparecer `[OK] Bot conectado como ...`. Ahí mismo aparecerán también los errores (imagen inválida, falta de permisos, etc.) si algo falla en producción.

## 7. Notas técnicas

- **Token**: nunca está escrito en el código; se lee con `os.getenv("DISCORD_TOKEN")`. Si falta, el bot lo avisa claramente en consola y no arranca.
- **Intent necesario**: en el [Discord Developer Portal](https://discord.com/developers/applications), dentro de tu aplicación → pestaña **Bot**, asegúrate de que el interruptor **"Message Content Intent"** esté activado. Sin eso, el bot no puede leer el texto de `!crear ...` ni tus respuestas (esto es una casilla del bot que ya tienes creado, no hace falta crear nada nuevo).
- **Errores manejados**: imagen faltante o inválida, timeout de respuesta, cancelación, plantilla inexistente, token faltante, y falta de permisos para enviar mensajes/archivos (todos quedan además registrados en los logs de Railway con detalle para depurar).
- **Fuentes**: para cambiar la tipografía, solo reemplaza el archivo `.ttf` dentro de `fonts/` y actualiza la ruta correspondiente (`title_font_path` o `date_font_path`) en `engine/config.py` — no hay que tocar nada más.
