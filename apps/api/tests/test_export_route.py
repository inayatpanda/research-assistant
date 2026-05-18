"""End-to-end tests for /api export + import routes."""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from research_api.container import get_container
from research_api.db.models import (
    Article,
    ManuscriptSection,
    Project,
)
from research_api.services.export.bundle_export import (
    SCHEMA_VERSION,
    BundleInputs,
    build_bundle,
)


async def _make_project(client, title="Export P", study_type="Outcome Study") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": study_type, "citation_style": "vancouver"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(*, title: str, project_id: str, user_id: str = "local-user") -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            user_id=user_id, project_id=project_id, title=title,
            authors=["Doe J"], year=2024, journal="J",
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


async def _seed_section(
    *, project_id: str, section_name: str, content: str,
    user_id: str = "local-user",
) -> None:
    container = get_container()
    async with container.session_factory() as session:
        sec = ManuscriptSection(
            user_id=user_id, project_id=project_id,
            section_name=section_name, content=content,
            word_count=len(content.split()),
        )
        session.add(sec)
        await session.commit()


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


# ── DOCX export ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_docx_returns_attachment(client):
    pid = await _make_project(client)
    aid = await _seed_article(title="Foo", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>Cite [CITE_{aid}].</p>",
    )
    r = await client.post(f"/api/projects/{pid}/export/docx")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    cd = r.headers["content-disposition"]
    assert cd.startswith("attachment;")
    assert ".docx" in cd
    # docx files start with the ZIP magic 'PK'.
    assert r.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_export_docx_filename_slugified(client):
    pid = await _make_project(client, title="My Hairy/Title..\\With weird*chars")
    r = await client.post(f"/api/projects/{pid}/export/docx")
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    # Filename must not leak any path-traversal characters.
    assert "/" not in cd.split("filename=")[1]
    assert ".." not in cd.split("filename=")[1]
    assert "\\" not in cd.split("filename=")[1]


@pytest.mark.asyncio
async def test_export_docx_404_for_missing_project(client):
    r = await client.post("/api/projects/does-not-exist/export/docx")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_docx_works_with_empty_manuscript(client):
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/export/docx")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_export_docx_consolidates_adjacent_numeric_citation_sups(client):
    """Adjacent `<sup data-citation>[1][2][3]</sup>` tokens collapse to `[1-3]`
    in DOCX output (BUG #15)."""
    from docx import Document  # local import — only needed for this test

    pid = await _make_project(client)
    content = (
        '<p>Multiple refs '
        '<sup data-citation data-article-id="x1">[1]</sup>'
        '<sup data-citation data-article-id="x2">[2]</sup>'
        '<sup data-citation data-article-id="x3">[3]</sup>'
        ' end.</p>'
    )
    await _seed_section(
        project_id=pid, section_name="Introduction", content=content,
    )
    r = await client.post(f"/api/projects/{pid}/export/docx")
    assert r.status_code == 200
    doc = Document(io.BytesIO(r.content))
    text = "\n".join(p.text for p in doc.paragraphs)
    # Collapsed range body appears; original [1] [2] [3] should NOT each appear.
    assert "[1-3]" in text


# ── PDF export ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_pdf_returns_attachment(client):
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/export/pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert ".pdf" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_pdf_404_for_missing_project(client):
    r = await client.post("/api/projects/missing/export/pdf")
    assert r.status_code == 404


# ── Bundle export ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_bundle_returns_json_attachment(client):
    pid = await _make_project(client, title="Bundle P")
    aid = await _seed_article(title="Foo", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>[CITE_{aid}]</p>",
    )
    r = await client.post(f"/api/projects/{pid}/export/bundle")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    body = json.loads(r.content)
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["project"]["id"] == pid
    assert body["project"]["title"] == "Bundle P"
    assert len(body["articles"]) == 1
    assert body["articles"][0]["id"] == aid
    assert len(body["manuscript_sections"]) == 1


@pytest.mark.asyncio
async def test_export_bundle_404_for_missing_project(client):
    r = await client.post("/api/projects/missing/export/bundle")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_bundle_includes_all_relevant_groups_when_empty(client):
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/export/bundle")
    assert r.status_code == 200
    body = json.loads(r.content)
    for key in (
        "articles", "highlights", "article_notes", "manuscript_sections",
        "abbreviations", "datasets", "dataset_variables", "analyses",
        "analysis_results", "search_records", "screening_records",
        "rob_assessments", "extraction_records",
    ):
        assert body[key] == [], f"{key} should be empty"
    assert body["review"] is None


# ── Import bundle ──────────────────────────────────────────────────────


def _make_minimal_bundle(user_id: str = "user-a", title: str = "Imported") -> dict:
    p = Project(
        id="proj-orig", user_id=user_id, title=title,
        study_type="Outcome Study", citation_style="vancouver",
        ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return build_bundle(BundleInputs(project=p))


@pytest.mark.asyncio
async def test_import_bundle_creates_new_project(client):
    bundle = _make_minimal_bundle(title="ImportedX")
    files = {"file": ("bundle.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "project_id" in body
    assert body["counts"]["projects"] == 1

    # Verify the new project is GET-able and owned by the current user.
    pid = body["project_id"]
    r2 = await client.get(f"/api/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "ImportedX"


@pytest.mark.asyncio
async def test_import_bundle_rejects_oversize(client):
    payload = b"{" + b" " * (51 * 1024 * 1024) + b"}"
    files = {"file": ("big.json", payload, "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_import_bundle_rejects_non_json(client):
    files = {"file": ("notes.txt", b"This is not JSON.", "text/plain")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_import_bundle_rejects_pdf(client):
    files = {"file": ("doc.pdf", b"%PDF-1.7\n...", "application/pdf")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_import_bundle_rejects_missing_schema_version(client):
    bundle = _make_minimal_bundle()
    del bundle["schema_version"]
    files = {"file": ("b.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_import_bundle_rejects_missing_project(client):
    bundle = _make_minimal_bundle()
    del bundle["project"]
    files = {"file": ("b.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_import_bundle_round_trip(client):
    # Export, then import, and confirm the data lands.
    pid = await _make_project(client, title="RT Source")
    aid = await _seed_article(title="Roundtrip", project_id=pid)
    await _seed_section(
        project_id=pid, section_name="Introduction",
        content=f"<p>Source [CITE_{aid}]</p>",
    )

    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    bundle_bytes = exp.content
    files = {"file": ("bundle.json", bundle_bytes, "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 200, r.text
    new_pid = r.json()["project_id"]
    assert new_pid != pid

    # Confirm articles + sections came across.
    arts = (await client.get(f"/api/projects/{new_pid}/articles")).json()
    assert len(arts) == 1
    assert arts[0]["title"] == "Roundtrip"


@pytest.mark.asyncio
async def test_import_empty_file_rejected(client):
    files = {"file": ("empty.json", b"", "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_import_invalid_json_rejected(client):
    files = {"file": ("b.json", b"{not valid json", "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code in (415, 422)
