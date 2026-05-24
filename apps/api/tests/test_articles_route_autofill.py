"""F1 — Upload route runs the cheap autofill path before AI.

Verifies:
  - DOI hit → ``autofill_status=doi_match``, fields stamped with ``"doi"``
  - DOI miss + non-empty heuristic → ``autofill_status=heuristic_only``
  - ``?use_ai=false`` opts out of Gemini so bulk uploads don't burn money
"""
from __future__ import annotations

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
async def test_upload_with_doi_match_stamps_provenance(client, monkeypatch):
    project_id = await _make_project(client)

    async def fake_autofill(_bytes: bytes):
        return {
            "fields": {
                "title": "Crossref-Resolved Title",
                "journal": "The Journal of Made Up Things",
                "year": 2024,
                "doi": "10.9999/fake.doi",
            },
            "provenance": {
                "title": "doi",
                "journal": "doi",
                "year": "doi",
                "doi": "doi",
            },
            "autofill_status": "doi_match",
            "doi_candidate": "10.9999/fake.doi",
        }

    import research_api.routes.articles as routes_articles

    monkeypatch.setattr(routes_articles, "extract_metadata_for_pdf", fake_autofill)

    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    # use_ai=false → the FakeAIProvider should NOT be consulted; the cheap
    # path's fields are what land in the row.
    r = await client.post(
        f"/api/projects/{project_id}/articles/upload?use_ai=false", files=files
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["autofill_status"] == "doi_match"
    assert body["autofilled_by"]["title"] == "doi"
    assert body["autofilled_by"]["doi"] == "doi"
    assert body["article"]["title"] == "Crossref-Resolved Title"
    assert body["article"]["doi"] == "10.9999/fake.doi"
    assert body["article"]["journal"] == "The Journal of Made Up Things"
    assert body["article"]["year"] == 2024
    # AI was skipped → no AI fake calls recorded.
    assert "extract_citation" not in client.fake_ai.calls  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_upload_heuristic_only_when_no_doi(client, monkeypatch):
    project_id = await _make_project(client)

    async def fake_autofill(_bytes: bytes):
        return {
            "fields": {"title": "Heuristic Guess Title", "year": 2019},
            "provenance": {"title": "heuristic", "year": "heuristic"},
            "autofill_status": "heuristic_only",
            "doi_candidate": None,
        }

    import research_api.routes.articles as routes_articles

    monkeypatch.setattr(routes_articles, "extract_metadata_for_pdf", fake_autofill)

    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    r = await client.post(
        f"/api/projects/{project_id}/articles/upload?use_ai=false", files=files
    )
    assert r.status_code == 201
    body = r.json()
    assert body["autofill_status"] == "heuristic_only"
    assert body["autofilled_by"] == {"title": "heuristic", "year": "heuristic"}
    assert body["article"]["title"] == "Heuristic Guess Title"
    assert body["article"]["year"] == 2019


@pytest.mark.asyncio
async def test_upload_failed_autofill_falls_back_to_filename(client, monkeypatch):
    project_id = await _make_project(client)

    async def fake_autofill(_bytes: bytes):
        return {
            "fields": {},
            "provenance": {},
            "autofill_status": "failed",
            "doi_candidate": None,
        }

    import research_api.routes.articles as routes_articles

    monkeypatch.setattr(routes_articles, "extract_metadata_for_pdf", fake_autofill)

    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    r = await client.post(
        f"/api/projects/{project_id}/articles/upload?use_ai=false", files=files
    )
    assert r.status_code == 201
    body = r.json()
    assert body["autofill_status"] == "failed"
    assert body["autofilled_by"] == {}
    # Filename fallback kicks in when both paths return nothing.
    assert body["article"]["title"] == "paper.pdf"
