from urllib.parse import urlsplit


def canonical_link_key(url):
    """
    Agrupa variantes que representan la misma transferencia.

    WeTransfer suele incluir en un correo varias rutas para el mismo envío:
    una general, otras por archivo y versiones con seguimiento.
    """

    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    segments = [
        segment
        for segment in (parts.path or "").split("/")
        if segment
    ]

    if host == "we.tl" and segments:
        return ("wetransfer-short", segments[0])

    if (
        host.endswith("wetransfer.com")
        and len(segments) >= 3
        and segments[0].lower() == "downloads"
    ):
        return (
            "wetransfer",
            segments[1].lower(),
            segments[2].lower(),
        )

    return ("url", url)
