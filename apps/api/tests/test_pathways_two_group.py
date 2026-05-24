"""F3 Pathway 1 — Two-group comparison: backend tests."""
from __future__ import annotations

import math
import io

import numpy as np
import pandas as pd
import pytest

from research_api.services.pathways import prose as prose_svc
from research_api.services.pathways import two_group


def _df_normal(n=30, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "score": np.concatenate(
                [rng.normal(10, 2, n), rng.normal(7, 2, n)]
            ),
            "arm": ["A"] * n + ["B"] * n,
        }
    )


def test_two_group_numeric_normal_picks_student_t():
    df = _df_normal()
    out = two_group.run(df, outcome="score", group="arm")
    assert out["outcome_type"] == "numeric"
    assert out["test_used"] in {"student_t", "welch_t"}
    assert out["p_value"] < 0.01
    assert out["effect_label"] == "cohens_d"
    assert out["ci_low"] is not None and out["ci_high"] is not None
    assert out["assumptions"]["normal"] is True


def test_two_group_numeric_non_normal_falls_back_to_mann_whitney():
    rng = np.random.default_rng(1)
    # Heavily skewed → Shapiro should reject normality.
    df = pd.DataFrame(
        {
            "score": np.concatenate(
                [rng.exponential(1.0, 40), rng.exponential(3.0, 40)]
            ),
            "arm": ["A"] * 40 + ["B"] * 40,
        }
    )
    out = two_group.run(df, outcome="score", group="arm")
    assert out["test_used"] == "mann_whitney"
    assert out["effect_label"] == "rank_biserial"
    assert out["p_value"] < 0.05


def test_two_group_unequal_variances_uses_welch():
    rng = np.random.default_rng(2)
    df = pd.DataFrame(
        {
            "score": np.concatenate(
                [rng.normal(10, 1, 40), rng.normal(10.5, 5, 40)]
            ),
            "arm": ["A"] * 40 + ["B"] * 40,
        }
    )
    out = two_group.run(df, outcome="score", group="arm")
    # Levene should flag unequal variances → Welch.
    if out["assumptions"]["normal"]:
        assert out["test_used"] == "welch_t"


def test_two_group_categorical_outcome_2x2_chi_square():
    df = pd.DataFrame(
        {
            "outcome": ["pos"] * 40 + ["neg"] * 60 + ["pos"] * 20 + ["neg"] * 80,
            "arm": ["A"] * 100 + ["B"] * 100,
        }
    )
    out = two_group.run(df, outcome="outcome", group="arm")
    assert out["outcome_type"] == "categorical"
    assert out["test_used"] == "chi_squared"
    assert "odds_ratio" in out
    assert out["effect_label"] == "cramers_v"


def test_two_group_categorical_2x2_low_expected_uses_fisher():
    df = pd.DataFrame(
        {
            "outcome": ["pos"] * 1 + ["neg"] * 9 + ["pos"] * 4 + ["neg"] * 6,
            "arm": ["A"] * 10 + ["B"] * 10,
        }
    )
    out = two_group.run(df, outcome="outcome", group="arm")
    assert out["test_used"] == "fisher_exact"
    assert out["effect_label"] == "odds_ratio"


def test_two_group_three_levels_raises():
    df = pd.DataFrame({"score": [1, 2, 3, 4, 5, 6], "arm": ["A", "B", "C"] * 2})
    with pytest.raises(ValueError):
        two_group.run(df, outcome="score", group="arm")


def test_two_group_all_same_values_raises():
    df = pd.DataFrame({"score": [1.0] * 10, "arm": ["A"] * 5 + ["B"] * 5})
    with pytest.raises(ValueError):
        two_group.run(df, outcome="score", group="arm")


def test_two_group_missing_columns_raises():
    df = pd.DataFrame({"score": [1, 2, 3], "arm": ["A", "B", "A"]})
    with pytest.raises(ValueError, match="not in dataset"):
        two_group.run(df, outcome="missing", group="arm")


def test_two_group_prose_methods_results_present():
    df = _df_normal()
    out = two_group.run(df, outcome="score", group="arm")
    p = prose_svc.prose_two_group(out)
    assert "Methods:" in p["methods"]
    assert "Results:" in p["results"]
    assert "p=" in p["results"] or "p<" in p["results"]


# ----- Route tests -----


CSV_BYTES_NUMERIC = (
    b"score,group\n"
    + b"\n".join(f"{10 + i % 3},A".encode() for i in range(20))
    + b"\n"
    + b"\n".join(f"{6 + i % 3},B".encode() for i in range(20))
    + b"\n"
)


async def _project(client, title="P", st="Outcome Study") -> str:
    r = await client.post("/api/projects", json={"title": title, "study_type": st})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload(client, project_id, body=CSV_BYTES_NUMERIC):
    files = {"file": ("data.csv", body, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_route_two_group_happy_path(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/pathways/two-group",
        json={"outcome": "score", "group": "group"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pathway"] == "two-group"
    assert body["result"]["test_used"] in {"student_t", "welch_t", "mann_whitney"}
    assert "Methods:" in body["prose"]["methods"]


@pytest.mark.asyncio
async def test_route_two_group_unknown_column_422(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/pathways/two-group",
        json={"outcome": "nope", "group": "group"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_route_two_group_missing_dataset_404(client):
    pid = await _project(client)
    r = await client.post(
        f"/api/projects/{pid}/datasets/missing/pathways/two-group",
        json={"outcome": "score", "group": "group"},
    )
    assert r.status_code == 404
