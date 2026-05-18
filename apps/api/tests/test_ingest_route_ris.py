"""Phase 8.6 — POST /projects/{pid}/articles/import-ris."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_import_ris_returns_preview_list(client):
    pid = await _make_project(client)
    payload = (FIXTURES / "ris_zotero_sample.ris").read_bytes()
    files = {"file": ("export.ris", payload, "application/x-research-info-systems")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-ris", files=files
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 3
    assert all(item["source"] == "ris" for item in body)


@pytest.mark.asyncio
async def test_import_ris_404_on_other_user_project(client):
    payload = (FIXTURES / "ris_zotero_sample.ris").read_bytes()
    files = {"file": ("export.ris", payload, "application/x-research-info-systems")}
    r = await client.post(
        "/api/projects/missing/articles/import-ris", files=files
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_ris_413_when_oversize(client):
    pid = await _make_project(client)
    big = b"TY  - JOUR\nTI  - x\nER  -\n" + b"x" * (3 * 1024 * 1024)
    files = {"file": ("big.ris", big, "application/x-research-info-systems")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-ris", files=files
    )
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_import_ris_422_when_zero_records(client):
    pid = await _make_project(client)
    # No TY tag → magic-byte sniff rejects
    files = {"file": ("empty.ris", b"this is not RIS", "application/octet-stream")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-ris", files=files
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_import_ris_handles_zotero_export_fixture(client):
    pid = await _make_project(client)
    payload = (FIXTURES / "ris_zotero_sample.ris").read_bytes()
    files = {"file": ("z.ris", payload, "application/x-research-info-systems")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-ris", files=files
    )
    assert r.status_code == 200
    assert len(r.json()) == 3
