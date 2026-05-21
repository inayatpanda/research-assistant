---
slug: linear-regression
title: Simple linear regression
family: correlation_regression
when_to_use: Model a continuous outcome as a linear function of one continuous (or binary) predictor.
assumptions:
  - Linearity between predictor and outcome
  - Independence of residuals
  - Homoscedasticity (constant residual variance)
  - Normally distributed residuals
alternatives:
  - multiple-linear-regression
  - spearman-correlation
worked_example_domain: medicine
worked_example_dataset: hba1c_vs_fasting_glucose
related_concepts:
  - regression-coefficient
  - residual-diagnostics
  - r-squared
---

# Simple linear regression

## When to use

Use simple linear regression when you want a quantitative model of how one continuous predictor relates to a continuous outcome — for example, predicting HbA1c from fasting glucose, or grip strength from age. The slope gives the expected change in outcome per unit change in predictor.

## Assumptions

Linearity between predictor and outcome, independent observations, residuals with constant variance (homoscedasticity), and approximately normal residuals. Always inspect residuals-vs-fitted and Q-Q plots before trusting the model.

## Hypotheses

- H0: slope = 0
- H1: slope != 0

## Worked example (medicine — HbA1c vs fasting glucose)

In a primary care diabetes audit, HbA1c (%) was regressed on fasting plasma glucose (mmol/L) in 220 patients with type 2 diabetes. Residual diagnostics showed mild heteroscedasticity but no influential outliers.

## Reporting

> "Each 1 mmol/L increase in fasting glucose was associated with an HbA1c increase of 0.42% (95% CI 0.36 to 0.48, t(218)=14.0, p<0.001, R^2 = 0.47, n=220)."

## Pitfalls

- A high R^2 does not validate the model; check residuals for non-linearity or outliers.
- Don't extrapolate beyond the range of observed predictor values.

## Software

In the app: Statistics -> Regression -> Linear (single predictor).
