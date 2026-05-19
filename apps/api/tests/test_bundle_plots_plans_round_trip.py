"""Phase 13.5 — Bundle export/import round-trip for plots + analysis plans."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from research_api.db.models import (
    AnalysisPlan,
    AnalysisPlanRun,
    Dataset,
    DatasetPlot,
    Project,
)
from research_api.services.export.bundle_export import BundleInputs, build_bundle
from research_api.services.export.bundle_import import import_bundle


@pytest.mark.asyncio
async def test_dataset_plot_round_trip(session):
    p = Project(
        id="proj-orig", user_id="user-a", title="P", study_type="Outcome Study"
    )
    ds = Dataset(
        id="ds-orig", user_id="user-a", project_id="proj-orig",
        filename="d.csv", file_ref={"backend": "local", "key": "k"},
        file_type="text/csv", n_rows=2, n_columns=1,
    )
    plot = DatasetPlot(
        id="pl-orig", user_id="user-a", project_id="proj-orig",
        dataset_id="ds-orig", title="my plot",
        spec={"geom": "histogram", "x": "score"},
        png_data_uri="data:image/png;base64,iVBOR=",
    )
    plot.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    plot.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(
        project=p, datasets=[ds], dataset_plots=[plot],
    ))
    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert counts["dataset_plots"] == 1
    row = (await session.execute(select(DatasetPlot))).scalar_one()
    assert row.user_id == "user-b"
    assert row.title == "my plot"
    assert row.spec["geom"] == "histogram"


@pytest.mark.asyncio
async def test_analysis_plan_and_runs_round_trip(session):
    p = Project(
        id="proj-orig", user_id="user-a", title="P", study_type="Outcome Study"
    )
    plan = AnalysisPlan(
        id="pl-orig", user_id="user-a", project_id="proj-orig",
        name="My plan", description="notes",
        steps=[{"type": "plot", "args": {"geom": "histogram", "x": "score"}}],
    )
    plan.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    plan.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    run = AnalysisPlanRun(
        id="run-orig", user_id="user-a", plan_id="pl-orig",
        dataset_id="ds-orig",
        result_blob={"steps": [{"step_index": 0, "type": "plot", "status": "ok",
                                 "output": {}, "error": None}]},
        status="ok", error=None,
    )
    run.executed_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(
        project=p, analysis_plans=[plan], analysis_plan_runs=[run],
    ))
    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert counts["analysis_plans"] == 1
    assert counts["analysis_plan_runs"] == 1

    new_plan = (await session.execute(select(AnalysisPlan))).scalar_one()
    assert new_plan.user_id == "user-b"
    assert new_plan.name == "My plan"
    new_run = (await session.execute(select(AnalysisPlanRun))).scalar_one()
    assert new_run.plan_id == new_plan.id
    assert new_run.status == "ok"


@pytest.mark.asyncio
async def test_orphan_plot_dropped_when_dataset_missing(session):
    """A plot referencing a dataset NOT in the bundle is silently dropped."""
    p = Project(
        id="proj-orig", user_id="user-a", title="P", study_type="Outcome Study"
    )
    plot = DatasetPlot(
        id="pl-orig", user_id="user-a", project_id="proj-orig",
        dataset_id="ds-missing", title="x",
        spec={"geom": "histogram", "x": "y"},
        png_data_uri="",
    )
    plot.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    plot.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    bundle = build_bundle(BundleInputs(project=p, dataset_plots=[plot]))
    counts = await import_bundle(bundle, target_user_id="user-b", session=session)
    assert counts["dataset_plots"] == 0
