"""End-to-end tests for /api/articles routes.

Uses the FakeAIProvider from conftest — no real Gemini calls.
"""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


async def _make_project(client, title="P", study_type="Outcome Study") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": study_type}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_upload_pipeline_happy_path(client):
    project_id = await _make_project(client)
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    r = await client.post(f"/api/projects/{project_id}/articles/upload", files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["article"]["title"] == "Fake Title from AI"
    assert body["article"]["authors"] == ["First Author", "Second Author"]
    assert body["article"]["file_url"]
    assert body["article"]["file_url"].startswith("/files/")
    assert body["duplicate_of"] is None
    assert body["extraction_source"] in {"ai", "both"}


@pytest.mark.asyncio
async def test_upload_returns_413_for_oversize(client):
    project_id = await _make_project(client)
    big = b"%PDF-1.4 " + b"x" * (60 * 1024 * 1024)  # 60 MB > 50 cap
    files = {"file": ("big.pdf", big, "application/pdf")}
    r = await client.post(f"/api/projects/{project_id}/articles/upload", files=files)
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_upload_returns_415_for_unsupported_mime(client):
    project_id = await _make_project(client)
    files = {"file": ("note.txt", b"plain text only", "text/plain")}
    r = await client.post(f"/api/projects/{project_id}/articles/upload", files=files)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_upload_returns_400_for_empty(client):
    project_id = await _make_project(client)
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    r = await client.post(f"/api/projects/{project_id}/articles/upload", files=files)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_upload_returns_404_for_missing_project(client):
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    r = await client.post(
        "/api/projects/nonexistent/articles/upload", files=files
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_detection_on_second_upload(client):
    project_id = await _make_project(client)
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}

    first = await client.post(f"/api/projects/{project_id}/articles/upload", files=files)
    assert first.status_code == 201

    second = await client.post(
        f"/api/projects/{project_id}/articles/upload",
        files={"file": ("same-doi.pdf", pdf, "application/pdf")},
    )
    assert second.status_code == 201
    body = second.json()
    assert body["duplicate_of"] is not None
    assert body["duplicate_of"]["id"] == first.json()["article"]["id"]


@pytest.mark.asyncio
async def test_list_articles_with_filters(client):
    project_id = await _make_project(client)
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    await client.post(f"/api/projects/{project_id}/articles/upload", files=files)

    r = await client.get(f"/api/projects/{project_id}/articles")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r2 = await client.get(f"/api/projects/{project_id}/articles?q=Fake")
    assert len(r2.json()) == 1
    r3 = await client.get(f"/api/projects/{project_id}/articles?q=zzz-nope")
    assert len(r3.json()) == 0


@pytest.mark.asyncio
async def test_patch_article(client):
    project_id = await _make_project(client)
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    upload = await client.post(
        f"/api/projects/{project_id}/articles/upload", files=files
    )
    aid = upload.json()["article"]["id"]

    r = await client.patch(
        f"/api/articles/{aid}",
        json={"review_status": "included", "study_design": "RCT"},
    )
    assert r.status_code == 200
    assert r.json()["review_status"] == "included"
    assert r.json()["study_design"] == "RCT"


@pytest.mark.asyncio
async def test_delete_article(client):
    project_id = await _make_project(client)
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    upload = await client.post(
        f"/api/projects/{project_id}/articles/upload", files=files
    )
    aid = upload.json()["article"]["id"]
    r = await client.delete(f"/api/articles/{aid}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/articles/{aid}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_articles_invalid_sort_falls_back_to_created_desc(client):
    """Bogus ?sort=... should NOT 500 — it must be coerced (#L-sort-500)."""
    project_id = await _make_project(client)
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    files = {"file": ("paper.pdf", pdf, "application/pdf")}
    await client.post(f"/api/projects/{project_id}/articles/upload", files=files)

    for bogus in ("title_asc", "title_desc", "authors_asc", "foobar"):
        r = await client.get(
            f"/api/projects/{project_id}/articles", params={"sort": bogus}
        )
        assert r.status_code == 200, (bogus, r.status_code, r.text)
        assert isinstance(r.json(), list)
