"""MP16 — Grey-literature ``reference_type`` rendering across styles.

Each non-``journal_article`` reference type emits a stable shape regardless
of the configured citation style. The grey-lit dispatch takes precedence
over the per-style journal-article formatter so a thesis reads
``Author. Title [thesis]. Univ; 2024.`` whether the project is configured
for Vancouver, Lancet, NEJM, or BJSM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest

from research_api.services.citation_format import bibliography_entry, format_entry


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


# ─── Web resource ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("style", ["vancouver", "lancet", "jbjs_am"])
def test_web_resource_shape(style: str):
    a = A(
        title="WHO TB Report",
        authors=["World Health Organization"],
        year=2024,
        url="https://who.int/tb/report",
        reference_type="web_resource",
    )
    out = format_entry(a, style=style)
    assert "[Internet]" in out
    today = date.today().isoformat()
    assert today in out
    assert "Available from: https://who.int/tb/report" in out


# ─── Thesis ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("style", ["vancouver", "nejm", "bjsm"])
def test_thesis_shape(style: str):
    a = A(
        title="Hip biomechanics post-arthroplasty",
        authors=["Jane Doe"],
        year=2023,
        journal="University of Edinburgh",
        reference_type="thesis",
    )
    out = format_entry(a, style=style)
    assert "[thesis]" in out
    assert "Doe J" in out
    assert "University of Edinburgh" in out
    assert "2023" in out


# ─── Preprint ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("style", ["vancouver", "lancet", "jama"])
def test_preprint_shape(style: str):
    a = A(
        title="Novel marker for OA",
        authors=["John Smith", "Aisha Khan"],
        year=2024,
        journal="medRxiv",
        doi="10.1101/2024.01.01.000001",
        reference_type="preprint",
    )
    out = format_entry(a, style=style)
    assert "[preprint]" in out
    assert "medRxiv" in out
    assert "doi:10.1101/2024.01.01.000001" in out


# ─── Registry record ────────────────────────────────────────────────────────


@pytest.mark.parametrize("style", ["vancouver", "nejm", "bjj"])
def test_registry_record_shape(style: str):
    a = A(
        title="THA outcomes RCT NCT01234567",
        year=2022,
        journal="ClinicalTrials.gov",
        url="https://clinicaltrials.gov/ct2/show/NCT01234567",
        reference_type="registry_record",
    )
    out = format_entry(a, style=style)
    assert "ClinicalTrials.gov" in out
    assert "Available from: https://clinicaltrials.gov" in out
    assert "2022" in out


# ─── Numbered prefix preserved for grey-lit refs ───────────────────────────


def test_grey_lit_numbered_prefix_vancouver():
    a = A(
        title="Surgery handbook",
        authors=["Jane Doe"],
        year=2023,
        journal="Oxford Univ Press",
        reference_type="book",
    )
    out = bibliography_entry(a, number=5, style="vancouver")
    assert out.startswith("5. ")
    assert "Surgery handbook." in out


def test_grey_lit_numbered_prefix_ieee():
    a = A(
        title="Reg record",
        year=2024,
        journal="EUClinicalTrials",
        reference_type="registry_record",
    )
    out = bibliography_entry(a, number=2, style="ieee")
    assert out.startswith("[2] ")
