"""Phase 17 (MP17) — Inter-rater reliability statistics.

Pure functions:

  * ``fleiss_kappa(matrix)``: statsmodels' Fleiss kappa for n subjects ×
    k categories where each cell is the count of raters assigning that
    category. Returns ``{kappa, z, p}``.
  * ``krippendorff_alpha(ratings, level)``: Krippendorff's α implemented
    from the published formula. ``ratings`` is a 2-D ndarray (raters ×
    items) where missing values are ``np.nan``. Levels: ``nominal``,
    ``ordinal``, ``interval``.
  * ``weighted_kappa(rater1, rater2, weights)``: sklearn's Cohen-kappa
    with ``linear`` or ``quadratic`` weights, plus bootstrap CI.
"""
from __future__ import annotations

import math
from itertools import combinations
from typing import Any, Literal

import numpy as np
from scipy import stats


def fleiss_kappa(matrix: np.ndarray | list[list[int]]) -> dict[str, Any]:
    """Fleiss kappa with significance test.

    ``matrix`` is a 2-D array of shape (n_subjects, n_categories) where each
    cell carries the count of raters that assigned that category to that
    subject. All rows must sum to the same total (n_raters).
    """
    from statsmodels.stats.inter_rater import fleiss_kappa as _sm_fleiss

    arr = np.asarray(matrix, dtype=float)
    if arr.ndim != 2:
        raise ValueError("matrix must be 2-D (n_subjects x n_categories)")
    n_subj, n_cat = arr.shape
    if n_subj < 2 or n_cat < 2:
        raise ValueError("need >= 2 subjects and >= 2 categories")
    row_sums = arr.sum(axis=1)
    if not np.allclose(row_sums, row_sums[0]):
        raise ValueError("each subject must have the same number of raters")
    n_raters = float(row_sums[0])
    if n_raters < 2:
        raise ValueError("need >= 2 raters")
    # statsmodels' Fleiss formula divides by (1 - p_e). When every cell maps
    # to the same category, p_e == 1 and the division yields NaN. Treat that
    # degenerate case as perfect agreement by convention.
    proportions = arr.sum(axis=0) / (n_subj * n_raters)
    pe_check = float(np.sum(proportions**2))
    if pe_check >= 1.0:
        kappa = 1.0
    else:
        kappa = float(_sm_fleiss(arr, method="fleiss"))
    # Approximate large-sample SE (Fleiss et al. 1979) — used for a z test.
    p_j = arr.sum(axis=0) / (n_subj * n_raters)
    pe = float(np.sum(p_j**2))
    if pe >= 1 or n_raters <= 1 or pe <= 0:
        z, p = float("nan"), float("nan")
    else:
        denom = math.sqrt(2.0 / (n_subj * n_raters * (n_raters - 1))) * math.sqrt(
            pe - (2.0 * n_raters - 3.0) * pe**2 + 2.0 * (n_raters - 2.0) * np.sum(p_j**3)
        )
        if denom <= 0:
            z, p = float("nan"), float("nan")
        else:
            z = kappa * (1.0 - pe) / denom
            p = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    return {
        "kappa": kappa,
        "z": float(z) if not (isinstance(z, float) and math.isnan(z)) else float("nan"),
        "p": float(p) if not (isinstance(p, float) and math.isnan(p)) else float("nan"),
        "n_subjects": int(n_subj),
        "n_raters": int(n_raters),
        "n_categories": int(n_cat),
    }


Level = Literal["nominal", "ordinal", "interval"]


def _delta(a: float, b: float, *, level: Level, values: np.ndarray) -> float:
    """Pairwise distance metric for Krippendorff's α.

    For ``interval`` the squared difference. For ``ordinal`` we map each
    unique value to its rank position then square the rank difference. For
    ``nominal`` 0/1.
    """
    if math.isnan(a) or math.isnan(b):
        return float("nan")
    if level == "nominal":
        return 0.0 if a == b else 1.0
    if level == "interval":
        return float((a - b) ** 2)
    if level == "ordinal":
        # Build ordered value list ONCE; mapping a value to its index.
        unique = np.sort(np.unique(values[~np.isnan(values)]))
        rank_a = int(np.searchsorted(unique, a))
        rank_b = int(np.searchsorted(unique, b))
        return float((rank_a - rank_b) ** 2)
    raise ValueError(f"unknown level: {level!r}")


