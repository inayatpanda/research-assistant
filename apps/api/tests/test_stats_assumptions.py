from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.assumptions import (
    AssumptionCheck,
    levene,
    proportional_hazards_check,
    shapiro,
)


def test_shapiro_normal_sample_passes():
    rng = np.random.default_rng(0)
    sample = rng.normal(size=200).tolist()
    result = shapiro(sample)
    assert isinstance(result, AssumptionCheck)
    assert result.test_name == "shapiro"
    assert 0.0 <= result.p_value <= 1.0
    assert result.ok is True
    assert result.p_value > 0.05


def test_shapiro_bimodal_fails():
    sample = [1.0] * 50 + [10.0] * 50
    result = shapiro(sample)
    assert result.ok is False
    assert result.p_value < 0.05


def test_shapiro_returns_message():
    rng = np.random.default_rng(0)
    sample = rng.normal(size=50).tolist()
    result = shapiro(sample)
    assert result.note
    assert "normal" in result.note.lower()


def test_shapiro_too_few_points():
    result = shapiro([1.0, 2.0])
    assert result.ok is False
    assert "too few" in result.note.lower() or "insufficient" in result.note.lower()


def test_levene_equal_variance_passes():
    rng = np.random.default_rng(1)
    a = rng.normal(0, 1, size=100).tolist()
    b = rng.normal(0, 1, size=100).tolist()
    result = levene(a, b)
    assert result.test_name == "levene"
    assert result.ok is True
    assert result.p_value > 0.05


def test_levene_unequal_variance_fails():
    rng = np.random.default_rng(2)
    a = rng.normal(0, 1.0, size=200).tolist()
    b = rng.normal(0, 5.0, size=200).tolist()
    result = levene(a, b)
    assert result.ok is False
    assert result.p_value < 0.05


def test_levene_three_groups_supported():
    rng = np.random.default_rng(3)
    a = rng.normal(0, 1, size=80).tolist()
    b = rng.normal(0, 1, size=80).tolist()
    c = rng.normal(0, 1, size=80).tolist()
    result = levene(a, b, c)
    assert isinstance(result.statistic, float)
    assert 0.0 <= result.p_value <= 1.0


def test_levene_requires_two_groups():
    with pytest.raises(ValueError):
        levene([1.0, 2.0, 3.0])


def test_proportional_hazards_check_returns_shape():
    rng = np.random.default_rng(4)
    n = 80
    df = pd.DataFrame(
        {
            "time": rng.uniform(1, 100, size=n),
            "event": rng.integers(0, 2, size=n),
            "covariate": rng.normal(0, 1, size=n),
        }
    )
    result = proportional_hazards_check(df, duration_col="time", event_col="event")
    assert result.test_name == "prop_hazards"
    assert isinstance(result.statistic, float)
    assert 0.0 <= result.p_value <= 1.0
    assert isinstance(result.ok, bool)


def test_proportional_hazards_check_message_present():
    rng = np.random.default_rng(5)
    n = 60
    df = pd.DataFrame(
        {
            "time": rng.uniform(1, 50, size=n),
            "event": rng.integers(0, 2, size=n),
            "age": rng.normal(50, 10, size=n),
        }
    )
    result = proportional_hazards_check(df, duration_col="time", event_col="event")
    assert result.note
