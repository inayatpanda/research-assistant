---
slug: friedman
title: Friedman test
family: non_parametric_comparison
when_to_use: Compare three or more related measurements on the same subjects when the outcome is ordinal or the within-subject differences are non-normal.
assumptions:
  - Outcome is at least ordinal
  - Subjects are independent
  - Each subject is measured at every time point or condition
alternatives:
  - repeated-measures-anova
  - linear-mixed-effects-model
worked_example_domain: surgery
worked_example_dataset: surgeon_workload_three_techniques
related_concepts:
  - rank-test
  - within-subjects-design
---

# Friedman test

## When to use

Friedman's test is the non-parametric counterpart of repeated-measures ANOVA. Use it when the same subjects are measured under three or more conditions and the outcome is ordinal or markedly skewed — for example, surgeons rating workload (NASA-TLX) after performing each of three operative techniques.

## Assumptions

Subjects are independent, each subject contributes a value for every condition (no missing data), and the outcome is at least ordinal. The test ranks values within each subject and compares those ranks across conditions.

## Hypotheses

- H0: the median is the same across conditions
- H1: at least one condition's median differs

## Worked example (surgery — surgeon-rated workload across three laparoscopic techniques)

Twenty consultant surgeons performed each of three laparoscopic suturing techniques in a within-subject simulator study, rating workload on the NASA-TLX (0-100) after each task. Medians were 38, 52, and 64.

## Reporting

> "NASA-TLX workload differed across techniques (Friedman chi-squared(2)=22.1, p<0.001). Wilcoxon signed-rank post-hoc tests with Bonferroni correction showed every pairwise comparison was significant (all adjusted p<0.05)."

## Pitfalls

- Friedman requires complete data per subject; missing values force you into a mixed model.
- Don't conflate "ordinal" with "categorical": Friedman is invalid for nominal outcomes.

## Software

In the app: Statistics -> Non-parametric -> Friedman.
