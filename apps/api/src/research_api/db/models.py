from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


def new_id() -> str:
    return uuid4().hex


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    study_type: Mapped[str] = mapped_column(String(64), nullable=False)
    citation_style: Mapped[str] = mapped_column(String(32), default="vancouver", nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(32), default="gemini", nullable=False)
    target_journal: Mapped[str | None] = mapped_column(Text, nullable=True)
    prospero_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clinicaltrials_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Phase 8.7 — Journal template key from the server-side catalogue
    # (services/journal_templates/catalogue.py). Null = no template selected.
    template_journal: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Phase 16 (MP16) — Inline citation rendering mode for the TipTap
    # CitationNodeView. One of ``bracket_numeric`` | ``superscript_numeric``
    # | ``author_year_parens``. The ``server_default`` is set in addition to
    # the Python-side default so raw-SQL INSERTs (e.g. legacy test fixtures
    # that explicitly enumerate the columns to write) don't trip the
    # NOT-NULL constraint.
    inline_citation_mode: Mapped[str] = mapped_column(
        String(32),
        default="bracket_numeric",
        server_default="bracket_numeric",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = (
        Index("ix_highlights_article_page", "article_id", "page_number"),
        Index("ix_highlights_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_text: Mapped[str] = mapped_column(Text, nullable=False)
    colour: Mapped[str] = mapped_column(String(16), nullable=False)  # intro|method|results|discussion
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    bounding_coords: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArticleNote(Base):
    __tablename__ = "article_notes"
    __table_args__ = (
        Index("uq_article_notes_article_user", "article_id", "user_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_user_project", "user_id", "project_id"),
        Index("ix_articles_doi", "doi"),
        Index("ix_articles_pmid", "pmid"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    journal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issue: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(64), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)

    file_ref: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    study_design: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict_of_interest: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 8.6 — ingestion provenance + PubMed cross-reference
    pmid: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="upload", nullable=False)

    # Phase 16 (MP16) — Citation depth. Reference category drives style
    # rendering (journal article, book, thesis, preprint, registry record,
    # web resource, etc.). ``url`` is the authoritative URL for grey-lit
    # entries whose identifier is *not* a DOI.
    reference_type: Mapped[str] = mapped_column(
        String(32),
        default="journal_article",
        server_default="journal_article",
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ManuscriptSection(Base):
    __tablename__ = "manuscript_sections"
    __table_args__ = (
        Index(
            "uq_manuscript_section_project_user_section",
            "project_id",
            "user_id",
            "section_name",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # Phase 4: 'Introduction' | 'Methodology' | 'Results' | 'Discussion'
    # Phase 5 extends to 'Abstract' | 'Conclusion'.
    section_name: Mapped[str] = mapped_column(String(32), nullable=False)
    # Phase 4 stored plain text; Phase 5 stores HTML (TipTap-rendered). Same column type.
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Abbreviation(Base):
    __tablename__ = "abbreviations"
    __table_args__ = (
        Index(
            "uq_abbreviation_project_user_short",
            "project_id",
            "user_id",
            "short_form",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    short_form: Mapped[str] = mapped_column(String(32), nullable=False)
    long_form: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        Index("ix_datasets_user_project", "user_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_ref: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    n_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    n_columns: Mapped[int] = mapped_column(Integer, nullable=False)
    # Phase 13 — PSM: a matched-output dataset points back to its source.
    # Nullable; SET NULL on source delete to preserve the matched row.
    derived_from_dataset_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Phase 13 — PSM: covariate-balance JSON (smd_before / smd_after / params).
    dataset_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Phase 13 (MP13) — Cross-dataset ops: list of source dataset ids.
    derived_from_dataset_ids: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DatasetTransformation(Base):
    """Phase 13 (MP13) — Ordered stack of pure-function ops applied to a
    dataset before any analysis runs. The original CSV is untouched.
    """

    __tablename__ = "dataset_transformations"
    __table_args__ = (
        Index(
            "ix_dataset_transformations_dataset_position",
            "dataset_id",
            "position",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    op_type: Mapped[str] = mapped_column(String(32), nullable=False)
    op_args: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DatasetVariable(Base):
    __tablename__ = "dataset_variables"
    __table_args__ = (
        Index("uq_dataset_variable_dataset_name", "dataset_id", "name", unique=True),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    inferred_type: Mapped[str] = mapped_column(String(32), nullable=False)
    user_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    n_missing: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_values: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    # Phase 17 (MP17) — Optional binding to the curated instrument catalogue.
    # Pure metadata — never affects how analyses run; used only by reports + UI.
    instrument_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # DEMO-FIX-C (mig 0022) — Free-text display label used by charts,
    # AI prose and exports. Defaults to the canonical ``name`` so legacy
    # datasets render identically until edited.
    display_label: Mapped[str | None] = mapped_column(Text, nullable=True)


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("ix_analyses_user_project", "user_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    chosen_test: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    # Phase 17 (MP17) — Optional FK to an analysis-population for sub-cohort
    # restriction (ITT/PP/safety/etc). NULL = whole dataset.
    population_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("analysis_populations.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Phase 17 (MP17) — Pre-registration lock fields.
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    integrity_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        Index("uq_analysis_results_analysis", "analysis_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    analysis_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    chart: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        Index("uq_reviews_project_user", "project_id", "user_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    pico_population: Mapped[str | None] = mapped_column(Text, nullable=True)
    pico_intervention: Mapped[str | None] = mapped_column(Text, nullable=True)
    pico_comparator: Mapped[str | None] = mapped_column(Text, nullable=True)
    pico_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_inclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_exclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Phase 19 (MP19) — Mixed-design SR: per-study RoB tool selection.
    tool_per_study: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SearchRecord(Base):
    __tablename__ = "search_records"
    __table_args__ = (
        Index("ix_search_records_review", "review_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    database_name: Mapped[str] = mapped_column(String(64), nullable=False)
    query_string: Mapped[str] = mapped_column(Text, nullable=False)
    date_searched: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    n_results: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ScreeningRecord(Base):
    __tablename__ = "screening_records"
    __table_args__ = (
        Index(
            "uq_screening_review_article_stage",
            "review_id", "article_id", "stage",
            unique=True,
        ),
        Index("ix_screening_review_stage", "review_id", "stage"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    exclusion_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_suggestion: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RobAssessment(Base):
    __tablename__ = "rob_assessments"
    __table_args__ = (
        Index(
            "uq_rob_review_article_tool",
            "review_id", "article_id", "tool",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    tool: Mapped[str] = mapped_column(String(16), nullable=False)
    domain_answers: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    overall_auto: Mapped[str] = mapped_column(String(16), nullable=False)
    overall_override: Mapped[str | None] = mapped_column(String(16), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ExtractionRecord(Base):
    __tablename__ = "extraction_records"
    __table_args__ = (
        Index(
            "uq_extraction_review_article",
            "review_id", "article_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MetaAnalysis(Base):
    __tablename__ = "meta_analyses"
    __table_args__ = (
        Index("ix_meta_analyses_review", "review_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    effect_metric: Mapped[str] = mapped_column(String(8), nullable=False)
    model: Mapped[str] = mapped_column(String(8), nullable=False)
    subgroup_variable: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pooled_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    pooled_se: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    z_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    q_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    q_df: Mapped[int | None] = mapped_column(Integer, nullable=True)
    q_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    i2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tau2: Mapped[float | None] = mapped_column(Float, nullable=True)
    subgroup_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MetaInput(Base):
    __tablename__ = "meta_inputs"
    __table_args__ = (
        Index(
            "uq_meta_inputs_meta_article",
            "meta_id", "article_id",
            unique=True,
        ),
        Index("ix_meta_inputs_meta", "meta_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    meta_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("meta_analyses.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    study_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subgroup: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Continuous (MD / SMD)
    mean_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    sd_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mean_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    sd_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_b: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Binary (OR / RR)
    events_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_a_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    events_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_b_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Time-to-event (HR)
    log_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    se_log_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr_ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr_ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Correlation (r)
    r: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_r: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Figure(Base):
    """Phase 8.7 — researcher-uploaded figure (PNG/JPEG/SVG).

    figure_number is 1-based ordinal within the (project_id, user_id) scope;
    repository maintains contiguity on reorder/delete via a two-step UPDATE
    that first offsets all rows by +1000 to dodge the UNIQUE constraint.
    """

    __tablename__ = "figures"
    __table_args__ = (
        Index("ix_figures_user_id", "user_id"),
        Index("ix_figures_project", "project_id"),
        Index(
            "uq_figures_project_user_number",
            "project_id", "user_id", "figure_number",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    file_ref: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    figure_number: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    alt_text: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ConsortData(Base):
    """Phase 8.7 — CONSORT 2010 flow counters; one row per (project, user)."""

    __tablename__ = "consort_data"
    __table_args__ = (
        Index("ix_consort_user_id", "user_id"),
        Index(
            "uq_consort_project_user",
            "project_id", "user_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    enrollment_assessed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrollment_excluded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrollment_excluded_reasons: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True)
    randomised: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allocated_intervention: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allocated_control: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervention_received: Mapped[int | None] = mapped_column(Integer, nullable=True)
    control_received: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervention_lost_followup: Mapped[int | None] = mapped_column(Integer, nullable=True)
    control_lost_followup: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervention_discontinued: Mapped[int | None] = mapped_column(Integer, nullable=True)
    control_discontinued: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervention_analysed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    control_analysed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Author(Base):
    """Phase 10 — ICMJE structured author row.

    `position` is 1-based sort order within the (project_id, user_id) scope.
    `is_corresponding` is enforced as at-most-one-per-project by the repository
    via a clearing UPDATE before any insert/update sets it true.
    """

    __tablename__ = "authors"
    __table_args__ = (
        Index("ix_authors_project_user", "project_id", "user_id"),
        Index("ix_authors_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    given_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    family_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    orcid: Mapped[str | None] = mapped_column(String(19), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    is_corresponding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Affiliation(Base):
    """Phase 10 — institutional affiliation row, scoped per (project, user)."""

    __tablename__ = "affiliations"
    __table_args__ = (
        Index("ix_affiliations_project_user", "project_id", "user_id"),
        Index("ix_affiliations_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuthorAffiliation(Base):
    """Phase 10 — many-to-many link between Author and Affiliation."""

    __tablename__ = "author_affiliations"
    __table_args__ = (
        Index(
            "uq_author_affiliation_pair",
            "author_id", "affiliation_id",
            unique=True,
        ),
        Index("ix_author_affiliations_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("authors.id", ondelete="CASCADE"), nullable=False
    )
    affiliation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("affiliations.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Contribution(Base):
    """Phase 10 — CRediT contribution role row, one per (author, role).

    The 14 CRediT roles are validated at the Pydantic boundary; the DB column
    stays a plain string so future role additions don't require a migration.
    """

    __tablename__ = "contributions"
    __table_args__ = (
        Index(
            "uq_contribution_author_role",
            "author_id", "role",
            unique=True,
        ),
        Index("ix_contributions_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("authors.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)


class ProjectFrontmatter(Base):
    """Phase 10 — per-project ICMJE front-matter row (1:1 with project)."""

    __tablename__ = "project_frontmatter"
    __table_args__ = (
        Index(
            "uq_project_frontmatter_project_user",
            "project_id", "user_id",
            unique=True,
        ),
        Index("ix_project_frontmatter_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    funding_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    funders: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    ethics_irb: Mapped[str | None] = mapped_column(Text, nullable=True)
    ethics_approval_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    ethics_consent: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflicts_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_abstract_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    structured_abstract: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ManuscriptSnapshot(Base):
    """Phase 11 — immutable point-in-time copy of the project's manuscript.

    `full_blob` carries a JSON snapshot of every section's HTML plus the
    Phase-10 ICMJE rows (authors / affiliations / contributions /
    project_frontmatter), figures, abbreviations, meta_analyses, and
    extraction_records. Snapshots are append-only; the only mutation is
    DELETE.
    """

    __tablename__ = "manuscript_snapshots"
    __table_args__ = (
        Index(
            "uq_manuscript_snapshots_project_user_label",
            "project_id", "user_id", "label",
            unique=True,
        ),
        Index(
            "ix_manuscript_snapshots_project_user",
            "project_id", "user_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_blob: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CoverLetter(Base):
    """Phase 12 — single cover letter per (project, user).

    `target_journal` is a key from the JournalTemplate catalogue (e.g.
    "jbjs"). `novelty_points` is a JSON list of short bullets (2-5 typical).
    `body_html` is the TipTap-rendered cover-letter body — the user always
    edits, but the AI populates the first draft via
    `POST /cover-letter/draft`.
    """

    __tablename__ = "cover_letters"
    __table_args__ = (
        Index(
            "uq_cover_letters_project_user",
            "project_id", "user_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    target_journal: Mapped[str | None] = mapped_column(String(64), nullable=True)
    novelty_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    body_html: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ReviewerResponse(Base):
    """Phase 12 — one row per reviewer (typically "Reviewer 1" / "Reviewer 2").

    `comments` is a JSON list of dicts:
        [{"comment_text": "...", "response_html": "..."}, ...]
    The AI's segmenter splits the user's free-text dump on blank-line +
    numeric-prefix heuristic and drafts initial responses; the user then
    edits each row inline.
    """

    __tablename__ = "reviewer_responses"
    __table_args__ = (
        Index(
            "ix_reviewer_responses_project_user",
            "project_id", "user_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_label: Mapped[str] = mapped_column(String(64), nullable=False)
    comments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DatasetPlot(Base):
    """Phase 13.5 (MP13.5) — saved plot for a dataset.

    The grammar-of-graphics ``spec`` JSON (``{geom, x, y?, color?, facet?,
    args?}``) is replayed on demand by the plot renderer. ``png_data_uri``
    caches the most recent render so the UI can list plots without paying
    the seaborn cost on every fetch.
    """

    __tablename__ = "dataset_plots"
    __table_args__ = (
        Index("ix_dataset_plots_dataset_user", "dataset_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    png_data_uri: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Python-side default with microsecond precision so two plots inserted
    # in the same wall-clock second still sort deterministically by ``created_at``.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnalysisPlan(Base):
    """Phase 13.5 (MP13.5) — named ordered list of steps, scoped per (project, user).

    Each step is a JSON dict ``{type: "transform"|"test"|"plot", args: {...}}``.
    Plans are re-usable templates; the source of truth for any one execution
    lives in ``analysis_plan_runs``.
    """

    __tablename__ = "analysis_plans"
    __table_args__ = (
        Index("ix_analysis_plans_project_user", "project_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # Phase 17 (MP17) — Pre-registration lock fields.
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    integrity_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnalysisPlanRun(Base):
    """Phase 13.5 (MP13.5) — append-only run record for a plan.

    ``result_blob`` holds the per-step output list; each entry is shaped
    ``{step_index, type, status: "ok"|"failed", output: {...}, error?: str}``.
    A single failed step does NOT abort the run — the run continues, but
    the roll-up ``status`` becomes "partial". An exception escaping the
    runner itself stamps the run "failed" with the ``error`` field set.
    """

    __tablename__ = "analysis_plan_runs"
    __table_args__ = (
        Index("ix_analysis_plan_runs_plan", "plan_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("analysis_plans.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[str] = mapped_column(String(32), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    result_blob: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class GradeAssessment(Base):
    """Phase 14 (MP14) — GRADE certainty-of-evidence assessment per outcome.

    One row per (review, outcome_label). The five downgrade domains and three
    upgrade domains are persisted as plain strings (validated at the Pydantic
    boundary). ``certainty`` is derived by ``services.review.grade`` on every
    write, but persisted so the SoF builder can sort/filter without re-running
    the algorithm. ``meta_id`` is optional — narrative-synthesis outcomes
    don't have a pooled estimate.
    """

    __tablename__ = "grade_assessments"
    __table_args__ = (
        Index(
            "uq_grade_assessments_review_outcome",
            "review_id", "outcome_label",
            unique=True,
        ),
        Index(
            "ix_grade_assessments_review_user",
            "review_id", "user_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    meta_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("meta_analyses.id", ondelete="SET NULL"),
        nullable=True,
    )
    outcome_label: Mapped[str] = mapped_column(String(255), nullable=False)
    starting_certainty: Mapped[str] = mapped_column(
        String(16), nullable=False, default="high"
    )
    domain_risk_of_bias: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_serious"
    )
    domain_inconsistency: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_serious"
    )
    domain_indirectness: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_serious"
    )
    domain_imprecision: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_serious"
    )
    domain_publication_bias: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_serious"
    )
    upgrade_large_effect: Mapped[str] = mapped_column(
        String(16), nullable=False, default="none"
    )
    upgrade_dose_response: Mapped[str] = mapped_column(
        String(16), nullable=False, default="none"
    )
    upgrade_confounders_against: Mapped[str] = mapped_column(
        String(16), nullable=False, default="none"
    )
    certainty: Mapped[str] = mapped_column(
        String(16), nullable=False, default="high"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ProsperoDraft(Base):
    """Phase 14 (MP14) — PROSPERO registration draft.

    The 22 PROSPERO fields are kept as a flat JSON dict so we can add/remove
    fields without a migration. The service layer (``services.review.prospero``)
    owns the field catalogue + default pre-fill logic.
    """

    __tablename__ = "prospero_drafts"
    __table_args__ = (
        Index(
            "uq_prospero_drafts_review_user",
            "review_id", "user_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LivingReviewJob(Base):
    """Phase 15 (MP15) — auto-rerun job for a saved PubMed query.

    One job per ``review_id``. The scheduler claims a lease via a conditional
    UPDATE before running so multiple processes can share the same DB without
    double-firing. ``last_hit_count`` is the number of *new* PMIDs from the
    most recent run (not the cumulative total).
    """

    __tablename__ = "living_review_jobs"
    __table_args__ = (
        Index(
            "uq_living_review_jobs_review",
            "review_id",
            unique=True,
        ),
        Index(
            "ix_living_review_jobs_user_enabled",
            "user_id", "enabled",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    pubmed_query: Mapped[str] = mapped_column(Text, nullable=False)
    schedule: Mapped[str] = mapped_column(String(16), nullable=False, default="weekly")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_hit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_holder: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LivingReviewHit(Base):
    """Phase 15 (MP15) — a single new PMID surfaced by a living-review run.

    Decision flow: every fresh PMID lands as ``new``; the user accepts (→
    imported as an Article) or dismisses it. Hits are transient — they are
    NOT carried in the project bundle so an import starts the rerun history
    fresh.
    """

    __tablename__ = "living_review_hits"
    __table_args__ = (
        Index(
            "ix_living_review_hits_job_decision",
            "job_id", "decision",
        ),
        Index(
            "uq_living_review_hits_job_pmid",
            "job_id", "pmid",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("living_review_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    pmid: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    seen_in_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ManuscriptComment(Base):
    """Phase 11 — margin comment anchored to a manuscript section.

    `anchor_start`/`anchor_end` are ProseMirror integer positions. The
    frontend defends against stale anchors when text drifts; the backend
    never validates the positions against the live content.

    `section_name` is one of Abstract / Introduction / Methodology /
    Results / Discussion / Conclusion / FrontMatter.
    """

    __tablename__ = "manuscript_comments"
    __table_args__ = (
        Index(
            "ix_manuscript_comments_section",
            "project_id", "user_id", "section_name", "resolved",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    section_name: Mapped[str] = mapped_column(String(32), nullable=False)
    anchor_start: Mapped[int] = mapped_column(Integer, nullable=False)
    anchor_end: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MeshTerm(Base):
    """Phase 19 (MP19) — Cached NCBI MeSH descriptor.

    Each project keeps its own cache; the descriptor_ui (e.g. ``D013313``)
    is unique within a project. Source distinguishes between user-typed
    custom terms and NCBI lookups so the UI can flag deprecated cache rows
    for refresh.
    """

    __tablename__ = "mesh_terms"
    __table_args__ = (
        Index(
            "uq_mesh_terms_project_ui",
            "project_id", "descriptor_ui",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    descriptor_ui: Mapped[str] = mapped_column(String(32), nullable=False)
    descriptor_name: Mapped[str] = mapped_column(String(500), nullable=False)
    scope_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tree_numbers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    entry_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str] = mapped_column(
        String(16), default="ncbi_lookup", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SearchStrategy(Base):
    """Phase 19 (MP19) — Per-review query builder row.

    ``database`` is one of the canonical literal set (validated at the
    Pydantic boundary). ``mesh_term_ids`` is a list of ``mesh_terms.id``
    that the user pinned into this query. ``translated_from_id`` is a
    self-FK that tracks cross-DB translation lineage (e.g. an Embase
    query auto-derived from a PubMed source). ``warnings`` captures
    untranslatable fragments from the cross-DB translator so the UI can
    surface them before the user runs the query.
    """

    __tablename__ = "search_strategies"
    __table_args__ = (
        Index("ix_search_strategies_review", "review_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    database: Mapped[str] = mapped_column(String(32), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mesh_term_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    translated_from_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("search_strategies.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class NarrativeSynthesisEntry(Base):
    """Phase 19 (MP19) — Per-outcome qualitative summary row.

    ``study_citations`` is a JSON list of article_ids cited in this row.
    ``narrative_html`` carries trusted HTML edited by the user (the same
    sanitisation rules as manuscript sections — DOMPurify on the FE).
    """

    __tablename__ = "narrative_synthesis_entries"
    __table_args__ = (
        Index("ix_narrative_synthesis_review", "review_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    outcome_label: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument: Mapped[str] = mapped_column(String(255), nullable=False)
    range_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[str] = mapped_column(
        String(20), default="neutral", nullable=False
    )
    narrative_html: Mapped[str] = mapped_column(Text, default="", nullable=False)
    study_citations: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OutcomeInstrument(Base):
    """Phase 19 (MP19) — Studies x instruments many-to-many comparison row.

    ``study_values`` is a list of
    ``{article_id, group_label, value, sd_or_ci, n}`` entries so a single
    instrument row can carry multiple per-study cells without spawning a
    second-level table.
    """

    __tablename__ = "outcome_instruments"
    __table_args__ = (
        Index("ix_outcome_instruments_review", "review_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    outcome_label: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score_range_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_range_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    mid: Mapped[float | None] = mapped_column(Float, nullable=True)
    study_values: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalysisPopulation(Base):
    """Phase 17 (MP17) — A named sub-population definition for a dataset.

    ``definition`` is a JSON dict carrying:
      - ``filter``: an optional pandas ``query()``-style expression (e.g.
        ``"approach == 'anterior'"``); empty / missing means "all rows".
      - ``label``: a free-text label like ``"ITT"`` / ``"PP"`` / ``"safety"``.

    ``study_assignment_field`` names the column that holds the randomised
    allocation; ``treatment_received_field`` names the column that holds the
    actual treatment received (NULL when not relevant — eg single-arm).
    """

    __tablename__ = "analysis_populations"
    __table_args__ = (
        Index("ix_analysis_populations_dataset", "dataset_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    study_assignment_field: Mapped[str] = mapped_column(String(255), nullable=False)
    treatment_received_field: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ImputationRun(Base):
    """Phase 17 (MP17) — One MICE / KNN / mean / median / LOCF run record.

    ``pooled_summary`` carries the Rubin-pooled per-column summary produced
    by ``services.stats.imputation.summarise_pooled``.
    """

    __tablename__ = "imputation_runs"
    __table_args__ = (
        Index("ix_imputation_runs_dataset", "dataset_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    n_imputations: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    target_cols: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    pooled_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EconomicAnalysis(Base):
    """Phase 18 (MP18) — Health economics configuration for one CEA.

    One row per cost-effectiveness analysis on a project. Holds the
    perspective, time horizon, currency, discount rates, WTP thresholds,
    utility value-set choice, bootstrap n + seed, treatment column,
    comparator/intervention labels, and the cost-column bindings (which
    columns play which economic role — unit_cost / quantity / cost_total /
    utility_score / qaly_weight / time_to_event).

    The optional ``ai_interpretation`` text mirrors AnalysisResult — it is
    populated by the /interpret endpoint and pushed to the manuscript.
    """

    __tablename__ = "economic_analyses"
    __table_args__ = (
        Index("ix_economic_analyses_project_user", "project_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="GBP")
    time_horizon_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=12
    )
    perspective: Mapped[str] = mapped_column(
        String(32), nullable=False, default="healthcare_system"
    )
    discount_rate_costs: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.035
    )
    discount_rate_qalys: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.035
    )
    wtp_thresholds: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    utility_value_set: Mapped[str] = mapped_column(
        String(32), nullable=False, default="EQ5D_5L_UK"
    )
    bootstrap_n: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    treatment_col: Mapped[str] = mapped_column(String(255), nullable=False)
    comparator_label: Mapped[str] = mapped_column(String(255), nullable=False)
    intervention_label: Mapped[str] = mapped_column(String(255), nullable=False)
    cost_columns: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    ai_interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EconomicResult(Base):
    """Phase 18 (MP18) — One result row per ``EconomicAnalysis``.

    UNIQUE constraint on ``economic_analysis_id`` means re-running an
    analysis updates this row in-place.
    """

    __tablename__ = "economic_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    economic_analysis_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("economic_analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    mean_cost_diff: Mapped[float] = mapped_column(Float, nullable=False)
    mean_qaly_diff: Mapped[float] = mapped_column(Float, nullable=False)
    icer: Mapped[float | None] = mapped_column(Float, nullable=True)
    dominance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    nmb_at_thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    ceac_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    plane_bootstrap: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    sensitivity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    plane_png_uri: Mapped[str] = mapped_column(Text, nullable=False)
    ceac_png_uri: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChecklistRun(Base):
    """Phase 20 (MP20) — One filled-in reporting checklist for a project.

    The catalogue (CONSORT 2010, PRISMA 2020, CHEERS 2022, STROBE cohort/
    case-control/cross-sectional, TRIPOD-AI, SPIRIT 2013, SQUIRE 2.0,
    CARE, AGREE II, SAMPL, PRISMA-S, PRISMA-ScR) is static — kept in
    ``services/checklists/catalogues/*.json``. This table stores the
    user-edited *answers* keyed by ``(project_id, user_id,
    checklist_key, title)``.

    A project can hold multiple runs of the same checklist for different
    submission versions — the ``title`` discriminator (e.g. ``"v1
    submission to JBJS"``) keeps them separate.
    """

    __tablename__ = "checklist_runs"
    __table_args__ = (
        Index("ix_checklist_runs_project_user", "project_id", "user_id"),
        Index(
            "uq_checklist_runs_project_user_key_title",
            "project_id",
            "user_id",
            "checklist_key",
            "title",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    checklist_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    overall_compliance_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PeerReview(Base):
    """Phase 4.6 — One AI peer-review critique for a project.

    Two source modes share the table:

    * ``source_type == 'manuscript'`` — reviews the user's own manuscript.
      ``manuscript_snapshot`` stores a frozen copy of the sections at
      review time so the critique remains meaningful even after the
      manuscript evolves. ``source_file_ref`` is NULL.
    * ``source_type == 'uploaded_pdf' | 'uploaded_docx'`` — reviews an
      externally uploaded document. ``source_file_ref`` holds
      ``{"backend", "key", "filename", "size"}``. ``manuscript_snapshot``
      is NULL.

    ``critique`` is the structured JSON the AI provider returns; see
    ``services/ai/prompts/peer_review.py`` for the schema.
    ``recommendation`` is one of reject | major_revision |
    minor_revision | accept.
    """

    __tablename__ = "peer_reviews"
    __table_args__ = (
        Index(
            "ix_peer_reviews_project_user_created",
            "project_id",
            "user_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
            name="fk_peer_reviews_project_id",
        ),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_file_ref: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    source_title: Mapped[str] = mapped_column(String(1000), nullable=False)
    manuscript_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    critique: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── Phase S1: Multi-user auth ────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_token_hash", "token_hash", unique=True),
        Index("ix_sessions_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_sessions_user_id"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        Index("ix_invitations_token_hash", "token_hash", unique=True),
        Index("ix_invitations_project_email", "project_id", "email"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
            name="fk_invitations_project_id",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    invited_by: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_invitations_invited_by",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_by: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_invitations_accepted_by",
        ),
        nullable=True,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index(
            "ix_audit_events_user_action_created",
            "user_id",
            "action",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── Phase S1: Project membership / RBAC (migration 0028) ────────────────


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        Index(
            "uq_project_members_project_user",
            "project_id",
            "user_id",
            unique=True,
        ),
        Index("ix_project_members_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
            name="fk_project_members_project_id",
        ),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_project_members_user_id",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    invited_by: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_project_members_invited_by",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
