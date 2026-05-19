"""Phase 15 (MP15) — Bundle export/import round-trip for living-review jobs.

Hits are intentionally not part of the bundle: they are transient signals that
reset on import so a re-deployed project starts fresh against PubMed.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from research_api.db.models import (
    LivingReviewHit,
    LivingReviewJob,
    Project,
    Review,
)
from research_api.services.export.bundle_export import BundleInputs, build_bundle
from research_api.services.export.bundle_import import import_bundle


def _make_project_and_review() -> tuple[Project, Review]:
    p = Project(
        id="proj-orig",
        user_id="user-a",
        title="Living SR",
        study_type="Systematic Review",
    )
    r = Review(
        id="rev-orig",
        user_id="user-a",
        project_id="proj-orig",
        pico_population="Adults",
    )
    r.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    r.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return p, r


@pytest.mark.asyncio
async def test_living_review_job_round_trips(session):
    p, r = _make_project_and_review()
    job = LivingReviewJob(
        id="job-orig",
        user_id="user-a",
        project_id="proj-orig",
        review_id="rev-orig",
        pubmed_query="aspirin AND stroke",
        schedule="monthly",
        enabled=True,
        last_run_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
        last_hit_count=7,
        lease_holder="some-host-12345",
    )
    job.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    job.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    bundle = build_bundle(
        BundleInputs(project=p, review=r, living_review_job=job)
    )

    counts = await import_bundle(
        bundle, target_user_id="user-b", session=session
    )
    assert counts["living_review_job"] == 1

    row = (await session.execute(select(LivingReviewJob))).scalar_one()
    assert row.user_id == "user-b"
    assert row.pubmed_query == "aspirin AND stroke"
    assert row.schedule == "monthly"
    assert row.enabled is True
    # Lease + run history must be reset so the new instance can run cleanly.
    assert row.lease_holder is None
    assert row.last_run_at is None
    assert row.last_hit_count is None


@pytest.mark.asyncio
async def test_living_review_hits_are_not_carried(session):
    """Hits don't ride the bundle — they're transient."""
    p, r = _make_project_and_review()
    job = LivingReviewJob(
        id="job-orig",
        user_id="user-a",
        project_id="proj-orig",
        review_id="rev-orig",
        pubmed_query="x",
        schedule="weekly",
        enabled=True,
    )

    bundle = build_bundle(
        BundleInputs(project=p, review=r, living_review_job=job)
    )
    # Even though we never put hits into the bundle, defensively assert there
    # is no top-level "living_review_hits" key — that would imply transient
    # rerun history was being persisted across the import boundary.
    assert "living_review_hits" not in bundle

    await import_bundle(bundle, target_user_id="user-b", session=session)
    hits = (await session.execute(select(LivingReviewHit))).scalars().all()
    assert hits == []


@pytest.mark.asyncio
async def test_invalid_schedule_falls_back_to_weekly(session):
    p, r = _make_project_and_review()
    job = LivingReviewJob(
        id="job-orig",
        user_id="user-a",
        project_id="proj-orig",
        review_id="rev-orig",
        pubmed_query="x",
        schedule="weekly",
        enabled=True,
    )
    bundle = build_bundle(
        BundleInputs(project=p, review=r, living_review_job=job)
    )
    # Smuggle a bogus schedule into the bundle.
    bundle["living_review_job"]["schedule"] = "fortnightly"

    counts = await import_bundle(
        bundle, target_user_id="user-b", session=session
    )
    assert counts["living_review_job"] == 1
    row = (await session.execute(select(LivingReviewJob))).scalar_one()
    assert row.schedule == "weekly"
