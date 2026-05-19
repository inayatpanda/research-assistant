"""Phase 14 (MP14) — GRADE push: SoF table emitted to Results section."""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "SOF P", "study_type": "Systematic Review"},
    )
    return r.json()["id"]


async def _seed_article(*, title: str, project_id: str, user_id: str) -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            user_id=user_id, project_id=project_id, title=title, authors=["X"],
            year=2024,
        )
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


def _grade(**over):
    base = {
        "outcome_label": "Mortality",
        "starting_certainty": "high",
        "domain_risk_of_bias": "not_serious",
        "domain_inconsistency": "not_serious",
        "domain_indirectness": "not_serious",
        "domain_imprecision": "not_serious",
        "domain_publication_bias": "not_serious",
        "upgrade_large_effect": "none",
        "upgrade_dose_response": "none",
        "upgrade_confounders_against": "none",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_push_emits_sof_table_with_certainty_badge(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/review/grade", json=_grade())

    r = await client.post(f"/api/projects/{pid}/review/grade/push")
    assert r.status_code == 200, r.text
    content = r.json()["content"]
    assert 'class="sof-table"' in content
    assert "Mortality" in content
    # The certainty badge wrapper must be present.
    assert 'class="cert cert-high"' in content


@pytest.mark.asyncio
async def test_push_idempotent_replaces_previous_sof_block(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/review/grade", json=_grade())

    await client.post(f"/api/projects/{pid}/review/grade/push")
    r2 = await client.post(f"/api/projects/{pid}/review/grade/push")
    assert r2.status_code == 200
    content = r2.json()["content"]
    assert content.count('class="sof-table"') == 1


@pytest.mark.asyncio
async def test_push_includes_cite_tokens_for_pooled_studies(client):
    """When the GRADE row is linked to a meta-analysis, the SoF row carries
    `[CITE_<aid>]` tokens for each pooled study."""
    _switch_user("user-a")
    pid = await _make_project(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    meta = (
        await client.post(f"/api/projects/{pid}/reviews/meta", json=body)
    ).json()
    await client.post(f"/api/projects/{pid}/reviews/meta/{meta['id']}/run")

    grade_body = _grade(meta_id=meta["id"])
    await client.post(f"/api/projects/{pid}/review/grade", json=grade_body)

    r = await client.post(f"/api/projects/{pid}/review/grade/push")
    assert r.status_code == 200
    content = r.json()["content"]
    # Cite tokens may be resolved by _push_to_section in some paths, but the
    # SoF builder always emits them; here we ensure the article_id surfaces
    # one way or another.
    for aid in (a1, a2):
        assert (
            f"[CITE_{aid}]" in content
            or f'data-article-id="{aid}"' in content
        )


@pytest.mark.asyncio
async def test_push_narrative_synthesis_when_no_meta_link(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/review/grade", json=_grade())

    r = await client.post(f"/api/projects/{pid}/review/grade/push")
    assert r.status_code == 200
    content = r.json()["content"]
    assert "Narrative synthesis" in content
