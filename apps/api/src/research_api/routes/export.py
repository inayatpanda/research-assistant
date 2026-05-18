"""Export + import routes: DOCX / PDF / Bundle export, and Bundle import."""
from __future__ import annotations

import io
import json
import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import (
    Abbreviation,
    Analysis,
    AnalysisResult,
    Article,
    ArticleNote,
    ConsortData,
    Dataset,
    DatasetVariable,
    ExtractionRecord,
    Figure,
    Highlight,
    ManuscriptSection,
    MetaAnalysis,
    MetaInput,
    Project,
    Review,
    RobAssessment,
    ScreeningRecord,
    SearchRecord,
)
from ..repositories.articles import SqliteArticleRepository
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.article import ArticleFilters
from ..schemas.export import (
    BibliographyEntryRead,
    BibliographyResponse,
    BundleImportResponse,
)
from ..services.citation_format import (
    CitationStyle,
    bibliography_entry,
    consolidate_inline_clusters,
    format_entry,
)
from ..services.export.bibliography import (
    CANONICAL_SECTION_ORDER,
    build_bibliography,
)
from ..services.export.bundle_export import BundleInputs, build_bundle
from ..services.export.bundle_import import BundleImportError, import_bundle
from ..services.export.docx_export import render_docx
from ..services.export.pdf_export import render_pdf

router = APIRouter(tags=["export"])
log = logging.getLogger("research_api.export")

_ALLOWED_STYLES: tuple[CitationStyle, ...] = ("vancouver", "apa", "harvard", "ieee")
# UI-facing aliases; the user sees "APA 7" so `?style=apa7` must be accepted
# and resolved to the canonical `apa`.
_STYLE_ALIASES: dict[str, CitationStyle] = {"apa7": "apa"}
_IMPORT_SIZE_CAP_BYTES = 50 * 1024 * 1024  # 50 MiB
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9_-]+")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


def _slugify_filename(title: str | None) -> str:
    """Slugify project title for Content-Disposition.

    Strips path traversal, control chars; keeps only `[A-Za-z0-9_-]`. Falls
    back to `project` if the slug would be empty.
    """
    raw = (title or "").strip()
    raw = raw.replace(" ", "-")
    slug = _FILENAME_SAFE_RE.sub("", raw)
    slug = slug.strip("-_") or "project"
    return slug[:80]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _coerce_style(style: str | None, project_style: str) -> CitationStyle:
    s = style or project_style
    # Map aliases (e.g. `apa7` → `apa`) before validating.
    s = _STYLE_ALIASES.get(s, s)
    if s not in _ALLOWED_STYLES:
        raise HTTPException(status_code=422, detail=f"Unsupported citation style: {s!r}")
    return s  # type: ignore[return-value]


async def _load_articles(session: AsyncSession, project_id: str, user_id: str) -> list[Article]:
    return await SqliteArticleRepository(session).list_for_project(
        project_id, user_id, ArticleFilters()
    )


async def _load_sections(session: AsyncSession, project_id: str, user_id: str) -> list[ManuscriptSection]:
    return await SqliteManuscriptSectionRepository(session).list_for_project(
        project_id, user_id
    )


async def _build_bib_entries(
    sections: list[ManuscriptSection], articles: list[Article], style: CitationStyle
):
    by_id = {a.id: a for a in articles}
    return build_bibliography(articles_by_id=by_id, sections=sections, style=style)


class _ConsolidatedSection:
    """Lightweight stand-in for a ManuscriptSection used by render_docx/pdf.

    Decoupled from the ORM class so we can safely mutate `content` without
    poisoning the SQLAlchemy session-managed row.
    """
    __slots__ = ("section_name", "content")

    def __init__(self, section_name: str, content: str) -> None:
        self.section_name = section_name
        self.content = content


def _consolidate_sections(
    sections: list[ManuscriptSection], style: CitationStyle
) -> list[_ConsolidatedSection]:
    """Return shallow copies of `sections` with inline citation clusters
    consolidated per `style`. Original ORM rows are NOT mutated."""
    return [
        _ConsolidatedSection(
            section_name=s.section_name,
            content=consolidate_inline_clusters(s.content or "", style),
        )
        for s in sections
    ]


def _first_section_by_article(
    sections: list[ManuscriptSection],
) -> dict[str, str]:
    """Walk sections in canonical order, recording the first section where
    each article id was cited (mirrors the bibliography service's order)."""
    out: dict[str, str] = {}
    by_name = {s.section_name: s for s in sections}
    from ..services.export.bibliography import _CITE_OR_ATTR
    for name in CANONICAL_SECTION_ORDER:
        s = by_name.get(name)
        if s is None:
            continue
        for m in _CITE_OR_ATTR.finditer(s.content or ""):
            aid = m.group(1) or m.group(2)
            if aid and aid not in out:
                out[aid] = name
    return out


