---
slug: wilcoxon-signed-rank
title: Wilcoxon signed-rank test
family: non_parametric_comparison
when_to_use: Compare two related measurements (paired or before/after) when within-pair differences are not normal or the outcome is ordinal.
assumptions:
  - Within-pair differences are at least ordinal
  - Pairs are independent of each other
  - Distribution of differences is approximately symmetric (for inference on the median difference)
alternatives:
  - paired-t-test
  - sign-test
worked_example_domain: medicine
worked_example_dataset: pain_score_pre_post_analgesic
related_concepts:
  - rank-test
  - paired-design
---

# Wilcoxon signed-rank test

## When to use

Use the Wilcoxon signed-rank test as the non-parametric counterpart of the paired t-test — for example, comparing a patient's pain score before and after an intervention when scores are skewed or ordinal (such as a 0-10 numeric rating scale).

## Assumptions

Pairs are independent and the within-pair differences are at least ordinal. To interpret a significant result as a shift in median you should also believe the distribution of differences is roughly symmetric; otherwise just claim a distributional shift.

## Hypotheses

- H0: the distribution of within-pair differences is centred on zero
- H1: the distribution is shifted away from zero

## Worked example (medicine — numeric pain rating before and after IV paracetamol)

In 40 emergency department patients with acute musculoskeletal pain, pain was rated on a 0-10 NRS before and 30 minutes after IV paracetamol. Median pre-treatment score was 8 (IQR 7-9); median post was 4 (IQR 3-6).

## Reporting

> "Pain scores fell from a median of 8 (IQR 7-9) to 4 (IQR 3-6) after IV paracetamol; Wilcoxon signed-rank W=748, p<0.001."

## Pitfalls

- Drop pairs whose difference is exactly zero, then base the test on the remaining n; some packages handle ties differently.
- Don't report a "mean change" with this test — use the Hodges-Lehmann estimator or median paired difference.

## Software

In the app: Statistics -> Non-parametric -> Wilcoxon signed-rank.
