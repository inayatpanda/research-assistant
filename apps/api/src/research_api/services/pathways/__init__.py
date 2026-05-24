"""F3 Research Pathways — guided statistical workflow orchestrators.

Each pathway module exposes a single ``run(df, ...) -> dict`` function
that picks the right test automatically based on column types + data
shape, executes it via the existing ``services.stats`` primitives, and
returns a JSON-serialisable result blob ready for the prose templates
in ``prose.py``.

Five pathways:

  * ``two_group``   — A vs B (numeric or categorical outcome)
  * ``risk_factors`` — univariable + multivariable regression
  * ``survival``     — Kaplan-Meier + optional Cox
  * ``diagnostic``   — ROC / sens / spec / PPV / NPV
  * ``agreement``    — ICC / Bland-Altman / Cohen's kappa
"""
from __future__ import annotations

from . import agreement, diagnostic, prose, risk_factors, survival, two_group

__all__ = [
    "agreement",
    "diagnostic",
    "prose",
    "risk_factors",
    "survival",
    "two_group",
]
