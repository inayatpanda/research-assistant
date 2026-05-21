---
slug: net-monetary-benefit
title: Net monetary benefit (NMB)
concept_family: cost-effectiveness
formula: "NMB = (Effect × WTP) - Cost"
units: "currency (e.g. £)"
worked_example_domain: surgery
related_concepts:
  - incremental-cost-effectiveness-ratio
  - willingness-to-pay-threshold
  - cost-effectiveness-acceptability-curve
---

## Definition

Net monetary benefit (NMB) re-expresses cost-effectiveness on a single monetary scale by multiplying clinical benefit by a willingness-to-pay (WTP) threshold and subtracting cost. A positive NMB means the strategy delivers more value than it consumes; the strategy with the highest NMB at the chosen WTP is the optimal choice.

## Formula

```
NMB = (Effect × WTP) − Cost
INB (incremental NMB) = NMB_new − NMB_comparator
```

## Interpretation

NMB sidesteps the awkward properties of the ICER (negative ratios when the new strategy is dominated, infinite ratios when ΔEffect = 0). It is also the natural quantity to summarise across PSA simulations — proportion of iterations with positive INB equals the probability the new strategy is cost-effective at that WTP. Plotting NMB versus WTP yields the cost-effectiveness acceptability curve.

## Worked example (surgery)

Bariatric surgery vs. medical therapy in severe obesity: ΔEffect = 1.8 QALYs, ΔCost = £18,000, WTP = £20,000/QALY. INB = (1.8 × 20,000) − 18,000 = 36,000 − 18,000 = £18,000 — strongly positive, so surgery is preferred at this threshold.

## How to report

Always state the WTP threshold(s) at which NMB is calculated. Report INB alongside the ICER and provide a sensitivity analysis across plausible WTP values — see the [CEAC](?slug=cost-effectiveness-acceptability-curve).
