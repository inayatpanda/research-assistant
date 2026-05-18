"""Reviews routes: PICO + Search + Screening + RoB + Extraction + PRISMA + push."""
from __future__ import annotations

import base64
import logging
import re
from collections.abc import AsyncIterator
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.articles import SqliteArticleRepository
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import (
    ScreeningArticleMismatch,
    SqliteReviewRepository,
)
from ..schemas.manuscript_section import ManuscriptSectionRead
from ..schemas.review import (
    AIScreeningSuggestResponse,
    ExtractionRecordCreate,
    ExtractionRecordRead,
    ExtractionRecordUpdate,
    PrismaCounts,
    ReviewRead,
    ReviewUpdate,
    RoBAssessmentCreate,
    RoBAssessmentRead,
    RoBAssessmentUpdate,
    ScreeningRecordCreate,
    ScreeningRecordRead,
    ScreeningRecordUpdate,
    SearchRecordCreate,
    SearchRecordRead,
    SearchRecordUpdate,
)
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)
from ..services.review import extraction_schema as extraction_schema_svc
from ..services.review import prisma as prisma_svc
from ..services.review import rob_rules

router = APIRouter(tags=["reviews"])
log = logging.getLogger("research_api.reviews")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


def _map_ai_error(e: Exception) -> HTTPException:
    log.warning("AI error: %s: %s", type(e).__name__, e)
    if isinstance(e, AIRateLimited):
        return HTTPException(status_code=429, detail="AI rate limited")
    if isinstance(e, AISourceInsufficient):
        return HTTPException(
            status_code=422, detail="insufficient input to suggest screening"
        )
    return HTTPException(status_code=503, detail="AI provider unavailable")


async def _resolve_review(
    project_id: str, session: AsyncSession, user_id: str
):
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewRepository(session)
    review = await repo.get_or_create(project_id=project_id, user_id=user_id)
    return repo, review


# ── Review (PICO + eligibility) ─────────────────────────────────────────


