"""Phase 12 — Bundle export/import round-trip for cover_letter + reviewer_responses.

Mirrors the Phase 10/11 round-trip tests: build an in-memory bundle holding
both rows, import as a different user, and confirm the counts + content
survive.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from research_api.db.models import CoverLetter, Project, ReviewerResponse
from research_api.services.export.bundle_export import (
    BundleInputs,
    build_bundle,
)
from research_api.services.export.bundle_import import import_bundle


def _make_project_row() -> Project:
    return Project(
        id="proj-orig",
        user_id="user-a",
        title="Imported Project",
        study_type="Outcome Study",
        citation_style="vancouver",
        ai_provider="gemini",
    )


@pytest.mark.asyncio
async def test_round_trip_carries_cover_letter(session) -> None:
    proj = _make_project_row()
    cover = CoverLetter(
        id="cl-1",
        user_id="user-a",
        project_id=proj.id,
        target_journal="jbjs",
        novelty_points=["First MC trial", "10-yr follow-up"],
        body_html="<p>Dear Editor,</p>",
        ai_model="gemini-2.5-flash",
    )
    bundle = build_bundle(BundleInputs(project=proj, cover_letter=cover))

    counts = await import_bundle(
        bundle, target_user_id="user-b", session=session
    )
    assert counts["cover_letter"] == 1
    new_proj = (await session.execute(select(Project))).scalar_one()
    imported = (
        await session.execute(
            select(CoverLetter).where(
                CoverLetter.project_id == new_proj.id,
                CoverLetter.user_id == "user-b",
            )
        )
    ).scalar_one()
    assert imported.target_journal == "jbjs"
    assert imported.novelty_points == ["First MC trial", "10-yr follow-up"]
    assert imported.body_html == "<p>Dear Editor,</p>"
    assert imported.ai_model == "gemini-2.5-flash"
    # The imported user_id is the *target*, not the bundle's original.
    assert imported.user_id == "user-b"


@pytest.mark.asyncio
async def test_round_trip_carries_reviewer_responses(session) -> None:
    proj = _make_project_row()
    rr = ReviewerResponse(
        id="rr-1",
        user_id="user-a",
        project_id=proj.id,
        reviewer_label="Reviewer 2",
        comments=[
            {"comment_text": "Add power calc.", "response_html": "<p>Done.</p>"},
            {"comment_text": "Fix typo.", "response_html": "<p>Fixed.</p>"},
        ],
    )
    bundle = build_bundle(
        BundleInputs(project=proj, reviewer_responses=[rr])
    )

    counts = await import_bundle(
        bundle, target_user_id="user-b", session=session
    )
    assert counts["reviewer_responses"] == 1
    new_proj = (await session.execute(select(Project))).scalar_one()
    imported = (
        await session.execute(
            select(ReviewerResponse).where(
                ReviewerResponse.project_id == new_proj.id,
                ReviewerResponse.user_id == "user-b",
            )
        )
    ).scalar_one()
    assert imported.reviewer_label == "Reviewer 2"
    assert len(imported.comments) == 2
    assert imported.comments[0]["comment_text"] == "Add power calc."


@pytest.mark.asyncio
async def test_round_trip_drops_blank_comment_rows(session) -> None:
    """Defence-in-depth: a bundle smuggling a comments row with blank
    `comment_text` is dropped on import."""
    proj = _make_project_row()
    rr = ReviewerResponse(
        id="rr-1",
        user_id="user-a",
        project_id=proj.id,
        reviewer_label="R1",
        comments=[
            {"comment_text": "   ", "response_html": "evil"},
            {"comment_text": "ok", "response_html": ""},
        ],
    )
    bundle = build_bundle(
        BundleInputs(project=proj, reviewer_responses=[rr])
    )
    await import_bundle(bundle, target_user_id="user-b", session=session)
    new_proj = (await session.execute(select(Project))).scalar_one()
    imported = (
        await session.execute(
            select(ReviewerResponse).where(
                ReviewerResponse.project_id == new_proj.id,
            )
        )
    ).scalar_one()
    # Only the non-blank row survives.
    assert len(imported.comments) == 1
    assert imported.comments[0]["comment_text"] == "ok"
