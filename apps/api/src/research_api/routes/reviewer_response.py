"""Phase 12 — Reviewer-response routes.

Endpoints (under /api/projects/{project_id}/reviewer-responses):

  GET    /                              list rows
  POST   /                              AI-draft a new row from raw_comments
  PATCH  /{response_id}                 update reviewer_label and/or comments
  DELETE /{response_id}                 delete
"""
from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import ManuscriptSection, ProjectFrontmatter
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviewer_responses import SqliteReviewerResponseRepository
from ..schemas.reviewer_response import (
    ReviewerResponseCreate,
    ReviewerResponseRead,
    ReviewerResponseUpdate,
)
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)
from ..services.export.docx_export import html_to_docx_bytes
from ..services.export.submission_package import (
    ReviewerResponsePayload,
    _build_response_to_reviewers_html,
)

router = APIRouter(tags=["reviewer-responses"])
log = logging.getLogger("research_api.reviewer_response")


_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _slugify_for_filename(text: str | None) -> str:
    """Filesystem-safe slug for the standalone DOCX download filename."""
    raw = (text or "").strip().replace(" ", "-")
    s = _SLUG_RE.sub("", raw).strip("-_")
    return (s or "reviewer-response")[:80]


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _load_abstract(
    session: AsyncSession, project_id: str, user_id: str
) -> str:
    """Best-effort abstract lookup for AI context (structured > freeform)."""
    fm = (
        await session.execute(
            select(ProjectFrontmatter).where(
                ProjectFrontmatter.project_id == project_id,
                ProjectFrontmatter.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if (
        fm
        and fm.structured_abstract_enabled
        and isinstance(fm.structured_abstract, dict)
    ):
        parts = [
            fm.structured_abstract.get("background") or "",
            fm.structured_abstract.get("methods") or "",
            fm.structured_abstract.get("results") or "",
            fm.structured_abstract.get("conclusions") or "",
        ]
        return "\n".join(p.strip() for p in parts if p.strip())

    sec = (
        await session.execute(
            select(ManuscriptSection).where(
                ManuscriptSection.project_id == project_id,
                ManuscriptSection.user_id == user_id,
                ManuscriptSection.section_name == "Abstract",
            )
        )
    ).scalar_one_or_none()
    return (sec.content if sec else "") or ""


@router.get(
    "/projects/{project_id}/reviewer-responses",
    response_model=list[ReviewerResponseRead],
)
async def list_reviewer_responses(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ReviewerResponseRead]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewerResponseRepository(session)
    rows = await repo.list_for_project(project_id=project_id, user_id=user_id)
    return [ReviewerResponseRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/reviewer-responses",
    response_model=ReviewerResponseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reviewer_response(
    project_id: str,
    body: ReviewerResponseCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
    container: Container = Depends(get_container),
) -> ReviewerResponseRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    abstract = await _load_abstract(session, project_id, user_id)

    try:
        result = await container.ai.draft_reviewer_response(
            raw_comments=body.raw_comments, abstract=abstract
        )
    except AIRateLimited:
        raise HTTPException(status_code=429, detail="AI rate limited") from None
    except AISourceInsufficient as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except (AIProviderUnavailable, AIError):
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None
    except Exception:
        log.exception("Unexpected AI error in draft_reviewer_response")
        raise HTTPException(
            status_code=503, detail="AI provider unavailable"
        ) from None

    comments = result.get("comments") or []
    repo = SqliteReviewerResponseRepository(session)
    row = await repo.create(
        project_id=project_id,
        user_id=user_id,
        reviewer_label=body.reviewer_label,
        comments=comments,
    )
    return ReviewerResponseRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/reviewer-responses/{response_id}",
    response_model=ReviewerResponseRead,
)
async def patch_reviewer_response(
    project_id: str,
    response_id: str,
    body: ReviewerResponseUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ReviewerResponseRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewerResponseRepository(session)
    existing = await repo.get(response_id, user_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Reviewer response not found")

    comments_payload: list[dict] | None = None
    if body.comments is not None:
        comments_payload = [c.model_dump() for c in body.comments]

    row = await repo.update(
        response_id,
        user_id,
        reviewer_label=body.reviewer_label,
        comments=comments_payload,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Reviewer response not found")
    return ReviewerResponseRead.model_validate(row)


@router.delete(
    "/projects/{project_id}/reviewer-responses/{response_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reviewer_response(
    project_id: str,
    response_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewerResponseRepository(session)
    existing = await repo.get(response_id, user_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Reviewer response not found")
    await repo.delete(response_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/reviewer-responses/{response_id}/export/docx",
)
async def export_reviewer_response_docx(
    project_id: str,
    response_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    """Sub-export sweep HIGH bug — standalone DOCX for one reviewer row.

    The submission-package zip aggregates *all* reviewer responses into a
    single `response_to_reviewers.docx`. During iteration researchers also
    want per-row downloads so they can paste a single reviewer's reply
    into their journal portal without unzipping the full package.

    Returns 422 when the row has no comments — emitting a blank DOCX
    file would just confuse the recipient.
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewerResponseRepository(session)
    row = await repo.get(response_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Reviewer response not found")
    if not row.comments:
        raise HTTPException(
            status_code=422,
            detail="No comments to export — paste raw comments and draft first",
        )

    payload = ReviewerResponsePayload(
        reviewer_label=row.reviewer_label,
        comments=list(row.comments or []),
    )
    body_html = _build_response_to_reviewers_html([payload])
    title = f"Response — {row.reviewer_label}"
    data = html_to_docx_bytes(body_html, title=title)

    slug = _slugify_for_filename(row.reviewer_label)
    filename = f"{slug}_response.docx"
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
