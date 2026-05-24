"""F2.4 — Bulk upload race / concurrency sanity check.

The frontend fires up to 4 concurrent ``POST /upload`` requests. The
backend does *not* eagerly rebuild any project-wide artefact on upload
(bibliography is built on demand at export time), so concurrent uploads
should land cleanly without serialisation contention.

These tests are the safety net that catches future regressions where
someone adds a synchronous "rebuild bibliography" step inside the upload
route and torpedoes bulk mode.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_four_concurrent_uploads_all_succeed(client, monkeypatch):
    """Four parallel uploads to the same project all return 201."""
    project_id = await _make_project(client)

    # Stub the cheap autofill so the test doesn't depend on the deterministic
    # sample.pdf text-extraction path (which yields very little text).
    async def fake_autofill(_bytes: bytes):
        return {
            "fields": {"title": "Concurrent Upload Stub"},
            "provenance": {"title": "heuristic"},
            "autofill_status": "heuristic_only",
            "doi_candidate": None,
        }

    import research_api.routes.articles as routes_articles

    monkeypatch.setattr(routes_articles, "extract_metadata_for_pdf", fake_autofill)

    pdf = (FIXTURES / "sample.pdf").read_bytes()

    async def upload(i: int):
        files = {"file": (f"paper-{i}.pdf", pdf, "application/pdf")}
        return await client.post(
            f"/api/projects/{project_id}/articles/upload?use_ai=false",
            files=files,
        )

    responses = await asyncio.gather(*[upload(i) for i in range(4)])
    assert [r.status_code for r in responses] == [201, 201, 201, 201]

    # All four rows are persisted (duplicate detector may flag overlap but
    # never blocks the row from being created).
    list_r = await client.get(f"/api/projects/{project_id}/articles")
    assert list_r.status_code == 200
    assert len(list_r.json()) == 4


@pytest.mark.asyncio
async def test_upload_does_not_rebuild_bibliography_eagerly(client, monkeypatch):
    """The upload route must not invoke ``build_bibliography`` synchronously.

    Bulk upload mode depends on this guarantee — if every upload triggered
    a full bibliography rebuild, 50 concurrent uploads would O(N²) the
    server. This test wraps ``build_bibliography`` and asserts the upload
    pipeline never calls it.
    """
    project_id = await _make_project(client)

    from research_api.services.export import bibliography as bib_mod

    call_count = 0
    original = bib_mod.build_bibliography

    def counting_build(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(bib_mod, "build_bibliography", counting_build)

    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    r = await client.post(
        f"/api/projects/{project_id}/articles/upload?use_ai=false", files=files
    )
    assert r.status_code == 201
    assert call_count == 0, (
        f"build_bibliography was called {call_count} times during upload — "
        "bulk uploads would amplify this into a thundering herd."
    )
