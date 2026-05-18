"""Phase 8.6 — Article.pmid + Article.source schema additions."""
from __future__ import annotations

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from research_api.db.models import Article, new_id


async def _seed_project(session: AsyncSession, *, user_id: str = "u1") -> str:
    pid = new_id()
    await session.execute(
        text(
            "INSERT INTO projects (id, user_id, title, study_type, citation_style,"
            " ai_provider) VALUES (:id, :u, 'P', 'rct', 'vancouver', 'gemini')"
        ),
        {"id": pid, "u": user_id},
    )
    await session.commit()
    return pid


@pytest.mark.asyncio
async def test_article_pmid_persists_and_is_indexed(session: AsyncSession):
    pid = await _seed_project(session)
    a = Article(
        id=new_id(),
        user_id="u1",
        project_id=pid,
        title="Test",
        pmid="12345678",
        source="pubmed",
    )
    session.add(a)
    await session.commit()

    # PMID query works
    row = (
        await session.execute(select(Article).where(Article.pmid == "12345678"))
    ).scalar_one_or_none()
    assert row is not None
    assert row.source == "pubmed"

    # Index exists (SQLite reports it in sqlite_master)
    rs = await session.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_articles_pmid'")
    )
    assert rs.scalar_one_or_none() == "ix_articles_pmid"


@pytest.mark.asyncio
async def test_article_source_defaults_to_upload_when_omitted(session: AsyncSession):
    """The ORM default is 'upload' — inserts that don't set source land as 'upload'."""
    pid = await _seed_project(session)
    a = Article(
        id=new_id(),
        user_id="u1",
        project_id=pid,
        title="Test",
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    assert a.source == "upload"


@pytest.mark.asyncio
async def test_article_source_accepts_known_values(session: AsyncSession):
    """All known source enum values round-trip through the column."""
    pid = await _seed_project(session)
    for src in ("upload", "doi", "pubmed", "ris", "bibtex", "manual"):
        a = Article(
            id=new_id(),
            user_id="u1",
            project_id=pid,
            title=f"T-{src}",
            source=src,
        )
        session.add(a)
    await session.commit()

    rows = (await session.execute(select(Article))).scalars().all()
    sources = sorted(r.source for r in rows)
    assert sources == ["bibtex", "doi", "manual", "pubmed", "ris", "upload"]
