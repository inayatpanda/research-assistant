"""Phase 4.6 — AI peer-review routes.

Endpoints (under ``/api`` via the mounted router prefix):

  GET    /projects/{pid}/peer-reviews
  GET    /projects/{pid}/peer-reviews/{id}
  POST   /projects/{pid}/peer-reviews/manuscript
  POST   /projects/{pid}/peer-reviews/upload          multipart `file`
  DELETE /projects/{pid}/peer-reviews/{id}
  POST   /projects/{pid}/peer-reviews/{id}/export?format=pdf|docx

All routes are scoped to the active user via ``container.settings.local_user_id``.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.peer_reviews import SqlitePeerReviewRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.peer_review import (
    PeerReviewManuscriptRequest,
    PeerReviewRead,
    PeerReviewSummary,
)
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)
from ..services.peer_review import (
    PeerReviewExtractError,
    extract_manuscript_for_peer_review,
    extract_uploaded_document,
    render_critique_docx,
    render_critique_pdf,
)

logger = logging.getLogger("research_api.peer_reviews")

router = APIRouter(tags=["peer_reviews"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


async def _ensure_project(
    project_id: str, session: AsyncSession, user_id: str
) -> None:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _to_summary(row) -> PeerReviewSummary:
    return PeerReviewSummary.model_validate(row)


def _to_read(row) -> PeerReviewRead:
    return PeerReviewRead.model_validate(row)


# ── List + Get ───────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/peer-reviews",
    response_model=list[PeerReviewSummary],
)
async def list_peer_reviews(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[PeerReviewSummary]:
    await _ensure_project(project_id, session, user_id)
    repo = SqlitePeerReviewRepository(session)
    rows = await repo.list_for_project(project_id, user_id)
    return [_to_summary(r) for r in rows]


@router.get(
    "/projects/{project_id}/peer-reviews/{peer_review_id}",
    response_model=PeerReviewRead,
)
async def get_peer_review(
    project_id: str,
    peer_review_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PeerReviewRead:
    await _ensure_project(project_id, session, user_id)
    repo = SqlitePeerReviewRepository(session)
    row = await repo.get(peer_review_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Peer review not found")
    return _to_read(row)


# ── Create (manuscript mode) ─────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/peer-reviews/manuscript",
    response_model=PeerReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_manuscript(
    project_id: str,
    body: PeerReviewManuscriptRequest | None = None,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PeerReviewRead:
    await _ensure_project(project_id, session, user_id)

    extraction = await extract_manuscript_for_peer_review(
        project_id=project_id, user_id=user_id, session=session
    )
    if not extraction.text.strip() or len(extraction.text.strip()) < 200:
        raise HTTPException(
            status_code=422,
            detail=(
                "Manuscript is too short to peer-review (need at least one"
                " filled section)."
            ),
        )

    title = (
        (body.title_override or "").strip()
        if body and body.title_override
        else extraction.title
    )

    repo = SqlitePeerReviewRepository(session)
    row = await repo.create_pending(
        project_id=project_id,
        user_id=user_id,
        source_type="manuscript",
        source_title=title or "Untitled manuscript",
        source_file_ref=None,
        manuscript_snapshot={
            "sections": extraction.sections,
            "metadata": extraction.metadata,
            "study_type": extraction.study_type,
        },
        ai_model=container.ai.active_model or "pending",
    )

    try:
        critique = await container.ai.peer_review(
            manuscript_text=extraction.text,
            title=title or extraction.title,
            study_type=extraction.study_type,
            metadata=extraction.metadata,
        )
    except AISourceInsufficient as e:
        await repo.mark_failed(
            peer_review_id=row.id, user_id=user_id, error=type(e).__name__
        )
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (AIProviderUnavailable, AIRateLimited, AIError) as e:
        logger.warning("peer_review AI error: %s: %s", type(e).__name__, e)
        await repo.mark_failed(
            peer_review_id=row.id, user_id=user_id, error=type(e).__name__
        )
        raise HTTPException(status_code=503, detail=type(e).__name__) from e
    except Exception as e:
        logger.exception("unexpected peer_review error")
        await repo.mark_failed(
            peer_review_id=row.id, user_id=user_id, error="UnexpectedAIError"
        )
        raise HTTPException(
            status_code=500, detail="Unexpected AI error"
        ) from e

    recommendation = str(critique.get("recommendation") or "major_revision")
    ai_model = str(critique.get("model") or container.ai.active_model or "unknown")
    row = await repo.mark_completed(
        peer_review_id=row.id,
        user_id=user_id,
        critique=_drop_model_key(critique),
        recommendation=recommendation,
        ai_model=ai_model,
    )
    assert row is not None
    return _to_read(row)


# ── Create (uploaded file mode) ──────────────────────────────────────────


@router.post(
    "/projects/{project_id}/peer-reviews/upload",
    response_model=PeerReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_upload(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PeerReviewRead:
    await _ensure_project(project_id, session, user_id)

    data = await file.read()
    try:
        extraction = extract_uploaded_document(
            data=data, original_filename=file.filename
        )
    except PeerReviewExtractError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e

    if not extraction.text.strip() or len(extraction.text.strip()) < 200:
        raise HTTPException(
            status_code=422,
            detail=(
                "Uploaded document did not yield enough text to peer-review."
            ),
        )

    ref = await container.storage.save(
        user_id, "peer-reviews", file.filename or "upload", data
    )
    file_ref: dict[str, Any] = {
        "backend": ref.backend,
        "key": ref.key,
        "filename": file.filename or "upload",
        "size": len(data),
        "mime": extraction.mime,
    }
    source_title = (file.filename or "Uploaded document")[:255]

    repo = SqlitePeerReviewRepository(session)
    row = await repo.create_pending(
        project_id=project_id,
        user_id=user_id,
        source_type=extraction.source_type,
        source_title=source_title,
        source_file_ref=file_ref,
        manuscript_snapshot=None,
        ai_model=container.ai.active_model or "pending",
    )

    try:
        critique = await container.ai.peer_review(
            manuscript_text=extraction.text,
            title=source_title,
            study_type=None,
            metadata={
                "n_figures": 0,
                "n_tables": 0,
                "n_references": 0,
                "n_authors": 0,
            },
        )
    except AISourceInsufficient as e:
        await repo.mark_failed(
            peer_review_id=row.id, user_id=user_id, error=type(e).__name__
        )
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (AIProviderUnavailable, AIRateLimited, AIError) as e:
        logger.warning("peer_review AI error: %s: %s", type(e).__name__, e)
        await repo.mark_failed(
            peer_review_id=row.id, user_id=user_id, error=type(e).__name__
        )
        raise HTTPException(status_code=503, detail=type(e).__name__) from e
    except Exception as e:
        logger.exception("unexpected peer_review error")
        await repo.mark_failed(
            peer_review_id=row.id, user_id=user_id, error="UnexpectedAIError"
        )
        raise HTTPException(
            status_code=500, detail="Unexpected AI error"
        ) from e

    recommendation = str(critique.get("recommendation") or "major_revision")
    ai_model = str(critique.get("model") or container.ai.active_model or "unknown")
    row = await repo.mark_completed(
        peer_review_id=row.id,
        user_id=user_id,
        critique=_drop_model_key(critique),
        recommendation=recommendation,
        ai_model=ai_model,
    )
    assert row is not None
    return _to_read(row)


# ── Delete + Export ──────────────────────────────────────────────────────


@router.delete(
    "/projects/{project_id}/peer-reviews/{peer_review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_peer_review(
    project_id: str,
    peer_review_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    await _ensure_project(project_id, session, user_id)
    repo = SqlitePeerReviewRepository(session)
    row = await repo.get(peer_review_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Peer review not found")
    # Delete the stored upload if present (best-effort — never blocks row delete).
    if row.source_file_ref:
        from ..services.storage import StorageRef

        try:
            await container.storage.delete(
                StorageRef(
                    backend=row.source_file_ref["backend"],
                    key=row.source_file_ref["key"],
                )
            )
        except Exception:
            pass
    await repo.delete(peer_review_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/peer-reviews/{peer_review_id}/export",
)
async def export_peer_review(
    project_id: str,
    peer_review_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    await _ensure_project(project_id, session, user_id)
    repo = SqlitePeerReviewRepository(session)
    row = await repo.get(peer_review_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Peer review not found")
    if row.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot export a review with status={row.status}",
        )
    critique = dict(row.critique or {})
    critique["recommendation"] = row.recommendation
    if format == "pdf":
        data = render_critique_pdf(
            source_title=row.source_title, critique=critique
        )
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="peer-review-{row.id}.pdf"'
                ),
            },
        )
    data = render_critique_docx(source_title=row.source_title, critique=critique)
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="peer-review-{row.id}.docx"'
            ),
        },
    )


def _drop_model_key(critique: dict[str, Any]) -> dict[str, Any]:
    """Return a copy without the transient ``model`` key (we persist it on the row)."""
    out = dict(critique)
    out.pop("model", None)
    return out
