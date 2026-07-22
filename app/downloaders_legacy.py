import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from app.downloaders.smart_browser import try_smart_download

from app.config import Config
from app.utils import extension_allowed, safe_filename, unique_path

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


def response_filename(url, response):
    content_disposition = response.headers.get("content-disposition", "")
    for pattern in (r"filename\*=UTF-8''([^;]+)", r'filename="?([^";]+)"?'):
        match = re.search(pattern, content_disposition, re.I)
        if match:
            return safe_filename(unquote(match.group(1)))

    name = Path(urlparse(response.url or url).path).name
    if name and "." in name:
        return safe_filename(name)

    content_type = response.headers.get("content-type", "").split(";")[0].lower()
    extension = {
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    }.get(content_type, ".bin")
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    return f"link_{digest}{extension}"


def looks_like_file(response):
    content_type = response.headers.get("content-type", "").lower()
    disposition = response.headers.get("content-disposition", "").lower()
    return "attachment" in disposition or (
        "text/html" not in content_type
        and content_type.startswith(("application/", "image/", "audio/", "video/", "text/csv"))
    )


def download_direct(url, target_dir):
    try:
        with requests.get(
            url,
            timeout=(20, 300),
            allow_redirects=True,
            stream=True,
            headers={"User-Agent": USER_AGENT},
        ) as response:
            response.raise_for_status()
            if not looks_like_file(response):
                print(f"[DIRECTO] No es un archivo: {url}")
                return None

            filename = response_filename(url, response)
            if not extension_allowed(filename, Config.allowed_extensions):
                print(f"[DIRECTO] Extensión no permitida: {filename}")
                return None

            destination = unique_path(target_dir / filename)
            with destination.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        output.write(chunk)
            print(f"[DIRECTO] Descargado: {destination}")
            return destination
    except Exception as exc:
        print(f"[DIRECTO] Falló {url}: {exc}")
        return None


def drive_direct(url):
    patterns = (
        r"drive\.google\.com/file/d/([^/]+)",
        r"drive\.google\.com/open\?id=([^&]+)",
        r"drive\.google\.com/uc\?.*id=([^&]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, url, re.I)
        if match:
            return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
    return None


def _save_playwright_download(download, target_dir, provider):
    suggested = safe_filename(download.suggested_filename or f"{provider.lower()}_download.bin")
    if not extension_allowed(suggested, Config.allowed_extensions):
        print(f"[{provider}] Extensión no permitida: {suggested}")
        return None

    destination = unique_path(target_dir / suggested)
    download.save_as(str(destination))
    print(f"[{provider}] Descargado: {destination}")
    return destination


def _click_if_visible(page, selectors):
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() and locator.is_visible(timeout=1500):
                locator.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def download_with_browser(url, target_dir, provider, download_selectors):
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

            # Cookie/consent dialogs used by several transfer services.
            _click_if_visible(
                page,
                [
                    "button:has-text('Accept all')",
                    "button:has-text('Accept')",
                    "button:has-text('Aceptar todo')",
                    "button:has-text('Aceptar')",
                    "button:has-text('I agree')",
                    "button:has-text('Agree')",
                ],
            )
            page.wait_for_timeout(1000)

            for selector in download_selectors:
                try:
                    locator = page.locator(selector).first
                    if not locator.count() or not locator.is_visible(timeout=2500):
                        continue
                    print(f"[{provider}] Botón encontrado: {selector}")
                    with page.expect_download(timeout=180000) as download_info:
                        locator.click(timeout=15000)
                    result = _save_playwright_download(download_info.value, target_dir, provider)
                    browser.close()
                    return result
                except PlaywrightTimeoutError:
                    # Some providers reveal a second download button after the first click.
                    try:
                        locator.click(timeout=10000)
                        page.wait_for_timeout(2500)
                    except Exception:
                        pass
                except Exception:
                    continue

            # Generic second pass after any intermediate page transition.
            generic_selectors = [
                "a[download]",
                "a[href*='download']",
                "button:has-text('Download')",
                "button:has-text('Descargar')",
                "a:has-text('Download')",
                "a:has-text('Descargar')",
            ]
            for selector in generic_selectors:
                try:
                    locator = page.locator(selector).first
                    if not locator.count() or not locator.is_visible(timeout=2000):
                        continue
                    with page.expect_download(timeout=180000) as download_info:
                        locator.click(timeout=15000)
                    result = _save_playwright_download(download_info.value, target_dir, provider)
                    browser.close()
                    return result
                except Exception:
                    continue

            print(f"[{provider}] Iniciando Smart Browser...")

            download = try_smart_download(
                page,
                provider,
                download_selectors,
)

            if download:
               result = _save_playwright_download(
                   download,
                   target_dir,
                   provider,
    )
    browser.close()
    return result

            print(f"[{provider}] No se encontró un botón que iniciara descarga. URL final: {page.url}")

            browser.close()
            return None


def download_sendgb(url, target_dir):
    if not Config.enable_sendgb:
        return None
    return download_with_browser(
        url,
        target_dir,
        "SENDGB",
        [
            "a[download]",
            "a[href*='download']",
            "button:has-text('Download')",
            "button:has-text('Descargar')",
            "a:has-text('Download')",
            "a:has-text('Descargar')",
        ],
    )


def download_wetransfer(url, target_dir):
    return download_with_browser(
        url,
        target_dir,
        "WETRANSFER",
        [
            "button:has-text('Download')",
            "button:has-text('Descargar')",
            "a:has-text('Download')",
            "a:has-text('Descargar')",
            "button[data-testid*='download']",
            "a[data-testid*='download']",
        ],
    )


def download_transfernow(url, target_dir):
    return download_with_browser(
        url,
        target_dir,
        "TRANSFERNOW",
        [
            "button:has-text('Descargar')",
            "a:has-text('Descargar')",
            "button:has-text('Download')",
            "a:has-text('Download')",
            "a[href*='/download']",
        ],
    )


def download_sendallfiles(url, target_dir):
    return download_with_browser(
        url,
        target_dir,
        "SENDALLFILES",
        [
            "button:has-text('Download')",
            "button:has-text('Descargar')",
            "a:has-text('Download')",
            "a:has-text('Descargar')",
            "a[download]",
        ],
    )


def provider_for(url):
    host = (urlparse(url).hostname or "").lower()
    if host == "we.tl" or host.endswith("wetransfer.com"):
        return "wetransfer"
    if host.endswith("transfernow.net"):
        return "transfernow"
    if host.endswith("sendallfiles.com"):
        return "sendallfiles"
    if host.endswith("sendgb.com"):
        return "sendgb"
    if host == "drive.google.com":
        return "drive"
    return "direct"


def download_url(url, target_dir):
    provider = provider_for(url)
    print(f"[ENLACE] Proveedor={provider} URL={url}")

    if provider == "wetransfer":
        return download_wetransfer(url, target_dir)
    if provider == "transfernow":
        return download_transfernow(url, target_dir)
    if provider == "sendallfiles":
        return download_sendallfiles(url, target_dir)
    if provider == "sendgb":
        return download_sendgb(url, target_dir)
    if provider == "drive":
        direct = drive_direct(url)
        if direct:
            return download_direct(direct, target_dir)
    return download_direct(url, target_dir)
