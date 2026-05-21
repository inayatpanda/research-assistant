"""Phase 12 — Cover-letter routes.

Endpoints (under /api/projects/{project_id}/cover-letter):

  GET   /                  get or auto-create the cover letter row
  PATCH /                  partial update (target_journal / novelty / body_html)
  POST  /draft             AI-draft the body_html using the persisted journal
                           + novelty bullets + ICMJE corresponding author
"""
from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..db.models import (
    Affiliation,
    Author,
    AuthorAffiliation,
    ManuscriptSection,
    ProjectFrontmatter,
)
from ..repositories.cover_letters import SqliteCoverLetterRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.cover_letter import (
    CoverLetterDraftRequest,
    CoverLetterRead,
    CoverLetterUpdate,
)
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)
from ..services.export.docx_export import html_to_docx_bytes
from ..services.journal_templates.catalogue import JOURNALS

router = APIRouter(tags=["cover-letter"])
log = logging.getLogger("research_api.cover_letter")


_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _slugify_for_filename(title: str | None) -> str:
    """Filesystem-safe slug for the standalone DOCX download.

    Mirrors the rule used by `submission_package.slugify_for_zip` so the
    standalone export and the bundled package share the same filename stem
    when the user downloads both.
    """
    raw = (title or "").strip().replace(" ", "-")
    s = _SLUG_RE.sub("", raw).strip("-_")
    return (s or "project")[:80]


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


def _validate_journal(key: str | None) -> str | None:
    """Reject unknown journal keys at the route boundary.

    None is fine — the cover letter row is allowed to be journal-less until
    the user picks one before drafting.
    """
    if key is None or key == "":
        return None
    if key not in JOURNALS:
        raise HTTPException(
            status_code=422, detail=f"Unknown journal key: {key!r}"
        )
    return key


async def _load_corresponding(
    session: AsyncSession, project_id: str, user_id: str
) -> tuple[str | None, str | None, str | None]:
    """Resolve the corresponding-author display fields from MP10 rows.

    Returns (name, affiliation_text, email). All three may be None when no
    authors have been added.
    """
    stmt = (
        select(Author)
        .where(
            Author.project_id == project_id,
            Author.user_id == user_id,
            Author.is_corresponding.is_(True),
        )
        .order_by(Author.position.asc())
    )
    author = (await session.execute(stmt)).scalars().first()
    if author is None:
        # Fall back to the first author by position so the cover letter
        # at least has *something* under the signature line.
        stmt = (
            select(Author)
            .where(Author.project_id == project_id, Author.user_id == user_id)
            .order_by(Author.position.asc())
        )
        author = (await session.execute(stmt)).scalars().first()
    if author is None:
        return None, None, None

    # Resolve the first affiliation linked to this author.
    aff_stmt = (
        select(Affiliation)
        .join(
            AuthorAffiliation,
            AuthorAffiliation.affiliation_id == Affiliation.id,
        )
        .where(
            AuthorAffiliation.author_id == author.id,
            AuthorAffiliation.user_id == user_id,
        )
        .order_by(AuthorAffiliation.position.asc())
    )
    aff = (await session.execute(aff_stmt)).scalars().first()
    aff_text: str | None = None
    if aff is not None:
        parts = [aff.name, aff.address, aff.city, aff.country]
        aff_text = ", ".join(p for p in parts if p)
    return author.full_name, aff_text, author.email


