from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


BLOCKED_EXTENSIONS = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".png",
    ".svg",
    ".webp",
    ".woff",
    ".woff2",
}

BLOCKED_DOMAINS = {
    "backgrounds.wetransfer.net",
    "email.wetransfer.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "mail.storage.infomaniak.com",
    "infomaniak.com",
    "news.infomaniak.com",
    "support.infomaniak.com",
    "u922094.ct.sendgrid.net",
    "www.w3.org",
}

BLOCKED_KEYWORDS = {
    "about",
    "banner",
    "cookie",
    "faq",
    "font",
    "logo",
    "pixel",
    "privacy",
    "report_abuse",
    "support",
    "terms",
    "tracking",
    "unsubscribe",
}


def normalize_domain(url: str) -> str:
    """
    Retorna el dominio del enlace en minúsculas y sin puerto.
    """
    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower().strip()

    if domain.startswith("www."):
        domain_without_www = domain[4:]
        if domain_without_www in BLOCKED_DOMAINS:
            return domain_without_www

    return domain


def has_blocked_extension(url: str) -> bool:
    """
    Comprueba si la ruta del enlace termina en una extensión decorativa
    o propia de recursos web.
    """
    parsed = urlparse(url)
    extension = Path(parsed.path).suffix.lower()

    return extension in BLOCKED_EXTENSIONS


def has_blocked_domain(url: str) -> bool:
    """
    Comprueba si el dominio pertenece a recursos decorativos,
    seguimiento, fuentes o documentación técnica.
    """
    domain = normalize_domain(url)

    return any(
        domain == blocked_domain
        or domain.endswith(f".{blocked_domain}")
        for blocked_domain in BLOCKED_DOMAINS
    )


def has_blocked_keyword(url: str) -> bool:
    """
    Comprueba palabras típicas de enlaces que no contienen archivos
    enviados por el usuario.
    """
    normalized_url = url.lower()

    return any(keyword in normalized_url for keyword in BLOCKED_KEYWORDS)


def should_ignore_url(url: str) -> tuple[bool, str]:
    """
    Determina si un enlace debe ignorarse.

    Retorna:
        (True, motivo) si debe ignorarse.
        (False, "") si puede continuar al descargador.
    """
    if not url:
        return True, "URL vacía"

    if not url.startswith(("http://", "https://")):
        return True, "Protocolo no permitido"

    if has_blocked_domain(url):
        return True, "Dominio bloqueado"

    if has_blocked_extension(url):
        return True, "Extensión bloqueada"

    if has_blocked_keyword(url):
        return True, "Palabra bloqueada"

    return False, ""
