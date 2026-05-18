"""Phase 10 — ICMJE front-matter routes.

Twelve endpoints across five resources:

  Authors (under /api/projects/{project_id}/authors)
    GET    /                          list authors (ordered by position)
    POST   /                          create author
    PATCH  /{author_id}                update author
    DELETE /{author_id}                delete author
    POST   /reorder                   reorder ids
    POST   /{author_id}/set-corresponding  flip is_corresponding=true; clears others

  Affiliations (under /api/projects/{project_id}/affiliations)
    GET    /
    POST   /
    PATCH  /{aff_id}
    DELETE /{aff_id}
    POST   /reorder

  Author-Affiliation m2m (mounted under authors)
    POST   /api/authors/{author_id}/affiliations/{aff_id}     link
    DELETE /api/authors/{author_id}/affiliations/{aff_id}     unlink

  Contributions
    POST   /api/authors/{author_id}/contributions  body: {role}
    DELETE /api/authors/{author_id}/contributions/{role}

  Front matter
    GET   /api/projects/{project_id}/frontmatter   auto-creates on first GET
    PATCH /api/projects/{project_id}/frontmatter
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Author, Affiliation, ProjectFrontmatter
from ..repositories.frontmatter import (
    _UNSET,
    SqliteAffiliationRepository,
    SqliteAuthorRepository,
    SqliteContributionRepository,
    SqliteFrontmatterRepository,
)
from ..repositories.projects import SqliteProjectRepository
from ..schemas.frontmatter import (
    AffiliationCreate,
    AffiliationRead,
    AffiliationReorderRequest,
    AffiliationUpdate,
    AuthorCreate,
    AuthorRead,
    AuthorReorderRequest,
    AuthorUpdate,
    ContributionRead,
    ContributionSetRequest,
    CREDIT_ROLES,
    ProjectFrontmatterRead,
    ProjectFrontmatterUpdate,
    StructuredAbstract,
)


router = APIRouter(tags=["frontmatter"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _hydrate_author(
    author: Author, aff_repo: SqliteAffiliationRepository, user_id: str
) -> AuthorRead:
    links = await aff_repo.list_links_for_author(author.id, user_id)
    read = AuthorRead.model_validate(author)
    read.affiliation_ids = [link.affiliation_id for link in links]
    return read


def _hydrate_frontmatter(row: ProjectFrontmatter) -> ProjectFrontmatterRead:
    funders = row.funders or []
    sa = row.structured_abstract or {}
    abstract = StructuredAbstract(
        background=sa.get("background", "") or "",
        methods=sa.get("methods", "") or "",
        results=sa.get("results", "") or "",
        conclusions=sa.get("conclusions", "") or "",
    )
    return ProjectFrontmatterRead(
        id=row.id,
        project_id=row.project_id,
        funding_statement=row.funding_statement,
        funders=funders,  # Pydantic validates the dicts → Funder
        ethics_irb=row.ethics_irb,
        ethics_approval_number=row.ethics_approval_number,
        ethics_consent=row.ethics_consent,
        conflicts_statement=row.conflicts_statement,
        structured_abstract_enabled=row.structured_abstract_enabled,
        structured_abstract=abstract,
        updated_at=row.updated_at,
    )


# ── Authors ───────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/authors", response_model=list[AuthorRead]
)
async def list_authors(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AuthorRead]:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAuthorRepository(session)
    aff_repo = SqliteAffiliationRepository(session)
    rows = await repo.list(project_id=project_id, user_id=user_id)
    return [await _hydrate_author(r, aff_repo, user_id) for r in rows]


@router.post(
    "/projects/{project_id}/authors",
    response_model=AuthorRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_author(
    project_id: str,
    body: AuthorCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AuthorRead:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAuthorRepository(session)
    author = await repo.create(
        project_id=project_id,
        user_id=user_id,
        full_name=body.full_name,
        given_name=body.given_name,
        family_name=body.family_name,
        orcid=body.orcid,
        email=body.email,
        is_corresponding=body.is_corresponding,
    )
    aff_repo = SqliteAffiliationRepository(session)
    return await _hydrate_author(author, aff_repo, user_id)


@router.patch("/authors/{author_id}", response_model=AuthorRead)
async def update_author(
    author_id: str,
    body: AuthorUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AuthorRead:
    repo = SqliteAuthorRepository(session)
    # Distinguish "field not supplied" from "field set to null" for orcid/email
    # by inspecting the body's fields_set.
    patch = body.model_dump(exclude_unset=True)
    updated = await repo.update(
        author_id,
        user_id,
        full_name=patch.get("full_name"),
        given_name=patch.get("given_name"),
        family_name=patch.get("family_name"),
        orcid=patch["orcid"] if "orcid" in patch else _UNSET,  # type: ignore[arg-type]
        email=patch["email"] if "email" in patch else _UNSET,  # type: ignore[arg-type]
        is_corresponding=patch.get("is_corresponding"),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Author not found")
    aff_repo = SqliteAffiliationRepository(session)
    return await _hydrate_author(updated, aff_repo, user_id)


@router.delete("/authors/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_author(
    author_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteAuthorRepository(session)
    deleted = await repo.delete(author_id, user_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return None


@router.post(
    "/projects/{project_id}/authors/reorder",
    response_model=list[AuthorRead],
)
async def reorder_authors(
    project_id: str,
    body: AuthorReorderRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AuthorRead]:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAuthorRepository(session)
    try:
        rows = await repo.reorder(
            project_id=project_id,
            user_id=user_id,
            ordered_ids=body.ordered_author_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    aff_repo = SqliteAffiliationRepository(session)
    return [await _hydrate_author(r, aff_repo, user_id) for r in rows]


@router.post(
    "/authors/{author_id}/set-corresponding", response_model=AuthorRead
)
async def set_corresponding_author(
    author_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AuthorRead:
    repo = SqliteAuthorRepository(session)
    updated = await repo.set_corresponding(author_id, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Author not found")
    aff_repo = SqliteAffiliationRepository(session)
    return await _hydrate_author(updated, aff_repo, user_id)


# ── Affiliations ──────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/affiliations",
    response_model=list[AffiliationRead],
)
async def list_affiliations(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AffiliationRead]:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAffiliationRepository(session)
    rows = await repo.list(project_id=project_id, user_id=user_id)
    return [AffiliationRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/affiliations",
    response_model=AffiliationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_affiliation(
    project_id: str,
    body: AffiliationCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AffiliationRead:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAffiliationRepository(session)
    aff = await repo.create(
        project_id=project_id,
        user_id=user_id,
        name=body.name,
        address=body.address,
        city=body.city,
        country=body.country,
    )
    return AffiliationRead.model_validate(aff)


@router.patch(
    "/affiliations/{affiliation_id}", response_model=AffiliationRead
)
async def update_affiliation(
    affiliation_id: str,
    body: AffiliationUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AffiliationRead:
    repo = SqliteAffiliationRepository(session)
    patch = body.model_dump(exclude_unset=True)
    updated = await repo.update(
        affiliation_id,
        user_id,
        name=patch.get("name"),
        address=patch["address"] if "address" in patch else _UNSET,  # type: ignore[arg-type]
        city=patch["city"] if "city" in patch else _UNSET,  # type: ignore[arg-type]
        country=patch["country"] if "country" in patch else _UNSET,  # type: ignore[arg-type]
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Affiliation not found")
    return AffiliationRead.model_validate(updated)


@router.delete(
    "/affiliations/{affiliation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_affiliation(
    affiliation_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteAffiliationRepository(session)
    deleted = await repo.delete(affiliation_id, user_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Affiliation not found")
    return None


@router.post(
    "/projects/{project_id}/affiliations/reorder",
    response_model=list[AffiliationRead],
)
async def reorder_affiliations(
    project_id: str,
    body: AffiliationReorderRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AffiliationRead]:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAffiliationRepository(session)
    try:
        rows = await repo.reorder(
            project_id=project_id,
            user_id=user_id,
            ordered_ids=body.ordered_affiliation_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return [AffiliationRead.model_validate(r) for r in rows]


# ── Author ↔ Affiliation m2m ──────────────────────────────────────────


@router.post(
    "/authors/{author_id}/affiliations/{affiliation_id}",
    response_model=AuthorRead,
)
async def link_author_affiliation(
    author_id: str,
    affiliation_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AuthorRead:
    aff_repo = SqliteAffiliationRepository(session)
    link = await aff_repo.link(
        author_id=author_id,
        affiliation_id=affiliation_id,
        user_id=user_id,
    )
    if link is None:
        raise HTTPException(
            status_code=404,
            detail="Author and affiliation must both belong to the user and project",
        )
    author = await SqliteAuthorRepository(session).get(author_id, user_id)
    if author is None:  # pragma: no cover — defensive
        raise HTTPException(status_code=404, detail="Author not found")
    return await _hydrate_author(author, aff_repo, user_id)


@router.delete(
    "/authors/{author_id}/affiliations/{affiliation_id}",
    response_model=AuthorRead,
)
async def unlink_author_affiliation(
    author_id: str,
    affiliation_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AuthorRead:
    aff_repo = SqliteAffiliationRepository(session)
    author = await SqliteAuthorRepository(session).get(author_id, user_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    removed = await aff_repo.unlink(
        author_id=author_id,
        affiliation_id=affiliation_id,
        user_id=user_id,
    )
    if not removed:
        # Either the affiliation didn't belong to this user, or the link was
        # already absent. Surface 404 to match other DELETE semantics.
        raise HTTPException(status_code=404, detail="Link not found")
    return await _hydrate_author(author, aff_repo, user_id)


# ── Contributions ─────────────────────────────────────────────────────


@router.get(
    "/authors/{author_id}/contributions",
    response_model=list[ContributionRead],
)
async def list_contributions(
    author_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ContributionRead]:
    author = await SqliteAuthorRepository(session).get(author_id, user_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    repo = SqliteContributionRepository(session)
    rows = await repo.list_for_author(author_id, user_id)
    return [ContributionRead.model_validate(r) for r in rows]


@router.post(
    "/authors/{author_id}/contributions",
    response_model=ContributionRead,
    status_code=status.HTTP_201_CREATED,
)
async def set_contribution(
    author_id: str,
    body: ContributionSetRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ContributionRead:
    if body.role not in CREDIT_ROLES:
        raise HTTPException(status_code=422, detail="Unknown CRediT role")
    repo = SqliteContributionRepository(session)
    contribution = await repo.set(
        author_id=author_id, role=body.role, user_id=user_id
    )
    if contribution is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return ContributionRead.model_validate(contribution)


@router.delete(
    "/authors/{author_id}/contributions/{role}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_contribution(
    author_id: str,
    role: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    author = await SqliteAuthorRepository(session).get(author_id, user_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    repo = SqliteContributionRepository(session)
    await repo.clear(author_id=author_id, role=role, user_id=user_id)
    return None


# ── Project Frontmatter ───────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/frontmatter",
    response_model=ProjectFrontmatterRead,
)
async def get_project_frontmatter(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ProjectFrontmatterRead:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteFrontmatterRepository(session)
    row = await repo.get_or_create(project_id=project_id, user_id=user_id)
    return _hydrate_frontmatter(row)


@router.patch(
    "/projects/{project_id}/frontmatter",
    response_model=ProjectFrontmatterRead,
)
async def patch_project_frontmatter(
    project_id: str,
    body: ProjectFrontmatterUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ProjectFrontmatterRead:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteFrontmatterRepository(session)
    patch_data = body.model_dump(exclude_unset=True)
    # Coerce Pydantic submodels to plain dicts for JSON storage.
    if "funders" in patch_data and patch_data["funders"] is not None:
        patch_data["funders"] = [
            f if isinstance(f, dict) else f.model_dump()
            for f in patch_data["funders"]
        ]
    if (
        "structured_abstract" in patch_data
        and patch_data["structured_abstract"] is not None
    ):
        sa = patch_data["structured_abstract"]
        patch_data["structured_abstract"] = (
            sa if isinstance(sa, dict) else sa.model_dump()
        )
    row = await repo.update(
        project_id=project_id, user_id=user_id, patch=patch_data
    )
    assert row is not None
    return _hydrate_frontmatter(row)
