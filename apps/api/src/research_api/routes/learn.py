"""Phase 5a + 5b — Learn hub routes.

Read-only public endpoints serving curated reference content from
``research_api/learn/``. No DB writes, no auth. The frontend renders the
Markdown body client-side.

  GET /api/learn/stat-tests           -> list (summaries)
  GET /api/learn/stat-tests/{slug}    -> full entry

Phase 5b — additional categories:

  GET /api/learn/checklists           -> list of reporting-checklist summaries
  GET /api/learn/checklists/{slug}    -> full checklist entry
  GET /api/learn/economics            -> list of health-economics summaries
  GET /api/learn/economics/{slug}     -> full economics entry
  GET /api/learn/submission           -> list of submission topic summaries
  GET /api/learn/submission/{slug}    -> full submission entry
  GET /api/learn/search?q=...         -> cross-category substring search
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ..learn.loader import (
    ChecklistRead,
    ChecklistSummary,
    EconomicsRead,
    EconomicsSummary,
    LearnSearchHit,
    StatTestRead,
    StatTestSummary,
    SubmissionRead,
    SubmissionSummary,
    WalkthroughRead,
    WalkthroughSummary,
    get_checklist,
    get_economics,
    get_stat_test,
    get_submission,
    get_walkthrough,
    list_checklists,
    list_economics,
    list_stat_tests,
    list_submission,
    list_walkthroughs,
    search_all,
)

router = APIRouter(tags=["learn"], prefix="/learn")


# --- Stat tests (Phase 5a) ---


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


# --- Checklists (Phase 5b) ---


@router.get("/checklists", response_model=list[ChecklistSummary])
async def get_checklists_list() -> list[ChecklistSummary]:
    return list_checklists()


@router.get("/checklists/{slug}", response_model=ChecklistRead)
async def get_checklist_entry(slug: str) -> ChecklistRead:
    entry = get_checklist(slug)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"checklist {slug!r} not found",
        )
    return ChecklistRead(
        slug=entry.slug,
        title=entry.title,
        reporting_standard=entry.reporting_standard,
        applies_to_study_types=list(entry.applies_to_study_types),
        version=entry.version,
        official_url=entry.official_url,
        worked_example_domain=entry.worked_example_domain,
        related_concepts=list(entry.related_concepts),
        body_md=entry.body_md,
    )


# --- Economics (Phase 5b) ---


@router.get("/economics", response_model=list[EconomicsSummary])
async def get_economics_list() -> list[EconomicsSummary]:
    return list_economics()


@router.get("/economics/{slug}", response_model=EconomicsRead)
async def get_economics_entry(slug: str) -> EconomicsRead:
    entry = get_economics(slug)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"economics concept {slug!r} not found",
        )
    return EconomicsRead(
        slug=entry.slug,
        title=entry.title,
        concept_family=entry.concept_family,
        formula=entry.formula,
        units=entry.units,
        worked_example_domain=entry.worked_example_domain,
        related_concepts=list(entry.related_concepts),
        body_md=entry.body_md,
    )


# --- Submission (Phase 5b) ---


@router.get("/submission", response_model=list[SubmissionSummary])
async def get_submission_list() -> list[SubmissionSummary]:
    return list_submission()


@router.get("/submission/{slug}", response_model=SubmissionRead)
async def get_submission_entry(slug: str) -> SubmissionRead:
    entry = get_submission(slug)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"submission topic {slug!r} not found",
        )
    return SubmissionRead(
        slug=entry.slug,
        title=entry.title,
        topic=entry.topic,
        topic_family=entry.topic_family,
        worked_example_domain=entry.worked_example_domain,
        related_concepts=list(entry.related_concepts),
        body_md=entry.body_md,
    )


# --- Walkthroughs (Phase 5c) ---


@router.get("/walkthroughs", response_model=list[WalkthroughSummary])
async def get_walkthroughs_list() -> list[WalkthroughSummary]:
    """Return every walkthrough summary."""
    return list_walkthroughs()


@router.get("/walkthroughs/{slug}", response_model=WalkthroughRead)
async def get_walkthrough_entry(slug: str) -> WalkthroughRead:
    """Return one walkthrough entry (frontmatter + Markdown body)."""
    entry = get_walkthrough(slug)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"walkthrough {slug!r} not found",
        )
    return WalkthroughRead(
        slug=entry.slug,
        title=entry.title,
        study_type=entry.study_type,
        estimated_reading_minutes=entry.estimated_reading_minutes,
        sections=list(entry.sections),
        worked_example_domain=entry.worked_example_domain,
        related_concepts=list(entry.related_concepts),
        body_md=entry.body_md,
    )


# --- Cross-category search (Phase 5b) ---


@router.get("/search", response_model=list[LearnSearchHit])
async def get_search(q: str = Query(..., min_length=1, max_length=120)) -> list[LearnSearchHit]:
    """Naive substring search across every Learn category."""
    return search_all(q)
