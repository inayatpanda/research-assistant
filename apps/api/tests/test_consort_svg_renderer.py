"""Phase 8.7 — CONSORT SVG renderer tests."""
from __future__ import annotations

from xml.etree import ElementTree as ET

from research_api.services.consort.counter import derive_flow
from research_api.services.consort.svg_renderer import render_consort_svg


def test_render_consort_svg_returns_well_formed_xml() -> None:
    svg = render_consort_svg(derive_flow({}))
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_render_consort_svg_contains_all_numbers_when_populated() -> None:
    flow = derive_flow({
        "enrollment_assessed": 200,
        "enrollment_excluded": 50,
        "randomised": 150,
        "allocated_intervention": 75,
        "allocated_control": 75,
        "intervention_received": 70,
        "control_received": 72,
        "intervention_lost_followup": 3,
        "control_lost_followup": 2,
        "intervention_discontinued": 1,
        "control_discontinued": 1,
        "intervention_analysed": 71,
        "control_analysed": 72,
    })
    svg = render_consort_svg(flow)
    # Spot-check each number is present
    for n in (200, 50, 150, 75, 70, 72, 71):
        assert f"n = {n}" in svg


def test_render_consort_svg_shows_em_dash_for_missing_numbers() -> None:
    svg = render_consort_svg(derive_flow({}))
    assert "—" in svg


def test_render_consort_svg_includes_reasons_when_present() -> None:
    flow = derive_flow({
        "enrollment_excluded": 50,
        "enrollment_excluded_reasons": {"Declined": 30, "Ineligible": 20},
    })
    svg = render_consort_svg(flow)
    assert "Declined" in svg and "Ineligible" in svg
    assert "Reasons" in svg


def test_render_consort_svg_omits_reasons_block_when_empty() -> None:
    flow = derive_flow({"enrollment_excluded": 50})
    svg = render_consort_svg(flow)
    # No "Reasons" heading when reasons dict absent or empty
    assert "Reasons" not in svg


def test_render_consort_svg_html_escapes_reason_labels() -> None:
    flow = derive_flow({
        "enrollment_excluded": 5,
        "enrollment_excluded_reasons": {"<script>alert(1)</script>": 5},
    })
    svg = render_consort_svg(flow)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_render_consort_svg_root_element_has_xmlns() -> None:
    svg = render_consort_svg(derive_flow({}))
    root = ET.fromstring(svg)
    # ElementTree namespaces appear in the tag itself
    assert "http://www.w3.org/2000/svg" in root.tag
