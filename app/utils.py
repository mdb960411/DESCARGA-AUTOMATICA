import base64
import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def decode_base64url(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def safe_filename(name):
    clean = unquote(name or "").strip()
    clean = re.sub(r'[\\/*?:"<>|]+', "_", clean).replace("\r", "").replace("\n", "")
    return clean[:180] or "archivo"


def unique_path(path):
    if not path.exists():
        return path
    for i in range(2, 10000):
        candidate = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("No fue posible generar nombre único")


def extension_allowed(filename, allowed):
    return not allowed or Path(filename).suffix.lower() in allowed


def url_for_log(url):
    """
    Evita publicar en Cloud Logging el token completo de un enlace de descarga.
    """
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or "sin-dominio"
        digest = hashlib.sha256(url.encode("utf-8", errors="ignore")).hexdigest()[:10]
        return f"{parsed.scheme or 'https'}://{host}/[enlace-{digest}]"
    except Exception:
        return "[enlace-no-disponible]"


def safe_error_message(error):
    text = str(error)
    text = re.sub(
        r"https?://[^\s<>\"]+",
        "[URL-protegida]",
        text,
        flags=re.IGNORECASE,
    )
    return text[:1000]
