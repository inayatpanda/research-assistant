---
slug: ancova
title: ANCOVA (analysis of covariance)
family: comparison_of_means
when_to_use: Compare group means on a continuous outcome while adjusting for one or more continuous covariates (typically a baseline measurement).
assumptions:
  - Outcome is continuous
  - Covariate-outcome relationship is linear in every group
  - Slopes are parallel across groups (homogeneity of regression slopes)
  - Residuals are approximately normal with equal variance
alternatives:
  - linear-regression
  - change-score-analysis
worked_example_domain: medicine
worked_example_dataset: bp_followup_adjusted_for_baseline
related_concepts:
  - baseline-adjustment
  - regression-to-the-mean
---

# ANCOVA

## When to use

ANCOVA is the standard analysis for randomised trials with a baseline measurement of the primary outcome. Comparing follow-up means while adjusting for baseline increases statistical power and avoids the regression-to-the-mean trap that hits crude change-score analyses.

## Assumptions

Within each group the relationship between covariate and outcome should be approximately linear, and that relationship should be the same in every group (parallel slopes). Check by adding a group x covariate interaction term — if it is significant, ANCOVA is inappropriate.

## Hypotheses

- H0: adjusted means are equal across groups
- H1: at least one adjusted mean differs

## Worked example (medicine — 12-week systolic BP, two antihypertensive regimens)

200 patients were randomised to drug A or drug B. Mean baseline SBP was 156 mmHg in both arms. At 12 weeks, unadjusted means were 138 (A) and 142 (B); ANCOVA adjusted for baseline gave adjusted means of 137.6 vs 141.4.

## Reporting

> "After adjustment for baseline SBP, follow-up SBP was 3.8 mmHg lower on drug A (95% CI 1.2 to 6.4, F(1,197)=8.2, p=0.005)."

## Pitfalls

- Never use the change score (follow-up minus baseline) as your outcome in a randomised trial — it is less efficient and biased when baselines differ by chance.
- Check the parallel-slopes assumption before reporting.

## Software

In the app: Statistics -> Linear regression (add a group factor and baseline covariate).
