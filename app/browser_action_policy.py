import re
import unicodedata
from urllib.parse import urlparse


BLOCKED_ACTION_DOMAINS = {
    "adservice.google.com",
    "doubleclick.net",
    "google.com",
    "googlesyndication.com",
}

# Controles de registro, planes pagados y promociones. Aunque una URL
# comercial contenga la palabra "download", nunca debe recibir un clic del
# navegador automático.
HARD_BLOCKED_ACTION_WORDS = (
    "se ultimate",
    "go ultimate",
    "ultimate now",
    "upgrade",
    "create account",
    "create your account",
    "crea tu cuenta",
    "sign up",
    "register",
    "registrate",
    "iniciar sesion",
)

HARD_BLOCKED_URL_PARTS = (
    "/sign-up",
    "/signup",
    "/register",
    "/registration",
    "/login",
    "/pricing",
    "/plans",
    "/upgrade",
    "/ultimate",
)


def normalized_action_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    ).casefold()
    return re.sub(r"\s+", " ", text).strip()


def action_location_is_blocked(url):
    try:
        parsed = urlparse(str(url or ""))
        host = (parsed.hostname or "").casefold()
        path = normalized_action_text(
            f"{parsed.path} {parsed.query} {parsed.fragment}"
        )
    except Exception:
        host = ""
        path = normalized_action_text(url)

    if any(
        host == domain or host.endswith(f".{domain}")
        for domain in BLOCKED_ACTION_DOMAINS
    ):
        return True
    return any(part in path for part in HARD_BLOCKED_URL_PARTS)


def action_metadata_is_blocked(metadata):
    fields = normalized_action_text(
        " ".join(
            str(metadata.get(name, ""))
            for name in (
                "text",
                "aria",
                "title",
                "testid",
                "role",
                "type",
                "name",
                "className",
            )
        )
    )
    if any(word in fields for word in HARD_BLOCKED_ACTION_WORDS):
        return True
    return action_location_is_blocked(metadata.get("href", ""))
