"""Phase 18 (MP18) — AI prompt for interpreting a Health Economics result.

Mirrors ``result_interpretation.py``: a single Results-paragraph prompt
constrained to use the exact numeric inputs verbatim, leave the
``[CITE_dataset_<id>]`` token unmodified, and avoid any inline
author-year wrapper (per DEMO-FIX-C cleanup).

The prompt assembles three short narrative beats:

  1. Cost-effectiveness narrative (ICER + dominance + mean diffs).
  2. CEAC interpretation (probability of being CE at each WTP).
  3. Sensitivity note (PSA/DSA/scenario summary, when supplied).
"""
from __future__ import annotations

import json
from typing import Any


ECONOMIC_INTERPRETATION_PROMPT = """You are helping a medical researcher write a Results paragraph from a cost-effectiveness analysis.

ANALYSIS NAME: {name}
PERSPECTIVE: {perspective}
TIME HORIZON: {time_horizon_months} months
CURRENCY: {currency}
DISCOUNT RATES: costs {disc_costs}, QALYs {disc_qalys}
INTERVENTION: {intervention_label}
COMPARATOR: {comparator_label}
UTILITY VALUE SET: {value_set}

CORE RESULT (the truth — do not invent or alter):
- mean_cost_diff = {mean_cost_diff}
- mean_qaly_diff = {mean_qaly_diff}
- icer = {icer}
- dominance_status = {dominance_status}
- nmb_at_thresholds = {nmb_block}
- ceac (probability cost-effective at the listed WTP thresholds):
{ceac_block}

SENSITIVITY (optional summary — only mention if present):
{sensitivity_block}

CITATION TOKEN (DO NOT CHANGE — leave verbatim in the output): {cite_token}

Rules:
- Output one paragraph (4-6 sentences) suitable for the Results section of a manuscript.
- Use the exact numbers above. NEVER invent a different number.
- Round costs to whole {currency} units. Round QALYs to 4 decimal places. Round ICER to whole {currency} units.
- Round probabilities to 0.001 (e.g. 0.823 → "82.3%").
- Cite the dataset by inserting {cite_token} EXACTLY ONCE at the end of the first sentence.
- Emit ONLY the raw token {cite_token}. Do NOT wrap it in parenthesised author-year text such as "(Dataset, 2026)" — the downstream citation engine renders the visible marker per the active journal style.
- If dominance_status is "dominant": state the intervention dominates (cheaper and more effective). Do not report an ICER.
- If dominance_status is "dominated": state the intervention is dominated. Do not report an ICER.
- If dominance_status is "northeast": report the positive ICER and compare it to the WTP thresholds.
- If dominance_status is "southwest": state the intervention is cheaper but less effective, then report the ICER and explain it's a trade-off.
- Mention CEAC probability at the largest WTP threshold.
- Mention sensitivity briefly only if a sensitivity block is supplied.
- Do NOT discuss methodology beyond a one-clause reminder.

Paragraph:"""


def _format_nmb_block(nmb_at_thresholds: dict[str, Any] | None) -> str:
    if not nmb_at_thresholds:
        return "(none)"
    items = sorted(nmb_at_thresholds.items(), key=lambda kv: int(kv[0]))
    return ", ".join(f"NMB@{k}={v:.0f}" for k, v in items)


def _format_ceac_block(
    ceac_data: list[dict[str, Any]] | None,
    wtp_thresholds: list[int] | None,
) -> str:
    if not ceac_data:
        return "  (no CEAC data)"
    if not wtp_thresholds:
        return "  (no WTP thresholds supplied)"
    # Render only the rows AT the wtp_thresholds (the curve carries many points).
    wanted = set(int(w) for w in wtp_thresholds)
    rows: list[str] = []
    for p in ceac_data:
        if int(p.get("wtp", -1)) in wanted:
            rows.append(
                f"  wtp={int(p['wtp'])}  P(cost-effective)={float(p['prob_costeffective']):.3f}"
            )
    return "\n".join(rows) if rows else "  (no matching CEAC points)"


def _format_sensitivity_block(sensitivity: dict[str, Any] | None) -> str:
    if not sensitivity:
        return "  (none provided)"
    kind = sensitivity.get("type", "?")
    summary = sensitivity.get("summary") or {}
    lines: list[str] = [f"  kind: {kind}"]
    for k, v in summary.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def build_economic_interpretation_prompt(
    *,
    name: str,
    perspective: str,
    time_horizon_months: int,
    currency: str,
    discount_rate_costs: float,
    discount_rate_qalys: float,
    intervention_label: str,
    comparator_label: str,
    value_set: str,
    mean_cost_diff: float,
    mean_qaly_diff: float,
    icer: float | None,
    dominance_status: str,
    nmb_at_thresholds: dict[str, Any] | None,
    ceac_data: list[dict[str, Any]] | None,
    wtp_thresholds: list[int] | None,
    sensitivity: dict[str, Any] | None,
    cite_token: str,
) -> str:
    return ECONOMIC_INTERPRETATION_PROMPT.format(
        name=name,
        perspective=perspective,
        time_horizon_months=time_horizon_months,
        currency=currency,
        disc_costs=discount_rate_costs,
        disc_qalys=discount_rate_qalys,
        intervention_label=intervention_label,
        comparator_label=comparator_label,
        value_set=value_set,
        mean_cost_diff=mean_cost_diff,
        mean_qaly_diff=mean_qaly_diff,
        icer=icer,
        dominance_status=dominance_status,
        nmb_block=_format_nmb_block(nmb_at_thresholds),
        ceac_block=_format_ceac_block(ceac_data, wtp_thresholds),
        sensitivity_block=_format_sensitivity_block(sensitivity),
        cite_token=cite_token,
    )


__all__ = ["build_economic_interpretation_prompt"]
