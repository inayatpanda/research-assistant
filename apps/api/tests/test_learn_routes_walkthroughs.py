"""Phase 5c — Walkthrough HTTP routes."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_walkthroughs_returns_summaries(client) -> None:
    r = await client.get("/api/learn/walkthroughs")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 4
    slugs = {row["slug"] for row in body}
    expected = {
        "systematic-review-from-scratch",
        "rct-write-up",
        "observational-study-write-up",
        "meta-analysis-walkthrough",
    }
    assert slugs == expected
    sample = body[0]
    assert {
        "slug",
        "title",
        "study_type",
        "estimated_reading_minutes",
        "sections",
        "short_blurb",
        "worked_example_domain",
    }.issubset(sample.keys())
    assert "body_md" not in sample


@pytest.mark.asyncio
async def test_get_walkthrough_by_slug_returns_full_entry(client) -> None:
    r = await client.get("/api/learn/walkthroughs/systematic-review-from-scratch")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "systematic-review-from-scratch"
    assert body["study_type"] == "systematic_review"
    assert body["estimated_reading_minutes"] >= 10
    assert body["worked_example_domain"] == "orthopaedics"
    assert isinstance(body["sections"], list) and len(body["sections"]) >= 5
    assert "PRISMA" in body["body_md"]


@pytest.mark.asyncio
async def test_walkthrough_404(client) -> None:
    r = await client.get("/api/learn/walkthroughs/no-such-walkthrough")
    assert r.status_code == 404