async def _load_abstract_and_title(
    session: AsyncSession, project_id: str, user_id: str
) -> tuple[str, str]:
    """Pull the project title + Abstract section text for the prompt.

    Falls back to the project title if no Abstract section exists yet.
    Honours the MP10 structured-abstract pathway by flattening the four
    sub-fields into a paragraph block.
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    title = (project.title if project else "") or "Untitled manuscript"

    frontmatter = (
        await session.execute(
            select(ProjectFrontmatter).where(
                ProjectFrontmatter.project_id == project_id,
                ProjectFrontmatter.user_id == user_id,
            )
        )
    ).scalar_one_or_none()

    if (
        frontmatter
        and frontmatter.structured_abstract_enabled
        and isinstance(frontmatter.structured_abstract, dict)
    ):
        sa = frontmatter.structured_abstract
        chunks = [
            f"Background: {sa.get('background', '').strip()}",
            f"Methods: {sa.get('methods', '').strip()}",
            f"Results: {sa.get('results', '').strip()}",
            f"Conclusions: {sa.get('conclusions', '').strip()}",
        ]
        return title, "\n".join(c for c in chunks if c.endswith(":") is False)

    sec = (
        await session.execute(
            select(ManuscriptSection).where(
                ManuscriptSection.project_id == project_id,
                ManuscriptSection.user_id == user_id,
                ManuscriptSection.section_name == "Abstract",
            )
        )
    ).scalar_one_or_none()
    return title, (sec.content if sec else "") or ""


@router.get(
    "/projects/{project_id}/cover-letter",
    response_model=CoverLetterRead,
)
async def get_cover_letter(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CoverLetterRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteCoverLetterRepository(session)
    row = await repo.get_or_create(project_id=project_id, user_id=user_id)
    return CoverLetterRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/cover-letter",
    response_model=CoverLetterRead,
)
async def patch_cover_letter(
    project_id: str,
    body: CoverLetterUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CoverLetterRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteCoverLetterRepository(session)
    # Ensure a row exists so a PATCH on a fresh project works without an
    # extra GET. Auto-creation is also what the GET does.
    await repo.get_or_create(project_id=project_id, user_id=user_id)
    journal = _validate_journal(body.target_journal)

    kwargs: dict = {}
    if body.target_journal is not None:
        kwargs["target_journal"] = journal
    if body.novelty_points is not None:
        kwargs["novelty_points"] = body.novelty_points
    if body.body_html is not None:
        kwargs["body_html"] = body.body_html

    row = await repo.update(project_id=project_id, user_id=user_id, **kwargs)
    if row is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return CoverLetterRead.model_validate(row)


@router.post(
    "/projects/{project_id}/cover-letter/draft",
    response_model=CoverLetterRead,
)
async def draft_cover_letter(
    project_id: str,
    body: CoverLetterDraftRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
    container: Container = Depends(get_container),
) -> CoverLetterRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteCoverLetterRepository(session)
    row = await repo.get_or_create(project_id=project_id, user_id=user_id)

    # Validate optional overrides at the boundary so the prompt only sees a
    # legitimate journal label.
    override_journal = _validate_journal(body.target_journal)
    journal_key = override_journal or row.target_journal
    if not journal_key:
        raise HTTPException(
            status_code=422,
            detail="target_journal is required (pick one before drafting)",
        )
    journal = JOURNALS.get(journal_key)
    if journal is None:
        # Belt-and-braces — _validate_journal already screens unknowns.
        raise HTTPException(
            status_code=422, detail=f"Unknown journal key: {journal_key!r}"
        )

    novelty = body.novelty_points if body.novelty_points is not None else (
        row.novelty_points or []
    )

    title, abstract = await _load_abstract_and_title(
        session, project_id, user_id
    )
    name, aff_text, email = await _load_corresponding(
        session, project_id, user_id
    )
    frontmatter = (
        await session.execute(
            select(ProjectFrontmatter).where(
                ProjectFrontmatter.project_id == project_id,
                ProjectFrontmatter.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    conflicts = frontmatter.conflicts_statement if frontmatter else None

    try:
        result = await container.ai.draft_cover_letter(
            title=title,
            abstract=abstract,
            journal_label=journal.label,
            novelty_points=novelty,
            corresponding_name=name,
            corresponding_affiliation=aff_text,
            corresponding_email=email,
            conflicts_statement=conflicts,
        )
    except AIRateLimited:
        raise HTTPException(status_code=429, detail="AI rate limited") from None
    except AISourceInsufficient as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except (AIProviderUnavailable, AIError):
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None
    except Exception:
        log.exception("Unexpected AI error in draft_cover_letter")
        raise HTTPException(
            status_code=503, detail="AI provider unavailable"
        ) from None

    updated = await repo.update(
        project_id=project_id,
        user_id=user_id,
        target_journal=journal_key,
        novelty_points=novelty,
        body_html=result.get("body_html", ""),
        ai_model=result.get("model"),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return CoverLetterRead.model_validate(updated)


@router.post(
    "/projects/{project_id}/cover-letter/export/docx",
)
async def export_cover_letter_docx(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    """Sub-export sweep HIGH bug — standalone DOCX for the cover letter.

    The submission-package zip embeds `cover_letter.docx`, but researchers
    iterating on the prose want to download the letter on its own without
    pulling the entire manuscript bundle.

    Returns 422 when no cover letter has been drafted yet (body_html
    empty) — generating an "(Empty)" DOCX on the user's machine would be
    misleading.
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteCoverLetterRepository(session)
    row = await repo.get_or_create(project_id=project_id, user_id=user_id)
    body_html = (row.body_html or "").strip()
    if not body_html:
        raise HTTPException(
            status_code=422,
            detail="Cover letter is empty — draft or paste a body first",
        )

    journal = JOURNALS.get(row.target_journal or "") if row.target_journal else None
    title = (
        f"Cover Letter — {journal.label}"
        if journal is not None
        else "Cover Letter"
    )
    data = html_to_docx_bytes(body_html, title=title)

    slug = _slugify_for_filename(project.title)
    filename = f"{slug}_cover_letter.docx"
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
