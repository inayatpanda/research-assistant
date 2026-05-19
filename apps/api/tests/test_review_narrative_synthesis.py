"""Phase 19 (MP19) — Narrative synthesis + outcome instruments HTML builders."""
from __future__ import annotations

from research_api.services.review.narrative_synthesis import (
    build_narrative_table_html,
    build_outcome_instruments_table_html,
)


def test_narrative_table_renders_each_entry():
    entries = [
        {
            "outcome_label": "Pain",
            "instrument": "VAS",
            "range_text": "0–10",
            "direction": "lower_better",
            "narrative_html": "<p>Reduced.</p>",
            "study_citations": ["a1", "a2"],
        },
        {
            "outcome_label": "Function",
            "instrument": "Oxford Hip",
            "range_text": "0–48",
            "direction": "higher_better",
            "narrative_html": "<p>Improved.</p>",
            "study_citations": ["a1"],
        },
    ]
    html = build_narrative_table_html(entries)
    # 1 header <tr> + 2 body <tr> = 3 total
    assert html.count("<tr>") == 3
    # Body has exactly 2 data rows.
    body = html.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert body.count("<tr>") == 2
    assert "Pain" in html
    assert "VAS" in html
    assert "Oxford Hip" in html
    assert "[CITE_a1]" in html
    assert "[CITE_a2]" in html
    assert 'class="narrative-synthesis-table"' in html


def test_narrative_direction_renders_arrows():
    entries = [{
        "outcome_label": "A", "instrument": "I", "range_text": "0-10",
        "direction": "higher_better", "narrative_html": "", "study_citations": [],
    }]
    html = build_narrative_table_html(entries)
    assert "↑" in html


def test_narrative_escapes_dangerous_outcome_label():
    entries = [{
        "outcome_label": "<script>alert(1)</script>",
        "instrument": "X", "range_text": "", "direction": "neutral",
        "narrative_html": "<p>ok</p>", "study_citations": [],
    }]
    html = build_narrative_table_html(entries)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_outcome_instruments_builds_grid_with_study_columns():
    rows = [
        {
            "outcome_label": "Pain", "instrument_name": "VAS",
            "score_range_low": 0, "score_range_high": 10, "mid": 2,
            "study_values": [
                {"article_id": "s1", "group_label": "T", "value": 3.2, "sd_or_ci": "1.0", "n": 50},
                {"article_id": "s2", "group_label": "T", "value": 4.5, "sd_or_ci": "1.2", "n": 60},
            ],
        },
        {
            "outcome_label": "Pain", "instrument_name": "NRS",
            "score_range_low": 0, "score_range_high": 10, "mid": 2,
            "study_values": [
                {"article_id": "s2", "group_label": "T", "value": 5.0, "sd_or_ci": "0.9", "n": 60},
                {"article_id": "s3", "group_label": "T", "value": 6.1, "sd_or_ci": "1.5", "n": 40},
            ],
        },
    ]
    html = build_outcome_instruments_table_html(rows)
    assert "[CITE_s1]" in html
    assert "[CITE_s2]" in html
    assert "[CITE_s3]" in html
    assert "VAS" in html
    assert "NRS" in html
    # s3 should be a "—" cell in the VAS row
    assert "—" in html


def test_outcome_instruments_handles_empty_input():
    html = build_outcome_instruments_table_html([])
    assert 'class="outcome-instruments-table"' in html
    assert "<tbody></tbody>" in html
