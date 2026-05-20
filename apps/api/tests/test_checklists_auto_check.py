"""Phase 20 (MP20) — Best-effort auto-check heuristic.

The contract: a matching paragraph in the hinted section should produce
``mapped_section`` + ``mapped_text_excerpt`` for that item. No match
should leave both null and the status at ``"unclear"``. User-set
``pass`` / ``fail`` / ``na`` statuses must survive an auto-check pass.
"""
from __future__ import annotations

from research_api.services.checklists.auto_check import (
    auto_check,
    compute_compliance_pct,
    initial_items,
)
from research_api.services.checklists.catalogue import get_catalogue


def _consort():
    cat = get_catalogue("CONSORT_2010")
    assert cat is not None
    return cat


def test_initial_items_seed_every_item_as_unclear() -> None:
    cat = _consort()
    items = initial_items(cat)
    assert len(items) == cat.item_count
    statuses = {i["status"] for i in items}
    assert statuses == {"unclear"}
    # Mapping fields start empty.
    for it in items:
        assert it["mapped_section"] is None
        assert it["mapped_text_excerpt"] is None


def test_auto_check_matches_randomisation_paragraph_in_methods() -> None:
    cat = _consort()
    sections = {
        "Methodology": (
            "Eligible patients were enrolled and gave informed consent.\n\n"
            "Randomisation was performed using a computer-generated block "
            "allocation sequence with block sizes of 4 and 6, stratified by "
            "study site."
        ),
        "Results": "We enrolled 200 participants between January and June.",
    }
    items = auto_check(catalogue=cat, sections_text=sections)
    by_id = {i["item_id"]: i for i in items}

    # Item 8 ("Randomisation: sequence generation") should be mapped to
    # the Methods paragraph mentioning the allocation sequence.
    randomisation_item = by_id["8"]
    assert randomisation_item["mapped_section"] == "Methodology"
    excerpt = randomisation_item["mapped_text_excerpt"]
    assert excerpt is not None
    assert "randomisation" in excerpt.lower() or "allocation" in excerpt.lower()


def test_auto_check_defaults_to_unclear_when_no_match_found() -> None:
    cat = _consort()
    # Empty manuscript — nothing to match against.
    items = auto_check(catalogue=cat, sections_text={"Methodology": "lorem ipsum dolor sit amet."})
    for it in items:
        assert it["status"] == "unclear"
        assert it["mapped_section"] is None
        assert it["mapped_text_excerpt"] is None


def test_auto_check_preserves_user_set_status_and_comments() -> None:
    cat = _consort()
    current = initial_items(cat)
    current[0]["status"] = "pass"
    current[0]["comment"] = "Verified manually"
    current[1]["status"] = "na"
    items = auto_check(catalogue=cat, sections_text={}, current_items=current)
    by_id = {i["item_id"]: i for i in items}
    assert by_id["1"]["status"] == "pass"
    assert by_id["1"]["comment"] == "Verified manually"
    assert by_id["2"]["status"] == "na"


def test_auto_check_excerpt_is_capped_at_80_chars() -> None:
    cat = _consort()
    long_para = (
        "Randomisation was implemented through a sequential web portal "
        "with permuted blocks and stratification across the four recruiting "
        "centres in this multicentre trial protocol."
    )
    sections = {"Methodology": long_para}
    items = auto_check(catalogue=cat, sections_text=sections)
    by_id = {i["item_id"]: i for i in items}
    excerpt = by_id["8"]["mapped_text_excerpt"]
    assert excerpt is not None
    assert len(excerpt) <= 80


def test_auto_check_falls_back_to_other_sections_when_hint_empty() -> None:
    cat = _consort()
    # Put the randomisation text in Discussion (wrong section per hint) —
    # the matcher should still surface it after the hint pass fails.
    sections = {
        "Methodology": "Lorem ipsum dolor sit amet.",
        "Discussion": (
            "We discuss the implications. Randomisation by computer-"
            "generated allocation sequence was the primary design feature."
        ),
    }
    items = auto_check(catalogue=cat, sections_text=sections)
    by_id = {i["item_id"]: i for i in items}
    assert by_id["8"]["mapped_section"] == "Discussion"


def test_compute_compliance_pct_excludes_na_from_denominator() -> None:
    items = [
        {"item_id": "1", "status": "pass"},
        {"item_id": "2", "status": "pass"},
        {"item_id": "3", "status": "fail"},
        {"item_id": "4", "status": "unclear"},
        {"item_id": "5", "status": "na"},  # excluded from denominator
        {"item_id": "6", "status": "na"},
    ]
    # 2 pass / (6 - 2 na) = 50%
    assert compute_compliance_pct(items) == 50.0


def test_compute_compliance_pct_all_na_returns_zero() -> None:
    items = [{"item_id": str(i), "status": "na"} for i in range(5)]
    assert compute_compliance_pct(items) == 0.0


def test_auto_check_does_not_pre_fill_status_as_pass() -> None:
    """Hard rule: auto-check NEVER sets status to 'pass'. Only the user does."""
    cat = _consort()
    # Aggressive multi-paragraph match — even then, status stays unclear.
    sections = {
        "Methodology": (
            "Randomisation was performed using a computer-generated "
            "sequence with block stratification. Blinding of assessors "
            "was maintained throughout. Sample size was calculated to "
            "detect a 10% difference."
        ),
    }
    items = auto_check(catalogue=cat, sections_text=sections)
    for it in items:
        assert it["status"] in ("unclear",), (
            f"item {it['item_id']} got status={it['status']!r}; "
            "auto-check must not set status to pass"
        )
