---
slug: icc
title: Intraclass correlation coefficient (ICC)
family: agreement_reliability
when_to_use: Quantify the reliability of measurements by two or more raters (or repeated measurements) on the same subjects.
assumptions:
  - Continuous measurements
  - Subjects are independent
  - Choose the right ICC form (one-way / two-way; absolute agreement vs consistency; single rater vs average)
alternatives:
  - cohens-kappa
  - bland-altman
worked_example_domain: orthopaedics
worked_example_dataset: inter_rater_xray_oa_grading
related_concepts:
  - inter-rater-reliability
  - test-retest
  - shrout-fleiss-types
---

# Intraclass correlation coefficient (ICC)

## When to use

Use the ICC when several raters or repeated measurements assess the same continuous quantity and you want a single number for how consistent they are — for example, two radiologists grading osteoarthritis severity from knee X-rays, or repeated radiographic measurements of leg length discrepancy.

## Assumptions

Independent subjects and continuous measurements. Crucially, pick the right ICC form (Shrout & Fleiss, or McGraw & Wong): one-way vs two-way model, absolute agreement vs consistency, and single-rater vs average-of-raters. Misreporting the form is the most common ICC error.

## Hypotheses

ICC is reported as an estimate with a 95% CI rather than a hypothesis test. Conventional benchmarks: <0.5 poor, 0.5-0.75 moderate, 0.75-0.9 good, >0.9 excellent.

## Worked example (orthopaedics — inter-rater reliability of Kellgren-Lawrence grading on knee X-rays)

Two consultant radiologists each graded the same 80 weight-bearing knee radiographs on the 0-4 KL scale. A two-way random-effects, absolute-agreement, single-measure model was selected.

## Reporting

> "Inter-rater reliability between the two radiologists for KL grading was good (ICC(2,1) = 0.81, 95% CI 0.73 to 0.87, n=80)."

## Pitfalls

- Always state the exact ICC form; an ICC(1,1) and ICC(3,k) can differ markedly on the same data.
- A high ICC across a narrow range of subjects is misleading — sample diverse subjects to estimate reliability properly.

## Software

In the app: Statistics -> Agreement -> ICC (choose model).
