PERMANENT_FAILURE_MARKERS = (
    "caducad",
    "expirad",
    "ya no está disponible",
    "no longer available",
    "transfer deleted",
    "archivo eliminado",
    "http 404",
    "http 410",
)


def failure_is_permanent(errors):
    combined = " ".join(str(error) for error in errors).casefold()
    return any(marker in combined for marker in PERMANENT_FAILURE_MARKERS)
