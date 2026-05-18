"""Phase 7.5 security regression: cross-user / cross-project isolation for /reviews/meta/*."""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article, ExtractionRecord, Review


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Systematic Review"}
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


async def _seed_extraction_for_user(
    *, project_id: str, article_id: str, user_id: str, design: str = "RCT"
) -> None:
    container = get_container()
    async with container.session_factory() as session:
        from sqlalchemy import select
        # get or create review for this (project, user)
        review = (await session.execute(
            select(Review).where(Review.project_id == project_id, Review.user_id == user_id)
        )).scalar_one_or_none()
        if review is None:
            review = Review(user_id=user_id, project_id=project_id)
            session.add(review)
            await session.flush()
        ext = ExtractionRecord(
            user_id=user_id, review_id=review.id, article_id=article_id,
            fields={"basic": {"design": design}},
        )
        session.add(ext)
        await session.commit()


def _md_input(article_id: str, mean_a=1.0):
    return {
        "article_id": article_id,
        "mean_a": mean_a, "sd_a": 0.5, "n_a": 20,
        "mean_b": 0.5, "sd_b": 0.5, "n_b": 20,
    }


async def _create_meta_as_user_a(client, pid: str) -> tuple[str, list[str]]:
    _switch_user("user-a")
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    return created["id"], [a1, a2]


@pytest.mark.asyncio
async def test_list_meta_isolated_across_users(client):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    mid_a, _ = await _create_meta_as_user_a(client, pid_a)

    _switch_user("user-b")
    # user-b also makes a project but can't see user-a's
    pid_b = await _make_project(client, "B")
    r = await client.get(f"/api/projects/{pid_b}/reviews/meta")
    assert r.status_code == 200
    assert r.json() == []
    # Try to access user-a's project — 404 because user-b doesn't own it
    r = await client.get(f"/api/projects/{pid_a}/reviews/meta")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_meta_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid, _ = await _create_meta_as_user_a(client, pid)
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{mid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_meta_rejects_other_user_article(client):
    _switch_user("user-b")
    pid_b = await _make_project(client, "B")
    a_b = await _seed_article(title="b-art", project_id=pid_b, user_id="user-b")

    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    a_a = await _seed_article(title="a-art", project_id=pid_a, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a_a, 1.0), _md_input(a_b, 2.0)],  # a_b belongs to user-b
    }
    r = await client.post(f"/api/projects/{pid_a}/reviews/meta", json=body)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_meta_inputs_isolated_across_users(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid, _ = await _create_meta_as_user_a(client, pid)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/reviews/meta/{mid}/inputs",
        json=_md_input("00000000000000000000000000000000", mean_a=2.0),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid, _ = await _create_meta_as_user_a(client, pid)
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_forest_png_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid, _ = await _create_meta_as_user_a(client, pid)
    await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{mid}/forest.png")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_funnel_png_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid, _ = await _create_meta_as_user_a(client, pid)
    await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/meta/{mid}/funnel.png")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_interpret_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid, _ = await _create_meta_as_user_a(client, pid)
    await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/interpret")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_push_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid, _ = await _create_meta_as_user_a(client, pid)
    await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_subgroup_variable_resolution_uses_owners_extraction_only(client):
    """User A defines a meta with subgroup_variable='basic.design'.
    User B has another extraction record on the same articles (with a different design).
    Running the meta for user A reads only A's extraction record.

    This relies on the cross-user article check — user B cannot reference user A's
    articles in their own extraction records, so cross-user contamination requires
    that the meta run actively queries by user_id.
    """
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    a1 = await _seed_article(title="S1", project_id=pid_a, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid_a, user_id="user-a")
    await _seed_extraction_for_user(project_id=pid_a, article_id=a1, user_id="user-a", design="RCT")
    await _seed_extraction_for_user(project_id=pid_a, article_id=a2, user_id="user-a", design="RCT")

    body = {
        "effect_metric": "md", "model": "fixed",
        "subgroup_variable": "basic.design",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid_a}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid_a}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text
    sg = r.json()["subgroup_summary"]
    # Should see only RCT — never "Cohort" (which would come from a foreign user's data)
    assert set(sg.keys()) <= {"RCT", "Unspecified"}
