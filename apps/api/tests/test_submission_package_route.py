"""Phase 12 — Submission-package endpoint integration tests."""
from __future__ import annotations

import io
import zipfile

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "Knee OA RCT", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_submission_package_returns_zip(client) -> None:
    pid = await _make_project(client)
    # Seed minimal content.
    await client.put(
        f"/api/projects/{pid}/manuscript-sections/Abstract",
        json={"content": "<p>Abstract body</p>"},
    )
    r = await client.post(
        f"/api/projects/{pid}/export/submission-package",
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    disp = r.headers["content-disposition"]
    assert "Knee-OA-RCT_vdraft.zip" in disp
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert any(n.endswith("/manuscript.docx") for n in names)
    assert any(n.endswith("/cover_letter.docx") for n in names)


@pytest.mark.asyncio
async def test_submission_package_uses_snapshot_when_supplied(client) -> None:
    pid = await _make_project(client)
    await client.put(
        f"/api/projects/{pid}/manuscript-sections/Abstract",
        json={"content": "<p>Snapshot content</p>"},
    )
    snap = await client.post(
        f"/api/projects/{pid}/snapshots", json={"label": "v1-submission"}
    )
    assert snap.status_code == 201
    sid = snap.json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/export/submission-package",
        params={"snapshot_id": sid},
    )
    assert r.status_code == 200
    # Filename should encode the snapshot label.
    assert "v1-submission" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_submission_package_404_on_missing_snapshot(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/export/submission-package",
        params={"snapshot_id": "does-not-exist"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_submission_package_404_on_missing_project(client) -> None:
    r = await client.post(
        "/api/projects/does-not-exist/export/submission-package"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_submission_package_includes_reviewer_responses(client) -> None:
    pid = await _make_project(client)
    await client.put(
        f"/api/projects/{pid}/manuscript-sections/Abstract",
        json={"content": "<p>x</p>"},
    )
    await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "Reviewer 1", "raw_comments": "Add power calc."},
    )
    r = await client.post(
        f"/api/projects/{pid}/export/submission-package"
    )
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert any(n.endswith("/response_to_reviewers.docx") for n in names)
