"""DEMO-FIX-A — Tests for the standalone diagnostic-tests routes."""
from __future__ import annotations

import pytest

from research_api.container import get_container


CSV_BYTES = (
    b"score,group\n"
    # Cluster A: tightly distributed near 10.
    b"10,A\n10.5,A\n11,A\n9.5,A\n10.2,A\n9.8,A\n10.1,A\n9.9,A\n10.3,A\n10.4,A\n"
    b"10.0,A\n9.7,A\n10.6,A\n9.4,A\n10.05,A\n9.95,A\n10.15,A\n9.85,A\n"
    # Cluster B: spread much more widely → unequal variance vs A.
    b"5,B\n8,B\n2,B\n12,B\n0,B\n14,B\n3,B\n11,B\n6,B\n9,B\n"
    b"4,B\n13,B\n1,B\n15,B\n7,B\n10,B\n5.5,B\n9.5,B\n"
)


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Outcome Study"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload(client, pid: str) -> dict:
    r = await client.post(
        f"/api/projects/{pid}/datasets",
        files={"file": ("d.csv", CSV_BYTES, "text/csv")},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Happy paths ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_shapiro_wilk_returns_interpretation(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/run",
        json={"test_key": "shapiro_wilk", "column_name": "score"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["test_key"] == "shapiro_wilk"
    assert body["n"] > 0
    assert isinstance(body["statistic"], float)
    assert isinstance(body["interpretation"], str) and body["interpretation"]


@pytest.mark.asyncio
async def test_anderson_darling_returns_critical_values(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/run",
        json={"test_key": "anderson_darling", "column_name": "score"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["critical_values"] is not None
    assert "5%" in body["critical_values"]
    # AD doesn't return a p-value.
    assert body["p"] is None


@pytest.mark.asyncio
async def test_levene_detects_unequal_variance(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/run",
        json={
            "test_key": "levene",
            "column_name": "score",
            "group_column": "group",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["k"] == 2
    assert body["center"] == "median"
    # The two clusters above were engineered to differ in variance, so the
    # Levene test should reject (p < 0.05) and flag ok=False.
    assert body["p"] < 0.05
    assert body["ok"] is False


@pytest.mark.asyncio
async def test_levene_without_group_column_returns_422(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/run",
        json={"test_key": "levene", "column_name": "score"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_qq_plot_returns_png(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/qq-plot",
        json={"column_name": "score"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_histogram_returns_png(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/histogram",
        json={"column_name": "score", "title": "Score histogram"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


# ── 404 / 422 error paths ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_unknown_dataset_returns_404(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/datasets/no_such_ds/diagnostics/run",
        json={"test_key": "shapiro_wilk", "column_name": "score"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_unknown_column_returns_422(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/run",
        json={"test_key": "shapiro_wilk", "column_name": "no_such_col"},
    )
    assert r.status_code == 422


# ── Cross-user / cross-project isolation ───────────────────────────────


@pytest.mark.asyncio
async def test_run_404_for_other_user(client):
    _switch_user("alice")
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    _switch_user("bob")
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/diagnostics/run",
        json={"test_key": "shapiro_wilk", "column_name": "score"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_404_for_dataset_in_other_project(client):
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    ds = await _upload(client, pid_a)
    # Same user, but ask about dataset under the wrong project_id.
    r = await client.post(
        f"/api/projects/{pid_b}/datasets/{ds['id']}/diagnostics/run",
        json={"test_key": "shapiro_wilk", "column_name": "score"},
    )
    assert r.status_code == 404
