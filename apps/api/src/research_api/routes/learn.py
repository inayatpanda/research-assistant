"""Phase 5a — Learn hub routes.

Read-only public endpoints serving curated reference content from
``research_api/learn/``. No DB writes, no auth. The frontend renders the
Markdown body client-side.

  GET /api/learn/stat-tests           → list (summaries)
  GET /api/learn/stat-tests/{slug}    → full entry
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..learn.loader import (
    StatTestRead,
    StatTestSummary,
    get_stat_test,
    list_stat_tests,
)

router = APIRouter(tags=["learn"], prefix="/learn")


@router.get("/stat-tests", response_model=list[StatTestSummary])
async def get_stat_tests_list() -> list[StatTestSummary]:
    """Return every curated stat-test entry as a list-view summary."""
    return list_stat_tests()


@router.get("/stat-tests/{slug}", response_model=StatTestRead)
async def get_stat_test_entry(slug: str) -> StatTestRead:
    """Return one stat-test entry (frontmatter + Markdown body)."""
    entry = get_stat_test(slug)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"stat-test {slug!r} not found",
        )
    return StatTestRead(
        slug=entry.slug,
        title=entry.title,
        family=entry.family,
        when_to_use=entry.when_to_use,
        assumptions=list(entry.assumptions),
        alternatives=list(entry.alternatives),
        worked_example_domain=entry.worked_example_domain,
        worked_example_dataset=entry.worked_example_dataset,
        related_concepts=list(entry.related_concepts),
        body_md=entry.body_md,
    )
