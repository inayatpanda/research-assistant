"""Phase 13 (MP13) — GLM (and GEE) deviance-residual diagnostic."""
from __future__ import annotations

from typing import Any

import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from ._base import fig_context, fig_to_data_uri

_FAMILY_MAP = {
    "Poisson": sm.families.Poisson(),
    "Binomial": sm.families.Binomial(),
    "Gamma": sm.families.Gamma(link=sm.families.links.Log()),
}


def render_glm_deviance_residuals(
    *,
    df: pd.DataFrame,
    outcome: str,
    predictors: list[str],
    family: str,
) -> dict[str, Any]:
    if family not in _FAMILY_MAP:
        raise ValueError(f"unknown GLM family {family!r}")
    df = df.dropna(subset=[outcome, *predictors])
    formula = f"{outcome} ~ " + " + ".join(predictors)
    model = smf.glm(formula, data=df, family=_FAMILY_MAP[family]).fit()
    fitted = model.fittedvalues
    resid = model.resid_deviance

    with fig_context() as fig:
        ax = fig.gca()
        ax.scatter(fitted, resid, alpha=0.55, color="#4263eb", s=18)
        ax.axhline(0, color="#868e96", linestyle="--", linewidth=1)
        ax.set_xlabel("Fitted values")
        ax.set_ylabel("Deviance residuals")
        ax.set_title(f"{family} GLM — deviance residuals vs fitted")
        return fig_to_data_uri(fig)
