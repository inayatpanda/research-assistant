---
slug: repeated-measures-anova
title: Repeated-measures ANOVA
family: comparison_of_means
when_to_use: Compare a continuous outcome across three or more time points measured on the same subjects.
assumptions:
  - Outcome is continuous
  - Approximately normal at each time point
  - Sphericity (equal variance of within-subject differences) — use Mauchly's test
  - Subjects are independent
alternatives:
  - friedman
  - linear-mixed-effects-model
worked_example_domain: orthopaedics
worked_example_dataset: rom_post_rotator_cuff_repair
related_concepts:
  - sphericity-correction
  - greenhouse-geisser
---

# Repeated-measures ANOVA

## When to use

Use this test for a continuous outcome measured repeatedly on the same subjects — for example range of motion at 6 weeks, 3 months, and 12 months after the same surgery. It is the within-subjects analogue of one-way ANOVA.

## Assumptions

Normality at each time point and sphericity: the variance of all pairwise within-subject differences should be equal. If Mauchly's test rejects sphericity, apply a Greenhouse-Geisser or Huynh-Feldt correction to the degrees of freedom.

## Hypotheses

- H0: mean is the same at every time point
- H1: at least one time-point mean differs

## Worked example (orthopaedics — shoulder abduction after rotator cuff repair)

Thirty-five patients had shoulder abduction recorded at 6 weeks, 3 months, and 12 months. Means were 78 +/- 14, 121 +/- 17, and 148 +/- 19 degrees. Mauchly's test indicated sphericity violation (p=0.04), so Greenhouse-Geisser was applied (epsilon=0.78).

## Reporting

> "Shoulder abduction differed across time points (F(1.56, 53.0)=212, p<0.001, partial eta-squared=0.86). Pairwise Bonferroni-corrected contrasts confirmed improvement at every interval (all p<0.001)."

## Pitfalls

- Don't ignore missing time points — listwise deletion discards entire patients and biases results. A linear mixed model handles missingness more gracefully.
- Report whether you used a sphericity correction; uncorrected df overstates significance.

## Software

In the app: Statistics -> ANOVA -> Repeated measures.
