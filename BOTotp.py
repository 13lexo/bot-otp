import os
import base64
import re
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

# Cargar variables de entorno desde Render
# En Render, configuras las variables desde la interfaz, no desde el .env
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')

# Expresión regular para extraer el código de verificación
codigo_regex = r'<td class="p2b"[^>]*>(\d{4})</td>'

# Definir el alcance de acceso a la cuenta de Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Crear y devolver un servicio de Gmail con credenciales."""
    try:
        if not GOOGLE_CREDENTIALS:
            print("Credenciales de Google no encontradas en las variables de entorno.")
            return None

        # Convertir las credenciales de Google de JSON a diccionario
        creds_info = json.loads(GOOGLE_CREDENTIALS)

        # Crear credenciales de OAuth2 usando el token de acceso y el refresh token
        creds = Credentials(
            token=creds_info['token'],
            refresh_token=creds_info['refresh_token'],
            token_uri=creds_info['token_uri'],
            client_id=creds_info['client_id'],
            client_secret=creds_info['client_secret'],
            scopes=SCOPES,
        )

        # Si el token ha expirado, renovarlo
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # Crear el servicio de Gmail
        service = build('gmail', 'v1', credentials=creds)
        return service

    except Exception as e:
        print(f"Error al obtener el servicio de Gmail: {e}")
        return None

async def send_code_to_telegram(code, chat_id, bot):
    """Enviar el código de verificación a Telegram."""
    await bot.send_message(chat_id=chat_id, text=f'El código de verificación de Uber Eats es: {code}')

async def start(update: Update, context):
    """Manejar el comando /start y explicar cómo usar el bot."""
    await update.message.reply_text(
        "¡Hola! Soy tu bot de verificación de Uber Eats. Envíame una dirección de correo electrónico y te daré el código de verificación asociado a esa cuenta. Creado por leXo. https://t.me/+F2gM5GGrt0Y1NzY0"
    )

async def handle_message(update: Update, context):
    """Manejar el mensaje recibido por el bot."""
    user_id = update.message.chat_id
    email_address = update.message.text.strip()

    # Obtener el servicio de Gmail con el token
    service = get_gmail_service()
    
    if not service:
        await send_code_to_telegram("No se pudo autenticar con Gmail.", user_id, context.bot)
        return

    # Buscar el correo de Uber Eats para la dirección proporcionada
    message = search_verification_emails(service, email_address)
    
    if message:
        # Extraer el código de verificación
        code = extract_verification_code(message)
        
        if code:
            print(f'Código de verificación encontrado: {code}')
            await send_code_to_telegram(code, user_id, context.bot)
        else:
            print('No se encontró un código de verificación en el correo.')
            await send_code_to_telegram('No se encontró un código de verificación en el correo.', user_id, context.bot)
    else:
        print(f'No se encontraron correos de Uber Eats para {email_address}.')
        await send_code_to_telegram(f'No se encontraron correos de Uber Eats para {email_address}.', user_id, context.bot)

def main():
    """Iniciar el bot de Telegram y escuchar mensajes."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Agregar el comando /start
    application.add_handler(CommandHandler("start", start))

    # Agregar el handler para manejar mensajes de texto (dirección de correo electrónico)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Iniciar el bot
    application.run_polling()

if __name__ == '__main__':
    main()
