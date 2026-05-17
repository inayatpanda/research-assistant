"""Find 'Long Form (LF)' patterns in manuscript text.

Heuristic: a parenthesised token like (ABC) is an abbreviation defined inline
when the immediately preceding N words start with the same N letters (case
insensitive on the words; uppercase letters in the abbreviation tell us N).
"""
from __future__ import annotations

import re

_ABBR_RE = re.compile(r"\(([A-Z][A-Za-z]{1,9}s?)\)")


def scan_abbreviations(text: str) -> list[tuple[str, str]]:
    """Return list of (short_form, long_form) tuples in order of first appearance,
    deduplicated by short_form."""
    if not text:
        return []
    out: dict[str, str] = {}
    for m in _ABBR_RE.finditer(text):
        abbr = m.group(1)
        # Count *uppercase* letters in the abbreviation — that's how many words
        # back we need to walk. Trailing 's' for plural ('PROMs') doesn't count.
        letters = [c for c in abbr if c.isupper()]
        if len(letters) < 2:
            continue
        before = text[: m.start()].rstrip()
        words = re.findall(r"[A-Za-z][A-Za-z-]*", before)
        if len(words) < len(letters):
            continue
        tail = words[-len(letters):]
        initials = "".join(w[0].upper() for w in tail)
        if initials != "".join(letters):
            continue
        long_form = " ".join(tail)
        if abbr not in out:
            out[abbr] = long_form
    return list(out.items())
