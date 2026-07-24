from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.browser_profile import (
    USER_AGENT,
    browser_context_options,
    browser_launch_arguments,
)
from app.config import Config
from app.download_result import DownloadResult
from app.downloaders.common import (
    click_if_visible,
    save_playwright_download,
)
from app.downloaders.direct import download_direct
from app.downloaders.smart_browser import try_smart_download
from app.utils import safe_error_message, url_for_log

CONSENT_SELECTORS = [
    "button:has-text('Accept all')",
    "button:has-text('Accept')",
    "button:has-text('Aceptar todo')",
    "button:has-text('Aceptar')",
    "button:has-text('I agree')",
    "button:has-text('Agree')",
    "button:has-text('Acepto')",
    "button:has-text('I accept')",
    "button:has-text('J’accepte')",
    "button:has-text('Accepter')",
]

GENERIC_DOWNLOAD_SELECTORS = [
    "a[download]",
    "a[href*='download']",
    "button:has-text('Download')",
    "button:has-text('Descargar')",
    "a:has-text('Download')",
    "a:has-text('Descargar')",
]

SELECTOR_DOWNLOAD_TIMEOUT_MS = 20_000
BROWSER_TOTAL_TIMEOUT_SECONDS = 120
MAX_REQUEST_RECORDS = 2_000
MAX_MULTI_DOWNLOAD_CONTROLS = 50


@dataclass
class HttpDownloadHandoff:
    url: str
    filename: str
    referer: str
    cookies: list[dict]
    user_agent: str
    method: str = "GET"
    request_body: str | None = None
    headers: dict | None = None


def _try_locator_download(page, locator, timeout=SELECTOR_DOWNLOAD_TIMEOUT_MS):
    with page.expect_download(timeout=timeout) as download_info:
        locator.click(timeout=10_000)
    return download_info.value


def _try_selector_download(page, selector, timeout=SELECTOR_DOWNLOAD_TIMEOUT_MS):
    locator = page.locator(selector).first
    if not locator.count() or not locator.is_visible(timeout=1500):
        return None
    return _try_locator_download(page, locator, timeout=timeout)


def _safe_request_headers(headers):
    excluded = {
        "accept-encoding",
        "connection",
        "content-length",
        "cookie",
        "host",
        "user-agent",
    }
    return {
        name: value
        for name, value in (headers or {}).items()
        if name.lower() not in excluded
        and not name.lower().startswith("sec-")
    }


def _remember_request(request, records):
    try:
        if len(records) >= MAX_REQUEST_RECORDS:
            records.pop(next(iter(records)))
        records[request.url] = {
            "method": request.method,
            "request_body": request.post_data,
            "headers": _safe_request_headers(request.headers),
        }
    except Exception:
        pass


def _create_http_handoff(
    download,
    page,
    context,
    provider,
    request_records,
    allow_http_handoff,
):
    if not Config.browser_http_handoff or not allow_http_handoff:
        return None

    download_url = download.url
    if not download_url.lower().startswith(("http://", "https://")):
        return None

    filename = download.suggested_filename or f"{provider.lower()}_download.bin"
    request_details = request_records.get(download_url, {})
    try:
        browser_user_agent = page.evaluate("() => navigator.userAgent")
    except Exception:
        browser_user_agent = USER_AGENT

    handoff = HttpDownloadHandoff(
        url=download_url,
        filename=filename,
        referer=page.url,
        cookies=context.cookies(),
        user_agent=browser_user_agent,
        method=request_details.get("method", "GET"),
        request_body=request_details.get("request_body"),
        headers=request_details.get("headers"),
    )

    # Detiene la copia administrada por Chromium antes de que un archivo grande
    # ocupe el sistema de archivos en memoria de Cloud Run.
    try:
        download.cancel()
    except Exception:
        pass

    print(
        f"[{provider}] Enlace real capturado; "
        "se cerrará Chromium y continuará por HTTP en bloques"
    )
    return handoff


def _visible_indices(root, selector):
    try:
        locator = root.locator(selector)
        count = min(locator.count(), MAX_MULTI_DOWNLOAD_CONTROLS)
    except Exception:
        return []

    indices = []
    for index in range(count):
        try:
            if locator.nth(index).is_visible(timeout=750):
                indices.append(index)
        except Exception:
            continue
    return indices


def _browser_roots(page, search_all_frames):
    if not search_all_frames:
        return [("principal", page)]

    roots = [("principal", page.main_frame)]
    for index, frame in enumerate(page.frames, 1):
        if frame == page.main_frame:
            continue
        roots.append((f"marco-{index}", frame))
    return roots


