---
slug: two-way-anova
title: Two-way ANOVA
family: comparison_of_means
when_to_use: Compare a continuous outcome across the levels of two categorical factors simultaneously and test their interaction.
assumptions:
  - Outcome is continuous
  - Approximately normal within each factor-combination cell
  - Equal variances across cells
  - Observations are independent
alternatives:
  - linear-regression
  - non-parametric-factorial-ranks
worked_example_domain: surgery
worked_example_dataset: blood_loss_by_approach_and_anaesthesia
related_concepts:
  - interaction-effect
  - main-effects
  - effect-size-partial-eta-squared
---

# Two-way ANOVA

## When to use

Use a two-way ANOVA when two categorical predictors might each affect a continuous outcome and you also want to test whether they interact — for example, surgical approach (open vs minimally invasive) crossed with anaesthesia type (general vs regional) on intraoperative blood loss.

## Assumptions

Normality and equal variance within each cell of the factor-combination grid, and independence. The design should be balanced or near-balanced; severe imbalance combined with non-normality can distort F-tests.

## Hypotheses

- Main effect A: levels of factor A have equal means
- Main effect B: levels of factor B have equal means
- Interaction A x B: the effect of A is the same at every level of B

## Worked example (surgery — blood loss by approach and anaesthesia)

In 120 elective colorectal resections, intraoperative blood loss was modelled by approach (open vs laparoscopic) and anaesthesia (general vs combined general+epidural). The interaction was significant.

## Reporting

> "There was a significant interaction between approach and anaesthesia (F(1,116)=6.4, p=0.013, partial eta-squared=0.05). Among open cases, combined epidural reduced blood loss by 180 mL (95% CI 92 to 268, p<0.001); the corresponding effect in laparoscopic cases was negligible (mean difference 18 mL, p=0.71)."

## Pitfalls

- If the interaction is significant, do not interpret main effects in isolation — report cell means or simple effects.
- Unbalanced designs need Type III sums of squares; the default in many tools is Type I, which can mislead.

## Software

In the app: Statistics -> ANOVA -> Two-way (factorial).
