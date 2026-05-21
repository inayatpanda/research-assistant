---
slug: levenes-test
title: Levene's test for equal variances
family: diagnostic
when_to_use: Test whether two or more groups have equal variances before running an equal-variance ANOVA or t-test.
assumptions:
  - Outcome is continuous
  - Observations are independent
  - Less sensitive to non-normality than Bartlett's test
alternatives:
  - bartlett-test
  - brown-forsythe
worked_example_domain: surgery
worked_example_dataset: blood_loss_variance_three_centres
related_concepts:
  - homoscedasticity
  - welch-correction
---

# Levene's test for equal variances

## When to use

Levene's test checks whether two or more groups have similar variances — an assumption of Student's t-test and the equal-variance ANOVA. Use it to decide whether to apply Welch's correction. It is fairly robust to non-normality, unlike Bartlett's test.

## Assumptions

Independent observations and a continuous outcome. Levene's test uses absolute deviations from the group mean (or median in the Brown-Forsythe variant), which makes it robust to mild departures from normality.

## Hypotheses

- H0: variances are equal across groups
- H1: at least one group's variance differs

## Worked example (surgery — intraoperative blood loss variance across three centres)

In a multicentre audit of 240 hepatectomies (80 per centre), blood loss (mL) variance was checked across centres before performing a between-centre ANOVA. Centre C had a clearly wider spread on inspection.

## Reporting

> "Variances differed across centres (Levene's F(2,237)=4.95, p=0.008). Welch's ANOVA was therefore used in place of the equal-variance ANOVA for the subsequent comparison of means."

## Pitfalls

- Don't make Levene's the gatekeeper of all variance-related decisions; Welch's t-test/ANOVA is often a safer default regardless of the Levene p value.
- A significant Levene with very large n can flag trivially small variance differences.

## Software

In the app: Statistics -> Diagnostics -> Levene's test.
