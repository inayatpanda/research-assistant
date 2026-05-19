"""Phase 6 security regression: prove every datasets/analyses endpoint is
scoped by both user_id and project_id.

Approach:
- Repository-level: spin up two users + projects on the bare `session` fixture
  and assert each repo method refuses to leak rows.
- Route-level: drive the live ASGI app twice with a swapped
  container.settings.local_user_id to simulate a second authenticated user.
- Cross-project (same user): create two projects A and B, upload a dataset
  into A, then verify B cannot read/list/mutate it.
"""
import pytest

from research_api.container import get_container
from research_api.db.models import Project
from research_api.repositories.analyses import SqliteAnalysisRepository
from research_api.repositories.datasets import SqliteDatasetRepository
from research_api.services.stats.ingest import InferredColumn


CSV_BYTES = (
    b"score,group\n"
    b"10,A\n12,A\n14,A\n11,A\n13,A\n9,A\n"
    b"6,B\n8,B\n7,B\n8,B\n6,B\n9,B\n"
)


# ── Repository-level (user_id-scoped CRUD) ──────────────────────────────────


async def _seed_dataset(session, user_id: str, project_id: str, filename: str = "d.csv"):
    repo = SqliteDatasetRepository(session)
    return await repo.create(
        project_id=project_id,
        filename=filename,
        file_ref={"backend": "local", "key": f"{user_id}/datasets/k"},
        file_type="text/csv",
        n_rows=2,
        n_columns=1,
        variables=[
            InferredColumn(
                name="x", position=0, inferred_type="numeric", n_missing=0,
                sample_values=["1", "2"],
            )
        ],
        user_id=user_id,
    )


async def _make_project_row(session, user_id: str) -> Project:
    p = Project(user_id=user_id, title="P", study_type="Outcome Study")
    session.add(p)
    await session.flush()
    return p


@pytest.mark.asyncio
async def test_dataset_get_isolated_across_users(session):
    p = await _make_project_row(session, "user-a")
    ds = await _seed_dataset(session, "user-a", p.id)
    repo = SqliteDatasetRepository(session)
    assert await repo.get(ds.id, "user-a") is not None
    assert await repo.get(ds.id, "user-b") is None


@pytest.mark.asyncio
async def test_dataset_list_isolated_across_users(session):
    pa = await _make_project_row(session, "user-a")
    pb = await _make_project_row(session, "user-b")
    await _seed_dataset(session, "user-a", pa.id, filename="a.csv")
    await _seed_dataset(session, "user-b", pb.id, filename="b.csv")
    repo = SqliteDatasetRepository(session)
    a_rows = await repo.list_for_project(pa.id, "user-a")
    b_rows = await repo.list_for_project(pb.id, "user-b")
    assert {r.filename for r in a_rows} == {"a.csv"}
    assert {r.filename for r in b_rows} == {"b.csv"}
    cross = await repo.list_for_project(pa.id, "user-b")
    assert cross == []


@pytest.mark.asyncio
async def test_dataset_update_variable_isolated_across_users(session):
    p = await _make_project_row(session, "user-a")
    ds = await _seed_dataset(session, "user-a", p.id)
    repo = SqliteDatasetRepository(session)
    variables = await repo.list_variables(ds.id, "user-a")
    assert variables, "expected at least one variable"
    var_id = variables[0].id
    leaked = await repo.update_variable_type(
        variable_id=var_id, user_type="ordinal", user_id="user-b"
    )
    assert leaked is None
    refreshed = (await repo.list_variables(ds.id, "user-a"))[0]
    assert refreshed.user_type is None


@pytest.mark.asyncio
async def test_dataset_delete_isolated_across_users(session):
    p = await _make_project_row(session, "user-a")
    ds = await _seed_dataset(session, "user-a", p.id)
    repo = SqliteDatasetRepository(session)
    # Attacker cannot delete by passing the wrong user_id
    await repo.delete(ds.id, "user-b")
    assert await repo.get(ds.id, "user-a") is not None
    # Real owner can delete
    await repo.delete(ds.id, "user-a")
    assert await repo.get(ds.id, "user-a") is None


@pytest.mark.asyncio
async def test_analysis_get_isolated_across_users(session):
    p = await _make_project_row(session, "user-a")
    ds = await _seed_dataset(session, "user-a", p.id)
    repo = SqliteAnalysisRepository(session)
    a = await repo.create(
        project_id=p.id, dataset_id=ds.id,
        question_type="group_comparison", chosen_test="independent_t",
        recommendation_rationale="r", variables={"outcome": "x", "groups": "x"},
        status="ready", user_id="user-a",
    )
    assert await repo.get(a.id, "user-a") is not None
    assert await repo.get(a.id, "user-b") is None


