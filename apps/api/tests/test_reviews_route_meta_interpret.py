"""Routes — POST /reviews/meta/{id}/interpret."""
from __future__ import annotations

import re

import pytest

from research_api.container import get_container
from research_api.db.models import Article
from research_api.services.ai import AIProviderUnavailable, AIRateLimited


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project_via_api(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Systematic Review"}
    )
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


async def _seed_and_run(client) -> tuple[str, str, list[str]]:
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="Study One", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="Study Two", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    return pid, created["id"], [a1, a2]


@pytest.mark.asyncio
async def test_interpret_writes_prose_and_returns(client):
    pid, mid, _ = await _seed_and_run(client)
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/interpret")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ai_interpretation"] is not None
    assert len(data["ai_interpretation"]) > 0


@pytest.mark.asyncio
async def test_interpret_422_when_not_completed(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    # Don't run
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/interpret")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_interpret_429_when_rate_limited(client):
    pid, mid, _ = await _seed_and_run(client)
    fake_ai = client.fake_ai

    async def _raise(**kw):
        raise AIRateLimited("rate", provider="fake")

    fake_ai.interpret_meta_analysis = _raise
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/interpret")
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_interpret_503_when_provider_unavailable(client):
    pid, mid, _ = await _seed_and_run(client)
    fake_ai = client.fake_ai

    async def _raise(**kw):
        raise AIProviderUnavailable("down", provider="fake")

    fake_ai.interpret_meta_analysis = _raise
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/interpret")
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_interpret_prose_contains_every_study_token(client):
    pid, mid, art_ids = await _seed_and_run(client)
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/interpret")
    assert r.status_code == 200, r.text
    prose = r.json()["ai_interpretation"]
    for aid in art_ids:
        assert f"[CITE_{aid}]" in prose


@pytest.mark.asyncio
async def test_interpret_404_for_other_user(client):
    pid, mid, _ = await _seed_and_run(client)
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/interpret")
    assert r.status_code == 404
