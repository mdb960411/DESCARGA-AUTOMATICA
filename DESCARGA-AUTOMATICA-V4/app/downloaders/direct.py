from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from app.config import Config
from app.downloaders.common import USER_AGENT
from app.utils import (
    extension_allowed,
    safe_error_message,
    safe_filename,
    unique_path,
    url_for_log,
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
        "application/illustrator": ".ai",
        "application/postscript": ".ps",
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "image/vnd.adobe.photoshop": ".psd",
        "image/tiff": ".tif",
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    }.get(content_type, ".bin")
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    return f"link_{digest}{extension}"


def looks_like_file(response):
    content_type = response.headers.get("content-type", "").lower()
    disposition = response.headers.get("content-disposition", "").lower()
    non_file_types = (
        "application/json",
        "application/problem+json",
        "text/html",
    )
    if any(item in content_type for item in non_file_types):
        return False

    return "attachment" in disposition or (
        "text/html" not in content_type
        and content_type.startswith(
            ("application/", "image/", "audio/", "video/", "text/csv")
        )
    )


def _content_length(response):
    try:
        return int(response.headers.get("content-length", "0"))
    except (TypeError, ValueError):
        return 0


def _cookie_jar(cookies):
    jar = requests.cookies.RequestsCookieJar()
    for cookie in cookies or []:
        name = cookie.get("name")
        if not name:
            continue
        cookie_options = {"path": cookie.get("path") or "/"}
        if cookie.get("domain"):
            cookie_options["domain"] = cookie["domain"]
        jar.set(name, cookie.get("value", ""), **cookie_options)
    return jar


def download_direct(
    url,
    target_dir,
    *,
    method="GET",
    request_body=None,
    extra_headers=None,
    cookies=None,
    filename_hint=None,
    provider="DIRECTO",
):
    destination = None
    safe_url = url_for_log(url)
    try:
        headers = {"User-Agent": USER_AGENT}
        headers.update(extra_headers or {})

        with requests.Session() as session:
            session.cookies.update(_cookie_jar(cookies))

            with session.request(
                method.upper(),
                url,
                data=request_body,
                timeout=(20, Config.download_timeout_seconds),
                allow_redirects=True,
                stream=True,
                headers=headers,
            ) as response:
                response.raise_for_status()
                if not looks_like_file(response):
                    print(f"[{provider}] La respuesta no es un archivo: {safe_url}")
                    return None

                expected_size = _content_length(response)
                if expected_size > Config.max_file_size_bytes():
                    print(
                        f"[{provider}] Archivo rechazado por tamaño: "
                        f"{expected_size / (1024 ** 3):.2f} GiB"
                    )
                    return None

                response_name = response_filename(url, response)
                hinted_name = (
                    safe_filename(filename_hint) if filename_hint else ""
                )
                filename = (
                    hinted_name
                    if hinted_name and Path(hinted_name).suffix
                    else response_name
                )
                if (
                    not extension_allowed(filename, Config.allowed_extensions)
                    and extension_allowed(
                        response_name, Config.allowed_extensions
                    )
                ):
                    filename = response_name
                if not extension_allowed(filename, Config.allowed_extensions):
                    print(f"[{provider}] Extensión no permitida: {filename}")
                    return None

                destination = unique_path(Path(target_dir) / filename)
                written = 0
                next_progress_log = 256 * 1024 * 1024

                with destination.open("wb") as output:
                    for chunk in response.iter_content(
                        Config.download_chunk_size_bytes()
                    ):
                        if chunk:
                            output.write(chunk)
                            written += len(chunk)

                            if written > Config.max_file_size_bytes():
                                raise RuntimeError(
                                    "El archivo supera MAX_FILE_SIZE_MB "
                                    "durante la descarga"
                                )

                            if written >= next_progress_log:
                                print(
                                    f"[{provider}] Descargados "
                                    f"{written / (1024 ** 3):.2f} GiB "
                                    f"de {filename}"
                                )
                                next_progress_log += 256 * 1024 * 1024

            print(
                f"[{provider}] Descargado: {destination.name} "
                f"({written / (1024 ** 2):.1f} MiB)"
            )
            return destination
    except Exception as exc:
        if destination is not None:
            try:
                destination.unlink(missing_ok=True)
            except Exception:
                pass
        print(
            f"[{provider}] Falló {safe_url}: "
            f"{safe_error_message(exc)}"
        )
        return None
