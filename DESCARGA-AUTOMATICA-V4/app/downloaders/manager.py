from __future__ import annotations

from urllib.parse import urlparse

from app.downloaders.direct import download_direct
from app.downloaders.drive import download_drive
from app.downloaders.providers import (
    download_sendallfiles,
    download_sendgb,
    download_swisstransfer,
    download_transfernow,
    download_wetransfer,
)
from app.utils import url_for_log


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
    if host.endswith("swisstransfer.com"):
        return "swisstransfer"
    if host == "drive.google.com":
        return "drive"
    return "direct"


def download_url(url, target_dir):
    provider = provider_for(url)
    print(f"[ENLACE] Proveedor={provider} URL={url_for_log(url)}")

    handlers = {
        "wetransfer": download_wetransfer,
        "transfernow": download_transfernow,
        "sendallfiles": download_sendallfiles,
        "sendgb": download_sendgb,
        "swisstransfer": download_swisstransfer,
        "drive": download_drive,
        "direct": download_direct,
    }
    return handlers[provider](url, target_dir)
