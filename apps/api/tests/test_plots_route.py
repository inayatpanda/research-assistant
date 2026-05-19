"""Phase 13.5 (MP13.5) — plot route smoke tests."""
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
async def test_create_plot_returns_data_uri(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "box", "x": "group", "y": "score", "title": "Box"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "Box"
    assert body["spec"]["geom"] == "box"
    assert body["png_data_uri"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_list_plots_returns_in_creation_order(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "histogram", "x": "score"},
    )
    await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "box", "x": "group", "y": "score"},
    )
    r = await client.get(f"/api/projects/{pid}/datasets/{ds['id']}/plots")
    assert r.status_code == 200
    plots = r.json()
    assert len(plots) == 2
    # Newest first
    assert plots[0]["spec"]["geom"] == "box"


@pytest.mark.asyncio
async def test_get_plot_individual(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    cr = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "histogram", "x": "score"},
    )
    plot_id = cr.json()["id"]
    r = await client.get(f"/api/projects/{pid}/plots/{plot_id}")
    assert r.status_code == 200
    assert r.json()["id"] == plot_id


@pytest.mark.asyncio
async def test_delete_plot(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    cr = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "histogram", "x": "score"},
    )
    plot_id = cr.json()["id"]
    r = await client.delete(f"/api/projects/{pid}/plots/{plot_id}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/projects/{pid}/plots/{plot_id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_plot_returns_fresh_uri(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    cr = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "histogram", "x": "score"},
    )
    plot_id = cr.json()["id"]
    r = await client.post(f"/api/projects/{pid}/plots/{plot_id}/regenerate")
    assert r.status_code == 200, r.text
    assert r.json()["png_data_uri"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_create_plot_unknown_geom_422(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "noop", "x": "score"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_plot_missing_column_422(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "box", "x": "no_such_col", "y": "score"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_plot_unknown_dataset_404(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/datasets/no_such_ds/plots",
        json={"geom": "histogram", "x": "score"},
    )
    assert r.status_code == 404
