---
slug: quality-adjusted-life-year
title: Quality-adjusted life-year (QALY)
concept_family: outcomes-measurement
formula: "QALY = Sum over time periods of (utility_t × duration_t)"
units: "QALYs (dimensionless years weighted 0-1)"
worked_example_domain: medicine
related_concepts:
  - cost-utility-analysis
  - eq-5d
  - incremental-cost-effectiveness-ratio
  - disability-adjusted-life-year
---

## Definition

A QALY combines length of life with health-related quality of life into a single number. One QALY equals one year spent in perfect health (utility = 1.0). A year spent in poor health is worth less than one QALY (e.g. 0.6). Death and "worse than dead" states score 0 or negative.

## Formula and health-state valuation

```
QALY = Sigma_t (utility_t × duration_t)
```

Utilities (or "health-state values") come from preference-based measures applied to patient responses: most commonly EQ-5D-3L / EQ-5D-5L with a country-specific value set (e.g. the NICE-recommended EQ-5D-3L UK tariff). Alternatives include SF-6D, HUI3, and direct elicitation (time trade-off, standard gamble).

## Interpretation

A patient who lives 5 years at utility 0.8, followed by 3 years at utility 0.5, accrues 5×0.8 + 3×0.5 = 5.5 QALYs. QALYs gained from an intervention are the integral of the difference between two utility-by-time curves ("area between curves").

## Worked example (medicine)

A novel CKD therapy lifts mean EQ-5D-5L utility from 0.62 to 0.74 over a 10-year horizon while extending survival from 6.8 to 7.4 years on average. Discounted lifetime QALYs rise from 4.21 to 5.48 — a 1.27 QALY gain per patient.

## How to report

State the source of utilities (instrument + value set + respondent group), how baseline utility was estimated, whether values were discounted, and how missing utility data were imputed. CHEERS items 12-13 require this transparency.
