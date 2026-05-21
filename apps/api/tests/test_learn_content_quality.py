"""Phase 5a — Content-quality regression.

Catches shoddy or accidentally truncated content: every body must be at
least 80 words, mention assumptions, and contain a worked example.
"""
from __future__ import annotations

import re

from research_api.learn.loader import _reset_cache, load_all_stat_tests


_MIN_WORDS = 80
_WORKED_EXAMPLE_HINT = re.compile(r"worked example", re.IGNORECASE)
_ASSUMPTIONS_HINT = re.compile(r"assumption", re.IGNORECASE)
_REPORTING_HINT = re.compile(r"reporting", re.IGNORECASE)


def setup_function() -> None:
    _reset_cache()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def test_every_body_meets_minimum_word_count() -> None:
    entries = load_all_stat_tests()
    short: list[tuple[str, int]] = []
    for e in entries:
        wc = _word_count(e.body_md)
        if wc < _MIN_WORDS:
            short.append((e.slug, wc))
    assert not short, f"entries below minimum {_MIN_WORDS} words: {short}"


def test_every_body_contains_a_worked_example_section() -> None:
    missing: list[str] = []
    for e in load_all_stat_tests():
        if not _WORKED_EXAMPLE_HINT.search(e.body_md):
            missing.append(e.slug)
    assert not missing, f"entries missing a worked example: {missing}"


def test_every_body_mentions_assumptions_and_reporting() -> None:
    """Each entry must teach the reader about assumptions and how to report."""
    missing_assumptions: list[str] = []
    missing_reporting: list[str] = []
    for e in load_all_stat_tests():
        if not _ASSUMPTIONS_HINT.search(e.body_md):
            missing_assumptions.append(e.slug)
        if not _REPORTING_HINT.search(e.body_md):
            missing_reporting.append(e.slug)
    assert not missing_assumptions, (
        f"entries with no 'assumption' mention: {missing_assumptions}"
    )
    assert not missing_reporting, (
        f"entries with no 'reporting' mention: {missing_reporting}"
    )
