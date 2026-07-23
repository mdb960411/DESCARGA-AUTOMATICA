from __future__ import annotations

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


def _try_selector_download(page, selector, timeout=180000):
    locator = page.locator(selector).first
    if not locator.count() or not locator.is_visible(timeout=2500):
        return None

    with page.expect_download(timeout=timeout) as download_info:
        locator.click(timeout=15000)
    return download_info.value


def download_with_browser(url, target_dir, provider, download_selectors):
    browser = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            context = browser.new_context(
                accept_downloads=True,
                user_agent=USER_AGENT,
                viewport={"width": 1440, "height": 1000},
            )
            page = context.new_page()

            print(f"[{provider}] Abriendo: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(3000)

            click_if_visible(page, CONSENT_SELECTORS)
            page.wait_for_timeout(1000)

            for selector in download_selectors:
                try:
                    print(f"[{provider}] Probando selector: {selector}")
                    download = _try_selector_download(page, selector)
                    if download:
                        return save_playwright_download(download, target_dir, provider)
                except PlaywrightTimeoutError:
                    # Algunos servicios muestran una segunda pantalla luego del clic.
                    try:
                        page.locator(selector).first.click(timeout=10000)
                        page.wait_for_timeout(2500)
                    except Exception:
                        pass
                except Exception:
                    continue

            for selector in GENERIC_DOWNLOAD_SELECTORS:
                try:
                    download = _try_selector_download(page, selector)
                    if download:
                        return save_playwright_download(download, target_dir, provider)
                except Exception:
                    continue

            print(f"[{provider}] Iniciando Smart Browser...")
            download = try_smart_download(page, provider, download_selectors)
            if download:
                return save_playwright_download(download, target_dir, provider)

            print(
                f"[{provider}] No se encontró un botón que iniciara descarga. "
                f"URL final: {page.url}"
            )
            return None
    except Exception as exc:
        print(f"[{provider}] Error: {exc}")
        return None
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
