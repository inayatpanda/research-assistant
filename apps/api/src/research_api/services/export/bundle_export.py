"""Project bundle export: pure transform from ORM rows to a JSON-serialisable dict.

The bundle is the wire format for full-project portability — used by both the
JSON export endpoint and (via `bundle_import`) the matching import endpoint.

Design rules:
  - Pure: no DB / FS / network. Callers pass already-scoped lists.
  - JSON-only output: datetimes serialised to ISO-8601, no Decimals.
  - All FK fields retained verbatim so the import can rewrite them via an old→
    new id map.
  - `user_id` IS present in the bundle (round-trip needs to survive json) but
    the import service is mandated to ignore it and stamp the importing user.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ...db.models import (
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
    GradeAssessment,
    Highlight,
    ManuscriptComment,
    ManuscriptSection,
    ManuscriptSnapshot,
    MetaAnalysis,
    MetaInput,
    Project,
    ProjectFrontmatter,
    ProsperoDraft,
    Review,
    ReviewerResponse,
    RobAssessment,
    ScreeningRecord,
    SearchRecord,
)

SCHEMA_VERSION = 1
EXPORTED_FROM = "Research Manuscript Assistant v0.0.1"


@dataclass
class BundleInputs:
    project: Project
    articles: list[Article] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    article_notes: list[ArticleNote] = field(default_factory=list)
    manuscript_sections: list[ManuscriptSection] = field(default_factory=list)
    abbreviations: list[Abbreviation] = field(default_factory=list)
    datasets: list[Dataset] = field(default_factory=list)
    dataset_variables: list[DatasetVariable] = field(default_factory=list)
    # Phase 13 (MP13) — Pure-function transformation stacks per dataset.
    dataset_transformations: list[DatasetTransformation] = field(default_factory=list)
    analyses: list[Analysis] = field(default_factory=list)
    analysis_results: list[AnalysisResult] = field(default_factory=list)
    review: Review | None = None
    search_records: list[SearchRecord] = field(default_factory=list)
    screening_records: list[ScreeningRecord] = field(default_factory=list)
    rob_assessments: list[RobAssessment] = field(default_factory=list)
    extraction_records: list[ExtractionRecord] = field(default_factory=list)
    # Phase 8.7 additions
    figures: list[Figure] = field(default_factory=list)
    consort_data: ConsortData | None = None
    # Phase 7.5 additions
    meta_analyses: list[MetaAnalysis] = field(default_factory=list)
    meta_inputs: list[MetaInput] = field(default_factory=list)
    # Phase 10 — ICMJE structured front-matter
    authors: list[Author] = field(default_factory=list)
    affiliations: list[Affiliation] = field(default_factory=list)
    author_affiliations: list[AuthorAffiliation] = field(default_factory=list)
    contributions: list[Contribution] = field(default_factory=list)
    project_frontmatter: ProjectFrontmatter | None = None
    # Phase 11 — manuscript snapshots + margin comments
    manuscript_snapshots: list[ManuscriptSnapshot] = field(default_factory=list)
    manuscript_comments: list[ManuscriptComment] = field(default_factory=list)
    # Phase 12 — cover letter + reviewer responses
    cover_letter: CoverLetter | None = None
    reviewer_responses: list[ReviewerResponse] = field(default_factory=list)
    # Phase 13.5 — plots + analysis plans + plan runs
    dataset_plots: list[DatasetPlot] = field(default_factory=list)
    analysis_plans: list[AnalysisPlan] = field(default_factory=list)
    analysis_plan_runs: list[AnalysisPlanRun] = field(default_factory=list)
    # Phase 14 (MP14) — GRADE assessments + PROSPERO drafts
    grade_assessments: list[GradeAssessment] = field(default_factory=list)
    prospero_draft: ProsperoDraft | None = None


def _serialise(value: Any) -> Any:
    if isinstance(value, datetime):
        # Always ISO-8601; preserve tz info if present, otherwise mark naive as UTC.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialise(v) for v in value]
    return value


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Map an ORM row to a JSON-friendly dict.

    We deliberately read columns from `__table__.columns` rather than
    `__dict__` so we never accidentally surface lazy-loaded relationships or
    internal `_sa_instance_state`.
    """
    out: dict[str, Any] = {}
    for col in row.__table__.columns:
        name = col.name
        out[name] = _serialise(getattr(row, name))
    return out


