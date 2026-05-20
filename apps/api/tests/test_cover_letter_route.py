"""Phase 12 — Cover-letter route tests (GET / PATCH / POST draft)."""
from __future__ import annotations

import io
import zipfile

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "Knee OA Study", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_get_auto_creates_empty_cover_letter(client) -> None:
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/cover-letter")
    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == pid
    assert body["target_journal"] is None
    assert body["novelty_points"] == []
    assert body["body_html"] == ""
    assert body["ai_model"] is None


@pytest.mark.asyncio
async def test_patch_updates_fields(client) -> None:
    pid = await _make_project(client)
    await client.get(f"/api/projects/{pid}/cover-letter")  # ensure row
    r = await client.patch(
        f"/api/projects/{pid}/cover-letter",
        json={
            "target_journal": "jbjs",
            "novelty_points": ["A", "B", "C"],
            "body_html": "<p>hello</p>",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_journal"] == "jbjs"
    assert body["novelty_points"] == ["A", "B", "C"]
    assert body["body_html"] == "<p>hello</p>"


@pytest.mark.asyncio
async def test_patch_rejects_unknown_journal(client) -> None:
    pid = await _make_project(client)
    r = await client.patch(
        f"/api/projects/{pid}/cover-letter",
        json={"target_journal": "nature-knees"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_draft_requires_target_journal(client) -> None:
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/cover-letter/draft", json={})
    # Without a journal selected the route 422s.
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_draft_populates_body_html_and_model(client) -> None:
    pid = await _make_project(client)
    # Set journal + novelty up front.
    await client.patch(
        f"/api/projects/{pid}/cover-letter",
        json={
            "target_journal": "jbjs",
            "novelty_points": ["First multicentre RCT", "Long follow-up"],
        },
    )
    r = await client.post(
        f"/api/projects/{pid}/cover-letter/draft", json={}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "Dear Editor" in body["body_html"]
    assert body["ai_model"] == "fake-model"
    assert "draft_cover_letter" in client.fake_ai.calls  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_draft_accepts_override_journal_and_novelty(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/cover-letter/draft",
        json={"target_journal": "bjj", "novelty_points": ["Only bullet"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_journal"] == "bjj"
    assert body["novelty_points"] == ["Only bullet"]


@pytest.mark.asyncio
async def test_404_when_project_missing(client) -> None:
    r = await client.get("/api/projects/does-not-exist/cover-letter")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_novelty_points_trimmed_blank(client) -> None:
    pid = await _make_project(client)
    r = await client.patch(
        f"/api/projects/{pid}/cover-letter",
        json={"novelty_points": ["", "  ", "real"]},
    )
    assert r.status_code == 200
    assert r.json()["novelty_points"] == ["real"]


# ── Sub-export sweep — standalone cover-letter DOCX download ─────────


@pytest.mark.asyncio
async def test_export_docx_returns_valid_attachment(client) -> None:
    """Regression: cover-letter editor needs a standalone DOCX download —
    without it researchers must export the entire submission package zip
    just to email the cover letter to a co-author for review.
    """
    pid = await _make_project(client)
    await client.patch(
        f"/api/projects/{pid}/cover-letter",
        json={
            "target_journal": "jbjs",
            "body_html": "<p>Dear Editor,</p><p>Please consider …</p>",
        },
    )
    r = await client.post(f"/api/projects/{pid}/cover-letter/export/docx")
    assert r.status_code == 200, r.text
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and ".docx" in cd
    # DOCX is a zip — magic bytes start with 'PK'
    assert r.content[:2] == b"PK"
    # Unzip the OOXML container and confirm the body text + title landed
    # in document.xml. The whole file is gzipped so a raw `in` check on the
    # response bytes won't find the words — extract and read instead.
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
    assert "Dear Editor" in document_xml
    assert "Cover Letter" in document_xml


@pytest.mark.asyncio
async def test_export_docx_422_when_body_empty(client) -> None:
    """Regression: emitting a blank DOCX confuses the user — must 422."""
    pid = await _make_project(client)
    # Auto-creates an empty row; no body_html.
    r = await client.post(f"/api/projects/{pid}/cover-letter/export/docx")
    assert r.status_code == 422
    assert "empty" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_export_docx_404_when_project_missing(client) -> None:
    r = await client.post(
        "/api/projects/does-not-exist/cover-letter/export/docx"
    )
    assert r.status_code == 404
