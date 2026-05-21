"""Phase 4.6 — Peer-review prompt unit tests."""
from __future__ import annotations

from research_api.services.ai.prompts.peer_review import (
    PEER_REVIEW_SYSTEM_PROMPT,
    build_peer_review_prompt,
)


def test_system_prompt_lists_structured_output_keys() -> None:
    text = PEER_REVIEW_SYSTEM_PROMPT
    for key in (
        "overall_impression",
        "strengths",
        "major_issues",
        "minor_issues",
        "methodological_concerns",
        "statistical_concerns",
        "reporting_concerns",
        "presentation_concerns",
        "references_concerns",
        "suggestions_for_improvement",
        "recommendation",
    ):
        assert key in text, f"system prompt missing key {key!r}"
    # Recommendation enum must be present so the model can pick one.
    for level in ("reject", "major_revision", "minor_revision", "accept"):
        assert level in text


def test_system_prompt_states_no_hallucination_and_section_naming_rules() -> None:
    text = PEER_REVIEW_SYSTEM_PROMPT.lower()
    # No-hallucination rule must be explicit.
    assert "do not invent" in text or "no hallucinat" in text
    # Section-naming rule must reference at least a couple of canonical
    # IMRaD sections so the model knows to cite them.
    for sect in ("introduction", "methods", "results", "discussion"):
        assert sect in text


def test_user_prompt_includes_title_study_type_and_metadata_counts() -> None:
    system, user = build_peer_review_prompt(
        title="A trial of widgets",
        study_type="Randomised Controlled Trial",
        manuscript_text="Body of manuscript " * 50,
        metadata={
            "n_figures": 3,
            "n_tables": 2,
            "n_references": 25,
            "n_authors": 4,
        },
    )
    assert system == PEER_REVIEW_SYSTEM_PROMPT
    assert "A trial of widgets" in user
    assert "Randomised Controlled Trial" in user
    assert "Figures: 3" in user
    assert "Tables: 2" in user
    assert "References cited: 25" in user
    assert "Authors listed: 4" in user
    # Body must appear (truncated to 60k).
    assert "Body of manuscript" in user
