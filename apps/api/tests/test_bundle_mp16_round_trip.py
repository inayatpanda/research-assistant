"""MP16 — Bundle export/import round-trip for the new article + project fields.

The ``_row_to_dict`` exporter reflects every column from
``__table__.columns``, so the new ``articles.reference_type``,
``articles.url``, and ``projects.inline_citation_mode`` fields should
round-trip automatically. This regression test pins that behaviour.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article, Project, new_id
from research_api.services.export.bundle_export import BundleInputs, build_bundle


@pytest.mark.asyncio
async def test_bundle_export_includes_mp16_fields(session):
    project = Project(
        id=new_id(),
        user_id="u1",
        title="MP16 round-trip",
        study_type="Outcome Study",
        citation_style="lancet",
        ai_provider="gemini",
        inline_citation_mode="superscript_numeric",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    article = Article(
        id=new_id(),
        user_id="u1",
        project_id=project.id,
        title="WHO TB report",
        authors=["World Health Organization"],
        year=2024,
        reference_type="web_resource",
        url="https://who.int/tb",
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)

    bundle = build_bundle(
        BundleInputs(project=project, articles=[article])
    )
    assert bundle["project"]["inline_citation_mode"] == "superscript_numeric"
    assert bundle["articles"][0]["reference_type"] == "web_resource"
    assert bundle["articles"][0]["url"] == "https://who.int/tb"


@pytest.mark.asyncio
async def test_bundle_export_defaults_for_unset_mp16_fields(session):
    """Projects without an explicit inline_citation_mode export the default
    ``bracket_numeric`` value (server default applies)."""
    project = Project(
        id=new_id(),
        user_id="u1",
        title="Defaults project",
        study_type="Outcome Study",
        citation_style="vancouver",
        ai_provider="gemini",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    article = Article(
        id=new_id(),
        user_id="u1",
        project_id=project.id,
        title="Plain article",
        authors=["Jane Doe"],
        year=2024,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    bundle = build_bundle(BundleInputs(project=project, articles=[article]))
    assert bundle["project"]["inline_citation_mode"] == "bracket_numeric"
    assert bundle["articles"][0]["reference_type"] == "journal_article"
    assert bundle["articles"][0]["url"] is None
