from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

from research_api.services.review.prisma import (
    PrismaCounts,
    count_flow,
    render_svg,
)


@dataclass
class FakeSearch:
    n_results: int
    database_name: str = "PubMed"
    query_string: str = "q"
    date_searched: datetime = datetime.now(timezone.utc)


@dataclass
class FakeScreen:
    stage: str
    decision: str
    article_id: str = "a1"
    exclusion_category: str | None = None


EXCLUSION_KEYS = (
    "population",
    "intervention",
    "outcome",
    "study_design",
    "language",
    "duplicate",
    "other",
)


def test_identified_sums_n_results():
    searches = [FakeSearch(n_results=10), FakeSearch(n_results=25), FakeSearch(n_results=3)]
    counts = count_flow(search_records=searches, screening_records=[])
    assert counts.identified == 38


def test_identified_zero_when_no_records():
    counts = count_flow(search_records=[], screening_records=[])
    assert counts.identified == 0
    assert counts.after_dedupe == 0
    assert counts.screened == 0
    assert counts.excluded_title == 0
    assert counts.full_text_assessed == 0
    assert counts.included == 0
    assert all(v == 0 for v in counts.excluded_full.values())
    assert set(counts.excluded_full.keys()) == set(EXCLUSION_KEYS)


def test_after_dedupe_equals_identified_v1():
    searches = [FakeSearch(n_results=100)]
    counts = count_flow(search_records=searches, screening_records=[])
    assert counts.after_dedupe == counts.identified == 100


def test_screened_excludes_pending():
    screens = [
        FakeScreen(stage="title_abstract", decision="pending", article_id="a1"),
        FakeScreen(stage="title_abstract", decision="include", article_id="a2"),
        FakeScreen(stage="title_abstract", decision="exclude", article_id="a3"),
        FakeScreen(stage="title_abstract", decision="maybe", article_id="a4"),
    ]
    counts = count_flow(search_records=[], screening_records=screens)
    assert counts.screened == 3


def test_excluded_title_only_counts_title_stage():
    screens = [
        FakeScreen(stage="title_abstract", decision="exclude", article_id="a1"),
        FakeScreen(stage="title_abstract", decision="exclude", article_id="a2"),
        FakeScreen(stage="full_text", decision="exclude", article_id="a3"),
    ]
    counts = count_flow(search_records=[], screening_records=screens)
    assert counts.excluded_title == 2


def test_full_text_assessed_requires_title_include_or_maybe():
    screens = [
        FakeScreen(stage="title_abstract", decision="include", article_id="a1"),
        FakeScreen(stage="full_text", decision="include", article_id="a1"),
        FakeScreen(stage="title_abstract", decision="maybe", article_id="a2"),
        FakeScreen(stage="full_text", decision="exclude", article_id="a2",
                   exclusion_category="population"),
        FakeScreen(stage="title_abstract", decision="exclude", article_id="a3"),
        FakeScreen(stage="full_text", decision="include", article_id="a3"),
    ]
    counts = count_flow(search_records=[], screening_records=screens)
    assert counts.full_text_assessed == 3


def test_full_text_without_title_stage_still_counts():
    screens = [
        FakeScreen(stage="full_text", decision="include", article_id="a1"),
        FakeScreen(stage="full_text", decision="exclude", article_id="a2",
                   exclusion_category="outcome"),
    ]
    counts = count_flow(search_records=[], screening_records=screens)
    assert counts.full_text_assessed == 2
    assert counts.included == 1


def test_excluded_full_buckets_categories():
    screens = [
        FakeScreen(stage="full_text", decision="exclude", article_id="a1",
                   exclusion_category="population"),
        FakeScreen(stage="full_text", decision="exclude", article_id="a2",
                   exclusion_category="population"),
        FakeScreen(stage="full_text", decision="exclude", article_id="a3",
                   exclusion_category="duplicate"),
        FakeScreen(stage="full_text", decision="exclude", article_id="a4",
                   exclusion_category="other"),
    ]
    counts = count_flow(search_records=[], screening_records=screens)
    assert set(counts.excluded_full.keys()) == set(EXCLUSION_KEYS)
    assert counts.excluded_full["population"] == 2
    assert counts.excluded_full["duplicate"] == 1
    assert counts.excluded_full["other"] == 1
    assert counts.excluded_full["intervention"] == 0
    assert counts.excluded_full["outcome"] == 0
    assert counts.excluded_full["study_design"] == 0
    assert counts.excluded_full["language"] == 0


def test_included_counts_full_text_includes_only():
    screens = [
        FakeScreen(stage="full_text", decision="include", article_id="a1"),
        FakeScreen(stage="full_text", decision="include", article_id="a2"),
        FakeScreen(stage="full_text", decision="exclude", article_id="a3",
                   exclusion_category="population"),
        FakeScreen(stage="title_abstract", decision="include", article_id="a4"),
    ]
    counts = count_flow(search_records=[], screening_records=screens)
    assert counts.included == 2


def test_render_svg_returns_string_with_box_for_each_count():
    counts = PrismaCounts(
        identified=120,
        after_dedupe=110,
        screened=110,
        excluded_title=70,
        full_text_assessed=40,
        excluded_full={k: 0 for k in EXCLUSION_KEYS} | {"population": 5, "outcome": 3},
        included=32,
    )
    svg = render_svg(counts)
    assert isinstance(svg, str)
    assert "Records identified" in svg
    assert "Records screened" in svg
    assert "Studies included" in svg
    assert "120" in svg
    assert "110" in svg
    assert "70" in svg
    assert "40" in svg
    assert "32" in svg
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_render_svg_handles_zero_counts():
    counts = PrismaCounts(
        identified=0,
        after_dedupe=0,
        screened=0,
        excluded_title=0,
        full_text_assessed=0,
        excluded_full={k: 0 for k in EXCLUSION_KEYS},
        included=0,
    )
    svg = render_svg(counts)
    assert "NaN" not in svg
    assert "None" not in svg
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_render_svg_escapes_xml_in_title():
    counts = PrismaCounts(
        identified=1, after_dedupe=1, screened=1, excluded_title=0,
        full_text_assessed=1, excluded_full={k: 0 for k in EXCLUSION_KEYS},
        included=1,
    )
    svg = render_svg(counts, title="<script>alert(1)</script>")
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
