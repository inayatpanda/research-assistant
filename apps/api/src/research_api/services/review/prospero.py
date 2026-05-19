"""Phase 14 (MP14) — PROSPERO registration helper.

PROSPERO requires 22 fields (per the 2018 guidance). We pre-fill what we
can from the project's review state; the user copy-pastes the rendered
text into the PROSPERO web form.

The field catalogue is a pure tuple-of-tuples so we can add/remove labels
without touching the DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Protocol


PROSPERO_FIELDS: tuple[tuple[str, str], ...] = (
    ("title", "Review title"),
    ("anticipated_start_date", "Anticipated or actual start date"),
    ("anticipated_completion_date", "Anticipated completion date"),
    ("stage", "Stage of review at time of this submission"),
    ("named_contact", "Named contact"),
    ("named_contact_email", "Named contact email"),
    ("named_contact_address", "Named contact address"),
    ("organisational_affiliation", "Organisational affiliation of the review"),
    ("review_team_members", "Review team members and their organisational affiliations"),
    ("funding_sources", "Funding sources/sponsors"),
    ("conflicts_of_interest", "Conflicts of interest"),
    ("collaborators", "Collaborators"),
    ("review_question", "Review question"),
    ("searches", "Searches"),
    ("url_to_protocol", "URL to search strategy / additional protocol"),
    ("condition_or_domain", "Condition or domain being studied"),
    ("participants", "Participants/population"),
    ("intervention_exposure", "Intervention(s), exposure(s)"),
    ("comparators_control", "Comparator(s)/control"),
    ("types_of_study", "Types of study to be included"),
    ("context", "Context"),
    ("primary_outcomes", "Main outcome(s)"),
)


class _ReviewLike(Protocol):
    id: str
    project_id: str
    pico_population: str | None
    pico_intervention: str | None
    pico_comparator: str | None
    pico_outcome: str | None
    eligibility_inclusion: str | None
    eligibility_exclusion: str | None
    created_at: datetime


class _ProjectLike(Protocol):
    title: str


class _SearchRecordLike(Protocol):
    database_name: str
    query_string: str
    date_searched: datetime


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.date().isoformat()


def default_draft(
    review: _ReviewLike,
    *,
    project: _ProjectLike | None = None,
    search_records: Iterable[_SearchRecordLike] | None = None,
) -> dict[str, str]:
    """Build the default 22-field dict for a newly-created PROSPERO draft.

    Args:
        review: the project's Review row (PICO + eligibility text).
        project: the parent Project row (used for the registry title).
        search_records: optional list of SearchRecord rows used to populate
            the ``searches`` field.

    Returns:
        Flat ``dict[str, str]`` with every key from ``PROSPERO_FIELDS`` set
        to a best-effort default (often empty string).
    """
    out: dict[str, str] = {key: "" for key, _label in PROSPERO_FIELDS}

    if project is not None:
        out["title"] = (getattr(project, "title", None) or "").strip()

    created = getattr(review, "created_at", None)
    if isinstance(created, datetime):
        start = created
        end = created + timedelta(days=183)  # ~6 months
        out["anticipated_start_date"] = _fmt_date(start)
        out["anticipated_completion_date"] = _fmt_date(end)

    out["stage"] = "Ongoing"

    inclusion = (review.eligibility_inclusion or "").strip()
    exclusion = (review.eligibility_exclusion or "").strip()
    out["types_of_study"] = inclusion
    if exclusion:
        out["context"] = f"Excluded: {exclusion}"

    out["participants"] = (review.pico_population or "").strip()
    out["intervention_exposure"] = (review.pico_intervention or "").strip()
    out["comparators_control"] = (review.pico_comparator or "").strip()
    out["primary_outcomes"] = (review.pico_outcome or "").strip()
    out["review_question"] = _compose_review_question(review)
    out["condition_or_domain"] = out["participants"]

    if search_records:
        lines: list[str] = []
        for rec in search_records:
            db = (getattr(rec, "database_name", "") or "").strip()
            q = (getattr(rec, "query_string", "") or "").strip()
            date = _fmt_date(getattr(rec, "date_searched", None))
            lines.append(f"{db} ({date}): {q}".strip())
        out["searches"] = "\n".join(lines)

    return out


def _compose_review_question(review: _ReviewLike) -> str:
    """Compose a 1-sentence PICO question from non-empty PICO parts."""
    pieces: list[str] = []
    pop = (review.pico_population or "").strip()
    iv = (review.pico_intervention or "").strip()
    comp = (review.pico_comparator or "").strip()
    out = (review.pico_outcome or "").strip()
    if pop:
        pieces.append(f"In {pop}")
    if iv:
        verb = "does"
        pieces.append(f"{verb} {iv}")
    if comp:
        pieces.append(f"compared with {comp}")
    if out:
        pieces.append(f"affect {out}")
    if not pieces:
        return ""
    return ", ".join(pieces).strip() + "?"


def format_for_export(fields: dict[str, str]) -> str:
    """Render the 22 fields as a single labelled text block.

    Output shape::

        Review title: <value>

        Anticipated or actual start date: <value>

        ...

    Designed for the researcher to copy-paste straight into PROSPERO's web
    form. Each field is labelled with its human-friendly label (not its key).
    """
    parts: list[str] = []
    for key, label in PROSPERO_FIELDS:
        value = (fields.get(key) or "").strip()
        parts.append(f"{label}: {value}".rstrip())
    return "\n\n".join(parts)
