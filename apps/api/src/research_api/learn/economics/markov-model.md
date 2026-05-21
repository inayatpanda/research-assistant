---
slug: markov-model
title: Markov model (basics for trial economists)
concept_family: decision-analytic-models
formula: "P(state at t+1) = P(state at t) × transition matrix"
units: "cohort distribution per cycle"
worked_example_domain: medicine
related_concepts:
  - cost-utility-analysis
  - probabilistic-sensitivity-analysis
  - half-cycle-correction
---

## Definition

A Markov model represents disease progression as a set of mutually exclusive health states with cycle-by-cycle transition probabilities. Each cycle a cohort moves between states (or stays), accruing costs and effects proportional to the time spent. The "Markovian assumption" is that future moves depend only on the present state, not on history.

## Formula

```
n_t+1 = n_t × P
```

where `n_t` is the row vector of cohort proportions across states at time t, and `P` is the (states × states) transition probability matrix. Costs and utilities accrue as `Σ_t n_t · c` and `Σ_t n_t · u` over the chosen time horizon, discounted appropriately.

## Interpretation

Use Markov models when the disease has recurrent, time-dependent events (relapse-remission, infection-treatment-cure) and a long horizon. When the Markovian assumption is violated by memory (e.g. number of prior relapses changes future risk), use tunnel states or a state-transition microsimulation instead.

## Worked example (medicine)

A 3-state heart-failure model (NYHA II → III → IV → death). Annual transition probabilities are estimated from the placebo arm of a registry. A new therapy lowers the II→III transition by 25% — simulate 30 cycles and compare lifetime cost and QALYs.

## How to report

Provide the full transition probability matrix, the source of each transition, the cycle length, whether half-cycle correction was applied, and the time horizon. CHEERS item 16 requires a state-transition diagram or schematic.
