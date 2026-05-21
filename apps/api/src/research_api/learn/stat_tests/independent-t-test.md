---
slug: independent-t-test
title: Independent samples t-test
family: comparison_of_means
when_to_use: Compare the means of one continuous variable across two independent groups when each observation belongs to exactly one group.
assumptions:
  - Outcome is continuous (interval or ratio)
  - Approximately normal in each group, or n large enough for the CLT
  - Independence of observations within and between groups
  - Approximately equal variances (otherwise use Welch's correction)
alternatives:
  - mann-whitney-u
  - welch-t-test
worked_example_domain: orthopaedics
worked_example_dataset: knee_flexion_two_implants
related_concepts:
  - confidence-intervals
  - effect-size-cohens-d
  - normality-checks
---

# Independent samples t-test

## When to use

Use this test to compare a single continuous outcome between two unrelated groups — for example, post-operative outcomes between two implant designs, two anaesthetic regimens, or two rehabilitation protocols. Each patient must contribute to exactly one group.

## Assumptions

The outcome should be approximately normally distributed within each group (check with a Shapiro-Wilk test or Q-Q plot), variances should be similar (Levene's test), and observations must be independent. If sample sizes per group exceed roughly 30, the central limit theorem makes the normality assumption flexible.

## Hypotheses

- H0: mean(Group A) = mean(Group B)
- H1: mean(Group A) != mean(Group B)

## Worked example (orthopaedics — knee flexion, two implant types)

Sixty patients undergoing primary total knee arthroplasty were randomised to either Implant A (n=30) or Implant B (n=30). Knee flexion (degrees) was measured at 6 weeks. Mean flexion was 110.4 +/- 8.2 in Group A and 105.1 +/- 7.6 in Group B. The Levene test was non-significant (p=0.62) so equal variances were assumed.

## Reporting

> "Mean flexion was greater in Implant A (110.4 +/- 8.2 degrees) than Implant B (105.1 +/- 7.6 degrees); the difference of 5.3 degrees (95% CI 1.2 to 9.4) was statistically significant (t(58)=2.61, p=0.011, Cohen's d=0.67)."

## Pitfalls

- Don't dichotomise a continuous variable to fit this test.
- Don't run a t-test on paired or matched data — use the paired t-test.
- Always report the confidence interval alongside the p value.

## Software

In the app: Statistics -> t-test -> Independent samples.
