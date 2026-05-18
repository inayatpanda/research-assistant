"""Routes — GET /reviews/meta/{id}/forest.png and /funnel.png."""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article

_PNG = b"\x89PNG\r\n\x1a\n"


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project_via_api(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Systematic Review"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(*, title: str, project_id: str, user_id: str) -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(user_id=user_id, project_id=project_id, title=title, authors=["X"], year=2024)
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


def _md_input(article_id: str, mean_a=1.0):
    return {
        "article_id": article_id,
        "mean_a": mean_a, "sd_a": 0.5, "n_a": 20,
        "mean_b": 0.5, "sd_b": 0.5, "n_b": 20,
    }


async def _seed_and_run(client) -> tuple[str, str]:
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    return pid, created["id"]


@pytest.mark.asyncio
async def test_forest_png_returns_200_with_image_content_type(client):
    pid, mid = await _seed_and_run(client)
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{mid}/forest.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_forest_png_starts_with_png_magic_bytes(client):
    pid, mid = await _seed_and_run(client)
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{mid}/forest.png")
    assert r.content[:8] == _PNG


@pytest.mark.asyncio
async def test_forest_png_409_when_not_completed(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    # Don't run — status stays draft
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{created['id']}/forest.png")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_funnel_png_returns_200_with_image_content_type(client):
    pid, mid = await _seed_and_run(client)
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{mid}/funnel.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == _PNG


@pytest.mark.asyncio
async def test_plots_404_for_other_user(client):
    pid, mid = await _seed_and_run(client)
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{mid}/forest.png")
    assert r.status_code == 404
