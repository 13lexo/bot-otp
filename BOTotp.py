import os
import base64
import re
import pickle
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configuración de Telegram
TELEGRAM_TOKEN = '7745056911:AAENoA2p0dyWa1OuGP-2ncDQnXzDdxDZ2MM'

# Expresión regular para extraer el código de verificación
codigo_regex = r'<td class="p2b"[^>]*>(\d{4})</td>'

# Definir el alcance de acceso a la cuenta de Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Autenticación y creación del servicio de Gmail."""
    creds = None
    # Cargar las credenciales desde token.json (ya generadas)
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Si las credenciales no son válidas o han expirado, pedir renovación o autenticación
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Las credenciales no son válidas. Vuelve a autorizar.")
            return None

    service = build('gmail', 'v1', credentials=creds)
    return service

def search_verification_emails(service, email_address):
    """Buscar correos de Uber Eats enviados a una dirección específica."""
    try:
        # Buscar correos con el remitente y asunto específicos y filtrados por la dirección 'To'
        results = service.users().messages().list(userId='me', q=f"from:admin@uber.com subject:Your Uber account verification code to:{email_address}").execute()
        messages = results.get('messages', [])
        
        if not messages:
            print(f"No se encontraron correos de Uber Eats enviados a {email_address}.")
            return None

        # Obtener el último correo
        message = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
        return message

    except HttpError as error:
        print(f'Ha ocurrido un error: {error}')
        return None

def extract_verification_code(message):
    """Extraer el código de verificación del cuerpo del mensaje."""
    for part in message['payload']['headers']:
        if part['name'] == 'Content-Type' and 'text/html' in part['value']:
            # Extraer el cuerpo HTML del correo
            data = message['payload']['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Buscar el código de verificación usando la expresión regular
            match = re.search(codigo_regex, body)
            if match:
                return match.group(1)
    return None

async def send_code_to_telegram(code, chat_id):
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
        await send_code_to_telegram("No se pudo autenticar con Gmail.", user_id)
        return

    # Buscar el correo de Uber Eats para la dirección proporcionada
    message = search_verification_emails(service, email_address)
    
    if message:
        # Extraer el código de verificación
        code = extract_verification_code(message)
        
        if code:
            print(f'Código de verificación encontrado: {code}')
            await send_code_to_telegram(code, user_id)
        else:
            print('No se encontró un código de verificación en el correo.')
            await send_code_to_telegram('No se encontró un código de verificación en el correo.', user_id)
    else:
        print(f'No se encontraron correos de Uber Eats para {email_address}.')
        await send_code_to_telegram(f'No se encontraron correos de Uber Eats para {email_address}.', user_id)

def main():
    """Iniciar el bot de Telegram y escuchar mensajes."""
    global bot
    bot = Bot(token=TELEGRAM_TOKEN)

    # Crear la aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Agregar el comando /start
    application.add_handler(CommandHandler("start", start))

    # Agregar el handler para manejar mensajes de texto (dirección de correo electrónico)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Iniciar el bot
    application.run_polling()

if __name__ == '__main__':
    main()
