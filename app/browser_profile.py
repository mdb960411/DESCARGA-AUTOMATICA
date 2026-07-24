USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

BASE_LAUNCH_ARGUMENTS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--mute-audio",
]

OPTIMIZED_LAUNCH_ARGUMENTS = [
    "--disable-extensions",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-breakpad",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-features=Translate,BackForwardCache,AcceptCHFrame",
    "--disable-hang-monitor",
    "--no-first-run",
    "--no-default-browser-check",
    "--renderer-process-limit=2",
    "--js-flags=--max-old-space-size=192",
]


def browser_launch_arguments(compatibility_mode=False):
    """
    En modo compatible se conservan las funciones normales de Chromium.

    El perfil optimizado sigue disponible para proveedores que ya funcionan y
    donde reducir procesos ayuda a mantener bajo el uso de memoria.
    """

    arguments = list(BASE_LAUNCH_ARGUMENTS)
    if not compatibility_mode:
        arguments.extend(OPTIMIZED_LAUNCH_ARGUMENTS)
    return arguments


def browser_context_options(compatibility_mode=False):
    options = {
        "accept_downloads": True,
        "viewport": {"width": 1280, "height": 800},
        "locale": "es-CL",
        "timezone_id": "America/Santiago",
    }

    if compatibility_mode:
        # Usa el User-Agent real del Chromium incluido en la imagen y permite
        # que la aplicación web registre y utilice sus Service Workers.
        options["service_workers"] = "allow"
    else:
        options["user_agent"] = USER_AGENT
        options["service_workers"] = "block"

    return options
