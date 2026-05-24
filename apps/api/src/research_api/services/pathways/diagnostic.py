"""F3 Pathway 4 — Diagnostic accuracy.

Continuous test:
  * ROC curve (full coords)
  * AUC + 95% CI (DeLong-style standard error from Hanley/McNeil)
  * Optimal threshold by Youden index
  * Sens/spec/PPV/NPV + LR+/LR- at the optimal threshold

Binary test:
  * 2x2 table, sens/spec/PPV/NPV + Wilson 95% CIs
  * LR+/LR-

Pre-test probability is sliced via Bayes when requested.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as _s


def _wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    z = float(_s.norm.ppf(1 - alpha / 2))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def _is_numeric(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    coerced = pd.to_numeric(series, errors="coerce")
    return coerced.notna().sum() / max(len(series), 1) > 0.8


def _is_binary(series: pd.Series) -> bool:
    vals = pd.to_numeric(series, errors="coerce").dropna().unique().tolist()
    return set(vals).issubset({0, 1, 0.0, 1.0}) and len(vals) >= 1


def _roc_curve(scores: np.ndarray, labels: np.ndarray) -> dict[str, list[float]]:
    """Return ROC curve coords sorted by descending score."""
    order = np.argsort(-scores)
    s = scores[order]
    y = labels[order]
    pos = float(y.sum())
    neg = float(len(y) - pos)
    if pos == 0 or neg == 0:
        return {"fpr": [0.0, 1.0], "tpr": [0.0, 1.0], "thresholds": [float(s.max()), float(s.min())]}
    tps = np.cumsum(y)
    fps = np.cumsum(1 - y)
    tpr = (tps / pos).tolist()
    fpr = (fps / neg).tolist()
    thr = s.tolist()
    # Prepend (0, 0).
    return {
        "fpr": [0.0] + [float(x) for x in fpr],
        "tpr": [0.0] + [float(x) for x in tpr],
        "thresholds": [float(s.max()) + 1.0] + [float(x) for x in thr],
    }


def _auc_from_roc(roc: dict[str, list[float]]) -> float:
    trap = getattr(np, "trapezoid", None) or np.trapz
    return float(trap(roc["tpr"], roc["fpr"]))


def _hanley_se(auc: float, n_pos: int, n_neg: int) -> float:
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    q1 = auc / (2 - auc)
    q2 = 2 * auc * auc / (1 + auc)
    se = np.sqrt(
        (auc * (1 - auc) + (n_pos - 1) * (q1 - auc * auc) + (n_neg - 1) * (q2 - auc * auc))
        / (n_pos * n_neg)
    )
    return float(se)


def _metrics_for_2x2(tp: int, fp: int, fn: int, tn: int) -> dict[str, Any]:
    sens = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    spec = tn / (tn + fp) if (tn + fp) > 0 else float("nan")
    ppv = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    npv = tn / (tn + fn) if (tn + fn) > 0 else float("nan")
    lr_pos = sens / (1 - spec) if (1 - spec) > 0 else float("inf")
    lr_neg = (1 - sens) / spec if spec > 0 else float("inf")
    sens_ci = _wilson_ci(tp, tp + fn)
    spec_ci = _wilson_ci(tn, tn + fp)
    ppv_ci = _wilson_ci(tp, tp + fp)
    npv_ci = _wilson_ci(tn, tn + fn)
    return {
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "sensitivity": float(sens),
        "specificity": float(spec),
        "ppv": float(ppv),
        "npv": float(npv),
        "lr_pos": float(lr_pos) if np.isfinite(lr_pos) else None,
        "lr_neg": float(lr_neg) if np.isfinite(lr_neg) else None,
        "sensitivity_ci": list(sens_ci),
        "specificity_ci": list(spec_ci),
        "ppv_ci": list(ppv_ci),
        "npv_ci": list(npv_ci),
    }


def run(
    df: pd.DataFrame,
    *,
    test: str,
    reference: str,
    pre_test_probability: float | None = None,
) -> dict[str, Any]:
    if test not in df.columns:
        raise ValueError(f"test column '{test}' not in dataset")
    if reference not in df.columns:
        raise ValueError(f"reference column '{reference}' not in dataset")
    if test == reference:
        raise ValueError("test and reference columns must differ")

    clean = df[[test, reference]].dropna().copy()
    if clean.empty:
        raise ValueError("no rows with non-missing test/reference values")
    if not _is_binary(clean[reference]):
        raise ValueError(
            f"reference standard '{reference}' must be binary (0/1)"
        )
    clean[reference] = pd.to_numeric(clean[reference], errors="coerce").astype(int)
    clean = clean.dropna(subset=[reference])
    labels = clean[reference].to_numpy(dtype=int)

    test_is_binary = _is_binary(clean[test])
    test_is_numeric_only = _is_numeric(clean[test]) and not test_is_binary

    out: dict[str, Any] = {
        "pathway": "diagnostic",
        "test": test,
        "reference": reference,
        "n": int(len(clean)),
        "n_positive": int(labels.sum()),
        "n_negative": int(len(labels) - labels.sum()),
    }

    if test_is_numeric_only:
        scores = pd.to_numeric(clean[test], errors="coerce").to_numpy(dtype=float)
        roc = _roc_curve(scores, labels)
        auc = _auc_from_roc(roc)
        se = _hanley_se(auc, int(labels.sum()), int(len(labels) - labels.sum()))
        auc_ci = (
            (max(0.0, auc - 1.96 * se), min(1.0, auc + 1.96 * se))
            if np.isfinite(se)
            else (float("nan"), float("nan"))
        )

        # Youden's J — find threshold maximising sens + spec - 1.
        best_j, best_thr, best_idx = -1.0, float("nan"), 0
        for i in range(len(roc["fpr"])):
            j = roc["tpr"][i] - roc["fpr"][i]
            if j > best_j:
                best_j = j
                best_thr = roc["thresholds"][i]
                best_idx = i

        # Reconstruct counts at the chosen threshold.
        pred = (scores >= best_thr).astype(int)
        tp = int(((pred == 1) & (labels == 1)).sum())
        fp = int(((pred == 1) & (labels == 0)).sum())
        fn = int(((pred == 0) & (labels == 1)).sum())
        tn = int(((pred == 0) & (labels == 0)).sum())
        metrics = _metrics_for_2x2(tp, fp, fn, tn)
        out.update(
            {
                "test_type": "continuous",
                "auc": float(auc),
                "auc_ci_low": float(auc_ci[0]),
                "auc_ci_high": float(auc_ci[1]),
                "roc": roc,
                "optimal_threshold": float(best_thr),
                "youden_j": float(best_j),
                "at_optimal": metrics,
            }
        )
    elif test_is_binary:
        pred = pd.to_numeric(clean[test], errors="coerce").astype(int).to_numpy()
        tp = int(((pred == 1) & (labels == 1)).sum())
        fp = int(((pred == 1) & (labels == 0)).sum())
        fn = int(((pred == 0) & (labels == 1)).sum())
        tn = int(((pred == 0) & (labels == 0)).sum())
        out.update(
            {
                "test_type": "binary",
                "metrics": _metrics_for_2x2(tp, fp, fn, tn),
            }
        )
    else:
        raise ValueError(
            f"test column '{test}' must be numeric (continuous) or binary (0/1)"
        )

    if pre_test_probability is not None:
        p_pre = float(pre_test_probability)
        if not 0.0 < p_pre < 1.0:
            raise ValueError("pre_test_probability must lie strictly between 0 and 1")
        metrics = out.get("at_optimal") or out.get("metrics") or {}
        lr_pos = metrics.get("lr_pos")
        lr_neg = metrics.get("lr_neg")
        odds_pre = p_pre / (1 - p_pre)
        post_pos = float("nan")
        post_neg = float("nan")
        if lr_pos is not None:
            post_odds = odds_pre * lr_pos
            post_pos = post_odds / (1 + post_odds)
        if lr_neg is not None:
            post_odds = odds_pre * lr_neg
            post_neg = post_odds / (1 + post_odds)
        out["bayes"] = {
            "pre_test_probability": p_pre,
            "post_test_prob_positive": float(post_pos) if np.isfinite(post_pos) else None,
            "post_test_prob_negative": float(post_neg) if np.isfinite(post_neg) else None,
        }
    return out
