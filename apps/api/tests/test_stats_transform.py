"""Phase 13 (MP13) — Pure-function transform op tests."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.transform import (
    OP_TYPES,
    TransformError,
    apply_op,
    apply_transformations,
)


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [10.0, 20.0, 30.0, 40.0, 50.0],
            "g": ["x", "x", "y", "y", "z"],
            "miss": [1.0, None, 3.0, None, 5.0],
        }
    )


# ── filter ─────────────────────────────────────────────────────────────


def test_filter_eq_keeps_only_matching_rows():
    out = apply_op(_df(), "filter", {"column": "g", "op": "==", "value": "x"})
    assert list(out["a"]) == [1.0, 2.0]


def test_filter_gt_with_numeric_threshold():
    out = apply_op(_df(), "filter", {"column": "a", "op": ">", "value": 3})
    assert list(out["a"]) == [4.0, 5.0]


def test_filter_in_list():
    out = apply_op(
        _df(), "filter", {"column": "g", "op": "in", "value": ["y", "z"]}
    )
    assert list(out["g"]) == ["y", "y", "z"]


def test_filter_notna_drops_only_nulls_in_column():
    out = apply_op(_df(), "filter", {"column": "miss", "op": "notna", "value": None})
    assert list(out["miss"]) == [1.0, 3.0, 5.0]


def test_filter_isna_keeps_only_nulls():
    out = apply_op(_df(), "filter", {"column": "miss", "op": "isna", "value": None})
    assert out.shape[0] == 2
    assert out["miss"].isna().all()


def test_filter_unknown_op_raises():
    with pytest.raises(TransformError):
        apply_op(_df(), "filter", {"column": "a", "op": "~~", "value": 0})


def test_filter_missing_column_raises():
    with pytest.raises(TransformError):
        apply_op(_df(), "filter", {"column": "nope", "op": "==", "value": 0})


def test_filter_does_not_mutate_input():
    df = _df()
    apply_op(df, "filter", {"column": "a", "op": ">", "value": 3})
    assert df.shape[0] == 5


# ── filter (expression shape, DEMO-FIX-D HIGH-2) ───────────────────────


def test_filter_expr_string_equality():
    """The new UI persists ``{expr: "g == 'x'"}`` — _filter must accept it."""
    out = apply_op(_df(), "filter", {"expr": "g == 'x'"})
    assert list(out["a"]) == [1.0, 2.0]


def test_filter_expr_numeric_comparison():
    out = apply_op(_df(), "filter", {"expr": "a > 3"})
    assert list(out["a"]) == [4.0, 5.0]


def test_filter_expr_compound_boolean():
    out = apply_op(_df(), "filter", {"expr": "a > 1 and g == 'x'"})
    assert list(out["a"]) == [2.0]


def test_filter_expr_unknown_column_rejected():
    with pytest.raises(TransformError):
        apply_op(_df(), "filter", {"expr": "no_such_col == 1"})


def test_filter_expr_forbids_attribute_access():
    """Whitelisting must reject ``.`` to block ``__builtins__`` style access."""
    with pytest.raises(TransformError):
        apply_op(_df(), "filter", {"expr": "a.__class__ == 'int'"})


def test_filter_expr_forbids_parentheses_call_syntax():
    """No call-like syntax — closes another exfiltration vector."""
    with pytest.raises(TransformError):
        apply_op(_df(), "filter", {"expr": "len(a) > 0"})


def test_filter_expr_list_literal_rejected():
    """List literals require ``[`` / ``]`` which we forbid — caller should
    fall back to the structured ``{column, op: in, value: [...]}`` shape.
    """
    with pytest.raises(TransformError):
        apply_op(_df(), "filter", {"expr": "g in ['y', 'z']"})



def test_mutate_simple_column_copy():
    out = apply_op(_df(), "mutate", {"new_column": "a_copy", "expression": "a"})
    assert list(out["a_copy"]) == list(_df()["a"])


def test_mutate_log_of_column():
    out = apply_op(_df(), "mutate", {"new_column": "log_a", "expression": "log(a)"})
    assert math.isclose(float(out["log_a"].iloc[0]), math.log(1.0))
    assert math.isclose(float(out["log_a"].iloc[4]), math.log(5.0))


def test_mutate_column_arithmetic():
    out = apply_op(
        _df(), "mutate", {"new_column": "sum_ab", "expression": "a + b"}
    )
    assert list(out["sum_ab"]) == [11.0, 22.0, 33.0, 44.0, 55.0]


def test_mutate_scalar_multiplier():
    out = apply_op(
        _df(), "mutate", {"new_column": "scaled", "expression": "a * 2"}
    )
    assert list(out["scaled"]) == [2.0, 4.0, 6.0, 8.0, 10.0]


def test_mutate_invalid_expression_raises():
    with pytest.raises(TransformError):
        apply_op(_df(), "mutate", {"new_column": "x", "expression": "a + + b"})


# ── select ─────────────────────────────────────────────────────────────


def test_select_keeps_subset_of_columns():
    out = apply_op(_df(), "select", {"columns": ["a", "g"]})
    assert list(out.columns) == ["a", "g"]


def test_select_missing_column_raises():
    with pytest.raises(TransformError):
        apply_op(_df(), "select", {"columns": ["a", "nope"]})


# ── recode ─────────────────────────────────────────────────────────────


def test_recode_maps_values_keeps_unmapped():
    out = apply_op(
        _df(), "recode", {"column": "g", "mapping": {"x": "alpha"}}
    )
    assert list(out["g"]) == ["alpha", "alpha", "y", "y", "z"]


def test_recode_with_default_replaces_unmapped():
    out = apply_op(
        _df(),
        "recode",
        {"column": "g", "mapping": {"x": "alpha"}, "default": "other"},
    )
    assert list(out["g"]) == ["alpha", "alpha", "other", "other", "other"]


# ── drop_na ────────────────────────────────────────────────────────────


def test_drop_na_specific_column():
    out = apply_op(_df(), "drop_na", {"columns": ["miss"]})
    assert out["miss"].notna().all()
    assert out.shape[0] == 3


def test_drop_na_all_columns_when_null():
    out = apply_op(_df(), "drop_na", {"columns": None})
    assert out.shape[0] == 3


# ── log_transform ──────────────────────────────────────────────────────


def test_log_transform_base_e_default():
    out = apply_op(
        _df(), "log_transform", {"column": "b", "new_column": "log_b"}
    )
    assert math.isclose(float(out["log_b"].iloc[0]), math.log(10.0))


def test_log_transform_base_10():
    out = apply_op(
        _df(),
        "log_transform",
        {"column": "b", "new_column": "log10_b", "base": "10"},
    )
    assert math.isclose(float(out["log10_b"].iloc[1]), math.log10(20.0))


def test_log_transform_bad_base_raises():
    with pytest.raises(TransformError):
        apply_op(
            _df(),
            "log_transform",
            {"column": "b", "new_column": "x", "base": "bad"},
        )


# ── z_score ────────────────────────────────────────────────────────────


def test_z_score_mean_zero_std_one():
    out = apply_op(_df(), "z_score", {"column": "a", "new_column": "z_a"})
    assert math.isclose(float(out["z_a"].mean()), 0.0, abs_tol=1e-9)
    assert math.isclose(float(out["z_a"].std(ddof=1)), 1.0, abs_tol=1e-9)


def test_z_score_zero_variance_raises():
    df = pd.DataFrame({"x": [1.0, 1.0, 1.0]})
    with pytest.raises(TransformError):
        apply_op(df, "z_score", {"column": "x", "new_column": "z"})


# ── group_summarise ────────────────────────────────────────────────────


def test_group_summarise_mean_per_group():
    out = apply_op(
        _df(),
        "group_summarise",
        {"by": ["g"], "agg": {"a": "mean"}},
    )
    out = out.sort_values("g").reset_index(drop=True)
    assert list(out["g"]) == ["x", "y", "z"]
    assert list(out["a"]) == [1.5, 3.5, 5.0]


def test_group_summarise_unknown_agg_raises():
    with pytest.raises(TransformError):
        apply_op(
            _df(),
            "group_summarise",
            {"by": ["g"], "agg": {"a": "median_squared"}},
        )


# ── pipeline ───────────────────────────────────────────────────────────


def test_apply_transformations_runs_in_order():
    ops = [
        {"op_type": "filter", "op_args": {"column": "miss", "op": "notna"}},
        {
            "op_type": "log_transform",
            "op_args": {"column": "miss", "new_column": "log_miss"},
        },
    ]
    out = apply_transformations(_df(), ops)
    assert out.shape[0] == 3
    assert "log_miss" in out.columns


def test_apply_transformations_does_not_mutate_input():
    df = _df()
    ops = [{"op_type": "drop_na", "op_args": {"columns": None}}]
    apply_transformations(df, ops)
    assert df.shape[0] == 5


def test_apply_transformations_empty_stack_is_identity():
    df = _df()
    out = apply_transformations(df, [])
    assert out.equals(df)


def test_op_types_constant_matches_dispatch():
    # Just a guard to keep the schema Literal in sync.
    assert set(OP_TYPES) == {
        "filter",
        "mutate",
        "select",
        "recode",
        "drop_na",
        "log_transform",
        "z_score",
        "group_summarise",
        "drop_rows",
    }


def test_drop_rows_by_integer_indices():
    df = _df()
    n = len(df)
    out = apply_op(df, "drop_rows", {"indices": [0, 2]})
    assert len(out) == n - 2


def test_drop_rows_by_r_prefixed_ids():
    df = _df()
    n = len(df)
    out = apply_op(df, "drop_rows", {"drop_row_ids": ["r-0", "r-1"]})
    assert len(out) == n - 2


def test_drop_rows_empty_list_is_identity():
    df = _df()
    out = apply_op(df, "drop_rows", {"indices": []})
    assert len(out) == len(df)


def test_drop_rows_invalid_id_raises():
    df = _df()
    with pytest.raises(TransformError):
        apply_op(df, "drop_rows", {"drop_row_ids": ["nonsense"]})


def test_unknown_op_type_raises():
    with pytest.raises(TransformError):
        apply_op(_df(), "rotate_42", {})
