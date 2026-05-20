"""Article routes: upload pipeline + CRUD.

Upload pipeline:
1. Validate (MIME, size cap, filename normalised)
2. storage.save -> StorageRef
3. pdf_text.extract -> string
4. ai.extract_citation -> CitationMetadata (catch errors gracefully)
5. If DOI present: crossref.lookup_doi to enrich/correct
6. Merge metadata (CrossRef wins on overlap because confidence=1.0)
7. repo.find_duplicate -> existing article if any
8. repo.create -> new article
9. Return UploadResponse with signed URL attached
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.articles import SqliteArticleRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.article import (
    ArticleCreate,
    ArticleFilters,
    ArticleRead,
    ArticleUpdate,
    ReviewStatus,
    StorageRefSchema,
)
from ..schemas.upload import ExtractionSource, UploadResponse
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
    CitationMetadata,
)
from ..services.crossref import lookup_doi
from ..services.pdf_text import detect_mime, extract_first_pages_text

router = APIRouter(tags=["articles"])


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


def _orm_to_read(orm) -> ArticleRead:
    return ArticleRead.model_validate(orm)


async def _hydrated(orm, container: Container) -> ArticleRead:
    return await _attach_signed_url(_orm_to_read(orm), container)


# ─── Upload pipeline ────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/articles/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_article(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> UploadResponse:
    settings = container.settings

    # 0. Verify project exists & belongs to user
    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Read + validate
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.file_size_cap_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.file_size_cap_mb} MB cap",
        )
    mime = detect_mime(data)
    if mime not in settings.allowed_upload_mime:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported MIME {mime}; allowed: {settings.allowed_upload_mime}",
        )

    # 2. Save to storage
    ref = await container.storage.save(
        user_id, "articles", file.filename or "upload", data
    )

    # 3. Extract text
    text = extract_first_pages_text(data, n=2)

    # 4. AI extraction (best effort)
    ai_meta: CitationMetadata | None = None
    extraction_error: str | None = None
    try:
        ai_meta = await container.ai.extract_citation(text)
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as e:
        # Return error CLASS only (e.g. "AIRateLimited"). The message may
        # contain provider-internal details (endpoints, partial keys); keep
        # those in server logs, not in the API response.
        import logging
        logging.getLogger("research_api.articles").warning(
            "AI extraction failed: %s: %s", type(e).__name__, e
        )
        extraction_error = type(e).__name__
    except Exception:
        import logging
        logging.getLogger("research_api.articles").exception("Unexpected AI error")
        extraction_error = "UnexpectedAIError"

    # 5. CrossRef enrichment if DOI present
    cr_meta: CitationMetadata | None = None
    doi_candidate = ai_meta.doi if ai_meta else None
    if doi_candidate:
        cr_meta = await lookup_doi(doi_candidate)

    # 6. Merge metadata
    merged, source = _merge_metadata(ai_meta, cr_meta)
    if merged is None:
        # Could not extract anything useful — create with bare filename
        merged = CitationMetadata(title=file.filename or "Untitled upload", confidence=0.0)
        source = "none"

    # 7. Duplicate check
    repo = SqliteArticleRepository(session)
    duplicate = await repo.find_duplicate(
        project_id=project_id, doi=merged.doi, title=merged.title, user_id=user_id
    )

    # 8. Create row (even if duplicate — keep both so the user can review and merge)
    article_create = ArticleCreate(
        title=merged.title,
        authors=merged.authors,
        journal=merged.journal,
        year=merged.year,
        volume=merged.volume,
        issue=merged.issue,
        pages=merged.pages,
        doi=merged.doi,
        file_ref=StorageRefSchema(backend=ref.backend, key=ref.key),
        file_type=mime,
    )
    article = await repo.create(
        project_id=project_id, data=article_create, user_id=user_id
    )

    return UploadResponse(
        article=await _hydrated(article, container),
        duplicate_of=await _hydrated(duplicate, container) if duplicate else None,
        extraction_source=source,
        extraction_error=extraction_error,
    )


def _merge_metadata(
    ai: CitationMetadata | None, cr: CitationMetadata | None
) -> tuple[CitationMetadata | None, ExtractionSource]:
    """CrossRef wins on overlap (confidence=1.0); AI fills gaps."""
    if cr and ai:
        merged = CitationMetadata(
            title=cr.title or ai.title,
            authors=cr.authors or ai.authors,
            journal=cr.journal or ai.journal,
            year=cr.year or ai.year,
            volume=cr.volume or ai.volume,
            issue=cr.issue or ai.issue,
            pages=cr.pages or ai.pages,
            doi=cr.doi or ai.doi,
            confidence=max(cr.confidence, ai.confidence),
        )
        return merged, "both"
    if cr:
        return cr, "crossref"
    if ai:
        return ai, "ai"
    return None, "none"


# ─── List + CRUD ────────────────────────────────────────────────────────────


# Sort keys the backend understands (the ArticleFilters Literal). Anything
# else is coerced to ``created_desc`` so a bogus query string can't 500 the
# whole list endpoint (#L-sort-500).
_ALLOWED_SORT_KEYS = {"year_desc", "year_asc", "title", "created_desc"}


@router.get("/projects/{project_id}/articles", response_model=list[ArticleRead])
async def list_articles(
    project_id: str,
    q: str | None = Query(default=None),
    review_status: ReviewStatus | None = Query(default=None),
    study_design: str | None = Query(default=None),
    sort: str = Query(default="created_desc"),
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ArticleRead]:
    repo = SqliteArticleRepository(session)
    safe_sort = sort if sort in _ALLOWED_SORT_KEYS else "created_desc"
    filters = ArticleFilters(
        q=q,
        review_status=review_status,
        study_design=study_design,
        sort=safe_sort,  # type: ignore[arg-type]
    )
    rows = await repo.list_for_project(project_id, user_id, filters)
    return [await _hydrated(a, container) for a in rows]


@router.get("/articles/{article_id}", response_model=ArticleRead)
async def get_article(
    article_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ArticleRead:
    repo = SqliteArticleRepository(session)
    found = await repo.get(article_id, user_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return await _hydrated(found, container)


@router.patch("/articles/{article_id}", response_model=ArticleRead)
async def update_article(
    article_id: str,
    patch: ArticleUpdate,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ArticleRead:
    repo = SqliteArticleRepository(session)
    updated = await repo.update(article_id, patch, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return await _hydrated(updated, container)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteArticleRepository(session)
    found = await repo.get(article_id, user_id)
    if found is not None and found.file_ref:
        from ..services.storage import StorageRef

        try:
            await container.storage.delete(
                StorageRef(backend=found.file_ref["backend"], key=found.file_ref["key"])
            )
        except Exception:
            pass  # file gone is OK; don't block row delete
    await repo.delete(article_id, user_id)