@pytest.mark.asyncio
async def test_analysis_list_isolated_across_users(session):
    pa = await _make_project_row(session, "user-a")
    pb = await _make_project_row(session, "user-b")
    dsa = await _seed_dataset(session, "user-a", pa.id)
    dsb = await _seed_dataset(session, "user-b", pb.id)
    repo = SqliteAnalysisRepository(session)
    await repo.create(
        project_id=pa.id, dataset_id=dsa.id,
        question_type="group_comparison", chosen_test="independent_t",
        recommendation_rationale="r", variables={}, status="ready", user_id="user-a",
    )
    await repo.create(
        project_id=pb.id, dataset_id=dsb.id,
        question_type="group_comparison", chosen_test="independent_t",
        recommendation_rationale="r", variables={}, status="ready", user_id="user-b",
    )
    a_rows = await repo.list_for_dataset(
        project_id=pa.id, dataset_id=dsa.id, user_id="user-a"
    )
    b_rows = await repo.list_for_dataset(
        project_id=pb.id, dataset_id=dsb.id, user_id="user-b"
    )
    assert len(a_rows) == 1
    assert len(b_rows) == 1
    cross = await repo.list_for_dataset(
        project_id=pa.id, dataset_id=dsa.id, user_id="user-b"
    )
    assert cross == []


@pytest.mark.asyncio
async def test_analysis_result_isolated_across_users(session):
    p = await _make_project_row(session, "user-a")
    ds = await _seed_dataset(session, "user-a", p.id)
    repo = SqliteAnalysisRepository(session)
    a = await repo.create(
        project_id=p.id, dataset_id=ds.id,
        question_type="group_comparison", chosen_test="independent_t",
        recommendation_rationale="r", variables={}, status="ready", user_id="user-a",
    )
    leaked = await repo.update_result(
        analysis_id=a.id,
        summary={"p_value": 0.001}, assumptions={}, chart=None,
        user_id="user-b",
    )
    assert leaked is None
    leaked_interp = await repo.update_interpretation(
        analysis_id=a.id, ai_interpretation="hacked", user_id="user-b"
    )
    assert leaked_interp is None


@pytest.mark.asyncio
async def test_analysis_delete_isolated_across_users(session):
    p = await _make_project_row(session, "user-a")
    ds = await _seed_dataset(session, "user-a", p.id)
    repo = SqliteAnalysisRepository(session)
    a = await repo.create(
        project_id=p.id, dataset_id=ds.id,
        question_type="group_comparison", chosen_test="independent_t",
        recommendation_rationale="r", variables={}, status="ready", user_id="user-a",
    )
    await repo.delete(a.id, "user-b")
    assert await repo.get(a.id, "user-a") is not None


# ── Route-level (HTTP attack surface) ───────────────────────────────────────


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Outcome Study"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload_dataset(client, project_id: str) -> dict:
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


