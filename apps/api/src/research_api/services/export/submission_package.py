"""Phase 12 — Submission package zip builder.

Pure function — no DB, no FS, no network. The route layer reads figure
bytes from FileStorage and passes them in as a list of
`(figure_number, ext, bytes)` tuples.

Layout of the produced zip:
    {slug}/manuscript.docx
    {slug}/Figure_1.png ...           (each figure as separate file)
    {slug}/Table_1.docx ...           (each TipTap <table> as its own DOCX)
    {slug}/cover_letter.docx          (always, even if body is empty)
    {slug}/response_to_reviewers.docx (only when reviewer_responses non-empty)

Filename: `{project_slug}_v{snapshot_label_or_'draft'}.zip`. The slug
strips path-traversal characters (`.`, `/`, `\\`, control chars) and falls
back to "project" when the slug would otherwise be empty.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from typing import Iterable

from ..citation_format import CitationStyle, consolidate_inline_clusters
from .bibliography import BibliographyEntry
from .docx_export import (
    FrontMatterPayload,
    html_to_docx_bytes,
    render_docx,
    tables_to_individual_docx,
)


_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")
_FIGURE_EXT_RE = re.compile(r"^[A-Za-z0-9]{1,6}$")


@dataclass(frozen=True)
class FigurePackageItem:
    """Single figure to include in the package.

    `ext` is the lowercase extension (`png`, `jpg`, `jpeg`, `svg`) without
    a leading dot. The route layer derives it from the figure's
    `file_type` MIME (image/png → "png", etc.).
    """

    figure_number: int
    ext: str
    data: bytes


@dataclass(frozen=True)
class CoverLetterPayload:
    body_html: str
    target_journal_label: str | None = None


@dataclass(frozen=True)
class ReviewerResponsePayload:
    reviewer_label: str
    comments: list[dict]  # each {comment_text, response_html}


def slugify_for_zip(title: str | None) -> str:
    """Slug rule for the zip filename.

    Strips path traversal (`.`, `/`, `\\`), control chars, and anything
    outside `[A-Za-z0-9_-]`. Spaces collapse to `-`. Returns "project"
    when the slug would otherwise be empty.
    """
    raw = (title or "").strip()
    raw = raw.replace(" ", "-")
    slug = _SLUG_RE.sub("", raw)
    slug = slug.strip("-_")
    return (slug or "project")[:80]


def _safe_ext(ext: str) -> str:
    """Defence-in-depth — reject path-traversal characters in figure ext."""
    ext = (ext or "").lstrip(".").lower()
    if not _FIGURE_EXT_RE.match(ext):
        return "bin"
    return ext


def _section_html_after_consolidation(section, style: CitationStyle) -> str:
    """Pre-consolidate inline citations the same way the export route does
    so the per-table DOCX renders match the manuscript's table cells."""
    return consolidate_inline_clusters(section.content or "", style)


def _build_response_to_reviewers_html(
    responses: Iterable[ReviewerResponsePayload],
) -> str:
    """Concatenate every reviewer's segmented comments into a single HTML
    blob that `html_to_docx_bytes` can convert."""
    chunks: list[str] = []
    for resp in responses:
        chunks.append(
            f"<p><strong>{_html_escape(resp.reviewer_label)}</strong></p>"
        )
        for idx, c in enumerate(resp.comments or [], start=1):
            comment_text = (c.get("comment_text") or "").strip()
            response_html = (c.get("response_html") or "").strip()
            if not comment_text:
                continue
            chunks.append(
                f"<p><strong>Comment {idx}.</strong> {_html_escape(comment_text)}</p>"
            )
            if response_html:
                # response_html is already trusted HTML (TipTap output).
                chunks.append(
                    f"<p><strong>Response.</strong> {response_html}</p>"
                )
            else:
                chunks.append("<p><em>(No response drafted yet.)</em></p>")
    return "\n".join(chunks)


