from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.config import Config
from app.downloaders.common import USER_AGENT, click_if_visible, save_playwright_download
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
BROWSER_TOTAL_TIMEOUT_SECONDS = 90

BLOCKED_HOST_TERMS = (
    "adservice",
    "doubleclick",
    "facebook.net",
    "google-analytics",
    "googlesyndication",
    "googletagmanager",
    "hotjar",
)


@dataclass
class HttpDownloadHandoff:
    url: str
    filename: str
    referer: str
    cookies: list[dict]
    method: str = "GET"
    request_body: str | None = None
    headers: dict | None = None


def _block_heavy_resources(route, request):
    host = (urlsplit(request.url).hostname or "").lower()
    blocked_host = any(term in host for term in BLOCKED_HOST_TERMS)

    if blocked_host or request.resource_type in {"image", "media", "font"}:
        route.abort()
    else:
        route.continue_()


def _try_selector_download(page, selector, timeout=SELECTOR_DOWNLOAD_TIMEOUT_MS):
    locator = page.locator(selector).first
    if not locator.count() or not locator.is_visible(timeout=1500):
        return None

    with page.expect_download(timeout=timeout) as download_info:
        locator.click(timeout=10_000)
    return download_info.value


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


def download_with_browser(url, target_dir, provider, download_selectors):
    browser = None
    context = None
    started_at = monotonic()
    handoff = None
    saved_path = None
    request_records = {}

    try:
        browser_download_dir = Path(target_dir) / ".browser-downloads"
        browser_download_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
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
                service_workers="block",
            )
            context.route("**/*", _block_heavy_resources)

            page = context.new_page()
            page.on(
                "request",
                lambda request: _remember_request(
                    request, request_records
                ),
            )
            page.set_default_timeout(10_000)
            page.set_default_navigation_timeout(90_000)

            print(f"[{provider}] Abriendo: {url_for_log(url)}")
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(2500)

            click_if_visible(page, CONSENT_SELECTORS)
            page.wait_for_timeout(750)

            ordered_selectors = list(
                dict.fromkeys([*download_selectors, *GENERIC_DOWNLOAD_SELECTORS])
            )

            for selector in ordered_selectors:
                elapsed = monotonic() - started_at
                if elapsed >= BROWSER_TOTAL_TIMEOUT_SECONDS:
                    print(
                        f"[{provider}] Tiempo maximo del navegador alcanzado "
                        f"({BROWSER_TOTAL_TIMEOUT_SECONDS}s)"
                    )
                    break

                try:
                    print(f"[{provider}] Probando selector: {selector}")
                    download = _try_selector_download(page, selector)
                    if download:
                        handoff = _create_http_handoff(
                            download,
                            page,
                            context,
                            provider,
                            request_records,
                        )
                        if handoff is None:
                            saved_path = save_playwright_download(
                                download, target_dir, provider
                            )
                        break
                except PlaywrightTimeoutError:
                    print(
                        f"[{provider}] El selector no inicio una descarga "
                        f"en {SELECTOR_DOWNLOAD_TIMEOUT_MS // 1000}s: {selector}"
                    )
                    continue
                except Exception as exc:
                    print(
                        f"[{provider}] Selector descartado: {selector} "
                        f"({safe_error_message(exc)})"
                    )
                    continue

            if handoff is None and saved_path is None:
                remaining = max(
                    0,
                    int(BROWSER_TOTAL_TIMEOUT_SECONDS - (monotonic() - started_at)),
                )
                if remaining <= 0:
                    print(f"[{provider}] Sin tiempo restante para Smart Browser")
                else:
                    print(f"[{provider}] Iniciando Smart Browser...")
                    download = try_smart_download(
                        page,
                        provider,
                        download_selectors,
                        max_seconds=min(30, remaining),
                    )
                    if download:
                        handoff = _create_http_handoff(
                            download,
                            page,
                            context,
                            provider,
                            request_records,
                        )
                        if handoff is None:
                            saved_path = save_playwright_download(
                                download, target_dir, provider
                            )

            if handoff is None and saved_path is None:
                print(
                    f"[{provider}] No se encontró un botón que iniciara descarga"
                )

    except Exception as exc:
        print(f"[{provider}] Error: {safe_error_message(exc)}")

    finally:
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

    if handoff is not None:
        return download_direct(
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

    return saved_path