async def _make_analysis(client, project_id: str, dataset_id: str) -> dict:
    r = await client.post(
        f"/api/projects/{project_id}/datasets/{dataset_id}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


@pytest.mark.asyncio
async def test_user_a_cannot_list_user_b_datasets(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    await _upload_dataset(client, project_a)

    _switch_user("user-b")
    project_b = await _make_project(client, title="B")
    # Endpoint: list datasets in project_a — user-b cannot see project_a at all
    r = await client.get(f"/api/projects/{project_a}/datasets")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_read_user_b_dataset(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{project_a}/datasets/{ds['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_delete_user_b_dataset(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)

    _switch_user("user-b")
    r = await client.delete(f"/api/projects/{project_a}/datasets/{ds['id']}")
    assert r.status_code == 404

    _switch_user("user-a")
    r2 = await client.get(f"/api/projects/{project_a}/datasets/{ds['id']}")
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_user_a_cannot_update_user_b_variable(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    var_id = ds["variables"][0]["id"]

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{project_a}/datasets/{ds['id']}/variables/{var_id}",
        json={"user_type": "ordinal"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_recommend_against_user_b_dataset(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{project_a}/datasets/{ds['id']}/analyses/recommend",
        json={
            "question_type": "group_comparison",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_create_analysis_against_user_b_dataset(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{project_a}/datasets/{ds['id']}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_list_user_b_analyses(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    await _make_analysis(client, project_a, ds["id"])

    _switch_user("user-b")
    r = await client.get(
        f"/api/projects/{project_a}/datasets/{ds['id']}/analyses"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_run_user_b_analysis(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    a = await _make_analysis(client, project_a, ds["id"])

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{project_a}/analyses/{a['id']}/run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_interpret_user_b_analysis(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    a = await _make_analysis(client, project_a, ds["id"])
    await client.post(f"/api/projects/{project_a}/analyses/{a['id']}/run")

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{project_a}/analyses/{a['id']}/interpret")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_push_user_b_analysis(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    a = await _make_analysis(client, project_a, ds["id"])
    await client.post(f"/api/projects/{project_a}/analyses/{a['id']}/run")
    await client.post(f"/api/projects/{project_a}/analyses/{a['id']}/interpret")

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{project_a}/analyses/{a['id']}/push", json={}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_get_user_b_analysis(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    a = await _make_analysis(client, project_a, ds["id"])

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{project_a}/analyses/{a['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_delete_user_b_analysis(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    a = await _make_analysis(client, project_a, ds["id"])

    _switch_user("user-b")
    r = await client.delete(f"/api/projects/{project_a}/analyses/{a['id']}")
    assert r.status_code == 404

    _switch_user("user-a")
    r2 = await client.get(f"/api/projects/{project_a}/analyses/{a['id']}")
    assert r2.status_code == 200


# ── Cross-project (same user) — dataset in project X must not be reachable
#    through project Y. ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_project_dataset_get_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)

    r = await client.get(f"/api/projects/{project_y}/datasets/{ds['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_project_dataset_delete_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)

    r = await client.delete(f"/api/projects/{project_y}/datasets/{ds['id']}")
    assert r.status_code == 404
    r2 = await client.get(f"/api/projects/{project_x}/datasets/{ds['id']}")
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_cross_project_variable_update_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)
    var_id = ds["variables"][0]["id"]

    r = await client.patch(
        f"/api/projects/{project_y}/datasets/{ds['id']}/variables/{var_id}",
        json={"user_type": "ordinal"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_project_recommend_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)

    r = await client.post(
        f"/api/projects/{project_y}/datasets/{ds['id']}/analyses/recommend",
        json={
            "question_type": "group_comparison",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_project_create_analysis_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)

    r = await client.post(
        f"/api/projects/{project_y}/datasets/{ds['id']}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_project_run_analysis_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)
    a = await _make_analysis(client, project_x, ds["id"])

    r = await client.post(f"/api/projects/{project_y}/analyses/{a['id']}/run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_project_interpret_analysis_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)
    a = await _make_analysis(client, project_x, ds["id"])
    await client.post(f"/api/projects/{project_x}/analyses/{a['id']}/run")

    r = await client.post(f"/api/projects/{project_y}/analyses/{a['id']}/interpret")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_project_push_analysis_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)
    a = await _make_analysis(client, project_x, ds["id"])
    await client.post(f"/api/projects/{project_x}/analyses/{a['id']}/run")
    await client.post(f"/api/projects/{project_x}/analyses/{a['id']}/interpret")

    r = await client.post(
        f"/api/projects/{project_y}/analyses/{a['id']}/push", json={}
    )
    assert r.status_code == 404


# ── Phase 13 — PSM endpoint isolation ───────────────────────────────────


PSM_CSV_BYTES = (
    b"age,sex,t,outcome\n"
    b"45,0,0,1.2\n50,1,1,2.1\n55,0,0,1.5\n60,1,1,2.5\n"
    b"42,1,0,0.9\n48,0,1,2.3\n52,1,0,1.7\n58,0,1,2.6\n"
    b"40,0,0,1.0\n65,1,1,2.8\n44,1,0,1.4\n62,0,1,2.4\n"
    b"46,0,1,2.0\n49,1,0,1.6\n51,1,1,2.2\n54,0,0,1.3\n"
)


@pytest.mark.asyncio
async def test_psm_cross_user_404(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    files = {"file": ("psm.csv", PSM_CSV_BYTES, "text/csv")}
    ru = await client.post(f"/api/projects/{project_a}/datasets", files=files)
    assert ru.status_code == 201
    ds = ru.json()

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{project_a}/datasets/{ds['id']}/psm",
        json={
            "treatment_col": "t",
            "covariate_cols": ["age", "sex"],
            "caliper_sd": 0.2,
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_psm_cross_project_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    files = {"file": ("psm.csv", PSM_CSV_BYTES, "text/csv")}
    ru = await client.post(f"/api/projects/{project_x}/datasets", files=files)
    assert ru.status_code == 201
    ds = ru.json()

    r = await client.post(
        f"/api/projects/{project_y}/datasets/{ds['id']}/psm",
        json={
            "treatment_col": "t",
            "covariate_cols": ["age", "sex"],
            "caliper_sd": 0.2,
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_psm_unknown_project_404(client):
    r = await client.post(
        "/api/projects/does-not-exist/datasets/abc/psm",
        json={
            "treatment_col": "t",
            "covariate_cols": ["age", "sex"],
            "caliper_sd": 0.2,
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_psm_rejects_unknown_treatment_column(client):
    project_a = await _make_project(client, title="A")
    files = {"file": ("psm.csv", PSM_CSV_BYTES, "text/csv")}
    ru = await client.post(f"/api/projects/{project_a}/datasets", files=files)
    ds = ru.json()

    r = await client.post(
        f"/api/projects/{project_a}/datasets/{ds['id']}/psm",
        json={
            "treatment_col": "no_such_col",
            "covariate_cols": ["age"],
            "caliper_sd": 0.2,
        },
    )
    assert r.status_code == 422


# ── Phase 13.5 — Plots + analysis plans + stats report isolation ─────


@pytest.mark.asyncio
async def test_plots_cross_user_404(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    cp = await client.post(
        f"/api/projects/{project_a}/datasets/{ds['id']}/plots",
        json={"geom": "histogram", "x": "score"},
    )
    plot_id = cp.json()["id"]

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{project_a}/plots/{plot_id}")
    assert r.status_code == 404
    r2 = await client.delete(f"/api/projects/{project_a}/plots/{plot_id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_plots_cross_project_404(client):
    project_x = await _make_project(client, title="X")
    project_y = await _make_project(client, title="Y")
    ds = await _upload_dataset(client, project_x)
    cp = await client.post(
        f"/api/projects/{project_x}/datasets/{ds['id']}/plots",
        json={"geom": "histogram", "x": "score"},
    )
    plot_id = cp.json()["id"]
    r = await client.get(f"/api/projects/{project_y}/plots/{plot_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_analysis_plan_cross_user_404(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    cp = await client.post(
        f"/api/projects/{project_a}/analysis-plans",
        json={"name": "p", "steps": []},
    )
    plan_id = cp.json()["id"]

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{project_a}/analysis-plans/{plan_id}")
    assert r.status_code == 404
    r2 = await client.delete(f"/api/projects/{project_a}/analysis-plans/{plan_id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_analysis_plan_run_cross_user_404(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)
    cp = await client.post(
        f"/api/projects/{project_a}/analysis-plans",
        json={"name": "p", "steps": []},
    )
    plan_id = cp.json()["id"]

    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{project_a}/analysis-plans/{plan_id}/run",
        json={"dataset_id": ds["id"]},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_analysis_plans_listing_isolated(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    await client.post(
        f"/api/projects/{project_a}/analysis-plans",
        json={"name": "p", "steps": []},
    )

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{project_a}/analysis-plans")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_stats_report_cross_user_404(client):
    _switch_user("user-a")
    project_a = await _make_project(client, title="A")
    ds = await _upload_dataset(client, project_a)

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{project_a}/datasets/{ds['id']}/report")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_psm_persists_matched_dataset_linked_back(client):
    project_a = await _make_project(client, title="A")
    files = {"file": ("psm.csv", PSM_CSV_BYTES, "text/csv")}
    ru = await client.post(f"/api/projects/{project_a}/datasets", files=files)
    src = ru.json()

    r = await client.post(
        f"/api/projects/{project_a}/datasets/{src['id']}/psm",
        json={
            "treatment_col": "t",
            "covariate_cols": ["age", "sex"],
            "caliper_sd": 1.0,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    new_id = body["matched_dataset_id"]
    assert new_id != src["id"]

    # The new dataset is visible under the same project + carries the
    # derived_from FK + metadata JSON.
    get_r = await client.get(f"/api/projects/{project_a}/datasets/{new_id}")
    assert get_r.status_code == 200
    fetched = get_r.json()
    assert fetched["derived_from_dataset_id"] == src["id"]
    assert "psm" in fetched["dataset_metadata"]
    psm_meta = fetched["dataset_metadata"]["psm"]
    assert psm_meta["source_dataset_id"] == src["id"]
    assert psm_meta["caliper_sd"] == 1.0
