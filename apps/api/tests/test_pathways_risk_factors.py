"""F3 Pathway 2 — Risk factor identification: backend tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.pathways import prose as prose_svc
from research_api.services.pathways import risk_factors


def _binary_df(n=200, seed=0):
    rng = np.random.default_rng(seed)
    age = rng.normal(60, 10, n)
    sex = rng.integers(0, 2, n)
    smoker = rng.integers(0, 2, n)
    # outcome strongly driven by age + smoker.
    logit = -5 + 0.05 * age + 1.5 * smoker
    p = 1.0 / (1.0 + np.exp(-logit))
    y = rng.binomial(1, p, n)
    return pd.DataFrame({"y": y, "age": age, "sex": sex, "smoker": smoker})


def _continuous_df(n=120, seed=0):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    y = 1.5 + 0.8 * x1 + 0.3 * x2 + rng.normal(0, 0.5, n)
    return pd.DataFrame({"y": y, "x1": x1, "x2": x2})


def test_risk_factors_binary_outcome_runs_logistic():
    df = _binary_df()
    out = risk_factors.run(df, outcome="y", predictors=["age", "smoker"])
    assert out["model"] == "logistic"
    assert len(out["multivariable"]) >= 2
    rows = {r["term"]: r for r in out["multivariable"]}
    assert "age" in rows
    # OR for age should be > 1 given how we generated.
    assert rows["age"]["estimate"] > 1.0
    assert "auc" in out["omnibus"]
    assert "hosmer_lemeshow_p" in out["omnibus"]


def test_risk_factors_univariable_and_multivariable_present():
    df = _binary_df()
    out = risk_factors.run(df, outcome="y", predictors=["age", "smoker", "sex"])
    assert len(out["univariable"]) == 3
    assert len(out["multivariable"]) == 3


def test_risk_factors_continuous_outcome_runs_linear():
    df = _continuous_df()
    out = risk_factors.run(df, outcome="y", predictors=["x1", "x2"])
    assert out["model"] == "linear"
    rows = {r["term"]: r for r in out["multivariable"]}
    # x1 beta should be near 0.8.
    assert 0.5 < rows["x1"]["estimate"] < 1.1
    assert "r_squared" in out["omnibus"]
    assert out["omnibus"]["r_squared"] > 0.5


def test_risk_factors_confounders_force_into_model():
    df = _binary_df()
    out = risk_factors.run(
        df, outcome="y", predictors=["smoker"], confounders=["age"]
    )
    rows = {r["term"]: r for r in out["multivariable"]}
    assert "age" in rows
    assert "smoker" in rows


def test_risk_factors_multicollinearity_warning():
    rng = np.random.default_rng(7)
    n = 200
    x1 = rng.normal(0, 1, n)
    x2 = x1 + rng.normal(0, 0.01, n)  # almost perfectly collinear
    y = 1 + 2 * x1 + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"y": y, "x1": x1, "x2": x2})
    out = risk_factors.run(df, outcome="y", predictors=["x1", "x2"])
    assert out["omnibus"].get("multicollinearity_warning") is True
    assert out["omnibus"].get("max_vif") > 5


def test_risk_factors_missing_outcome_column_raises():
    df = _binary_df()
    with pytest.raises(ValueError):
        risk_factors.run(df, outcome="missing", predictors=["age"])


def test_risk_factors_empty_predictors_raises():
    df = _binary_df()
    with pytest.raises(ValueError):
        risk_factors.run(df, outcome="y", predictors=[])


def test_risk_factors_prose_includes_aor_or_beta():
    df = _binary_df()
    out = risk_factors.run(df, outcome="y", predictors=["age", "smoker"])
    prose = prose_svc.prose_risk_factors(out)
    assert "OR" in prose["results"] or "aOR" in prose["methods"]
    assert "logistic" in prose["methods"]


CSV_BIN = b"y,age,smoker\n" + b"\n".join(
    f"{(i + 7) % 2},{40 + i % 25},{i % 3 % 2}".encode() for i in range(60)
) + b"\n"


async def _project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Risk Factor Analysis"}
    )
    return r.json()["id"]


async def _upload(client, project_id, body=CSV_BIN):
    files = {"file": ("d.csv", body, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_route_risk_factors_happy_path(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/pathways/risk-factors",
        json={"outcome": "y", "predictors": ["age", "smoker"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["model"] == "logistic"
    assert "univariable" in body["result"]
    assert "multivariable" in body["result"]
