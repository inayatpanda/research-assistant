---
slug: pearson-correlation
title: Pearson correlation
family: correlation_regression
when_to_use: Quantify the strength and direction of a linear relationship between two continuous variables.
assumptions:
  - Both variables are continuous
  - Relationship is approximately linear
  - Bivariate normality
  - No strong outliers
alternatives:
  - spearman-correlation
  - kendall-tau
worked_example_domain: orthopaedics
worked_example_dataset: bmd_vs_hip_axis_length
related_concepts:
  - scatterplot
  - linear-relationship
  - r-squared
---

# Pearson correlation

## When to use

Pearson's r measures the linear association between two continuous variables. Use it when both variables are roughly normal, the scatterplot looks linear, and there are no extreme outliers — for example, bone mineral density (BMD) versus hip axis length in osteoporosis screening.

## Assumptions

Both variables are continuous and approximately normally distributed, the relationship is linear (always plot the data first), and there are no influential outliers. Pearson's r is extremely sensitive to single extreme points.

## Hypotheses

- H0: rho = 0
- H1: rho != 0

## Worked example (orthopaedics — femoral neck BMD vs hip axis length)

In 150 postmenopausal women undergoing DXA, femoral neck BMD (g/cm^2) and hip axis length (mm) were recorded. The scatterplot showed a moderate negative linear association with no obvious outliers.

## Reporting

> "Femoral neck BMD was inversely correlated with hip axis length (r = -0.36, 95% CI -0.49 to -0.21, p<0.001, n=150). Hip axis length explained roughly 13% of the variance in BMD (R^2 = 0.13)."

## Pitfalls

- A high r does not imply causation, nor a clinically meaningful effect.
- A non-significant r can hide a real non-linear relationship — always look at the scatterplot.

## Software

In the app: Statistics -> Correlation -> Pearson.
