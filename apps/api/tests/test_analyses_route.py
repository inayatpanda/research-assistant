"""End-to-end tests for /api analyses routes."""
import pytest

# A 12-row dataset designed so an independent t-test on score~group is significant.
CSV_BYTES = (
    b"score,group\n"
    b"10,A\n12,A\n14,A\n11,A\n13,A\n9,A\n"
    b"6,B\n8,B\n7,B\n8,B\n6,B\n9,B\n"
)


async def _make_project(client, title="Stats P", study_type="Outcome Study") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": study_type}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload_dataset(client, project_id, body: bytes = CSV_BYTES) -> dict:
    files = {"file": ("data.csv", body, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


async def _make_analysis(client, project_id, dataset_id, chosen_test="independent_t"):
    r = await client.post(
        f"/api/projects/{project_id}/datasets/{dataset_id}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": chosen_test,
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_recommend_returns_independent_t(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)

    r = await client.post(
        f"/api/projects/{project_id}/datasets/{ds['id']}/analyses/recommend",
        json={
            "question_type": "group_comparison",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chosen_test"] == "independent_t"
    assert body["rationale"]


@pytest.mark.asyncio
async def test_recommend_404_missing_dataset(client):
    project_id = await _make_project(client)
    r = await client.post(
        f"/api/projects/{project_id}/datasets/missing/analyses/recommend",
        json={
            "question_type": "group_comparison",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_recommend_422_unknown_column(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    r = await client.post(
        f"/api/projects/{project_id}/datasets/{ds['id']}/analyses/recommend",
        json={
            "question_type": "group_comparison",
            "variables": {"outcome": "not_a_col", "groups": "group"},
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_analysis_happy_path(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])
    assert a["chosen_test"] == "independent_t"
    assert a["status"] == "ready"
    assert a["result"] is None


@pytest.mark.asyncio
async def test_create_analysis_404_missing_dataset(client):
    project_id = await _make_project(client)
    r = await client.post(
        f"/api/projects/{project_id}/datasets/missing/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_analysis_422_unknown_column(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    r = await client.post(
        f"/api/projects/{project_id}/datasets/{ds['id']}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "not_real"},
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_analyses_for_dataset(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    await _make_analysis(client, project_id, ds["id"])
    r = await client.get(
        f"/api/projects/{project_id}/datasets/{ds['id']}/analyses"
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_analysis(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])
    r = await client.get(f"/api/projects/{project_id}/analyses/{a['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == a["id"]


@pytest.mark.asyncio
async def test_get_analysis_404(client):
    project_id = await _make_project(client)
    r = await client.get(f"/api/projects/{project_id}/analyses/missing")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_analysis_attaches_result(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])

    r = await client.post(f"/api/projects/{project_id}/analyses/{a['id']}/run")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["result"] is not None
    assert body["result"]["summary"]["p_value"] < 0.05
    assert "shapiro" in body["result"]["assumptions"]
    assert "levene" in body["result"]["assumptions"]


@pytest.mark.asyncio
async def test_run_analysis_404(client):
    project_id = await _make_project(client)
    r = await client.post(f"/api/projects/{project_id}/analyses/missing/run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_interpret_analysis_attaches_prose_with_cite_token(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])
    await client.post(f"/api/projects/{project_id}/analyses/{a['id']}/run")

    r = await client.post(
        f"/api/projects/{project_id}/analyses/{a['id']}/interpret"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    interp = body["result"]["ai_interpretation"]
    assert interp
    assert f"[CITE_dataset_{ds['id']}]" in interp


@pytest.mark.asyncio
async def test_interpret_422_without_result(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])
    r = await client.post(
        f"/api/projects/{project_id}/analyses/{a['id']}/interpret"
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_push_to_manuscript_appends_paragraph(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])
    await client.post(f"/api/projects/{project_id}/analyses/{a['id']}/run")
    await client.post(f"/api/projects/{project_id}/analyses/{a['id']}/interpret")

    r = await client.post(
        f"/api/projects/{project_id}/analyses/{a['id']}/push",
        json={},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["section_name"] == "Results"
    assert f"[CITE_dataset_{ds['id']}]" in body["content"]
    assert body["word_count"] > 0


@pytest.mark.asyncio
async def test_push_to_manuscript_appends_not_overwrite(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)

    # Seed an existing Results section with some text
    seed = await client.put(
        f"/api/projects/{project_id}/sections/Results",
        json={"section_name": "Results", "content": "<p>Existing content.</p>"},
    )
    assert seed.status_code in (200, 201), seed.text

    a = await _make_analysis(client, project_id, ds["id"])
    await client.post(f"/api/projects/{project_id}/analyses/{a['id']}/run")
    await client.post(f"/api/projects/{project_id}/analyses/{a['id']}/interpret")

    r = await client.post(
        f"/api/projects/{project_id}/analyses/{a['id']}/push",
        json={},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "Existing content." in body["content"]
    assert f"[CITE_dataset_{ds['id']}]" in body["content"]


@pytest.mark.asyncio
async def test_push_422_without_interpretation(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])
    r = await client.post(
        f"/api/projects/{project_id}/analyses/{a['id']}/push", json={}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_analysis(client):
    project_id = await _make_project(client)
    ds = await _upload_dataset(client, project_id)
    a = await _make_analysis(client, project_id, ds["id"])
    r = await client.delete(f"/api/projects/{project_id}/analyses/{a['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/projects/{project_id}/analyses/{a['id']}")
    assert r2.status_code == 404
