from __future__ import annotations

import unicodedata
from time import sleep

from app.download_result import DownloadResult


PERMANENT_DOWNLOAD_ERROR_TERMS = (
    "caducad",
    "expirad",
    "ya no esta disponible",
    "no encontro la transferencia",
    "requiere una contrasena",
    "formato o tamano rechazado",
    "extension no permitida",
    "excede el tamano",
    "archivo demasiado grande",
)


def errors_are_retryable(errors):
    if not errors:
        return False

    normalized = unicodedata.normalize(
        "NFKD",
        " ".join(str(error) for error in errors),
    )
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    ).casefold()
    return not any(
        term in normalized
        for term in PERMANENT_DOWNLOAD_ERROR_TERMS
    )


def download_with_retries(
    handler,
    url,
    target_dir,
    *,
    provider,
    max_attempts,
    retry_delay_seconds,
    sleep_fn=sleep,
):
    result = None
    for attempt in range(1, max_attempts + 1):
        if max_attempts > 1:
            print(
                f"[{provider.upper()}] Intento {attempt} "
                f"de {max_attempts}"
            )

        raw_result = handler(url, target_dir)
        result = DownloadResult.from_value(
            raw_result,
            default_error="La descarga no se completó",
        )
        result.retryable = (
            not result.manual_actions
            and errors_are_retryable(result.errors)
        )

        retry_now = (
            attempt < max_attempts
            and not result.paths
            and not result.manual_actions
            and result.retryable
        )
        if not retry_now:
            if attempt > 1 and result.paths:
                print(
                    f"[{provider.upper()}] Descarga recuperada "
                    f"en el intento {attempt}"
                )
            return result

        delay = retry_delay_seconds * attempt
        print(
            f"[{provider.upper()}] Fallo transitorio; se abrirá "
            f"un navegador nuevo en {delay}s"
        )
        if delay:
            sleep_fn(delay)

    return result
