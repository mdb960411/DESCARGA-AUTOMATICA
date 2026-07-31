import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.config import Config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.file",
]


def _load_json_source(inline_value, file_path, description):
    try:
        if file_path is not None:
            raw_value = file_path.read_text(encoding="utf-8")
        else:
            raw_value = inline_value
        value = json.loads(raw_value)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{description} no contiene JSON válido") from exc

    if not isinstance(value, dict):
        raise RuntimeError(f"{description} debe contener un objeto JSON")
    return value


def get_credentials():
    token_data = _load_json_source(
        Config.google_oauth_token_json,
        Config.google_oauth_token_file,
        "El token OAuth",
    )
    client_data = _load_json_source(
        Config.google_client_secret_json,
        Config.google_client_secret_file,
        "El secreto del cliente OAuth",
    )
    installed = client_data.get("installed") or client_data.get("web")
    if not installed:
        raise RuntimeError("Credenciales OAuth inválidas")
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get(
            "token_uri", "https://oauth2.googleapis.com/token"
        ),
        client_id=installed["client_id"],
        client_secret=installed["client_secret"],
        scopes=SCOPES,
    )
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("Token OAuth inválido o sin refresh_token")
    return creds
