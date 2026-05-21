"""Phase 4.5 — Route tests for /manuscript/articles-table.

Articles are seeded directly via the container's session factory because
the public articles API is upload-only (multipart) and we don't need the
PDF extraction pipeline here. Pattern matches ``test_reviews_route.py``.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article


# ── helpers ────────────────────────────────────────────────────────────


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(
    client, *, title: str = "P", study_type: str = "Systematic Review"
) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": study_type},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(
    *,
    project_id: str,
    user_id: str,
    title: str = "T",
    authors: list[str] | None = None,
    year: int | None = 2024,
    journal: str | None = "J",
    doi: str | None = None,
    study_design: str | None = None,
) -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            user_id=user_id,
            project_id=project_id,
            title=title,
            authors=authors or ["Smith J"],
            year=year,
            journal=journal,
            doi=doi,
            study_design=study_design,
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


# ── happy path + basic shape ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_articles_table_happy_path(client):
    _switch_user("local-user")
    pid = await _make_project(client)
    a1 = await _seed_article(
        project_id=pid, user_id="local-user",
        title="One", authors=["Smith J"], year=2024,
    )
    a2 = await _seed_article(
        project_id=pid, user_id="local-user",
        title="Two", authors=["Doe A", "Roe B"], year=2023,
    )

    body = {
        "article_ids": [a1, a2],
        "columns": [
            {"preset": "author_year_citation", "label": "Study"},
            {"preset": "title", "label": "Title"},
            {"preset": "journal", "label": "Journal"},
        ],
    }
    r = await client.post(
        f"/api/projects/{pid}/manuscript/articles-table", json=body
    )
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert "<table" in html and "rma-articles-table" in html
    assert f'data-article-id="{a1}"' in html
    assert f'data-article-id="{a2}"' in html
    assert "Smith (2024)" in html
    assert "Doe and Roe (2023)" in html
    assert ">One<" in html


@pytest.mark.asyncio
async def test_build_articles_table_404_unknown_project(client):
    _switch_user("local-user")
    r = await client.post(
        "/api/projects/does-not-exist/manuscript/articles-table",
        json={
            "article_ids": ["x"],
            "columns": [{"preset": "title", "label": "Title"}],
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_build_articles_table_404_when_no_articles_match(client):
    _switch_user("local-user")
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/manuscript/articles-table",
        json={
            "article_ids": ["nonexistent-id"],
            "columns": [{"preset": "title", "label": "Title"}],
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_build_articles_table_422_for_empty_article_ids(client):
    _switch_user("local-user")
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/manuscript/articles-table",
        json={
            "article_ids": [],
            "columns": [{"preset": "title", "label": "Title"}],
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_build_articles_table_422_for_empty_columns(client):
    _switch_user("local-user")
    pid = await _make_project(client)
    a1 = await _seed_article(project_id=pid, user_id="local-user")
    r = await client.post(
        f"/api/projects/{pid}/manuscript/articles-table",
        json={"article_ids": [a1], "columns": []},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_build_articles_table_synthesises_first_column(client):
    """Caller forgot to put the author-year column first — server adds it."""
    _switch_user("local-user")
    pid = await _make_project(client)
    a1 = await _seed_article(
        project_id=pid, user_id="local-user",
        authors=["Smith J"], year=2024,
    )

    body = {
        "article_ids": [a1],
        "columns": [{"preset": "title", "label": "Title"}],
    }
    r = await client.post(
        f"/api/projects/{pid}/manuscript/articles-table", json=body
    )
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert f'data-article-id="{a1}"' in html
    assert "Smith (2024)" in html


@pytest.mark.asyncio
async def test_build_articles_table_with_extraction_fills_cells(client):
    _switch_user("local-user")
    pid = await _make_project(client)
    a1 = await _seed_article(
        project_id=pid, user_id="local-user",
        authors=["Smith J"], year=2024,
    )

    body = {
        "article_id": a1,
        "fields": {
            "basic": {
                "first_author": "Smith J",
                "year": 2024,
                "country": "UK",
            },
            "population": {"n_total": 150},
            "intervention": {"name": "TKA"},
        },
    }
    r = await client.post(f"/api/projects/{pid}/reviews/extraction", json=body)
    assert r.status_code in {200, 201}, r.text

    r = await client.post(
        f"/api/projects/{pid}/manuscript/articles-table",
        json={
            "article_ids": [a1],
            "columns": [
                {"preset": "author_year_citation", "label": "Study"},
                {"preset": "country", "label": "Country"},
                {"preset": "sample_size_n", "label": "N"},
                {"preset": "intervention", "label": "Intervention"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert "UK" in html
    assert "150" in html
    assert "TKA" in html


@pytest.mark.asyncio
async def test_build_articles_table_custom_column_renders_empty_cell(client):
    _switch_user("local-user")
    pid = await _make_project(client)
    a1 = await _seed_article(project_id=pid, user_id="local-user")
    r = await client.post(
        f"/api/projects/{pid}/manuscript/articles-table",
        json={
            "article_ids": [a1],
            "columns": [
                {"preset": "author_year_citation", "label": "Study"},
                {"preset": None, "label": "My notes"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert ">My notes<" in html


# ── cross-user / cross-project isolation ───────────────────────────────


@pytest.mark.asyncio
async def test_isolation_other_users_project_404(client):
    """user-b cannot see user-a's project at all."""
    _switch_user("user-a")
    pid_a = await _make_project(client, title="A")
    _ = await _seed_article(project_id=pid_a, user_id="user-a")

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid_a}/manuscript/articles-table",
        json={
            "article_ids": ["whatever"],
            "columns": [{"preset": "title", "label": "Title"}],
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_isolation_article_id_from_other_user_filtered_out(client):
    """An article id that belongs to another user must be silently dropped."""
    _switch_user("user-a")
    pid_a = await _make_project(client, title="A")
    a_a = await _seed_article(project_id=pid_a, user_id="user-a")

    _switch_user("user-b")
    pid_b = await _make_project(client, title="B")
    a_b = await _seed_article(project_id=pid_b, user_id="user-b", title="B-only")

    # As user-b, supply user-a's article id alongside user-b's own id.
    # user-a's id falls out of the intersection — only B-only is rendered.
    r = await client.post(
        f"/api/projects/{pid_b}/manuscript/articles-table",
        json={
            "article_ids": [a_a, a_b],
            "columns": [
                {"preset": "author_year_citation", "label": "Study"},
                {"preset": "title", "label": "Title"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert f'data-article-id="{a_b}"' in html
    assert f'data-article-id="{a_a}"' not in html
    assert "B-only" in html


@pytest.mark.asyncio
async def test_isolation_article_id_from_other_project_filtered_out(client):
    """Same user, different project — article id from project A must not
    render against project B."""
    _switch_user("local-user")
    pid_a = await _make_project(client, title="A")
    pid_b = await _make_project(client, title="B")
    a_a = await _seed_article(project_id=pid_a, user_id="local-user", title="OnlyA")
    a_b = await _seed_article(project_id=pid_b, user_id="local-user", title="OnlyB")

    r = await client.post(
        f"/api/projects/{pid_b}/manuscript/articles-table",
        json={
            "article_ids": [a_a, a_b],
            "columns": [
                {"preset": "author_year_citation", "label": "Study"},
                {"preset": "title", "label": "Title"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert f'data-article-id="{a_b}"' in html
    assert f'data-article-id="{a_a}"' not in html
    assert "OnlyB" in html
    assert "OnlyA" not in html


@pytest.mark.asyncio
async def test_isolation_only_other_users_articles_returns_404(client):
    """If every requested id belongs to another user, we return 404 — no
    partial leakage."""
    _switch_user("user-a")
    pid_a = await _make_project(client, title="A")
    a_a = await _seed_article(project_id=pid_a, user_id="user-a")

    _switch_user("user-b")
    pid_b = await _make_project(client, title="B")
    r = await client.post(
        f"/api/projects/{pid_b}/manuscript/articles-table",
        json={
            "article_ids": [a_a],
            "columns": [{"preset": "title", "label": "Title"}],
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_isolation_other_users_extraction_not_leaked(client):
    """If user-a has an extraction for an article and user-b somehow had
    a same-title article, user-b's table must NOT pull user-a's extraction.

    We exercise this indirectly: user-b builds a table against user-b's
    own article, and the resulting HTML must not contain any of user-a's
    private extraction values.
    """
    _switch_user("user-a")
    pid_a = await _make_project(client, title="A")
    a_a = await _seed_article(project_id=pid_a, user_id="user-a")
    ext_body = {
        "article_id": a_a,
        "fields": {
            "basic": {
                "first_author": "Smith J",
                "year": 2024,
                "country": "SECRET-COUNTRY",
            },
            "population": {"n_total": 999},
            "intervention": {"name": "SECRET-RX"},
        },
    }
    r = await client.post(f"/api/projects/{pid_a}/reviews/extraction", json=ext_body)
    assert r.status_code in {200, 201}, r.text

    _switch_user("user-b")
    pid_b = await _make_project(client, title="B")
    a_b = await _seed_article(project_id=pid_b, user_id="user-b")
    r = await client.post(
        f"/api/projects/{pid_b}/manuscript/articles-table",
        json={
            "article_ids": [a_b],
            "columns": [
                {"preset": "author_year_citation", "label": "Study"},
                {"preset": "country", "label": "Country"},
                {"preset": "sample_size_n", "label": "N"},
                {"preset": "intervention", "label": "Intervention"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert "SECRET-COUNTRY" not in html
    assert "SECRET-RX" not in html
    assert "999" not in html
