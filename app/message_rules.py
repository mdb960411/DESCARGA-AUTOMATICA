from __future__ import annotations

import unicodedata


def _normalized_text(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return normalized.casefold()


def is_sender_confirmation(sender, subject):
    sender = str(sender or "").casefold()
    subject = _normalized_text(subject)

    if sender.endswith("@transfernow.net"):
        return any(
            phrase in subject
            for phrase in (
                "se ha enviado con exito a",
                "has been sent successfully to",
                "your transfer was sent successfully",
            )
        )
    return False


def retry_label_names(base_label, max_runs):
    return [
        f"{base_label}-{attempt}"
        for attempt in range(1, max_runs)
    ]
