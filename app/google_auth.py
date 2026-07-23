import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from app.config import Config

SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/drive.file"]

def get_credentials():
    token_data = json.loads(Config.google_oauth_token_json)
    client_data = json.loads(Config.google_client_secret_json)
    installed = client_data.get("installed") or client_data.get("web")
    if not installed:
        raise RuntimeError("Credenciales OAuth inválidas")
    creds = Credentials(token=token_data.get("token"), refresh_token=token_data.get("refresh_token"), token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"), client_id=installed["client_id"], client_secret=installed["client_secret"], scopes=SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("Token OAuth inválido o sin refresh_token")
    return creds
