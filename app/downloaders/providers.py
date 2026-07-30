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
            "button:text-is('Descargar todo')",
            "button:text-is('Download all')",
            "button:text-is('Descargar')",
            "button:text-is('Download')",
            "button[data-testid='download-button']",
            "[data-testid*='download' i]",
            "[aria-label*='download' i]",
            "[aria-label*='descargar' i]",
            "button:has-text('Download')",
            "button:has-text('Descargar')",
            "button:has-text('Get your files')",
            "button:has-text('Get files')",
            "a:has-text('Download')",
            "a:has-text('Descargar')",
            "a:has-text('Get your files')",
            "button[data-testid*='download']",
            "a[data-testid*='download']",
        ],
        wait_for_download_controls_seconds=15,
        native_user_agent=True,
        allow_service_workers=True,
        search_all_frames=True,
        # WeTransfer puede invalidar su URL de un solo uso cuando Chromium
        # cancela la descarga para cederla a requests. Se conserva la descarga
        # nativa directamente sobre el bucket montado.
        allow_http_handoff=False,
    )


def download_transfernow(url, target_dir):
    return download_with_browser(
        url,
        target_dir,
        "TRANSFERNOW",
        [
            "a:text-is('Download file')",
            "a:text-is('Descargar archivo')",
            "button:text-is('Download file')",
            "button:text-is('Descargar archivo')",
            "button:text-is('Descargar todo')",
            "button:text-is('Download all')",
            "[data-testid*='download' i]",
            "[aria-label*='download' i]",
            "[aria-label*='descargar' i]",
            "button:has-text('Descargar')",
            "button:has-text('Descargar todo')",
            "a:has-text('Descargar')",
            "button:has-text('Download')",
            "button:has-text('Download all')",
            "a:has-text('Download')",
            "button:has-text('Télécharger')",
            "a:has-text('Télécharger')",
            "a[href*='/download']",
        ],
        wait_for_download_controls_seconds=15,
        native_user_agent=True,
        search_all_frames=True,
    )


def download_sendallfiles(url, target_dir):
    return download_with_browser(
        url,
        target_dir,
        "SENDALLFILES",
        [
            "button:text-is('Descargar')",
            "button:has-text('Descargar')",
            "[role='button']:text-is('Descargar')",
            "[role='button']:has-text('Descargar')",
            "a:text-is('Descargar')",
            "button:text-is('Download')",
            "button:has-text('Download')",
            "[role='button']:text-is('Download')",
            "[role='button']:has-text('Download')",
            "a:has-text('Descargar')",
            "a:has-text('Download')",
            "input[type='button'][value='Descargar']",
            "input[type='submit'][value='Descargar']",
            "a[download]",
        ],
        download_all=True,
        wait_for_download_controls_seconds=60,
        compatibility_mode=True,
        search_all_frames=True,
        # Conserva la sesión validada por Cloudflare mientras Chromium escribe
        # directamente en el volumen externo montado.
        allow_http_handoff=False,
        manual_on_pending_challenge=True,
    )


def download_swisstransfer(url, target_dir):
    return download_with_browser(
        url,
        target_dir,
        "SWISSTRANSFER",
        [
            "[data-testid*='download' i]",
            "[aria-label*='download' i]",
            "[aria-label*='descargar' i]",
            "[title*='download' i]",
            "[title*='descargar' i]",
            "button:has-text('Descargar todo')",
            "a:has-text('Descargar todo')",
            "[role='button']:has-text('Descargar todo')",
            "button:has-text('Download all')",
            "a:has-text('Download all')",
            "[role='button']:has-text('Download all')",
            "button:has-text('Tout télécharger')",
            "a:has-text('Tout télécharger')",
            "button:has-text('Tutto scaricare')",
            "a:has-text('Tutto scaricare')",
            "button[data-testid*='download']",
            "a[data-testid*='download']",
            "a[download]",
        ],
        wait_for_download_controls_seconds=15,
        native_user_agent=True,
        search_all_frames=True,
    )
