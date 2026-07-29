from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from time import monotonic

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


DOWNLOAD_WORDS = (
    "download",
    "descargar",
    "descargar todo",
    "download all",
    "tout télécharger",
    "télécharger",
    "scarica",
    "get your files",
    "get files",
    "get file",
    "obtener archivos",
    "obtener archivo",
    "save files",
)

CONTINUE_WORDS = (
    "continue",
    "continuar",
    "proceed",
    "siguiente",
    "next",
)

NEGATIVE_WORDS = (
    "upload",
    "subir",
    "sign in",
    "login",
    "iniciar sesión",
    "share",
    "compartir",
    "facebook",
    "twitter",
    "upgrade",
    "cancel",
    "cancelar",
    "reject",
    "rechazar",
)

ACTION_SELECTOR = (
    "button, a, [role='button'], [role='link'], "
    "input[type='button'], input[type='submit'], "
    "[data-testid], [aria-label], [title]"
)
MAX_ACTIONS_PER_ROOT = 100


@dataclass
class SmartDownloadResult:
    download: object | None
    page: object
    progressed: bool = False


@dataclass
class ActionCandidate:
    root_name: str
    locator: object
    score: int
    description: str
    identity: str


def build_download_selectors(extra_selectors=None):
    selectors = list(extra_selectors or [])
    selectors.extend(
        [
            "[download]",
            "a[download]",
            "a[href*='download' i]",
            "[data-testid*='download' i]",
            "[aria-label*='download' i]",
            "[aria-label*='descargar' i]",
            "[title*='download' i]",
            "[title*='descargar' i]",
        ]
    )
    for word in (*DOWNLOAD_WORDS, *CONTINUE_WORDS):
        selectors.extend(
            [
                f"button:has-text('{word}')",
                f"a:has-text('{word}')",
                f"[role='button']:has-text('{word}')",
                f"[role='link']:has-text('{word}')",
            ]
        )
    return list(dict.fromkeys(selectors))


def _roots(page, search_all_frames):
    roots = [("principal", page.main_frame)]
    if not search_all_frames:
        return roots

    for index, frame in enumerate(page.frames, 1):
        if frame == page.main_frame:
            continue
        roots.append((f"marco-{index}", frame))
    return roots


def _safe_ui_value(value, limit=90):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(
        r"https?://[^\s<>\"]+",
        "[URL]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "[correo]",
        text,
    )
    text = re.sub(
        r"\b[\w .()_-]{1,80}\."
        r"(zip|rar|7z|pdf|ai|ps|eps|indd|idml|psd|tif|tiff)\b",
        "[archivo]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b[A-Za-z0-9_-]{24,}\b",
        "[token]",
        text,
    )
    return text[:limit]


def _element_metadata(locator):
    try:
        return locator.evaluate(
            """
            element => {
              const href = element.href || element.getAttribute('href') || '';
              const text = (
                element.innerText ||
                element.value ||
                element.textContent ||
                ''
              ).trim();
              return {
                tag: (element.tagName || '').toLowerCase(),
                text,
                aria: element.getAttribute('aria-label') || '',
                title: element.getAttribute('title') || '',
                testid: element.getAttribute('data-testid') || '',
                role: element.getAttribute('role') || '',
                type: element.getAttribute('type') || '',
                name: element.getAttribute('name') || '',
                href,
                className:
                  typeof element.className === 'string'
                    ? element.className
                    : ''
              };
            }
            """
        )
    except Exception:
        return {}


def _href_hint(href):
    value = str(href or "").casefold()
    if not value:
        return ""
    if "download" in value or "descarg" in value:
        return "descarga"
    if re.search(
        r"\.(zip|rar|7z|pdf|ai|ps|eps|indd|idml|psd)(?:[?#]|$)",
        value,
    ):
        return "archivo"
    return "enlace"


def _candidate_score(metadata):
    fields = " ".join(
        str(metadata.get(name, ""))
        for name in (
            "text",
            "aria",
            "title",
            "testid",
            "role",
            "type",
            "name",
            "href",
            "className",
        )
    ).casefold()

    score = 0
    if any(word in fields for word in DOWNLOAD_WORDS):
        score += 12
    if "download" in str(metadata.get("testid", "")).casefold():
        score += 8
    if "download" in str(metadata.get("href", "")).casefold():
        score += 7
    if any(word in fields for word in CONTINUE_WORDS):
        score += 4
    if metadata.get("tag") in {"button", "a"}:
        score += 1
    if any(word in fields for word in NEGATIVE_WORDS):
        score -= 14
    return score


def _candidate_description(metadata):
    parts = [f"tag={_safe_ui_value(metadata.get('tag')) or '?'}"]
    for label, field in (
        ("texto", "text"),
        ("aria", "aria"),
        ("titulo", "title"),
        ("testid", "testid"),
        ("rol", "role"),
        ("tipo", "type"),
    ):
        value = _safe_ui_value(metadata.get(field))
        if value:
            parts.append(f"{label}={value!r}")

    href_hint = _href_hint(metadata.get("href"))
    if href_hint:
        parts.append(f"destino={href_hint}")
    return " ".join(parts)


