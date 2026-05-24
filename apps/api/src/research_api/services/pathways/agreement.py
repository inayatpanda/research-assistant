"""F3 Pathway 5 — Agreement / reliability between two raters.

Numeric (continuous):
  * ICC (two-way mixed, absolute agreement) via the variance-component
    formula on the long-format dataframe.
  * Bland-Altman: mean difference (bias) + 95% limits of agreement.

Categorical:
  * Cohen's unweighted kappa (binary/nominal).
  * Weighted kappa (linear weights) when ordinal-like ordering is given
    or detected from sorted unique values.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as _s


def _is_numeric(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    coerced = pd.to_numeric(series, errors="coerce")
    return coerced.notna().sum() / max(len(series), 1) > 0.8


def _icc_a1(rater_a: np.ndarray, rater_b: np.ndarray) -> dict[str, float]:
    """ICC(A,1) — two-way mixed, single rater, absolute agreement.

    Follows McGraw & Wong (1996) formulae:
        ICC(A,1) = (MS_R - MS_E) / (MS_R + (k-1) MS_E
                                    + k/n * (MS_C - MS_E))
    with k = 2 raters, n = n subjects.
    """
    n = len(rater_a)
    if n < 2:
        return {"icc": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"),
                "f": float("nan"), "p_value": float("nan"), "n": n}
    k = 2
    mat = np.column_stack([rater_a, rater_b])
    grand_mean = mat.mean()
    row_means = mat.mean(axis=1)
    col_means = mat.mean(axis=0)
    # Sums of squares.
    ss_total = float(((mat - grand_mean) ** 2).sum())
    ss_rows = float(k * ((row_means - grand_mean) ** 2).sum())
    ss_cols = float(n * ((col_means - grand_mean) ** 2).sum())
    ss_err = ss_total - ss_rows - ss_cols
    # Mean squares.
    ms_r = ss_rows / (n - 1)
    ms_c = ss_cols / (k - 1)
    ms_e = ss_err / ((n - 1) * (k - 1)) if (n - 1) * (k - 1) > 0 else float("nan")
    # Perfect agreement collapses MS_E to ~0 → ICC = 1 by definition.
    if not np.isfinite(ms_e):
        icc = float("nan")
    elif ms_e <= 1e-12 and ms_r > 0:
        icc = 1.0
    elif ms_r <= 0:
        icc = 0.0
    else:
        icc = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e + (k / n) * (ms_c - ms_e))
    # F-statistic + 95% CI from McGraw & Wong.
    f_val = ms_r / ms_e if ms_e > 0 else float("nan")
    p_val = float("nan")
    ci_low, ci_high = float("nan"), float("nan")
    if np.isfinite(f_val):
        df1 = n - 1
        df2 = (n - 1) * (k - 1)
        p_val = float(1.0 - _s.f.cdf(f_val, df1, df2))
        # Approximate CI for ICC(A,1).
        try:
            fl = float(_s.f.ppf(0.975, df1, df2))
            fu = float(_s.f.ppf(0.025, df1, df2))
            ci_low = (f_val / fl - 1) / (f_val / fl + (k - 1) + (k / n) * (ms_c / ms_e - 1)) if ms_e > 0 else float("nan")
            ci_high = (f_val / fu - 1) / (f_val / fu + (k - 1) + (k / n) * (ms_c / ms_e - 1)) if ms_e > 0 else float("nan")
        except Exception:
            pass
    return {
        "icc": float(icc) if np.isfinite(icc) else float("nan"),
        "ci_low": float(ci_low) if np.isfinite(ci_low) else float("nan"),
        "ci_high": float(ci_high) if np.isfinite(ci_high) else float("nan"),
        "f": float(f_val) if np.isfinite(f_val) else float("nan"),
        "p_value": p_val,
        "n": int(n),
    }


def _bland_altman(a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    diffs = a - b
    bias = float(diffs.mean())
    sd_diff = float(diffs.std(ddof=1)) if len(diffs) > 1 else float("nan")
    loa_low = bias - 1.96 * sd_diff
    loa_high = bias + 1.96 * sd_diff
    means = ((a + b) / 2.0).tolist()
    return {
        "bias": bias,
        "sd_diff": sd_diff if np.isfinite(sd_diff) else None,
        "loa_low": float(loa_low) if np.isfinite(loa_low) else None,
        "loa_high": float(loa_high) if np.isfinite(loa_high) else None,
        "points": [
            {"mean": float(m), "diff": float(d)}
            for m, d in zip(means, diffs.tolist())
        ],
    }


def _kappa(a: list[Any], b: list[Any], weighted: bool = False) -> dict[str, Any]:
    classes = sorted(set(a) | set(b), key=str)
    k = len(classes)
    n = len(a)
    if k < 2 or n < 2:
        return {"kappa": float("nan"), "n": n, "po": float("nan"), "pe": float("nan")}
    idx = {c: i for i, c in enumerate(classes)}
    O = np.zeros((k, k))
    for x, y in zip(a, b):
        O[idx[x], idx[y]] += 1
    O = O / n
    row_marg = O.sum(axis=1)
    col_marg = O.sum(axis=0)
    if weighted:
        # Linear weights: w_ij = 1 - |i - j| / (k - 1).
        W = np.array(
            [
                [1.0 - abs(i - j) / (k - 1) for j in range(k)]
                for i in range(k)
            ]
        )
        po = float((W * O).sum())
        pe = float((W * np.outer(row_marg, col_marg)).sum())
    else:
        po = float(np.trace(O))
        pe = float((row_marg * col_marg).sum())
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else float("nan")
    # SE for unweighted (Cohen 1960 approx).
    se = float(np.sqrt(po * (1 - po) / (n * (1 - pe) ** 2))) if (1 - pe) > 0 else float("nan")
    z = kappa / se if np.isfinite(se) and se > 0 else float("nan")
    p_val = float(2 * (1 - _s.norm.cdf(abs(z)))) if np.isfinite(z) else float("nan")
    ci_low = float(kappa - 1.96 * se) if np.isfinite(se) else float("nan")
    ci_high = float(kappa + 1.96 * se) if np.isfinite(se) else float("nan")
    return {
        "kappa": float(kappa) if np.isfinite(kappa) else float("nan"),
        "weighted": bool(weighted),
        "po": po,
        "pe": pe,
        "se": se if np.isfinite(se) else None,
        "ci_low": ci_low if np.isfinite(ci_low) else None,
        "ci_high": ci_high if np.isfinite(ci_high) else None,
        "p_value": p_val if np.isfinite(p_val) else None,
        "n": n,
        "classes": [str(c) for c in classes],
    }


def run(
    df: pd.DataFrame,
    *,
    rater_a: str,
    rater_b: str,
    ordinal: bool | None = None,
) -> dict[str, Any]:
    if rater_a not in df.columns:
        raise ValueError(f"rater_a column '{rater_a}' not in dataset")
    if rater_b not in df.columns:
        raise ValueError(f"rater_b column '{rater_b}' not in dataset")
    if rater_a == rater_b:
        raise ValueError("rater_a and rater_b must differ")

    clean = df[[rater_a, rater_b]].dropna().copy()
    if len(clean) < 2:
        raise ValueError("need at least 2 paired observations")

    is_numeric = _is_numeric(clean[rater_a]) and _is_numeric(clean[rater_b])
    out: dict[str, Any] = {
        "pathway": "agreement",
        "rater_a": rater_a,
        "rater_b": rater_b,
        "n_pairs": int(len(clean)),
    }
    if is_numeric:
        a = pd.to_numeric(clean[rater_a], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(clean[rater_b], errors="coerce").to_numpy(dtype=float)
        out["data_type"] = "continuous"
        out["icc"] = _icc_a1(a, b)
        out["bland_altman"] = _bland_altman(a, b)
    else:
        a = clean[rater_a].astype(str).tolist()
        b = clean[rater_b].astype(str).tolist()
        weighted_flag = bool(ordinal) if ordinal is not None else (
            len(set(a) | set(b)) >= 3
        )
        out["data_type"] = "categorical"
        out["kappa"] = _kappa(a, b, weighted=False)
        if weighted_flag:
            out["weighted_kappa"] = _kappa(a, b, weighted=True)
    return out
