from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlsplit


BLOCKED_DIRECT_DOMAINS = {
    "accounts.google.com",
    "myaccount.google.com",
    "notifications.googleapis.com",
    "support.google.com",
    "g.co",
    "googleusercontent.com",
}

BLOCKED_PATH_TERMS = (
    "unsubscribe",
    "notification-settings",
    "help-center",
    "/legal/",
    "/terms",
    "/privacy",
    "user-reports",
    "/contact",
)


def _domain_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")


def is_useful_email_link(
    url: str,
    allowed_extensions: set[str],
    *,
    explicit_download: bool = False,
) -> bool:
    """
    Conserva transferencias conocidas y enlaces directos con evidencia clara.

    Los correos HTML incluyen píxeles, logos y enlaces de navegación. No se
    envía una URL desconocida al descargador solo por aparecer dentro del HTML.
    """

    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    path_lower = path.casefold()

    if host == "we.tl":
        return path.startswith("/t-")
    if host.endswith("wetransfer.com"):
        return path.startswith("/downloads/")
    if host.endswith("sendgb.com"):
        blocked_prefixes = (
            "/images/",
            "/css/",
            "/js/",
            "/assets/",
        )
        return (
            path.strip("/") != ""
            and not path_lower.startswith(blocked_prefixes)
        )
    if host.endswith("sendallfiles.com"):
        return "/d/" in path
    if host.endswith("transfernow.net"):
        return path.startswith("/dl/")
    if host.endswith("swisstransfer.com"):
        return path.startswith("/d/")

    if host == "drive.google.com":
        return any(
            token in url
            for token in ("/file/d/", "open?id=", "uc?")
        )

    if any(
        _domain_matches(host, blocked_domain)
        for blocked_domain in BLOCKED_DIRECT_DOMAINS
    ):
        return False

    if any(term in path_lower for term in BLOCKED_PATH_TERMS):
        return False

    suffix = PurePosixPath(path).suffix.casefold()
    if suffix and suffix in allowed_extensions:
        return True

    # Un botón o enlace rotulado explícitamente como descarga puede apuntar a
    # un endpoint sin extensión que entrega Content-Disposition: attachment.
    return explicit_download
