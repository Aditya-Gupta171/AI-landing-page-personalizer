from __future__ import annotations

import os
from typing import List

import requests
import trafilatura
from bs4 import BeautifulSoup, Tag

from src.schemas import PageSection, PageSnapshot


def _is_js_rendering_enabled() -> bool:
    enabled = os.getenv("ENABLE_JS_RENDERING", "false").strip().lower() == "true"
    if not enabled:
        return False

    # On some Windows + Streamlit runtimes Playwright subprocess startup can emit
    # noisy asyncio NotImplementedError warnings. Keep it off unless explicitly forced.
    if os.name == "nt":
        allow_unstable = (
            os.getenv("ENABLE_JS_RENDERING_UNSTABLE", "false").strip().lower() == "true"
        )
        if not allow_unstable:
            return False

    return True


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _fetch_html_static(url: str, timeout_seconds: int) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=timeout_seconds)
    response.raise_for_status()
    return response.text


def _fetch_html_playwright(url: str, timeout_seconds: int) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    timeout_ms = timeout_seconds * 1000
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                page.wait_for_timeout(1200)
                html = page.content()
            finally:
                browser.close()
        return html
    except Exception:
        # If Playwright is unavailable in the current runtime context,
        # silently skip JS rendering and keep static extraction.
        return None


SKIP_CTA_TEXTS = {
    "skip to content",
    "menu",
    "search",
    "home",
    "sign in",
    "log in",
}


def _has_ancestor_tag(node: Tag, tag_names: set[str]) -> bool:
    parent = node.parent
    while isinstance(parent, Tag):
        if parent.name in tag_names:
            return True
        parent = parent.parent
    return False


def _score_cta_text(text: str) -> int:
    value = text.lower()
    score = 0
    keywords = [
        "start",
        "try",
        "book",
        "demo",
        "free",
        "get",
        "shop",
        "sell",
    ]
    for keyword in keywords:
        if keyword in value:
            score += 2
    if 3 <= len(text) <= 32:
        score += 1
    return score


def _extract_primary_cta(soup: BeautifulSoup) -> str:
    candidates: list[tuple[int, str]] = []

    for element in soup.find_all(["button", "a"]):
        if not isinstance(element, Tag):
            continue

        text = _clean_text(element.get_text(" ", strip=True))
        if not text:
            continue

        lower_text = text.lower()
        if lower_text in SKIP_CTA_TEXTS:
            continue
        if lower_text.startswith("skip to"):
            continue
        if _has_ancestor_tag(element, {"nav", "header", "footer"}):
            continue
        if len(text) < 3 or len(text) > 45:
            continue

        score = _score_cta_text(text)
        candidates.append((score, text))

    if not candidates:
        return "Get Started"

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _extract_heading_body(heading: Tag) -> str:
    chunks: List[str] = []

    for sibling in heading.next_siblings:
        if isinstance(sibling, Tag) and sibling.name in {"h1", "h2", "h3"}:
            break
        if isinstance(sibling, Tag):
            text = _clean_text(sibling.get_text(" ", strip=True))
            if text:
                chunks.append(text)
        elif isinstance(sibling, str):
            text = _clean_text(sibling)
            if text:
                chunks.append(text)

        if len(" ".join(chunks)) > 600:
            break

    body = _clean_text(" ".join(chunks))
    if body:
        return body

    # Fallback: extract nearby paragraph/list copy from local container.
    container = heading.find_parent(["section", "article", "div", "main"])
    if not isinstance(container, Tag):
        return ""

    local_parts: List[str] = []
    for node in container.find_all(["p", "li"], limit=8):
        text = _clean_text(node.get_text(" ", strip=True))
        if text:
            local_parts.append(text)

    joined = _clean_text(" ".join(local_parts))
    return joined[:600]


def _extract_sections(soup: BeautifulSoup, limit: int = 8) -> List[PageSection]:
    sections: List[PageSection] = []
    headings = soup.find_all(["h1", "h2", "h3"])

    for heading in headings:
        if not isinstance(heading, Tag):
            continue

        title = _clean_text(heading.get_text(" ", strip=True))
        if not title:
            continue

        body = _extract_heading_body(heading)
        sections.append(PageSection(heading=title, body=body))

        if len(sections) >= limit:
            break

    if sections:
        return sections

    # Fallback for pages without clear heading hierarchy.
    paragraphs = [
        _clean_text(p.get_text(" ", strip=True))
        for p in soup.find_all("p")
        if _clean_text(p.get_text(" ", strip=True))
    ]
    for idx, para in enumerate(paragraphs[:limit], start=1):
        sections.append(PageSection(heading=f"Section {idx}", body=para))

    return sections


def _should_try_js_render(primary_cta: str, sections: List[PageSection]) -> bool:
    cta_value = primary_cta.lower().strip()
    weak_cta = cta_value.startswith("skip to") or cta_value in SKIP_CTA_TEXTS

    if not sections:
        return True

    empty_bodies = sum(1 for sec in sections if not sec.body.strip())
    mostly_empty = empty_bodies >= max(2, len(sections) // 2)
    return weak_cta or mostly_empty


def _build_snapshot_from_html(url: str, html: str) -> PageSnapshot:
    soup = BeautifulSoup(html, "lxml")

    title = _clean_text(soup.title.get_text(strip=True)) if soup.title else ""
    hero = soup.find("h1")
    hero_headline = _clean_text(hero.get_text(" ", strip=True)) if hero else title

    primary_cta = _extract_primary_cta(soup)

    extracted = trafilatura.extract(html, include_links=False, include_images=False)
    raw_text = extracted if extracted else _clean_text(soup.get_text(" ", strip=True))
    sections = _extract_sections(soup)

    return PageSnapshot(
        url=url,
        title=title,
        hero_headline=hero_headline,
        primary_cta=primary_cta,
        sections=sections,
        raw_text=raw_text,
    )


def fetch_page_snapshot(url: str, timeout_seconds: int = 20) -> PageSnapshot:
    static_html = _fetch_html_static(url=url, timeout_seconds=timeout_seconds)
    snapshot = _build_snapshot_from_html(url=url, html=static_html)

    if _is_js_rendering_enabled() and _should_try_js_render(snapshot.primary_cta, snapshot.sections):
        rendered_html = _fetch_html_playwright(url=url, timeout_seconds=timeout_seconds)
        if rendered_html:
            rendered_snapshot = _build_snapshot_from_html(url=url, html=rendered_html)
            if not _should_try_js_render(
                rendered_snapshot.primary_cta,
                rendered_snapshot.sections,
            ):
                return rendered_snapshot

    return snapshot
