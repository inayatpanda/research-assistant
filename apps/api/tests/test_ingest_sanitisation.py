"""DEMO-FIX-C — Header sanitiser regression tests.

The sanitiser maps arbitrary spreadsheet headers (whitespace, parens,
leading digits, punctuation, Unicode) to Python-identifier-safe names so
the runner's column-name whitelist accepts them. The original spelling is
preserved as a display label on the DatasetVariable row.

These tests live at the pure-function level: they cover the rules in
research_api.services.stats.ingest.sanitize_header and the collision
resolution in sanitize_headers, plus the end-to-end ingest() path that
combines both with column inference.
"""
from __future__ import annotations

import io

import pandas as pd
import pytest

from research_api.services.stats.ingest import (
    CSV_MIME,
    ingest,
    sanitize_header,
    sanitize_headers,
)


def test_sanitize_header_replaces_whitespace_and_parens() -> None:
    """The canonical example from the spec.

    "VAS Pain at 6 months (post-op)" → must become a valid Python
    identifier with no spaces or parens.
    """
    assert sanitize_header("VAS Pain at 6 months (post-op)") == "vas_pain_at_6_months_post_op"


def test_sanitize_header_handles_hyphens_and_dots() -> None:
    assert sanitize_header("follow-up.6m") == "follow_up_6m"
    assert sanitize_header("BMI/kg.m2") == "bmi_kg_m2"


def test_sanitize_header_prefixes_leading_digits() -> None:
    """Identifiers can't start with a digit — the sanitiser prefixes c_."""
    assert sanitize_header("6m_pain").startswith("c_")
    assert sanitize_header("6m_pain") == "c_6m_pain"
    assert sanitize_header("123") == "c_123"


def test_sanitize_header_empty_and_unicode_fallback() -> None:
    """Empty / all-punctuation / non-ASCII headers fall back to col_<idx>."""
    assert sanitize_header("", index=0) == "col_0"
    assert sanitize_header("   ", index=3) == "col_3"
    # All-punctuation collapses to empty post-strip → fallback.
    assert sanitize_header("***", index=7) == "col_7"
    # Pure non-ASCII Unicode word characters get stripped by the regex.
    # The sanitiser maps them all to `_`, so the post-collapse string is
    # empty and falls back to col_<idx>.
    assert sanitize_header("патент", index=2) == "col_2"


def test_sanitize_header_idempotent() -> None:
    """Applying the sanitiser twice must equal applying it once."""
    examples = [
        "VAS Pain at 6 months (post-op)",
        "follow-up.6m",
        "6m_pain",
        "Already_Clean",
        "   weird ",
        "BMI / kg·m²",
    ]
    for raw in examples:
        once = sanitize_header(raw)
        twice = sanitize_header(once)
        assert once == twice, f"non-idempotent for {raw!r}: {once!r} != {twice!r}"


def test_sanitize_header_lowercase() -> None:
    assert sanitize_header("AGE_YEARS") == "age_years"
    assert sanitize_header("Sex") == "sex"


def test_sanitize_headers_collision_resolution() -> None:
    """Two raw headers that sanitise to the same value get _2 / _3 suffixes."""
    raws = ["Sex", "sex", "SEX"]
    sanitised, report = sanitize_headers(raws)
    assert sanitised == ["sex", "sex_2", "sex_3"]
    # All three are renamed in the report — "sex" → "sex_2" is a rename
    # because the canonical name went to a later index.
    pairs = {(o, s) for o, s in report}
    assert ("Sex", "sex") in pairs
    assert ("sex", "sex_2") in pairs
    assert ("SEX", "sex_3") in pairs


def test_sanitize_headers_no_op_when_clean() -> None:
    raws = ["age", "sex", "bmi"]
    sanitised, report = sanitize_headers(raws)
    assert sanitised == raws
    assert report == []


def test_sanitize_headers_report_pairs_match() -> None:
    """Every report entry's sanitised value appears in the output list."""
    raws = ["6m_pain", "VAS Score", "Group (T1)"]
    sanitised, report = sanitize_headers(raws)
    assert len(sanitised) == 3
    for original, new in report:
        assert new in sanitised
        # Original is preserved verbatim (case + spaces).
        assert original in raws


def test_ingest_csv_with_unsafe_headers_renames_and_reports() -> None:
    """Full ingest path: CSV with parens + spaces is sanitised."""
    csv = b"VAS Pain at 6 months (post-op),BMI group\n3.5,High\n4.2,Low\n"
    result = ingest(csv, CSV_MIME)
    assert result.n_rows == 2
    assert result.n_columns == 2
    names = [c.name for c in result.columns]
    assert names == ["vas_pain_at_6_months_post_op", "bmi_group"]
    # Display labels preserve the original spelling.
    labels = [c.display_label for c in result.columns]
    assert labels == ["VAS Pain at 6 months (post-op)", "BMI group"]
    # Sanitisation report lists both renames.
    pairs = {(e["original"], e["sanitised"]) for e in result.header_sanitisation_report}
    assert ("VAS Pain at 6 months (post-op)", "vas_pain_at_6_months_post_op") in pairs
    assert ("BMI group", "bmi_group") in pairs


def test_ingest_with_clean_headers_reports_empty() -> None:
    """No renames → empty header_sanitisation_report."""
    csv = b"age,sex,bmi\n42,M,24.1\n31,F,21.0\n"
    result = ingest(csv, CSV_MIME)
    assert result.header_sanitisation_report == []
    assert [c.display_label for c in result.columns] == ["age", "sex", "bmi"]


def test_ingest_collisions_get_suffixed_and_dataframe_loads() -> None:
    """When two raw headers collapse to the same canonical, both columns
    survive in the report and the inferred-column list still has unique
    names (no DataFrame KeyError)."""
    csv = b"Sex,sex,SEX\nM,1,male\nF,0,female\n"
    result = ingest(csv, CSV_MIME)
    names = [c.name for c in result.columns]
    # Exactly three columns, all unique.
    assert len(set(names)) == 3
    # All three originals appear as display labels.
    labels = [c.display_label for c in result.columns]
    assert sorted(labels) == ["SEX", "Sex", "sex"]


def test_ingest_keeps_runner_whitelist_safe() -> None:
    """The sanitiser MUST always produce names that satisfy the runner's
    ``^[A-Za-z_][A-Za-z0-9_]*$`` whitelist — this is the security guarantee."""
    import re

    rx = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    raws = [
        "VAS Pain at 6 months (post-op)",
        "6m_pain",
        "BMI / kg·m²",
        "   weird ",
        "Group(T-1)",
        "%change",
        "",  # empty
    ]
    sanitised, _ = sanitize_headers(raws)
    for s in sanitised:
        assert rx.match(s), f"runner would reject {s!r}"


def test_ingest_csv_with_leading_digit_headers() -> None:
    """Leading-digit headers get the c_ prefix and load cleanly."""
    csv = b"6m_pain,12m_pain\n3.5,4.2\n2.1,3.0\n"
    result = ingest(csv, CSV_MIME)
    names = [c.name for c in result.columns]
    assert names == ["c_6m_pain", "c_12m_pain"]
