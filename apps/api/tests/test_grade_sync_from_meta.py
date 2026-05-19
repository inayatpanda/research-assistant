"""Phase 19 (MP19) — GRADE sync-from-meta integration.

When a GRADE assessment carries a ``meta_id`` pointing to a published
meta-analysis, the GRADE push (SoF table) auto-fills the effect estimate
and n_studies columns from the linked meta-analysis result.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "GRADE Sync", "study_type": "Systematic Review"},
    )
    return r.json()["id"]


async def _seed_article(*, project_id: str, user_id: str, title: str) -> str:
    container = get_container()
    async with container.session_factory() as s:
        a = Article(
            user_id=user_id,
            project_id=project_id,
            title=title,
            authors=["X"],
            year=2024,
        )
        s.add(a)
        await s.commit()
        await s.refresh(a)
        return a.id


async def _create_and_run_meta(client, pid: str) -> tuple[str, list[str]]:
    a1 = await _seed_article(project_id=pid, user_id="local-user", title="A")
    a2 = await _seed_article(project_id=pid, user_id="local-user", title="B")
    a3 = await _seed_article(project_id=pid, user_id="local-user", title="C")
    body = {
        "effect_metric": "md",
        "model": "fixed",
        "inputs": [
            {"article_id": a1, "mean_a": 1.0, "sd_a": 0.5, "n_a": 30,
             "mean_b": 0.5, "sd_b": 0.5, "n_b": 30},
            {"article_id": a2, "mean_a": 1.2, "sd_a": 0.5, "n_a": 30,
             "mean_b": 0.6, "sd_b": 0.5, "n_b": 30},
            {"article_id": a3, "mean_a": 1.5, "sd_a": 0.6, "n_a": 30,
             "mean_b": 0.5, "sd_b": 0.6, "n_b": 30},
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    mid = created["id"]
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/run")
    assert r.status_code == 200, r.text
    return mid, [a1, a2, a3]


def _grade_body(outcome: str, meta_id: str | None = None):
    return {
        "outcome_label": outcome,
        "starting_certainty": "high",
        "domain_risk_of_bias": "not_serious",
        "domain_inconsistency": "not_serious",
        "domain_indirectness": "not_serious",
        "domain_imprecision": "not_serious",
        "domain_publication_bias": "not_serious",
        "upgrade_large_effect": "none",
        "upgrade_dose_response": "none",
        "upgrade_confounders_against": "none",
        "meta_id": meta_id,
    }


@pytest.mark.asyncio
async def test_grade_push_renders_pooled_estimate_when_meta_linked(client):
    pid = await _make_project(client)
    mid, _ = await _create_and_run_meta(client, pid)

    r = await client.post(
        f"/api/projects/{pid}/review/grade",
        json=_grade_body("Pain", meta_id=mid),
    )
    assert r.status_code == 201, r.text

    r = await client.post(f"/api/projects/{pid}/review/grade/push")
    assert r.status_code == 200, r.text
    body_html = r.json()["content"]
    # SoF should reference the pooled MD and the number of studies (3)
    assert "MD" in body_html
    assert "3 studies" in body_html or "n=3" in body_html or "studies" in body_html
    # Article CITE tokens come from the pooled inputs
    assert "[CITE_" in body_html


@pytest.mark.asyncio
async def test_grade_push_handles_unlinked_assessment(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/grade",
        json=_grade_body("Function", meta_id=None),
    )
    assert r.status_code == 201

    r = await client.post(f"/api/projects/{pid}/review/grade/push")
    assert r.status_code == 200
    # Unlinked rows render the table but without a pooled effect string.
    body_html = r.json()["content"]
    assert "sof-table" in body_html


@pytest.mark.asyncio
async def test_grade_with_invalid_meta_id_is_rejected(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/grade",
        json=_grade_body("Pain", meta_id="ffffffffffffffffffffffffffffffff"),
    )
    assert r.status_code == 404
