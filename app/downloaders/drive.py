from __future__ import annotations

import re

from app.downloaders.direct import download_direct
from app.utils import url_for_log


def drive_direct_url(url):
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


def download_drive(url, target_dir):
    direct_url = drive_direct_url(url)
    if not direct_url:
        print(
            "[DRIVE] No se pudo obtener el ID del archivo: "
            f"{url_for_log(url)}"
        )
        return None
    return download_direct(direct_url, target_dir)
