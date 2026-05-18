"""Phase 8.6 — POST /projects/{pid}/articles/import-bibtex."""
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
async def test_import_bibtex_returns_preview_list(client):
    pid = await _make_project(client)
    payload = (FIXTURES / "bibtex_zotero_sample.bib").read_bytes()
    files = {"file": ("export.bib", payload, "application/x-bibtex")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-bibtex", files=files
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 2
    assert all(item["source"] == "bibtex" for item in body)


@pytest.mark.asyncio
async def test_import_bibtex_404_on_other_user_project(client):
    payload = (FIXTURES / "bibtex_zotero_sample.bib").read_bytes()
    files = {"file": ("export.bib", payload, "application/x-bibtex")}
    r = await client.post(
        "/api/projects/missing/articles/import-bibtex", files=files
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_bibtex_413_when_oversize(client):
    pid = await _make_project(client)
    big = b"@article{x, title={t}, author={A}, year={2023}}\n" + b"x" * (3 * 1024 * 1024)
    files = {"file": ("big.bib", big, "application/x-bibtex")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-bibtex", files=files
    )
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_import_bibtex_422_when_zero_records(client):
    pid = await _make_project(client)
    files = {"file": ("plain.bib", b"no bibtex content here", "text/plain")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-bibtex", files=files
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_import_bibtex_handles_zotero_mendeley_googlescholar_fixtures(client):
    pid = await _make_project(client)
    for name, expected_count in (
        ("bibtex_zotero_sample.bib", 2),
        ("bibtex_mendeley_sample.bib", 1),
        ("bibtex_googlescholar_sample.bib", 2),
    ):
        payload = (FIXTURES / name).read_bytes()
        files = {"file": (name, payload, "application/x-bibtex")}
        r = await client.post(
            f"/api/projects/{pid}/articles/import-bibtex", files=files
        )
        assert r.status_code == 200, r.text
        assert len(r.json()) == expected_count
