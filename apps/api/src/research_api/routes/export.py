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
    Affiliation,
    Analysis,
    AnalysisPlan,
    AnalysisPlanRun,
    AnalysisResult,
    Article,
    ArticleNote,
    Author,
    AuthorAffiliation,
    ConsortData,
    Contribution,
    CoverLetter,
    Dataset,
    DatasetPlot,
    DatasetTransformation,
    DatasetVariable,
    ExtractionRecord,
    Figure,
    Highlight,
    ManuscriptComment,
    ManuscriptSection,
    ManuscriptSnapshot,
    MetaAnalysis,
    MetaInput,
    Project,
    ProjectFrontmatter,
    Review,
    ReviewerResponse,
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
from ..services.export.docx_export import FrontMatterPayload, render_docx
from ..services.export.pdf_export import render_pdf
from ..services.export.stats_report import (
    ReportAnalysis,
    ReportDataset,
    ReportPlot,
    ReportProject,
    ReportTransformation,
    build_stats_report,
)
from ..services.export.submission_package import (
    CoverLetterPayload,
    FigurePackageItem,
    ReviewerResponsePayload,
    build_submission_zip,
)
from ..services.storage.base import StorageRef

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


async def _load_frontmatter_payload(
    session: AsyncSession, project_id: str, user_id: str
) -> FrontMatterPayload | None:
    """Phase 10 — load authors + affiliations + links + frontmatter for export.

    Returns None when the project has no authors and no frontmatter row, so
    legacy pre-Phase-10 exports keep their original layout untouched.
    """
    authors = list((await session.execute(
        select(Author).where(
            Author.project_id == project_id, Author.user_id == user_id
        ).order_by(Author.position.asc())
    )).scalars().all())
    affiliations = list((await session.execute(
        select(Affiliation).where(
            Affiliation.project_id == project_id, Affiliation.user_id == user_id
        ).order_by(Affiliation.position.asc())
    )).scalars().all())
    links: list[AuthorAffiliation] = []
    if authors:
        author_ids = [a.id for a in authors]
        links = list((await session.execute(
            select(AuthorAffiliation).where(
                AuthorAffiliation.user_id == user_id,
                AuthorAffiliation.author_id.in_(author_ids),
            ).order_by(AuthorAffiliation.position.asc())
        )).scalars().all())
    frontmatter = (await session.execute(
        select(ProjectFrontmatter).where(
            ProjectFrontmatter.project_id == project_id,
            ProjectFrontmatter.user_id == user_id,
        )
    )).scalar_one_or_none()

    if not authors and frontmatter is None:
        return None

    links_by_author: dict[str, list[str]] = {}
    for link in links:
        links_by_author.setdefault(link.author_id, []).append(link.affiliation_id)

    author_payload = [
        {
            "id": a.id,
            "full_name": a.full_name,
            "given_name": a.given_name,
            "family_name": a.family_name,
            "orcid": a.orcid,
            "email": a.email,
            "is_corresponding": a.is_corresponding,
            "position": a.position,
            "affiliation_ids": links_by_author.get(a.id, []),
        }
        for a in authors
    ]
    aff_payload = [
        {
            "id": a.id,
            "name": a.name,
            "address": a.address,
            "city": a.city,
            "country": a.country,
            "position": a.position,
        }
        for a in affiliations
    ]
    return FrontMatterPayload(
        authors=author_payload,
        affiliations=aff_payload,
        funding_statement=(frontmatter.funding_statement if frontmatter else None),
        funders=(frontmatter.funders or []) if frontmatter else [],
        ethics_irb=(frontmatter.ethics_irb if frontmatter else None),
        ethics_approval_number=(
            frontmatter.ethics_approval_number if frontmatter else None
        ),
        ethics_consent=(frontmatter.ethics_consent if frontmatter else None),
        conflicts_statement=(
            frontmatter.conflicts_statement if frontmatter else None
        ),
        structured_abstract_enabled=bool(
            frontmatter and frontmatter.structured_abstract_enabled
        ),
        structured_abstract=(
            frontmatter.structured_abstract if frontmatter else None
        ),
    )


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
    frontmatter = await _load_frontmatter_payload(session, project_id, user_id)
    data = render_docx(
        project=project,
        sections=consolidated,
        bibliography=entries,
        frontmatter=frontmatter,
    )

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
    frontmatter = await _load_frontmatter_payload(session, project_id, user_id)
    data = render_pdf(
        project=project,
        sections=consolidated,
        bibliography=entries,
        frontmatter=frontmatter,
    )

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
    dataset_transformations: list[DatasetTransformation] = []
    if dataset_ids:
        dataset_variables = list((await session.execute(
            select(DatasetVariable).where(
                DatasetVariable.user_id == user_id,
                DatasetVariable.dataset_id.in_(dataset_ids),
            )
        )).scalars().all())
        dataset_transformations = list((await session.execute(
            select(DatasetTransformation).where(
                DatasetTransformation.user_id == user_id,
                DatasetTransformation.dataset_id.in_(dataset_ids),
            ).order_by(DatasetTransformation.position.asc())
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

    # Phase 10 — ICMJE front-matter rows.
    fm_authors = list((await session.execute(
        select(Author).where(
            Author.project_id == project_id, Author.user_id == user_id
        ).order_by(Author.position.asc())
    )).scalars().all())
    fm_affiliations = list((await session.execute(
        select(Affiliation).where(
            Affiliation.project_id == project_id, Affiliation.user_id == user_id
        ).order_by(Affiliation.position.asc())
    )).scalars().all())
    fm_author_affiliations: list[AuthorAffiliation] = []
    fm_contributions: list[Contribution] = []
    if fm_authors:
        author_ids_p10 = [a.id for a in fm_authors]
        fm_author_affiliations = list((await session.execute(
            select(AuthorAffiliation).where(
                AuthorAffiliation.user_id == user_id,
                AuthorAffiliation.author_id.in_(author_ids_p10),
            )
        )).scalars().all())
        fm_contributions = list((await session.execute(
            select(Contribution).where(
                Contribution.user_id == user_id,
                Contribution.author_id.in_(author_ids_p10),
            )
        )).scalars().all())
    project_frontmatter = (await session.execute(
        select(ProjectFrontmatter).where(
            ProjectFrontmatter.project_id == project_id,
            ProjectFrontmatter.user_id == user_id,
        )
    )).scalar_one_or_none()

    # Phase 11 — snapshots + margin comments.
    manuscript_snapshots = list((await session.execute(
        select(ManuscriptSnapshot).where(
            ManuscriptSnapshot.project_id == project_id,
            ManuscriptSnapshot.user_id == user_id,
        ).order_by(ManuscriptSnapshot.created_at.asc())
    )).scalars().all())
    manuscript_comments = list((await session.execute(
        select(ManuscriptComment).where(
            ManuscriptComment.project_id == project_id,
            ManuscriptComment.user_id == user_id,
        ).order_by(ManuscriptComment.created_at.asc())
    )).scalars().all())

    # Phase 12 — cover letter + reviewer responses.
    cover_letter_row = (await session.execute(
        select(CoverLetter).where(
            CoverLetter.project_id == project_id,
            CoverLetter.user_id == user_id,
        )
    )).scalar_one_or_none()
    reviewer_response_rows = list((await session.execute(
        select(ReviewerResponse).where(
            ReviewerResponse.project_id == project_id,
            ReviewerResponse.user_id == user_id,
        ).order_by(ReviewerResponse.created_at.asc())
    )).scalars().all())

    # Phase 13.5 — dataset plots + analysis plans + plan runs
    dataset_plots: list[DatasetPlot] = []
    if dataset_ids:
        dataset_plots = list((await session.execute(
            select(DatasetPlot).where(
                DatasetPlot.user_id == user_id,
                DatasetPlot.dataset_id.in_(dataset_ids),
            )
        )).scalars().all())
    analysis_plans = list((await session.execute(
        select(AnalysisPlan).where(
            AnalysisPlan.project_id == project_id,
            AnalysisPlan.user_id == user_id,
        )
    )).scalars().all())
    plan_ids = [p.id for p in analysis_plans]
    analysis_plan_runs: list[AnalysisPlanRun] = []
    if plan_ids:
        analysis_plan_runs = list((await session.execute(
            select(AnalysisPlanRun).where(
                AnalysisPlanRun.user_id == user_id,
                AnalysisPlanRun.plan_id.in_(plan_ids),
            )
        )).scalars().all())

    return BundleInputs(
        project=project,
        articles=articles,
        highlights=highlights,
        article_notes=article_notes,
        manuscript_sections=sections,
        abbreviations=abbreviations,
        datasets=datasets,
        dataset_variables=dataset_variables,
        dataset_transformations=dataset_transformations,
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
        authors=fm_authors,
        affiliations=fm_affiliations,
        author_affiliations=fm_author_affiliations,
        contributions=fm_contributions,
        project_frontmatter=project_frontmatter,
        manuscript_snapshots=manuscript_snapshots,
        manuscript_comments=manuscript_comments,
        cover_letter=cover_letter_row,
        reviewer_responses=reviewer_response_rows,
        dataset_plots=dataset_plots,
        analysis_plans=analysis_plans,
        analysis_plan_runs=analysis_plan_runs,
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


_MIME_TO_EXT: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/svg+xml": "svg",
    "image/webp": "webp",
}


def _figure_ext(file_type: str | None) -> str:
    return _MIME_TO_EXT.get((file_type or "").lower(), "bin")


async def _load_figure_bytes(
    container: Container, figures: list[Figure]
) -> list[FigurePackageItem]:
    """Resolve each Figure row to a (figure_number, ext, bytes) item.

    Missing files (storage 404 / backend="missing") are skipped silently —
    the manuscript still renders without them. The submission package zip
    therefore matches the live figures gallery state.
    """
    items: list[FigurePackageItem] = []
    for fig in figures:
        ref_in = fig.file_ref or {}
        backend = ref_in.get("backend")
        key = ref_in.get("key")
        if not backend or not key or backend == "missing":
            continue
        try:
            data = await container.storage.read(
                StorageRef(backend=backend, key=key)
            )
        except FileNotFoundError:
            continue
        except Exception:
            log.exception("Failed to read figure bytes for fig=%s", fig.id)
            continue
        items.append(
            FigurePackageItem(
                figure_number=int(fig.figure_number or 1),
                ext=_figure_ext(fig.file_type),
                data=data,
            )
        )
    return items


def _sections_from_snapshot_blob(
    blob: dict | None,
) -> list[ManuscriptSection]:
    """Materialise lightweight section objects from a snapshot blob so the
    main render_docx pipeline can consume them without knowing about the
    snapshot at all.

    The blob's `manuscript_sections` was captured via
    `SqliteSnapshotRepository._row_to_jsonable` — we only need
    `section_name` + `content` here.
    """
    out: list[ManuscriptSection] = []
    for row in (blob or {}).get("manuscript_sections") or []:
        m = ManuscriptSection(
            id=row.get("id") or "",
            user_id=row.get("user_id") or "",
            project_id=row.get("project_id") or "",
            section_name=row.get("section_name") or "",
            content=row.get("content") or "",
            word_count=row.get("word_count") or 0,
        )
        out.append(m)
    return out


@router.post(
    "/projects/{project_id}/export/submission-package",
)
async def export_submission_package(
    project_id: str,
    snapshot_id: str | None = Query(default=None),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
    container: Container = Depends(get_container),
) -> StreamingResponse:
    """Phase 12 — Bundle manuscript + figures + tables + cover letter +
    reviewer responses into a single zip download.

    Query params:
        snapshot_id: optional. When set, the manuscript content is read
        from that snapshot's `full_blob` instead of the live tables. Cover
        letter + reviewer responses always come from the LIVE rows (those
        edits keep happening between submission rounds).
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    snapshot_label: str | None = None
    if snapshot_id:
        snap = (
            await session.execute(
                select(ManuscriptSnapshot).where(
                    ManuscriptSnapshot.id == snapshot_id,
                    ManuscriptSnapshot.user_id == user_id,
                    ManuscriptSnapshot.project_id == project_id,
                )
            )
        ).scalar_one_or_none()
        if snap is None:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        sections = _sections_from_snapshot_blob(snap.full_blob)
        snapshot_label = snap.label
    else:
        sections = await _load_sections(session, project_id, user_id)

    articles = await _load_articles(session, project_id, user_id)
    style = _coerce_style(None, project.citation_style)
    entries = await _build_bib_entries(sections, articles, style)
    frontmatter = await _load_frontmatter_payload(session, project_id, user_id)

    figures = list((await session.execute(
        select(Figure).where(
            Figure.project_id == project_id,
            Figure.user_id == user_id,
        ).order_by(Figure.figure_number.asc())
    )).scalars().all())
    figure_items = await _load_figure_bytes(container, figures)

    cl = (
        await session.execute(
            select(CoverLetter).where(
                CoverLetter.project_id == project_id,
                CoverLetter.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    cl_payload: CoverLetterPayload | None = None
    if cl is not None:
        from ..services.journal_templates.catalogue import JOURNALS

        journal = JOURNALS.get(cl.target_journal or "")
        cl_payload = CoverLetterPayload(
            body_html=cl.body_html or "",
            target_journal_label=(journal.label if journal else None),
        )

    rr_rows = list((await session.execute(
        select(ReviewerResponse).where(
            ReviewerResponse.project_id == project_id,
            ReviewerResponse.user_id == user_id,
        ).order_by(ReviewerResponse.created_at.asc())
    )).scalars().all())
    rr_payloads = [
        ReviewerResponsePayload(
            reviewer_label=r.reviewer_label,
            comments=list(r.comments or []),
        )
        for r in rr_rows
    ]

    filename, data = build_submission_zip(
        project=project,
        sections=sections,
        articles=articles,
        frontmatter=frontmatter,
        figures=figure_items,
        cover_letter=cl_payload,
        reviewer_responses=rr_payloads,
        bibliography=entries,
        style=style,
        snapshot_label=snapshot_label,
    )

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


_STATS_TEST_LABELS = {
    "independent_t": "Independent t-test",
    "paired_t": "Paired t-test",
    "mann_whitney": "Mann-Whitney U",
    "wilcoxon_signed": "Wilcoxon signed-rank",
    "chi_squared": "Chi-squared",
    "fisher_exact": "Fisher's exact",
    "one_way_anova": "One-way ANOVA",
    "kruskal_wallis": "Kruskal-Wallis",
    "rm_anova": "Repeated-measures ANOVA",
    "pearson": "Pearson correlation",
    "spearman": "Spearman correlation",
    "linear_regression": "Linear regression",
    "multiple_linear": "Multiple linear regression",
    "logistic": "Logistic regression",
    "kaplan_meier": "Kaplan-Meier survival",
    "cox_ph": "Cox proportional hazards",
    "icc": "Intraclass correlation",
    "cohen_kappa": "Cohen's kappa",
    "mixed_effects_lm": "Mixed-effects linear",
    "glm_poisson": "GLM Poisson",
    "glm_binomial": "GLM Binomial",
    "glm_gamma": "GLM Gamma",
    "gee": "Generalised estimating equations",
    "bootstrap_mean_diff": "Bootstrap mean difference",
    "permutation_test": "Permutation test",
    "tost_equivalence": "TOST equivalence",
    "tost_noninferiority": "TOST non-inferiority",
}


@router.post("/projects/{project_id}/datasets/{dataset_id}/report")
async def export_stats_report(
    project_id: str,
    dataset_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> StreamingResponse:
    """Phase 13.5 — Build the full statistical report PDF for a dataset."""
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    ds = (await session.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == user_id,
            Dataset.project_id == project_id,
        )
    )).scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    transformations = list((await session.execute(
        select(DatasetTransformation).where(
            DatasetTransformation.dataset_id == dataset_id,
            DatasetTransformation.user_id == user_id,
        ).order_by(DatasetTransformation.position.asc())
    )).scalars().all())

    analyses = list((await session.execute(
        select(Analysis).where(
            Analysis.dataset_id == dataset_id,
            Analysis.user_id == user_id,
        ).order_by(Analysis.created_at.asc())
    )).scalars().all())

    analysis_ids = [a.id for a in analyses]
    results: list[AnalysisResult] = []
    if analysis_ids:
        results = list((await session.execute(
            select(AnalysisResult).where(
                AnalysisResult.user_id == user_id,
                AnalysisResult.analysis_id.in_(analysis_ids),
            )
        )).scalars().all())
    results_by_aid = {r.analysis_id: r for r in results}

    plot_rows = list((await session.execute(
        select(DatasetPlot).where(
            DatasetPlot.dataset_id == dataset_id,
            DatasetPlot.user_id == user_id,
        ).order_by(DatasetPlot.created_at.asc())
    )).scalars().all())

    report_analyses: list[ReportAnalysis] = []
    for a in analyses:
        r = results_by_aid.get(a.id)
        summary = dict(r.summary) if r and r.summary else {}
        assumptions = dict(r.assumptions) if r and r.assumptions else {}
        chart_uri: str | None = None
        if r and r.chart and isinstance(r.chart, dict):
            chart_uri = r.chart.get("data_uri")
        report_analyses.append(ReportAnalysis(
            test_label=_STATS_TEST_LABELS.get(a.chosen_test, a.chosen_test),
            variables=dict(a.variables or {}),
            summary=summary,
            assumptions=assumptions,
            chart_data_uri=chart_uri,
            ai_interpretation=(r.ai_interpretation if r else None),
        ))

    report_plots = [
        ReportPlot(
            title=p.title,
            geom=(p.spec or {}).get("geom", "plot"),
            png_data_uri=p.png_data_uri,
        )
        for p in plot_rows
    ]
    report_transforms = [
        ReportTransformation(
            op_type=t.op_type,
            label=t.label,
            op_args=dict(t.op_args or {}),
        )
        for t in transformations
    ]
    data = build_stats_report(
        project=ReportProject(title=project.title, study_type=project.study_type),
        dataset=ReportDataset(
            id=ds.id,
            filename=ds.filename,
            n_rows=ds.n_rows,
            n_columns=ds.n_columns,
        ),
        analyses=report_analyses,
        plots=report_plots,
        transformations=report_transforms,
    )

    slug = _slugify_filename(project.title)
    filename = f"{slug}-stats-report-{_today()}.pdf"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
