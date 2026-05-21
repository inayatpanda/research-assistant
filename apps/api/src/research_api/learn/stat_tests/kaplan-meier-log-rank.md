---
slug: kaplan-meier-log-rank
title: Kaplan-Meier survival + log-rank test
family: survival
when_to_use: Estimate and compare survival functions between two or more groups when censoring is present.
assumptions:
  - Time-to-event outcome with right-censoring
  - Non-informative censoring
  - Proportional hazards (for valid log-rank inference)
alternatives:
  - cox-proportional-hazards
  - wilcoxon-gehan-test
worked_example_domain: orthopaedics
worked_example_dataset: implant_survival_two_designs
related_concepts:
  - censoring
  - survival-curves
  - log-rank-test
---

# Kaplan-Meier + log-rank

## When to use

Kaplan-Meier (KM) curves visualise survival (or any time-to-event) data for one or more groups; the log-rank test compares those curves. Use them for unadjusted comparisons of implant survival, recurrence-free survival, or any time-to-event outcome with censoring.

## Assumptions

Right-censoring is non-informative, and the groups have proportional hazards over follow-up. Crossing KM curves violate proportional hazards and signal that the log-rank statistic should be interpreted with care (consider Wilcoxon-Gehan or restricted mean survival times instead).

## Hypotheses

- H0: survival functions are identical across groups
- H1: at least one group's survival differs

## Worked example (orthopaedics — implant survival of two TKR designs)

In a single-surgeon cohort of 800 TKRs (400 per design), 10-year implant survival was 96% (Design A) vs 91% (Design B), with the curves diverging after year five.

## Reporting

> "10-year implant survival was 96% (95% CI 93 to 98) for Design A and 91% (95% CI 87 to 94) for Design B. The difference was significant (log-rank chi-squared(1)=8.42, p=0.004)."

## Pitfalls

- KM is an unadjusted analysis; if groups differ at baseline, the comparison is confounded — pair it with Cox regression.
- Don't compare curves at a single time point without addressing multiple-testing concerns.

## Software

In the app: Statistics -> Survival -> Kaplan-Meier (log-rank test).
