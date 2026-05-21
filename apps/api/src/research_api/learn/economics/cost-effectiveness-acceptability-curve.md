---
slug: cost-effectiveness-acceptability-curve
title: Cost-effectiveness acceptability curve (CEAC)
concept_family: uncertainty
formula: "P(intervention is cost-effective | WTP) plotted vs WTP"
units: "probability (0-1)"
worked_example_domain: orthopaedics
related_concepts:
  - probabilistic-sensitivity-analysis
  - net-monetary-benefit
  - willingness-to-pay-threshold
---

## Definition

A cost-effectiveness acceptability curve (CEAC) plots, on the y-axis, the probability that an intervention is cost-effective and, on the x-axis, the willingness-to-pay threshold. It is the standard graphical summary of probabilistic sensitivity analysis (PSA) uncertainty around the ICER.

## Interpretation

At each WTP, compute the proportion of PSA iterations in which the intervention's net monetary benefit exceeds the comparator's. Plot the result. A CEAC that rises steeply and reaches >0.8 below the relevant threshold indicates robust cost-effectiveness; a flat curve hovering near 0.5 indicates genuine equipoise.

## Worked example (orthopaedics)

Across 5,000 PSA iterations of cementless vs. cemented hip arthroplasty, cementless is cost-effective in 78% of iterations at £10,000/QALY and 92% at £20,000/QALY. The CEAC crosses 0.5 at about £6,500/QALY — i.e. cementless is "more likely than not" cost-effective above this WTP.

## How to report

Show one curve per strategy on the same axes (the so-called "frontier" CEAC), label the curves with their probability at the policy-relevant WTP, and include the cost-effectiveness acceptability frontier (CEAF), which traces the strategy with the highest expected NMB at each WTP. CHEERS item 24 requires this output for any modelled CEA.
