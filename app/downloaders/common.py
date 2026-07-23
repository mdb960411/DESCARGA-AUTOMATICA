from __future__ import annotations

from pathlib import Path

from app.config import Config
from app.utils import extension_allowed, safe_filename, unique_path

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


def save_playwright_download(download, target_dir: Path, provider: str):
    suggested = safe_filename(
        download.suggested_filename or f"{provider.lower()}_download.bin"
    )
    if not extension_allowed(suggested, Config.allowed_extensions):
        print(f"[{provider}] Extensión no permitida: {suggested}")
        return None

    destination = unique_path(Path(target_dir) / suggested)
    try:
        download.save_as(str(destination))
        size = destination.stat().st_size

        if size > Config.max_file_size_bytes():
            destination.unlink(missing_ok=True)
            print(
                f"[{provider}] Archivo rechazado por tamaño: "
                f"{size / (1024 ** 3):.2f} GiB"
            )
            return None

        print(
            f"[{provider}] Descargado: {destination.name} "
            f"({size / (1024 ** 2):.1f} MiB)"
        )
        return destination
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def click_if_visible(page, selectors) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() and locator.is_visible(timeout=1500):
                locator.click(timeout=5000)
                return True
        except Exception:
            continue
    return False
