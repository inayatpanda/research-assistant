"""Phase 13.5 (MP13.5) — Analysis plan + run route tests."""
import pytest

CSV_BYTES = (
    b"score,group\n"
    b"10,A\n12,A\n14,A\n11,A\n13,A\n9,A\n"
    b"6,B\n8,B\n7,B\n8,B\n6,B\n9,B\n"
)


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


async def _upload(client, pid) -> dict:
    r = await client.post(
        f"/api/projects/{pid}/datasets",
        files={"file": ("d.csv", CSV_BYTES, "text/csv")},
    )
    return r.json()


@pytest.mark.asyncio
async def test_create_plan(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "baseline", "steps": []},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "baseline"


@pytest.mark.asyncio
async def test_list_plans(client):
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "p1", "steps": []},
    )
    await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "p2", "steps": []},
    )
    r = await client.get(f"/api/projects/{pid}/analysis-plans")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_update_plan(client):
    pid = await _make_project(client)
    cr = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "p1", "steps": []},
    )
    plan_id = cr.json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/analysis-plans/{plan_id}",
        json={"name": "p1-renamed", "description": "edits", "steps": [
            {"type": "plot", "args": {"geom": "histogram", "x": "score"}}
        ]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "p1-renamed"
    assert body["description"] == "edits"
    assert len(body["steps"]) == 1


@pytest.mark.asyncio
async def test_delete_plan(client):
    pid = await _make_project(client)
    cr = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "p1", "steps": []},
    )
    plan_id = cr.json()["id"]
    r = await client.delete(f"/api/projects/{pid}/analysis-plans/{plan_id}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/projects/{pid}/analysis-plans/{plan_id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_run_plan_returns_ok_status(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    steps = [
        {"type": "test",
         "args": {"test_key": "independent_t",
                  "variables": {"outcome": "score", "groups": "group"}}},
        {"type": "plot",
         "args": {"geom": "box", "x": "group", "y": "score"}},
    ]
    cr = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "two-step", "steps": steps},
    )
    plan_id = cr.json()["id"]
    rr = await client.post(
        f"/api/projects/{pid}/analysis-plans/{plan_id}/run",
        json={"dataset_id": ds["id"]},
    )
    assert rr.status_code == 200, rr.text
    body = rr.json()
    assert body["status"] == "ok"
    assert len(body["result_blob"]["steps"]) == 2


@pytest.mark.asyncio
async def test_run_plan_with_failing_step_returns_partial(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    cr = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "bad", "steps": [
            {"type": "test",
             "args": {"test_key": "independent_t",
                      "variables": {"outcome": "no_such_col", "groups": "group"}}},
            {"type": "plot",
             "args": {"geom": "histogram", "x": "score"}},
        ]},
    )
    plan_id = cr.json()["id"]
    rr = await client.post(
        f"/api/projects/{pid}/analysis-plans/{plan_id}/run",
        json={"dataset_id": ds["id"]},
    )
    assert rr.status_code == 200
    body = rr.json()
    assert body["status"] == "partial"
    statuses = [s["status"] for s in body["result_blob"]["steps"]]
    assert "failed" in statuses
    assert "ok" in statuses


@pytest.mark.asyncio
async def test_list_runs(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    cr = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "p", "steps": []},
    )
    plan_id = cr.json()["id"]
    for _ in range(3):
        await client.post(
            f"/api/projects/{pid}/analysis-plans/{plan_id}/run",
            json={"dataset_id": ds["id"]},
        )
    r = await client.get(f"/api/projects/{pid}/analysis-plans/{plan_id}/runs")
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_get_single_run(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    cr = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "p", "steps": [
            {"type": "plot", "args": {"geom": "histogram", "x": "score"}}
        ]},
    )
    plan_id = cr.json()["id"]
    rr = await client.post(
        f"/api/projects/{pid}/analysis-plans/{plan_id}/run",
        json={"dataset_id": ds["id"]},
    )
    run_id = rr.json()["id"]
    r = await client.get(f"/api/projects/{pid}/analysis-plan-runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["id"] == run_id


@pytest.mark.asyncio
async def test_run_unknown_dataset_404(client):
    pid = await _make_project(client)
    cr = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "p", "steps": []},
    )
    plan_id = cr.json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/analysis-plans/{plan_id}/run",
        json={"dataset_id": "nope"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_unknown_plan_404(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/analysis-plans/nope/run",
        json={"dataset_id": ds["id"]},
    )
    assert r.status_code == 404
