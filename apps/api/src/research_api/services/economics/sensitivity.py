"""Phase 18 (MP18) — Sensitivity analyses (PSA / DSA / scenario).

The three flavours:

  * **PSA** (probabilistic): draw each parameter from its specified
    distribution, recompute the ICER + NMB per draw, summarise.
  * **DSA** (one-way deterministic): vary one parameter at a time
    between its low/high bounds, holding others at their base value.
    Output is the familiar tornado-chart shape.
  * **Scenario**: a list of named scenarios, each with explicit
    parameter overrides — useful for "best/worst case" pre-specifications.

The parameter shapes are deliberately simple so callers can build them
from a small JSON body. The "base_inputs" dict carries the same
parameters the main computation used, so DSA can vary one at a time
while holding the rest constant.

We rely on the standard ICER / NMB plumbing from ``icer.py``.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from .icer import compute_icer, compute_nmb


def _sample_one(
    spec: dict[str, Any], rng: np.random.Generator
) -> float:
    """Draw one value from a distribution spec.

    Supported ``dist`` values:
      - ``"normal"``: mean, sd
      - ``"lognormal"``: meanlog, sdlog
      - ``"beta"``: alpha, beta
      - ``"gamma"``: shape, scale
      - ``"uniform"``: low, high
      - ``"fixed"``: value (degenerate point mass)
    """
    dist = spec.get("dist", "normal")
    if dist == "normal":
        return float(rng.normal(spec["mean"], spec["sd"]))
    if dist == "lognormal":
        return float(rng.lognormal(spec["meanlog"], spec["sdlog"]))
    if dist == "beta":
        return float(rng.beta(spec["alpha"], spec["beta"]))
    if dist == "gamma":
        return float(rng.gamma(spec["shape"], spec["scale"]))
    if dist == "uniform":
        return float(rng.uniform(spec["low"], spec["high"]))
    if dist == "fixed":
        return float(spec["value"])
    raise ValueError(f"unknown distribution {dist!r}")


def _compute_for_inputs(
    inputs: dict[str, float], *, wtp: float
) -> dict[str, Any]:
    dC = float(inputs["mean_cost_diff"])
    dQ = float(inputs["mean_qaly_diff"])
    icer = compute_icer(dC, dQ)
    nmb = compute_nmb(dC, dQ, wtp_threshold=wtp)
    return {
        "mean_cost_diff": dC,
        "mean_qaly_diff": dQ,
        "icer": icer["icer"],
        "dominance_status": icer["dominance_status"],
        "nmb": nmb,
    }


def psa(
    base_inputs: dict[str, float],
    parameter_distributions: dict[str, dict[str, Any]],
    *,
    n_psa: int = 1000,
    seed: int = 42,
    wtp: float = 30_000.0,
) -> dict[str, Any]:
    """Probabilistic sensitivity analysis.

    Each parameter in ``parameter_distributions`` is sampled per draw and
    overrides the corresponding key in ``base_inputs``. Required keys in
    base_inputs: ``mean_cost_diff``, ``mean_qaly_diff``.

    Returns ``{results: list[dict], summary: dict}`` where ``summary``
    holds the mean / 2.5% / 97.5% across draws for ICER and NMB, plus the
    fraction-cost-effective at the supplied wtp.
    """
    rng = np.random.default_rng(seed)
    results: list[dict[str, Any]] = []
    for _ in range(int(n_psa)):
        inputs = dict(base_inputs)
        for name, spec in parameter_distributions.items():
            inputs[name] = _sample_one(spec, rng)
        results.append(_compute_for_inputs(inputs, wtp=wtp))

    nmbs = np.asarray([r["nmb"] for r in results], dtype=float)
    icers = np.asarray(
        [r["icer"] for r in results if r["icer"] is not None], dtype=float
    )
    fraction_ce = float((nmbs > 0).mean()) if nmbs.size else 0.0
    summary: dict[str, Any] = {
        "n_psa": len(results),
        "wtp": wtp,
        "fraction_cost_effective": fraction_ce,
        "nmb_mean": float(nmbs.mean()) if nmbs.size else None,
        "nmb_ci_low": float(np.percentile(nmbs, 2.5)) if nmbs.size else None,
        "nmb_ci_high": float(np.percentile(nmbs, 97.5)) if nmbs.size else None,
        "icer_mean": float(icers.mean()) if icers.size else None,
        "icer_ci_low": float(np.percentile(icers, 2.5)) if icers.size else None,
        "icer_ci_high": float(np.percentile(icers, 97.5)) if icers.size else None,
    }
    return {"type": "psa", "results": results, "summary": summary}


def dsa(
    base_inputs: dict[str, float],
    parameter_ranges: dict[str, dict[str, float]],
    *,
    wtp: float = 30_000.0,
) -> dict[str, Any]:
    """One-way deterministic sensitivity analysis.

    For each parameter, vary it to its low and high while holding the
    others at base. Returns the per-parameter ICER / NMB at each
    extreme — directly consumable by ``charts.render_tornado``.
    """
    results: list[dict[str, Any]] = []
    base_icer = compute_icer(
        base_inputs["mean_cost_diff"], base_inputs["mean_qaly_diff"]
    )
    base_nmb = compute_nmb(
        base_inputs["mean_cost_diff"],
        base_inputs["mean_qaly_diff"],
        wtp_threshold=wtp,
    )
    for name, bounds in parameter_ranges.items():
        low = float(bounds["low"])
        high = float(bounds["high"])
        low_inputs = {**base_inputs, name: low}
        high_inputs = {**base_inputs, name: high}
        lo = _compute_for_inputs(low_inputs, wtp=wtp)
        hi = _compute_for_inputs(high_inputs, wtp=wtp)
        results.append(
            {
                "param": name,
                "low_value": low,
                "high_value": high,
                "low_icer": lo["icer"],
                "high_icer": hi["icer"],
                "low_nmb": lo["nmb"],
                "high_nmb": hi["nmb"],
            }
        )
    return {
        "type": "dsa",
        "results": results,
        "summary": {
            "base_icer": base_icer["icer"],
            "base_dominance_status": base_icer["dominance_status"],
            "base_nmb": base_nmb,
            "wtp": wtp,
        },
    }


def scenario(
    base_inputs: dict[str, float],
    scenarios: Iterable[dict[str, Any]],
    *,
    wtp: float = 30_000.0,
) -> dict[str, Any]:
    """Named-scenario sensitivity.

    Each scenario is ``{name, overrides: {param: value}}``. Result mirrors
    DSA shape: per-scenario ICER + NMB + dominance status.
    """
    results: list[dict[str, Any]] = []
    for sc in scenarios:
        name = sc.get("name") or "(unnamed)"
        overrides = sc.get("overrides") or {}
        inputs = {**base_inputs, **{k: float(v) for k, v in overrides.items()}}
        comp = _compute_for_inputs(inputs, wtp=wtp)
        results.append({"name": name, "overrides": overrides, **comp})
    return {"type": "scenario", "results": results, "summary": {"wtp": wtp}}


__all__ = ["psa", "dsa", "scenario"]
