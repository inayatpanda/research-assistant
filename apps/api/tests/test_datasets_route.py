"""End-to-end tests for /api/projects/{pid}/datasets routes."""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

CSV_BYTES = b"age,group,score\n45,A,10\n50,B,12\n42,A,8\n55,B,14\n"


async def _make_project(client, title="Stats P", study_type="Outcome Study") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": study_type}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_upload_csv_dataset_happy_path(client):
    project_id = await _make_project(client)
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "data.csv"
    assert body["file_type"] == "text/csv"
    assert body["n_rows"] == 4
    assert body["n_columns"] == 3
    assert len(body["variables"]) == 3
    by_name = {v["name"]: v for v in body["variables"]}
    assert by_name["age"]["inferred_type"] == "numeric"
    assert by_name["group"]["inferred_type"] == "nominal"
    assert by_name["score"]["inferred_type"] == "numeric"


@pytest.mark.asyncio
async def test_upload_xlsx_dataset(client):
    project_id = await _make_project(client)
    xlsx = (FIXTURES / "tiny.xlsx").read_bytes()
    files = {
        "file": (
            "tiny.xlsx",
            xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "tiny.xlsx"
    assert body["file_type"].endswith("spreadsheetml.sheet")
    assert body["n_columns"] >= 1


@pytest.mark.asyncio
async def test_upload_rejects_pdf_bytes(client):
    project_id = await _make_project(client)
    files = {"file": ("fake.csv", b"%PDF-1.4 not really a csv", "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_unknown_bytes(client):
    project_id = await _make_project(client)
    files = {"file": ("data.bin", b"\x00\x01\x02\x03", "application/octet-stream")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_empty(client):
    project_id = await _make_project(client)
    files = {"file": ("data.csv", b"", "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_oversize(client):
    project_id = await _make_project(client)
    huge = b"a,b\n" + (b"1,2\n" * (60 * 1024 * 1024 // 4))
    files = {"file": ("big.csv", huge, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_upload_404_for_missing_project(client):
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    r = await client.post("/api/projects/nope/datasets", files=files)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_datasets(client):
    project_id = await _make_project(client)
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    await client.post(f"/api/projects/{project_id}/datasets", files=files)

    r = await client.get(f"/api/projects/{project_id}/datasets")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_list_datasets_404_for_missing_project(client):
    r = await client.get("/api/projects/nope/datasets")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_dataset_with_variables(client):
    project_id = await _make_project(client)
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    up = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    dataset_id = up.json()["id"]

    r = await client.get(f"/api/projects/{project_id}/datasets/{dataset_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == dataset_id
    assert len(body["variables"]) == 3


@pytest.mark.asyncio
async def test_get_dataset_404(client):
    project_id = await _make_project(client)
    r = await client.get(f"/api/projects/{project_id}/datasets/missing")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_variable_type(client):
    project_id = await _make_project(client)
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    up = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    dataset = up.json()
    dataset_id = dataset["id"]
    age_var = next(v for v in dataset["variables"] if v["name"] == "age")

    r = await client.patch(
        f"/api/projects/{project_id}/datasets/{dataset_id}/variables/{age_var['id']}",
        json={"user_type": "ordinal"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user_type"] == "ordinal"


@pytest.mark.asyncio
async def test_update_variable_404_for_unknown_id(client):
    project_id = await _make_project(client)
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    up = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    dataset_id = up.json()["id"]

    r = await client.patch(
        f"/api/projects/{project_id}/datasets/{dataset_id}/variables/bogus",
        json={"user_type": "nominal"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_dataset(client):
    project_id = await _make_project(client)
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    up = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    dataset_id = up.json()["id"]

    r = await client.delete(f"/api/projects/{project_id}/datasets/{dataset_id}")
    assert r.status_code == 204

    r2 = await client.get(f"/api/projects/{project_id}/datasets/{dataset_id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_dataset_404_for_missing(client):
    project_id = await _make_project(client)
    r = await client.delete(f"/api/projects/{project_id}/datasets/missing")
    assert r.status_code == 404
