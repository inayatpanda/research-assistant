"""Phase 5b — Learn routes for the new categories (read-only, no auth)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_checklists_returns_summaries(client) -> None:
    r = await client.get("/api/learn/checklists")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 12
    sample = body[0]
    assert {
        "slug",
        "title",
        "reporting_standard",
        "applies_to_study_types",
        "version",
        "short_blurb",
        "worked_example_domain",
    }.issubset(sample.keys())
    assert "body_md" not in sample
    slugs = {row["slug"] for row in body}
    assert "consort" in slugs
    assert "prisma" in slugs


@pytest.mark.asyncio
async def test_get_checklist_by_slug_returns_full_entry(client) -> None:
    r = await client.get("/api/learn/checklists/consort")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "consort"
    assert body["reporting_standard"] == "CONSORT"
    assert body["official_url"].startswith("http")
    assert "25" in body["body_md"]
    # 404 path
    r404 = await client.get("/api/learn/checklists/not-a-real-checklist")
    assert r404.status_code == 404


@pytest.mark.asyncio
async def test_list_economics_returns_summaries(client) -> None:
    r = await client.get("/api/learn/economics")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 10
    slugs = {row["slug"] for row in body}
    assert "incremental-cost-effectiveness-ratio" in slugs
    assert "quality-adjusted-life-year" in slugs
    sample = body[0]
    assert "concept_family" in sample
    assert "body_md" not in sample


@pytest.mark.asyncio
async def test_get_economics_by_slug_returns_full_entry(client) -> None:
    r = await client.get("/api/learn/economics/incremental-cost-effectiveness-ratio")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "incremental-cost-effectiveness-ratio"
    assert body["concept_family"]
    assert body["formula"]
    assert "QALY" in body["body_md"]
    r404 = await client.get("/api/learn/economics/no-such-concept")
    assert r404.status_code == 404


@pytest.mark.asyncio
async def test_list_submission_returns_summaries(client) -> None:
    r = await client.get("/api/learn/submission")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 11
    families = {row["topic_family"] for row in body}
    assert {"planning", "writing", "submitting", "post-decision"}.issubset(families)
    slugs = {row["slug"] for row in body}
    assert "cover-letter" in slugs
    assert "response-to-reviewers" in slugs


@pytest.mark.asyncio
async def test_get_submission_by_slug_and_search(client) -> None:
    r = await client.get("/api/learn/submission/cover-letter")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "cover-letter"
    assert body["topic"] == "cover-letter"
    assert body["topic_family"] == "writing"

    r404 = await client.get("/api/learn/submission/no-such-topic")
    assert r404.status_code == 404

    # Search should reach across categories.
    rs = await client.get("/api/learn/search", params={"q": "qaly"})
    assert rs.status_code == 200, rs.text
    hits = rs.json()
    assert isinstance(hits, list)
    assert hits, "expected at least one search hit for 'qaly'"
    categories = {h["category"] for h in hits}
    assert "economics" in categories
