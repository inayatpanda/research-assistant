"""DEMO-FIX-A — Pydantic schemas for the standalone diagnostics panel."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DiagnosticTestKey = Literal[
    "shapiro_wilk",
    "anderson_darling",
    "kolmogorov_smirnov",
    "dagostino_pearson",
    "levene",
    "bartlett",
]


class DiagnosticRequest(BaseModel):
    """Body for ``POST .../diagnostics/run``.

    ``column_name`` is the numeric column to inspect.  ``group_column`` is
    required for Levene / Bartlett and ignored for the single-sample
    normality tests.
    """

    model_config = ConfigDict(extra="forbid")

    test_key: DiagnosticTestKey
    column_name: str = Field(min_length=1)
    group_column: str | None = None


class PlotRequest(BaseModel):
    """Body for the Q-Q / histogram PNG endpoints."""

    model_config = ConfigDict(extra="forbid")

    column_name: str = Field(min_length=1)
    title: str | None = None


class DiagnosticResult(BaseModel):
    """Generic shape for the JSON returned by ``/diagnostics/run``.

    The shape mirrors what the underlying ``services.stats.diagnostics_standalone``
    functions return.  ``critical_values`` and ``significance_levels`` are
    populated only by Anderson-Darling.
    """

    test_key: DiagnosticTestKey
    statistic: float
    p: float | None = None
    n: int
    interpretation: str
    ok: bool
    # Anderson-Darling extras.
    critical_values: dict[str, float] | None = None
    significance_levels: list[float] | None = None
    # Levene / Bartlett extras.
    k: int | None = None
    center: str | None = None
    # Optional escape hatch for additional fields a future variant might
    # surface without forcing a schema bump.
    extras: dict[str, Any] | None = None
