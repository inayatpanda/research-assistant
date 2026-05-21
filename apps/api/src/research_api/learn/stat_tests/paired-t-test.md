---
slug: paired-t-test
title: Paired samples t-test
family: comparison_of_means
when_to_use: Compare two related measurements on the same subject (or matched pair) — typically before-and-after measurements of a continuous outcome.
assumptions:
  - Outcome is continuous
  - The within-pair differences are approximately normal
  - Pairs are independent of each other
alternatives:
  - wilcoxon-signed-rank
worked_example_domain: orthopaedics
worked_example_dataset: hip_oxford_score_pre_post
related_concepts:
  - paired-design
  - normality-checks
  - effect-size-cohens-dz
---

# Paired samples t-test

## When to use

Choose the paired t-test whenever the two measurements being compared come from the same subject, the same joint, or a matched pair. Typical orthopaedic uses are pre-operative versus post-operative outcome scores, or left-versus-right comparisons in symmetric conditions.

## Assumptions

The key assumption is that the within-pair differences are approximately normal — not the raw scores themselves. Plot a histogram or Q-Q plot of the differences. Pairs themselves must still be independent (one patient does not influence another).

## Hypotheses

- H0: mean of within-pair differences = 0
- H1: mean of within-pair differences != 0

## Worked example (orthopaedics — Oxford Hip Score before and after total hip arthroplasty)

Forty patients had their Oxford Hip Score recorded preoperatively and at 12 months postoperatively. Mean score rose from 18.2 +/- 6.1 to 41.8 +/- 5.4. The mean within-patient improvement was 23.6 (SD of differences 7.9).

## Reporting

> "Oxford Hip Score improved from 18.2 +/- 6.1 preoperatively to 41.8 +/- 5.4 at 12 months, a mean improvement of 23.6 points (95% CI 21.1 to 26.1; t(39)=18.9, p<0.001; Cohen's dz=2.99)."

## Pitfalls

- Do not run an independent t-test on paired data — it discards the pairing and inflates variance.
- If many differences are zero or strongly skewed, prefer the Wilcoxon signed-rank test.

## Software

In the app: Statistics -> t-test -> Paired samples.
