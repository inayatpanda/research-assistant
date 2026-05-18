"""Reviews route tests — Tasks 8-12.

Endpoints exercised in this file:
- GET/PATCH /reviews
- GET/POST/PATCH/DELETE /reviews/search
- GET/POST/PATCH/DELETE /reviews/screening (+ /ai-suggest)
- GET /reviews/rob/tools; GET/POST/PATCH/DELETE /reviews/rob
- GET /reviews/extraction/schema; GET/POST/PATCH/DELETE /reviews/extraction
- GET /reviews/prisma; POST /reviews/{prisma,search,rob,extraction}/push
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest

from research_api.container import get_container
from research_api.db.models import Article, Project
from research_api.services.ai import AIProviderUnavailable, AIRateLimited


# ── helpers ────────────────────────────────────────────────────────────


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project_via_api(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Systematic Review"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(
    *, title: str, project_id: str, user_id: str, abstract: str | None = None
) -> str:
    """Insert an article directly via the container's session factory."""
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            user_id=user_id,
            project_id=project_id,
            title=title,
            authors=["Smith J"],
            abstract=abstract,
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


def _search_body(
    *, n: int = 12, db: str = "PubMed", q: str = "tka AND knee"
) -> dict:
    return {
        "database_name": db,
        "query_string": q,
        "date_searched": "2025-01-15T00:00:00Z",
        "n_results": n,
    }


def _good_extraction_fields() -> dict:
    return {
        "basic": {
            "first_author": "Smith J",
            "year": 2024,
            "country": "Canada",
            "design": "RCT",
        },
        "population": {"n_total": 100, "mean_age": 60},
        "intervention": {"name": "TKA"},
        "comparator": {"name": "Physio"},
        "outcomes": {"outcomes": [{"name": "WOMAC at 12mo"}]},
        "funding": {},
        "notes": {},
    }


def _rob2_answers_low() -> dict[str, str]:
    return {
        "randomisation": "low",
        "deviations": "low",
        "missing_outcome": "low",
        "measurement": "low",
        "reporting": "low",
    }


# ── Task 8: Review + Search ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_review_creates_on_first_call(client):
    pid = await _make_project_via_api(client)
    r = await client.get(f"/api/projects/{pid}/reviews")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == pid
    assert body["pico_population"] is None
    # Second call should return the same review row
    r2 = await client.get(f"/api/projects/{pid}/reviews")
    assert r2.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_get_review_404_for_unknown_project(client):
    r = await client.get("/api/projects/nope/reviews")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_review_updates_pico(client):
    pid = await _make_project_via_api(client)
    r = await client.patch(
        f"/api/projects/{pid}/reviews",
        json={
            "pico_population": "adults with knee OA",
            "pico_intervention": "TKA",
            "eligibility_inclusion": "RCTs only",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pico_population"] == "adults with knee OA"
    assert body["pico_intervention"] == "TKA"
    assert body["eligibility_inclusion"] == "RCTs only"


@pytest.mark.asyncio
async def test_list_search_empty(client):
    pid = await _make_project_via_api(client)
    r = await client.get(f"/api/projects/{pid}/reviews/search")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_search_happy_path(client):
    pid = await _make_project_via_api(client)
    r = await client.post(
        f"/api/projects/{pid}/reviews/search", json=_search_body(n=42)
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["database_name"] == "PubMed"
    assert body["n_results"] == 42


@pytest.mark.asyncio
async def test_create_search_invalid_database_returns_422(client):
    pid = await _make_project_via_api(client)
    bad = _search_body()
    bad["database_name"] = "NotARealDatabase"
    r = await client.post(f"/api/projects/{pid}/reviews/search", json=bad)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_search_changes_n_results(client):
    pid = await _make_project_via_api(client)
    created = (
        await client.post(f"/api/projects/{pid}/reviews/search", json=_search_body())
    ).json()
    r = await client.patch(
        f"/api/projects/{pid}/reviews/search/{created['id']}",
        json={"n_results": 99},
    )
    assert r.status_code == 200, r.text
    assert r.json()["n_results"] == 99


@pytest.mark.asyncio
async def test_delete_search_204(client):
    pid = await _make_project_via_api(client)
    created = (
        await client.post(f"/api/projects/{pid}/reviews/search", json=_search_body())
    ).json()
    r = await client.delete(f"/api/projects/{pid}/reviews/search/{created['id']}")
    assert r.status_code == 204
    out = await client.get(f"/api/projects/{pid}/reviews/search")
    assert out.json() == []


@pytest.mark.asyncio
async def test_search_404_for_unknown_id(client):
    pid = await _make_project_via_api(client)
    r = await client.patch(
        f"/api/projects/{pid}/reviews/search/missing", json={"n_results": 1}
    )
    assert r.status_code == 404


# ── Task 9: Screening + AI suggest ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_screening_empty(client):
    pid = await _make_project_via_api(client)
    r = await client.get(f"/api/projects/{pid}/reviews/screening")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_post_screening_creates_title_row(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A study", project_id=pid, user_id="local-user")
    r = await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": aid, "stage": "title_abstract"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["decision"] == "pending"
    assert r.json()["stage"] == "title_abstract"


@pytest.mark.asyncio
async def test_post_screening_upsert_idempotent(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    r1 = await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": aid, "stage": "title_abstract", "decision": "include"},
    )
    r2 = await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": aid, "stage": "title_abstract", "decision": "exclude",
              "exclusion_category": "population"},
    )
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["decision"] == "exclude"


@pytest.mark.asyncio
async def test_screening_filter_by_stage(client):
    pid = await _make_project_via_api(client)
    a1 = await _seed_article(title="A1", project_id=pid, user_id="local-user")
    a2 = await _seed_article(title="A2", project_id=pid, user_id="local-user")
    await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": a1, "stage": "title_abstract"},
    )
    await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": a2, "stage": "full_text"},
    )
    r = await client.get(
        f"/api/projects/{pid}/reviews/screening", params={"stage": "title_abstract"}
    )
    assert {row["article_id"] for row in r.json()} == {a1}


