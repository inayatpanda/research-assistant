"""Phase 4.6 — Peer-review route happy paths."""
from __future__ import annotations

import io

import pytest
from docx import Document as DocxDocument
from pypdf import PdfWriter


async def _make_project_with_manuscript(client) -> str:
    r = await client.post(
        "/api/projects",
        json={
            "title": "Trial of widgets",
            "study_type": "Randomised Controlled Trial",
        },
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    # Seed manuscript sections — keep each long enough so the combined
    # text comfortably exceeds the 200-char minimum.
    sections = {
        "Abstract": "Background: widgets are commonly used. Methods: 80 patients were randomised. Results: outcomes favoured the intervention. Conclusion: widgets help.",
        "Introduction": "Widgets are commonly used in clinical practice but their efficacy has not been rigorously established by prior trials.",
        "Methodology": "We randomised 80 patients to either widget or sham. Outcomes were recorded at six weeks by blinded assessors.",
        "Results": "The mean improvement was 5.3 points in the widget arm vs 2.1 points in the sham arm (p=0.002).",
        "Discussion": "Our findings extend prior observational data and support routine use of widgets in selected patients.",
        "Conclusion": "Widgets reduce symptoms compared with sham at six weeks.",
    }
    for name, content in sections.items():
        sec = await client.put(
            f"/api/projects/{pid}/sections/{name}",
            json={"section_name": name, "content": content},
        )
        assert sec.status_code == 200, sec.text
    return pid


def _make_docx_bytes(text: str) -> bytes:
    doc = DocxDocument()
    for ln in text.splitlines():
        if ln.strip():
            doc.add_paragraph(ln)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_generate_from_manuscript_happy_path(client) -> None:
    pid = await _make_project_with_manuscript(client)

    r = await client.post(f"/api/projects/{pid}/peer-reviews/manuscript")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_type"] == "manuscript"
    assert body["status"] == "completed"
    assert body["recommendation"] in {
        "reject",
        "major_revision",
        "minor_revision",
        "accept",
    }
    critique = body["critique"]
    assert isinstance(critique.get("strengths"), list)
    assert "fake-model" not in body["ai_model"]  # uses configured model name
    # The snapshot preserves sections at review time.
    snap = body["manuscript_snapshot"]
    assert isinstance(snap, dict)
    assert "Methodology" in snap["sections"]


@pytest.mark.asyncio
async def test_generate_from_upload_docx_happy_path(client) -> None:
    pid = await _make_project_with_manuscript(client)
    # Pad text so it exceeds the 200-char threshold the route enforces.
    long_text = "Methods of this study were rigorous. " * 30
    docx_bytes = _make_docx_bytes(long_text)
    files = {"file": ("paper.docx", docx_bytes, "application/octet-stream")}
    r = await client.post(
        f"/api/projects/{pid}/peer-reviews/upload", files=files
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_type"] == "uploaded_docx"
    assert body["status"] == "completed"
    assert body["source_file_ref"]["filename"] == "paper.docx"


@pytest.mark.asyncio
async def test_list_and_get_peer_reviews(client) -> None:
    pid = await _make_project_with_manuscript(client)
    a = await client.post(f"/api/projects/{pid}/peer-reviews/manuscript")
    b = await client.post(f"/api/projects/{pid}/peer-reviews/manuscript")
    assert a.status_code == 201 and b.status_code == 201

    r = await client.get(f"/api/projects/{pid}/peer-reviews")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    # Latest first.
    assert rows[0]["created_at"] >= rows[1]["created_at"]

    one = await client.get(
        f"/api/projects/{pid}/peer-reviews/{rows[0]['id']}"
    )
    assert one.status_code == 200
    assert one.json()["id"] == rows[0]["id"]


@pytest.mark.asyncio
async def test_delete_peer_review_removes_row(client) -> None:
    pid = await _make_project_with_manuscript(client)
    r = await client.post(f"/api/projects/{pid}/peer-reviews/manuscript")
    rid = r.json()["id"]

    d = await client.delete(f"/api/projects/{pid}/peer-reviews/{rid}")
    assert d.status_code == 204

    g = await client.get(f"/api/projects/{pid}/peer-reviews/{rid}")
    assert g.status_code == 404


@pytest.mark.asyncio
async def test_export_peer_review_pdf_and_docx(client) -> None:
    pid = await _make_project_with_manuscript(client)
    r = await client.post(f"/api/projects/{pid}/peer-reviews/manuscript")
    rid = r.json()["id"]

    pdf = await client.post(
        f"/api/projects/{pid}/peer-reviews/{rid}/export",
        params={"format": "pdf"},
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-"

    docx = await client.post(
        f"/api/projects/{pid}/peer-reviews/{rid}/export",
        params={"format": "docx"},
    )
    assert docx.status_code == 200
    # DOCX files are zip archives.
    assert docx.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_upload_rejects_non_document(client) -> None:
    pid = await _make_project_with_manuscript(client)
    files = {
        "file": ("note.txt", b"plain text only", "application/octet-stream")
    }
    r = await client.post(
        f"/api/projects/{pid}/peer-reviews/upload", files=files
    )
    assert r.status_code == 415
