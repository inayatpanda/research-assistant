"""Kaplan-Meier survival curve renderer — Phase 8.5 Task 6."""
from __future__ import annotations

from typing import Any

import pandas as pd

from ._base import fig_context, fig_to_data_uri


def render_km_curve(
    *,
    df: pd.DataFrame,
    duration: str,
    event: str,
    groups: str | None = None,
) -> dict[str, Any]:
    """Kaplan-Meier survival curves with optional grouping."""
    from lifelines import KaplanMeierFitter
    from lifelines.plotting import add_at_risk_counts

    if duration not in df.columns or event not in df.columns:
        raise ValueError(
            f"KM curve requires {duration!r} and {event!r} columns"
        )
    cols = [duration, event] + ([groups] if groups else [])
    sub = df[cols].dropna()
    if sub.empty:
        raise ValueError("KM curve: dataframe is empty after NaN drop")

    with fig_context(figsize=(7.0, 5.0)) as fig:
        ax = fig.add_subplot(1, 1, 1)
        fitters: list[KaplanMeierFitter] = []

        if groups is None:
            kmf = KaplanMeierFitter()
            kmf.fit(sub[duration], event_observed=sub[event], label="overall")
            kmf.plot_survival_function(ax=ax, ci_show=True)
            fitters.append(kmf)
        else:
            levels = sorted(sub[groups].dropna().unique().tolist(), key=str)
            for lv in levels:
                lv_sub = sub[sub[groups] == lv]
                if lv_sub.empty:
                    continue
                kmf = KaplanMeierFitter()
                kmf.fit(
                    lv_sub[duration],
                    event_observed=lv_sub[event],
                    label=str(lv),
                )
                kmf.plot_survival_function(ax=ax, ci_show=True)
                fitters.append(kmf)

        ax.set_xlabel(duration)
        ax.set_ylabel("Survival probability")
        ax.set_ylim(-0.02, 1.05)
        ax.set_title("Kaplan-Meier survival")

        # At-risk counts band beneath the main axes.
        try:
            add_at_risk_counts(*fitters, ax=ax, fig=fig)
        except Exception:
            # add_at_risk_counts can be fragile on edge cases; skip silently —
            # the main KM panel is the important deliverable.
            pass

        return fig_to_data_uri(fig)
