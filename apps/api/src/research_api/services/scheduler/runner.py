"""Phase 15 (MP15) — APScheduler integration for living systematic reviews.

We use ``BackgroundScheduler`` (threaded) rather than ``AsyncIOScheduler``
because it doesn't fight with FastAPI's lifespan loop — the scheduler thread
just kicks off a coroutine in its own event loop per trigger.

Lease pattern (SQL):
    UPDATE living_review_jobs
       SET lease_holder = :host
     WHERE id = :id AND lease_holder IS NULL

A row count of 0 means another process beat us; the job silently skips.
Release is the symmetric ``SET lease_holder = NULL`` keyed on the held value.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...db.models import LivingReviewHit, LivingReviewJob, new_id
from ..ingest.pubmed import search_pubmed
from ..review.living import diff_new_hits

logger = logging.getLogger("research_api.scheduler.runner")

# Lease identifier — host + pid so multi-instance dev/prod doesn't collide.
LEASE_HOLDER = f"{socket.gethostname()}-{os.getpid()}"

# Module-level scheduler singleton. The lifespan owns its lifecycle.
_scheduler: BackgroundScheduler | None = None


def _trigger_for(schedule: str) -> CronTrigger:
    if schedule == "daily":
        return CronTrigger(hour=2, minute=0)
    if schedule == "monthly":
        return CronTrigger(day=1, hour=2, minute=0)
    # Default + explicit "weekly" → Monday 02:00.
    return CronTrigger(day_of_week="mon", hour=2, minute=0)


# ─── Lease helpers ──────────────────────────────────────────────────────────


async def claim_lease(job_id: str, session: AsyncSession) -> bool:
    """Atomically claim the job's lease. Returns True iff this caller now holds it.

    Uses a conditional UPDATE (lease_holder IS NULL) so two concurrent runners
    can't both observe a free lease and both try to claim it.
    """
    stmt = (
        update(LivingReviewJob)
        .where(
            LivingReviewJob.id == job_id,
            LivingReviewJob.lease_holder.is_(None),
        )
        .values(lease_holder=LEASE_HOLDER)
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0


async def release_lease(job_id: str, session: AsyncSession) -> None:
    """Release the lease we hold. No-op if another holder owns it (defensive)."""
    stmt = (
        update(LivingReviewJob)
        .where(
            LivingReviewJob.id == job_id,
            LivingReviewJob.lease_holder == LEASE_HOLDER,
        )
        .values(lease_holder=None)
    )
    await session.execute(stmt)
    await session.commit()


# ─── Core run ───────────────────────────────────────────────────────────────


async def run_job(
    job_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    pubmed_search: Callable[..., Awaitable[list[Any]]] | None = None,
    ncbi_api_key: str | None = None,
    entrez_email: str = "noreply@research-assistant.local",
) -> dict[str, int]:
    """Run a single living-review job. Returns ``{"new_hits": N, "total": M}``.

    Skips silently (returns ``{"new_hits": 0, "total": 0, "skipped": 1}``)
    when another instance already holds the lease.
    """
    search_fn = pubmed_search or search_pubmed

    async with session_factory() as session:
        claimed = await claim_lease(job_id, session)
        if not claimed:
            logger.info("living-review job %s skipped (lease held)", job_id)
            return {"new_hits": 0, "total": 0, "skipped": 1}

        try:
            job = await session.get(LivingReviewJob, job_id)
            if job is None or not job.enabled:
                return {"new_hits": 0, "total": 0}

            results = await search_fn(
                job.pubmed_query,
                retmax=50,
                api_key=ncbi_api_key,
                email=entrez_email,
            )
            fresh_meta = list(results or [])
            fresh_pmids: list[str] = []
            title_by_pmid: dict[str, str] = {}
            for m in fresh_meta:
                pmid = getattr(m, "pmid", None) or (
                    m.get("pmid") if isinstance(m, dict) else None
                )
                title = getattr(m, "title", None) or (
                    m.get("title") if isinstance(m, dict) else None
                )
                if pmid:
                    fresh_pmids.append(pmid)
                    title_by_pmid[pmid] = title or "Untitled"

            prior_rows = (
                await session.execute(
                    select(LivingReviewHit.pmid).where(
                        LivingReviewHit.job_id == job_id
                    )
                )
            ).scalars().all()
            prior = set(prior_rows)
            new_pmids = diff_new_hits(prior, fresh_pmids)

            now = datetime.now(timezone.utc)
            for pmid in new_pmids:
                session.add(
                    LivingReviewHit(
                        id=new_id(),
                        user_id=job.user_id,
                        job_id=job_id,
                        run_at=now,
                        pmid=pmid,
                        title=title_by_pmid.get(pmid, "Untitled"),
                        decision="new",
                        seen_in_baseline=False,
                    )
                )

            job.last_run_at = now
            job.last_hit_count = len(new_pmids)
            await session.commit()

            return {"new_hits": len(new_pmids), "total": len(fresh_pmids)}
        finally:
            try:
                await release_lease(job_id, session)
            except Exception:  # pragma: no cover — defensive
                logger.warning("lease release failed for job %s", job_id, exc_info=True)


def _kick_run(
    job_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    ncbi_api_key: str | None,
    entrez_email: str,
) -> None:
    """Thread-side entry: spin up a fresh event loop and await the coroutine."""
    try:
        asyncio.run(
            run_job(
                job_id,
                session_factory,
                ncbi_api_key=ncbi_api_key,
                entrez_email=entrez_email,
            )
        )
    except Exception:  # pragma: no cover — defensive
        logger.exception("living-review run failed for job %s", job_id)


# ─── Lifecycle ──────────────────────────────────────────────────────────────


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


def _start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
        _scheduler.start()
    return _scheduler


def register_job(
    job_id: str,
    schedule: str,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    ncbi_api_key: str | None = None,
    entrez_email: str = "noreply@research-assistant.local",
) -> None:
    """Register (or replace) a single APScheduler job for this living-review row."""
    sched = _start_scheduler()
    sched.add_job(
        _kick_run,
        trigger=_trigger_for(schedule),
        id=f"living-review-{job_id}",
        replace_existing=True,
        kwargs={
            "job_id": job_id,
            "session_factory": session_factory,
            "ncbi_api_key": ncbi_api_key,
            "entrez_email": entrez_email,
        },
    )


def unregister_job(job_id: str) -> None:
    sched = get_scheduler()
    if sched is None:
        return
    try:
        sched.remove_job(f"living-review-{job_id}")
    except Exception:
        # APScheduler raises JobLookupError on missing — safe to ignore.
        pass


async def init_scheduler(app) -> None:
    """FastAPI startup hook — schedule every enabled job from the DB.

    Honours ``SCHEDULER_DISABLED=1`` so the test suite never starts a real
    threaded scheduler.
    """
    if os.environ.get("SCHEDULER_DISABLED") == "1":
        logger.info("scheduler disabled via SCHEDULER_DISABLED env flag")
        return

    from ...container import get_container

    container = get_container()
    session_factory = container.session_factory

    async with session_factory() as session:
        try:
            rows = (
                await session.execute(
                    select(LivingReviewJob).where(LivingReviewJob.enabled.is_(True))
                )
            ).scalars().all()
        except Exception:
            # Table may not exist on fresh containers (e.g. before migrate);
            # don't crash boot.
            logger.warning("could not read living_review_jobs at startup", exc_info=True)
            rows = []

    _start_scheduler()
    for job in rows:
        register_job(
            job.id,
            job.schedule,
            session_factory,
            ncbi_api_key=container.settings.ncbi_api_key,
            entrez_email=container.settings.entrez_email,
        )
    logger.info("scheduler initialised with %d living-review jobs", len(rows))


async def shutdown_scheduler(app) -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:  # pragma: no cover
            pass
        _scheduler = None


__all__ = [
    "LEASE_HOLDER",
    "claim_lease",
    "release_lease",
    "run_job",
    "register_job",
    "unregister_job",
    "init_scheduler",
    "shutdown_scheduler",
    "get_scheduler",
]
