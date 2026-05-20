"""Phase 13.5 (MP13.5) — Analysis plan runner.

Walks a plan's step list against a dataset, applies each step via the relevant
service, and captures the per-step output. A single failed step does NOT abort
the run — the run continues, the step is stamped status="failed" with the
exception message, and the overall run's roll-up status becomes "partial". An
unexpected exception escaping the runner itself stamps the entire run "failed".
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .plot_renderer import PlotRenderError, render_plot
from .runner import run as runner_run
from .transform import TransformError, apply_op

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlanRunOutcome:
    """In-memory roll-up of a single plan-run before persistence."""

    status: str  # "ok" | "partial" | "failed"
    result_blob: dict[str, Any]
    error: str | None


def run_plan(
    *,
    steps: list[dict[str, Any]],
    df: pd.DataFrame,
    display_labels: dict[str, str] | None = None,
) -> PlanRunOutcome:
    """Execute each step against ``df`` (or an evolving copy for transforms).

    Returns a PlanRunOutcome describing the whole run. Pure & sync — the
    route layer wraps this and persists the outcome via the repository.

    Behaviour
    ---------
    - ``transform`` steps mutate the "live" DataFrame for subsequent steps.
    - ``test`` and ``plot`` steps see the latest live DataFrame but their
      output does not feed the next step.
    - Any single step's error is caught and stamped on its output; the run
      continues with the remaining steps. If at least one step fails, the
      run's roll-up ``status`` is ``partial``; if none fail, ``ok``.
    """
    if not isinstance(steps, list):
        return PlanRunOutcome(
            status="failed",
            result_blob={"steps": []},
            error="steps must be a list",
        )

    live = df
    out_steps: list[dict[str, Any]] = []
    any_failed = False

    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            out_steps.append({
                "step_index": idx,
                "type": "unknown",
                "status": "failed",
                "output": {},
                "error": "step must be an object",
            })
            any_failed = True
            continue
        step_type = step.get("type")
        args = step.get("args") or {}
        try:
            if step_type == "transform":
                op_type = args.get("op_type")
                op_args = args.get("op_args") or {}
                if not isinstance(op_type, str):
                    raise TransformError("transform step missing op_type")
                live = apply_op(live, op_type, op_args)
                out_steps.append({
                    "step_index": idx,
                    "type": "transform",
                    "status": "ok",
                    "output": {
                        "op_type": op_type,
                        "n_rows_after": int(len(live)),
                        "n_cols_after": int(len(live.columns)),
                    },
                    "error": None,
                })
            elif step_type == "test":
                test_key = args.get("test_key")
                variables = args.get("variables") or {}
                if not isinstance(test_key, str):
                    raise ValueError("test step missing test_key")
                result = runner_run(
                    test_key=test_key,
                    df=live,
                    variables=dict(variables),
                    display_labels=display_labels,
                )
                out_steps.append({
                    "step_index": idx,
                    "type": "test",
                    "status": "ok",
                    "output": {
                        "test_key": result.test_key,
                        "statistic": result.statistic,
                        "p_value": result.p_value,
                        "effect_size": result.effect_size,
                        "ci_low": result.ci_low,
                        "ci_high": result.ci_high,
                        "n": result.n,
                        "df": result.df,
                    },
                    "error": None,
                })
            elif step_type == "plot":
                # args carries the full PlotSpec dict
                png = render_plot(live, args)
                data_uri = (
                    "data:image/png;base64,"
                    + base64.b64encode(png).decode("ascii")
                )
                out_steps.append({
                    "step_index": idx,
                    "type": "plot",
                    "status": "ok",
                    "output": {
                        "geom": args.get("geom"),
                        "png_data_uri": data_uri,
                        "byte_size": len(png),
                    },
                    "error": None,
                })
            else:
                raise ValueError(f"unknown step type {step_type!r}")
        except (TransformError, PlotRenderError, ValueError) as exc:
            log.info("plan step %d (%s) failed: %s", idx, step_type, exc)
            any_failed = True
            out_steps.append({
                "step_index": idx,
                "type": step_type or "unknown",
                "status": "failed",
                "output": {},
                "error": str(exc),
            })
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "plan step %d (%s) raised unexpected: %s", idx, step_type, exc
            )
            any_failed = True
            out_steps.append({
                "step_index": idx,
                "type": step_type or "unknown",
                "status": "failed",
                "output": {},
                "error": f"{type(exc).__name__}: {exc}",
            })

    return PlanRunOutcome(
        status="partial" if any_failed else "ok",
        result_blob={"steps": out_steps},
        error=None,
    )
