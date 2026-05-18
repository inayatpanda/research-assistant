"""Routes — Meta CRUD."""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article, Project


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
        a = Article(
            user_id=user_id, project_id=project_id, title=title, authors=["X"], year=2024,
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


def _md_input(article_id: str, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20):
    return {
        "article_id": article_id,
        "mean_a": mean_a, "sd_a": sd_a, "n_a": n_a,
        "mean_b": mean_b, "sd_b": sd_b, "n_b": n_b,
    }


@pytest.mark.asyncio
async def test_create_meta_with_two_inputs_returns_201_with_draft_status(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "title": "X",
        "effect_metric": "md",
        "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    r = await client.post(f"/api/projects/{pid}/reviews/meta", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "draft"
    assert len(data["inputs"]) == 2


@pytest.mark.asyncio
async def test_create_meta_with_one_input_returns_422(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1)],
    }
    r = await client.post(f"/api/projects/{pid}/reviews/meta", json=body)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_meta_with_other_project_article_returns_422(client):
    _switch_user("user-a")
    pid_a = await _make_project_via_api(client, "A")
    pid_b = await _make_project_via_api(client, "B")
    a1 = await _seed_article(title="from-A1", project_id=pid_a, user_id="user-a")
    a_other = await _seed_article(title="from-B", project_id=pid_b, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a_other)],
    }
    r = await client.post(f"/api/projects/{pid_a}/reviews/meta", json=body)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_meta_filters_by_review(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    await client.post(f"/api/projects/{pid}/reviews/meta", json=body)
    r = await client.get(f"/api/projects/{pid}/reviews/meta")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_meta_hydrates_inputs(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{created['id']}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["inputs"]) == 2


@pytest.mark.asyncio
async def test_patch_meta_updates_metric(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.patch(
        f"/api/projects/{pid}/reviews/meta/{created['id']}",
        json={"effect_metric": "smd"},
    )
    assert r.status_code == 200
    assert r.json()["effect_metric"] == "smd"
    assert r.json()["status"] == "draft"  # patches that affect metric reset state


@pytest.mark.asyncio
async def test_delete_meta_returns_204_and_cascades(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.delete(f"/api/projects/{pid}/reviews/meta/{created['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/projects/{pid}/reviews/meta/{created['id']}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_upsert_input_idempotent_via_article_id(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    # Upsert same article — should overwrite
    new_inp = _md_input(a1, mean_a=99.0)
    r = await client.post(
        f"/api/projects/{pid}/reviews/meta/{created['id']}/inputs", json=new_inp
    )
    assert r.status_code == 201
    fetched = (await client.get(f"/api/projects/{pid}/reviews/meta/{created['id']}")).json()
    assert len(fetched["inputs"]) == 2
    targets = [inp for inp in fetched["inputs"] if inp["article_id"] == a1]
    assert targets[0]["mean_a"] == 99.0


@pytest.mark.asyncio
async def test_meta_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()

    # Switch to a different user — should 404
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{created['id']}")
    assert r.status_code == 404
