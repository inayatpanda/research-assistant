---
slug: mann-whitney-u
title: Mann-Whitney U test
family: non_parametric_comparison
when_to_use: Compare the distributions of a continuous or ordinal outcome between two independent groups when normality is not plausible.
assumptions:
  - Outcome is at least ordinal
  - Observations are independent
  - The two distributions have similar shape (if interpreting as a median test)
alternatives:
  - independent-t-test
  - welch-t-test
worked_example_domain: medicine
worked_example_dataset: hospital_los_two_pathways
related_concepts:
  - rank-sum
  - skewed-distributions
  - effect-size-r
---

# Mann-Whitney U test

## When to use

Reach for Mann-Whitney (also called Wilcoxon rank-sum) when comparing a continuous outcome between two independent groups and either the data are clearly skewed, the sample is small, or the outcome is ordinal (e.g. a 5-point pain scale). The test compares the ranks of values, not their means.

## Assumptions

Independence within and between groups. The test is genuinely distribution-free for the null "the distributions are identical", but if you intend to interpret a significant result as a difference in medians you must assume the two distributions have similar shape.

## Hypotheses

- H0: the two distributions are identical
- H1: one distribution is stochastically larger than the other

## Worked example (medicine — hospital length of stay on two pneumonia pathways)

Length of stay was recorded for 60 patients on pathway A and 55 on pathway B. Medians were 4 days (IQR 3-7) vs 6 days (IQR 4-9). The distributions were right-skewed.

## Reporting

> "Median length of stay was shorter on pathway A (4 days, IQR 3-7) than on pathway B (6 days, IQR 4-9); Mann-Whitney U=1135, p=0.003, r=0.28."

## Pitfalls

- Report medians and IQRs, not means and SDs, alongside this test.
- A significant Mann-Whitney does not always mean medians differ — it can reflect a difference in shape or spread.

## Software

In the app: Statistics -> Non-parametric -> Mann-Whitney U.