def _html_escape(text: str) -> str:
    """Minimal escape — the surrounding HTML uses `<p><strong>`, so we
    only need to neutralise `<`, `>`, `&` in the reviewer's raw text."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def build_submission_zip(
    *,
    project,
    sections: list,
    articles: list,
    frontmatter: FrontMatterPayload | None,
    figures: list[FigurePackageItem],
    cover_letter: CoverLetterPayload | None,
    reviewer_responses: list[ReviewerResponsePayload],
    bibliography: list[BibliographyEntry],
    style: CitationStyle,
    snapshot_label: str | None = None,
) -> tuple[str, bytes]:
    """Assemble the submission-package zip in memory.

    Returns `(filename, bytes)`. The filename is
    `{slug}_v{snapshot_or_'draft'}.zip` per the roadmap.

    The caller is responsible for:
      - loading figure bytes from `FileStorage` (the builder is pure).
      - resolving `bibliography` via the existing `build_bibliography`.
      - consolidating section HTML (we do it again here in case the caller
        passed raw rows; `consolidate_inline_clusters` is idempotent).
    """
    buf = io.BytesIO()
    slug = slugify_for_zip(getattr(project, "title", "project"))
    version = _slug_version(snapshot_label)
    filename = f"{slug}_v{version}.zip"

    # Pre-process sections: same consolidation pass as the main export.
    class _Sec:
        __slots__ = ("section_name", "content")

        def __init__(self, name: str, content: str) -> None:
            self.section_name = name
            self.content = content

    consolidated_sections = [
        _Sec(s.section_name, _section_html_after_consolidation(s, style))
        for s in sections
    ]

    # Manuscript DOCX (tables stay INLINE per the spec — extracted tables go
    # into Table_N.docx in addition, not instead).
    manuscript_bytes = render_docx(
        project=project,
        sections=consolidated_sections,
        bibliography=bibliography,
        frontmatter=frontmatter,
    )

    # Walk every section in document order to extract <table>s sequentially.
    # Tables are numbered globally across all sections so Table_1.docx is
    # the manuscript's first table regardless of which section holds it.
    table_blobs: list[bytes] = []
    for s in consolidated_sections:
        per_section = tables_to_individual_docx(s.content)
        for idx in sorted(per_section.keys()):
            table_blobs.append(per_section[idx])

    with zipfile.ZipFile(
        buf, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        zf.writestr(f"{slug}/manuscript.docx", manuscript_bytes)

        # Figures — sorted by figure_number for deterministic ordering.
        for fig in sorted(figures, key=lambda f: f.figure_number):
            ext = _safe_ext(fig.ext)
            # `figure_number` is an int that the route validates as positive;
            # we still clamp negative numbers to absolute value as defence.
            num = abs(int(fig.figure_number or 1))
            zf.writestr(f"{slug}/Figure_{num}.{ext}", fig.data)

        # Tables — globally numbered 1-based.
        for i, blob in enumerate(table_blobs, start=1):
            zf.writestr(f"{slug}/Table_{i}.docx", blob)

        # Cover letter — always present in the package (empty when absent).
        cl_html = (cover_letter.body_html if cover_letter else "") or ""
        cl_title = (
            f"Cover Letter — {cover_letter.target_journal_label}"
            if cover_letter and cover_letter.target_journal_label
            else "Cover Letter"
        )
        cover_bytes = html_to_docx_bytes(cl_html, title=cl_title)
        zf.writestr(f"{slug}/cover_letter.docx", cover_bytes)

        # Response to reviewers — only when at least one row exists.
        if reviewer_responses:
            response_html = _build_response_to_reviewers_html(
                reviewer_responses
            )
            response_bytes = html_to_docx_bytes(
                response_html, title="Response to Reviewers"
            )
            zf.writestr(
                f"{slug}/response_to_reviewers.docx", response_bytes
            )

    return filename, buf.getvalue()


def _slug_version(snapshot_label: str | None) -> str:
    """Map snapshot label to a filesystem-safe version segment.

    Empty / None → "draft". Otherwise the label is slugified (same rule as
    the project title) so a label like "v1 — initial submission" lands as
    "v1-initial-submission".
    """
    raw = (snapshot_label or "").strip()
    if not raw:
        return "draft"
    raw = raw.replace(" ", "-")
    s = _SLUG_RE.sub("", raw).strip("-_")
    return s or "draft"
