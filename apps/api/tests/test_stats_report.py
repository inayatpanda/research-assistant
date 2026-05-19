"""Phase 13.5 (MP13.5) — stats report builder + route tests."""
import pytest

from research_api.services.export.stats_report import (
    ReportAnalysis,
    ReportDataset,
    ReportPlot,
    ReportProject,
    ReportTransformation,
    build_stats_report,
)


def test_build_stats_report_empty_smoke():
    data = build_stats_report(
        project=ReportProject(title="A study", study_type="Outcome Study"),
        dataset=ReportDataset(
            id="ds1", filename="x.csv", n_rows=10, n_columns=3
        ),
        analyses=[],
        plots=[],
        transformations=[],
    )
    assert data[:4] == b"%PDF"


def test_build_stats_report_includes_analysis_summary():
    data = build_stats_report(
        project=ReportProject(title="A", study_type="x"),
        dataset=ReportDataset(id="d", filename="d.csv", n_rows=1, n_columns=1),
        analyses=[
            ReportAnalysis(
                test_label="Independent t-test",
                variables={"outcome": "score", "groups": "group"},
                summary={
                    "statistic": 4.2,
                    "p_value": 0.001,
                    "effect_size": 1.2,
                    "ci_low": 0.5,
                    "ci_high": 2.0,
                    "n": 12,
                    "df": 10,
                },
                assumptions={"shapiro": {"statistic": 0.9, "p_value": 0.4, "ok": True}},
                chart_data_uri=None,
                ai_interpretation="There is a difference.",
            )
        ],
        plots=[],
        transformations=[],
    )
    assert data[:4] == b"%PDF"
    assert len(data) > 1000


def test_build_stats_report_with_transformations():
    data = build_stats_report(
        project=ReportProject(title="A", study_type="x"),
        dataset=ReportDataset(id="d", filename="d.csv", n_rows=1, n_columns=1),
        analyses=[],
        plots=[],
        transformations=[
            ReportTransformation(op_type="filter", label="age>18", op_args={}),
            ReportTransformation(op_type="z_score", label="z", op_args={}),
        ],
    )
    assert data[:4] == b"%PDF"


def test_build_stats_report_with_plot_uri():
    # 1x1 transparent PNG
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASs"
        "JTYQAAAAASUVORK5CYII="
    )
    uri = f"data:image/png;base64,{png_b64}"
    data = build_stats_report(
        project=ReportProject(title="A", study_type="x"),
        dataset=ReportDataset(id="d", filename="d.csv", n_rows=1, n_columns=1),
        analyses=[],
        plots=[ReportPlot(title="My plot", geom="histogram", png_data_uri=uri)],
        transformations=[],
    )
    assert data[:4] == b"%PDF"


# ── Route tests ──────────────────────────────────────────────────────

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
async def test_export_report_route_returns_pdf(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(f"/api/projects/{pid}/datasets/{ds['id']}/report")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_export_report_includes_analyses(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    a = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    await client.post(f"/api/projects/{pid}/analyses/{a.json()['id']}/run")
    r = await client.post(f"/api/projects/{pid}/datasets/{ds['id']}/report")
    assert r.status_code == 200
    assert len(r.content) > 1500


@pytest.mark.asyncio
async def test_export_report_includes_plots(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/plots",
        json={"geom": "histogram", "x": "score", "title": "Hist"},
    )
    r = await client.post(f"/api/projects/{pid}/datasets/{ds['id']}/report")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_export_report_unknown_dataset_404(client):
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/datasets/noid/report")
    assert r.status_code == 404
