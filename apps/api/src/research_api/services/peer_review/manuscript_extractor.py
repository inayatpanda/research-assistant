"""Phase 4.6 — Flatten a project's manuscript into a peer-reviewable text.

The output drives both the AI prompt (the manuscript body) and the row's
``manuscript_snapshot`` JSON so historical reviews remain meaningful
after the manuscript evolves.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Article, Author, Figure
from ...repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ...repositories.projects import SqliteProjectRepository

SECTION_ORDER: tuple[str, ...] = (
    "Abstract",
    "Introduction",
    "Methodology",
    "Results",
    "Discussion",
    "Conclusion",
)


@dataclass
class ManuscriptExtraction:
    """Flattened representation of an in-app manuscript."""

    title: str
    study_type: str | None
    text: str
    sections: dict[str, str]
    metadata: dict[str, int]


class _HTMLStripper(HTMLParser):
    """Drops HTML/TipTap markup, keeping only visible text.

    Block-level tags emit a newline so paragraph structure survives in
    the flattened text. Inline tags pass-through their text content.
    """

    _BLOCK = {
        "p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
        "table", "tr", "br", "blockquote", "section", "article",
        "figcaption", "figure",
    }
    _DROP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._drop_depth = 0

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        if tag in self._DROP:
            self._drop_depth += 1
            return
        if tag in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag in self._DROP and self._drop_depth > 0:
            self._drop_depth -= 1
            return
        if tag in self._BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._drop_depth > 0:
            return
        if data:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw.splitlines()]
        out: list[str] = []
        prev_blank = True
        for ln in lines:
            if not ln:
                if not prev_blank:
                    out.append("")
                prev_blank = True
                continue
            out.append(ln)
            prev_blank = False
        return "\n".join(out).strip()


def strip_tiptap_html(html: str) -> str:
    """Return plain prose for an HTML fragment (used by peer-review)."""
    if not html:
        return ""
    parser = _HTMLStripper()
    parser.feed(html)
    return parser.text()


def _count_tables_in_html(html: str) -> int:
    """Cheap regex count of ``<table>`` opens in the section HTML."""
    if not html:
        return 0
    return len(re.findall(r"<table\b", html, flags=re.IGNORECASE))


async def extract_manuscript_for_peer_review(
    *, project_id: str, user_id: str, session: AsyncSession
) -> ManuscriptExtraction:
    """Flatten the project's manuscript for peer-review.

    Section headers are emitted as upper-cased lines so the AI can refer
    to them when describing issues. Empty sections are kept with a
    placeholder so the AI knows they are missing.
    """
    proj_repo = SqliteProjectRepository(session)
    project = await proj_repo.get(project_id, user_id)
    if project is None:
        raise ValueError("Project not found")

    ms_repo = SqliteManuscriptSectionRepository(session)
    sections = await ms_repo.list_for_project(project_id, user_id)
    sections_html: dict[str, str] = {
        s.section_name: (s.content or "") for s in sections
    }
    sections_text: dict[str, str] = {
        name: strip_tiptap_html(html) for name, html in sections_html.items()
    }

    from sqlalchemy import func

    n_references = int(
        await session.scalar(
            select(func.count(Article.id)).where(
                Article.project_id == project_id, Article.user_id == user_id
            )
        )
        or 0
    )
    n_figures = int(
        await session.scalar(
            select(func.count(Figure.id)).where(
                Figure.project_id == project_id, Figure.user_id == user_id
            )
        )
        or 0
    )
    n_authors = int(
        await session.scalar(
            select(func.count(Author.id)).where(
                Author.project_id == project_id, Author.user_id == user_id
            )
        )
        or 0
    )
    n_tables = sum(_count_tables_in_html(html) for html in sections_html.values())

    body_parts: list[str] = []
    for name in SECTION_ORDER:
        body = sections_text.get(name, "").strip()
        if body:
            body_parts.append(f"## {name.upper()}\n\n{body}")
        else:
            body_parts.append(f"## {name.upper()}\n\n(this section is empty)")
    text = "\n\n".join(body_parts)

    metadata = {
        "n_figures": n_figures,
        "n_tables": n_tables,
        "n_references": n_references,
        "n_authors": n_authors,
    }

    return ManuscriptExtraction(
        title=project.title,
        study_type=project.study_type,
        text=text,
        sections=sections_text,
        metadata=metadata,
    )
