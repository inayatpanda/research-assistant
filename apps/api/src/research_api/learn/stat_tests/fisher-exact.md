---
slug: fisher-exact
title: Fisher's exact test
family: categorical_association
when_to_use: Test association in a small 2x2 (or larger) contingency table when expected counts are too low for chi-square.
assumptions:
  - Variables are categorical
  - Observations are independent
  - Row and column totals are conceptually fixed (originally) but the test is robust to this assumption
alternatives:
  - chi-square-independence
worked_example_domain: surgery
worked_example_dataset: anastomotic_leak_by_stapler_type
related_concepts:
  - exact-test
  - sparse-tables
---

# Fisher's exact test

## When to use

Use Fisher's exact test whenever a 2x2 contingency table has an expected count below 5 in any cell — typically with small surgical cohorts, rare outcomes, or pilot studies. The test enumerates every more-extreme table under the null and computes an exact p value, so no normal approximation is involved.

## Assumptions

Independent observations and categorical predictor and outcome. The exact test is conservative with very sparse tables; mid-p variants exist if conservatism is a concern.

## Hypotheses

- H0: the two variables are independent
- H1: they are associated

## Worked example (surgery — anastomotic leak rate by circular stapler model)

In a retrospective series of 60 low anterior resections, anastomotic leak occurred in 2/30 cases stapled with model A and 9/30 with model B.

## Reporting

> "Anastomotic leak occurred in 2/30 (6.7%) with stapler A vs 9/30 (30%) with stapler B; Fisher's exact two-sided p=0.041, odds ratio 0.17 (95% CI 0.03 to 0.85)."

## Pitfalls

- For 2x2 tables, report the odds ratio with a confidence interval — a p value alone is unhelpful.
- Don't use Fisher's exact for paired data; that needs McNemar's test.

## Software

In the app: Statistics -> Categorical -> Fisher's exact.
