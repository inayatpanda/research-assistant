"""Phase 14 (MP14) — Bundle export/import round-trip for GRADE + PROSPERO."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from research_api.db.models import (
    GradeAssessment,
    Project,
    ProsperoDraft,
    Review,
)
from research_api.services.export.bundle_export import BundleInputs, build_bundle
from research_api.services.export.bundle_import import import_bundle


def _make_project_and_review() -> tuple[Project, Review]:
    p = Project(
        id="proj-orig", user_id="user-a", title="GRADE SR",
        study_type="Systematic Review",
    )
    r = Review(
        id="rev-orig", user_id="user-a", project_id="proj-orig",
        pico_population="Adults", pico_intervention="X",
        pico_comparator="Placebo", pico_outcome="Stroke",
    )
    r.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    r.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return p, r


@pytest.mark.asyncio
async def test_grade_assessment_round_trip(session):
    p, r = _make_project_and_review()
    g = GradeAssessment(
        id="g-orig", user_id="user-a", project_id="proj-orig",
        review_id="rev-orig", meta_id=None,
        outcome_label="Mortality",
        starting_certainty="high",
        domain_risk_of_bias="serious",
        domain_inconsistency="not_serious",
        domain_indirectness="not_serious",
        domain_imprecision="not_serious",
        domain_publication_bias="not_serious",
        upgrade_large_effect="none",
        upgrade_dose_response="none",
        upgrade_confounders_against="none",
        certainty="moderate",
        notes="Hi",
    )
    g.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    g.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(
        project=p, review=r, grade_assessments=[g],
    ))
    counts = await import_bundle(
        bundle, target_user_id="user-b", session=session
    )
    assert counts["grade_assessments"] == 1

    row = (await session.execute(select(GradeAssessment))).scalar_one()
    assert row.user_id == "user-b"
    assert row.outcome_label == "Mortality"
    assert row.domain_risk_of_bias == "serious"
    assert row.certainty == "moderate"


@pytest.mark.asyncio
async def test_grade_orphan_meta_link_dropped(session):
    """When the source meta_analysis isn't carried in the bundle, the import
    silently nulls the meta_id so the row still lands (orphan link → narrative)."""
    p, r = _make_project_and_review()
    g = GradeAssessment(
        id="g-orig", user_id="user-a", project_id="proj-orig",
        review_id="rev-orig", meta_id="meta-missing",
        outcome_label="Mortality",
        starting_certainty="high",
        domain_risk_of_bias="not_serious",
        domain_inconsistency="not_serious",
        domain_indirectness="not_serious",
        domain_imprecision="not_serious",
        domain_publication_bias="not_serious",
        upgrade_large_effect="none",
        upgrade_dose_response="none",
        upgrade_confounders_against="none",
        certainty="high",
        notes=None,
    )
    g.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    g.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(
        project=p, review=r, grade_assessments=[g],
    ))
    counts = await import_bundle(
        bundle, target_user_id="user-b", session=session
    )
    assert counts["grade_assessments"] == 1
    row = (await session.execute(select(GradeAssessment))).scalar_one()
    assert row.meta_id is None


@pytest.mark.asyncio
async def test_prospero_draft_round_trip(session):
    p, r = _make_project_and_review()
    pros = ProsperoDraft(
        id="pros-orig", user_id="user-a", project_id="proj-orig",
        review_id="rev-orig",
        fields={"title": "GRADE SR", "named_contact": "Dr A"},
    )
    pros.updated_at = datetime(2025, 1, 5, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(
        project=p, review=r, prospero_draft=pros,
    ))
    counts = await import_bundle(
        bundle, target_user_id="user-b", session=session
    )
    assert counts["prospero_draft"] == 1

    row = (await session.execute(select(ProsperoDraft))).scalar_one()
    assert row.user_id == "user-b"
    assert row.fields["title"] == "GRADE SR"
    assert row.fields["named_contact"] == "Dr A"
