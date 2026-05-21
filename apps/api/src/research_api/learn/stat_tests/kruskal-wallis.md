---
slug: kruskal-wallis
title: Kruskal-Wallis H test
family: non_parametric_comparison
when_to_use: Compare distributions of a continuous or ordinal outcome across three or more independent groups when normality fails.
assumptions:
  - Outcome is at least ordinal
  - Independent observations within and between groups
  - Distributions have similar shape (for interpreting as a median test)
alternatives:
  - one-way-anova
  - welch-anova
worked_example_domain: orthopaedics
worked_example_dataset: oxford_knee_score_three_implants
related_concepts:
  - rank-test
  - dunn-post-hoc
---

# Kruskal-Wallis H test

## When to use

Kruskal-Wallis is the non-parametric analogue of one-way ANOVA. Use it for an outcome that is ordinal, clearly skewed, or measured on a small sample where normality cannot be assumed, across three or more independent groups.

## Assumptions

Independence of observations and an at-least-ordinal outcome. The test compares mean ranks; significant results imply at least one group's distribution differs. Post-hoc pairwise comparisons (Dunn's test with Bonferroni correction) identify which groups differ.

## Hypotheses

- H0: all groups have identical distributions
- H1: at least one group's distribution is stochastically different

## Worked example (orthopaedics — Oxford Knee Score across three implant designs)

In a registry cohort, 12-month Oxford Knee Score was compared across three implant designs (n=80, 85, 75). Medians were 41 (IQR 37-44), 39 (IQR 34-43), and 36 (IQR 31-41).

## Reporting

> "Oxford Knee Score at 12 months differed across implant designs (Kruskal-Wallis H(2)=18.6, p<0.001). Dunn's post-hoc with Bonferroni correction showed Implant A scored higher than Implant C (adjusted p<0.001) and higher than Implant B (adjusted p=0.04); B and C did not differ."

## Pitfalls

- Don't quote a difference in means alongside this test; report medians and IQRs.
- Skipping post-hoc tests when the omnibus is significant leaves the result uninterpretable.

## Software

In the app: Statistics -> Non-parametric -> Kruskal-Wallis (post-hoc: Dunn).
