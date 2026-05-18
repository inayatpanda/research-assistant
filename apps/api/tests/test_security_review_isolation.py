"""Phase 7 security regression: prove every reviews endpoint is scoped by
both user_id and project_id.

Approach mirrors test_security_stats_isolation.py: drive the live ASGI app
twice with a swapped container.settings.local_user_id, and also verify
cross-project isolation for the same user.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container
from research_api.db.models import Article


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Systematic Review"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(*, title: str, project_id: str, user_id: str) -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            user_id=user_id, project_id=project_id, title=title,
            authors=["X"],
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


def _search_body(n: int = 10) -> dict:
    return {
        "database_name": "PubMed",
        "query_string": "x",
        "date_searched": "2025-01-15T00:00:00Z",
        "n_results": n,
    }


def _rob_answers() -> dict[str, str]:
    return {
        "randomisation": "low",
        "deviations": "low",
        "missing_outcome": "low",
        "measurement": "low",
        "reporting": "low",
    }


def _good_extraction_fields() -> dict:
    return {
        "basic": {"first_author": "X", "year": 2024, "design": "RCT"},
        "population": {"n_total": 50},
        "intervention": {"name": "T"},
        "comparator": {"name": "C"},
        "outcomes": {"outcomes": [{"name": "O"}]},
        "funding": {},
        "notes": {},
    }


# ── Review (PICO) ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_review_cannot_be_read_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    await client.get(f"/api/projects/{pid}/reviews")

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_review_cannot_be_patched_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    await client.get(f"/api/projects/{pid}/reviews")

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/reviews", json={"pico_population": "leaked"}
    )
    assert r.status_code == 404


# ── Search records ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_records_cannot_be_listed_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    await client.post(f"/api/projects/{pid}/reviews/search", json=_search_body())

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/search")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_records_isolated_across_projects(client):
    pid_x = await _make_project(client, title="X")
    pid_y = await _make_project(client, title="Y")
    await client.post(f"/api/projects/{pid_x}/reviews/search", json=_search_body(7))
    rows_y = (await client.get(f"/api/projects/{pid_y}/reviews/search")).json()
    assert rows_y == []
    rows_x = (await client.get(f"/api/projects/{pid_x}/reviews/search")).json()
    assert len(rows_x) == 1


@pytest.mark.asyncio
async def test_search_record_cannot_be_updated_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    created = (
        await client.post(f"/api/projects/{pid}/reviews/search", json=_search_body())
    ).json()

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/reviews/search/{created['id']}", json={"n_results": 999}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_record_cannot_be_deleted_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    created = (
        await client.post(f"/api/projects/{pid}/reviews/search", json=_search_body())
    ).json()

    _switch_user("user-b")
    r = await client.delete(
        f"/api/projects/{pid}/reviews/search/{created['id']}"
    )
    assert r.status_code == 404

    _switch_user("user-a")
    rows = (await client.get(f"/api/projects/{pid}/reviews/search")).json()
    assert len(rows) == 1


# ── Screening ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_screening_cannot_be_listed_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": aid, "stage": "title_abstract"},
    )

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/screening")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_screening_rejects_article_from_other_project_same_user(client):
    pid_a = await _make_project(client, title="A")
    pid_b = await _make_project(client, title="B")
    a_in_b = await _seed_article(title="X", project_id=pid_b, user_id="local-user")
    r = await client.post(
        f"/api/projects/{pid_a}/reviews/screening",
        json={"article_id": a_in_b, "stage": "title_abstract"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_screening_cannot_be_updated_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/reviews/screening/{created['id']}",
        json={"decision": "include"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_screening_cannot_be_deleted_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()

    _switch_user("user-b")
    r = await client.delete(
        f"/api/projects/{pid}/reviews/screening/{created['id']}"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ai_suggest_cannot_be_called_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/reviews/screening/{created['id']}/ai-suggest"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ai_suggest_does_not_clobber_existing_user_decision(client):
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract", "decision": "include"},
        )
    ).json()
    r = await client.post(
        f"/api/projects/{pid}/reviews/screening/{created['id']}/ai-suggest"
    )
    assert r.status_code == 200
    rows = (await client.get(f"/api/projects/{pid}/reviews/screening")).json()
    row = next(r for r in rows if r["id"] == created["id"])
    assert row["decision"] == "include"


@pytest.mark.asyncio
async def test_screening_ai_suggestion_does_not_decide(client):
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()
    await client.post(
        f"/api/projects/{pid}/reviews/screening/{created['id']}/ai-suggest"
    )
    rows = (await client.get(f"/api/projects/{pid}/reviews/screening")).json()
    row = next(r for r in rows if r["id"] == created["id"])
    assert row["ai_suggestion"] is not None
    assert row["decided_at"] is None


# ── RoB ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rob_cannot_be_listed_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": _rob_answers()},
    )

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/rob")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rob_cannot_be_created_against_other_user_project(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": _rob_answers()},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rob_cannot_be_patched_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/rob",
            json={"article_id": aid, "tool": "rob2", "domain_answers": _rob_answers()},
        )
    ).json()

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/reviews/rob/{created['id']}",
        json={"overall_override": "high"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rob_cannot_be_deleted_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/rob",
            json={"article_id": aid, "tool": "rob2", "domain_answers": _rob_answers()},
        )
    ).json()

    _switch_user("user-b")
    r = await client.delete(f"/api/projects/{pid}/reviews/rob/{created['id']}")
    assert r.status_code == 404


# ── Extraction ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extraction_cannot_be_listed_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid, "fields": _good_extraction_fields()},
    )

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/extraction")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_extraction_cannot_be_created_against_other_user_project(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid, "fields": _good_extraction_fields()},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_extraction_cannot_be_patched_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/extraction",
            json={"article_id": aid, "fields": _good_extraction_fields()},
        )
    ).json()

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/reviews/extraction/{created['id']}",
        json={"fields": _good_extraction_fields()},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_extraction_cannot_be_deleted_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")
    aid = await _seed_article(title="A", project_id=pid, user_id="user-a")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/extraction",
            json={"article_id": aid, "fields": _good_extraction_fields()},
        )
    ).json()

    _switch_user("user-b")
    r = await client.delete(
        f"/api/projects/{pid}/reviews/extraction/{created['id']}"
    )
    assert r.status_code == 404


# ── PRISMA + push ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prisma_cannot_be_read_by_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/reviews/prisma")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "endpoint",
    [
        "/reviews/prisma/push",
        "/reviews/search/push",
        "/reviews/rob/push",
        "/reviews/extraction/push",
    ],
)
@pytest.mark.asyncio
async def test_push_endpoints_cannot_be_called_by_other_user(client, endpoint):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}{endpoint}")
    assert r.status_code == 404


# ── Cross-project same-user isolation ──────────────────────────────────


@pytest.mark.asyncio
async def test_cross_project_screening_isolated(client):
    pid_x = await _make_project(client, title="X")
    pid_y = await _make_project(client, title="Y")
    aid_x = await _seed_article(title="X", project_id=pid_x, user_id="local-user")
    await client.post(
        f"/api/projects/{pid_x}/reviews/screening",
        json={"article_id": aid_x, "stage": "title_abstract"},
    )
    rows_y = (await client.get(f"/api/projects/{pid_y}/reviews/screening")).json()
    assert rows_y == []


@pytest.mark.asyncio
async def test_cross_project_rob_isolated(client):
    pid_x = await _make_project(client, title="X")
    pid_y = await _make_project(client, title="Y")
    aid_x = await _seed_article(title="X", project_id=pid_x, user_id="local-user")
    await client.post(
        f"/api/projects/{pid_x}/reviews/rob",
        json={"article_id": aid_x, "tool": "rob2", "domain_answers": _rob_answers()},
    )
    rows_y = (await client.get(f"/api/projects/{pid_y}/reviews/rob")).json()
    assert rows_y == []


@pytest.mark.asyncio
async def test_cross_project_extraction_isolated(client):
    pid_x = await _make_project(client, title="X")
    pid_y = await _make_project(client, title="Y")
    aid_x = await _seed_article(title="X", project_id=pid_x, user_id="local-user")
    await client.post(
        f"/api/projects/{pid_x}/reviews/extraction",
        json={"article_id": aid_x, "fields": _good_extraction_fields()},
    )
    rows_y = (await client.get(f"/api/projects/{pid_y}/reviews/extraction")).json()
    assert rows_y == []
