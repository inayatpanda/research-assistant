"""Phase 19 (MP19) — SR-depth route happy paths.

Covers:
- Narrative-synthesis CRUD + push to Results.
- Outcome-instruments CRUD + push to Results.
- MeSH cache CRUD.
- Search-strategy translate (non-persist + persist variants).
- Meta extensions: publication-bias / leave-one-out / subgroup-interaction
  / meta-regression are smoke-tested with seeded meta inputs.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article


async def _make_project(client, title: str = "P-SR") -> str:
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


# ── Narrative synthesis ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_narrative_crud_and_push(client):
    pid = await _make_project(client)
    body = {
        "outcome_label": "Pain",
        "instrument": "VAS",
        "range_text": "0-10",
        "direction": "lower_better",
        "narrative_html": "<p>Reduced.</p>",
        "study_citations": [],
    }
    r = await client.post(
        f"/api/projects/{pid}/review/narrative-synthesis", json=body
    )
    assert r.status_code == 201
    eid = r.json()["id"]

    r = await client.get(f"/api/projects/{pid}/review/narrative-synthesis")
    assert r.status_code == 200
    assert any(e["id"] == eid for e in r.json())

    r = await client.patch(
        f"/api/projects/{pid}/review/narrative-synthesis/{eid}",
        json={"direction": "neutral"},
    )
    assert r.status_code == 200
    assert r.json()["direction"] == "neutral"

    r = await client.post(f"/api/projects/{pid}/review/narrative-synthesis/push")
    assert r.status_code == 200, r.text
    assert "narrative-synthesis-table" in r.json()["content"]

    r = await client.delete(
        f"/api/projects/{pid}/review/narrative-synthesis/{eid}"
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_narrative_patch_404_for_unknown_entry(client):
    pid = await _make_project(client)
    r = await client.patch(
        f"/api/projects/{pid}/review/narrative-synthesis/nonexistent",
        json={"direction": "neutral"},
    )
    assert r.status_code == 404


# ── Outcome instruments ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_outcome_instruments_crud_and_push(client):
    pid = await _make_project(client)
    aid = await _seed_article(
        project_id=pid, user_id="local-user", title="Study A"
    )
    body = {
        "outcome_label": "Function",
        "instrument_name": "OKS",
        "score_range_low": 0,
        "score_range_high": 48,
        "mid": 5,
        "study_values": [
            {"article_id": aid, "group_label": "Intervention",
             "value": 38.0, "sd_or_ci": "4.1", "n": 60}
        ],
    }
    r = await client.post(
        f"/api/projects/{pid}/review/outcome-instruments", json=body
    )
    assert r.status_code == 201, r.text
    iid = r.json()["id"]

    r = await client.get(f"/api/projects/{pid}/review/outcome-instruments")
    assert r.status_code == 200
    assert any(row["id"] == iid for row in r.json())

    r = await client.patch(
        f"/api/projects/{pid}/review/outcome-instruments/{iid}",
        json={"mid": 6.5},
    )
    assert r.status_code == 200
    assert r.json()["mid"] == 6.5

    r = await client.post(
        f"/api/projects/{pid}/review/outcome-instruments/push"
    )
    assert r.status_code == 200
    assert "outcome-instruments-table" in r.json()["content"]

    r = await client.delete(
        f"/api/projects/{pid}/review/outcome-instruments/{iid}"
    )
    assert r.status_code == 204


# ── MeSH cache CRUD ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mesh_cache_crud(client):
    pid = await _make_project(client)
    body = {
        "descriptor_ui": "D006085",
        "descriptor_name": "Arthroplasty, Replacement, Hip",
        "scope_note": "Replacement of the hip joint.",
        "tree_numbers": ["E04.555.110"],
        "entry_terms": ["Total Hip Arthroplasty"],
        "source": "user_added",
    }
    r = await client.post(
        f"/api/projects/{pid}/review/mesh/cache", json=body
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    assert r.json()["descriptor_ui"] == "D006085"

    r = await client.get(f"/api/projects/{pid}/review/mesh/cache")
    assert r.status_code == 200
    assert any(m["id"] == mid for m in r.json())

    r = await client.delete(f"/api/projects/{pid}/review/mesh/cache/{mid}")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_mesh_cache_unique_per_project_descriptor(client):
    pid = await _make_project(client)
    body = {
        "descriptor_ui": "D006085",
        "descriptor_name": "Arthroplasty, Replacement, Hip",
        "tree_numbers": [],
        "entry_terms": [],
        "source": "user_added",
    }
    r1 = await client.post(f"/api/projects/{pid}/review/mesh/cache", json=body)
    assert r1.status_code == 201
    # Upsert: re-posting the same UI returns the same row (or updates it)
    r2 = await client.post(f"/api/projects/{pid}/review/mesh/cache", json=body)
    assert r2.status_code == 201


# ── Search-strategy translate (non-persist) ──────────────────────────


@pytest.mark.asyncio
async def test_translate_non_persist_returns_query(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json={
            "name": "Base",
            "database": "PubMed",
            "query_text": '"diabetes"[MeSH Terms] AND insulin[tw]',
            "mesh_term_ids": [],
        },
    )
    sid = r.json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies/{sid}/translate",
        params={"to": "wos"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["target"] == "wos"
    assert "TS=" in body["translated_query"]


# ── Meta extensions ──────────────────────────────────────────────────


async def _create_meta_with_inputs(client, pid: str) -> str:
    """Create a small MD meta-analysis for use in extension tests."""
    arts = []
    for i in range(4):
        arts.append(
            await _seed_article(
                project_id=pid, user_id="local-user", title=f"S{i + 1}"
            )
        )
    inputs = [
        {"article_id": arts[0], "mean_a": 1.0, "sd_a": 0.5, "n_a": 25,
         "mean_b": 0.5, "sd_b": 0.5, "n_b": 25},
        {"article_id": arts[1], "mean_a": 1.2, "sd_a": 0.5, "n_a": 25,
         "mean_b": 0.6, "sd_b": 0.5, "n_b": 25},
        {"article_id": arts[2], "mean_a": 1.4, "sd_a": 0.6, "n_a": 25,
         "mean_b": 0.7, "sd_b": 0.6, "n_b": 25},
        {"article_id": arts[3], "mean_a": 0.9, "sd_a": 0.5, "n_a": 25,
         "mean_b": 0.6, "sd_b": 0.5, "n_b": 25},
    ]
    r = await client.post(
        f"/api/projects/{pid}/reviews/meta",
        json={"effect_metric": "md", "model": "random", "inputs": inputs},
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    rr = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    assert rr.status_code == 200, rr.text
    return mid


@pytest.mark.asyncio
async def test_publication_bias_route_returns_test_panel(client):
    pid = await _make_project(client)
    mid = await _create_meta_with_inputs(client, pid)
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/publication-bias"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["metric"] == "md"
    methods = {t["method"] for t in body["tests"]}
    assert "egger" in methods
    assert "begg" in methods


@pytest.mark.asyncio
async def test_leave_one_out_route(client):
    pid = await _make_project(client)
    mid = await _create_meta_with_inputs(client, pid)
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/leave-one-out"
    )
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 4
    assert all("pooled_effect" in row for row in rows)


@pytest.mark.asyncio
async def test_leave_one_out_png_route(client):
    pid = await _make_project(client)
    mid = await _create_meta_with_inputs(client, pid)
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/leave-one-out.png"
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_meta_regression_route(client):
    pid = await _make_project(client)
    mid = await _create_meta_with_inputs(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/reviews/meta/{mid}/meta-regression",
        json={
            "moderator": [50.0, 55.0, 60.0, 65.0],
            "moderator_label": "Mean age",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "coef" in body and "p" in body and "r2" in body
    assert body["n"] == 4
    assert isinstance(body["bubble_plot_png_base64"], str)


@pytest.mark.asyncio
async def test_meta_regression_moderator_length_mismatch_422(client):
    pid = await _make_project(client)
    mid = await _create_meta_with_inputs(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/reviews/meta/{mid}/meta-regression",
        json={"moderator": [50.0, 55.0]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_subgroup_interaction_route_requires_subgroup_variable(client):
    pid = await _make_project(client)
    mid = await _create_meta_with_inputs(client, pid)
    r = await client.get(
        f"/api/projects/{pid}/reviews/meta/{mid}/subgroup-interaction"
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_outcome_instruments_route_empty_push_renders_empty_grid(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/outcome-instruments/push"
    )
    assert r.status_code == 200
    assert "outcome-instruments-table" in r.json()["content"]
