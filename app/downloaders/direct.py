from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from app.config import Config
from app.downloaders.common import USER_AGENT
from app.utils import extension_allowed, safe_filename, unique_path


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
        and content_type.startswith(
            ("application/", "image/", "audio/", "video/", "text/csv")
        )
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

            destination = unique_path(Path(target_dir) / filename)
            with destination.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        output.write(chunk)

            print(f"[DIRECTO] Descargado: {destination}")
            return destination
    except Exception as exc:
        print(f"[DIRECTO] Falló {url}: {exc}")
        return None
