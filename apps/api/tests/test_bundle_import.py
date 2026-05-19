"""Bundle import — SECURITY-CRITICAL.

Properties under test:
  - every imported row is owned by `target_user_id`, regardless of what the
    bundle claims;
  - every imported row gets a fresh primary key, and all FKs are rewritten
    against the old→new id map;
  - unknown top-level keys are silently dropped (forward-compat);
  - missing/invalid schema_version → ValueError;
  - missing `project` → ValueError;
  - export → import round-trip is lossless modulo IDs and user_id;
  - a partial failure rolls the entire import back.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

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
from research_api.services.export.bundle_import import (
    BundleImportError,
    import_bundle,
)


def _make_minimal_bundle(user_id: str = "user-a") -> dict:
    p = Project(
        id="proj-orig",
        user_id=user_id,
        title="Orig",
        study_type="Outcome Study",
        citation_style="vancouver",
        ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return build_bundle(BundleInputs(project=p))


@pytest.mark.asyncio
async def test_import_minimal_bundle_creates_project(session):
    bundle = _make_minimal_bundle()
    result = await import_bundle(bundle, target_user_id="user-b", session=session)

    assert result["projects"] == 1
    row = (await session.execute(select(Project))).scalar_one()
    assert row.user_id == "user-b"  # target stamped
    assert row.title == "Orig"
    assert row.id != "proj-orig"  # fresh PK


@pytest.mark.asyncio
async def test_import_stamps_target_user_id_regardless_of_bundle(session):
    bundle = _make_minimal_bundle(user_id="attacker")
    bundle["project"]["user_id"] = "attacker"
    await import_bundle(bundle, target_user_id="victim", session=session)
    row = (await session.execute(select(Project))).scalar_one()
    assert row.user_id == "victim"


@pytest.mark.asyncio
async def test_import_rejects_missing_schema_version(session):
    bundle = _make_minimal_bundle()
    del bundle["schema_version"]
    with pytest.raises(BundleImportError):
        await import_bundle(bundle, target_user_id="user-b", session=session)


@pytest.mark.asyncio
async def test_import_rejects_wrong_schema_version(session):
    bundle = _make_minimal_bundle()
    bundle["schema_version"] = 99
    with pytest.raises(BundleImportError):
        await import_bundle(bundle, target_user_id="user-b", session=session)


@pytest.mark.asyncio
async def test_import_rejects_missing_project(session):
    bundle = _make_minimal_bundle()
    del bundle["project"]
    with pytest.raises(BundleImportError):
        await import_bundle(bundle, target_user_id="user-b", session=session)


@pytest.mark.asyncio
async def test_import_silently_drops_unknown_top_level_keys(session):
    bundle = _make_minimal_bundle()
    bundle["future_feature"] = {"will": "exist"}
    bundle["another_unknown"] = [1, 2, 3]
    result = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert result["projects"] == 1


@pytest.mark.asyncio
async def test_import_mints_fresh_ids_for_all_rows(session):
    # Build a bundle with at least one row in each table.
    p = Project(
        id="proj-orig", user_id="user-a", title="P", study_type="Outcome Study",
        citation_style="vancouver", ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    a = Article(
        id="art-orig", user_id="user-a", project_id="proj-orig",
        title="A", authors=["Doe J"], year=2024,
    )
    a.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    h = Highlight(
        id="h-orig", user_id="user-a", article_id="art-orig",
        page_number=1, selected_text="x", colour="results",
        section="Results", bounding_coords={"x": 0, "y": 0, "w": 1, "h": 1},
    )
    h.created_at = datetime(2025, 1, 3, tzinfo=timezone.utc)
    bundle = build_bundle(BundleInputs(project=p, articles=[a], highlights=[h]))

    await import_bundle(bundle, target_user_id="user-b", session=session)
    proj = (await session.execute(select(Project))).scalar_one()
    art = (await session.execute(select(Article))).scalar_one()
    hi = (await session.execute(select(Highlight))).scalar_one()

    assert proj.id != "proj-orig"
    assert art.id != "art-orig"
    assert hi.id != "h-orig"
    # FKs rewritten.
    assert art.project_id == proj.id
    assert hi.article_id == art.id
    # All re-tagged.
    assert proj.user_id == art.user_id == hi.user_id == "user-b"


@pytest.mark.asyncio
async def test_import_full_round_trip_lossless(session):
    # Build a comprehensive bundle and verify content (modulo IDs) round-trips.
    p = Project(
        id="proj-orig", user_id="user-a", title="Big", study_type="Outcome Study",
        citation_style="ieee", ai_provider="gemini", target_journal="Nature",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    a = Article(
        id="art-orig", user_id="user-a", project_id="proj-orig",
        title="Article Title", authors=["Doe J", "Smith K"], journal="JAMA",
        year=2024, doi="10.1/x",
    )
    a.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    h = Highlight(
        id="h-orig", user_id="user-a", article_id="art-orig",
        page_number=3, selected_text="findings", colour="results",
        section="Results", bounding_coords={"x": 1, "y": 2, "w": 3, "h": 4},
        user_note="my note", ai_summary="summary", sort_order=2,
    )
    h.created_at = datetime(2025, 1, 3, tzinfo=timezone.utc)
    n = ArticleNote(
        id="note-orig", user_id="user-a", article_id="art-orig",
        content="cite this for intro",
    )
    n.updated_at = datetime(2025, 1, 4, tzinfo=timezone.utc)
    sect = ManuscriptSection(
        id="s-orig", user_id="user-a", project_id="proj-orig",
        section_name="Introduction", content="<p>hello [CITE_art-orig]</p>",
        word_count=2,
    )
    sect.updated_at = datetime(2025, 1, 5, tzinfo=timezone.utc)
    abbr = Abbreviation(
        id="ab-orig", user_id="user-a", project_id="proj-orig",
        short_form="RCT", long_form="randomised controlled trial",
    )
    abbr.created_at = datetime(2025, 1, 6, tzinfo=timezone.utc)
    ds = Dataset(
        id="ds-orig", user_id="user-a", project_id="proj-orig",
        filename="data.csv", file_ref={"backend": "local", "key": "datasets/x"},
        file_type="text/csv", n_rows=10, n_columns=3,
    )
    ds.created_at = datetime(2025, 1, 7, tzinfo=timezone.utc)
    dv = DatasetVariable(
        id="dv-orig", user_id="user-a", dataset_id="ds-orig",
        name="age", position=0, inferred_type="numeric",
        user_type="continuous", n_missing=2, sample_values=[1, 2, 3],
    )
    an = Analysis(
        id="an-orig", user_id="user-a", project_id="proj-orig",
        dataset_id="ds-orig",
        question_type="compare_means", chosen_test="t_test",
        recommendation_rationale="ok", variables={"a": "age"},
    )
    an.created_at = datetime(2025, 1, 8, tzinfo=timezone.utc)
    ar = AnalysisResult(
        id="ar-orig", user_id="user-a", analysis_id="an-orig",
        summary={"statistic": 1.5, "p_value": 0.04},
        assumptions={"normality": True}, ai_interpretation="solid result",
    )
    ar.created_at = datetime(2025, 1, 9, tzinfo=timezone.utc)
    rv = Review(
        id="rv-orig", user_id="user-a", project_id="proj-orig",
        pico_population="adults", pico_intervention="drug X",
    )
    rv.created_at = datetime(2025, 1, 10, tzinfo=timezone.utc)
    rv.updated_at = datetime(2025, 1, 10, tzinfo=timezone.utc)
    sr = SearchRecord(
        id="sr-orig", user_id="user-a", review_id="rv-orig",
        database_name="pubmed", query_string="cancer",
        date_searched=datetime(2025, 1, 12), n_results=42, notes="ok",
    )
    sr.created_at = datetime(2025, 1, 11, tzinfo=timezone.utc)
    sc = ScreeningRecord(
        id="sc-orig", user_id="user-a", review_id="rv-orig", article_id="art-orig",
        stage="title_abstract", decision="include", reason="relevant",
    )
    sc.created_at = datetime(2025, 1, 12, tzinfo=timezone.utc)
    rob = RobAssessment(
        id="rb-orig", user_id="user-a", review_id="rv-orig", article_id="art-orig",
        tool="rob2", domain_answers={"d1": "low"}, overall_auto="low",
    )
    rob.created_at = datetime(2025, 1, 13, tzinfo=timezone.utc)
    rob.updated_at = datetime(2025, 1, 13, tzinfo=timezone.utc)
    ext = ExtractionRecord(
        id="ex-orig", user_id="user-a", review_id="rv-orig", article_id="art-orig",
        fields={"setting": "uk"},
    )
    ext.created_at = datetime(2025, 1, 14, tzinfo=timezone.utc)
    ext.updated_at = datetime(2025, 1, 14, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(
        project=p, articles=[a], highlights=[h], article_notes=[n],
        manuscript_sections=[sect], abbreviations=[abbr],
        datasets=[ds], dataset_variables=[dv],
        analyses=[an], analysis_results=[ar],
        review=rv, search_records=[sr], screening_records=[sc],
        rob_assessments=[rob], extraction_records=[ext],
    ))

    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert counts == {
        "projects": 1, "articles": 1, "highlights": 1, "article_notes": 1,
        "manuscript_sections": 1, "abbreviations": 1,
        "datasets": 1, "dataset_variables": 1,
        # Phase 13 (MP13) — bundle source didn't include any transformations.
        "dataset_transformations": 0,
        "analyses": 1, "analysis_results": 1,
        "reviews": 1, "search_records": 1, "screening_records": 1,
        "rob_assessments": 1, "extraction_records": 1,
        "figures": 0, "consort_data": 0,
        "meta_analyses": 0, "meta_inputs": 0,
        # Phase 10 additions — bundle source didn't include any rows.
        "authors": 0, "affiliations": 0, "author_affiliations": 0,
        "contributions": 0, "project_frontmatter": 0,
        # Phase 11 additions — bundle source didn't include any rows.
        "manuscript_snapshots": 0, "manuscript_comments": 0,
        # Phase 12 additions — bundle source didn't include any rows.
        "cover_letter": 0, "reviewer_responses": 0,
        # Phase 13.5 additions — bundle source didn't include any rows.
        "dataset_plots": 0, "analysis_plans": 0, "analysis_plan_runs": 0,
        # Phase 14 (MP14) additions — bundle source didn't include any rows.
        "grade_assessments": 0, "prospero_draft": 0,
        # Phase 15 (MP15) additions — bundle source didn't include any rows.
        "living_review_job": 0,
        # Phase 19 (MP19) additions — bundle source didn't include any rows.
        "mesh_terms": 0, "search_strategies": 0,
        "narrative_synthesis_entries": 0, "outcome_instruments": 0,
    }

    # Verify content survives (modulo IDs + user_id).
    proj = (await session.execute(select(Project))).scalar_one()
    assert proj.title == "Big"
    assert proj.citation_style == "ieee"
    assert proj.target_journal == "Nature"

    art = (await session.execute(select(Article))).scalar_one()
    assert art.authors == ["Doe J", "Smith K"]
    assert art.year == 2024
    assert art.doi == "10.1/x"
    assert art.project_id == proj.id

    hi = (await session.execute(select(Highlight))).scalar_one()
    assert hi.bounding_coords == {"x": 1, "y": 2, "w": 3, "h": 4}
    assert hi.user_note == "my note"
    assert hi.article_id == art.id

    sec_row = (await session.execute(select(ManuscriptSection))).scalar_one()
    assert sec_row.section_name == "Introduction"
    assert sec_row.project_id == proj.id

    rev = (await session.execute(select(Review))).scalar_one()
    assert rev.pico_population == "adults"
    assert rev.project_id == proj.id

    sc_row = (await session.execute(select(ScreeningRecord))).scalar_one()
    assert sc_row.review_id == rev.id
    assert sc_row.article_id == art.id

    rob_row = (await session.execute(select(RobAssessment))).scalar_one()
    assert rob_row.review_id == rev.id
    assert rob_row.domain_answers == {"d1": "low"}

    # Every imported row owned by user-b.
    for table in (Project, Article, Highlight, ArticleNote, ManuscriptSection,
                  Abbreviation, Dataset, DatasetVariable, Analysis,
                  AnalysisResult, Review, SearchRecord, ScreeningRecord,
                  RobAssessment, ExtractionRecord):
        for row in (await session.execute(select(table))).scalars().all():
            assert row.user_id == "user-b", f"{table.__name__} not retagged"


@pytest.mark.asyncio
async def test_import_skips_orphan_highlight(session):
    # A highlight referencing an article not in the bundle is silently dropped
    # (the bundle should never be assembled this way; this is defensive).
    bundle = _make_minimal_bundle()
    bundle["highlights"] = [{
        "id": "h-orig", "user_id": "user-a", "article_id": "missing-art",
        "page_number": 1, "selected_text": "x", "colour": "results",
        "section": "Results",
        "bounding_coords": {"x": 0, "y": 0, "w": 1, "h": 1},
        "user_note": None, "ai_summary": None, "sort_order": 0,
        "created_at": "2025-01-01T00:00:00+00:00",
    }]
    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert counts["highlights"] == 0


@pytest.mark.asyncio
async def test_import_rolls_back_on_error(session):
    # Two manuscript sections with the same (project_id, user_id, section_name)
    # violate uq_manuscript_section_project_user_section → IntegrityError.
    p = Project(
        id="proj-orig", user_id="user-a", title="P",
        study_type="Outcome Study", citation_style="vancouver", ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    s1 = ManuscriptSection(
        id="s1", user_id="user-a", project_id="proj-orig",
        section_name="Introduction", content="<p>a</p>", word_count=1,
    )
    s1.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    s2 = ManuscriptSection(
        id="s2", user_id="user-a", project_id="proj-orig",
        section_name="Introduction", content="<p>b</p>", word_count=1,
    )
    s2.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bundle = build_bundle(BundleInputs(project=p, manuscript_sections=[s1, s2]))

    with pytest.raises(Exception):
        await import_bundle(bundle, target_user_id="user-b", session=session)

    # Project must not survive.
    projects = (await session.execute(select(Project))).scalars().all()
    assert projects == []


@pytest.mark.asyncio
async def test_import_does_not_clobber_existing_user_projects(session):
    # Pre-existing project in user-b's space.
    existing = Project(
        id="pre", user_id="user-b", title="MINE",
        study_type="Outcome Study", citation_style="vancouver", ai_provider="gemini",
    )
    existing.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    existing.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    session.add(existing)
    await session.flush()

    bundle = _make_minimal_bundle(user_id="user-a")
    await import_bundle(bundle, target_user_id="user-b", session=session)

    rows = (await session.execute(select(Project))).scalars().all()
    titles = sorted(r.title for r in rows)
    assert titles == ["MINE", "Orig"]
    for r in rows:
        assert r.user_id == "user-b"


@pytest.mark.asyncio
async def test_import_large_bundle_completes_in_reasonable_time(session):
    # 200 articles must import in well under 5 seconds.
    p = Project(
        id="proj-orig", user_id="user-a", title="Big", study_type="Outcome Study",
        citation_style="vancouver", ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    arts = []
    for i in range(200):
        a = Article(
            id=f"art{i}", user_id="user-a", project_id="proj-orig",
            title=f"Article {i}", authors=["Doe J"], year=2024,
        )
        a.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
        arts.append(a)
    bundle = build_bundle(BundleInputs(project=p, articles=arts))

    t0 = time.perf_counter()
    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    elapsed = time.perf_counter() - t0
    assert counts["articles"] == 200
    assert elapsed < 5.0, f"import took {elapsed:.2f}s"


# ── Bug 2: figures / consort / meta_analyses / meta_inputs round-trip ─


@pytest.mark.asyncio
async def test_import_round_trips_figures_consort_meta(session):
    from research_api.db.models import (
        ConsortData,
        Figure,
        MetaAnalysis,
        MetaInput,
    )

    p = Project(
        id="proj-orig", user_id="user-a", title="P", study_type="Systematic Review",
        citation_style="vancouver", ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    art = Article(
        id="art1", user_id="user-a", project_id="proj-orig",
        title="A", authors=["Doe J"], year=2024,
    )
    art.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    fig = Figure(
        id="fig1", user_id="user-a", project_id="proj-orig",
        file_ref={"backend": "local", "key": "k.png"}, file_type="image/png",
        figure_number=1, caption="cap1", alt_text="alt1", byte_size=100,
    )
    fig.created_at = datetime(2025, 1, 3, tzinfo=timezone.utc)
    fig.updated_at = datetime(2025, 1, 3, tzinfo=timezone.utc)
    consort = ConsortData(
        id="con1", user_id="user-a", project_id="proj-orig",
        randomised=42,
    )
    consort.created_at = datetime(2025, 1, 4, tzinfo=timezone.utc)
    consort.updated_at = datetime(2025, 1, 4, tzinfo=timezone.utc)
    review = Review(id="rv1", user_id="user-a", project_id="proj-orig")
    review.created_at = datetime(2025, 1, 5, tzinfo=timezone.utc)
    review.updated_at = datetime(2025, 1, 5, tzinfo=timezone.utc)
    meta = MetaAnalysis(
        id="m1", user_id="user-a", review_id="rv1",
        effect_metric="md", model="random",
        pooled_estimate=0.42, status="completed",
    )
    meta.created_at = datetime(2025, 1, 6, tzinfo=timezone.utc)
    meta.updated_at = datetime(2025, 1, 6, tzinfo=timezone.utc)
    mi = MetaInput(
        id="mi1", user_id="user-a", meta_id="m1", article_id="art1",
        mean_a=1.0, sd_a=0.5, n_a=10,
        mean_b=0.5, sd_b=0.5, n_b=10,
    )
    mi.created_at = datetime(2025, 1, 6, tzinfo=timezone.utc)
    mi.updated_at = datetime(2025, 1, 6, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(
        project=p, articles=[art], review=review,
        figures=[fig], consort_data=consort,
        meta_analyses=[meta], meta_inputs=[mi],
    ))
    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert counts["figures"] == 1
    assert counts["consort_data"] == 1
    assert counts["meta_analyses"] == 1
    assert counts["meta_inputs"] == 1

    fig_rows = (await session.execute(select(Figure))).scalars().all()
    assert len(fig_rows) == 1
    assert fig_rows[0].user_id == "user-b"
    assert fig_rows[0].id != "fig1"
    assert fig_rows[0].caption == "cap1"

    con_rows = (await session.execute(select(ConsortData))).scalars().all()
    assert len(con_rows) == 1
    assert con_rows[0].user_id == "user-b"
    assert con_rows[0].randomised == 42

    meta_rows = (await session.execute(select(MetaAnalysis))).scalars().all()
    assert len(meta_rows) == 1
    assert meta_rows[0].user_id == "user-b"
    assert meta_rows[0].effect_metric == "md"

    mi_rows = (await session.execute(select(MetaInput))).scalars().all()
    assert len(mi_rows) == 1
    assert mi_rows[0].user_id == "user-b"
    # FK rewiring: meta_id and article_id should reference the *new* PKs.
    assert mi_rows[0].meta_id == meta_rows[0].id
    assert mi_rows[0].meta_id != "m1"


@pytest.mark.asyncio
async def test_import_meta_inputs_skipped_when_meta_orphan(session):
    """Defensive: a meta_input that references a missing/orphan meta_id
    must be silently dropped rather than crashing the import."""
    from research_api.db.models import MetaInput

    p = Project(
        id="proj-orig", user_id="user-a", title="P", study_type="Systematic Review",
        citation_style="vancouver", ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bundle = build_bundle(BundleInputs(project=p))
    # Manually inject an orphan meta_input (no review, no meta_analyses, no
    # articles). Import must not raise.
    bundle["meta_inputs"] = [{
        "id": "mi_orphan", "user_id": "user-a",
        "meta_id": "missing", "article_id": "missing",
        "mean_a": 1.0,
    }]
    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert counts["meta_inputs"] == 0
    mi_rows = (await session.execute(select(MetaInput))).scalars().all()
    assert mi_rows == []
