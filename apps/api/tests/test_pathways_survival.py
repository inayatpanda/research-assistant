"""F3 Pathway 3 — Survival: backend tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.pathways import prose as prose_svc
from research_api.services.pathways import survival


def _survival_df(n=80, seed=1):
    rng = np.random.default_rng(seed)
    arm = np.array(["A"] * (n // 2) + ["B"] * (n // 2))
    base = rng.exponential(scale=20.0, size=n)
    # Make arm B have shorter survival.
    base = np.where(arm == "B", base * 0.5, base)
    censor = rng.binomial(1, 0.8, n)
    return pd.DataFrame({"time": base, "event": censor, "arm": arm})


def test_survival_overall_km_runs():
    df = _survival_df()
    out = survival.run(df, time="time", event="event")
    assert out["n"] == len(df)
    assert out["overall"]["n_events"] >= 1
    assert isinstance(out["overall"]["times"], list)


def test_survival_with_strata_runs_logrank():
    df = _survival_df()
    out = survival.run(df, time="time", event="event", strata="arm")
    assert "logrank" in out
    assert "test_statistic" in out["logrank"]
    assert "p_value" in out["logrank"]


def test_survival_with_cox_predictor():
    df = _survival_df()
    df["age"] = np.random.default_rng(3).normal(60, 5, len(df))
    out = survival.run(
        df, time="time", event="event", predictors=["age"]
    )
    assert "cox" in out
    if "error" not in out["cox"]:
        terms = out["cox"]["terms"]
        assert any(t["term"] == "age" for t in terms)


def test_survival_no_events_raises():
    df = pd.DataFrame({"time": [1, 2, 3, 4], "event": [0, 0, 0, 0]})
    with pytest.raises(ValueError):
        survival.run(df, time="time", event="event")


def test_survival_negative_time_raises():
    df = pd.DataFrame({"time": [-1, 2, 3], "event": [1, 0, 1]})
    with pytest.raises(ValueError):
        survival.run(df, time="time", event="event")


def test_survival_bad_event_values_raises():
    df = pd.DataFrame({"time": [1, 2, 3], "event": [2, 0, 1]})
    with pytest.raises(ValueError):
        survival.run(df, time="time", event="event")


def test_survival_prose_includes_kaplan_meier():
    df = _survival_df()
    out = survival.run(df, time="time", event="event", strata="arm")
    p = prose_svc.prose_survival(out)
    assert "Kaplan-Meier" in p["methods"]
    assert "log-rank" in p["methods"] or "log-rank" in p["results"].lower()


CSV_SURV = b"time,event,arm\n" + b"\n".join(
    f"{10 + i % 20},{i % 2},{'A' if i % 2 == 0 else 'B'}".encode()
    for i in range(40)
) + b"\n"


async def _project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "P", "study_type": "Prospective Cohort"},
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_route_survival_happy_path(client):
    pid = await _project(client)
    files = {"file": ("s.csv", CSV_SURV, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    assert r.status_code == 201
    ds = r.json()
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/pathways/survival",
        json={"time": "time", "event": "event", "strata": "arm"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "overall" in body["result"]
    assert "Methods:" in body["prose"]["methods"]