def build_bundle(inputs: BundleInputs) -> dict[str, Any]:
    """Compose a full JSON-serialisable project bundle.

    Returns a `dict` (not bytes); the route layer is responsible for
    `json.dumps(..., indent=2)`-style serialisation and Content-Disposition.
    """
    project_dict = _row_to_dict(inputs.project)
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_from": EXPORTED_FROM,
        "project": project_dict,
        "articles": [_row_to_dict(a) for a in inputs.articles],
        "highlights": [_row_to_dict(h) for h in inputs.highlights],
        "article_notes": [_row_to_dict(n) for n in inputs.article_notes],
        "manuscript_sections": [_row_to_dict(s) for s in inputs.manuscript_sections],
        "abbreviations": [_row_to_dict(a) for a in inputs.abbreviations],
        "datasets": [_row_to_dict(d) for d in inputs.datasets],
        "dataset_variables": [_row_to_dict(v) for v in inputs.dataset_variables],
        "dataset_transformations": [
            _row_to_dict(t) for t in inputs.dataset_transformations
        ],
        "analyses": [_row_to_dict(a) for a in inputs.analyses],
        "analysis_results": [_row_to_dict(r) for r in inputs.analysis_results],
        "review": _row_to_dict(inputs.review) if inputs.review is not None else None,
        "search_records": [_row_to_dict(r) for r in inputs.search_records],
        "screening_records": [_row_to_dict(r) for r in inputs.screening_records],
        "rob_assessments": [_row_to_dict(r) for r in inputs.rob_assessments],
        "extraction_records": [_row_to_dict(r) for r in inputs.extraction_records],
        "figures": [_row_to_dict(f) for f in inputs.figures],
        "consort_data": (
            _row_to_dict(inputs.consort_data) if inputs.consort_data is not None else None
        ),
        "meta_analyses": [_row_to_dict(m) for m in inputs.meta_analyses],
        "meta_inputs": [_row_to_dict(i) for i in inputs.meta_inputs],
        "authors": [_row_to_dict(a) for a in inputs.authors],
        "affiliations": [_row_to_dict(a) for a in inputs.affiliations],
        "author_affiliations": [
            _row_to_dict(a) for a in inputs.author_affiliations
        ],
        "contributions": [_row_to_dict(c) for c in inputs.contributions],
        "project_frontmatter": (
            _row_to_dict(inputs.project_frontmatter)
            if inputs.project_frontmatter is not None
            else None
        ),
        "manuscript_snapshots": [
            _row_to_dict(s) for s in inputs.manuscript_snapshots
        ],
        "manuscript_comments": [
            _row_to_dict(c) for c in inputs.manuscript_comments
        ],
        "cover_letter": (
            _row_to_dict(inputs.cover_letter)
            if inputs.cover_letter is not None
            else None
        ),
        "reviewer_responses": [
            _row_to_dict(r) for r in inputs.reviewer_responses
        ],
        "dataset_plots": [_row_to_dict(p) for p in inputs.dataset_plots],
        "analysis_plans": [_row_to_dict(p) for p in inputs.analysis_plans],
        "analysis_plan_runs": [
            _row_to_dict(r) for r in inputs.analysis_plan_runs
        ],
        "grade_assessments": [
            _row_to_dict(g) for g in inputs.grade_assessments
        ],
        "prospero_draft": (
            _row_to_dict(inputs.prospero_draft)
            if inputs.prospero_draft is not None
            else None
        ),
    }
