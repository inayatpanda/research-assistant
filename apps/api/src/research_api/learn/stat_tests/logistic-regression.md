---
slug: logistic-regression
title: Logistic regression
family: correlation_regression
when_to_use: Model a binary outcome as a function of one or more predictors and report adjusted odds ratios.
assumptions:
  - Outcome is binary
  - Observations are independent
  - Linearity of predictors on the log-odds scale (for continuous predictors)
  - No severe multicollinearity
  - Adequate events-per-variable (typically >=10)
alternatives:
  - probit-regression
  - log-binomial-regression
worked_example_domain: surgery
worked_example_dataset: thirty_day_readmission_predictors
related_concepts:
  - odds-ratio
  - calibration
  - discrimination-auc
---

# Logistic regression

## When to use

Logistic regression models the probability of a binary outcome (yes/no, alive/dead, readmitted/not). Use it for risk prediction and to adjust an exposure's effect for confounders, producing odds ratios with confidence intervals. It is the workhorse of observational clinical research.

## Assumptions

Independent observations, binary outcome, linearity of continuous predictors on the log-odds scale (check with restricted cubic splines if doubtful), and roughly 10+ events per predictor variable to avoid over-fitting. Discrimination is summarised by the C-statistic (AUC); calibration by a Hosmer-Lemeshow test or calibration curve.

## Hypotheses

For each coefficient: H0 that beta_j = 0 (equivalently OR = 1); H1 otherwise.

## Worked example (surgery — predictors of 30-day readmission after colorectal surgery)

In a registry of 1,200 colorectal resections, 30-day readmission (10.4%) was modelled on age, ASA, laparoscopic vs open approach, and discharge day. AUC = 0.74 (95% CI 0.70-0.78), Hosmer-Lemeshow p=0.42.

## Reporting

> "Independent predictors of 30-day readmission were ASA grade >=3 (adjusted OR 1.9, 95% CI 1.3 to 2.8, p<0.001) and open approach (adjusted OR 1.5, 95% CI 1.0 to 2.2, p=0.04). Age and discharge day were not significant. Model discrimination AUC 0.74."

## Pitfalls

- An odds ratio is not a risk ratio when the outcome is common (>10%) — switch to log-binomial or report risk differences.
- Don't dichotomise continuous predictors before modelling — you lose information.

## Software

In the app: Statistics -> Regression -> Logistic.
