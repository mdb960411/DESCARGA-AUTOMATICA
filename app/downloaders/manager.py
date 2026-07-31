from __future__ import annotations

from time import sleep
from urllib.parse import urlparse

from app.config import Config
from app.download_result import DownloadResult
from app.failure_policy import failure_is_permanent
from app.downloaders.direct import download_direct
from app.downloaders.drive import download_drive
from app.downloaders.providers import (
    download_sendallfiles,
    download_sendgb,
    download_swisstransfer,
    download_transfernow,
    download_wetransfer,
)
from app.utils import url_for_log

BROWSER_PROVIDERS = {
    "wetransfer",
    "transfernow",
    "sendallfiles",
    "sendgb",
    "swisstransfer",
}

def provider_for(url):
    host = (urlparse(url).hostname or "").lower()
    if host == "we.tl" or host.endswith("wetransfer.com"):
        return "wetransfer"
    if host.endswith("transfernow.net"):
        return "transfernow"
    if host.endswith("sendallfiles.com"):
        return "sendallfiles"
    if host.endswith("sendgb.com"):
        return "sendgb"
    if host.endswith("swisstransfer.com"):
        return "swisstransfer"
    if host == "drive.google.com":
        return "drive"
    return "direct"


def download_url(url, target_dir):
    provider = provider_for(url)
    print(f"[ENLACE] Proveedor={provider} URL={url_for_log(url)}")

    handlers = {
        "wetransfer": download_wetransfer,
        "transfernow": download_transfernow,
        "sendallfiles": download_sendallfiles,
        "sendgb": download_sendgb,
        "swisstransfer": download_swisstransfer,
        "drive": download_drive,
        "direct": download_direct,
    }
    attempts = (
        Config.browser_provider_attempts
        if provider in BROWSER_PROVIDERS
        else 1
    )
    result = None
    for attempt in range(1, attempts + 1):
        if attempts > 1:
            print(f"[{provider.upper()}] Intento {attempt} de {attempts}")

        raw_result = handlers[provider](url, target_dir)
        result = DownloadResult.from_value(
            raw_result,
            default_error="La descarga no se completó",
        )

        # Nunca se repite un enlace que ya produjo archivos: evita descargas
        # duplicadas y conserva correctamente los resultados parciales.
        if result.paths or result.manual_actions:
            return result

        permanent_failure = failure_is_permanent(result.errors)
        if permanent_failure or attempt >= attempts:
            return result

        delay = Config.browser_retry_delay_seconds * attempt
        print(
            f"[{provider.upper()}] Fallo transitorio; "
            f"se conservará el perfil y se reintentará en {delay}s"
        )
        if delay:
            sleep(delay)

    return result or DownloadResult(
        errors=["La descarga no se completó"]
    )
