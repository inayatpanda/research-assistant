---
slug: incremental-cost-effectiveness-ratio
title: Incremental cost-effectiveness ratio (ICER)
concept_family: cost-effectiveness
formula: "ICER = (Cost_new - Cost_comparator) / (Effect_new - Effect_comparator)"
units: "currency per clinical unit (e.g. £/QALY)"
worked_example_domain: orthopaedics
related_concepts:
  - cost-effectiveness-ratio
  - quality-adjusted-life-year
  - willingness-to-pay-threshold
  - cost-effectiveness-acceptability-curve
---

## Definition

The incremental cost-effectiveness ratio (ICER) is the additional cost of adopting a new strategy divided by the additional clinical benefit it yields versus a relevant comparator. It is the headline output of every cost-effectiveness analysis and the input to a willingness-to-pay decision.

## Formula

```
ICER = (Cost_new − Cost_comparator) / (Effect_new − Effect_comparator)
```

## Interpretation

If the ICER lies below the WTP threshold (e.g. £20,000/QALY for NICE), the new intervention is "cost-effective". An ICER in the south-east quadrant of the cost-effectiveness plane (cheaper and more effective) is "dominant" — the ratio is reported but the decision is obvious. An ICER in the north-west quadrant (more expensive and less effective) is "dominated" and should be reported as such, not as a negative ICER.

## Worked example (orthopaedics)

Cementless hip arthroplasty costs £9,500 and yields 12.40 QALYs over a lifetime. Cemented costs £8,200 and yields 12.15 QALYs. ICER = (9,500 − 8,200) / (12.40 − 12.15) = 1,300 / 0.25 = £5,200/QALY — below NICE's £20,000 threshold, so cementless is cost-effective.

## How to report

State the comparator, the perspective, the discount rate, the time horizon, and the WTP threshold against which you judge the ICER. Show the deterministic ICER, then a probabilistic ICER from PSA with a [CEAC](?slug=cost-effectiveness-acceptability-curve). Never report a negative ICER — explain dominance instead.
