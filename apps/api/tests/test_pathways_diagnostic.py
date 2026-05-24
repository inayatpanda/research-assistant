"""F3 Pathway 4 — Diagnostic accuracy: backend tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.pathways import diagnostic
from research_api.services.pathways import prose as prose_svc


def _continuous_df(seed=0):
    rng = np.random.default_rng(seed)
    n = 200
    truth = rng.integers(0, 2, n)
    score = rng.normal(0.0, 1.0, n) + 1.8 * truth  # strong separation
    return pd.DataFrame({"score": score, "truth": truth})


def test_diagnostic_continuous_high_auc():
    df = _continuous_df()
    out = diagnostic.run(df, test="score", reference="truth")
    assert out["test_type"] == "continuous"
    assert out["auc"] > 0.8
    assert 0.0 < out["at_optimal"]["sensitivity"] <= 1.0
    assert 0.0 < out["at_optimal"]["specificity"] <= 1.0
    assert out["at_optimal"]["lr_pos"] is not None
    assert out["roc"]["fpr"][0] == 0.0


def test_diagnostic_random_test_auc_near_05():
    rng = np.random.default_rng(99)
    df = pd.DataFrame(
        {"score": rng.normal(0.0, 1.0, 400), "truth": rng.integers(0, 2, 400)}
    )
    out = diagnostic.run(df, test="score", reference="truth")
    assert 0.35 <= out["auc"] <= 0.65


def test_diagnostic_perfect_test_auc_one():
    df = pd.DataFrame(
        {"score": list(range(20)) + list(range(40, 60)),
         "truth": [0] * 20 + [1] * 20}
    )
    out = diagnostic.run(df, test="score", reference="truth")
    assert out["auc"] >= 0.99
    assert out["at_optimal"]["sensitivity"] >= 0.99
    assert out["at_optimal"]["specificity"] >= 0.99


def test_diagnostic_binary_test():
    df = pd.DataFrame(
        {"flag": [1, 1, 0, 0, 1, 1, 0, 0], "truth": [1, 1, 1, 0, 1, 0, 0, 0]}
    )
    out = diagnostic.run(df, test="flag", reference="truth")
    assert out["test_type"] == "binary"
    m = out["metrics"]
    assert m["tp"] == 3 and m["tn"] == 3 and m["fp"] == 1 and m["fn"] == 1


def test_diagnostic_bayes_post_test_probability():
    df = _continuous_df()
    out = diagnostic.run(
        df, test="score", reference="truth", pre_test_probability=0.2
    )
    assert "bayes" in out
    assert 0.0 < out["bayes"]["post_test_prob_positive"] <= 1.0
    # Post(+) should be higher than pre when LR+ > 1.
    assert out["bayes"]["post_test_prob_positive"] > 0.2


def test_diagnostic_bad_pretest_raises():
    df = _continuous_df()
    with pytest.raises(ValueError):
        diagnostic.run(df, test="score", reference="truth", pre_test_probability=1.5)


def test_diagnostic_non_binary_reference_raises():
    df = pd.DataFrame({"score": [1, 2, 3], "ref": [0, 1, 2]})
    with pytest.raises(ValueError):
        diagnostic.run(df, test="score", reference="ref")


def test_diagnostic_prose_includes_auc_and_sens_spec():
    df = _continuous_df()
    out = diagnostic.run(df, test="score", reference="truth")
    p = prose_svc.prose_diagnostic(out)
    assert "AUC" in p["results"]
    assert "sensitivity" in p["results"]


async def _project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "P", "study_type": "Outcome Study"},
    )
    return r.json()["id"]


CSV_DIAG = b"score,truth\n" + b"\n".join(
    f"{0.5 + (i % 5):.2f},{1 if i % 5 >= 3 else 0}".encode() for i in range(60)
) + b"\n"


@pytest.mark.asyncio
async def test_route_diagnostic_happy_path(client):
    pid = await _project(client)
    files = {"file": ("d.csv", CSV_DIAG, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    assert r.status_code == 201
    ds = r.json()
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/pathways/diagnostic",
        json={"test": "score", "reference": "truth"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["test_type"] == "continuous"
    assert "auc" in body["result"]
