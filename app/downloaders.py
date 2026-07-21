import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.config import Config
from app.utils import extension_allowed, safe_filename, unique_path


BROWSER_DOWNLOAD_DOMAINS = (
    "sendgb.com",
    "sendallfiles.com",
)

IGNORED_HOSTS = (
    "notifications.googleapis.com",
    "g.co",
    "google.com",
    "accounts.google.com",
)

DOWNLOAD_SELECTORS = (
    "a[download]",
    "a[href*='download' i]",
    "button:has-text('Download')",
    "button:has-text('Descargar')",
    "a:has-text('Download')",
    "a:has-text('Descargar')",
    "[role='button']:has-text('Download')",
    "[role='button']:has-text('Descargar')",
    "text=/^Download$/i",
    "text=/^Descargar$/i",
)

COOKIE_SELECTORS = (
    "button:has-text('Accept')",
    "button:has-text('Aceptar')",
    "button:has-text('Allow all')",
    "button:has-text('Permitir todas')",
)


def response_filename(url, response):
    content_disposition = response.headers.get("content-disposition", "")
    for pattern in (
        r"filename\*=UTF-8''([^;]+)",
        r'filename="?([^";]+)"?',
    ):
        match = re.search(pattern, content_disposition, re.I)
        if match:
            return safe_filename(unquote(match.group(1)))

    name = Path(urlparse(url).path).name
    if name and "." in name:
        return safe_filename(unquote(name))

    content_type = response.headers.get("content-type", "").split(";")[0].lower()
    extension = {
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }.get(content_type, ".bin")
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    return f"link_{digest}{extension}"


def looks_like_file(response):
    content_type = response.headers.get("content-type", "").lower()
    content_disposition = response.headers.get("content-disposition", "").lower()
    return (
        "attachment" in content_disposition
        or (
            "text/html" not in content_type
            and content_type.startswith(
                ("application/", "image/", "audio/", "video/", "text/csv")
            )
        )
    )


def hostname(url):
    return (urlparse(url).hostname or "").lower()


def should_ignore_url(url):
    host = hostname(url)
    return any(host == item or host.endswith(f".{item}") for item in IGNORED_HOSTS)


def download_direct(url, target_dir):
    try:
        with requests.get(
            url,
            timeout=90,
            allow_redirects=True,
            stream=True,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as response:
            response.raise_for_status()
            if not looks_like_file(response):
                return None

            filename = response_filename(url, response)
            if not extension_allowed(filename, Config.allowed_extensions):
                print(f"Extensión no permitida: {filename}")
                return None

            destination = unique_path(target_dir / filename)
            with destination.open("wb") as output:
                for chunk in response.iter_content(262144):
                    if chunk:
                        output.write(chunk)

            print(f"Enlace descargado: {destination}")
            return destination
    except Exception as exc:
        print(f"Descarga directa falló {url}: {exc}")
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


def _accept_cookies(page):
    for selector in COOKIE_SELECTORS:
        try:
            locator = page.locator(selector).first
            if locator.count() and locator.is_visible():
                locator.click(timeout=3000)
                page.wait_for_timeout(1000)
                return
        except Exception:
            continue


def _save_playwright_download(download, target_dir, provider_name):
    suggested = safe_filename(download.suggested_filename or "archivo_descargado.bin")
    if not extension_allowed(suggested, Config.allowed_extensions):
        print(f"{provider_name}: extensión no permitida: {suggested}")
        return None

    destination = unique_path(target_dir / suggested)
    download.save_as(str(destination))
    print(f"{provider_name} descargado: {destination}")
    return destination


def download_with_browser(url, target_dir, provider_name="Navegador"):
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            print(f"{provider_name}: abriendo {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            _accept_cookies(page)

            for selector in DOWNLOAD_SELECTORS:
                try:
                    locator = page.locator(selector).first
                    if locator.count() == 0 or not locator.is_visible():
                        continue

                    print(f"{provider_name}: intentando selector {selector}")
                    with page.expect_download(timeout=45000) as download_info:
                        locator.click(timeout=15000)
                    result = _save_playwright_download(
                        download_info.value, target_dir, provider_name
                    )
                    browser.close()
                    return result
                except PlaywrightTimeoutError:
                    continue
                except Exception as exc:
                    print(f"{provider_name}: selector falló ({selector}): {exc}")
                    continue

            browser.close()
            print(f"{provider_name}: no se encontró una descarga utilizable")
    except Exception as exc:
        print(f"Error {provider_name} {url}: {exc}")
    return None


def download_sendgb(url, target_dir):
    if not Config.enable_sendgb:
        return None
    return download_with_browser(url, target_dir, "SendGB")


def download_sendallfiles(url, target_dir):
    # La parte posterior a # contiene datos usados por el navegador. Playwright
    # conserva la URL completa y permite que el JavaScript del sitio la procese.
    return download_with_browser(url, target_dir, "SendAllFiles")


def download_url(url, target_dir):
    normalized = url.strip()
    host = hostname(normalized)

    if should_ignore_url(normalized):
        print(f"Enlace ignorado: {normalized}")
        return None

    if host == "sendgb.com" or host.endswith(".sendgb.com"):
        return download_sendgb(normalized, target_dir)

    if host == "sendallfiles.com" or host.endswith(".sendallfiles.com"):
        return download_sendallfiles(normalized, target_dir)

    direct = drive_direct(normalized)
    if direct:
        result = download_direct(direct, target_dir)
        if result:
            return result

    return download_direct(normalized, target_dir)
