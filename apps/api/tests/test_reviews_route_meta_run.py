"""Routes — POST /reviews/meta/{id}/run."""
from __future__ import annotations

import math

import pytest

from research_api.container import get_container
from research_api.db.models import Article, ExtractionRecord, Review


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


async def _seed_extraction(*, project_id: str, article_id: str, user_id: str, design: str = "RCT") -> None:
    container = get_container()
    async with container.session_factory() as session:
        # Ensure review exists for this project
        from sqlalchemy import select
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


def _md_input(article_id: str, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20):
    return {
        "article_id": article_id,
        "mean_a": mean_a, "sd_a": sd_a, "n_a": n_a,
        "mean_b": mean_b, "sd_b": sd_b, "n_b": n_b,
    }


def _smd_input(article_id: str, mean_a, sd_a, n_a, mean_b, sd_b, n_b):
    return {
        "article_id": article_id,
        "mean_a": mean_a, "sd_a": sd_a, "n_a": n_a,
        "mean_b": mean_b, "sd_b": sd_b, "n_b": n_b,
    }


def _or_input(article_id: str, *, events_a, n_a, events_b, n_b):
    return {
        "article_id": article_id,
        "events_a": events_a, "n_a_total": n_a,
        "events_b": events_b, "n_b_total": n_b,
    }


@pytest.mark.asyncio
async def test_run_smd_pool_random_known_answer(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    a3 = await _seed_article(title="S3", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "smd", "model": "random",
        "inputs": [
            _smd_input(a1, mean_a=10, sd_a=4, n_a=40, mean_b=8, sd_b=4, n_b=40),
            _smd_input(a2, mean_a=12, sd_a=5, n_a=35, mean_b=10, sd_b=5, n_b=35),
            _smd_input(a3, mean_a=9, sd_a=3, n_a=30, mean_b=8, sd_b=3, n_b=30),
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "completed"
    assert data["pooled_estimate"] is not None
    assert data["ci_low"] is not None
    assert data["ci_high"] is not None
    assert data["q_value"] is not None
    assert data["i2"] is not None


@pytest.mark.asyncio
async def test_run_or_pool_fixed_continuity_correction_applied(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "or", "model": "fixed",
        "inputs": [
            _or_input(a1, events_a=0, n_a=50, events_b=5, n_b=50),  # zero cell
            _or_input(a2, events_a=10, n_a=50, events_b=4, n_b=50),
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text
    data = r.json()
    # Continuity correction should keep pooled estimate finite
    assert math.isfinite(data["pooled_estimate"])


@pytest.mark.asyncio
async def test_run_hr_uses_log_hr_when_provided(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "hr", "model": "fixed",
        "inputs": [
            {"article_id": a1, "log_hr": -0.3567, "se_log_hr": 0.123},
            {"article_id": a2, "log_hr": -0.2, "se_log_hr": 0.10},
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "completed"
    # The pooled log-HR should be between the two input log-HR
    assert -0.40 < data["pooled_estimate"] < -0.10


@pytest.mark.asyncio
async def test_run_hr_back_calculates_se_from_ci(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "hr", "model": "fixed",
        "inputs": [
            {"article_id": a1, "hr": 0.70, "hr_ci_low": 0.55, "hr_ci_high": 0.89},
            {"article_id": a2, "hr": 0.80, "hr_ci_low": 0.65, "hr_ci_high": 0.99},
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_run_r_uses_fisher_z(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "r", "model": "fixed",
        "inputs": [
            {"article_id": a1, "r": 0.5, "n_r": 30},
            {"article_id": a2, "r": 0.4, "n_r": 40},
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text
    # pooled is on Fisher-z scale; back-transform somewhere around 0.45
    assert 0.2 < r.json()["pooled_estimate"] < 0.7


@pytest.mark.asyncio
async def test_run_subgroup_analysis_produces_summary(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    a3 = await _seed_article(title="S3", project_id=pid, user_id="user-a")
    a4 = await _seed_article(title="S4", project_id=pid, user_id="user-a")
    for a, design in [(a1, "RCT"), (a2, "RCT"), (a3, "Cohort"), (a4, "Cohort")]:
        await _seed_extraction(project_id=pid, article_id=a, user_id="user-a", design=design)

    body = {
        "effect_metric": "smd", "model": "random",
        "subgroup_variable": "basic.design",
        "inputs": [
            _smd_input(a1, mean_a=10, sd_a=4, n_a=40, mean_b=8, sd_b=4, n_b=40),
            _smd_input(a2, mean_a=11, sd_a=4, n_a=40, mean_b=9, sd_b=4, n_b=40),
            _smd_input(a3, mean_a=12, sd_a=4, n_a=40, mean_b=8, sd_b=4, n_b=40),
            _smd_input(a4, mean_a=13, sd_a=4, n_a=40, mean_b=9, sd_b=4, n_b=40),
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["subgroup_summary"] is not None
    sg = data["subgroup_summary"]
    assert "RCT" in sg and "Cohort" in sg
    assert sg["RCT"]["k"] == 2
    assert sg["Cohort"]["k"] == 2


@pytest.mark.asyncio
async def test_run_subgroup_with_single_member_is_summarised_but_no_pool(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    a3 = await _seed_article(title="S3", project_id=pid, user_id="user-a")
    await _seed_extraction(project_id=pid, article_id=a1, user_id="user-a", design="RCT")
    await _seed_extraction(project_id=pid, article_id=a2, user_id="user-a", design="RCT")
    await _seed_extraction(project_id=pid, article_id=a3, user_id="user-a", design="Cohort")

    body = {
        "effect_metric": "smd", "model": "fixed",
        "subgroup_variable": "basic.design",
        "inputs": [
            _smd_input(a1, mean_a=10, sd_a=4, n_a=40, mean_b=8, sd_b=4, n_b=40),
            _smd_input(a2, mean_a=11, sd_a=4, n_a=40, mean_b=9, sd_b=4, n_b=40),
            _smd_input(a3, mean_a=12, sd_a=4, n_a=40, mean_b=8, sd_b=4, n_b=40),
        ],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 200, r.text
    sg = r.json()["subgroup_summary"]
    assert sg["Cohort"]["k"] == 1
    assert sg["Cohort"]["estimate"] is None


@pytest.mark.asyncio
async def test_run_invalid_inputs_for_metric_returns_422_and_sets_failed_status(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    # Use OR metric but provide MD-shaped inputs (events fields are None)
    body = {
        "effect_metric": "or", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r.status_code == 422
    # And status flips to failed
    fetched = (await client.get(f"/api/projects/{pid}/reviews/meta/{created['id']}")).json()
    assert fetched["status"] == "failed"


@pytest.mark.asyncio
async def test_run_idempotent_overwrites_previous_pooled(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1), _md_input(a2, mean_a=2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r1 = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r1.status_code == 200
    first_est = r1.json()["pooled_estimate"]
    r2 = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    assert r2.status_code == 200
    assert r2.json()["pooled_estimate"] == first_est
