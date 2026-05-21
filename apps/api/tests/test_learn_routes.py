"""Phase 5a — Learn routes (read-only, no auth)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_stat_tests_returns_summaries(client) -> None:
    r = await client.get("/api/learn/stat-tests")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 27
    # Summaries carry slug + title + family + short_blurb + worked_example_domain
    sample = body[0]
    assert {"slug", "title", "family", "short_blurb", "worked_example_domain"}.issubset(
        sample.keys()
    )
    # The body should NOT be included in the list view.
    assert "body_md" not in sample
    # Spot-check a known slug.
    slugs = {row["slug"] for row in body}
    assert "independent-t-test" in slugs
    assert "cox-proportional-hazards" in slugs


@pytest.mark.asyncio
async def test_get_stat_test_by_slug_returns_full_entry(client) -> None:
    r = await client.get("/api/learn/stat-tests/paired-t-test")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "paired-t-test"
    assert body["title"] == "Paired samples t-test"
    assert body["family"] == "comparison_of_means"
    assert body["worked_example_domain"] == "orthopaedics"
    assert "Oxford Hip Score" in body["body_md"]
    assert isinstance(body["assumptions"], list) and body["assumptions"]
    assert isinstance(body["alternatives"], list)


@pytest.mark.asyncio
async def test_get_stat_test_404_on_unknown_slug(client) -> None:
    r = await client.get("/api/learn/stat-tests/not-a-real-test")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()
