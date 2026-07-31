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

WETRANSFER_BROWSER_OPTIONS = {
    "wait_for_download_controls_seconds": 30,
    "headed_mode": True,
    "compatibility_mode": True,
    "native_user_agent": True,
    "allow_service_workers": True,
    "search_all_frames": True,
    "browser_total_timeout_seconds": 100,
    "smart_browser_max_seconds": 30,
    "smart_browser_max_stages": 5,
    "smart_browser_stage_settle_ms": 1_000,
    "async_download_grace_seconds": 3,
}

SENDALLFILES_BROWSER_OPTIONS = {
    "wait_for_download_controls_seconds": 30,
    "headed_mode": True,
    "compatibility_mode": True,
    "search_all_frames": True,
    # Conserva la sesión validada por Cloudflare mientras Chromium escribe
    # directamente en el volumen externo montado.
    "allow_http_handoff": False,
    # Turnstile puede completarse automáticamente en una sesión nueva.
    # Un estado pendiente es transitorio, no una exigencia humana.
    "manual_on_pending_challenge": False,
}


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


def browser_context_options(
    compatibility_mode=False,
    *,
    native_user_agent=False,
    allow_service_workers=False,
):
    options = {
        "accept_downloads": True,
        "viewport": {"width": 1280, "height": 800},
        "locale": "es-CL",
        "timezone_id": "America/Santiago",
    }

    if compatibility_mode or allow_service_workers:
        options["service_workers"] = "allow"
    else:
        options["service_workers"] = "block"

    if compatibility_mode or native_user_agent:
        # Usa el User-Agent real del Chromium incluido en la imagen y permite
        # que los proveedores modernos no reciban una versión de Chrome fija.
        pass
    else:
        options["user_agent"] = USER_AGENT

    return options
