"""Phase 14 (MP14) — PROSPERO default_draft unit tests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from research_api.services.review.prospero import (
    PROSPERO_FIELDS,
    default_draft,
    format_for_export,
)


@dataclass
class FakeReview:
    id: str = "r1"
    project_id: str = "p1"
    pico_population: str | None = "Adults with hypertension"
    pico_intervention: str | None = "Drug X"
    pico_comparator: str | None = "Placebo"
    pico_outcome: str | None = "Stroke incidence"
    eligibility_inclusion: str | None = "RCTs in adults"
    eligibility_exclusion: str | None = "Case reports"
    created_at: datetime = datetime(2025, 1, 1, tzinfo=timezone.utc)


@dataclass
class FakeProject:
    title: str = "Hypertension review"


@dataclass
class FakeSearch:
    database_name: str
    query_string: str
    date_searched: datetime


def test_default_draft_contains_all_22_fields():
    draft = default_draft(FakeReview(), project=FakeProject())
    keys = {k for k, _ in PROSPERO_FIELDS}
    assert set(draft.keys()) == keys
    assert len(draft) == 22


def test_default_draft_prefills_title_from_project():
    draft = default_draft(FakeReview(), project=FakeProject(title="My SR"))
    assert draft["title"] == "My SR"


def test_default_draft_prefills_pico_fields():
    draft = default_draft(FakeReview(), project=FakeProject())
    assert draft["participants"] == "Adults with hypertension"
    assert draft["intervention_exposure"] == "Drug X"
    assert draft["comparators_control"] == "Placebo"
    assert draft["primary_outcomes"] == "Stroke incidence"


def test_default_draft_composes_review_question():
    draft = default_draft(FakeReview(), project=FakeProject())
    q = draft["review_question"]
    assert "Adults with hypertension" in q
    assert "Drug X" in q
    assert "Placebo" in q
    assert "Stroke incidence" in q
    assert q.endswith("?")


def test_default_draft_dates_are_offset_six_months():
    review = FakeReview(created_at=datetime(2025, 1, 15, tzinfo=timezone.utc))
    draft = default_draft(review, project=FakeProject())
    assert draft["anticipated_start_date"] == "2025-01-15"
    # +183 days from 2025-01-15 → 2025-07-17
    expected_end = (
        datetime(2025, 1, 15, tzinfo=timezone.utc) + timedelta(days=183)
    ).date().isoformat()
    assert draft["anticipated_completion_date"] == expected_end


def test_default_draft_fills_searches_from_search_records():
    searches = [
        FakeSearch("PubMed", "hypertension AND stroke", datetime(2025, 2, 1, tzinfo=timezone.utc)),
        FakeSearch("Embase", "hypertension", datetime(2025, 2, 5, tzinfo=timezone.utc)),
    ]
    draft = default_draft(
        FakeReview(), project=FakeProject(), search_records=searches
    )
    assert "PubMed" in draft["searches"]
    assert "Embase" in draft["searches"]
    assert "2025-02-01" in draft["searches"]


def test_default_draft_uses_empty_strings_when_pico_missing():
    review = FakeReview(
        pico_population=None, pico_intervention=None,
        pico_comparator=None, pico_outcome=None,
        eligibility_inclusion=None, eligibility_exclusion=None,
    )
    draft = default_draft(review, project=FakeProject(title=""))
    assert draft["participants"] == ""
    assert draft["intervention_exposure"] == ""
    assert draft["review_question"] == ""


def test_format_for_export_labels_each_field():
    draft = default_draft(FakeReview(), project=FakeProject())
    text = format_for_export(draft)
    assert "Review title: Hypertension review" in text
    assert "Participants/population: Adults with hypertension" in text
    # 22 labels separated by blank lines → 21 blank lines
    assert text.count("\n\n") == 21
