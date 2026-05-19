"""Phase 15 (MP15) — pure helpers for living systematic review.

Only side-effect-free helpers live here. The APScheduler integration and the
DB-side lease claim live in ``services.scheduler.runner``.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import LivingReviewHit


def diff_new_hits(prior_pmids: set[str], fresh_pmids: list[str]) -> list[str]:
    """Return PMIDs in ``fresh_pmids`` not present in ``prior_pmids``.

    Preserves the order of ``fresh_pmids`` and deduplicates within the fresh
    batch — a single PubMed efetch occasionally returns the same PMID twice
    when an article is cross-indexed.
    """
    out: list[str] = []
    seen: set[str] = set()
    for pmid in fresh_pmids:
        if not pmid or pmid in prior_pmids or pmid in seen:
            continue
        seen.add(pmid)
        out.append(pmid)
    return out


async def count_new_pending(job_id: str, session: AsyncSession) -> int:
    """Count hits with decision='new' for a job (badge value in the UI)."""
    stmt = select(func.count()).select_from(LivingReviewHit).where(
        LivingReviewHit.job_id == job_id,
        LivingReviewHit.decision == "new",
    )
    return int((await session.execute(stmt)).scalar_one())


__all__ = ["diff_new_hits", "count_new_pending"]
