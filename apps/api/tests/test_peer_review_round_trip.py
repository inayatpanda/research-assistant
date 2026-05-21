"""Phase 4.6 — Bundle export/import round-trip for ``peer_reviews``."""
from __future__ import annotations

import json

import pytest


async def _project_with_manuscript(client) -> str:
    r = await client.post(
        "/api/projects",
        json={
            "title": "Bundle peer-review",
            "study_type": "Randomised Controlled Trial",
        },
    )
    pid = r.json()["id"]
    long_body = (
        "Background: a randomised trial. "
        "Methods: 80 patients randomised to widget or sham. "
        "Results: widget arm improved by 5.3 points (p=0.002). "
        "Discussion: results extend prior data. "
    ) * 2
    for name in ("Abstract", "Introduction", "Methodology", "Results", "Discussion"):
        await client.put(
            f"/api/projects/{pid}/sections/{name}",
            json={"section_name": name, "content": long_body},
        )
    return pid


@pytest.mark.asyncio
async def test_bundle_round_trip_carries_peer_reviews(client) -> None:
    pid = await _project_with_manuscript(client)

    r = await client.post(f"/api/projects/{pid}/peer-reviews/manuscript")
    assert r.status_code == 201, r.text
    original = r.json()

    # Export.
    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    bundle = exp.json()
    assert len(bundle["peer_reviews"]) == 1
    exported = bundle["peer_reviews"][0]
    assert exported["recommendation"] == original["recommendation"]
    assert exported["source_type"] == "manuscript"
    assert exported["status"] == "completed"

    # Re-import into a fresh project.
    imp = await client.post(
        "/api/projects/import/bundle",
        files={
            "file": (
                "bundle.json",
                json.dumps(bundle).encode("utf-8"),
                "application/json",
            )
        },
    )
    assert imp.status_code in (200, 201), imp.text
    counts = imp.json().get("counts", imp.json())
    assert counts["peer_reviews"] == 1