def krippendorff_alpha(
    ratings: np.ndarray | list[list[float]],
    *,
    level: Level = "nominal",
) -> dict[str, Any]:
    """Krippendorff's α. ``ratings`` is shape (n_raters, n_items); NaN = miss.

    Implements the published "coincidence matrix" formula:

      α = 1 - (D_o / D_e)

    where ``D_o`` is the observed disagreement and ``D_e`` is the expected
    disagreement under independence.
    """
    arr = np.asarray(ratings, dtype=float)
    if arr.ndim != 2:
        raise ValueError("ratings must be 2-D (raters x items)")
    n_raters, n_items = arr.shape
    if n_raters < 2:
        raise ValueError("need >= 2 raters")
    if n_items < 1:
        raise ValueError("need >= 1 item")

    # Coincidence sum: pairable observation count per item.
    flat = arr.flatten()
    flat_valid = flat[~np.isnan(flat)]
    if flat_valid.size < 2:
        raise ValueError("need >= 2 non-missing observations total")

    # Observed disagreement.
    do_num = 0.0
    n_pairable_total = 0.0
    all_values_for_ordinal = arr  # used by _delta for ordinal level
    for item_idx in range(n_items):
        col = arr[:, item_idx]
        obs = col[~np.isnan(col)]
        m = obs.size
        if m < 2:
            continue
        # Each unordered pair contributes its delta scaled by 1/(m-1).
        # Equivalent to sum over ordered pairs / (m-1) with factor 2 cancelling.
        pair_sum = 0.0
        for i, j in combinations(range(m), 2):
            pair_sum += 2.0 * _delta(
                float(obs[i]), float(obs[j]), level=level, values=all_values_for_ordinal
            )
        do_num += pair_sum / (m - 1)
        n_pairable_total += m
    if n_pairable_total <= 0:
        raise ValueError("no pairable observations")
    d_o = do_num / n_pairable_total

    # Expected disagreement under independence.
    de_num = 0.0
    n_valid = flat_valid.size
    for i, j in combinations(range(n_valid), 2):
        de_num += 2.0 * _delta(
            float(flat_valid[i]), float(flat_valid[j]),
            level=level, values=all_values_for_ordinal,
        )
    d_e = de_num / (n_valid * (n_valid - 1))

    if d_e == 0:
        # All values are identical → perfect agreement by convention.
        alpha = 1.0
    else:
        alpha = 1.0 - (d_o / d_e)
    return {
        "alpha": float(alpha),
        "level": level,
        "n_raters": int(n_raters),
        "n_items": int(n_items),
        "n_pairable": int(n_pairable_total),
        "d_o": float(d_o),
        "d_e": float(d_e),
    }


def weighted_kappa(
    rater1: np.ndarray | list[Any],
    rater2: np.ndarray | list[Any],
    *,
    weights: Literal["linear", "quadratic"] = "linear",
    n_bootstrap: int = 0,
    seed: int = 0,
) -> dict[str, Any]:
    """Weighted Cohen's kappa via sklearn. Optional bootstrap CI."""
    from sklearn.metrics import cohen_kappa_score

    r1 = np.asarray(rater1)
    r2 = np.asarray(rater2)
    if r1.shape != r2.shape:
        raise ValueError("rater1 and rater2 must have the same shape")
    n = int(r1.shape[0])
    if n < 2:
        raise ValueError("need >= 2 paired ratings")
    if weights not in ("linear", "quadratic"):
        raise ValueError("weights must be 'linear' or 'quadratic'")
    kappa = float(cohen_kappa_score(r1, r2, weights=weights))

    ci_low: float | None = None
    ci_high: float | None = None
    se: float | None = None
    if n_bootstrap and n_bootstrap > 0:
        rng = np.random.default_rng(seed)
        boots: list[float] = []
        for _ in range(int(n_bootstrap)):
            idx = rng.integers(0, n, n)
            try:
                k_b = float(cohen_kappa_score(r1[idx], r2[idx], weights=weights))
                if not math.isnan(k_b):
                    boots.append(k_b)
            except ValueError:
                continue
        if boots:
            arr = np.asarray(boots)
            ci_low = float(np.quantile(arr, 0.025))
            ci_high = float(np.quantile(arr, 0.975))
            se = float(np.std(arr, ddof=1))
    return {
        "kappa": kappa,
        "weights": weights,
        "n": n,
        "se": se,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


__all__ = ["fleiss_kappa", "krippendorff_alpha", "weighted_kappa"]
