"""Phase 20 (MP20) — Best-effort auto-check for reporting checklists.

The intent is *not* to grade — the auto-checker only surfaces text excerpts
that look relevant to each checklist item so the user has somewhere to
start. Every item ends up with ``status = "unclear"``; the user reviews and
flips to ``pass`` / ``fail`` / ``na``.

Heuristic (deliberately simple, fully deterministic):

  1. From the item ``title`` + ``description``, extract candidate keywords:
     lowercase alpha tokens of length >= 4, excluding a small stop-word set.
  2. For each manuscript section, score every paragraph by the count of
     unique keyword hits (case-insensitive substring match).
  3. Prefer paragraphs in the section matching the item's ``section_hint``;
     fall back to any other section if no paragraph in the hinted section
     scores > 0.
  4. The first 80 chars of the best paragraph become ``mapped_text_excerpt``
     and that section becomes ``mapped_section``. No matches → both null.

The function is pure: no DB, no network, no AI. Tests pin it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .catalogue import ChecklistCatalogue, ChecklistItem


# Common English stop-words that would otherwise dominate the keyword set
# for short item titles. Kept small + explicit so we can reason about
# matches in tests.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "and", "for", "with", "from", "this", "that", "these", "those",
        "into", "such", "have", "been", "were", "their", "they", "them",
        "where", "when", "what", "which", "while", "study", "studies",
        "research", "data", "report", "reported", "describe", "described",
        "describes", "include", "included", "including", "based", "using",
        "used", "should", "could", "will", "are", "any", "all", "each",
        "other", "than", "into", "between", "across", "about", "after",
        "before", "during", "very", "more", "less", "most", "least",
        "make", "makes", "made", "much", "many", "some", "list", "give",
        "given", "gives", "see", "may", "must", "also", "use", "used",
        "uses", "main", "part", "parts", "your", "our", "its", "his",
        "her", "him", "she", "us", "we", "you", "in", "of", "on", "to",
        "is", "as", "if", "or", "an", "be", "do", "by", "at", "no",
        "yes", "not", "via", "per", "etc", "via",
    }
)


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']{3,}")


def _keywords(item: ChecklistItem) -> list[str]:
    """Stable, ordered, de-duplicated keyword list for an item."""
    text = f"{item.title} {item.description}".lower()
    seen: dict[str, None] = {}
    for tok in _WORD_RE.findall(text):
        if tok in _STOPWORDS:
            continue
        if len(tok) < 4:
            continue
        seen.setdefault(tok, None)
    return list(seen.keys())


def _paragraphs(section_text: str) -> list[str]:
    if not section_text:
        return []
    parts = re.split(r"\n\s*\n", section_text.strip())
    # Strip HTML-ish tags very lightly so paragraphs from rich-text drafts
    # don't poison the keyword match.
    cleaned: list[str] = []
    for p in parts:
        plain = re.sub(r"<[^>]+>", " ", p).strip()
        if plain:
            cleaned.append(plain)
    return cleaned


def _score(paragraph: str, keywords: list[str]) -> int:
    if not keywords or not paragraph:
        return 0
    low = paragraph.lower()
    return sum(1 for kw in keywords if kw in low)


@dataclass(frozen=True)
class _Match:
    section: str
    paragraph: str
    score: int


def _best_match(
    sections_text: dict[str, str], keywords: list[str], section_hint: str
) -> _Match | None:
    best: _Match | None = None
    # Pass 1 — restricted to the hinted section.
    if section_hint and section_hint in sections_text:
        for para in _paragraphs(sections_text[section_hint]):
            s = _score(para, keywords)
            if s > 0 and (best is None or s > best.score):
                best = _Match(section=section_hint, paragraph=para, score=s)
        if best is not None:
            return best
    # Pass 2 — anywhere.
    for sec_name, body in sections_text.items():
        if sec_name == section_hint:
            continue
        for para in _paragraphs(body):
            s = _score(para, keywords)
            if s > 0 and (best is None or s > best.score):
                best = _Match(section=sec_name, paragraph=para, score=s)
    return best


def _excerpt(text: str, *, max_chars: int = 80) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"  # …


def initial_items(catalogue: ChecklistCatalogue) -> list[dict[str, Any]]:
    """Seed the persisted ``items`` list when a new run is created."""
    return [
        {
            "item_id": it.id,
            "item_text": it.title,
            "status": "unclear",
            "comment": "",
            "mapped_section": None,
            "mapped_text_excerpt": None,
        }
        for it in catalogue.items
    ]


def auto_check(
    *,
    catalogue: ChecklistCatalogue,
    sections_text: dict[str, str],
    current_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return a refreshed items list with best-effort section mappings.

    Existing item statuses + comments are preserved — auto-check only
    overwrites ``mapped_section`` / ``mapped_text_excerpt`` (and only when
    a match is found). Status defaults to ``"unclear"`` for any item that
    is still at its initial unclear value; user-set ``pass`` / ``fail`` /
    ``na`` decisions survive.
    """
    by_id: dict[str, dict[str, Any]] = {}
    if current_items:
        for entry in current_items:
            if isinstance(entry, dict) and "item_id" in entry:
                by_id[str(entry["item_id"])] = dict(entry)

    out: list[dict[str, Any]] = []
    for it in catalogue.items:
        existing = by_id.get(it.id, {})
        keywords = _keywords(it)
        match = _best_match(sections_text, keywords, it.section_hint)
        entry: dict[str, Any] = {
            "item_id": it.id,
            "item_text": existing.get("item_text") or it.title,
            "status": existing.get("status") or "unclear",
            "comment": existing.get("comment") or "",
            "mapped_section": match.section if match else None,
            "mapped_text_excerpt": _excerpt(match.paragraph) if match else None,
        }
        out.append(entry)
    return out


def compute_compliance_pct(items: list[dict[str, Any]]) -> float:
    """Derived compliance percentage = pass / (total - na). Returns 0..100."""
    if not items:
        return 0.0
    total = len(items)
    n_na = sum(1 for i in items if (i or {}).get("status") == "na")
    denom = total - n_na
    if denom <= 0:
        return 0.0
    n_pass = sum(1 for i in items if (i or {}).get("status") == "pass")
    return round(100.0 * n_pass / denom, 1)


__all__ = [
    "auto_check",
    "compute_compliance_pct",
    "initial_items",
]
