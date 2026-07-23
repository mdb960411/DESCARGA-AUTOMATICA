import os
from pathlib import Path


def env_bool(name, default=False):
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "si", "sí"}


def env_int(name, default):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un número entero") from exc


DEFAULT_ALLOWED_EXTENSIONS = {
    ".7z",
    ".afdesign",
    ".afphoto",
    ".ai",
    ".ait",
    ".cdr",
    ".csv",
    ".doc",
    ".docx",
    ".eps",
    ".idml",
    ".indd",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".ps",
    ".psb",
    ".psd",
    ".rar",
    ".svg",
    ".tif",
    ".tiff",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}


class Config:
    gmail_query = os.getenv("GMAIL_QUERY", "is:unread")
    processed_label = os.getenv("PROCESSED_LABEL", "Descarga-Automatica-Procesado")
    error_label = os.getenv("ERROR_LABEL", "Descarga-Automatica-Error")
    partial_label = os.getenv("PARTIAL_LABEL", "Descarga-Automatica-Parcial")
    only_from = os.getenv("ONLY_FROM", "").strip().lower()
    only_from_domain = os.getenv("ONLY_FROM_DOMAIN", "").strip().lower()
    keyword = os.getenv("KEYWORD", "").strip().lower()
    max_emails = env_int("MAX_EMAILS", 20)
    drive_folder_id = os.getenv("DRIVE_FOLDER_ID", "").strip()
    download_dir = Path(os.getenv("DOWNLOAD_DIR", "/tmp/descargas"))
    google_oauth_token_json = os.getenv("GOOGLE_OAUTH_TOKEN_JSON", "").strip()
    google_client_secret_json = os.getenv("GOOGLE_CLIENT_SECRET_JSON", "").strip()
    enable_sendgb = env_bool("ENABLE_SENDGB", True)
    mark_as_read = env_bool("MARK_AS_READ", True)
    exclude_error_messages = env_bool("EXCLUDE_ERROR_MESSAGES", True)
    browser_http_handoff = env_bool("BROWSER_HTTP_HANDOFF", True)
    max_file_size_mb = env_int("MAX_FILE_SIZE_MB", 8192)
    download_chunk_size_mb = env_int("DOWNLOAD_CHUNK_SIZE_MB", 4)
    upload_chunk_size_mb = env_int("UPLOAD_CHUNK_SIZE_MB", 8)
    upload_retries = env_int("UPLOAD_RETRIES", 3)
    download_timeout_seconds = env_int("DOWNLOAD_TIMEOUT_SECONDS", 1800)

    _allowed_extensions_raw = os.getenv("ALLOWED_EXTENSIONS", "").strip()
    allowed_extensions = (
        {
            extension
            if extension.startswith(".")
            else f".{extension}"
            for extension in (
                item.strip().lower()
                for item in _allowed_extensions_raw.split(",")
            )
            if extension
        }
        if _allowed_extensions_raw
        else DEFAULT_ALLOWED_EXTENSIONS
    )

    @classmethod
    def max_file_size_bytes(cls):
        return cls.max_file_size_mb * 1024 * 1024

    @classmethod
    def download_chunk_size_bytes(cls):
        return cls.download_chunk_size_mb * 1024 * 1024

    @classmethod
    def upload_chunk_size_bytes(cls):
        return cls.upload_chunk_size_mb * 1024 * 1024

    @classmethod
    def validate(cls):
        missing = []
        for name, value in [
            ("GOOGLE_OAUTH_TOKEN_JSON", cls.google_oauth_token_json),
            ("GOOGLE_CLIENT_SECRET_JSON", cls.google_client_secret_json),
            ("DRIVE_FOLDER_ID", cls.drive_folder_id),
        ]:
            if not value:
                missing.append(name)
        if missing:
            raise RuntimeError("Faltan variables obligatorias: " + ", ".join(missing))

        positive_values = [
            ("MAX_EMAILS", cls.max_emails),
            ("MAX_FILE_SIZE_MB", cls.max_file_size_mb),
            ("DOWNLOAD_CHUNK_SIZE_MB", cls.download_chunk_size_mb),
            ("UPLOAD_CHUNK_SIZE_MB", cls.upload_chunk_size_mb),
            ("DOWNLOAD_TIMEOUT_SECONDS", cls.download_timeout_seconds),
        ]
        invalid = [name for name, value in positive_values if value <= 0]
        if invalid:
            raise RuntimeError(
                "Estas variables deben ser mayores que cero: " + ", ".join(invalid)
            )

        # Google Drive exige que los fragmentos de una subida reanudable sean
        # múltiplos de 256 KiB.
        if cls.upload_chunk_size_bytes() % (256 * 1024):
            raise RuntimeError(
                "UPLOAD_CHUNK_SIZE_MB debe producir fragmentos múltiplos de 256 KiB"
            )