@router.get(
    "/projects/{project_id}/reviews",
    response_model=ReviewRead,
)
async def get_review(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ReviewRead:
    _, review = await _resolve_review(project_id, session, user_id)
    return ReviewRead.model_validate(review)


@router.patch(
    "/projects/{project_id}/reviews",
    response_model=ReviewRead,
)
async def patch_review(
    project_id: str,
    body: ReviewUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ReviewRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    updated = await repo.update(review.id, body, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewRead.model_validate(updated)


# ── Search records ──────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/reviews/search",
    response_model=list[SearchRecordRead],
)
async def list_search_records(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[SearchRecordRead]:
    repo, review = await _resolve_review(project_id, session, user_id)
    rows = await repo.list_search(review.id, user_id)
    return [SearchRecordRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/reviews/search",
    response_model=SearchRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_search_record(
    project_id: str,
    body: SearchRecordCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SearchRecordRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    row = await repo.create_search(review_id=review.id, data=body, user_id=user_id)
    return SearchRecordRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/reviews/search/{search_id}",
    response_model=SearchRecordRead,
)
async def update_search_record(
    project_id: str,
    search_id: str,
    body: SearchRecordUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SearchRecordRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_search(search_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Search record not found")
    updated = await repo.update_search(search_id, body, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Search record not found")
    return SearchRecordRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/reviews/search/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_search_record(
    project_id: str,
    search_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_search(search_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Search record not found")
    await repo.delete_search(search_id, user_id)
    return None


# ── Screening ───────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/reviews/screening",
    response_model=list[ScreeningRecordRead],
)
async def list_screening_records(
    project_id: str,
    stage: str | None = Query(default=None, pattern="^(title_abstract|full_text)$"),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ScreeningRecordRead]:
    repo, review = await _resolve_review(project_id, session, user_id)
    rows = await repo.list_screening(review.id, user_id, stage=stage)
    return [ScreeningRecordRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/reviews/screening",
    response_model=ScreeningRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_screening_record(
    project_id: str,
    body: ScreeningRecordCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ScreeningRecordRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    try:
        row = await repo.upsert_screening(
            review_id=review.id, data=body, user_id=user_id
        )
    except ScreeningArticleMismatch as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return ScreeningRecordRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/reviews/screening/{screening_id}",
    response_model=ScreeningRecordRead,
)
async def update_screening_record(
    project_id: str,
    screening_id: str,
    body: ScreeningRecordUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ScreeningRecordRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_screening(screening_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Screening record not found")
    updated = await repo.update_screening(screening_id, body, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Screening record not found")
    return ScreeningRecordRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/reviews/screening/{screening_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_screening_record(
    project_id: str,
    screening_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_screening(screening_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Screening record not found")
    await repo.delete_screening(screening_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/reviews/screening/{screening_id}/ai-suggest",
    response_model=AIScreeningSuggestResponse,
)
async def ai_suggest_screening(
    project_id: str,
    screening_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AIScreeningSuggestResponse:
    repo, review = await _resolve_review(project_id, session, user_id)
    screening = await repo.get_screening(screening_id, user_id)
    if screening is None or screening.review_id != review.id:
        raise HTTPException(status_code=404, detail="Screening record not found")

    art_repo = SqliteArticleRepository(session)
    article = await art_repo.get(screening.article_id, user_id)
    if article is None or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")

    pico = {
        "population": review.pico_population,
        "intervention": review.pico_intervention,
        "comparator": review.pico_comparator,
        "outcome": review.pico_outcome,
    }
    try:
        suggestion = await container.ai.suggest_screening(
            eligibility_inclusion=review.eligibility_inclusion,
            eligibility_exclusion=review.eligibility_exclusion,
            pico=pico,
            article_title=article.title,
            article_abstract=article.abstract,
        )
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as exc:
        raise _map_ai_error(exc) from None
    except Exception:
        log.exception("Unexpected AI error in ai_suggest_screening")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None

    await repo.set_ai_suggestion(screening_id, suggestion, user_id)
    return AIScreeningSuggestResponse(
        vote=suggestion.get("vote", "maybe"),
        reason=suggestion.get("reason", ""),
        model=suggestion.get("model", ""),
    )


# ── RoB ─────────────────────────────────────────────────────────────────


@router.get("/projects/{project_id}/reviews/rob/tools")
async def list_rob_tools(project_id: str) -> list[dict]:
    out: list[dict] = []
    for key, tool in rob_rules.CATALOGUE.items():
        out.append(
            {
                "key": key,
                "label": tool.label,
                "applies_to": list(tool.applies_to),
                "domains": [
                    {
                        "key": d.key,
                        "label": d.label,
                        "question": d.question,
                        "answers": list(d.answers),
                        "critical": d.critical,
                    }
                    for d in tool.domains
                ],
            }
        )
    return out


@router.get(
    "/projects/{project_id}/reviews/rob",
    response_model=list[RoBAssessmentRead],
)
async def list_rob_assessments(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[RoBAssessmentRead]:
    repo, review = await _resolve_review(project_id, session, user_id)
    rows = await repo.list_rob(review.id, user_id)
    return [RoBAssessmentRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/reviews/rob",
    response_model=RoBAssessmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_rob_assessment(
    project_id: str,
    body: RoBAssessmentCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> RoBAssessmentRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    # Ensure the article belongs to the same project as the review.
    art_repo = SqliteArticleRepository(session)
    article = await art_repo.get(body.article_id, user_id)
    if article is None or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")

    try:
        overall_auto = rob_rules.derive_overall(body.tool, body.domain_answers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    row = await repo.upsert_rob(
        review_id=review.id,
        data=body,
        overall_auto=overall_auto,
        overall_override=None,
        user_id=user_id,
    )
    return RoBAssessmentRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/reviews/rob/{rob_id}",
    response_model=RoBAssessmentRead,
)
async def update_rob_assessment(
    project_id: str,
    rob_id: str,
    body: RoBAssessmentUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> RoBAssessmentRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_rob(rob_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="RoB assessment not found")

    overall_auto: str | None = None
    if body.domain_answers is not None:
        try:
            overall_auto = rob_rules.derive_overall(existing.tool, body.domain_answers)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    updated = await repo.update_rob(rob_id, body, overall_auto, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="RoB assessment not found")
    return RoBAssessmentRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/reviews/rob/{rob_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_rob_assessment(
    project_id: str,
    rob_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_rob(rob_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="RoB assessment not found")
    await repo.delete_rob(rob_id, user_id)
    return None


# ── Extraction ──────────────────────────────────────────────────────────


@router.get("/projects/{project_id}/reviews/extraction/schema")
async def get_extraction_schema(project_id: str) -> list[dict]:
    out: list[dict] = []
    for group in extraction_schema_svc.EXTRACTION_SCHEMA:
        out.append(
            {
                "key": group.key,
                "label": group.label,
                "fields": [
                    {
                        "key": f.key,
                        "label": f.label,
                        "type": f.type,
                        "required": f.required,
                        "choices": list(f.choices) if f.choices else None,
                        "allow_negative": f.allow_negative,
                    }
                    for f in group.fields
                ],
            }
        )
    return out


@router.get(
    "/projects/{project_id}/reviews/extraction",
    response_model=list[ExtractionRecordRead],
)
async def list_extraction_records(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ExtractionRecordRead]:
    repo, review = await _resolve_review(project_id, session, user_id)
    rows = await repo.list_extraction(review.id, user_id)
    return [ExtractionRecordRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/reviews/extraction",
    response_model=ExtractionRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_extraction_record(
    project_id: str,
    body: ExtractionRecordCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ExtractionRecordRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    art_repo = SqliteArticleRepository(session)
    article = await art_repo.get(body.article_id, user_id)
    if article is None or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")

    errors = extraction_schema_svc.validate(body.fields)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    row = await repo.upsert_extraction(
        review_id=review.id, data=body, user_id=user_id
    )
    return ExtractionRecordRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/reviews/extraction/{ext_id}",
    response_model=ExtractionRecordRead,
)
async def update_extraction_record(
    project_id: str,
    ext_id: str,
    body: ExtractionRecordUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ExtractionRecordRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_extraction(ext_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Extraction record not found")

    errors = extraction_schema_svc.validate(body.fields)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    updated = await repo.update_extraction(ext_id, body, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Extraction record not found")
    return ExtractionRecordRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/reviews/extraction/{ext_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_extraction_record(
    project_id: str,
    ext_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo, review = await _resolve_review(project_id, session, user_id)
    existing = await repo.get_extraction(ext_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Extraction record not found")
    await repo.delete_extraction(ext_id, user_id)
    return None


# ── PRISMA + push-to-manuscript ─────────────────────────────────────────


@router.get("/projects/{project_id}/reviews/prisma")
async def get_prisma(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict:
    repo, review = await _resolve_review(project_id, session, user_id)
    search_rows = await repo.list_search(review.id, user_id)
    screening_rows = await repo.list_screening(review.id, user_id)
    counts = prisma_svc.count_flow(
        search_records=search_rows, screening_records=screening_rows
    )
    svg = prisma_svc.render_svg(counts)
    return {
        "counts": PrismaCounts(
            identified=counts.identified,
            after_dedupe=counts.after_dedupe,
            screened=counts.screened,
            excluded_title=counts.excluded_title,
            full_text_assessed=counts.full_text_assessed,
            excluded_full=counts.excluded_full,
            included=counts.included,
        ).model_dump(),
        "svg": svg,
    }


_BLOCK_TAG_BY_CLASS: dict[str, str] = {
    "prisma-flow": "figure",
    "search-records-table": "table",
    "rob-traffic-light-table": "table",
    "extraction-table": "table",
}


def _strip_block_by_class(content: str, class_hook: str) -> str:
    """Remove any prior <tag class="<hook>">...</tag> block (deterministic, tag-aware)."""
    tag = _BLOCK_TAG_BY_CLASS[class_hook]
    pattern = re.compile(
        rf'<{tag}\b[^>]*\bclass="{re.escape(class_hook)}"[^>]*>.*?</{tag}>',
        flags=re.DOTALL,
    )
    return pattern.sub("", content)


async def _push_to_section(
    session: AsyncSession,
    *,
    project_id: str,
    section_name: str,
    html: str,
    class_hook: str,
    user_id: str,
) -> ManuscriptSectionRead:
    """Replace-by-class-hook: strip any prior artefact of the same class then append."""
    sec_repo = SqliteManuscriptSectionRepository(session)
    existing = await sec_repo.get(
        project_id=project_id, section_name=section_name, user_id=user_id
    )
    if existing is None or not existing.content:
        new_content = html
    else:
        stripped = _strip_block_by_class(existing.content, class_hook)
        new_content = stripped + html
    updated = await sec_repo.upsert(
        project_id=project_id,
        section_name=section_name,
        content=new_content,
        user_id=user_id,
    )
    return ManuscriptSectionRead.model_validate(updated)


@router.post(
    "/projects/{project_id}/reviews/prisma/push",
    response_model=ManuscriptSectionRead,
)
async def push_prisma(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    search_rows = await repo.list_search(review.id, user_id)
    screening_rows = await repo.list_screening(review.id, user_id)
    counts = prisma_svc.count_flow(
        search_records=search_rows, screening_records=screening_rows
    )
    svg = prisma_svc.render_svg(counts)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    html = (
        f'<figure class="prisma-flow">'
        f'<img src="data:image/svg+xml;base64,{encoded}" '
        f'alt="PRISMA 2020 flow diagram"/>'
        f'<figcaption>PRISMA 2020 flow diagram.</figcaption>'
        f'</figure>'
    )
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Methodology",
        html=html,
        class_hook="prisma-flow",
        user_id=user_id,
    )


@router.post(
    "/projects/{project_id}/reviews/search/push",
    response_model=ManuscriptSectionRead,
)
async def push_search(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    rows = await repo.list_search(review.id, user_id)
    header = (
        "<tr>"
        "<th>Database</th><th>Date searched</th><th>Query</th><th>n results</th>"
        "</tr>"
    )
    body_rows: list[str] = []
    for r in rows:
        body_rows.append(
            "<tr>"
            f"<td>{escape(r.database_name)}</td>"
            f"<td>{escape(r.date_searched.date().isoformat())}</td>"
            f"<td>{escape(r.query_string)}</td>"
            f"<td>{int(r.n_results)}</td>"
            "</tr>"
        )
    html = (
        '<table class="search-records-table">'
        f"<thead>{header}</thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Methodology",
        html=html,
        class_hook="search-records-table",
        user_id=user_id,
    )


async def _included_article_ids(repo: SqliteReviewRepository, review_id: str, user_id: str) -> list[str]:
    rows = await repo.list_screening(review_id, user_id, stage="full_text")
    return [r.article_id for r in rows if r.decision == "include"]


@router.post(
    "/projects/{project_id}/reviews/rob/push",
    response_model=ManuscriptSectionRead,
)
async def push_rob(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    included = await _included_article_ids(repo, review.id, user_id)
    all_rob = await repo.list_rob(review.id, user_id)
    by_article: dict[str, list] = {}
    for r in all_rob:
        by_article.setdefault(r.article_id, []).append(r)

    tools_used: list[str] = []
    for art_id in included:
        for r in by_article.get(art_id, []):
            if r.tool not in tools_used:
                tools_used.append(r.tool)
    if not tools_used:
        tools_used = ["rob2"]

    domain_keys: dict[str, list[str]] = {}
    for t in tools_used:
        tool = rob_rules.CATALOGUE.get(t)
        if tool is None:
            continue
        domain_keys[t] = [d.key for d in tool.domains]

    body_rows: list[str] = []
    for art_id in included:
        rob_rows = by_article.get(art_id, [])
        if not rob_rows:
            continue
        for r in rob_rows:
            domains_for_tool = domain_keys.get(r.tool, list(r.domain_answers.keys()))
            cells: list[str] = [
                f'<td>[CITE_{escape(art_id)}]</td>',
                f"<td>{escape(r.tool)}</td>",
            ]
            for d in domains_for_tool:
                ans = r.domain_answers.get(d, "")
                cells.append(f'<td class="rob-cell rob-{escape(ans)}">{escape(ans)}</td>')
            overall = r.overall_override or r.overall_auto
            cells.append(f'<td class="rob-overall">{escape(overall)}</td>')
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

    html = (
        '<table class="rob-traffic-light-table">'
        '<thead><tr><th>Study</th><th>Tool</th><th>Domains</th>'
        '<th>Overall</th></tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Results",
        html=html,
        class_hook="rob-traffic-light-table",
        user_id=user_id,
    )


@router.post(
    "/projects/{project_id}/reviews/extraction/push",
    response_model=ManuscriptSectionRead,
)
async def push_extraction(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    repo, review = await _resolve_review(project_id, session, user_id)
    included = await _included_article_ids(repo, review.id, user_id)
    all_ext = await repo.list_extraction(review.id, user_id)
    by_article = {r.article_id: r for r in all_ext}

    header = (
        "<tr>"
        "<th>Study</th><th>Design</th><th>N</th>"
        "<th>Intervention</th><th>Comparator</th><th>Outcomes</th>"
        "</tr>"
    )
    body_rows: list[str] = []
    for art_id in included:
        ext = by_article.get(art_id)
        if ext is None:
            log.warning("No extraction record for included article %s", art_id)
            continue
        f = ext.fields or {}
        basic = f.get("basic") or {}
        population = f.get("population") or {}
        intervention = f.get("intervention") or {}
        comparator = f.get("comparator") or {}
        outcomes_group = f.get("outcomes") or {}
        if isinstance(outcomes_group, list):
            outcomes = outcomes_group
        else:
            outcomes = outcomes_group.get("outcomes", []) if isinstance(outcomes_group, dict) else []
        outcomes_text = "; ".join(
            str(o.get("name", "")) for o in outcomes if isinstance(o, dict)
        )
        body_rows.append(
            "<tr>"
            f"<td>[CITE_{escape(art_id)}]</td>"
            f"<td>{escape(str(basic.get('design', '') or ''))}</td>"
            f"<td>{escape(str(population.get('n_total', '') or ''))}</td>"
            f"<td>{escape(str(intervention.get('name', '') or ''))}</td>"
            f"<td>{escape(str(comparator.get('name', '') or ''))}</td>"
            f"<td>{escape(outcomes_text)}</td>"
            "</tr>"
        )

    html = (
        '<table class="extraction-table">'
        f"<thead>{header}</thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Results",
        html=html,
        class_hook="extraction-table",
        user_id=user_id,
    )
