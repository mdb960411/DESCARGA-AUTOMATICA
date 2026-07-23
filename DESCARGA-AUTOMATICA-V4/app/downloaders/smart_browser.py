from __future__ import annotations

from time import monotonic

DOWNLOAD_WORDS = (
    "download",
    "descargar",
    "descargar todo",
    "download all",
    "tout télécharger",
    "get files",
    "get file",
    "obtener archivos",
    "obtener archivo",
    "save",
    "continuar",
    "continue",
)


def build_download_selectors(extra_selectors=None):
    selectors = list(extra_selectors or [])
    selectors.extend(
        [
            "[download]",
            "a[download]",
            "a[href*='download']",
            "button[data-testid*='download']",
            "a[data-testid*='download']",
            "[role='button'][data-testid*='download']",
        ]
    )
    for word in DOWNLOAD_WORDS:
        selectors.extend(
            [
                f"button:has-text('{word}')",
                f"a:has-text('{word}')",
                f"[role='button']:has-text('{word}')",
            ]
        )
    return list(dict.fromkeys(selectors))


def try_smart_download(page, provider, extra_selectors=None, max_seconds=30):
    selectors = build_download_selectors(extra_selectors)
    started_at = monotonic()
    candidates_tested = 0
    max_candidates = 20

    for selector in selectors:
        if monotonic() - started_at >= max_seconds or candidates_tested >= max_candidates:
            break
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 3)
            for index in range(count):
                if monotonic() - started_at >= max_seconds or candidates_tested >= max_candidates:
                    break
                candidate = locator.nth(index)
                try:
                    if not candidate.is_visible(timeout=1000):
                        continue
                    candidates_tested += 1
                    print(
                        f"[{provider}] Candidato inteligente: "
                        f"{selector} (elemento {index + 1})"
                    )
                    with page.expect_download(timeout=6000) as download_info:
                        candidate.click(timeout=5000)
                    print(f"[{provider}] Descarga iniciada mediante: {selector}")
                    return download_info.value
                except Exception:
                    continue
        except Exception:
            continue

    print(
        f"[{provider}] Smart Browser finalizado sin descarga "
        f"({candidates_tested} candidatos probados)"
    )
    return None
