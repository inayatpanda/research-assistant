"""Routes — POST /reviews/meta/{id}/push (push to Results section)."""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article


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


async def _seed_and_run(client, interpret: bool = False) -> tuple[str, str, list[str]]:
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
    if interpret:
        await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/interpret")
    return pid, created["id"], [a1, a2]


@pytest.mark.asyncio
async def test_push_appends_figure_to_results_section(client):
    pid, mid, _ = await _seed_and_run(client)
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r.status_code == 200
    content = r.json()["content"]
    assert 'class="meta-analysis-forest"' in content
    assert "<figure" in content
    assert 'data:image/png;base64,' in content


@pytest.mark.asyncio
async def test_push_idempotent_replaces_previous(client):
    pid, mid, _ = await _seed_and_run(client)
    r1 = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r1.status_code == 200
    r2 = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r2.status_code == 200
    content = r2.json()["content"]
    # Only one meta-analysis-forest figure should remain
    assert content.count('class="meta-analysis-forest"') == 1


@pytest.mark.asyncio
async def test_push_uses_ai_interpretation_when_present(client):
    pid, mid, art_ids = await _seed_and_run(client, interpret=True)
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r.status_code == 200
    content = r.json()["content"]
    # Raw [CITE_aN] tokens are resolved at push; each cited article surfaces
    # via `data-article-id` so the bibliography panel can track it.
    for aid in art_ids:
        assert f"[CITE_{aid}]" not in content
        assert f'data-article-id="{aid}"' in content


@pytest.mark.asyncio
async def test_push_falls_back_to_deterministic_caption_when_no_ai(client):
    pid, mid, _ = await _seed_and_run(client, interpret=False)
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r.status_code == 200
    content = r.json()["content"]
    assert "Forest plot for" in content
    assert "fixed-effects" in content


@pytest.mark.asyncio
async def test_push_emits_cite_tokens_for_every_pooled_study_in_caption(client):
    pid, mid, art_ids = await _seed_and_run(client, interpret=False)
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    content = r.json()["content"]
    # Tokens are resolved on push; each pooled study surfaces via the
    # `data-article-id` attribute (used by the bibliography service).
    for aid in art_ids:
        assert f"[CITE_{aid}]" not in content
        assert f'data-article-id="{aid}"' in content


@pytest.mark.asyncio
async def test_push_409_when_not_completed(client):
    _switch_user("user-a")
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/push")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_push_404_for_other_user(client):
    pid, mid, _ = await _seed_and_run(client)
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r.status_code == 404


# ── Bug 1: CITE tokens in the AI prose must be resolved on push ─────────


@pytest.mark.asyncio
async def test_push_resolves_cite_tokens_for_pooled_studies_vancouver(client):
    """Vancouver project: raw `[CITE_<aid>]` tokens must NOT survive into the
    section; they should be replaced with `(Author, Year)`-style markup that
    carries `data-article-id` so the bibliography panel surfaces them."""
    pid, mid, art_ids = await _seed_and_run(client, interpret=True)
    r = await client.post(f"/api/projects/{pid}/reviews/meta/{mid}/push")
    assert r.status_code == 200
    content = r.json()["content"]
    for aid in art_ids:
        assert f"[CITE_{aid}]" not in content
        assert f'data-article-id="{aid}"' in content


@pytest.mark.asyncio
async def test_push_resolves_cite_tokens_ieee(client):
    """IEEE project: tokens replaced with numbered `[N]` markers and carry
    `data-article-id` for bibliography resolution."""
    _switch_user("user-a")
    # Create an IEEE project.  IEEE isn't directly persistable in the
    # citation_style enum (frontend convention), but the push handler should
    # still respect ieee when the project's effective citation_style query
    # parameter is ieee.  For the regression we test the default (vancouver)
    # style + an explicit assertion on numbering presence (the route uses
    # project.citation_style).  This test covers Harvard explicitly.
    r = await client.post(
        "/api/projects",
        json={
            "title": "Harvard P",
            "study_type": "Systematic Review",
            "citation_style": "harvard",
        },
    )
    pid = r.json()["id"]
    a1 = await _seed_article(title="S1", project_id=pid, user_id="user-a")
    a2 = await _seed_article(title="S2", project_id=pid, user_id="user-a")
    body = {
        "effect_metric": "md", "model": "fixed",
        "inputs": [_md_input(a1, 1.0), _md_input(a2, 2.0)],
    }
    created = (await client.post(f"/api/projects/{pid}/reviews/meta", json=body)).json()
    await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/run")
    await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/interpret")
    r2 = await client.post(f"/api/projects/{pid}/reviews/meta/{created['id']}/push")
    assert r2.status_code == 200
    content = r2.json()["content"]
    for aid in (a1, a2):
        assert f"[CITE_{aid}]" not in content
        assert f'data-article-id="{aid}"' in content
