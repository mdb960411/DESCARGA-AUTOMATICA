from __future__ import annotations


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
    """
    Construye una lista ordenada de selectores que podrían iniciar
    una descarga.

    Los selectores específicos del proveedor se prueban primero.
    """

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

    # Elimina duplicados sin alterar el orden.
    return list(dict.fromkeys(selectors))


def try_smart_download(page, provider, extra_selectors=None):
    """
    Busca elementos visibles que puedan iniciar una descarga.

    Retorna el objeto Download de Playwright cuando tiene éxito.
    Retorna None cuando ningún elemento inicia una descarga.
    """

    selectors = build_download_selectors(extra_selectors)

    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 5)

            for index in range(count):
                candidate = locator.nth(index)

                try:
                    if not candidate.is_visible(timeout=1500):
                        continue

                    print(
                        f"[{provider}] Candidato inteligente: "
                        f"{selector} (elemento {index + 1})"
                    )

                    with page.expect_download(timeout=12000) as download_info:
                        candidate.click(timeout=10000)

                    print(
                        f"[{provider}] Descarga iniciada mediante: "
                        f"{selector}"
                    )

                    return download_info.value

                except Exception:
                    continue

        except Exception:
            continue

    print(
        f"[{provider}] Smart Browser no encontró "
        "un elemento que iniciara descarga"
    )

    return None
