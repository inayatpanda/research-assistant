---
slug: spearman-correlation
title: Spearman rank correlation
family: correlation_regression
when_to_use: Quantify monotonic association between two variables when one or both are ordinal or the relationship is non-linear.
assumptions:
  - Variables are at least ordinal
  - Relationship is monotonic (not necessarily linear)
  - Pairs are independent
alternatives:
  - pearson-correlation
  - kendall-tau
worked_example_domain: medicine
worked_example_dataset: nyha_class_vs_bnp
related_concepts:
  - rank-based-stats
  - monotonic-relationship
---

# Spearman rank correlation

## When to use

Spearman's rho is the rank-based companion of Pearson. Use it when either variable is ordinal (e.g. NYHA class, pain score), the relationship is monotonic but not linear, or outliers are influencing a Pearson estimate. It is more robust than Pearson and very widely applicable.

## Assumptions

Pairs are independent and the variables are at least ordinal. There is no normality assumption. The test detects monotonic — not specifically linear — relationships.

## Hypotheses

- H0: there is no monotonic association
- H1: there is a monotonic association (positive or negative)

## Worked example (medicine — NYHA class vs serum BNP in heart failure)

In 200 outpatients with heart failure, NYHA class (I-IV) and serum BNP (pg/mL, skewed) were recorded. BNP was right-skewed; ranks were used.

## Reporting

> "Serum BNP rose monotonically with NYHA class (Spearman's rho = 0.54, 95% CI 0.43 to 0.63, p<0.001, n=200)."

## Pitfalls

- Spearman captures monotonic associations only; a U-shaped relationship will give near-zero rho.
- Don't switch between Pearson and Spearman based on which produces a smaller p value — choose before analysis.

## Software

In the app: Statistics -> Correlation -> Spearman.
