import os
import base64
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, request

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de Telegram usando la variable de entorno TELEGRAM_TOKEN
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Expresión regular para extraer el código de verificación
codigo_regex = r'<td class="p2b"[^>]*>(\d{4})</td>'

# Configurar las credenciales de Google directamente desde las variables de entorno
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')  # JSON completo como string
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Flask application
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Recibir actualizaciones del bot de Telegram a través del webhook."""
    json_str = request.get_data(as_text=True)
    update = Update.de_json(json_str, bot)
    application.process_update(update)
    return 'ok', 200

def get_gmail_service():
    """Autenticación y creación del servicio de Gmail con OAuth2."""
    try:
        if not GOOGLE_CREDENTIALS:
            print("Credenciales de Google no encontradas en las variables de entorno.")
            return None

        # Convertir las credenciales en formato JSON a un diccionario
        creds_info = eval(GOOGLE_CREDENTIALS)

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
        print(f"Error al autenticar con Gmail: {e}")
        return None

def search_verification_emails(service, email_address):
    """Buscar correos de Uber Eats enviados a una dirección específica."""
    try:
        # Buscar correos con el remitente y asunto específicos y filtrados por la dirección 'To'
        results = service.users().messages().list(
            userId='me',
            q=f"from:admin@uber.com subject:Your Uber account verification code to:{email_address}",
        ).execute()
        messages = results.get('messages', [])

        if not messages:
            print(f"No se encontraron correos de Uber Eats enviados a {email_address}.")
            return None

        # Obtener el último correo
        message = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
        return message

    except HttpError as error:
        print(f"Ha ocurrido un error: {error}")
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
        "¡Hola! Soy tu bot de verificación de Uber Eats. Envíame una dirección de correo electrónico y te daré el código de verificación asociado a esa cuenta. Creado por leXo."
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
    """Iniciar el bot de Telegram y configurar el webhook."""
    global bot
    bot = Bot(token=TELEGRAM_TOKEN)

    # Crear la aplicación de Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Agregar el comando /start
    application.add_handler(CommandHandler("start", start))

    # Agregar el handler para manejar mensajes de texto (dirección de correo electrónico)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Configurar el webhook en Telegram
    bot.set_webhook(url='https://bot-otp-6.onrender.com')  # Asegúrate de cambiar 'your-render-url' por tu URL de Render

    # Iniciar el servidor Flask para el webhook
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Asignar puerto dinámico para Render

if __name__ == "__main__":
    main()