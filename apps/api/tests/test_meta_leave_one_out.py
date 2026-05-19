"""Phase 19 (MP19) — Leave-one-out sensitivity analysis."""
from __future__ import annotations

import pytest

from research_api.services.meta import effect_sizes as es
from research_api.services.meta.leave_one_out import (
    leave_one_out,
    render_leave_one_out_png,
)


def _eff(yi: float, se: float) -> es.Effect:
    return es.Effect(yi=yi, se=se, vi=se * se, metric="md")


def test_leave_one_out_returns_one_row_per_excluded_study():
    effects = [_eff(0.2, 0.1), _eff(0.4, 0.1), _eff(0.3, 0.1)]
    rows = leave_one_out(effects, ids=["s1", "s2", "s3"], model="fixed")
    assert [r.excluded_id for r in rows] == ["s1", "s2", "s3"]


def test_leave_one_out_drops_outlier_shifts_pooled():
    # Outlier s4 has a huge positive effect — excluding it lowers the pool.
    effects = [_eff(0.10, 0.1), _eff(0.15, 0.1), _eff(0.20, 0.1), _eff(2.0, 0.1)]
    rows = leave_one_out(effects, ids=["s1", "s2", "s3", "s4"], model="fixed")
    excluding_outlier = next(r for r in rows if r.excluded_id == "s4")
    excluding_first = next(r for r in rows if r.excluded_id == "s1")
    assert excluding_outlier.pooled_effect < excluding_first.pooled_effect


def test_leave_one_out_needs_three_studies():
    effects = [_eff(0.1, 0.1), _eff(0.2, 0.1)]
    with pytest.raises(ValueError):
        leave_one_out(effects, ids=["s1", "s2"], model="fixed")


def test_leave_one_out_ids_length_mismatch():
    effects = [_eff(0.1, 0.1), _eff(0.2, 0.1), _eff(0.3, 0.1)]
    with pytest.raises(ValueError):
        leave_one_out(effects, ids=["s1", "s2"], model="fixed")


def test_leave_one_out_each_row_has_finite_i2():
    effects = [_eff(0.1, 0.1), _eff(0.2, 0.1), _eff(0.3, 0.1)]
    rows = leave_one_out(effects, ids=["a", "b", "c"], model="random")
    for r in rows:
        assert 0.0 <= r.i2 <= 100.0


def test_render_leave_one_out_png_returns_bytes():
    effects = [_eff(0.1, 0.1), _eff(0.2, 0.1), _eff(0.3, 0.1)]
    rows = leave_one_out(effects, ids=["a", "b", "c"], model="fixed")
    png = render_leave_one_out_png(rows, overall_estimate=0.2, metric_label="MD")
    assert png.startswith(b"\x89PNG")
