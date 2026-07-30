from __future__ import annotations

import unicodedata
from urllib.parse import urlsplit


MARKETING_LABEL_TERMS = (
    "se ultimate",
    "be ultimate",
    "hazte ultimate",
    "obten ultimate",
    "get ultimate",
    "actualizar plan",
    "upgrade plan",
    "ver planes",
    "view plans",
    "start free trial",
    "iniciar prueba gratuita",
)

MARKETING_PATH_TERMS = (
    "/ultimate",
    "/pricing",
    "/plans",
    "/upgrade",
)


def normalized_action_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    return " ".join(text.casefold().split())


def is_marketing_action(label="", href=""):
    normalized_label = normalized_action_text(label)
    if any(
        term in normalized_label
        for term in MARKETING_LABEL_TERMS
    ):
        return True

    try:
        path = urlsplit(str(href or "")).path.casefold()
    except ValueError:
        path = ""
    return any(term in path for term in MARKETING_PATH_TERMS)