@pytest.mark.asyncio
async def test_patch_screening_changes_decision(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()
    r = await client.patch(
        f"/api/projects/{pid}/reviews/screening/{created['id']}",
        json={"decision": "include", "reason": "matches PICO"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["decision"] == "include"
    assert r.json()["reason"] == "matches PICO"
    assert r.json()["decided_at"] is not None


@pytest.mark.asyncio
async def test_post_screening_rejects_article_from_other_project(client):
    pid_a = await _make_project_via_api(client, title="A")
    pid_b = await _make_project_via_api(client, title="B")
    a_in_b = await _seed_article(title="A", project_id=pid_b, user_id="local-user")
    r = await client.post(
        f"/api/projects/{pid_a}/reviews/screening",
        json={"article_id": a_in_b, "stage": "title_abstract"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_ai_suggest_persists_suggestion_without_changing_decision(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(
        title="A", project_id=pid, user_id="local-user", abstract="An abstract"
    )
    await client.patch(
        f"/api/projects/{pid}/reviews",
        json={"eligibility_inclusion": "RCTs in adults"},
    )
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()
    r = await client.post(
        f"/api/projects/{pid}/reviews/screening/{created['id']}/ai-suggest"
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["vote"] == "maybe"
    # Fetch the screening row back via list — decision must remain "pending"
    rows = (
        await client.get(f"/api/projects/{pid}/reviews/screening")
    ).json()
    row = next(r for r in rows if r["id"] == created["id"])
    assert row["decision"] == "pending"
    assert row["ai_suggestion"]["vote"] == "maybe"


@pytest.mark.asyncio
async def test_ai_suggest_works_when_abstract_is_none(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()
    r = await client.post(
        f"/api/projects/{pid}/reviews/screening/{created['id']}/ai-suggest"
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_ai_suggest_returns_429_on_rate_limit(client, monkeypatch):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()

    async def boom(**_):
        raise AIRateLimited("slow down")

    monkeypatch.setattr(get_container().ai, "suggest_screening", boom)
    r = await client.post(
        f"/api/projects/{pid}/reviews/screening/{created['id']}/ai-suggest"
    )
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_ai_suggest_returns_503_on_provider_unavailable(client, monkeypatch):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()

    async def boom(**_):
        raise AIProviderUnavailable("down")

    monkeypatch.setattr(get_container().ai, "suggest_screening", boom)
    r = await client.post(
        f"/api/projects/{pid}/reviews/screening/{created['id']}/ai-suggest"
    )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_delete_screening_204(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": aid, "stage": "title_abstract"},
        )
    ).json()
    r = await client.delete(
        f"/api/projects/{pid}/reviews/screening/{created['id']}"
    )
    assert r.status_code == 204


# ── Task 10: RoB ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rob_tools_returns_four(client):
    pid = await _make_project_via_api(client)
    r = await client.get(f"/api/projects/{pid}/reviews/rob/tools")
    assert r.status_code == 200
    keys = {t["key"] for t in r.json()}
    assert keys == {"rob2", "robins_i", "nos", "amstar2"}


@pytest.mark.asyncio
async def test_create_rob2_happy(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    r = await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": _rob2_answers_low()},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["overall_auto"] == "low"
    assert body["tool"] == "rob2"


@pytest.mark.asyncio
async def test_create_rob_unknown_domain_returns_422(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    answers = dict(_rob2_answers_low())
    answers["bogus_domain"] = "low"
    r = await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": answers},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_rob_unknown_answer_returns_422(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    answers = dict(_rob2_answers_low())
    answers["randomisation"] = "wat"
    r = await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": answers},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_rob_upsert_idempotent(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    r1 = await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": _rob2_answers_low()},
    )
    high_answers = dict(_rob2_answers_low())
    high_answers["randomisation"] = "high"
    r2 = await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": high_answers},
    )
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["overall_auto"] == "high"


@pytest.mark.asyncio
async def test_patch_rob_re_derives_overall(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/rob",
            json={"article_id": aid, "tool": "rob2", "domain_answers": _rob2_answers_low()},
        )
    ).json()
    high = dict(_rob2_answers_low())
    high["reporting"] = "high"
    r = await client.patch(
        f"/api/projects/{pid}/reviews/rob/{created['id']}",
        json={"domain_answers": high},
    )
    assert r.status_code == 200
    assert r.json()["overall_auto"] == "high"


@pytest.mark.asyncio
async def test_patch_rob_respects_override(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/rob",
            json={"article_id": aid, "tool": "rob2", "domain_answers": _rob2_answers_low()},
        )
    ).json()
    r = await client.patch(
        f"/api/projects/{pid}/reviews/rob/{created['id']}",
        json={"overall_override": "high"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["overall_auto"] == "low"
    assert body["overall_override"] == "high"


@pytest.mark.asyncio
async def test_delete_rob_204(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/rob",
            json={"article_id": aid, "tool": "rob2", "domain_answers": _rob2_answers_low()},
        )
    ).json()
    r = await client.delete(f"/api/projects/{pid}/reviews/rob/{created['id']}")
    assert r.status_code == 204


# ── Task 11: Extraction ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extraction_schema_endpoint(client):
    pid = await _make_project_via_api(client)
    r = await client.get(f"/api/projects/{pid}/reviews/extraction/schema")
    assert r.status_code == 200
    groups = r.json()
    assert {g["key"] for g in groups} >= {"basic", "population", "intervention", "outcomes"}


@pytest.mark.asyncio
async def test_create_extraction_happy(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    r = await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid, "fields": _good_extraction_fields()},
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_create_extraction_missing_required_returns_422(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    fields = _good_extraction_fields()
    fields["basic"].pop("first_author")
    r = await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid, "fields": fields},
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "errors" in detail
    assert "basic" in detail["errors"]


@pytest.mark.asyncio
async def test_extraction_upsert_idempotent(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    r1 = await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid, "fields": _good_extraction_fields()},
    )
    f2 = _good_extraction_fields()
    f2["population"]["n_total"] = 500
    r2 = await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid, "fields": f2},
    )
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["fields"]["population"]["n_total"] == 500


@pytest.mark.asyncio
async def test_patch_extraction_re_validates(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/extraction",
            json={"article_id": aid, "fields": _good_extraction_fields()},
        )
    ).json()
    bad = _good_extraction_fields()
    bad["basic"].pop("year")
    r = await client.patch(
        f"/api/projects/{pid}/reviews/extraction/{created['id']}",
        json={"fields": bad},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_extraction_204(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    created = (
        await client.post(
            f"/api/projects/{pid}/reviews/extraction",
            json={"article_id": aid, "fields": _good_extraction_fields()},
        )
    ).json()
    r = await client.delete(
        f"/api/projects/{pid}/reviews/extraction/{created['id']}"
    )
    assert r.status_code == 204


# ── Task 12: PRISMA + push ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prisma_returns_counts_and_svg(client):
    pid = await _make_project_via_api(client)
    await client.post(
        f"/api/projects/{pid}/reviews/search", json=_search_body(n=10)
    )
    aid = await _seed_article(title="A", project_id=pid, user_id="local-user")
    await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": aid, "stage": "full_text", "decision": "include"},
    )
    r = await client.get(f"/api/projects/{pid}/reviews/prisma")
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["identified"] == 10
    assert body["counts"]["included"] == 1
    assert "<svg" in body["svg"]


@pytest.mark.asyncio
async def test_prisma_push_appends_figure_to_methodology(client):
    pid = await _make_project_via_api(client)
    await client.post(
        f"/api/projects/{pid}/reviews/search", json=_search_body(n=5)
    )
    r = await client.post(f"/api/projects/{pid}/reviews/prisma/push")
    assert r.status_code == 200
    body = r.json()
    assert body["section_name"] == "Methodology"
    assert "<figure" in body["content"]
    assert "data:image/svg+xml;base64," in body["content"]
    # The embedded base64 decodes to SVG
    enc = body["content"].split("base64,")[1].split('"')[0]
    decoded = base64.b64decode(enc).decode("utf-8")
    assert "<svg" in decoded


@pytest.mark.asyncio
async def test_prisma_push_does_not_clobber(client):
    pid = await _make_project_via_api(client)
    # Seed the Methodology section with pre-existing content
    await client.put(
        f"/api/projects/{pid}/sections/Methodology",
        json={"section_name": "Methodology", "content": "<p>Existing content.</p>"},
    )
    r = await client.post(f"/api/projects/{pid}/reviews/prisma/push")
    assert r.status_code == 200
    assert "<p>Existing content.</p>" in r.json()["content"]


@pytest.mark.asyncio
async def test_search_push_renders_table(client):
    pid = await _make_project_via_api(client)
    await client.post(
        f"/api/projects/{pid}/reviews/search",
        json=_search_body(n=7, db="PubMed", q="knee replacement"),
    )
    r = await client.post(f"/api/projects/{pid}/reviews/search/push")
    assert r.status_code == 200
    content = r.json()["content"]
    assert "<table" in content
    assert "PubMed" in content
    assert "knee replacement" in content


@pytest.mark.asyncio
async def test_rob_push_emits_cite_token_per_included_study(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="Study X", project_id=pid, user_id="local-user")
    # Mark it included at full text
    await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": aid, "stage": "full_text", "decision": "include"},
    )
    await client.post(
        f"/api/projects/{pid}/reviews/rob",
        json={"article_id": aid, "tool": "rob2", "domain_answers": _rob2_answers_low()},
    )
    r = await client.post(f"/api/projects/{pid}/reviews/rob/push")
    assert r.status_code == 200
    body = r.json()
    assert body["section_name"] == "Results"
    assert f"[CITE_{aid}]" in body["content"]


@pytest.mark.asyncio
async def test_extraction_push_renders_table_and_cite_tokens(client):
    pid = await _make_project_via_api(client)
    aid = await _seed_article(title="Study X", project_id=pid, user_id="local-user")
    await client.post(
        f"/api/projects/{pid}/reviews/screening",
        json={"article_id": aid, "stage": "full_text", "decision": "include"},
    )
    await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid, "fields": _good_extraction_fields()},
    )
    r = await client.post(f"/api/projects/{pid}/reviews/extraction/push")
    assert r.status_code == 200
    body = r.json()
    assert body["section_name"] == "Results"
    assert f"[CITE_{aid}]" in body["content"]
    assert "TKA" in body["content"]
    assert "WOMAC at 12mo" in body["content"]


@pytest.mark.asyncio
async def test_extraction_push_skips_studies_without_extraction(client):
    pid = await _make_project_via_api(client)
    aid_with = await _seed_article(
        title="With Ext", project_id=pid, user_id="local-user"
    )
    aid_without = await _seed_article(
        title="No Ext", project_id=pid, user_id="local-user"
    )
    for a in (aid_with, aid_without):
        await client.post(
            f"/api/projects/{pid}/reviews/screening",
            json={"article_id": a, "stage": "full_text", "decision": "include"},
        )
    await client.post(
        f"/api/projects/{pid}/reviews/extraction",
        json={"article_id": aid_with, "fields": _good_extraction_fields()},
    )
    r = await client.post(f"/api/projects/{pid}/reviews/extraction/push")
    assert r.status_code == 200
    content = r.json()["content"]
    assert f"[CITE_{aid_with}]" in content
    assert f"[CITE_{aid_without}]" not in content
