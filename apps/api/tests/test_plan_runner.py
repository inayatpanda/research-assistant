"""Phase 13.5 (MP13.5) — plan_runner unit tests."""
import pandas as pd
import pytest

from research_api.services.stats.plan_runner import run_plan


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({
        "score": [10, 12, 14, 11, 13, 9, 6, 8, 7, 8, 6, 9],
        "group": ["A"] * 6 + ["B"] * 6,
    })


def test_run_plan_empty_steps_returns_ok(df):
    out = run_plan(steps=[], df=df)
    assert out.status == "ok"
    assert out.result_blob == {"steps": []}
    assert out.error is None


def test_run_plan_invalid_steps_input_fails(df):
    out = run_plan(steps="not a list", df=df)  # type: ignore[arg-type]
    assert out.status == "failed"
    assert "list" in (out.error or "")


def test_run_plan_transform_step_ok(df):
    steps = [
        {"type": "transform",
         "args": {"op_type": "filter", "op_args": {"column": "group", "op": "==", "value": "A"}}}
    ]
    out = run_plan(steps=steps, df=df)
    assert out.status == "ok"
    assert out.result_blob["steps"][0]["status"] == "ok"
    assert out.result_blob["steps"][0]["output"]["n_rows_after"] == 6


def test_run_plan_test_step_ok(df):
    steps = [
        {"type": "test",
         "args": {"test_key": "independent_t",
                  "variables": {"outcome": "score", "groups": "group"}}}
    ]
    out = run_plan(steps=steps, df=df)
    assert out.status == "ok"
    assert out.result_blob["steps"][0]["status"] == "ok"
    assert out.result_blob["steps"][0]["output"]["test_key"] == "independent_t"


def test_run_plan_plot_step_ok(df):
    steps = [
        {"type": "plot",
         "args": {"geom": "box", "x": "group", "y": "score"}}
    ]
    out = run_plan(steps=steps, df=df)
    assert out.status == "ok"
    step = out.result_blob["steps"][0]
    assert step["status"] == "ok"
    assert step["output"]["png_data_uri"].startswith("data:image/png;base64,")


def test_run_plan_unknown_step_type_fails_step_not_run(df):
    steps = [{"type": "weird", "args": {}}]
    out = run_plan(steps=steps, df=df)
    assert out.status == "partial"
    assert out.result_blob["steps"][0]["status"] == "failed"
    assert "unknown step type" in out.result_blob["steps"][0]["error"]


def test_run_plan_partial_status_when_one_step_fails(df):
    steps = [
        {"type": "transform",
         "args": {"op_type": "filter", "op_args": {"column": "group", "op": "==", "value": "A"}}},
        {"type": "test",
         "args": {"test_key": "independent_t",
                  "variables": {"outcome": "no_such_col", "groups": "group"}}},
        {"type": "plot",
         "args": {"geom": "histogram", "x": "score"}},
    ]
    out = run_plan(steps=steps, df=df)
    # 1 ok transform, 1 failed test (missing col), 1 ok plot — partial.
    assert out.status == "partial"
    statuses = [s["status"] for s in out.result_blob["steps"]]
    assert statuses == ["ok", "failed", "ok"]


def test_run_plan_transform_step_feeds_subsequent(df):
    # After the filter, only B remains; the test will fail (only one group).
    steps = [
        {"type": "transform",
         "args": {"op_type": "filter", "op_args": {"column": "group", "op": "==", "value": "B"}}},
        {"type": "test",
         "args": {"test_key": "independent_t",
                  "variables": {"outcome": "score", "groups": "group"}}},
    ]
    out = run_plan(steps=steps, df=df)
    assert out.status == "partial"
    assert out.result_blob["steps"][0]["status"] == "ok"
    assert out.result_blob["steps"][0]["output"]["n_rows_after"] == 6
    assert out.result_blob["steps"][1]["status"] == "failed"


def test_run_plan_does_not_abort_after_step_failure(df):
    """Critical invariant: a failed step does NOT stop the run."""
    steps = [
        {"type": "test",
         "args": {"test_key": "nope", "variables": {}}},  # unknown test_key
        {"type": "plot",
         "args": {"geom": "histogram", "x": "score"}},
    ]
    out = run_plan(steps=steps, df=df)
    assert len(out.result_blob["steps"]) == 2
    assert out.result_blob["steps"][0]["status"] == "failed"
    assert out.result_blob["steps"][1]["status"] == "ok"
