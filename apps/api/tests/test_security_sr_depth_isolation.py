"""Phase 19 (MP19) — Cross-user / cross-project isolation across the
new SR-depth + MeSH + meta-extension surface area.

25+ isolation regressions covering every new endpoint:
- MeSH cache (list, post, delete)
- Search strategies (list, create, patch, delete, translate)
- Narrative synthesis (list, create, patch, delete, push)
- Outcome instruments (list, create, patch, delete, push)
- Meta extensions (publication-bias, leave-one-out, leave-one-out.png,
  subgroup-interaction, meta-regression)

Pattern: user-A seeds → user-B attempts cross-user access and must
either 404 or get an empty result. Cross-project: user-A creates two
projects pid_a and pid_b; objects scoped to pid_a are invisible from
pid_b.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Systematic Review"},
    )
    return r.json()["id"]


async def _seed_article(*, project_id: str, user_id: str, title: str = "A") -> str:
    container = get_container()
    async with container.session_factory() as s:
        a = Article(
            user_id=user_id, project_id=project_id, title=title,
            authors=["X"], year=2024,
        )
        s.add(a)
        await s.commit()
        await s.refresh(a)
        return a.id


def _strategy_body(**ov):
    return {
        "name": "ss",
        "database": "PubMed",
        "query_text": '"x"[MeSH Terms]',
        "mesh_term_ids": [],
        **ov,
    }


def _narrative_body(**ov):
    return {
        "outcome_label": "Pain",
        "instrument": "VAS",
        "range_text": "0-10",
        "direction": "lower_better",
        "narrative_html": "",
        "study_citations": [],
        **ov,
    }


def _instrument_body(**ov):
    return {
        "outcome_label": "Function",
        "instrument_name": "OKS",
        "score_range_low": 0,
        "score_range_high": 48,
        "mid": 5,
        "study_values": [],
        **ov,
    }


def _mesh_body(**ov):
    return {
        "descriptor_ui": "D000001",
        "descriptor_name": "Acetaminophen",
        "scope_note": None,
        "tree_numbers": [],
        "entry_terms": [],
        "source": "user_added",
        **ov,
    }


# ── MeSH cache ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mesh_cache_list_cross_user_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/review/mesh/cache", json=_mesh_body())
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/review/mesh/cache")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_mesh_cache_post_cross_user_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/review/mesh/cache", json=_mesh_body()
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_mesh_cache_delete_cross_user_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/mesh/cache", json=_mesh_body()
    )
    mid = r.json()["id"]
    _switch_user("user-b")
    r = await client.delete(f"/api/projects/{pid}/review/mesh/cache/{mid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_mesh_cache_isolated_per_project(client):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    await client.post(f"/api/projects/{pid_a}/review/mesh/cache", json=_mesh_body())
    r = await client.get(f"/api/projects/{pid_b}/review/mesh/cache")
    assert r.status_code == 200 and r.json() == []


# ── Search strategies ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_strategies_list_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_body(),
    )
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/review/search-strategies")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_strategies_create_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_body(),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_strategies_patch_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/review/search-strategies",
            json=_strategy_body(),
        )
    ).json()["id"]
    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/review/search-strategies/{sid}",
        json={"name": "hack"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_strategies_delete_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/review/search-strategies",
            json=_strategy_body(),
        )
    ).json()["id"]
    _switch_user("user-b")
    r = await client.delete(f"/api/projects/{pid}/review/search-strategies/{sid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_strategies_translate_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/review/search-strategies",
            json=_strategy_body(),
        )
    ).json()["id"]
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies/{sid}/translate",
        params={"to": "embase"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_strategies_isolated_per_project(client):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    await client.post(
        f"/api/projects/{pid_a}/review/search-strategies",
        json=_strategy_body(),
    )
    r = await client.get(f"/api/projects/{pid_b}/review/search-strategies")
    assert r.status_code == 200 and r.json() == []


# ── Narrative synthesis ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_narrative_list_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/narrative-synthesis",
        json=_narrative_body(),
    )
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/review/narrative-synthesis")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_narrative_patch_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    eid = (
        await client.post(
            f"/api/projects/{pid}/review/narrative-synthesis",
            json=_narrative_body(),
        )
    ).json()["id"]
    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/review/narrative-synthesis/{eid}",
        json={"direction": "neutral"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_narrative_delete_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    eid = (
        await client.post(
            f"/api/projects/{pid}/review/narrative-synthesis",
            json=_narrative_body(),
        )
    ).json()["id"]
    _switch_user("user-b")
    r = await client.delete(
        f"/api/projects/{pid}/review/narrative-synthesis/{eid}"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_narrative_push_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/narrative-synthesis",
        json=_narrative_body(),
    )
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/review/narrative-synthesis/push")
    assert r.status_code == 404


# ── Outcome instruments ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_outcome_instruments_list_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/outcome-instruments",
        json=_instrument_body(),
    )
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/review/outcome-instruments")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_outcome_instruments_patch_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    iid = (
        await client.post(
            f"/api/projects/{pid}/review/outcome-instruments",
            json=_instrument_body(),
        )
    ).json()["id"]
    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/review/outcome-instruments/{iid}",
        json={"mid": 7.0},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_outcome_instruments_delete_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    iid = (
        await client.post(
            f"/api/projects/{pid}/review/outcome-instruments",
            json=_instrument_body(),
        )
    ).json()["id"]
    _switch_user("user-b")
    r = await client.delete(
        f"/api/projects/{pid}/review/outcome-instruments/{iid}"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_outcome_instruments_push_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/outcome-instruments",
        json=_instrument_body(),
    )
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/review/outcome-instruments/push")
    assert r.status_code == 404


# ── Meta extensions ─────────────────────────────────────────────────


async def _seed_meta_for_user_a(client, pid: str) -> str:
    _switch_user("user-a")
    arts = []
    for i in range(3):
        arts.append(
            await _seed_article(
                project_id=pid, user_id="user-a", title=f"A-S{i}"
            )
        )
    body = {
        "effect_metric": "md", "model": "random",
        "inputs": [
            {"article_id": arts[0], "mean_a": 1.0, "sd_a": 0.5, "n_a": 30,
             "mean_b": 0.5, "sd_b": 0.5, "n_b": 30},
            {"article_id": arts[1], "mean_a": 1.2, "sd_a": 0.5, "n_a": 30,
             "mean_b": 0.6, "sd_b": 0.5, "n_b": 30},
            {"article_id": arts[2], "mean_a": 1.4, "sd_a": 0.5, "n_a": 30,
             "mean_b": 0.5, "sd_b": 0.5, "n_b": 30},
        ],
    }
    mid = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()["id"]
    await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    return mid


@pytest.mark.asyncio
async def test_publication_bias_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid = await _seed_meta_for_user_a(client, pid)
    _switch_user("user-b")
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/publication-bias"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_leave_one_out_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid = await _seed_meta_for_user_a(client, pid)
    _switch_user("user-b")
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/leave-one-out"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_leave_one_out_png_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid = await _seed_meta_for_user_a(client, pid)
    _switch_user("user-b")
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/leave-one-out.png"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_subgroup_interaction_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid = await _seed_meta_for_user_a(client, pid)
    _switch_user("user-b")
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/subgroup-interaction"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_meta_regression_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    mid = await _seed_meta_for_user_a(client, pid)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/reviews/meta/{mid}/meta-regression",
        json={"moderator": [1.0, 2.0, 3.0]},
    )
    assert r.status_code == 404


# ── MeSH search/suggest (project ownership) ─────────────────────────


@pytest.mark.asyncio
async def test_mesh_search_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.get(
        f"/api/projects/{pid}/review/mesh/search", params={"q": "diabetes"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_mesh_suggest_cross_user_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/review/mesh/suggest", json={})
    assert r.status_code == 404


# ── Cross-project isolation: same user, different projects ──────────


@pytest.mark.asyncio
async def test_narrative_isolated_per_project(client):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    await client.post(
        f"/api/projects/{pid_a}/review/narrative-synthesis",
        json=_narrative_body(),
    )
    r = await client.get(f"/api/projects/{pid_b}/review/narrative-synthesis")
    assert r.status_code == 200 and r.json() == []


@pytest.mark.asyncio
async def test_outcome_instruments_isolated_per_project(client):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    await client.post(
        f"/api/projects/{pid_a}/review/outcome-instruments",
        json=_instrument_body(),
    )
    r = await client.get(f"/api/projects/{pid_b}/review/outcome-instruments")
    assert r.status_code == 200 and r.json() == []


@pytest.mark.asyncio
async def test_strategy_in_project_a_not_visible_in_project_b(client):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    sid = (
        await client.post(
            f"/api/projects/{pid_a}/review/search-strategies",
            json=_strategy_body(),
        )
    ).json()["id"]
    # Same user, but the strategy was created under pid_a's review
    r = await client.patch(
        f"/api/projects/{pid_b}/review/search-strategies/{sid}",
        json={"name": "hack"},
    )
    assert r.status_code == 404