def _click_consent(page, search_all_frames):
    for _, root in _browser_roots(page, search_all_frames):
        if click_if_visible(root, CONSENT_SELECTORS):
            return True
    return False


def _wait_for_download_controls(
    page,
    selectors,
    wait_seconds,
    *,
    search_all_frames=False,
    provider="NAVEGADOR",
):
    started_at = monotonic()
    deadline = monotonic() + max(0, wait_seconds)
    next_progress_log = 15

    while True:
        _click_consent(page, search_all_frames)

        for root_name, root in _browser_roots(page, search_all_frames):
            for selector in selectors:
                indices = _visible_indices(root, selector)
                if indices:
                    return root_name, root, selector, indices

        if monotonic() >= deadline:
            return None, None, None, []

        elapsed = int(monotonic() - started_at)
        if elapsed >= next_progress_log:
            print(
                f"[{provider}] Esperando interfaz dinámica: "
                f"{elapsed}s de {wait_seconds}s"
            )
            next_progress_log += 15

        page.wait_for_timeout(1_000)


def _count_visible(root, selector, limit=100):
    try:
        locator = root.locator(selector)
        count = min(locator.count(), limit)
    except Exception:
        return 0

    visible = 0
    for index in range(count):
        try:
            if locator.nth(index).is_visible(timeout=250):
                visible += 1
        except Exception:
            continue
    return visible


def _turnstile_status(page):
    widget_count = 0
    response_found = False
    response_ready = False

    for _, root in _browser_roots(page, search_all_frames=True):
        try:
            widget_count += root.locator(
                "iframe[src*='challenges.cloudflare.com'], "
                "iframe[title*='Cloudflare']"
            ).count()
        except Exception:
            pass

        try:
            responses = root.locator(
                "input[name='cf-turnstile-response'], "
                "textarea[name='cf-turnstile-response']"
            )
            response_count = min(responses.count(), 10)
            response_found = response_found or response_count > 0
            for index in range(response_count):
                try:
                    if responses.nth(index).input_value(timeout=500).strip():
                        response_ready = True
                        break
                except Exception:
                    continue
        except Exception:
            pass

    if response_ready:
        return "completada"
    if widget_count or response_found:
        return "pendiente"
    return "no-detectada"


def _browser_diagnostics(page, context, provider):
    visible_actions = 0
    for _, root in _browser_roots(page, search_all_frames=True):
        visible_actions += _count_visible(
            root,
            "button, [role='button'], "
            "input[type='button'], input[type='submit']",
        )

    try:
        service_workers = len(context.service_workers)
    except Exception:
        service_workers = -1

    try:
        ready_state = page.evaluate("() => document.readyState")
    except Exception:
        ready_state = "desconocido"

    diagnostics = {
        "frames": len(page.frames),
        "visible_actions": visible_actions,
        "service_workers": service_workers,
        "turnstile": _turnstile_status(page),
        "ready_state": ready_state,
    }
    print(
        f"[{provider}] Diagnóstico seguro: "
        f"estado={diagnostics['ready_state']} "
        f"marcos={diagnostics['frames']} "
        f"acciones_visibles={diagnostics['visible_actions']} "
        f"service_workers={diagnostics['service_workers']} "
        f"turnstile={diagnostics['turnstile']}"
    )
    return diagnostics


def _normalized_page_text(page):
    try:
        text = page.locator("body").inner_text(timeout=3_000)
    except Exception:
        return ""

    text = unicodedata.normalize("NFKD", text[:50_000])
    return "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    ).casefold()


def _unavailable_reason(page, diagnostics=None):
    if diagnostics and diagnostics.get("turnstile") == "pendiente":
        return (
            "La validación de seguridad de Cloudflare quedó pendiente "
            "en Chromium"
        )

    text = _normalized_page_text(page)

    expired_terms = (
        "link has expired",
        "transfer has expired",
        "transfer is no longer available",
        "transferencia ha caducado",
        "transferencia ha expirado",
        "enlace ha caducado",
        "enlace ha expirado",
        "enlace caduco",
        "enlace expiro",
        "ya no esta disponible",
        "no longer available",
        "files have been deleted",
        "archivos han sido eliminados",
    )
    if any(term in text for term in expired_terms):
        return "El proveedor informa que el enlace está caducado o ya no está disponible"

    not_found_terms = (
        "transfer not found",
        "page not found",
        "404 not found",
        "transferencia no encontrada",
        "pagina no encontrada",
    )
    if any(term in text for term in not_found_terms):
        return "El proveedor no encontró la transferencia"

    password_terms = (
        "password required",
        "enter password",
        "contrasena requerida",
        "introduce la contrasena",
    )
    if any(term in text for term in password_terms):
        return "La transferencia requiere una contraseña"

    challenge_terms = (
        "checking your browser",
        "verify you are human",
        "verificando que eres humano",
        "verifica que eres humano",
    )
    if any(term in text for term in challenge_terms):
        return "La verificación de seguridad del proveedor no terminó"

    if diagnostics and diagnostics.get("visible_actions", 0) > 0:
        return (
            "La página cargó controles, pero el proveedor cambió "
            "el botón de descarga"
        )

    return "No se encontró un control que iniciara la descarga"


