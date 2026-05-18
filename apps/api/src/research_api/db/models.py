from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
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
