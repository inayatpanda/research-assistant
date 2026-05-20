"""DEMO-FIX-A — Unit tests for the standalone diagnostics service.

Each test uses a hand-verified data shape (clear normal vs clear skew, or
equal vs unequal variance) so we know what the answer should be and can
assert on direction (pass / fail) without depending on tiny p-value
numerics.
"""
from __future__ import annotations

import numpy as np
import pytest

from research_api.services.stats import diagnostics_standalone as diag


# ── Normality: pass / fail direction ───────────────────────────────────


def test_shapiro_wilk_normal_sample_passes():
    rng = np.random.default_rng(42)
    sample = rng.normal(loc=0.0, scale=1.0, size=200).tolist()
    out = diag.shapiro_wilk(sample)
    assert out["n"] == 200
    assert 0.0 <= out["statistic"] <= 1.0
    assert out["p"] > 0.05
    assert "consistent with a normal distribution" in out["interpretation"]


def test_shapiro_wilk_skewed_sample_fails_and_recommends_nonparametric():
    rng = np.random.default_rng(7)
    sample = rng.exponential(scale=1.0, size=200).tolist()
    out = diag.shapiro_wilk(sample)
    assert out["p"] < 0.05
    # The interpretation MUST suggest a non-parametric alternative.
    text = out["interpretation"].lower()
    assert "non-parametric" in text
    assert "mann-whitney" in text


def test_shapiro_wilk_too_few_values_raises():
    with pytest.raises(ValueError):
        diag.shapiro_wilk([1.0, 2.0])


def test_anderson_darling_returns_critical_value_dict():
    rng = np.random.default_rng(0)
    sample = rng.normal(0, 1, size=100).tolist()
    out = diag.anderson_darling(sample)
    assert "5%" in out["critical_values"]
    assert out["statistic"] >= 0
    # On a clear normal sample the statistic should be below the 5%
    # critical value most of the time → "consistent with a normal".
    assert "Anderson-Darling" in out["interpretation"]


def test_anderson_darling_skew_data_flags_departure():
    rng = np.random.default_rng(13)
    # Lognormal is strongly skewed → AD should reject normality.
    sample = rng.lognormal(mean=0.0, sigma=1.5, size=200).tolist()
    out = diag.anderson_darling(sample)
    assert out["statistic"] > out["critical_values"]["5%"]
    assert "Departure" in out["interpretation"]


def test_kolmogorov_smirnov_normal_passes():
    rng = np.random.default_rng(1)
    sample = rng.normal(0, 1, size=150).tolist()
    out = diag.kolmogorov_smirnov(sample)
    assert out["p"] > 0.05
    assert "consistent with a normal distribution" in out["interpretation"]


def test_dagostino_pearson_normal_passes_skew_fails():
    rng = np.random.default_rng(2)
    normal_sample = rng.normal(0, 1, size=200).tolist()
    out_norm = diag.dagostino_pearson(normal_sample)
    assert out_norm["p"] > 0.05
    skew_sample = rng.exponential(scale=1.0, size=200).tolist()
    out_skew = diag.dagostino_pearson(skew_sample)
    assert out_skew["p"] < 0.05
    assert "skew" in out_skew["interpretation"].lower()


# ── Equality of variance ───────────────────────────────────────────────


def test_levene_equal_variances_passes():
    rng = np.random.default_rng(3)
    g1 = rng.normal(0, 1, size=80).tolist()
    g2 = rng.normal(0, 1, size=80).tolist()
    out = diag.levene({"a": g1, "b": g2})
    assert out["k"] == 2
    assert out["center"] == "median"
    assert out["p"] > 0.05
    assert "consistent with equality" in out["interpretation"]


def test_levene_unequal_variances_fails_and_recommends_welch():
    rng = np.random.default_rng(4)
    g1 = rng.normal(0, 1.0, size=100).tolist()
    g2 = rng.normal(0, 4.0, size=100).tolist()
    out = diag.levene({"a": g1, "b": g2})
    assert out["p"] < 0.05
    assert "welch" in out["interpretation"].lower()


def test_bartlett_unequal_variances_fails():
    rng = np.random.default_rng(5)
    g1 = rng.normal(0, 1, size=80).tolist()
    g2 = rng.normal(0, 5, size=80).tolist()
    out = diag.bartlett({"a": g1, "b": g2})
    assert out["p"] < 0.05
    assert "differ significantly" in out["interpretation"]


def test_levene_requires_two_groups():
    with pytest.raises(ValueError):
        diag.levene({"only": [1.0, 2.0, 3.0]})


# ── Visual diagnostics ─────────────────────────────────────────────────


def test_qq_plot_png_returns_png_bytes():
    rng = np.random.default_rng(6)
    sample = rng.normal(0, 1, size=80).tolist()
    raw = diag.qq_plot_png(sample, title="Test")
    assert isinstance(raw, (bytes, bytearray))
    # PNG magic header.
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_histogram_normal_overlay_png_returns_png_bytes():
    rng = np.random.default_rng(8)
    sample = rng.normal(0, 1, size=80).tolist()
    raw = diag.histogram_normal_overlay_png(sample, title="Hist")
    assert isinstance(raw, (bytes, bytearray))
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
