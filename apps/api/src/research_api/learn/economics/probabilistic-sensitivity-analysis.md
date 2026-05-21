---
slug: probabilistic-sensitivity-analysis
title: Probabilistic sensitivity analysis (PSA)
concept_family: uncertainty
formula: "Sample parameters from distributions, recompute outputs, summarise the distribution of ICER/NMB"
units: "ICER distribution"
worked_example_domain: surgery
related_concepts:
  - cost-effectiveness-acceptability-curve
  - markov-model
  - cheers
---

## Definition

Probabilistic sensitivity analysis (PSA) propagates parameter uncertainty through an economic model by Monte Carlo sampling each input from its specified distribution, recomputing costs and effects, and summarising the joint distribution of outputs. PSA is the recommended (CHEERS item 20) way to express uncertainty in a model-based CEA.

## How it works

1. Assign a probability distribution to every uncertain parameter (Beta for probabilities and utilities, Gamma or Log-normal for costs, Normal/Log-normal for relative risks).
2. Draw n correlated samples (typically n = 1,000-10,000).
3. Run the model once per sample.
4. Plot results on the cost-effectiveness plane and derive the [CEAC](?slug=cost-effectiveness-acceptability-curve), mean ICER, and credible interval.

## Interpretation

The mean ICER from PSA is typically (but not always) close to the deterministic ICER. The shape of the cloud on the CE plane reveals whether uncertainty is driven by costs, effects, or both. A cloud crossing into the dominated quadrant indicates real risk that the intervention is worse on both axes.

## Worked example (surgery)

PSA on a cardiac-valve replacement model (n=5,000 iterations): mean ICER £14,200/QALY (95% CrI £6,800-£24,500), 81% probability of cost-effectiveness at £20,000/QALY.

## How to report

State the number of iterations, the distribution chosen for each parameter (with justification), how correlations were preserved, and present both the CE plane scatter and the CEAC. Pair with deterministic one-way and scenario analyses for transparency.
