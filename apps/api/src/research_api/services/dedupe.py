"""Duplicate detection for articles.

Strategy:
- DOI exact match (case-insensitive) → score = 1.0
- Otherwise, normalised title fuzzy ratio via rapidfuzz token_sort_ratio (0-100, scaled to 0-1)
"""
from __future__ import annotations

import re
from typing import Protocol

from rapidfuzz import fuzz


class _ArticleLike(Protocol):
    title: str | None
    doi: str | None


def _normalise_title(t: str | None) -> str:
    if not t:
        return ""
    s = t.lower()
    # Strip punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def score_match(a: _ArticleLike, b: _ArticleLike) -> float:
    """Return a 0.0-1.0 similarity score. 1.0 = certain duplicate."""
    if a.doi and b.doi and a.doi.lower() == b.doi.lower():
        return 1.0
    ta = _normalise_title(a.title)
    tb = _normalise_title(b.title)
    if not ta or not tb:
        return 0.0
    return fuzz.token_sort_ratio(ta, tb) / 100.0


def is_duplicate(a: _ArticleLike, b: _ArticleLike, *, threshold: float = 0.9) -> bool:
    return score_match(a, b) >= threshold
