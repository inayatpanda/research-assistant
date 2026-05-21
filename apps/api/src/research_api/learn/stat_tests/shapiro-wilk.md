---
slug: shapiro-wilk
title: Shapiro-Wilk normality test
family: diagnostic
when_to_use: Test whether a continuous sample plausibly came from a normal distribution.
assumptions:
  - Continuous sample
  - Independent observations
  - Sample size between 3 and ~5000 (varies by implementation)
alternatives:
  - anderson-darling
  - kolmogorov-smirnov
  - qq-plot-inspection
worked_example_domain: medicine
worked_example_dataset: residuals_lipid_trial
related_concepts:
  - normality
  - q-q-plot
  - clt
---

# Shapiro-Wilk normality test

## When to use

Use Shapiro-Wilk to check whether a continuous variable, or more typically the residuals of a model, are consistent with a normal distribution. It is most useful for moderate sample sizes (roughly 20-500). For very large samples it becomes hyper-sensitive and flags trivially small deviations.

## Assumptions

Independent observations and a continuous outcome. The test is sensitive to ties and is unsuitable for ordinal or count data. Pair the p value with a Q-Q plot — graphical inspection often beats a single test.

## Hypotheses

- H0: the data are drawn from a normal distribution
- H1: the data are not normal

## Worked example (medicine — residuals from a lipid-modification trial regression)

After fitting a regression of LDL change on baseline LDL and treatment arm (n=240), residuals were checked for normality. The Q-Q plot was approximately linear.

## Reporting

> "Residuals from the LDL change model showed no departure from normality (Shapiro-Wilk W=0.992, p=0.27, n=240)."

## Pitfalls

- Don't choose between t-test and Mann-Whitney based on a Shapiro p value alone; with large n, normality tests over-detect; with small n, they under-detect.
- The test concerns the residuals or the within-group distributions — not the raw outcome distribution overall.

## Software

In the app: Statistics -> Diagnostics -> Normality (Shapiro-Wilk).
