"""MP16 — Per-journal citation-style golden strings.

Each new style (Lancet / NEJM / BJJ / JBJS-Am / BJSM / JAMA) is exercised
against:
  1. A FULL article (all fields populated).
  2. A SPARSE article (missing journal/issue/pages/doi — verifies graceful
     degradation, no `KeyError` / no stray punctuation).

Numbered prefixes are checked because the bibliography pipeline relies on
``bibliography_entry(..., number=N)`` rendering them for every Vancouver-
family variant.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from research_api.services.citation_format import (
    ET_AL_THRESHOLDS,
    bibliography_entry,
    format_entry,
)


@dataclass
class A:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    reference_type: str = "journal_article"
    url: str | None = None


def _full() -> A:
    return A(
        title="Hip arthroplasty outcomes",
        authors=["John Doe", "Jane Smith", "Kira Patel"],
        year=2024,
        journal="J Orthop Res",
        volume="42",
        issue="3",
        pages="100-110",
        doi="10.1234/abc",
    )


def _sparse() -> A:
    return A(
        title="Sparse paper",
        authors=["John Doe", "Jane Smith"],
        year=2023,
    )


# ─── Lancet ─────────────────────────────────────────────────────────────────


def test_lancet_full_entry():
    out = format_entry(_full(), style="lancet")
    assert "Doe J, Smith J, Patel K." in out
    assert "Hip arthroplasty outcomes." in out
    assert "J Orthop Res" in out
    # Lancet quirk: space between year and `;`
    assert "2024; 42: 100-110." in out
    assert "doi:10.1234/abc" in out


def test_lancet_sparse_entry():
    out = format_entry(_sparse(), style="lancet")
    assert "Doe J, Smith J." in out
    assert "Sparse paper." in out
    assert "2023." in out
    # No volume/pages → no stray semicolon or hanging punctuation
    assert ";" not in out


# ─── NEJM ───────────────────────────────────────────────────────────────────


def test_nejm_full_entry():
    out = format_entry(_full(), style="nejm")
    # 3 authors fits exactly within NEJM threshold (et-al only after 3)
    assert "Doe J, Smith J, Patel K." in out
    assert "2024;42:100-110." in out  # no spaces in the year;vol:pages
    assert "doi:10.1234/abc" in out


def test_nejm_et_al_after_3():
    """NEJM uses ``et al.`` once the list exceeds 3 authors."""
    a = _full()
    a.authors = ["John Doe", "Jane Smith", "Kira Patel", "Lee Wong"]
    out = format_entry(a, style="nejm")
    assert "et al." in out
    assert "Lee Wong" not in out  # 4th author replaced by et al.


def test_nejm_sparse_entry():
    out = format_entry(_sparse(), style="nejm")
    assert "Doe J, Smith J." in out
    assert "2023." in out


# ─── BJJ (Bone & Joint Journal) ─────────────────────────────────────────────


def test_bjj_full_entry():
    out = format_entry(_full(), style="bjj")
    assert "Bone Joint J" in out
    # NB: BJJ ignores the supplied `journal` and forces "Bone Joint J"
    assert "J Orthop Res" not in out
    assert "2024;42(3):100-110." in out


def test_bjj_sparse_entry():
    out = format_entry(_sparse(), style="bjj")
    assert "Bone Joint J" in out
    assert "2023." in out


# ─── JBJS-Am ────────────────────────────────────────────────────────────────


def test_jbjs_am_full_entry():
    out = format_entry(_full(), style="jbjs_am")
    # JBJS-Am uses a period after the journal abbreviation
    assert "J Bone Joint Surg Am." in out
    assert "2024;42(3):100-110." in out


def test_jbjs_am_uses_6_author_threshold():
    """JBJS-Am follows ICMJE: 6 authors then ``et al.``."""
    assert ET_AL_THRESHOLDS["jbjs_am"] == 6
    a = _full()
    a.authors = [f"Author{i} X" for i in range(1, 8)]  # 7 authors
    out = format_entry(a, style="jbjs_am")
    assert "et al." in out
    assert "Author7 X" not in out


# ─── BJSM ───────────────────────────────────────────────────────────────────


def test_bjsm_full_entry():
    out = format_entry(_full(), style="bjsm")
    assert "Br J Sports Med" in out
    assert "2024;42:100-110." in out  # no issue parenthesis


def test_bjsm_sparse_entry():
    out = format_entry(_sparse(), style="bjsm")
    assert "Br J Sports Med" in out
    assert "2023." in out


# ─── JAMA ───────────────────────────────────────────────────────────────────


def test_jama_full_entry():
    out = format_entry(_full(), style="jama")
    # JAMA forces journal abbrev + period
    assert "JAMA." in out
    assert "2024;42(3):100-110." in out


def test_jama_sparse_entry():
    out = format_entry(_sparse(), style="jama")
    assert "JAMA." in out
    assert "2023." in out


# ─── Numbered prefixes for the new styles ───────────────────────────────────


def test_numbered_prefix_for_journal_variants():
    """``bibliography_entry(..., number=N)`` must prefix ``N. `` for every
    Vancouver-family variant (except IEEE which uses ``[N]``)."""
    a = _full()
    for style in ("lancet", "nejm", "bjj", "jbjs_am", "bjsm", "jama"):
        out = bibliography_entry(a, number=3, style=style)
        assert out.startswith("3. "), (style, out)
