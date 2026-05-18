"""Ingest routes (Phase 8.6).

Five ingest surfaces:

* ``POST /projects/{pid}/articles/lookup-doi``       — DOI → ArticleMetadata
* ``POST /projects/{pid}/articles/search-pubmed``    — search → list[ArticleMetadata]
* ``POST /projects/{pid}/articles/import-from-metadata`` — bulk-add to project
* ``POST /projects/{pid}/articles/import-ris``       — multipart .ris → preview
* ``POST /projects/{pid}/articles/import-bibtex``    — multipart .bib → preview

Two dedup surfaces:

* ``GET  /projects/{pid}/articles/duplicates``        — list[DuplicateGroup]
* ``POST /projects/{pid}/articles/merge-duplicates``  — keep + drop[] → kept row
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Article, new_id
from ..repositories.articles import SqliteArticleRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.article import ArticleRead
from ..schemas.ingest import (
    ArticleMetadata,
    DoiLookupRequest,
    DuplicateGroup,
    ImportFromMetadataRequest,
    ImportFromMetadataResponse,
    MergeRequest,
    PubMedSearchRequest,
)
from ..services.ingest.bibtex import parse_bibtex
from ..services.ingest.crossref import lookup_doi_metadata
from ..services.ingest.dedup import DuplicateCandidate, find_duplicates
from ..services.ingest.pubmed import PubMedFilters, search_pubmed
from ..services.ingest.ris import parse_ris

router = APIRouter(tags=["ingest"])

_FILE_SIZE_CAP = 2 * 1024 * 1024  # 2 MiB cap for RIS / BibTeX uploads
_RIS_MAGIC = "TY  -"
_BIBTEX_MAGIC = "@"


# ─── shared deps ────────────────────────────────────────────────────────────


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _attach_signed_url(
    article: ArticleRead, container: Container
) -> ArticleRead:
    if not article.file_ref:
        return article
    from ..services.storage import StorageRef

    ref = StorageRef(backend=article.file_ref["backend"], key=article.file_ref["key"])
    article.file_url = await container.storage.signed_url(ref, expires_in=3600)
    return article


async def _hydrated(orm: Article, container: Container) -> ArticleRead:
    return await _attach_signed_url(ArticleRead.model_validate(orm), container)


async def _resolve_project(
    session: AsyncSession, project_id: str, user_id: str
) -> None:
    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")


# ─── DOI lookup ─────────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/articles/lookup-doi",
    response_model=ArticleMetadata,
)
async def lookup_doi_route(
    project_id: str,
    body: DoiLookupRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ArticleMetadata:
    await _resolve_project(session, project_id, user_id)
    meta = await lookup_doi_metadata(
        body.doi, email=container.settings.entrez_email
    )
    if meta is None:
        raise HTTPException(
            status_code=404, detail="DOI not found in Crossref"
        )
    return meta


# ─── PubMed search ──────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/articles/search-pubmed",
    response_model=list[ArticleMetadata],
)
async def search_pubmed_route(
    project_id: str,
    body: PubMedSearchRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ArticleMetadata]:
    await _resolve_project(session, project_id, user_id)
    filters = (
        PubMedFilters(
            date_from=body.filters.date_from,
            date_to=body.filters.date_to,
            article_types=list(body.filters.article_types),
            english_only=body.filters.english_only,
        )
        if body.filters is not None
        else None
    )
    return await search_pubmed(
        body.query,
        retmax=body.retmax,
        sort=body.sort,
        filters=filters,
        api_key=container.settings.ncbi_api_key,
        email=container.settings.entrez_email,
    )


# ─── Import-from-metadata (bulk create) ─────────────────────────────────────


@router.post(
    "/projects/{project_id}/articles/import-from-metadata",
    response_model=ImportFromMetadataResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_from_metadata_route(
    project_id: str,
    body: ImportFromMetadataRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ImportFromMetadataResponse:
    await _resolve_project(session, project_id, user_id)

    # Load existing articles in the project once.
    from sqlalchemy import select

    existing_rows = list(
        (
            await session.execute(
                select(Article).where(
                    Article.project_id == project_id,
                    Article.user_id == user_id,
                )
            )
        )
        .scalars()
        .all()
    )

    created: list[Article] = []
    skipped: list[Article] = []
    existing_by_doi = {r.doi.lower(): r for r in existing_rows if r.doi}
    existing_by_pmid = {r.pmid: r for r in existing_rows if r.pmid}

    for item in body.items:
        match: Article | None = None
        if item.doi:
            match = existing_by_doi.get(item.doi.lower())
        if match is None and item.pmid:
            match = existing_by_pmid.get(item.pmid)
        if match is not None:
            skipped.append(match)
            continue

        a = Article(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            title=item.title,
            authors=item.authors,
            journal=item.journal,
            year=item.year,
            volume=item.volume,
            issue=item.issue,
            pages=item.pages,
            doi=item.doi,
            pmid=item.pmid,
            abstract=item.abstract,
            file_ref=None,
            file_type=None,
            source=item.source,
        )
        session.add(a)
        created.append(a)
        # Update dedup maps so subsequent items in the same batch skip too.
        if a.doi:
            existing_by_doi[a.doi.lower()] = a
        if a.pmid:
            existing_by_pmid[a.pmid] = a

    if created:
        await session.commit()
        for a in created:
            await session.refresh(a)

    # Build duplicate-group candidates over the union of existing + newly
    # created rows.
    all_rows = existing_rows + created
    candidates = [
        DuplicateCandidate(
            article_id=r.id,
            title=r.title,
            year=r.year,
            doi=r.doi,
            pmid=r.pmid,
        )
        for r in sorted(all_rows, key=lambda r: r.created_at or 0)
    ]
    duplicate_groups = find_duplicates(candidates)

    return ImportFromMetadataResponse(
        created=[await _hydrated(a, container) for a in created],
        skipped_duplicates=[await _hydrated(a, container) for a in skipped],
        duplicate_groups=duplicate_groups,
    )


# ─── RIS upload (multipart) ─────────────────────────────────────────────────


async def _read_text_payload(file: UploadFile) -> str:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > _FILE_SIZE_CAP:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {_FILE_SIZE_CAP // (1024 * 1024)} MiB cap",
        )
    return data.decode("utf-8", errors="replace")


@router.post(
    "/projects/{project_id}/articles/import-ris",
    response_model=list[ArticleMetadata],
)
async def import_ris_route(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ArticleMetadata]:
    await _resolve_project(session, project_id, user_id)
    text = await _read_text_payload(file)
    if _RIS_MAGIC not in text:
        raise HTTPException(
            status_code=422,
            detail="Not a valid RIS file (no TY  - record marker found)",
        )
    records = parse_ris(text)
    if not records:
        raise HTTPException(status_code=422, detail="No RIS records detected")
    return records


@router.post(
    "/projects/{project_id}/articles/import-bibtex",
    response_model=list[ArticleMetadata],
)
async def import_bibtex_route(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ArticleMetadata]:
    await _resolve_project(session, project_id, user_id)
    text = await _read_text_payload(file)
    if _BIBTEX_MAGIC not in text:
        raise HTTPException(
            status_code=422,
            detail="Not a valid BibTeX file (no @ entry marker found)",
        )
    records = parse_bibtex(text)
    if not records:
        raise HTTPException(
            status_code=422, detail="No BibTeX @article records detected"
        )
    return records


# ─── Duplicates GET + merge POST ────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/articles/duplicates",
    response_model=list[DuplicateGroup],
)
async def get_duplicates_route(
    project_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[DuplicateGroup]:
    await _resolve_project(session, project_id, user_id)

    from sqlalchemy import select

    rows = list(
        (
            await session.execute(
                select(Article)
                .where(
                    Article.project_id == project_id,
                    Article.user_id == user_id,
                )
                .order_by(Article.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    candidates = [
        DuplicateCandidate(
            article_id=r.id,
            title=r.title,
            year=r.year,
            doi=r.doi,
            pmid=r.pmid,
        )
        for r in rows
    ]
    return find_duplicates(candidates)


@router.post(
    "/projects/{project_id}/articles/merge-duplicates",
    response_model=ArticleRead,
)
async def merge_duplicates_route(
    project_id: str,
    body: MergeRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ArticleRead:
    await _resolve_project(session, project_id, user_id)

    repo = SqliteArticleRepository(session)
    # Verify the keep article belongs to THIS project before delegating.
    keep = await repo.get(body.keep_id, user_id)
    if keep is None or keep.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")

    try:
        kept = await repo.merge(
            keep_id=body.keep_id,
            drop_ids=body.drop_ids,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return await _hydrated(kept, container)
