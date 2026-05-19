"""Phase 14 (MP14) — PROSPERO draft routes."""
from __future__ import annotations

import pytest

from research_api.container import get_container


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "My PROSPERO review") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Systematic Review"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_get_prospero_auto_creates_with_22_fields(client):
    _switch_user("user-a")
    pid = await _make_project(client, "Stroke SR")
    r = await client.get(f"/api/projects/{pid}/review/prospero")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "fields" in payload
    fields = payload["fields"]
    assert isinstance(fields, dict)
    assert len(fields) == 22
    assert fields["title"] == "Stroke SR"


@pytest.mark.asyncio
async def test_get_prospero_is_stable_across_calls(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r1 = await client.get(f"/api/projects/{pid}/review/prospero")
    r2 = await client.get(f"/api/projects/{pid}/review/prospero")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_patch_prospero_merges_into_existing(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.get(f"/api/projects/{pid}/review/prospero")

    r = await client.patch(
        f"/api/projects/{pid}/review/prospero",
        json={"fields": {"named_contact": "Dr A", "named_contact_email": "a@x.com"}},
    )
    assert r.status_code == 200, r.text
    fields = r.json()["fields"]
    assert fields["named_contact"] == "Dr A"
    assert fields["named_contact_email"] == "a@x.com"
    # Original auto-filled title should survive the merge.
    assert fields["title"] != ""


@pytest.mark.asyncio
async def test_patch_prospero_creates_when_absent(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    # Skip the initial GET — patch should bootstrap.
    r = await client.patch(
        f"/api/projects/{pid}/review/prospero",
        json={"fields": {"funding_sources": "NIH"}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["fields"]["funding_sources"] == "NIH"


@pytest.mark.asyncio
async def test_export_returns_text_with_22_labels(client):
    _switch_user("user-a")
    pid = await _make_project(client, "Export SR")
    await client.get(f"/api/projects/{pid}/review/prospero")
    r = await client.post(f"/api/projects/{pid}/review/prospero/export")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/plain")
    text = r.text
    # Each of the 22 fields renders one label line.
    assert "Review title:" in text
    assert "Anticipated or actual start date:" in text
    assert "Main outcome(s):" in text
    assert "Export SR" in text


@pytest.mark.asyncio
async def test_export_auto_creates_if_missing(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/review/prospero/export")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_get_for_unknown_project_returns_404(client):
    _switch_user("user-a")
    r = await client.get("/api/projects/nope/review/prospero")
    assert r.status_code == 404
