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
