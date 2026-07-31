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
    ignored_label = os.getenv("IGNORED_LABEL", "Descarga-Automatica-Ignorado")
    manual_label = os.getenv("MANUAL_LABEL", "Descarga-Automatica-Manual")
    retry_label = os.getenv("RETRY_LABEL", "Descarga-Automatica-Reintento")
    only_from = os.getenv("ONLY_FROM", "").strip().lower()
    only_from_domain = os.getenv("ONLY_FROM_DOMAIN", "").strip().lower()
    keyword = os.getenv("KEYWORD", "").strip().lower()
    max_emails = env_int("MAX_EMAILS", 20)
    drive_folder_id = os.getenv("DRIVE_FOLDER_ID", "").strip()
    download_dir = Path(os.getenv("DOWNLOAD_DIR", "/tmp/descargas"))
    google_oauth_token_json = os.getenv("GOOGLE_OAUTH_TOKEN_JSON", "").strip()
    google_client_secret_json = os.getenv("GOOGLE_CLIENT_SECRET_JSON", "").strip()
    _google_oauth_token_file_raw = os.getenv(
        "GOOGLE_OAUTH_TOKEN_FILE", ""
    ).strip()
    google_oauth_token_file = (
        Path(_google_oauth_token_file_raw)
        if _google_oauth_token_file_raw
        else None
    )
    _google_client_secret_file_raw = os.getenv(
        "GOOGLE_CLIENT_SECRET_FILE", ""
    ).strip()
    google_client_secret_file = (
        Path(_google_client_secret_file_raw)
        if _google_client_secret_file_raw
        else None
    )
    _browser_profile_dir_raw = os.getenv("BROWSER_PROFILE_DIR", "").strip()
    browser_profile_dir = (
        Path(_browser_profile_dir_raw)
        if _browser_profile_dir_raw
        else None
    )
    state_dir = Path(
        os.getenv("STATE_DIR", "/tmp/gmail-downloader-state")
    )
    browser_headless = env_bool("BROWSER_HEADLESS", True)
    browser_diagnostics = env_bool("BROWSER_DIAGNOSTICS", True)
    enable_sendgb = env_bool("ENABLE_SENDGB", True)
    mark_as_read = env_bool("MARK_AS_READ", True)
    exclude_error_messages = env_bool("EXCLUDE_ERROR_MESSAGES", True)
    exclude_ignored_messages = env_bool("EXCLUDE_IGNORED_MESSAGES", True)
    exclude_manual_messages = env_bool("EXCLUDE_MANUAL_MESSAGES", True)
    browser_http_handoff = env_bool("BROWSER_HTTP_HANDOFF", True)
    browser_action_diagnostics = env_bool(
        "BROWSER_ACTION_DIAGNOSTICS",
        True,
    )
    max_file_size_mb = env_int("MAX_FILE_SIZE_MB", 8192)
    download_chunk_size_mb = env_int("DOWNLOAD_CHUNK_SIZE_MB", 4)
    upload_chunk_size_mb = env_int("UPLOAD_CHUNK_SIZE_MB", 8)
    upload_retries = env_int("UPLOAD_RETRIES", 3)
    download_timeout_seconds = env_int("DOWNLOAD_TIMEOUT_SECONDS", 1800)
    browser_provider_attempts = env_int("BROWSER_PROVIDER_ATTEMPTS", 2)
    browser_retry_delay_seconds = env_int(
        "BROWSER_RETRY_DELAY_SECONDS", 3
    )
    max_message_attempts = env_int("MAX_MESSAGE_ATTEMPTS", 5)
    stale_run_hours = env_int("STALE_RUN_HOURS", 24)
    max_diagnostic_files = env_int("MAX_DIAGNOSTIC_FILES", 20)

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
        if not cls.google_oauth_token_json and not cls.google_oauth_token_file:
            missing.append(
                "GOOGLE_OAUTH_TOKEN_JSON o GOOGLE_OAUTH_TOKEN_FILE"
            )
        if (
            not cls.google_client_secret_json
            and not cls.google_client_secret_file
        ):
            missing.append(
                "GOOGLE_CLIENT_SECRET_JSON o GOOGLE_CLIENT_SECRET_FILE"
            )
        if not cls.drive_folder_id:
            missing.append("DRIVE_FOLDER_ID")
        if missing:
            raise RuntimeError("Faltan variables obligatorias: " + ", ".join(missing))

        for name, path in (
            ("GOOGLE_OAUTH_TOKEN_FILE", cls.google_oauth_token_file),
            ("GOOGLE_CLIENT_SECRET_FILE", cls.google_client_secret_file),
        ):
            if path is not None and not path.is_file():
                raise RuntimeError(f"{name} no existe o no es un archivo")

        positive_values = [
            ("MAX_EMAILS", cls.max_emails),
            ("MAX_FILE_SIZE_MB", cls.max_file_size_mb),
            ("DOWNLOAD_CHUNK_SIZE_MB", cls.download_chunk_size_mb),
            ("UPLOAD_CHUNK_SIZE_MB", cls.upload_chunk_size_mb),
            ("DOWNLOAD_TIMEOUT_SECONDS", cls.download_timeout_seconds),
            ("BROWSER_PROVIDER_ATTEMPTS", cls.browser_provider_attempts),
            ("MAX_MESSAGE_ATTEMPTS", cls.max_message_attempts),
            ("MAX_DIAGNOSTIC_FILES", cls.max_diagnostic_files),
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

        non_negative_values = [
            ("BROWSER_RETRY_DELAY_SECONDS", cls.browser_retry_delay_seconds),
            ("STALE_RUN_HOURS", cls.stale_run_hours),
        ]
        invalid = [
            name for name, value in non_negative_values if value < 0
        ]
        if invalid:
            raise RuntimeError(
                "Estas variables no pueden ser negativas: "
                + ", ".join(invalid)
            )
