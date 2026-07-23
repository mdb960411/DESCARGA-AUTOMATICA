from __future__ import annotations

from time import monotonic

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.downloaders.common import USER_AGENT, click_if_visible, save_playwright_download
from app.downloaders.smart_browser import try_smart_download

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


def _block_heavy_resources(route, request):
    if request.resource_type in {"image", "media", "font"}:
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


def download_with_browser(url, target_dir, provider, download_selectors):
    browser = None
    context = None
    started_at = monotonic()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-background-networking",
                    "--no-first-run",
                    "--no-default-browser-check",
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
            page.set_default_timeout(10_000)
            page.set_default_navigation_timeout(90_000)

            print(f"[{provider}] Abriendo: {url}")
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
                    return None

                try:
                    print(f"[{provider}] Probando selector: {selector}")
                    download = _try_selector_download(page, selector)
                    if download:
                        return save_playwright_download(download, target_dir, provider)
                except PlaywrightTimeoutError:
                    print(
                        f"[{provider}] El selector no inicio una descarga "
                        f"en {SELECTOR_DOWNLOAD_TIMEOUT_MS // 1000}s: {selector}"
                    )
                    continue
                except Exception as exc:
                    print(f"[{provider}] Selector descartado: {selector} ({exc})")
                    continue

            remaining = max(
                0,
                int(BROWSER_TOTAL_TIMEOUT_SECONDS - (monotonic() - started_at)),
            )
            if remaining <= 0:
                print(f"[{provider}] Sin tiempo restante para Smart Browser")
                return None

            print(f"[{provider}] Iniciando Smart Browser...")
            download = try_smart_download(
                page,
                provider,
                download_selectors,
                max_seconds=min(30, remaining),
            )
            if download:
                return save_playwright_download(download, target_dir, provider)

            print(
                f"[{provider}] No se encontro un boton que iniciara descarga. "
                f"URL final: {page.url}"
            )
            return None

    except Exception as exc:
        print(f"[{provider}] Error: {exc}")
        return None

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