@router.post("/projects/{project_id}/export/docx")
async def export_docx(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> StreamingResponse:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    sections = await _load_sections(session, project_id, user_id)
    articles = await _load_articles(session, project_id, user_id)
    style = _coerce_style(None, project.citation_style)
    entries = await _build_bib_entries(sections, articles, style)
    consolidated = _consolidate_sections(sections, style)
    data = render_docx(project=project, sections=consolidated, bibliography=entries)

    slug = _slugify_filename(project.title)
    filename = f"{slug}-{_today()}.docx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/projects/{project_id}/export/pdf")
async def export_pdf(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> StreamingResponse:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    sections = await _load_sections(session, project_id, user_id)
    articles = await _load_articles(session, project_id, user_id)
    style = _coerce_style(None, project.citation_style)
    entries = await _build_bib_entries(sections, articles, style)
    consolidated = _consolidate_sections(sections, style)
    data = render_pdf(project=project, sections=consolidated, bibliography=entries)

    slug = _slugify_filename(project.title)
    filename = f"{slug}-{_today()}.pdf"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _collect_bundle_inputs(
    session: AsyncSession, *, project: Project, user_id: str
) -> BundleInputs:
    project_id = project.id
    articles = await _load_articles(session, project_id, user_id)
    article_ids = [a.id for a in articles]

    highlights: list[Highlight] = []
    article_notes: list[ArticleNote] = []
    if article_ids:
        highlights = list((await session.execute(
            select(Highlight).where(
                Highlight.user_id == user_id,
                Highlight.article_id.in_(article_ids),
            )
        )).scalars().all())
        article_notes = list((await session.execute(
            select(ArticleNote).where(
                ArticleNote.user_id == user_id,
                ArticleNote.article_id.in_(article_ids),
            )
        )).scalars().all())

    sections = await _load_sections(session, project_id, user_id)

    abbreviations = list((await session.execute(
        select(Abbreviation).where(
            Abbreviation.project_id == project_id,
            Abbreviation.user_id == user_id,
        )
    )).scalars().all())

    datasets = list((await session.execute(
        select(Dataset).where(
            Dataset.project_id == project_id,
            Dataset.user_id == user_id,
        )
    )).scalars().all())
    dataset_ids = [d.id for d in datasets]

    dataset_variables: list[DatasetVariable] = []
    if dataset_ids:
        dataset_variables = list((await session.execute(
            select(DatasetVariable).where(
                DatasetVariable.user_id == user_id,
                DatasetVariable.dataset_id.in_(dataset_ids),
            )
        )).scalars().all())

    analyses = list((await session.execute(
        select(Analysis).where(
            Analysis.project_id == project_id,
            Analysis.user_id == user_id,
        )
    )).scalars().all())
    analysis_ids = [a.id for a in analyses]

    analysis_results: list[AnalysisResult] = []
    if analysis_ids:
        analysis_results = list((await session.execute(
            select(AnalysisResult).where(
                AnalysisResult.user_id == user_id,
                AnalysisResult.analysis_id.in_(analysis_ids),
            )
        )).scalars().all())

    review = (await session.execute(
        select(Review).where(
            Review.project_id == project_id,
            Review.user_id == user_id,
        )
    )).scalar_one_or_none()

    search_records: list[SearchRecord] = []
    screening_records: list[ScreeningRecord] = []
    rob_assessments: list[RobAssessment] = []
    extraction_records: list[ExtractionRecord] = []
    meta_analyses: list[MetaAnalysis] = []
    meta_inputs: list[MetaInput] = []
    if review is not None:
        search_records = list((await session.execute(
            select(SearchRecord).where(
                SearchRecord.review_id == review.id,
                SearchRecord.user_id == user_id,
            )
        )).scalars().all())
        screening_records = list((await session.execute(
            select(ScreeningRecord).where(
                ScreeningRecord.review_id == review.id,
                ScreeningRecord.user_id == user_id,
            )
        )).scalars().all())
        rob_assessments = list((await session.execute(
            select(RobAssessment).where(
                RobAssessment.review_id == review.id,
                RobAssessment.user_id == user_id,
            )
        )).scalars().all())
        extraction_records = list((await session.execute(
            select(ExtractionRecord).where(
                ExtractionRecord.review_id == review.id,
                ExtractionRecord.user_id == user_id,
            )
        )).scalars().all())
        meta_analyses = list((await session.execute(
            select(MetaAnalysis).where(
                MetaAnalysis.review_id == review.id,
                MetaAnalysis.user_id == user_id,
            )
        )).scalars().all())
        meta_ids = [m.id for m in meta_analyses]
        if meta_ids:
            meta_inputs = list((await session.execute(
                select(MetaInput).where(
                    MetaInput.user_id == user_id,
                    MetaInput.meta_id.in_(meta_ids),
                )
            )).scalars().all())

    figures = list((await session.execute(
        select(Figure).where(
            Figure.project_id == project_id,
            Figure.user_id == user_id,
        )
    )).scalars().all())

    consort_data = (await session.execute(
        select(ConsortData).where(
            ConsortData.project_id == project_id,
            ConsortData.user_id == user_id,
        )
    )).scalar_one_or_none()

    return BundleInputs(
        project=project,
        articles=articles,
        highlights=highlights,
        article_notes=article_notes,
        manuscript_sections=sections,
        abbreviations=abbreviations,
        datasets=datasets,
        dataset_variables=dataset_variables,
        analyses=analyses,
        analysis_results=analysis_results,
        review=review,
        search_records=search_records,
        screening_records=screening_records,
        rob_assessments=rob_assessments,
        extraction_records=extraction_records,
        figures=figures,
        consort_data=consort_data,
        meta_analyses=meta_analyses,
        meta_inputs=meta_inputs,
    )


@router.post("/projects/{project_id}/export/bundle")
async def export_bundle(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    inputs = await _collect_bundle_inputs(session, project=project, user_id=user_id)
    bundle = build_bundle(inputs)
    body = json.dumps(bundle, indent=2).encode("utf-8")

    slug = _slugify_filename(project.title)
    filename = f"{slug}-bundle-{_today()}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/projects/import/bundle",
    response_model=BundleImportResponse,
    status_code=status.HTTP_200_OK,
)
async def import_bundle_route(
    file: Annotated[UploadFile, File(...)],
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> BundleImportResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > _IMPORT_SIZE_CAP_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Bundle exceeds {_IMPORT_SIZE_CAP_BYTES // (1024 * 1024)} MiB cap",
        )

    first = next((b for b in data if b not in (0x20, 0x09, 0x0A, 0x0D)), None)
    if first != ord("{"):
        raise HTTPException(status_code=415, detail="Bundle must be a JSON object")

    try:
        bundle = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=415, detail=f"Invalid JSON: {exc.msg}") from None

    if not isinstance(bundle, dict):
        raise HTTPException(status_code=415, detail="Bundle must be a JSON object")

    pre_ids = {
        row.id for row in (
            await session.execute(
                select(Project).where(Project.user_id == user_id)
            )
        ).scalars().all()
    }

    try:
        counts = await import_bundle(
            bundle, target_user_id=user_id, session=session
        )
    except BundleImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    post_rows = (await session.execute(
        select(Project).where(Project.user_id == user_id)
    )).scalars().all()
    new_project = next((p for p in post_rows if p.id not in pre_ids), None)
    if new_project is None:
        raise HTTPException(status_code=500, detail="Import succeeded but project missing")

    await session.commit()
    return BundleImportResponse(project_id=new_project.id, counts=counts)


@router.get(
    "/projects/{project_id}/bibliography",
    response_model=BibliographyResponse,
)
async def get_bibliography(
    project_id: str,
    style: str | None = Query(default=None),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> BibliographyResponse:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    coerced_style = _coerce_style(style, project.citation_style)
    sections = await _load_sections(session, project_id, user_id)
    articles = await _load_articles(session, project_id, user_id)
    by_id = {a.id: a for a in articles}
    entries = build_bibliography(
        articles_by_id=by_id, sections=sections, style=coerced_style
    )
    first_section_map = _first_section_by_article(sections)

    out: list[BibliographyEntryRead] = []
    for e in entries:
        article = by_id.get(e.article_id)
        if article is None:
            continue
        if coerced_style in ("vancouver", "ieee"):
            formatted = bibliography_entry(article, number=e.number, style=coerced_style)
        else:
            formatted = format_entry(article, style=coerced_style)
        out.append(BibliographyEntryRead(
            number=e.number,
            article_id=e.article_id,
            formatted_entry=formatted,
            first_section=first_section_map.get(e.article_id, ""),
        ))

    return BibliographyResponse(style=coerced_style, entries=out)
