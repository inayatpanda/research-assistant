"""Bundle import — SECURITY-CRITICAL.

Re-tags every imported row as `target_user_id`. Mints fresh primary keys and
rewrites FKs through an old→new id map. Wraps the entire operation in the
caller's session; on failure the session is rolled back and re-raised.

The bundle's `user_id` fields are NEVER trusted. The schema is permissive on
unknown top-level keys (forward-compat) but strict on `schema_version` and
the `project` root.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import (
    Abbreviation,
    Affiliation,
    Analysis,
    AnalysisPlan,
    AnalysisPlanRun,
    AnalysisPopulation,
    AnalysisResult,
    Article,
    ArticleNote,
    Author,
    AuthorAffiliation,
    ChecklistRun,
    ConsortData,
    Contribution,
    CoverLetter,
    Dataset,
    DatasetPlot,
    DatasetTransformation,
    DatasetVariable,
    EconomicAnalysis,
    EconomicResult,
    ExtractionRecord,
    Figure,
    GradeAssessment,
    Highlight,
    ImputationRun,
    LivingReviewJob,
    ManuscriptComment,
    ManuscriptSection,
    ManuscriptSnapshot,
    MeshTerm,
    MetaAnalysis,
    MetaInput,
    NarrativeSynthesisEntry,
    OutcomeInstrument,
    PeerReview,
    Project,
    ProjectFrontmatter,
    ProsperoDraft,
    Review,
    ReviewerResponse,
    RobAssessment,
    ScreeningRecord,
    SearchRecord,
    SearchStrategy,
)
from .bundle_export import SCHEMA_VERSION


class BundleImportError(ValueError):
    """Raised when a bundle is structurally invalid (versioning, missing project)."""


def _new_id() -> str:
    return uuid4().hex


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _validate(bundle: dict) -> None:
    if not isinstance(bundle, dict):
        raise BundleImportError("Bundle must be an object")
    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise BundleImportError(
            f"Unsupported schema_version: {bundle.get('schema_version')!r} "
            f"(expected {SCHEMA_VERSION})"
        )
    if "project" not in bundle or not isinstance(bundle["project"], dict):
        raise BundleImportError("Bundle missing required `project` object")


def _pick(d: dict, *keys: str) -> dict:
    return {k: d.get(k) for k in keys}


async def import_bundle(
    bundle: dict,
    *,
    target_user_id: str,
    session: AsyncSession,
) -> dict[str, int]:
    """Insert a bundle's content into `session` owned by `target_user_id`.

    Returns a per-table count dict. On any insert error the caller's session
    is rolled back via the surrounding transaction; we re-raise so the route
    layer can map to HTTP 422/500 as appropriate.
    """
    _validate(bundle)

    try:
        counts = await _do_import(bundle, target_user_id=target_user_id, session=session)
    except Exception:
        await session.rollback()
        raise
    return counts


async def _do_import(
    bundle: dict,
    *,
    target_user_id: str,
    session: AsyncSession,
) -> dict[str, int]:
    counts: dict[str, int] = {
        "projects": 0, "articles": 0, "highlights": 0, "article_notes": 0,
        "manuscript_sections": 0, "abbreviations": 0,
        "datasets": 0, "dataset_variables": 0, "dataset_transformations": 0,
        "analyses": 0, "analysis_results": 0,
        "reviews": 0, "search_records": 0, "screening_records": 0,
        "rob_assessments": 0, "extraction_records": 0,
        "figures": 0, "consort_data": 0,
        "meta_analyses": 0, "meta_inputs": 0,
        "authors": 0, "affiliations": 0, "author_affiliations": 0,
        "contributions": 0, "project_frontmatter": 0,
        "manuscript_snapshots": 0, "manuscript_comments": 0,
        "cover_letter": 0, "reviewer_responses": 0,
        "dataset_plots": 0, "analysis_plans": 0, "analysis_plan_runs": 0,
        "grade_assessments": 0, "prospero_draft": 0,
        "living_review_job": 0,
        "mesh_terms": 0, "search_strategies": 0,
        "narrative_synthesis_entries": 0, "outcome_instruments": 0,
        # Phase 17 (MP17) — Stats depth.
        "analysis_populations": 0, "imputation_runs": 0,
        # Phase 18 (MP18) — Health economics.
        "economic_analyses": 0, "economic_results": 0,
        # Phase 20 (MP20) — Interactive reporting checklists.
        "checklist_runs": 0,
        # Phase 4.6 — AI peer-review critiques.
        "peer_reviews": 0,
    }

    proj_in = bundle["project"]
    new_project_id = _new_id()
    project = Project(
        id=new_project_id,
        user_id=target_user_id,
        title=proj_in.get("title") or "Imported project",
        study_type=proj_in.get("study_type") or "Outcome Study",
        citation_style=proj_in.get("citation_style") or "vancouver",
        ai_provider=proj_in.get("ai_provider") or "gemini",
        target_journal=proj_in.get("target_journal"),
        prospero_number=proj_in.get("prospero_number"),
        clinicaltrials_number=proj_in.get("clinicaltrials_number"),
    )
    session.add(project)
    await session.flush()
    counts["projects"] = 1

    # Phase S1 — seed a project_members owner row so the importing user
    # has explicit access under the RBAC model. We only do this if a
    # real User row exists for ``target_user_id`` (FK constraint). In
    # tests that exercise the import-as-arbitrary-user pathway without a
    # users row, ``projects.user_id`` matches the importer and the
    # legacy-fallback path in ``ProjectMemberRepository.get_role`` takes
    # over.
    from sqlalchemy import select as _sa_select

    from ...db.models import ProjectMember, User

    has_user = (
        await session.execute(
            _sa_select(User.id).where(User.id == target_user_id)
        )
    ).scalar_one_or_none()
    if has_user is not None:
        session.add(
            ProjectMember(
                id=_new_id(),
                project_id=new_project_id,
                user_id=target_user_id,
                role="owner",
                invited_by=None,
            )
        )
        await session.flush()

    article_map: dict[str, str] = {}
    for art in bundle.get("articles") or []:
        old_id = art.get("id")
        new_id = _new_id()
        a = Article(
            id=new_id,
            user_id=target_user_id,
            project_id=new_project_id,
            title=art.get("title") or "Untitled",
            authors=art.get("authors") or [],
            journal=art.get("journal"),
            year=art.get("year"),
            volume=art.get("volume"),
            issue=art.get("issue"),
            pages=art.get("pages"),
            doi=art.get("doi"),
            file_ref=art.get("file_ref"),
            file_type=art.get("file_type"),
            abstract=art.get("abstract"),
            study_design=art.get("study_design"),
            review_status=art.get("review_status") or "pending",
            exclusion_reason=art.get("exclusion_reason"),
            conflict_of_interest=art.get("conflict_of_interest"),
        )
        session.add(a)
        if old_id is not None:
            article_map[old_id] = new_id
    if bundle.get("articles"):
        await session.flush()
        counts["articles"] = len(article_map)

    for hl in bundle.get("highlights") or []:
        old_art = hl.get("article_id")
        new_art = article_map.get(old_art)
        if new_art is None:
            continue  # orphan reference — skip silently
        session.add(Highlight(
            id=_new_id(),
            user_id=target_user_id,
            article_id=new_art,
            page_number=hl.get("page_number") or 0,
            selected_text=hl.get("selected_text") or "",
            colour=hl.get("colour") or "intro",
            section=hl.get("section") or "Introduction",
            bounding_coords=hl.get("bounding_coords") or {},
            user_note=hl.get("user_note"),
            ai_summary=hl.get("ai_summary"),
            sort_order=hl.get("sort_order") or 0,
        ))
        counts["highlights"] += 1
    if counts["highlights"]:
        await session.flush()

    for n in bundle.get("article_notes") or []:
        new_art = article_map.get(n.get("article_id"))
        if new_art is None:
            continue
        session.add(ArticleNote(
            id=_new_id(),
            user_id=target_user_id,
            article_id=new_art,
            content=n.get("content") or "",
        ))
        counts["article_notes"] += 1
    if counts["article_notes"]:
        await session.flush()

    for s in bundle.get("manuscript_sections") or []:
        session.add(ManuscriptSection(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            section_name=s.get("section_name") or "Introduction",
            content=s.get("content") or "",
            word_count=s.get("word_count") or 0,
        ))
        counts["manuscript_sections"] += 1
    if counts["manuscript_sections"]:
        await session.flush()

    for ab in bundle.get("abbreviations") or []:
        session.add(Abbreviation(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            short_form=ab.get("short_form") or "",
            long_form=ab.get("long_form") or "",
        ))
        counts["abbreviations"] += 1
    if counts["abbreviations"]:
        await session.flush()

    dataset_map: dict[str, str] = {}
    # First pass: assign new ids without resolving derived_from links yet so
    # we can remap source pointers after every row's new id is known.
    pending_psm: list[tuple[str, str | None]] = []  # (new_ds_id, old_source_id)
    for ds in bundle.get("datasets") or []:
        new_ds_id = _new_id()
        # File payloads are not in the bundle; mark file_ref as missing so the
        # stats UI can flag the dataset row as "file lost" without crashing.
        ref = ds.get("file_ref") or {}
        if not ref:
            ref = {"backend": "missing", "key": ""}
        session.add(Dataset(
            id=new_ds_id,
            user_id=target_user_id,
            project_id=new_project_id,
            filename=ds.get("filename") or "imported.csv",
            file_ref=ref,
            file_type=ds.get("file_type") or "text/csv",
            n_rows=ds.get("n_rows") or 0,
            n_columns=ds.get("n_columns") or 0,
            dataset_metadata=ds.get("dataset_metadata"),
            derived_from_dataset_ids=ds.get("derived_from_dataset_ids"),
        ))
        if ds.get("id"):
            dataset_map[ds["id"]] = new_ds_id
        pending_psm.append((new_ds_id, ds.get("derived_from_dataset_id")))
        counts["datasets"] += 1
    if counts["datasets"]:
        await session.flush()
        # Second pass — remap derived_from_dataset_id pointers now that all
        # new ids exist in dataset_map.
        for new_ds_id, old_source in pending_psm:
            if not old_source:
                continue
            mapped = dataset_map.get(old_source)
            if mapped is None:
                continue
            row = await session.get(Dataset, new_ds_id)
            if row is not None:
                row.derived_from_dataset_id = mapped
        await session.flush()

    for v in bundle.get("dataset_variables") or []:
        new_ds = dataset_map.get(v.get("dataset_id"))
        if new_ds is None:
            continue
        session.add(DatasetVariable(
            id=_new_id(),
            user_id=target_user_id,
            dataset_id=new_ds,
            name=v.get("name") or "",
            position=v.get("position") or 0,
            inferred_type=v.get("inferred_type") or "string",
            user_type=v.get("user_type"),
            n_missing=v.get("n_missing") or 0,
            sample_values=v.get("sample_values") or [],
        ))
        counts["dataset_variables"] += 1
    if counts["dataset_variables"]:
        await session.flush()

    # ── Phase 13 (MP13) — Dataset transformation stacks ───────────────
    for t in bundle.get("dataset_transformations") or []:
        new_ds = dataset_map.get(t.get("dataset_id"))
        if new_ds is None:
            continue
        op_type = t.get("op_type")
        if not op_type:
            continue
        session.add(DatasetTransformation(
            id=_new_id(),
            user_id=target_user_id,
            dataset_id=new_ds,
            position=int(t.get("position") or 0),
            op_type=op_type,
            op_args=t.get("op_args") or {},
            label=t.get("label") or "",
        ))
        counts["dataset_transformations"] += 1
    if counts["dataset_transformations"]:
        await session.flush()

    analysis_map: dict[str, str] = {}
    for an in bundle.get("analyses") or []:
        new_ds = dataset_map.get(an.get("dataset_id"))
        if new_ds is None:
            continue
        new_an_id = _new_id()
        session.add(Analysis(
            id=new_an_id,
            user_id=target_user_id,
            project_id=new_project_id,
            dataset_id=new_ds,
            question_type=an.get("question_type") or "",
            chosen_test=an.get("chosen_test") or "",
            recommendation_rationale=an.get("recommendation_rationale") or "",
            variables=an.get("variables") or {},
            status=an.get("status") or "draft",
        ))
        if an.get("id"):
            analysis_map[an["id"]] = new_an_id
        counts["analyses"] += 1
    if counts["analyses"]:
        await session.flush()

    for ar in bundle.get("analysis_results") or []:
        new_an = analysis_map.get(ar.get("analysis_id"))
        if new_an is None:
            continue
        session.add(AnalysisResult(
            id=_new_id(),
            user_id=target_user_id,
            analysis_id=new_an,
            summary=ar.get("summary") or {},
            assumptions=ar.get("assumptions") or {},
            chart=ar.get("chart"),
            ai_interpretation=ar.get("ai_interpretation"),
        ))
        counts["analysis_results"] += 1
    if counts["analysis_results"]:
        await session.flush()

    # Phase 17 (MP17) — Analysis populations + imputation runs.
    for pop in bundle.get("analysis_populations") or []:
        new_ds = dataset_map.get(pop.get("dataset_id"))
        if new_ds is None:
            continue
        session.add(AnalysisPopulation(
            id=_new_id(),
            user_id=target_user_id,
            dataset_id=new_ds,
            name=(pop.get("name") or "Population")[:255],
            definition=pop.get("definition") or {},
            study_assignment_field=(pop.get("study_assignment_field") or "")[:255],
            treatment_received_field=pop.get("treatment_received_field"),
        ))
        counts["analysis_populations"] += 1
    if counts["analysis_populations"]:
        await session.flush()

    for run in bundle.get("imputation_runs") or []:
        new_ds = dataset_map.get(run.get("dataset_id"))
        if new_ds is None:
            continue
        session.add(ImputationRun(
            id=_new_id(),
            user_id=target_user_id,
            dataset_id=new_ds,
            method=run.get("method") or "mice",
            n_imputations=int(run.get("n_imputations") or 5),
            seed=int(run.get("seed") or 42),
            target_cols=run.get("target_cols") or [],
            pooled_summary=run.get("pooled_summary") or {},
        ))
        counts["imputation_runs"] += 1
    if counts["imputation_runs"]:
        await session.flush()

    # Phase 18 (MP18) — Economic analyses + results.
    econ_map: dict[str, str] = {}
    for ea in bundle.get("economic_analyses") or []:
        old_id = ea.get("id")
        new_econ_id = _new_id()
        new_ds_id: str | None = None
        if ea.get("dataset_id"):
            new_ds_id = dataset_map.get(ea.get("dataset_id"))
            if new_ds_id is None:
                # Skip economic analyses whose dataset was not imported.
                continue
        session.add(EconomicAnalysis(
            id=new_econ_id,
            user_id=target_user_id,
            project_id=new_project_id,
            dataset_id=new_ds_id,
            name=(ea.get("name") or "Economic analysis")[:255],
            currency=ea.get("currency") or "GBP",
            time_horizon_months=int(ea.get("time_horizon_months") or 12),
            perspective=ea.get("perspective") or "healthcare_system",
            discount_rate_costs=float(ea.get("discount_rate_costs") or 0.035),
            discount_rate_qalys=float(ea.get("discount_rate_qalys") or 0.035),
            wtp_thresholds=ea.get("wtp_thresholds") or [20000, 30000],
            utility_value_set=ea.get("utility_value_set") or "EQ5D_5L_UK",
            bootstrap_n=int(ea.get("bootstrap_n") or 1000),
            seed=int(ea.get("seed") or 42),
            treatment_col=(ea.get("treatment_col") or "")[:255],
            comparator_label=(ea.get("comparator_label") or "")[:255],
            intervention_label=(ea.get("intervention_label") or "")[:255],
            cost_columns=ea.get("cost_columns") or [],
            ai_interpretation=ea.get("ai_interpretation"),
        ))
        if old_id is not None:
            econ_map[old_id] = new_econ_id
        counts["economic_analyses"] += 1
    if counts["economic_analyses"]:
        await session.flush()

    for er in bundle.get("economic_results") or []:
        new_eid = econ_map.get(er.get("economic_analysis_id"))
        if new_eid is None:
            continue
        session.add(EconomicResult(
            id=_new_id(),
            user_id=target_user_id,
            economic_analysis_id=new_eid,
            mean_cost_diff=float(er.get("mean_cost_diff") or 0.0),
            mean_qaly_diff=float(er.get("mean_qaly_diff") or 0.0),
            icer=er.get("icer"),
            dominance_status=er.get("dominance_status") or "icer_calculated",
            nmb_at_thresholds=er.get("nmb_at_thresholds") or {},
            ceac_data=er.get("ceac_data") or [],
            plane_bootstrap=er.get("plane_bootstrap") or [],
            sensitivity=er.get("sensitivity"),
            plane_png_uri=er.get("plane_png_uri") or "",
            ceac_png_uri=er.get("ceac_png_uri") or "",
        ))
        counts["economic_results"] += 1
    if counts["economic_results"]:
        await session.flush()

    # Phase 20 (MP20) — Checklist runs. The unique key includes ``title`` so
    # imports into an existing project can collide; we coerce the title by
    # appending a numeric suffix until the insert succeeds. The catalogue
    # JSONs are static, not in the bundle.
    seen_titles: dict[tuple[str, str], int] = {}
    for cr in bundle.get("checklist_runs") or []:
        key = str(cr.get("checklist_key") or "").strip()
        if not key:
            continue
        base_title = str(cr.get("title") or "Imported run")[:255]
        # Dedupe within the bundle itself by bumping the title — the
        # database UNIQUE constraint blocks (project, user, key, title)
        # collisions and we cannot rely on flush-level error reporting
        # here.
        dup_key = (key, base_title)
        n = seen_titles.get(dup_key, 0)
        title = base_title if n == 0 else f"{base_title} ({n})"
        seen_titles[dup_key] = n + 1
        items = cr.get("items")
        if not isinstance(items, list):
            items = []
        session.add(ChecklistRun(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            checklist_key=key[:64],
            title=title[:255],
            items=items,
            overall_compliance_pct=float(cr.get("overall_compliance_pct") or 0.0),
        ))
        counts["checklist_runs"] += 1
    if counts["checklist_runs"]:
        await session.flush()

    # Phase 4.6 — Peer-review critiques. We re-import the row verbatim
    # except for the uploaded source file (not transported in the bundle);
    # the ``source_file_ref`` survives as a stale reference for audit but
    # the export endpoint will refuse to stream the file.
    _allowed_recs = {"reject", "major_revision", "minor_revision", "accept"}
    _allowed_sources = {"manuscript", "uploaded_pdf", "uploaded_docx"}
    for pr in bundle.get("peer_reviews") or []:
        src = str(pr.get("source_type") or "manuscript")
        if src not in _allowed_sources:
            src = "manuscript"
        rec = str(pr.get("recommendation") or "major_revision")
        if rec not in _allowed_recs:
            rec = "major_revision"
        critique = pr.get("critique")
        if not isinstance(critique, dict):
            critique = {}
        snapshot = pr.get("manuscript_snapshot")
        if not isinstance(snapshot, dict):
            snapshot = None
        file_ref = pr.get("source_file_ref")
        if not isinstance(file_ref, dict):
            file_ref = None
        session.add(PeerReview(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            source_type=src,
            source_file_ref=file_ref,
            source_title=str(pr.get("source_title") or "Imported peer review")[:1000],
            manuscript_snapshot=snapshot,
            critique=critique,
            recommendation=rec,
            ai_model=str(pr.get("ai_model") or "imported")[:64],
            status=str(pr.get("status") or "completed")[:32],
            error=pr.get("error"),
        ))
        counts["peer_reviews"] += 1
    if counts["peer_reviews"]:
        await session.flush()

    review_in = bundle.get("review")
    new_review_id: str | None = None
    if isinstance(review_in, dict):
        new_review_id = _new_id()
        session.add(Review(
            id=new_review_id,
            user_id=target_user_id,
            project_id=new_project_id,
            pico_population=review_in.get("pico_population"),
            pico_intervention=review_in.get("pico_intervention"),
            pico_comparator=review_in.get("pico_comparator"),
            pico_outcome=review_in.get("pico_outcome"),
            eligibility_inclusion=review_in.get("eligibility_inclusion"),
            eligibility_exclusion=review_in.get("eligibility_exclusion"),
            tool_per_study=bool(review_in.get("tool_per_study", False)),
        ))
        await session.flush()
        counts["reviews"] = 1

    if new_review_id is not None:
        for s in bundle.get("search_records") or []:
            session.add(SearchRecord(
                id=_new_id(),
                user_id=target_user_id,
                review_id=new_review_id,
                database_name=s.get("database_name") or "",
                query_string=s.get("query_string") or "",
                date_searched=_parse_dt(s.get("date_searched")) or datetime.utcnow(),
                n_results=s.get("n_results") or 0,
                notes=s.get("notes"),
            ))
            counts["search_records"] += 1

        for sc in bundle.get("screening_records") or []:
            new_art = article_map.get(sc.get("article_id"))
            if new_art is None:
                continue
            session.add(ScreeningRecord(
                id=_new_id(),
                user_id=target_user_id,
                review_id=new_review_id,
                article_id=new_art,
                stage=sc.get("stage") or "title_abstract",
                decision=sc.get("decision") or "pending",
                exclusion_category=sc.get("exclusion_category"),
                reason=sc.get("reason"),
                reviewer_id=sc.get("reviewer_id"),
                ai_suggestion=sc.get("ai_suggestion"),
                decided_at=_parse_dt(sc.get("decided_at")),
            ))
            counts["screening_records"] += 1

        for rb in bundle.get("rob_assessments") or []:
            new_art = article_map.get(rb.get("article_id"))
            if new_art is None:
                continue
            session.add(RobAssessment(
                id=_new_id(),
                user_id=target_user_id,
                review_id=new_review_id,
                article_id=new_art,
                tool=rb.get("tool") or "rob2",
                domain_answers=rb.get("domain_answers") or {},
                overall_auto=rb.get("overall_auto") or "some_concerns",
                overall_override=rb.get("overall_override"),
                notes=rb.get("notes"),
            ))
            counts["rob_assessments"] += 1

        for ex in bundle.get("extraction_records") or []:
            new_art = article_map.get(ex.get("article_id"))
            if new_art is None:
                continue
            session.add(ExtractionRecord(
                id=_new_id(),
                user_id=target_user_id,
                review_id=new_review_id,
                article_id=new_art,
                fields=ex.get("fields") or {},
            ))
            counts["extraction_records"] += 1

        if any(counts[k] for k in (
            "search_records", "screening_records", "rob_assessments", "extraction_records"
        )):
            await session.flush()

    # ── Figures (Phase 8.7) ────────────────────────────────────────────
    for fig in bundle.get("figures") or []:
        ref = fig.get("file_ref") or {}
        if not ref:
            # File payloads aren't carried in the bundle — keep a "missing"
            # marker so the figures UI can render a placeholder.
            ref = {"backend": "missing", "key": ""}
        session.add(Figure(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            file_ref=ref,
            file_type=fig.get("file_type") or "image/png",
            figure_number=fig.get("figure_number") or (counts["figures"] + 1),
            caption=fig.get("caption") or "",
            alt_text=fig.get("alt_text") or "",
            width_px=fig.get("width_px"),
            height_px=fig.get("height_px"),
            byte_size=fig.get("byte_size") or 0,
        ))
        counts["figures"] += 1
    if counts["figures"]:
        await session.flush()

    # ── CONSORT data (Phase 8.7) ───────────────────────────────────────
    consort_in = bundle.get("consort_data")
    if isinstance(consort_in, dict):
        session.add(ConsortData(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            enrollment_assessed=consort_in.get("enrollment_assessed"),
            enrollment_excluded=consort_in.get("enrollment_excluded"),
            enrollment_excluded_reasons=consort_in.get("enrollment_excluded_reasons"),
            randomised=consort_in.get("randomised"),
            allocated_intervention=consort_in.get("allocated_intervention"),
            allocated_control=consort_in.get("allocated_control"),
            intervention_received=consort_in.get("intervention_received"),
            control_received=consort_in.get("control_received"),
            intervention_lost_followup=consort_in.get("intervention_lost_followup"),
            control_lost_followup=consort_in.get("control_lost_followup"),
            intervention_discontinued=consort_in.get("intervention_discontinued"),
            control_discontinued=consort_in.get("control_discontinued"),
            intervention_analysed=consort_in.get("intervention_analysed"),
            control_analysed=consort_in.get("control_analysed"),
        ))
        await session.flush()
        counts["consort_data"] = 1

    # ── Meta-analyses + inputs (Phase 7.5) ─────────────────────────────
    meta_map: dict[str, str] = {}
    if new_review_id is not None:
        for m in bundle.get("meta_analyses") or []:
            new_meta_id = _new_id()
            session.add(MetaAnalysis(
                id=new_meta_id,
                user_id=target_user_id,
                review_id=new_review_id,
                title=m.get("title"),
                effect_metric=m.get("effect_metric") or "md",
                model=m.get("model") or "fixed",
                subgroup_variable=m.get("subgroup_variable"),
                pooled_estimate=m.get("pooled_estimate"),
                pooled_se=m.get("pooled_se"),
                ci_low=m.get("ci_low"),
                ci_high=m.get("ci_high"),
                z_value=m.get("z_value"),
                p_value=m.get("p_value"),
                q_value=m.get("q_value"),
                q_df=m.get("q_df"),
                q_p=m.get("q_p"),
                i2=m.get("i2"),
                tau2=m.get("tau2"),
                subgroup_summary=m.get("subgroup_summary"),
                ai_interpretation=m.get("ai_interpretation"),
                status=m.get("status") or "draft",
            ))
            if m.get("id"):
                meta_map[m["id"]] = new_meta_id
            counts["meta_analyses"] += 1
        if counts["meta_analyses"]:
            await session.flush()

        for mi in bundle.get("meta_inputs") or []:
            new_meta = meta_map.get(mi.get("meta_id"))
            new_art = article_map.get(mi.get("article_id"))
            if new_meta is None or new_art is None:
                continue  # orphan input
            session.add(MetaInput(
                id=_new_id(),
                user_id=target_user_id,
                meta_id=new_meta,
                article_id=new_art,
                study_label=mi.get("study_label"),
                subgroup=mi.get("subgroup"),
                mean_a=mi.get("mean_a"),
                sd_a=mi.get("sd_a"),
                n_a=mi.get("n_a"),
                mean_b=mi.get("mean_b"),
                sd_b=mi.get("sd_b"),
                n_b=mi.get("n_b"),
                events_a=mi.get("events_a"),
                n_a_total=mi.get("n_a_total"),
                events_b=mi.get("events_b"),
                n_b_total=mi.get("n_b_total"),
                log_hr=mi.get("log_hr"),
                se_log_hr=mi.get("se_log_hr"),
                hr=mi.get("hr"),
                hr_ci_low=mi.get("hr_ci_low"),
                hr_ci_high=mi.get("hr_ci_high"),
                r=mi.get("r"),
                n_r=mi.get("n_r"),
            ))
            counts["meta_inputs"] += 1
        if counts["meta_inputs"]:
            await session.flush()

        # ── GRADE assessments (Phase 14) ───────────────────────────────
        # Drop the meta_id link if the source meta wasn't carried in this
        # bundle — otherwise we'd point at a meta from a different project.
        seen_outcomes: set[str] = set()
        for g in bundle.get("grade_assessments") or []:
            outcome = (g.get("outcome_label") or "").strip()
            if not outcome:
                continue
            if outcome in seen_outcomes:
                # UNIQUE(review_id, outcome_label) — drop duplicates instead
                # of failing the whole import.
                continue
            seen_outcomes.add(outcome)
            new_meta = meta_map.get(g.get("meta_id")) if g.get("meta_id") else None
            session.add(GradeAssessment(
                id=_new_id(),
                user_id=target_user_id,
                project_id=new_project_id,
                review_id=new_review_id,
                meta_id=new_meta,
                outcome_label=outcome,
                starting_certainty=g.get("starting_certainty") or "high",
                domain_risk_of_bias=g.get("domain_risk_of_bias") or "not_serious",
                domain_inconsistency=g.get("domain_inconsistency") or "not_serious",
                domain_indirectness=g.get("domain_indirectness") or "not_serious",
                domain_imprecision=g.get("domain_imprecision") or "not_serious",
                domain_publication_bias=g.get("domain_publication_bias") or "not_serious",
                upgrade_large_effect=g.get("upgrade_large_effect") or "none",
                upgrade_dose_response=g.get("upgrade_dose_response") or "none",
                upgrade_confounders_against=g.get("upgrade_confounders_against") or "none",
                certainty=g.get("certainty") or "low",
                notes=g.get("notes"),
            ))
            counts["grade_assessments"] += 1
        if counts["grade_assessments"]:
            await session.flush()

        # ── PROSPERO draft (Phase 14) ──────────────────────────────────
        pros_in = bundle.get("prospero_draft")
        if isinstance(pros_in, dict):
            fields_in = pros_in.get("fields")
            if not isinstance(fields_in, dict):
                fields_in = {}
            session.add(ProsperoDraft(
                id=_new_id(),
                user_id=target_user_id,
                project_id=new_project_id,
                review_id=new_review_id,
                fields=fields_in,
            ))
            await session.flush()
            counts["prospero_draft"] = 1

        # ── Living-review job (Phase 15) ───────────────────────────────
        # Hits are intentionally NOT carried — they reset on import so the
        # imported project starts fresh against the live PubMed corpus.
        # The lease_holder is also dropped so the new instance can claim it.
        living_in = bundle.get("living_review_job")
        if isinstance(living_in, dict):
            schedule = living_in.get("schedule") or "weekly"
            if schedule not in {"daily", "weekly", "monthly"}:
                schedule = "weekly"
            session.add(LivingReviewJob(
                id=_new_id(),
                user_id=target_user_id,
                project_id=new_project_id,
                review_id=new_review_id,
                pubmed_query=(living_in.get("pubmed_query") or "").strip()
                    or "imported query",
                schedule=schedule,
                enabled=bool(living_in.get("enabled", True)),
                last_run_at=None,
                last_hit_count=None,
                lease_holder=None,
            ))
            await session.flush()
            counts["living_review_job"] = 1

    # ── ICMJE front-matter (Phase 10) ──────────────────────────────────
    author_map: dict[str, str] = {}
    incoming_authors = bundle.get("authors") or []
    # Sort by position so newly-minted authors keep their relative order.
    incoming_authors = sorted(
        incoming_authors, key=lambda a: a.get("position") or 0
    )
    correspondings_remaining = 1  # at most one is_corresponding per project
    for author in incoming_authors:
        new_aid = _new_id()
        is_corr = bool(author.get("is_corresponding"))
        # Defensive: even if the bundle smuggles two corresponding authors,
        # the receiving project must respect the at-most-one invariant.
        if is_corr and correspondings_remaining <= 0:
            is_corr = False
        if is_corr:
            correspondings_remaining -= 1
        session.add(Author(
            id=new_aid,
            user_id=target_user_id,
            project_id=new_project_id,
            full_name=author.get("full_name") or "Unnamed",
            given_name=author.get("given_name") or "",
            family_name=author.get("family_name") or "",
            orcid=author.get("orcid"),
            email=author.get("email"),
            is_corresponding=is_corr,
            position=author.get("position") or (counts["authors"] + 1),
        ))
        if author.get("id"):
            author_map[author["id"]] = new_aid
        counts["authors"] += 1
    if counts["authors"]:
        await session.flush()

    affiliation_map: dict[str, str] = {}
    incoming_affiliations = sorted(
        bundle.get("affiliations") or [],
        key=lambda a: a.get("position") or 0,
    )
    for aff in incoming_affiliations:
        new_aff_id = _new_id()
        session.add(Affiliation(
            id=new_aff_id,
            user_id=target_user_id,
            project_id=new_project_id,
            name=aff.get("name") or "Unnamed",
            address=aff.get("address"),
            city=aff.get("city"),
            country=aff.get("country"),
            position=aff.get("position") or (counts["affiliations"] + 1),
        ))
        if aff.get("id"):
            affiliation_map[aff["id"]] = new_aff_id
        counts["affiliations"] += 1
    if counts["affiliations"]:
        await session.flush()

    # m2m links — drop orphans where either side wasn't carried in the bundle.
    seen_links: set[tuple[str, str]] = set()
    for link in bundle.get("author_affiliations") or []:
        new_aid = author_map.get(link.get("author_id"))
        new_aff = affiliation_map.get(link.get("affiliation_id"))
        if new_aid is None or new_aff is None:
            continue
        key = (new_aid, new_aff)
        if key in seen_links:
            continue  # avoid UNIQUE collision on duplicate links
        seen_links.add(key)
        session.add(AuthorAffiliation(
            id=_new_id(),
            user_id=target_user_id,
            author_id=new_aid,
            affiliation_id=new_aff,
            position=link.get("position") or 1,
        ))
        counts["author_affiliations"] += 1
    if counts["author_affiliations"]:
        await session.flush()

    seen_contributions: set[tuple[str, str]] = set()
    for c in bundle.get("contributions") or []:
        new_aid = author_map.get(c.get("author_id"))
        role = c.get("role")
        if new_aid is None or not role:
            continue
        key = (new_aid, role)
        if key in seen_contributions:
            continue
        seen_contributions.add(key)
        session.add(Contribution(
            id=_new_id(),
            user_id=target_user_id,
            author_id=new_aid,
            role=role,
        ))
        counts["contributions"] += 1
    if counts["contributions"]:
        await session.flush()

    fm_in = bundle.get("project_frontmatter")
    if isinstance(fm_in, dict):
        session.add(ProjectFrontmatter(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            funding_statement=fm_in.get("funding_statement"),
            funders=fm_in.get("funders") or [],
            ethics_irb=fm_in.get("ethics_irb"),
            ethics_approval_number=fm_in.get("ethics_approval_number"),
            ethics_consent=fm_in.get("ethics_consent"),
            conflicts_statement=fm_in.get("conflicts_statement"),
            structured_abstract_enabled=bool(
                fm_in.get("structured_abstract_enabled")
            ),
            structured_abstract=fm_in.get("structured_abstract") or {
                "background": "",
                "methods": "",
                "results": "",
                "conclusions": "",
            },
        ))
        await session.flush()
        counts["project_frontmatter"] = 1

    # ── Manuscript snapshots (Phase 11) ────────────────────────────────
    # Re-key on `label` collisions: if a snapshot with the same label already
    # exists for the new project (e.g. on importing into a populated user),
    # suffix with " (imported)" to dodge the UNIQUE (project, user, label)
    # constraint without dropping the row.
    seen_labels: set[str] = set()
    for snap in bundle.get("manuscript_snapshots") or []:
        raw_label = (snap.get("label") or "Imported").strip() or "Imported"
        label = raw_label
        suffix = 0
        while label in seen_labels:
            suffix += 1
            label = f"{raw_label} (imported {suffix})"
        seen_labels.add(label)
        session.add(ManuscriptSnapshot(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            label=label,
            description=snap.get("description"),
            full_blob=snap.get("full_blob") or {},
        ))
        counts["manuscript_snapshots"] += 1
    if counts["manuscript_snapshots"]:
        await session.flush()

    # ── Cover letter (Phase 12) ────────────────────────────────────────
    cl_in = bundle.get("cover_letter")
    if isinstance(cl_in, dict):
        session.add(CoverLetter(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            target_journal=cl_in.get("target_journal"),
            novelty_points=cl_in.get("novelty_points") or [],
            body_html=cl_in.get("body_html") or "",
            ai_model=cl_in.get("ai_model"),
        ))
        await session.flush()
        counts["cover_letter"] = 1

    # ── Reviewer responses (Phase 12) ──────────────────────────────────
    for rr in bundle.get("reviewer_responses") or []:
        label = (rr.get("reviewer_label") or "Reviewer").strip() or "Reviewer"
        raw_comments = rr.get("comments") or []
        # Defensive normalisation — drop any rows that aren't a {comment_text,
        # response_html} object so the JSON column stays a clean list.
        norm_comments: list[dict] = []
        for c in raw_comments:
            if not isinstance(c, dict):
                continue
            text = (c.get("comment_text") or "").strip()
            if not text:
                continue
            norm_comments.append({
                "comment_text": text,
                "response_html": c.get("response_html") or "",
            })
        session.add(ReviewerResponse(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            reviewer_label=label,
            comments=norm_comments,
        ))
        counts["reviewer_responses"] += 1
    if counts["reviewer_responses"]:
        await session.flush()

    # ── Phase 13.5 — Dataset plots ─────────────────────────────────────
    for plot in bundle.get("dataset_plots") or []:
        new_ds = dataset_map.get(plot.get("dataset_id"))
        if new_ds is None:
            continue
        spec = plot.get("spec")
        if not isinstance(spec, dict):
            continue
        session.add(DatasetPlot(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            dataset_id=new_ds,
            title=plot.get("title") or "",
            spec=spec,
            png_data_uri=plot.get("png_data_uri") or "",
        ))
        counts["dataset_plots"] += 1
    if counts["dataset_plots"]:
        await session.flush()

    # ── Phase 13.5 — Analysis plans + runs ────────────────────────────
    plan_map: dict[str, str] = {}
    for plan in bundle.get("analysis_plans") or []:
        new_plan_id = _new_id()
        steps = plan.get("steps")
        if not isinstance(steps, list):
            steps = []
        session.add(AnalysisPlan(
            id=new_plan_id,
            user_id=target_user_id,
            project_id=new_project_id,
            name=plan.get("name") or "Imported plan",
            description=plan.get("description"),
            steps=steps,
        ))
        if plan.get("id"):
            plan_map[plan["id"]] = new_plan_id
        counts["analysis_plans"] += 1
    if counts["analysis_plans"]:
        await session.flush()

    for run in bundle.get("analysis_plan_runs") or []:
        new_plan = plan_map.get(run.get("plan_id"))
        if new_plan is None:
            continue
        new_ds = dataset_map.get(run.get("dataset_id"))
        session.add(AnalysisPlanRun(
            id=_new_id(),
            user_id=target_user_id,
            plan_id=new_plan,
            dataset_id=new_ds or (run.get("dataset_id") or ""),
            result_blob=run.get("result_blob") or {},
            status=run.get("status") or "ok",
            error=run.get("error"),
        ))
        counts["analysis_plan_runs"] += 1
    if counts["analysis_plan_runs"]:
        await session.flush()

    # ── MeSH cache (Phase 19) ──────────────────────────────────────────
    mesh_map: dict[str, str] = {}
    seen_mesh_ui: set[str] = set()
    for mt in bundle.get("mesh_terms") or []:
        ui = (mt.get("descriptor_ui") or "").strip()
        if not ui or ui in seen_mesh_ui:
            continue
        seen_mesh_ui.add(ui)
        new_mt_id = _new_id()
        session.add(MeshTerm(
            id=new_mt_id,
            user_id=target_user_id,
            project_id=new_project_id,
            descriptor_ui=ui,
            descriptor_name=(mt.get("descriptor_name") or ui)[:500],
            scope_note=mt.get("scope_note"),
            tree_numbers=list(mt.get("tree_numbers") or []),
            entry_terms=list(mt.get("entry_terms") or []),
            source=mt.get("source") or "ncbi_lookup",
        ))
        if mt.get("id"):
            mesh_map[mt["id"]] = new_mt_id
        counts["mesh_terms"] += 1
    if counts["mesh_terms"]:
        await session.flush()

    # ── Search strategies (Phase 19) — two-pass to remap translated_from_id
    if new_review_id is not None:
        strategy_map: dict[str, str] = {}
        pending_translated: list[tuple[str, str | None]] = []
        for ss in bundle.get("search_strategies") or []:
            new_ss_id = _new_id()
            # Remap mesh_term_ids through the cache we just imported.
            mesh_ids = list(ss.get("mesh_term_ids") or [])
            mesh_ids = [mesh_map.get(m, m) for m in mesh_ids if m]
            db_name = (ss.get("database") or "PubMed")
            if db_name not in {"PubMed", "Embase", "Cochrane",
                               "Web of Science", "Scopus", "Other"}:
                db_name = "Other"
            session.add(SearchStrategy(
                id=new_ss_id,
                user_id=target_user_id,
                project_id=new_project_id,
                review_id=new_review_id,
                name=(ss.get("name") or "Imported strategy")[:255],
                database=db_name,
                query_text=ss.get("query_text") or "",
                mesh_term_ids=mesh_ids,
                translated_from_id=None,  # patched below
                is_locked=bool(ss.get("is_locked", False)),
                warnings=ss.get("warnings"),
            ))
            if ss.get("id"):
                strategy_map[ss["id"]] = new_ss_id
            pending_translated.append((new_ss_id, ss.get("translated_from_id")))
            counts["search_strategies"] += 1
        if counts["search_strategies"]:
            await session.flush()
            for new_ss_id, old_src in pending_translated:
                if not old_src:
                    continue
                mapped = strategy_map.get(old_src)
                if mapped is None:
                    continue
                row = await session.get(SearchStrategy, new_ss_id)
                if row is not None:
                    row.translated_from_id = mapped
            await session.flush()

        # ── Narrative synthesis entries (Phase 19) ─────────────────────
        for ns in bundle.get("narrative_synthesis_entries") or []:
            citations = list(ns.get("study_citations") or [])
            # Remap article_ids through article_map; drop any unknown ones.
            citations = [article_map.get(a) for a in citations if a]
            citations = [c for c in citations if c]
            session.add(NarrativeSynthesisEntry(
                id=_new_id(),
                user_id=target_user_id,
                review_id=new_review_id,
                outcome_label=(ns.get("outcome_label") or "Outcome")[:255],
                instrument=(ns.get("instrument") or "Instrument")[:255],
                range_text=ns.get("range_text"),
                direction=(ns.get("direction") or "neutral"),
                narrative_html=ns.get("narrative_html") or "",
                study_citations=citations,
            ))
            counts["narrative_synthesis_entries"] += 1
        if counts["narrative_synthesis_entries"]:
            await session.flush()

        # ── Outcome instruments (Phase 19) ─────────────────────────────
        for oi in bundle.get("outcome_instruments") or []:
            study_values = []
            for cell in oi.get("study_values") or []:
                if not isinstance(cell, dict):
                    continue
                old_aid = cell.get("article_id")
                new_aid = article_map.get(old_aid) if old_aid else None
                if new_aid is None:
                    continue
                study_values.append({
                    "article_id": new_aid,
                    "group_label": cell.get("group_label", ""),
                    "value": cell.get("value"),
                    "sd_or_ci": cell.get("sd_or_ci"),
                    "n": cell.get("n"),
                })
            session.add(OutcomeInstrument(
                id=_new_id(),
                user_id=target_user_id,
                review_id=new_review_id,
                outcome_label=(oi.get("outcome_label") or "Outcome")[:255],
                instrument_name=(oi.get("instrument_name") or "Instrument")[:255],
                score_range_low=oi.get("score_range_low"),
                score_range_high=oi.get("score_range_high"),
                mid=oi.get("mid"),
                study_values=study_values,
            ))
            counts["outcome_instruments"] += 1
        if counts["outcome_instruments"]:
            await session.flush()

    for cm in bundle.get("manuscript_comments") or []:
        section_name = cm.get("section_name") or "Introduction"
        anchor_start = int(cm.get("anchor_start") or 0)
        anchor_end = int(cm.get("anchor_end") or anchor_start)
        body_text = cm.get("body")
        if not body_text:
            continue
        session.add(ManuscriptComment(
            id=_new_id(),
            user_id=target_user_id,
            project_id=new_project_id,
            section_name=section_name,
            anchor_start=anchor_start,
            anchor_end=anchor_end,
            body=body_text,
            resolved=bool(cm.get("resolved")),
        ))
        counts["manuscript_comments"] += 1
    if counts["manuscript_comments"]:
        await session.flush()

    return counts
