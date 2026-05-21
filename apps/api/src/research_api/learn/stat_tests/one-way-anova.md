---
slug: one-way-anova
title: One-way ANOVA
family: comparison_of_means
when_to_use: Compare the means of a continuous outcome across three or more independent groups defined by one categorical factor.
assumptions:
  - Outcome is continuous
  - Approximately normal within each group
  - Equal variances across groups (homoscedasticity)
  - Observations are independent
alternatives:
  - kruskal-wallis
  - welch-anova
worked_example_domain: orthopaedics
worked_example_dataset: fixation_time_three_fracture_devices
related_concepts:
  - post-hoc-tukey
  - effect-size-eta-squared
---

# One-way ANOVA

## When to use

Use one-way ANOVA when the predictor is one categorical variable with at least three levels and the outcome is continuous. The omnibus F-test tells you whether at least one mean differs — it does not tell you which. Pair it with a post-hoc test (Tukey HSD is the usual choice) to identify specific differences.

## Assumptions

Normality within each group (or n large enough), equal variances across groups, and independence. Use Levene's test for variance equality and Shapiro-Wilk per group for normality. If variances are unequal, consider Welch's ANOVA.

## Hypotheses

- H0: mean_1 = mean_2 = ... = mean_k
- H1: at least one mean differs

## Worked example (orthopaedics — operative time across three distal radius fixation devices)

Ninety patients with distal radius fractures were operated on with one of three plate designs (n=30 each). Mean operative time was 38 +/- 7 min (Plate A), 45 +/- 8 min (Plate B), and 52 +/- 9 min (Plate C).

## Reporting

> "Operative time differed significantly across plate designs (F(2,87)=22.4, p<0.001; eta-squared=0.34). Tukey post-hoc tests showed Plate C was slower than Plate A by 14 min (95% CI 9 to 19, p<0.001) and Plate B was slower than Plate A by 7 min (95% CI 2 to 12, p=0.005)."

## Pitfalls

- Don't run multiple t-tests instead of an ANOVA — that inflates type I error.
- A significant ANOVA does not justify reporting only the largest pairwise difference; report the post-hoc comparisons that answer your question.

## Software

In the app: Statistics -> ANOVA -> One-way.
