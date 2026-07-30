from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlsplit


BLOCKED_RESPONSE_DOMAINS = {
    "adservice.google.com",
    "doubleclick.net",
    "google-analytics.com",
    "googlesyndication.com",
    "googletagmanager.com",
    "tagging.wetransfer.com",
}

BLOCKED_WEB_ASSET_SUFFIXES = {
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}

BLOCKED_WEB_ASSET_TERMS = (
    "analytics",
    "cookie",
    "favicon",
    "icon",
    "logo",
    "onetrust",
    "ot_guard",
    "pixel",
    "tagging",
    "tracking",
)

STRONG_FILE_TYPES = (
    "application/illustrator",
    "application/pdf",
    "application/postscript",
    "application/x-7z",
    "application/x-rar",
    "application/x-zip",
    "application/zip",
    "image/tiff",
    "image/vnd.adobe.photoshop",
)


def _domain_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")


def browser_file_response_score(
    url: str,
    headers: dict,
    resource_type: str,
    allowed_extensions: set[str],
) -> int | None:
    """
    Puntúa únicamente respuestas con evidencia de ser el archivo transferido.

    Un nombre con ``download`` o una extensión de imagen no basta: sitios como
    WeTransfer cargan logos, píxeles y endpoints de analítica durante la visita.
    """

    normalized_headers = {
        str(name).casefold(): str(value)
        for name, value in (headers or {}).items()
    }
    content_type = normalized_headers.get("content-type", "").casefold()
    disposition = normalized_headers.get(
        "content-disposition",
        "",
    ).casefold()
    parts = urlsplit(url)
    host = (parts.hostname or "").casefold()
    path_lower = (parts.path or "").casefold()
    suffix = PurePosixPath(parts.path or "").suffix.casefold()

    blocked_types = (
        "application/json",
        "font/",
        "javascript",
        "text/css",
        "text/html",
    )
    if any(item in content_type for item in blocked_types):
        return None

    if any(
        _domain_matches(host, blocked_domain)
        for blocked_domain in BLOCKED_RESPONSE_DOMAINS
    ):
        return None

    attachment = "attachment" in disposition
    if attachment:
        return 100

    # Sin Content-Disposition, los recursos web decorativos nunca deben
    # convertirse en archivos del trabajo, aunque .png/.svg estén permitidos.
    if (
        suffix in BLOCKED_WEB_ASSET_SUFFIXES
        or any(term in path_lower for term in BLOCKED_WEB_ASSET_TERMS)
    ):
        return None

    if any(item in content_type for item in STRONG_FILE_TYPES):
        return 90

    url_lower = url.casefold()
    download_hint = "download" in url_lower or "descarg" in url_lower
    allowed_suffix = bool(suffix) and suffix in allowed_extensions
    eligible_resource = resource_type in {
        "document",
        "fetch",
        "xhr",
        "other",
    }

    if (
        "application/octet-stream" in content_type
        and eligible_resource
        and (download_hint or allowed_suffix)
    ):
        return 80

    if (
        allowed_suffix
        and suffix not in BLOCKED_WEB_ASSET_SUFFIXES
        and eligible_resource
    ):
        return 60

    return None


def best_file_response(records):
    """Elige la evidencia más fuerte; en empate prefiere la más reciente."""

    values = list(records)
    if not values:
        return None
    return max(
        enumerate(values),
        key=lambda item: (item[1].get("score", 0), item[0]),
    )[1]
