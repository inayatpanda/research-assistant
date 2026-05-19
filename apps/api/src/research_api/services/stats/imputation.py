"""Phase 17 (MP17) — Multiple-imputation wrappers.

``run_mice`` produces ``m`` complete datasets via statsmodels' MICE
implementation. ``pool_with_rubin`` combines per-imputation point estimates +
standard errors into a single pooled estimate using Rubin's rules:

  - Q-bar = mean of point estimates across imputations
  - U-bar = mean of within-imputation variances
  - B    = between-imputation variance = sum((Q_i - Q-bar)^2) / (m - 1)
  - T    = U-bar + (1 + 1/m) * B  ← TOTAL pooled variance
  - df   = (m - 1) * (1 + U-bar / ((1 + 1/m) * B))^2  ← Barnard-Rubin df (small-sample)

We pool the mean of each target numeric column as a default summary so the
endpoint can report "after imputation, the pooled mean of `column_x` is X".

Simple fallbacks (mean / median / LOCF / KNN) are also provided so the route
can offer the user a non-stochastic baseline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PooledSummary:
    """Per-column Rubin-pooled summary."""

    column: str
    q_bar: float
    u_bar: float
    between_var: float
    total_var: float
    se: float
    df: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "q_bar": float(self.q_bar),
            "u_bar": float(self.u_bar),
            "between_var": float(self.between_var),
            "total_var": float(self.total_var),
            "se": float(self.se),
            "df": float(self.df),
        }


def _check_targets(df: pd.DataFrame, target_cols: list[str]) -> None:
    if not target_cols:
        raise ValueError("target_cols must be non-empty")
    missing = [c for c in target_cols if c not in df.columns]
    if missing:
        raise ValueError(f"target_cols not in dataframe: {missing}")


def run_mice(
    df: pd.DataFrame,
    *,
    target_cols: list[str],
    n_imputations: int = 5,
    seed: int = 42,
) -> list[pd.DataFrame]:
    """Run statsmodels' MICE imputer. Returns ``n_imputations`` complete dfs.

    Only numeric target columns are supported; non-numeric ones are dropped
    from the MICE working frame and copied through unchanged.
    """
    from statsmodels.imputation.mice import MICEData

    _check_targets(df, target_cols)
    if n_imputations < 1 or n_imputations > 20:
        raise ValueError("n_imputations must be in [1, 20]")

    numeric_targets = [
        c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])
    ]
    if not numeric_targets:
        raise ValueError("MICE requires at least one numeric target column")

    # MICEData fits per-column regression chains and so cannot handle
    # non-numeric auxiliary columns (it tries to .sum() them and concatenates
    # strings). Restrict the working frame to numeric columns, run MICE, then
    # paste the non-numeric columns back unchanged.
    np.random.seed(seed)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not any(c in numeric_targets for c in numeric_cols):
        raise ValueError("MICE requires the target columns to be numeric")
    other_cols = [c for c in df.columns if c not in numeric_cols]
    working = df[numeric_cols].copy(deep=True)
    mice = MICEData(working)
    imputed: list[pd.DataFrame] = []
    for _ in range(n_imputations):
        mice.update_all()
        merged = mice.data.copy(deep=True)
        if other_cols:
            for c in other_cols:
                merged[c] = df[c].to_numpy()
        # Preserve the original column order.
        merged = merged[df.columns.tolist()]
        imputed.append(merged)
    return imputed


def pool_with_rubin(
    imputed_frames: list[pd.DataFrame],
    *,
    target_cols: list[str],
) -> list[PooledSummary]:
    """Pool per-column mean estimates across imputations via Rubin's rules.

    The within-imputation variance ``U_i`` for a mean estimate is
    ``var(x) / n`` (the standard error squared).
    """
    if not imputed_frames:
        raise ValueError("imputed_frames must contain at least one frame")
    m = len(imputed_frames)
    summaries: list[PooledSummary] = []
    for col in target_cols:
        # Skip non-numeric columns (Rubin's rules apply to numeric estimates).
        first = imputed_frames[0][col]
        if not pd.api.types.is_numeric_dtype(first):
            continue
        qs = np.asarray(
            [float(np.mean(frame[col].to_numpy(dtype=float))) for frame in imputed_frames]
        )
        us = np.asarray(
            [
                float(np.var(frame[col].to_numpy(dtype=float), ddof=1)) / len(frame)
                for frame in imputed_frames
            ]
        )
        q_bar = float(np.mean(qs))
        u_bar = float(np.mean(us))
        if m > 1:
            between = float(np.sum((qs - q_bar) ** 2) / (m - 1))
        else:
            between = 0.0
        total = u_bar + (1.0 + 1.0 / m) * between
        se = math.sqrt(total) if total > 0 else 0.0
        # Barnard-Rubin small-sample df.
        if between > 0:
            df_pool = (m - 1) * (1.0 + (u_bar / ((1.0 + 1.0 / m) * between))) ** 2
        else:
            df_pool = float("inf")
        summaries.append(
            PooledSummary(
                column=col,
                q_bar=q_bar,
                u_bar=u_bar,
                between_var=between,
                total_var=total,
                se=se,
                df=df_pool,
            )
        )
    return summaries


def impute_simple(
    df: pd.DataFrame,
    *,
    method: str,
    target_cols: list[str],
) -> pd.DataFrame:
    """Single-imputation fallbacks. ``method`` ∈ {mean, median, last_observation, knn}.

    These return ONE complete df (no multiple-imputation pooling). For
    ``knn`` we use sklearn's ``KNNImputer`` over the numeric target columns.
    """
    _check_targets(df, target_cols)
    out = df.copy(deep=True)
    if method == "mean":
        for c in target_cols:
            if pd.api.types.is_numeric_dtype(out[c]):
                out[c] = out[c].fillna(out[c].mean())
        return out
    if method == "median":
        for c in target_cols:
            if pd.api.types.is_numeric_dtype(out[c]):
                out[c] = out[c].fillna(out[c].median())
        return out
    if method == "last_observation":
        for c in target_cols:
            out[c] = out[c].ffill().bfill()
        return out
    if method == "knn":
        from sklearn.impute import KNNImputer

        numeric_cols = [
            c for c in target_cols if pd.api.types.is_numeric_dtype(out[c])
        ]
        if not numeric_cols:
            return out
        imputer = KNNImputer(n_neighbors=min(5, max(1, len(out) - 1)))
        out[numeric_cols] = imputer.fit_transform(out[numeric_cols])
        return out
    raise ValueError(f"unknown imputation method: {method!r}")


__all__ = [
    "PooledSummary",
    "run_mice",
    "pool_with_rubin",
    "impute_simple",
]
