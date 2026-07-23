from __future__ import annotations

from app.config import Config
from app.downloaders.browser import download_with_browser


def download_sendgb(url, target_dir):
    if not Config.enable_sendgb:
        print("[SENDGB] Descarga deshabilitada por configuración")
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
