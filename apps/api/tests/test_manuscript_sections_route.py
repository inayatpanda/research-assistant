import pytest

from research_api.container import get_container
from research_api.repositories.articles import SqliteArticleRepository
from research_api.schemas.article import ArticleCreate


async def _make_project(client) -> str:
    r = await client.post("/api/projects", json={"title": "P", "study_type": "Outcome Study"})
    return r.json()["id"]


async def _make_article(project_id: str, **kwargs) -> str:
    """Create an article via the repo bypassing file-upload requirements."""
    container = get_container()
    async with container.session_factory() as s:
        repo = SqliteArticleRepository(s)
        art = await repo.create(
            project_id=project_id,
            data=ArticleCreate(
                title=kwargs.get("title", "Anterior vs posterior THA"),
                authors=kwargs.get("authors", ["K Matsumoto", "H Suzuki"]),
                year=kwargs.get("year", 2024),
                journal=kwargs.get("journal", "JBJS Am."),
            ),
            user_id="local-user",
        )
        await s.commit()
        return art.id


@pytest.mark.asyncio
async def test_get_section_returns_empty_when_no_row(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/sections/Results")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] is None
    assert body["content"] == ""
    assert body["word_count"] == 0
    assert body["section_name"] == "Results"


@pytest.mark.asyncio
async def test_put_then_get_roundtrip(client):
    pid = await _make_project(client)
    r = await client.put(
        f"/api/projects/{pid}/sections/Results",
        json={"section_name": "Results", "content": "Anterior approach was faster."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] is not None
    assert body["content"] == "Anterior approach was faster."
    assert body["word_count"] == 4

    r2 = await client.get(f"/api/projects/{pid}/sections/Results")
    assert r2.json()["content"] == "Anterior approach was faster."


@pytest.mark.asyncio
async def test_put_updates_same_row(client):
    pid = await _make_project(client)
    first = (
        await client.put(
            f"/api/projects/{pid}/sections/Results",
            json={"section_name": "Results", "content": "v1"},
        )
    ).json()
    second = (
        await client.put(
            f"/api/projects/{pid}/sections/Results",
            json={"section_name": "Results", "content": "v2 longer content here"},
        )
    ).json()
    assert second["id"] == first["id"]
    assert second["content"] == "v2 longer content here"
    assert second["word_count"] == 4


@pytest.mark.asyncio
async def test_section_unknown_project_404s(client):
    r = await client.get("/api/projects/nope/sections/Results")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_put_section_mismatch_422(client):
    pid = await _make_project(client)
    r = await client.put(
        f"/api/projects/{pid}/sections/Results",
        json={"section_name": "Introduction", "content": "x"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invalid_section_name_422(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/sections/NotARealSection")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_section_resolves_legacy_cite_tokens(client):
    """Sections persisted before the resolver was wired (e.g. early
    meta-analysis pushes) may contain raw `[CITE_<aid>]` tokens. On GET,
    these should be rewritten into `<sup data-citation>` markup so the
    manuscript renders citations + populates the bibliography (rcm-sweep
    HIGH bug)."""
    pid = await _make_project(client)
    article_id = await _make_article(pid)
    # Persist a section with raw CITE tokens (mirrors legacy data).
    legacy = f"<p>Anterior was faster [CITE_{article_id}].</p>"
    put = await client.put(
        f"/api/projects/{pid}/sections/Results",
        json={"section_name": "Results", "content": legacy},
    )
    assert put.status_code == 200
    # GET should rewrite the token in the response (without mutating storage).
    got = await client.get(f"/api/projects/{pid}/sections/Results")
    body = got.json()
    assert "[CITE_" not in body["content"]
    assert "data-citation" in body["content"]
    assert f'data-article-id="{article_id}"' in body["content"]


@pytest.mark.asyncio
async def test_get_section_leaves_unknown_cite_tokens(client):
    """When a token references an article id that doesn't exist in the
    library, the token is left intact so the researcher sees the broken
    reference rather than a silent drop."""
    pid = await _make_project(client)
    legacy = "<p>Cited [CITE_does_not_exist].</p>"
    await client.put(
        f"/api/projects/{pid}/sections/Results",
        json={"section_name": "Results", "content": legacy},
    )
    got = await client.get(f"/api/projects/{pid}/sections/Results")
    assert "[CITE_does_not_exist]" in got.json()["content"]


@pytest.mark.asyncio
async def test_get_section_resolves_clustered_cite_tokens(client):
    """Combined `[CITE_a, CITE_b]` clusters (the form Gemini emits for >5
    studies) should also be normalised + resolved."""
    pid = await _make_project(client)
    a1 = await _make_article(pid, title="Study 1")
    a2 = await _make_article(pid, title="Study 2")
    cluster = f"<p>Pooled <em>k</em>=2 [CITE_{a1}, CITE_{a2}].</p>"
    await client.put(
        f"/api/projects/{pid}/sections/Results",
        json={"section_name": "Results", "content": cluster},
    )
    got = await client.get(f"/api/projects/{pid}/sections/Results")
    body = got.json()
    assert "[CITE_" not in body["content"]
    assert body["content"].count("data-citation") == 2
