import hashlib, re
from pathlib import Path
from urllib.parse import urlparse
import requests
from playwright.sync_api import sync_playwright
from app.config import Config
from app.utils import extension_allowed, safe_filename, unique_path

def response_filename(url, response):
    cd = response.headers.get("content-disposition", "")
    for pattern in [r"filename\*=UTF-8''([^;]+)", r'filename="?([^";]+)"?']:
        m = re.search(pattern, cd, re.I)
        if m: return safe_filename(m.group(1))
    name = Path(urlparse(url).path).name
    if name and "." in name: return safe_filename(name)
    ext = {"application/pdf": ".pdf", "application/zip": ".zip", "text/csv": ".csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx"}.get(response.headers.get("content-type", "").split(";")[0].lower(), ".bin")
    return f"link_{hashlib.sha256(url.encode()).hexdigest()[:12]}{ext}"

def looks_like_file(response):
    ctype = response.headers.get("content-type", "").lower()
    return "attachment" in response.headers.get("content-disposition", "").lower() or ("text/html" not in ctype and ctype.startswith(("application/", "image/", "audio/", "video/", "text/csv")))

def download_direct(url, target_dir):
    try:
        with requests.get(url, timeout=90, allow_redirects=True, stream=True, headers={"User-Agent": "Mozilla/5.0"}) as response:
            response.raise_for_status()
            if not looks_like_file(response): return None
            filename = response_filename(url, response)
            if not extension_allowed(filename, Config.allowed_extensions): return None
            destination = unique_path(target_dir / filename)
            with destination.open("wb") as out:
                for chunk in response.iter_content(262144):
                    if chunk: out.write(chunk)
            print(f"Enlace descargado: {destination}")
            return destination
    except Exception as exc:
        print(f"Descarga directa falló {url}: {exc}")
        return None

def drive_direct(url):
    for p in [r"drive\.google\.com/file/d/([^/]+)", r"drive\.google\.com/open\?id=([^&]+)", r"drive\.google\.com/uc\?.*id=([^&]+)"]:
        m = re.search(p, url, re.I)
        if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    return None

def download_sendgb(url, target_dir):
    if not Config.enable_sendgb: return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(accept_downloads=True)
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            for selector in ["a[download]", "a[href*='download']", "button:has-text('Download')", "button:has-text('Descargar')", "text=/^Download$/i", "text=/^Descargar$/i"]:
                try:
                    locator = page.locator(selector).first
                    if locator.count() == 0: continue
                    with page.expect_download(timeout=20000) as info: locator.click(timeout=8000)
                    download = info.value
                    destination = unique_path(target_dir / safe_filename(download.suggested_filename))
                    download.save_as(str(destination))
                    browser.close()
                    print(f"SendGB descargado: {destination}")
                    return destination
                except Exception:
                    continue
            browser.close()
    except Exception as exc:
        print(f"Error SendGB {url}: {exc}")
    return None

def download_url(url, target_dir):
    if "sendgb.com" in url.lower(): return download_sendgb(url, target_dir)
    direct = drive_direct(url)
    if direct:
        result = download_direct(direct, target_dir)
        if result: return result
    return download_direct(url, target_dir)
