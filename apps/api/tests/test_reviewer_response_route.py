"""Phase 12 — Reviewer-response route tests (list / create / patch / delete)."""
from __future__ import annotations

import io
import zipfile

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "Knee OA", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_list_empty_initially(client) -> None:
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/reviewer-responses")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_drafts_responses_via_ai(client) -> None:
    pid = await _make_project(client)
    raw = "1. Add power calc.\n\n2. Fix typo."
    r = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "Reviewer 1", "raw_comments": raw},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reviewer_label"] == "Reviewer 1"
    # FakeAIProvider splits on blank lines → two segments.
    assert len(body["comments"]) == 2
    assert "Add power calc" in body["comments"][0]["comment_text"]
    assert "<p>" in body["comments"][0]["response_html"]
    assert "draft_reviewer_response" in client.fake_ai.calls  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_patch_overwrites_comments(client) -> None:
    pid = await _make_project(client)
    create = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "R1", "raw_comments": "Add x"},
    )
    rid = create.json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/reviewer-responses/{rid}",
        json={
            "reviewer_label": "Reviewer A",
            "comments": [
                {"comment_text": "User edited comment", "response_html": "<p>User reply.</p>"}
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reviewer_label"] == "Reviewer A"
    assert body["comments"] == [
        {"comment_text": "User edited comment", "response_html": "<p>User reply.</p>"}
    ]


@pytest.mark.asyncio
async def test_patch_drops_blank_comment_rows(client) -> None:
    pid = await _make_project(client)
    create = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "R1", "raw_comments": "x"},
    )
    rid = create.json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/reviewer-responses/{rid}",
        json={
            "comments": [
                {"comment_text": "   ", "response_html": "<p>x</p>"},
                {"comment_text": "kept", "response_html": ""},
            ]
        },
    )
    assert r.status_code == 200
    assert len(r.json()["comments"]) == 1
    assert r.json()["comments"][0]["comment_text"] == "kept"


@pytest.mark.asyncio
async def test_delete_removes_row(client) -> None:
    pid = await _make_project(client)
    create = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "R1", "raw_comments": "x"},
    )
    rid = create.json()["id"]
    r = await client.delete(
        f"/api/projects/{pid}/reviewer-responses/{rid}"
    )
    assert r.status_code == 204
    list_r = await client.get(f"/api/projects/{pid}/reviewer-responses")
    assert list_r.json() == []


@pytest.mark.asyncio
async def test_create_requires_raw_comments(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "R1", "raw_comments": ""},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_404_when_project_missing(client) -> None:
    r = await client.get("/api/projects/does-not-exist/reviewer-responses")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_404_for_unknown_id(client) -> None:
    pid = await _make_project(client)
    r = await client.patch(
        f"/api/projects/{pid}/reviewer-responses/nope",
        json={"reviewer_label": "x"},
    )
    assert r.status_code == 404


# ── Sub-export sweep — standalone reviewer-response DOCX download ────


@pytest.mark.asyncio
async def test_export_docx_returns_valid_attachment(client) -> None:
    """Regression: reviewer-row needs a single-row DOCX download —
    without it researchers must export the full submission package zip
    just to share one reviewer's response with a co-author.
    """
    pid = await _make_project(client)
    create = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "Reviewer 1", "raw_comments": "1. A.\n\n2. B."},
    )
    rid = create.json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/reviewer-responses/{rid}/export/docx"
    )
    assert r.status_code == 200, r.text
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and ".docx" in cd
    assert r.content[:2] == b"PK"  # DOCX is a zip
    # OOXML compresses document.xml so we can't grep raw bytes — extract.
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
    assert "Reviewer 1" in document_xml
    assert "Comment" in document_xml


@pytest.mark.asyncio
async def test_export_docx_422_when_comments_empty(client) -> None:
    """Regression: an export with zero comments must 422 — emitting an
    empty DOCX confuses reviewers and journal editors."""
    pid = await _make_project(client)
    create = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "R1", "raw_comments": "1. A."},
    )
    rid = create.json()["id"]
    # Clear comments via PATCH
    await client.patch(
        f"/api/projects/{pid}/reviewer-responses/{rid}",
        json={"comments": []},
    )
    r = await client.post(
        f"/api/projects/{pid}/reviewer-responses/{rid}/export/docx"
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_export_docx_404_when_row_missing(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/reviewer-responses/nope/export/docx"
    )
    assert r.status_code == 404
