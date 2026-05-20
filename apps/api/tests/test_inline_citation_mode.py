"""MP16 — Inline citation rendering mode unit tests.

``format_inline_citation`` is the source-of-truth contract that the TipTap
CitationNodeView mirrors on the frontend; verifying it here means the
backend export pipeline + the rich-text editor stay in lockstep.
"""
from __future__ import annotations

import pytest

from research_api.services.citation_format import format_inline_citation


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("bracket_numeric", "[7]"),
        ("superscript_numeric", "<sup>7</sup>"),
        ("author_year_parens", "(7)"),  # numeric fallback when used numerically
    ],
)
def test_format_inline_citation_per_mode(mode: str, expected: str):
    assert format_inline_citation(number=7, mode=mode) == expected


def test_format_inline_citation_default_mode_is_brackets():
    """No mode arg → falls back to ``bracket_numeric`` (canonical default)."""
    assert format_inline_citation(number=12) == "[12]"


def test_format_inline_citation_handles_large_numbers():
    assert format_inline_citation(number=1024, mode="superscript_numeric") == "<sup>1024</sup>"
