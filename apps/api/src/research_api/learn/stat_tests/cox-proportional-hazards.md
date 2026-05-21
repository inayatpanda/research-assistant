---
slug: cox-proportional-hazards
title: Cox proportional hazards regression
family: survival
when_to_use: Model time-to-event data while adjusting for covariates and report hazard ratios.
assumptions:
  - Outcome is time-to-event with possible censoring
  - Proportional hazards (hazard ratios constant over time)
  - Non-informative censoring
  - Linearity of continuous predictors on the log-hazard scale
alternatives:
  - kaplan-meier-log-rank
  - parametric-survival
  - flexible-parametric-models
worked_example_domain: surgery
worked_example_dataset: time_to_revision_two_implants_adjusted
related_concepts:
  - hazard-ratio
  - censoring
  - schoenfeld-residuals
---

# Cox proportional hazards regression

## When to use

The Cox model is the standard tool for time-to-event data with covariates — for example, modelling time to implant revision while adjusting for age, BMI, and implant brand. It produces hazard ratios with confidence intervals, treating censored observations correctly.

## Assumptions

Time-to-event with possible right-censoring; non-informative censoring (censored patients have the same future risk as those still at risk); proportional hazards — i.e. the hazard ratio for a covariate is constant over follow-up. Check with Schoenfeld residual tests or by plotting log(-log(S(t))) curves.

## Hypotheses

For each covariate: H0 that hazard ratio = 1 (beta = 0).

## Worked example (surgery — time to revision after primary hip arthroplasty)

In a registry of 4,800 primary hip arthroplasties (median follow-up 7 years, 312 revisions), time to revision was modelled on age, BMI, and bearing surface (ceramic-on-ceramic vs metal-on-poly), with the PH assumption confirmed by Schoenfeld tests.

## Reporting

> "Compared with ceramic-on-ceramic, metal-on-poly bearings were associated with a higher revision risk (adjusted HR 1.42, 95% CI 1.09 to 1.85, p=0.009). Each 10-year increment in age reduced revision risk (adjusted HR 0.78, 95% CI 0.69 to 0.88, p<0.001). The proportional hazards assumption was not violated (global Schoenfeld p=0.34)."

## Pitfalls

- If proportional hazards fails, consider time-varying coefficients or a flexible parametric model — don't just report the Cox estimate.
- Hazard ratios are not risk ratios; communicate the absolute event rates as well.

## Software

In the app: Statistics -> Survival -> Cox regression.
