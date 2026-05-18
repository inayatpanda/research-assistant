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
        "datasets": 0, "dataset_variables": 0,
        "analyses": 0, "analysis_results": 0,
        "reviews": 0, "search_records": 0, "screening_records": 0,
        "rob_assessments": 0, "extraction_records": 0,
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
        ))
        if ds.get("id"):
            dataset_map[ds["id"]] = new_ds_id
        counts["datasets"] += 1
    if counts["datasets"]:
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

    return counts
