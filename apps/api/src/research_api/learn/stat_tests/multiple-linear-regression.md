---
slug: multiple-linear-regression
title: Multiple linear regression
family: correlation_regression
when_to_use: Model a continuous outcome as a linear function of two or more predictors, adjusting each effect for the others.
assumptions:
  - Linearity for each continuous predictor
  - Independent residuals
  - Homoscedasticity
  - Normally distributed residuals
  - No severe multicollinearity (VIF < 5-10)
alternatives:
  - ridge-regression
  - generalised-additive-model
worked_example_domain: surgery
worked_example_dataset: los_by_age_asa_op_time
related_concepts:
  - confounding
  - adjustment
  - vif
---

# Multiple linear regression

## When to use

Use multiple linear regression when you need to adjust for several predictors simultaneously — for example, modelling postoperative length of stay (LOS) on age, ASA grade, and operative duration. Each coefficient gives the expected change in outcome per unit of that predictor with all others held constant.

## Assumptions

In addition to the simple-regression assumptions, multicollinearity between predictors should be modest (variance inflation factor below about 5). Check leverage and Cook's distance for influential points.

## Hypotheses

For each predictor:
- H0: slope_j = 0
- H1: slope_j != 0
Joint F-test: H0 that all slopes are zero.

## Worked example (surgery — postoperative LOS modelled on age, ASA, operative time)

In 450 elective hip arthroplasties, postoperative LOS (days) was modelled on age (years), ASA grade (1-4), and operative time (minutes). VIFs were all below 2.

## Reporting

> "Length of stay rose by 0.04 days per year of age (95% CI 0.02 to 0.06, p<0.001), by 0.61 days per ASA grade increment (95% CI 0.41 to 0.81, p<0.001), and by 0.012 days per minute of operative time (95% CI 0.007 to 0.017, p<0.001). Adjusted R^2 = 0.31, F(3,446)=68.4, p<0.001."

## Pitfalls

- Don't run "predictor fishing" by adding variables until R^2 is high; correct for multiple testing or use a pre-specified model.
- A non-significant coefficient does not mean the predictor is unimportant — it may be confounded.

## Software

In the app: Statistics -> Regression -> Linear (multiple predictors).
