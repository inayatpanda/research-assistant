---
slug: bland-altman
title: Bland-Altman analysis (agreement)
family: agreement_reliability
when_to_use: Quantify agreement between two methods of measuring the same continuous quantity.
assumptions:
  - Continuous measurements on a comparable scale
  - Differences are approximately normal (for the limits of agreement)
  - Variance of differences is roughly constant across the range
alternatives:
  - icc
  - deming-regression
worked_example_domain: orthopaedics
worked_example_dataset: radiology_vs_intraop_femur_neck_angle
related_concepts:
  - limits-of-agreement
  - bias
  - method-comparison
---

# Bland-Altman analysis

## When to use

Bland-Altman is the standard graphical method for comparing two ways of measuring the same continuous quantity — for example, a pre-operative CT measurement of femoral neck angle compared with intraoperative navigation. It plots the difference between methods against their mean and reports the bias and 95% limits of agreement.

## Assumptions

Both measurements should be on the same scale and approximately continuous. The differences should be roughly normal and have constant variance across the range; if variance grows with the mean, transform (e.g. log) before computing limits.

## Hypotheses

Bland-Altman is not a hypothesis test — it estimates: (1) the bias (mean difference) and (2) the 95% limits of agreement (mean +/- 1.96 SD of differences).

## Worked example (orthopaedics — CT-measured vs intraoperative femoral neck-shaft angle)

In 60 patients undergoing hip preservation surgery, the femoral neck-shaft angle was measured pre-operatively on CT and intraoperatively with computer navigation. The mean difference (CT - intraop) was -1.2 degrees with SD 2.8.

## Reporting

> "CT systematically underestimated the intraoperatively measured angle by 1.2 degrees; the 95% limits of agreement were -6.7 to 4.3 degrees, n=60."

## Pitfalls

- Don't report Pearson's r as evidence of agreement — two methods can correlate perfectly yet differ by a constant.
- The clinical acceptability of the limits of agreement is a judgement call; pre-specify what counts as acceptable.

## Software

In the app: Statistics -> Agreement -> Bland-Altman.
