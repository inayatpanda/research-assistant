"""Dataset citations included in the bibliography.

A `<sup data-citation data-article-id="dataset_<id>">` (or a raw
`[CITE_dataset_<id>]`) inside the manuscript should resolve against the
project's datasets list — NOT silently dropped as an orphan — and render
as a synthetic "Internal research dataset" entry styled per the active
citation style.

See `services/export/bibliography.build_bibliography(datasets=…)` and
`services/citation_format._dataset_entry`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest

from research_api.services.export.bibliography import (
    BibliographyEntry,
    build_bibliography,
)


@dataclass
class Section:
    section_name: str
    content: str


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


@dataclass
class Ds:
    """Minimal DatasetLike — only the fields the bibliography service reads."""
    id: str
    filename: str
    created_at: datetime
    project_id: str = "proj1"
    user_id: str = "user1"


def _sections(by_name: dict[str, str]) -> list[Section]:
    return [Section(section_name=name, content=html) for name, html in by_name.items()]


# --- core resolution --------------------------------------------------------


def test_dataset_citation_indexed_as_entry_one_vancouver():
    ds = Ds(
        id="abc123",
        filename="shoulder_BMI_outcomes.xlsx",
        created_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
    )
    sections = _sections({
        "Results": '<p>The mean differed <sup data-citation data-article-id="dataset_abc123">[1]</sup>.</p>',
    })
    out = build_bibliography(
        articles_by_id={}, sections=sections, style="vancouver", datasets=[ds],
    )
    assert len(out) == 1
    e = out[0]
    assert isinstance(e, BibliographyEntry)
    assert e.number == 1
    assert e.article_id == "dataset_abc123"
    assert e.type == "dataset"
    # Spec example: `1. Project investigators. shoulder_BMI_outcomes.xlsx. 2026. [Internal research dataset].`
    assert e.formatted == (
        "1. Project investigators. shoulder_BMI_outcomes.xlsx. 2026. [Internal research dataset]."
    )


def test_dataset_citation_apa_format():
    ds = Ds(
        id="abc123",
        filename="shoulder_BMI_outcomes.xlsx",
        created_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
    )
    sections = _sections({
        "Results": '<p>foo [CITE_dataset_abc123] bar</p>',
    })
    out = build_bibliography(
        articles_by_id={}, sections=sections, style="apa", datasets=[ds],
    )
    assert len(out) == 1
    e = out[0]
    assert e.type == "dataset"
    # Spec example: `Project investigators. (2026). shoulder_BMI_outcomes.xlsx [Internal research dataset].`
    assert e.formatted == (
        "Project investigators. (2026). shoulder_BMI_outcomes.xlsx [Internal research dataset]."
    )


def test_dataset_citation_harvard_format():
    ds = Ds(
        id="abc123",
        filename="trial.csv",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    sections = _sections({"Results": "[CITE_dataset_abc123]"})
    out = build_bibliography(
        articles_by_id={}, sections=sections, style="harvard", datasets=[ds],
    )
    assert out[0].formatted == (
        "Project investigators (2025) 'trial.csv'. [Internal research dataset]."
    )


def test_dataset_citation_ieee_format():
    ds = Ds(
        id="abc123",
        filename="trial.csv",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    sections = _sections({"Results": "[CITE_dataset_abc123]"})
    out = build_bibliography(
        articles_by_id={}, sections=sections, style="ieee", datasets=[ds],
    )
    assert out[0].formatted.startswith('[1] Project investigators, "trial.csv", 2025.')


# --- interaction with library articles -------------------------------------


def test_articles_and_datasets_interleaved_share_numbering():
    """Datasets appear in citation order alongside article references."""
    ds = Ds(
        id="ds1",
        filename="data.csv",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    art = A(title="Lib paper", authors=["John Doe"], year=2024, journal="J")
    sections = _sections({
        "Results": (
            '<p>First <sup data-citation data-article-id="dataset_ds1">[1]</sup>'
            ' then <sup data-citation data-article-id="a1">[2]</sup>.</p>'
        ),
    })
    out = build_bibliography(
        articles_by_id={"a1": art},
        sections=sections,
        style="vancouver",
        datasets=[ds],
    )
    assert [e.article_id for e in out] == ["dataset_ds1", "a1"]
    assert [e.number for e in out] == [1, 2]
    assert out[0].type == "dataset"
    assert out[1].type == "article"
    assert out[0].formatted.startswith("1. Project investigators. data.csv.")
    assert out[1].formatted.startswith("1. ") is False
    assert out[1].formatted.startswith("2. Doe J.")


def test_dataset_dedupes_across_sections():
    ds = Ds(
        id="ds1",
        filename="data.csv",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    sections = _sections({
        "Methodology": "[CITE_dataset_ds1]",
        "Results": "[CITE_dataset_ds1] [CITE_dataset_ds1]",
        "Discussion": "[CITE_dataset_ds1]",
    })
    out = build_bibliography(
        articles_by_id={}, sections=sections, style="vancouver", datasets=[ds],
    )
    assert len(out) == 1
    assert out[0].number == 1


# --- unknown-id behaviour --------------------------------------------------


def test_unknown_dataset_id_dropped_silently():
    """Cited `dataset_xxx` with no matching project dataset is dropped, matching
    the existing orphan-article policy. The integrity panel is the user-facing
    surface for orphans."""
    sections = _sections({"Results": "[CITE_dataset_missing]"})
    out = build_bibliography(
        articles_by_id={}, sections=sections, style="vancouver", datasets=[],
    )
    assert out == []


def test_datasets_kwarg_optional_back_compat():
    """Callers that haven't been updated yet still work — datasets defaults
    to empty so any dataset citation falls back to the orphan-drop path."""
    art = A(title="Lib paper", authors=["John Doe"], year=2024, journal="J")
    sections = _sections({"Results": "[CITE_a1]"})
    out = build_bibliography(
        articles_by_id={"a1": art}, sections=sections, style="vancouver",
    )
    assert len(out) == 1
    assert out[0].article_id == "a1"


# --- alphabetical ordering (APA / Harvard) ---------------------------------


def test_dataset_sorts_into_alphabetical_apa_list():
    """APA sorts by first-author surname. 'Project investigators' surname is
    'investigators', so a dataset citation should land between authors whose
    surnames sort either side of 'investigators'."""
    ds = Ds(
        id="ds1",
        filename="data.csv",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    a_alpha = A(title="Alpha", authors=["Alice Adams"], year=2024)  # surname: adams
    a_omega = A(title="Omega", authors=["Omar Zenith"], year=2024)  # surname: zenith
    sections = _sections({
        "Results": "[CITE_dataset_ds1] [CITE_a1] [CITE_a2]",
    })
    out = build_bibliography(
        articles_by_id={"a1": a_alpha, "a2": a_omega},
        sections=sections,
        style="apa",
        datasets=[ds],
    )
    # adams < investigators < zenith — alphabetical ordering across mixed types.
    # Article ids are stable identifiers; assert order rather than parsing
    # the formatted strings (article vs dataset entries have different shapes).
    assert [e.article_id for e in out] == ["a1", "dataset_ds1", "a2"]
    # And the formatted entries carry the expected shape for each.
    assert out[0].formatted.startswith("Adams, A.")
    assert out[1].formatted.startswith("Project investigators.")
    assert out[2].formatted.startswith("Zenith, O.")
