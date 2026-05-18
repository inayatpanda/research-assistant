"""End-to-end tests for /api/projects/{pid}/bibliography."""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article, ManuscriptSection


async def _make_project(
    client, title="Bib P", style: str = "vancouver",
) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Outcome Study", "citation_style": style},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(
    *, title: str, project_id: str, year: int = 2024, journal: str = "J",
    authors: list[str] | None = None, user_id: str = "local-user",
) -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            user_id=user_id, project_id=project_id, title=title,
            authors=authors or ["Doe J"], year=year, journal=journal,
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


async def _seed_section(
    *, project_id: str, section_name: str, content: str,
    user_id: str = "local-user",
) -> None:
    container = get_container()
    async with container.session_factory() as session:
        s = ManuscriptSection(
            user_id=user_id, project_id=project_id,
            section_name=section_name, content=content,
            word_count=len(content.split()),
        )
        session.add(s)
        await session.commit()


@pytest.mark.asyncio
async def test_bibliography_returns_entries_in_first_cite_order(client):
    pid = await _make_project(client)
    a1 = await _seed_article(title="Alpha", project_id=pid)
    a2 = await _seed_article(title="Beta", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{a2}] [CITE_{a1}]</p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["style"] == "vancouver"
    assert [e["article_id"] for e in body["entries"]] == [a2, a1]
    assert [e["number"] for e in body["entries"]] == [1, 2]


@pytest.mark.asyncio
async def test_bibliography_dedupes(client):
    pid = await _make_project(client)
    a1 = await _seed_article(title="Alpha", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{a1}] [CITE_{a1}]</p>",
    )
    await _seed_section(
        project_id=pid, section_name="Methodology",
        content=f"<p>[CITE_{a1}]</p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography")
    assert r.status_code == 200
    assert len(r.json()["entries"]) == 1


@pytest.mark.asyncio
async def test_bibliography_404_for_missing_project(client):
    r = await client.get("/api/projects/missing/bibliography")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_bibliography_respects_style_query_param(client):
    pid = await _make_project(client, style="vancouver")
    a1 = await _seed_article(
        title="Alpha", project_id=pid, authors=["John Doe"],
    )
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{a1}]</p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography?style=apa")
    assert r.status_code == 200
    body = r.json()
    assert body["style"] == "apa"
    # APA entries start with the author's surname-initial form, not a number.
    assert body["entries"][0]["formatted_entry"].startswith("Doe, J.")


@pytest.mark.asyncio
async def test_bibliography_defaults_to_project_style(client):
    pid = await _make_project(client, style="apa")
    a1 = await _seed_article(title="Alpha", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{a1}]</p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography")
    assert r.status_code == 200
    assert r.json()["style"] == "apa"


@pytest.mark.asyncio
async def test_bibliography_records_first_section(client):
    pid = await _make_project(client)
    a1 = await _seed_article(title="Alpha", project_id=pid)
    a2 = await _seed_article(title="Beta", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Methodology",
        content=f"<p>[CITE_{a2}]</p>",
    )
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{a1}]</p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography")
    body = r.json()
    sections_by_id = {e["article_id"]: e["first_section"] for e in body["entries"]}
    assert sections_by_id[a1] == "Introduction"
    assert sections_by_id[a2] == "Methodology"


@pytest.mark.asyncio
async def test_bibliography_rejects_invalid_style(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/bibliography?style=mla")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_bibliography_ieee_style_uses_brackets(client):
    pid = await _make_project(client)
    a1 = await _seed_article(title="Alpha", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{a1}]</p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography?style=ieee")
    body = r.json()
    assert body["entries"][0]["formatted_entry"].startswith("[1]")


@pytest.mark.asyncio
async def test_bibliography_empty_when_no_citations(client):
    pid = await _make_project(client)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content="<p>No citations here.</p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography")
    assert r.status_code == 200
    assert r.json()["entries"] == []


@pytest.mark.asyncio
async def test_bibliography_drops_unknown_article_ids(client):
    pid = await _make_project(client)
    a1 = await _seed_article(title="Alpha", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{a1}] [CITE_xnope] </p>",
    )
    r = await client.get(f"/api/projects/{pid}/bibliography")
    assert r.status_code == 200
    body = r.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["article_id"] == a1
