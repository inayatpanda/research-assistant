"""Phase 12 — Cover-letter prompt builder unit tests."""
from __future__ import annotations

from research_api.services.ai.prompts.cover_letter import (
    COVER_LETTER_SYSTEM_PROMPT,
    build_cover_letter_prompt,
)


def test_build_cover_letter_prompt_uses_all_fields() -> None:
    system, user = build_cover_letter_prompt(
        title="Knee OA RCT",
        abstract="Background: knee pain. Methods: 200 patients.",
        journal_label="JBJS",
        novelty_points=["First multicentre study", "Long follow-up"],
        corresponding_name="Dr. A. Smith",
        corresponding_affiliation="St. Mary's Hospital, London, UK",
        corresponding_email="a.smith@example.org",
        conflicts_statement="Authors declare no COI.",
    )
    assert system == COVER_LETTER_SYSTEM_PROMPT
    assert "JBJS" in user
    assert "Knee OA RCT" in user
    assert "First multicentre study" in user
    assert "Long follow-up" in user
    assert "Dr. A. Smith" in user
    assert "St. Mary's Hospital" in user
    assert "a.smith@example.org" in user
    assert "Authors declare no COI." in user


def test_build_cover_letter_prompt_falls_back_when_missing() -> None:
    _system, user = build_cover_letter_prompt(
        title="",
        abstract=None,
        journal_label="",
        novelty_points=None,
        corresponding_name=None,
        corresponding_affiliation=None,
        corresponding_email=None,
        conflicts_statement=None,
    )
    # Fallbacks are present so the model never sees a literal empty string.
    assert "(untitled manuscript)" in user
    assert "(no abstract provided)" in user
    assert "(none provided)" in user
    assert "(corresponding author)" in user
    # The default COI statement is supplied as a fallback.
    assert "no conflicts of interest" in user.lower()


def test_build_cover_letter_prompt_trims_long_abstract() -> None:
    long_abstract = "x" * 10000
    _, user = build_cover_letter_prompt(
        title="t",
        abstract=long_abstract,
        journal_label="J",
        novelty_points=None,
        corresponding_name=None,
        corresponding_affiliation=None,
        corresponding_email=None,
        conflicts_statement=None,
    )
    # Limit set to 4000 chars in builder.
    # User prompt template adds wrapping text but the abstract slice is bounded.
    assert user.count("x") <= 4000