def _capture_download(
    download,
    *,
    page,
    context,
    provider,
    target_dir,
    request_records,
    handoffs,
    saved_paths,
    allow_http_handoff,
):
    handoff = _create_http_handoff(
        download,
        page,
        context,
        provider,
        request_records,
        allow_http_handoff,
    )
    if handoff is not None:
        handoffs.append(handoff)
        return True

    if not allow_http_handoff:
        print(
            f"[{provider}] Descarga nativa del navegador activa; "
            "se conservará la sesión validada"
        )

    saved_path = save_playwright_download(download, target_dir, provider)
    if saved_path is not None:
        saved_paths.append(saved_path)
        return True

    return False


def _close_browser_objects(page, context, browser, event_listeners):
    for owner, event_name, listener in event_listeners:
        try:
            owner.remove_listener(event_name, listener)
        except Exception:
            pass

    if page is not None:
        try:
            if not page.is_closed():
                page.close()
        except Exception:
            pass

    if context is not None:
        try:
            context.close()
        except Exception:
            pass

    if browser is not None:
        try:
            browser.close()
        except Exception:
            pass


def download_with_browser(
    url,
    target_dir,
    provider,
    download_selectors,
    *,
    download_all=False,
    wait_for_download_controls_seconds=0,
    compatibility_mode=False,
    search_all_frames=False,
    allow_http_handoff=True,
):
    browser = None
    context = None
    page = None
    event_listeners = []
    started_at = monotonic()
    handoffs = []
    saved_paths = []
    errors = []
    unavailable_reason = None
    request_records = {}

    ordered_selectors = list(
        dict.fromkeys([*download_selectors, *GENERIC_DOWNLOAD_SELECTORS])
    )

    try:
        browser_download_dir = Path(target_dir) / ".browser-downloads"
        browser_download_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(
                    headless=True,
                    downloads_path=str(browser_download_dir),
                    args=browser_launch_arguments(compatibility_mode),
                )
                context = browser.new_context(
                    **browser_context_options(compatibility_mode)
                )

                # No se interceptan recursos con context.route(). Los callbacks
                # pendientes de esa ruta eran la causa de CancelledError y
                # TargetClosedError al apagar Chromium.
                page = context.new_page()
                request_listener = lambda request: _remember_request(
                    request, request_records
                )
                # El contexto también recibe las solicitudes realizadas por un
                # Service Worker; page.on("request") no siempre las observa.
                context.on("request", request_listener)
                event_listeners.append(
                    (context, "request", request_listener)
                )
                page.set_default_timeout(10_000)
                page.set_default_navigation_timeout(90_000)

                if compatibility_mode:
                    print(
                        f"[{provider}] Modo compatible activo: "
                        "User-Agent nativo y Service Workers habilitados"
                    )

                print(f"[{provider}] Abriendo: {url_for_log(url)}")
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                page.wait_for_timeout(2_500)

                if compatibility_mode:
                    try:
                        page.wait_for_load_state(
                            "networkidle",
                            timeout=15_000,
                        )
                    except PlaywrightTimeoutError:
                        print(
                            f"[{provider}] La red sigue activa; "
                            "se continuará esperando la interfaz"
                        )

                _click_consent(page, search_all_frames)
                page.wait_for_timeout(750)

                if download_all:
                    (
                        root_name,
                        control_root,
                        selector,
                        indices,
                    ) = _wait_for_download_controls(
                        page,
                        ordered_selectors,
                        wait_for_download_controls_seconds,
                        search_all_frames=search_all_frames,
                        provider=provider,
                    )

                    if selector:
                        print(
                            f"[{provider}] Controles de descarga detectados: "
                            f"{len(indices)} ({root_name})"
                        )
                        for position, index in enumerate(indices, 1):
                            try:
                                locator = control_root.locator(selector).nth(index)
                                if not locator.is_visible(timeout=1_000):
                                    errors.append(
                                        f"Archivo {position}: el botón dejó de estar visible"
                                    )
                                    continue

                                print(
                                    f"[{provider}] Iniciando archivo "
                                    f"{position} de {len(indices)}"
                                )
                                download = _try_locator_download(page, locator)
                                if not _capture_download(
                                    download,
                                    page=page,
                                    context=context,
                                    provider=provider,
                                    target_dir=target_dir,
                                    request_records=request_records,
                                    handoffs=handoffs,
                                    saved_paths=saved_paths,
                                    allow_http_handoff=allow_http_handoff,
                                ):
                                    errors.append(
                                        f"Archivo {position}: formato o tamaño rechazado"
                                    )
                            except PlaywrightTimeoutError:
                                errors.append(
                                    f"Archivo {position}: el botón no inició la descarga"
                                )
                            except Exception as exc:
                                errors.append(
                                    f"Archivo {position}: {safe_error_message(exc)}"
                                )
                    else:
                        diagnostics = _browser_diagnostics(
                            page,
                            context,
                            provider,
                        )
                        unavailable_reason = _unavailable_reason(
                            page,
                            diagnostics,
                        )
                else:
                    for selector in ordered_selectors:
                        elapsed = monotonic() - started_at
                        if elapsed >= BROWSER_TOTAL_TIMEOUT_SECONDS:
                            print(
                                f"[{provider}] Tiempo máximo del navegador alcanzado "
                                f"({BROWSER_TOTAL_TIMEOUT_SECONDS}s)"
                            )
                            break

                        try:
                            print(f"[{provider}] Probando selector: {selector}")
                            download = _try_selector_download(page, selector)
                            if download:
                                _capture_download(
                                    download,
                                    page=page,
                                    context=context,
                                    provider=provider,
                                    target_dir=target_dir,
                                    request_records=request_records,
                                    handoffs=handoffs,
                                    saved_paths=saved_paths,
                                    allow_http_handoff=allow_http_handoff,
                                )
                                break
                        except PlaywrightTimeoutError:
                            print(
                                f"[{provider}] El selector no inició una descarga "
                                f"en {SELECTOR_DOWNLOAD_TIMEOUT_MS // 1000}s: {selector}"
                            )
                            continue
                        except Exception as exc:
                            print(
                                f"[{provider}] Selector descartado: {selector} "
                                f"({safe_error_message(exc)})"
                            )
                            continue

                    if not handoffs and not saved_paths:
                        remaining = max(
                            0,
                            int(
                                BROWSER_TOTAL_TIMEOUT_SECONDS
                                - (monotonic() - started_at)
                            ),
                        )
                        if remaining <= 0:
                            print(
                                f"[{provider}] Sin tiempo restante para Smart Browser"
                            )
                        else:
                            print(f"[{provider}] Iniciando Smart Browser...")
                            download = try_smart_download(
                                page,
                                provider,
                                download_selectors,
                                max_seconds=min(30, remaining),
                            )
                            if download:
                                _capture_download(
                                    download,
                                    page=page,
                                    context=context,
                                    provider=provider,
                                    target_dir=target_dir,
                                    request_records=request_records,
                                    handoffs=handoffs,
                                    saved_paths=saved_paths,
                                    allow_http_handoff=allow_http_handoff,
                                )

                    if not handoffs and not saved_paths:
                        diagnostics = _browser_diagnostics(
                            page,
                            context,
                            provider,
                        )
                        unavailable_reason = _unavailable_reason(
                            page,
                            diagnostics,
                        )
            finally:
                # El cierre ocurre antes de salir de sync_playwright(), cuando
                # el canal del navegador todavía está activo.
                _close_browser_objects(
                    page,
                    context,
                    browser,
                    event_listeners,
                )
                page = None
                context = None
                browser = None

    except Exception as exc:
        errors.append(safe_error_message(exc))

    # Con Chromium ya cerrado, las descargas grandes continúan una por una por
    # HTTP en bloques sobre el volumen de Cloud Storage.
    for handoff in handoffs:
        path = download_direct(
            handoff.url,
            target_dir,
            method=handoff.method,
            request_body=handoff.request_body,
            extra_headers={
                **(handoff.headers or {}),
                "Referer": handoff.referer,
                "User-Agent": handoff.user_agent,
            },
            cookies=handoff.cookies,
            filename_hint=handoff.filename,
            provider=provider,
        )
        if path is not None:
            saved_paths.append(path)
        else:
            errors.append(
                f"No se pudo completar el archivo {handoff.filename}"
            )

    if not saved_paths and not errors:
        errors.append(
            unavailable_reason
            or "No se encontró un control que iniciara la descarga"
        )

    if unavailable_reason and not saved_paths and unavailable_reason not in errors:
        errors.append(unavailable_reason)

    if errors:
        for error in errors:
            print(f"[{provider}] {error}")

    return DownloadResult(paths=saved_paths, errors=errors)
