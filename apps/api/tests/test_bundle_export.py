"""Bundle export — pure transform over ORM rows to a JSON-serialisable dict.

The bundle is the wire format for export/import. It must:
  - omit SQLAlchemy internals,
  - serialise datetimes to ISO-8601,
  - carry every dependent row group,
  - never trust the caller's user_id (the export route is responsible for
    scoping the inputs).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from research_api.db.models import (
    Abbreviation,
    Analysis,
    AnalysisResult,
    Article,
    ArticleNote,
    Dataset,
    DatasetVariable,
    ExtractionRecord,
    Highlight,
    ManuscriptSection,
    Project,
    Review,
    RobAssessment,
    ScreeningRecord,
    SearchRecord,
)
from research_api.services.export.bundle_export import (
    SCHEMA_VERSION,
    BundleInputs,
    build_bundle,
)


def _mk_project() -> Project:
    p = Project(
        id="proj1",
        user_id="user-a",
        title="My Project",
        study_type="Outcome Study",
        citation_style="vancouver",
        ai_provider="gemini",
        target_journal="JAMA",
        prospero_number=None,
        clinicaltrials_number=None,
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    return p


def _mk_article(aid: str = "art1") -> Article:
    a = Article(
        id=aid,
        user_id="user-a",
        project_id="proj1",
        title="A study",
        authors=["Doe J", "Smith K"],
        journal="JAMA",
        year=2024,
        doi="10.1/x",
    )
    a.created_at = datetime(2025, 1, 3, tzinfo=timezone.utc)
    return a


def test_build_bundle_minimal_project_only():
    p = _mk_project()
    inputs = BundleInputs(project=p)
    out = build_bundle(inputs)
    assert out["schema_version"] == SCHEMA_VERSION
    assert "exported_at" in out
    assert "exported_from" in out
    assert out["project"]["id"] == "proj1"
    assert out["project"]["title"] == "My Project"
    assert out["articles"] == []
    assert out["highlights"] == []
    assert out["manuscript_sections"] == []
    assert out["review"] is None


def test_build_bundle_is_json_serialisable():
    p = _mk_project()
    a = _mk_article()
    inputs = BundleInputs(project=p, articles=[a])
    out = build_bundle(inputs)
    # Round-trip via json — no datetimes, no Decimals, no bytes lurking.
    raw = json.dumps(out)
    parsed = json.loads(raw)
    assert parsed["articles"][0]["id"] == "art1"


def test_build_bundle_datetimes_iso8601():
    p = _mk_project()
    out = build_bundle(BundleInputs(project=p))
    # ISO-8601 strings, not datetime objects.
    assert isinstance(out["project"]["created_at"], str)
    # ISO-8601 ends with Z or +HH:MM.
    assert "T" in out["project"]["created_at"]


def test_build_bundle_omits_sqlalchemy_internals():
    p = _mk_project()
    out = build_bundle(BundleInputs(project=p))
    assert "_sa_instance_state" not in out["project"]
    assert "registry" not in out["project"]


def test_build_bundle_includes_all_dependent_groups():
    p = _mk_project()
    a = _mk_article()
    h = Highlight(
        id="h1", user_id="user-a", article_id="art1",
        page_number=1, selected_text="hello",
        colour="intro", section="Introduction",
        bounding_coords={"x": 0, "y": 0, "w": 100, "h": 20},
    )
    h.created_at = datetime(2025, 1, 4, tzinfo=timezone.utc)
    note = ArticleNote(id="n1", user_id="user-a", article_id="art1", content="note")
    note.updated_at = datetime(2025, 1, 5, tzinfo=timezone.utc)
    sect = ManuscriptSection(
        id="s1", user_id="user-a", project_id="proj1",
        section_name="Introduction", content="<p>hi</p>", word_count=1,
    )
    sect.updated_at = datetime(2025, 1, 6, tzinfo=timezone.utc)
    abbr = Abbreviation(
        id="ab1", user_id="user-a", project_id="proj1",
        short_form="RCT", long_form="randomised controlled trial",
    )
    abbr.created_at = datetime(2025, 1, 7, tzinfo=timezone.utc)
    ds = Dataset(
        id="ds1", user_id="user-a", project_id="proj1",
        filename="d.csv", file_ref={"backend": "local", "key": "k"},
        file_type="text/csv", n_rows=10, n_columns=3,
    )
    ds.created_at = datetime(2025, 1, 8, tzinfo=timezone.utc)
    var = DatasetVariable(
        id="dv1", user_id="user-a", dataset_id="ds1",
        name="age", position=0, inferred_type="numeric",
        user_type=None, n_missing=0, sample_values=[1, 2, 3],
    )
    an = Analysis(
        id="an1", user_id="user-a", project_id="proj1", dataset_id="ds1",
        question_type="compare_means", chosen_test="t_test",
        recommendation_rationale="ok", variables={"a": "age"},
    )
    an.created_at = datetime(2025, 1, 9, tzinfo=timezone.utc)
    ar = AnalysisResult(
        id="ar1", user_id="user-a", analysis_id="an1",
        summary={"statistic": 1.0, "p_value": 0.05},
        assumptions={},
    )
    ar.created_at = datetime(2025, 1, 10, tzinfo=timezone.utc)
    rv = Review(id="rv1", user_id="user-a", project_id="proj1")
    rv.created_at = datetime(2025, 1, 11, tzinfo=timezone.utc)
    rv.updated_at = datetime(2025, 1, 11, tzinfo=timezone.utc)
    sr = SearchRecord(
        id="sr1", user_id="user-a", review_id="rv1",
        database_name="pubmed", query_string="cancer",
        date_searched=datetime(2025, 1, 12), n_results=42,
    )
    sr.created_at = datetime(2025, 1, 12, tzinfo=timezone.utc)
    sc = ScreeningRecord(
        id="sc1", user_id="user-a", review_id="rv1", article_id="art1",
        stage="title_abstract", decision="include",
    )
    sc.created_at = datetime(2025, 1, 13, tzinfo=timezone.utc)
    rob = RobAssessment(
        id="rb1", user_id="user-a", review_id="rv1", article_id="art1",
        tool="rob2", domain_answers={"d1": "low"}, overall_auto="low",
    )
    rob.created_at = datetime(2025, 1, 14, tzinfo=timezone.utc)
    rob.updated_at = datetime(2025, 1, 14, tzinfo=timezone.utc)
    ext = ExtractionRecord(
        id="ex1", user_id="user-a", review_id="rv1", article_id="art1",
        fields={"setting": "uk"},
    )
    ext.created_at = datetime(2025, 1, 15, tzinfo=timezone.utc)
    ext.updated_at = datetime(2025, 1, 15, tzinfo=timezone.utc)

    out = build_bundle(BundleInputs(
        project=p, articles=[a], highlights=[h], article_notes=[note],
        manuscript_sections=[sect], abbreviations=[abbr],
        datasets=[ds], dataset_variables=[var],
        analyses=[an], analysis_results=[ar],
        review=rv, search_records=[sr], screening_records=[sc],
        rob_assessments=[rob], extraction_records=[ext],
    ))
    assert len(out["articles"]) == 1
    assert len(out["highlights"]) == 1
    assert len(out["article_notes"]) == 1
    assert len(out["manuscript_sections"]) == 1
    assert len(out["abbreviations"]) == 1
    assert len(out["datasets"]) == 1
    assert len(out["dataset_variables"]) == 1
    assert len(out["analyses"]) == 1
    assert len(out["analysis_results"]) == 1
    assert out["review"] is not None
    assert out["review"]["id"] == "rv1"
    assert len(out["search_records"]) == 1
    assert len(out["screening_records"]) == 1
    assert len(out["rob_assessments"]) == 1
    assert len(out["extraction_records"]) == 1
    # FKs preserved.
    assert out["highlights"][0]["article_id"] == "art1"
    assert out["screening_records"][0]["review_id"] == "rv1"


def test_build_bundle_carries_json_columns_as_objects():
    p = _mk_project()
    a = _mk_article()
    h = Highlight(
        id="h1", user_id="user-a", article_id="art1",
        page_number=1, selected_text="x", colour="results",
        section="Results", bounding_coords={"x": 1, "y": 2, "w": 3, "h": 4},
    )
    h.created_at = datetime(2025, 1, 4, tzinfo=timezone.utc)
    out = build_bundle(BundleInputs(project=p, articles=[a], highlights=[h]))
    # JSON columns remain as dicts (not double-encoded).
    assert out["highlights"][0]["bounding_coords"] == {"x": 1, "y": 2, "w": 3, "h": 4}
    assert out["articles"][0]["authors"] == ["Doe J", "Smith K"]


def test_build_bundle_handles_review_absent():
    p = _mk_project()
    out = build_bundle(BundleInputs(project=p))
    assert out["review"] is None
    assert out["search_records"] == []
    assert out["screening_records"] == []
    assert out["rob_assessments"] == []
    assert out["extraction_records"] == []


# ── Bug 2: figures / consort / meta_analyses / meta_inputs round-trip ─


def test_build_bundle_includes_figures_consort_meta():
    from research_api.db.models import (
        ConsortData,
        Figure,
        MetaAnalysis,
        MetaInput,
        Review,
    )
    p = _mk_project()
    a = _mk_article()
    fig = Figure(
        id="fig1", user_id="user-a", project_id="proj1",
        file_ref={"backend": "local", "key": "k.png"}, file_type="image/png",
        figure_number=1, caption="A caption", alt_text="alt", byte_size=1234,
    )
    fig.created_at = datetime(2025, 1, 20, tzinfo=timezone.utc)
    fig.updated_at = datetime(2025, 1, 20, tzinfo=timezone.utc)
    consort = ConsortData(
        id="con1", user_id="user-a", project_id="proj1",
        enrollment_assessed=120, randomised=80,
    )
    consort.created_at = datetime(2025, 1, 21, tzinfo=timezone.utc)
    consort.updated_at = datetime(2025, 1, 21, tzinfo=timezone.utc)
    review = Review(id="rv1", user_id="user-a", project_id="proj1")
    review.created_at = datetime(2025, 1, 11, tzinfo=timezone.utc)
    review.updated_at = datetime(2025, 1, 11, tzinfo=timezone.utc)
    meta = MetaAnalysis(
        id="m1", user_id="user-a", review_id="rv1",
        effect_metric="md", model="fixed",
        pooled_estimate=0.5, ci_low=0.1, ci_high=0.9,
        status="completed",
    )
    meta.created_at = datetime(2025, 1, 22, tzinfo=timezone.utc)
    meta.updated_at = datetime(2025, 1, 22, tzinfo=timezone.utc)
    mi = MetaInput(
        id="mi1", user_id="user-a", meta_id="m1", article_id="art1",
        mean_a=1.0, sd_a=0.5, n_a=20,
        mean_b=0.5, sd_b=0.5, n_b=20,
    )
    mi.created_at = datetime(2025, 1, 22, tzinfo=timezone.utc)
    mi.updated_at = datetime(2025, 1, 22, tzinfo=timezone.utc)

    out = build_bundle(BundleInputs(
        project=p, articles=[a], review=review,
        figures=[fig], consort_data=consort,
        meta_analyses=[meta], meta_inputs=[mi],
    ))
    assert len(out["figures"]) == 1
    assert out["figures"][0]["caption"] == "A caption"
    assert out["consort_data"] is not None
    assert out["consort_data"]["randomised"] == 80
    assert len(out["meta_analyses"]) == 1
    assert out["meta_analyses"][0]["effect_metric"] == "md"
    assert len(out["meta_inputs"]) == 1
    assert out["meta_inputs"][0]["article_id"] == "art1"


def test_build_bundle_no_phase_75_87_when_absent():
    p = _mk_project()
    out = build_bundle(BundleInputs(project=p))
    assert out["figures"] == []
    assert out["consort_data"] is None
    assert out["meta_analyses"] == []
    assert out["meta_inputs"] == []
