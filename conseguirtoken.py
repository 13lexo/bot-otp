from google_auth_oauthlib.flow import InstalledAppFlow
import os

# Define el alcance de la API de Gmail que necesitas
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    # Crea el flujo de autenticación usando el archivo de credenciales descargado
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)

    # Ejecuta el flujo de autenticación en el navegador y guarda el token
    creds = flow.run_local_server(port=0)
    
    # Guarda las credenciales en token.json para usarlas en futuras ejecuciones
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

if __name__ == '__main__':
    main()
