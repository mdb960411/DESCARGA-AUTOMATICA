from __future__ import annotations

from pathlib import Path

from app.browser_profile import USER_AGENT
from app.config import Config
from app.utils import extension_allowed, safe_filename, unique_path


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
            locator = page.locator(selector)
            count = min(locator.count(), 10)
            for index in range(count):
                candidate = locator.nth(index)
                if candidate.is_visible(timeout=1500):
                    candidate.click(timeout=5000)
                    return True
        except Exception:
            continue
    return False
