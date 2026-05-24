"""F3 Pathway 5 — Agreement / reliability: backend tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.pathways import agreement
from research_api.services.pathways import prose as prose_svc


def test_agreement_continuous_perfect_agreement():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    df["b"] = df["a"]
    out = agreement.run(df, rater_a="a", rater_b="b")
    assert out["data_type"] == "continuous"
    assert out["icc"]["icc"] > 0.99
    assert abs(out["bland_altman"]["bias"]) < 1e-9


def test_agreement_continuous_random_low_icc():
    rng = np.random.default_rng(11)
    df = pd.DataFrame(
        {"a": rng.normal(0, 1, 40), "b": rng.normal(0, 1, 40)}
    )
    out = agreement.run(df, rater_a="a", rater_b="b")
    # Random pairs should have ICC near zero (or below).
    assert -0.5 < out["icc"]["icc"] < 0.5


def test_agreement_continuous_bland_altman_loa_present():
    rng = np.random.default_rng(2)
    a = rng.normal(0, 1, 50)
    b = a + rng.normal(0, 0.5, 50)
    df = pd.DataFrame({"a": a, "b": b})
    out = agreement.run(df, rater_a="a", rater_b="b")
    ba = out["bland_altman"]
    assert ba["loa_low"] < ba["bias"] < ba["loa_high"]
    assert len(ba["points"]) == 50


def test_agreement_categorical_cohen_kappa():
    df = pd.DataFrame(
        {
            "a": ["yes", "yes", "no", "no", "yes", "no"],
            "b": ["yes", "no", "no", "no", "yes", "no"],
        }
    )
    out = agreement.run(df, rater_a="a", rater_b="b")
    assert out["data_type"] == "categorical"
    assert -1.0 <= out["kappa"]["kappa"] <= 1.0


def test_agreement_categorical_weighted_kappa_for_ordinal():
    df = pd.DataFrame(
        {
            "a": ["low", "med", "high", "low", "med", "high"] * 4,
            "b": ["low", "low", "high", "med", "med", "high"] * 4,
        }
    )
    out = agreement.run(df, rater_a="a", rater_b="b")
    assert "weighted_kappa" in out
    assert -1.0 <= out["weighted_kappa"]["kappa"] <= 1.0


def test_agreement_too_few_pairs_raises():
    df = pd.DataFrame({"a": [1], "b": [1]})
    with pytest.raises(ValueError):
        agreement.run(df, rater_a="a", rater_b="b")


def test_agreement_same_rater_raises():
    df = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(ValueError):
        agreement.run(df, rater_a="a", rater_b="a")


def test_agreement_prose_includes_icc_or_kappa():
    df = pd.DataFrame({"a": list(range(20)), "b": [x + 0.5 for x in range(20)]})
    out = agreement.run(df, rater_a="a", rater_b="b")
    p = prose_svc.prose_agreement(out)
    assert "ICC" in p["methods"]
    assert "Bland-Altman" in p["methods"]


async def _project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "P", "study_type": "Outcome Study"},
    )
    return r.json()["id"]


CSV_AGREE = b"a,b\n" + b"\n".join(
    f"{1 + (i % 5)},{1 + ((i + 1) % 5)}".encode() for i in range(40)
) + b"\n"


@pytest.mark.asyncio
async def test_route_agreement_happy_path(client):
    pid = await _project(client)
    files = {"file": ("g.csv", CSV_AGREE, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    assert r.status_code == 201
    ds = r.json()
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/pathways/agreement",
        json={"rater_a": "a", "rater_b": "b"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["data_type"] == "continuous"
    assert "icc" in body["result"]


@pytest.mark.asyncio
async def test_route_push_to_manuscript(client):
    pid = await _project(client)
    files = {"file": ("g.csv", CSV_AGREE, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    ds = r.json()
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/pathways/push-to-manuscript",
        json={
            "pathway": "agreement",
            "target": "both",
            "methods": "Custom methods text",
            "results": "Custom results text",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["methods"] is not None
    assert body["results"] is not None
    assert "Custom methods text" in body["methods"]["content"]
    assert "Custom results text" in body["results"]["content"]
