from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.config import Config
from app.download_result import DownloadResult
from app.downloaders.common import (
    USER_AGENT,
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
):
    if not Config.browser_http_handoff:
        return None

    download_url = download.url
    if not download_url.lower().startswith(("http://", "https://")):
        return None

    filename = download.suggested_filename or f"{provider.lower()}_download.bin"
    request_details = request_records.get(download_url, {})
    handoff = HttpDownloadHandoff(
        url=download_url,
        filename=filename,
        referer=page.url,
        cookies=context.cookies(),
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


def _visible_indices(page, selector):
    try:
        locator = page.locator(selector)
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


def _wait_for_download_controls(page, selectors, wait_seconds):
    deadline = monotonic() + max(0, wait_seconds)

    while True:
        click_if_visible(page, CONSENT_SELECTORS)

        for selector in selectors:
            indices = _visible_indices(page, selector)
            if indices:
                return selector, indices

        if monotonic() >= deadline:
            return None, []

        page.wait_for_timeout(1_000)


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


def _unavailable_reason(page):
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
):
    handoff = _create_http_handoff(
        download,
        page,
        context,
        provider,
        request_records,
    )
    if handoff is not None:
        handoffs.append(handoff)
        return True

    saved_path = save_playwright_download(download, target_dir, provider)
    if saved_path is not None:
        saved_paths.append(saved_path)
        return True

    return False


def _close_browser_objects(page, context, browser, request_listener):
    if page is not None and request_listener is not None:
        try:
            page.remove_listener("request", request_listener)
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
):
    browser = None
    context = None
    page = None
    request_listener = None
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
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-gpu",
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
                        "--mute-audio",
                    ],
                )
                context = browser.new_context(
                    accept_downloads=True,
                    user_agent=USER_AGENT,
                    viewport={"width": 1280, "height": 800},
                    locale="es-CL",
                    timezone_id="America/Santiago",
                    service_workers="block",
                )

                # No se interceptan recursos con context.route(). Los callbacks
                # pendientes de esa ruta eran la causa de CancelledError y
                # TargetClosedError al apagar Chromium.
                page = context.new_page()
                request_listener = lambda request: _remember_request(
                    request, request_records
                )
                page.on("request", request_listener)
                page.set_default_timeout(10_000)
                page.set_default_navigation_timeout(90_000)

                print(f"[{provider}] Abriendo: {url_for_log(url)}")
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                page.wait_for_timeout(2_500)

                click_if_visible(page, CONSENT_SELECTORS)
                page.wait_for_timeout(750)

                if download_all:
                    selector, indices = _wait_for_download_controls(
                        page,
                        ordered_selectors,
                        wait_for_download_controls_seconds,
                    )

                    if selector:
                        print(
                            f"[{provider}] Controles de descarga detectados: "
                            f"{len(indices)}"
                        )
                        for position, index in enumerate(indices, 1):
                            try:
                                locator = page.locator(selector).nth(index)
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
                        unavailable_reason = _unavailable_reason(page)
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
                                )

                    if not handoffs and not saved_paths:
                        unavailable_reason = _unavailable_reason(page)
            finally:
                # El cierre ocurre antes de salir de sync_playwright(), cuando
                # el canal del navegador todavía está activo.
                _close_browser_objects(
                    page,
                    context,
                    browser,
                    request_listener,
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
