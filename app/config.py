import os
from pathlib import Path

def env_bool(name, default=False):
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "si", "sí"}

class Config:
    gmail_query = os.getenv("GMAIL_QUERY", "is:unread")
    processed_label = os.getenv("PROCESSED_LABEL", "Descarga-Automatica-Procesado")
    only_from = os.getenv("ONLY_FROM", "").strip().lower()
    only_from_domain = os.getenv("ONLY_FROM_DOMAIN", "").strip().lower()
    keyword = os.getenv("KEYWORD", "").strip().lower()
    max_emails = int(os.getenv("MAX_EMAILS", "20"))
    drive_folder_id = os.getenv("DRIVE_FOLDER_ID", "").strip()
    download_dir = Path(os.getenv("DOWNLOAD_DIR", "/tmp/descargas"))
    google_oauth_token_json = os.getenv("GOOGLE_OAUTH_TOKEN_JSON", "").strip()
    google_client_secret_json = os.getenv("GOOGLE_CLIENT_SECRET_JSON", "").strip()
    enable_sendgb = env_bool("ENABLE_SENDGB", True)
    mark_as_read = env_bool("MARK_AS_READ", True)
    allowed_extensions = {e.strip().lower() for e in os.getenv("ALLOWED_EXTENSIONS", "").split(",") if e.strip()}

    @classmethod
    def validate(cls):
        missing = []
        for name, value in [("GOOGLE_OAUTH_TOKEN_JSON", cls.google_oauth_token_json), ("GOOGLE_CLIENT_SECRET_JSON", cls.google_client_secret_json), ("DRIVE_FOLDER_ID", cls.drive_folder_id)]:
            if not value:
                missing.append(name)
        if missing:
            raise RuntimeError("Faltan variables obligatorias: " + ", ".join(missing))
