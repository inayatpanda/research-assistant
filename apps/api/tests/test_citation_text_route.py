"""MP16 — POST /projects/{pid}/articles/import-from-text."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

FIXTURES = Path(__file__).parent / "fixtures"


def _crossref_sample() -> dict:
    return json.loads((FIXTURES / "crossref_sample.json").read_text())


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_import_from_text_happy_path_with_doi(client):
    """A pasted Vancouver-style reference with a DOI resolves to the
    Crossref-derived metadata and is returned as ``status='ok'``."""
    pid = await _make_project(client)
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.1056/NEJMoa2110345").mock(
            return_value=Response(200, json=_crossref_sample())
        )
        r = await client.post(
            f"/api/projects/{pid}/articles/import-from-text",
            json={
                "text": (
                    "1. Patel S, Ricci M, Andersson L. Anterior vs Posterior. "
                    "N Engl J Med 2023;389(2):123-134. doi:10.1056/NEJMoa2110345"
                )
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["status"] == "ok"
    assert item["doi"] == "10.1056/NEJMoa2110345"
    assert item["parsed_metadata"]["title"].startswith("Anterior versus Posterior")


@pytest.mark.asyncio
async def test_import_from_text_returns_unresolved_when_crossref_404s(client):
    pid = await _make_project(client)
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.9999/missing").mock(return_value=Response(404))
        # Disable fuzzy fallback so we get a clean "unresolved" result.
        r = await client.post(
            f"/api/projects/{pid}/articles/import-from-text",
            json={
                "text": "1. Doe J. Missing reference. doi:10.9999/missing",
                "fuzzy_title_lookup": False,
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["status"] == "unresolved"
    assert item["doi"] == "10.9999/missing"
    assert item["parsed_metadata"] is None


@pytest.mark.asyncio
async def test_import_from_text_splits_multiple_fragments(client):
    pid = await _make_project(client)
    text = (
        "1. Doe J. Title one. doi:10.1056/NEJMoa2110345\n"
        "2. Smith K. Title two no identifier."
    )
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.1056/NEJMoa2110345").mock(
            return_value=Response(200, json=_crossref_sample())
        )
        r = await client.post(
            f"/api/projects/{pid}/articles/import-from-text",
            json={"text": text, "fuzzy_title_lookup": False},
        )
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["status"] == "ok"
    assert body["items"][1]["status"] == "unresolved"


@pytest.mark.asyncio
async def test_import_from_text_404_on_unknown_project(client):
    r = await client.post(
        "/api/projects/does-not-exist/articles/import-from-text",
        json={"text": "1. Doe J. Title. doi:10.1234/abc"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_from_text_422_on_empty_body(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-text",
        json={"text": ""},
    )
    assert r.status_code == 422
