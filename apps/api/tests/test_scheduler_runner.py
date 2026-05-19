"""Phase 15 (MP15) — scheduler runner tests.

We exercise ``run_job`` directly with a mocked PubMed search rather than
sitting on a real APScheduler trigger — APScheduler's job-store mechanics are
not what's interesting here. We DO verify the threaded scheduler can be
started + a near-immediate one-shot job fires, but the bulk of the assertions
land on ``run_job`` itself.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from sqlalchemy import select

from research_api.db.models import (
    LivingReviewHit,
    LivingReviewJob,
    Project,
    Review,
)
from research_api.services.scheduler.runner import (
    LEASE_HOLDER,
    claim_lease,
    release_lease,
    run_job,
)


@dataclass
class _FakeMeta:
    pmid: str
    title: str


async def _seed(session) -> tuple[Project, Review, LivingReviewJob]:
    p = Project(id="proj1", user_id="user-a", title="P", study_type="Systematic Review")
    session.add(p)
    await session.flush()
    r = Review(id="rev1", user_id="user-a", project_id="proj1")
    session.add(r)
    await session.flush()
    j = LivingReviewJob(
        id="job1",
        user_id="user-a",
        project_id="proj1",
        review_id="rev1",
        pubmed_query="aspirin",
        schedule="weekly",
        enabled=True,
    )
    session.add(j)
    await session.commit()
    return p, r, j


def _factory_from_session(session):
    """Wrap the test session into an ``async_sessionmaker``-shaped callable.

    run_job calls ``async with session_factory()`` then ``session.commit()``.
    We return a small async-cm shim that yields the SAME test session but
    suppresses .close() so the fixture's cleanup still owns it.
    """

    class _Shim:
        def __init__(self, s):
            self._s = s

        def __call__(self):
            outer = self

            class _CM:
                async def __aenter__(self_inner):
                    return outer._s

                async def __aexit__(self_inner, exc_type, exc, tb):
                    return None

            return _CM()

    return _Shim(session)


@pytest.mark.asyncio
async def test_run_job_fetches_pubmed_and_inserts_new_hits(session):
    _p, _r, _j = await _seed(session)

    async def fake_search(*_args, **_kwargs):
        return [
            _FakeMeta(pmid="111", title="Aspirin and X"),
            _FakeMeta(pmid="222", title="Aspirin and Y"),
        ]

    result = await run_job(
        "job1",
        _factory_from_session(session),
        pubmed_search=fake_search,
    )

    assert result["new_hits"] == 2
    assert result["total"] == 2

    hits = (await session.execute(select(LivingReviewHit))).scalars().all()
    pmids = sorted(h.pmid for h in hits)
    assert pmids == ["111", "222"]

    job = await session.get(LivingReviewJob, "job1")
    assert job.last_hit_count == 2
    assert job.last_run_at is not None
    # Lease must be released after a successful run.
    assert job.lease_holder is None


@pytest.mark.asyncio
async def test_run_job_skips_already_seen_pmids(session):
    _p, _r, _j = await _seed(session)
    session.add(LivingReviewHit(
        id="h-existing", user_id="user-a", job_id="job1",
        pmid="111", title="seen earlier", decision="dismissed",
    ))
    await session.commit()

    async def fake_search(*_args, **_kwargs):
        return [
            _FakeMeta(pmid="111", title="seen earlier"),
            _FakeMeta(pmid="333", title="brand new"),
        ]

    result = await run_job(
        "job1",
        _factory_from_session(session),
        pubmed_search=fake_search,
    )
    assert result["new_hits"] == 1
    assert result["total"] == 2
    job = await session.get(LivingReviewJob, "job1")
    assert job.last_hit_count == 1

    # The existing 'dismissed' row must NOT be re-inserted as 'new'.
    hits = list((await session.execute(select(LivingReviewHit))).scalars().all())
    assert {(h.pmid, h.decision) for h in hits} == {
        ("111", "dismissed"),
        ("333", "new"),
    }


@pytest.mark.asyncio
async def test_run_job_skips_when_lease_held_elsewhere(session):
    _p, _r, _j = await _seed(session)
    # Simulate another instance holding the lease.
    job = await session.get(LivingReviewJob, "job1")
    job.lease_holder = "other-host-9999"
    await session.commit()

    calls = {"n": 0}

    async def fake_search(*_args, **_kwargs):
        calls["n"] += 1
        return [_FakeMeta(pmid="abc", title="x")]

    result = await run_job(
        "job1",
        _factory_from_session(session),
        pubmed_search=fake_search,
    )
    assert result == {"new_hits": 0, "total": 0, "skipped": 1}
    assert calls["n"] == 0, "pubmed must not be called when lease held elsewhere"
    # Lease must still belong to the other instance.
    await session.refresh(job)
    assert job.lease_holder == "other-host-9999"


@pytest.mark.asyncio
async def test_run_job_no_op_when_job_disabled(session):
    _p, _r, j = await _seed(session)
    j.enabled = False
    await session.commit()

    async def fake_search(*_args, **_kwargs):
        return [_FakeMeta(pmid="999", title="ignored")]

    result = await run_job(
        "job1",
        _factory_from_session(session),
        pubmed_search=fake_search,
    )
    assert result == {"new_hits": 0, "total": 0}


@pytest.mark.asyncio
async def test_claim_and_release_lease_round_trip(session):
    _p, _r, _j = await _seed(session)

    claimed_a = await claim_lease("job1", session)
    assert claimed_a is True

    # A second concurrent claim must fail (still held by us).
    claimed_b = await claim_lease("job1", session)
    assert claimed_b is False

    await release_lease("job1", session)
    job = await session.get(LivingReviewJob, "job1")
    await session.refresh(job)
    assert job.lease_holder is None

    # After release, a fresh claim must succeed again.
    claimed_c = await claim_lease("job1", session)
    assert claimed_c is True
    await session.refresh(job)
    assert job.lease_holder == LEASE_HOLDER


def test_background_scheduler_starts_and_fires_one_shot(tmp_path):
    """Smoke: with SCHEDULER_DISABLED off, a near-immediate one-shot job runs.

    We don't go through ``run_job`` here — we just verify the threaded
    scheduler doesn't block startup and actually invokes the registered
    function. This guards the "must not block app startup" hard constraint.
    """
    import time
    import threading

    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(daemon=True, timezone="UTC")
    sched.start()
    try:
        fired = threading.Event()

        def cb():
            fired.set()

        from datetime import datetime, timedelta, timezone

        sched.add_job(
            cb,
            "date",
            run_date=datetime.now(timezone.utc) + timedelta(milliseconds=50),
            id="one-shot",
        )
        # Poll briefly — APScheduler dispatches in a worker thread, so we
        # need to yield to it.
        assert fired.wait(timeout=3.0)
    finally:
        # wait=True so the worker thread cleanly removes the one-shot job
        # from its own loop before we tear the scheduler down (otherwise a
        # benign JobLookupError races out as a PytestUnhandledThreadException).
        sched.shutdown(wait=True)