def _candidate_identity(root_name, metadata):
    raw = "|".join(
        [
            root_name,
            str(metadata.get("tag", "")),
            str(metadata.get("text", ""))[:200],
            str(metadata.get("aria", ""))[:200],
            str(metadata.get("title", ""))[:200],
            str(metadata.get("testid", ""))[:200],
            _href_hint(metadata.get("href")),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _metadata_candidates(page, search_all_frames):
    candidates = []
    seen = set()

    for root_name, root in _roots(page, search_all_frames):
        try:
            locator = root.locator(ACTION_SELECTOR)
            count = min(locator.count(), MAX_ACTIONS_PER_ROOT)
        except Exception:
            continue

        for index in range(count):
            item = locator.nth(index)
            try:
                if not item.is_visible(timeout=350):
                    continue
            except Exception:
                continue

            metadata = _element_metadata(item)
            score = _candidate_score(metadata)
            if score < 4:
                continue

            identity = _candidate_identity(root_name, metadata)
            if identity in seen:
                continue
            seen.add(identity)
            candidates.append(
                ActionCandidate(
                    root_name=root_name,
                    locator=item,
                    score=score,
                    description=_candidate_description(metadata),
                    identity=identity,
                )
            )

    return sorted(candidates, key=lambda item: item.score, reverse=True)


def _selector_candidates(page, selectors, search_all_frames):
    candidates = []
    seen = set()

    for root_name, root in _roots(page, search_all_frames):
        for selector in selectors:
            try:
                locator = root.locator(selector)
                count = min(locator.count(), 3)
            except Exception:
                continue

            for index in range(count):
                item = locator.nth(index)
                try:
                    if not item.is_visible(timeout=350):
                        continue
                except Exception:
                    continue

                metadata = _element_metadata(item)
                identity = _candidate_identity(root_name, metadata)
                if identity in seen:
                    continue
                seen.add(identity)
                candidates.append(
                    ActionCandidate(
                        root_name=root_name,
                        locator=item,
                        score=max(6, _candidate_score(metadata)),
                        description=_candidate_description(metadata),
                        identity=identity,
                    )
                )

    return candidates


def _page_state(page):
    try:
        state = page.evaluate(
            """
            () => ({
              url: location.href,
              actions: document.querySelectorAll(
                "button, a, [role='button'], [role='link']"
              ).length,
              text: (document.body?.innerText || '').slice(0, 2500)
            })
            """
        )
    except Exception:
        return ""

    raw = repr(state).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def visible_action_descriptions(page, limit=8):
    candidates = _metadata_candidates(page, search_all_frames=True)
    return [
        f"{item.root_name} puntaje={item.score} {item.description}"
        for item in candidates[:limit]
    ]


def try_smart_download(
    page,
    provider,
    extra_selectors=None,
    max_seconds=30,
    *,
    search_all_frames=False,
):
    selectors = build_download_selectors(extra_selectors)
    started_at = monotonic()
    candidates_tested = 0
    max_candidates = 24
    max_stages = 3
    stage = 1
    active_page = page
    progressed_any = False
    tested_states = set()

    while (
        monotonic() - started_at < max_seconds
        and candidates_tested < max_candidates
        and stage <= max_stages
    ):
        candidates = _selector_candidates(
            active_page,
            selectors,
            search_all_frames,
        )
        metadata_candidates = _metadata_candidates(
            active_page,
            search_all_frames,
        )

        known_ids = {candidate.identity for candidate in candidates}
        candidates.extend(
            candidate
            for candidate in metadata_candidates
            if candidate.identity not in known_ids
        )

        if not candidates:
            break

        progressed_stage = False
        state_before_stage = _page_state(active_page)

        for candidate in candidates:
            if (
                monotonic() - started_at >= max_seconds
                or candidates_tested >= max_candidates
            ):
                break

            state_key = (
                state_before_stage,
                candidate.root_name,
                candidate.identity,
            )
            if state_key in tested_states:
                continue
            tested_states.add(state_key)
            candidates_tested += 1

            print(
                f"[{provider}] Candidato inteligente etapa {stage}: "
                f"{candidate.root_name} {candidate.description}"
            )
            pages_before = {
                id(candidate_page)
                for candidate_page in active_page.context.pages
            }
            state_before_click = _page_state(active_page)

            try:
                remaining_ms = max(
                    1_500,
                    min(
                        7_000,
                        int(
                            (
                                max_seconds
                                - (monotonic() - started_at)
                            )
                            * 1_000
                        ),
                    ),
                )
                with active_page.expect_download(
                    timeout=remaining_ms
                ) as download_info:
                    candidate.locator.click(timeout=5_000)
                print(
                    f"[{provider}] Descarga iniciada mediante candidato "
                    f"inteligente"
                )
                return SmartDownloadResult(
                    download=download_info.value,
                    page=active_page,
                    progressed=True,
                )
            except PlaywrightTimeoutError:
                pass
            except Exception:
                continue

            try:
                active_page.wait_for_timeout(600)
            except Exception:
                pass

            new_pages = [
                candidate_page
                for candidate_page in active_page.context.pages
                if id(candidate_page) not in pages_before
                and not candidate_page.is_closed()
            ]
            if new_pages:
                active_page = new_pages[-1]
                try:
                    active_page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=8_000,
                    )
                except Exception:
                    pass

            state_after_click = _page_state(active_page)
            if state_after_click and state_after_click != state_before_click:
                progressed_any = True
                progressed_stage = True
                print(
                    f"[{provider}] La acción avanzó la interfaz; "
                    "se buscará el siguiente control"
                )
                break

        if not progressed_stage:
            break
        stage += 1

    print(
        f"[{provider}] Smart Browser finalizado sin descarga "
        f"({candidates_tested} candidatos, {stage - 1} avances)"
    )
    return SmartDownloadResult(
        download=None,
        page=active_page,
        progressed=progressed_any,
    )
