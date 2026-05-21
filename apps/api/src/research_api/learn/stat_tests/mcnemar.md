---
slug: mcnemar
title: McNemar's test
family: categorical_association
when_to_use: Compare two paired or matched binary outcomes (e.g. before vs after, or two diagnostic tests on the same patient).
assumptions:
  - Outcome is binary
  - Pairs are independent
  - Discordant pairs are the focus; concordant pairs cancel out
alternatives:
  - exact-binomial-on-discordant-pairs
worked_example_domain: surgery
worked_example_dataset: mri_vs_arthroscopy_paired
related_concepts:
  - paired-binary-design
  - diagnostic-test-agreement
---

# McNemar's test

## When to use

Use McNemar when the same subject contributes two binary measurements — for example, MRI positive/negative and arthroscopy positive/negative on the same knee, or symptom present before and after treatment. Only the discordant pairs (where the two measurements disagree) carry information about a possible shift.

## Assumptions

Pairs are independent of each other; binary outcomes; the marginal totals of discordant pairs are sufficient. With fewer than ~25 discordant pairs, use the exact binomial form.

## Hypotheses

- H0: the marginal proportions are equal across the two paired conditions
- H1: they differ

## Worked example (surgery — MRI vs diagnostic arthroscopy for meniscal tear)

In 120 patients with suspected meniscal tear, MRI and subsequent diagnostic arthroscopy were each classified positive or negative. The 2x2 table showed 65 both-positive, 30 both-negative, 18 MRI+/arthroscopy- and 7 MRI-/arthroscopy+.

## Reporting

> "MRI and arthroscopy disagreed in 25 of 120 cases. The proportion of MRI+ was 8.3% higher than arthroscopy+ (McNemar chi-squared(1)=4.84, p=0.028; exact 95% CI for the difference 1.0% to 16.0%)."

## Pitfalls

- A standard chi-square test on a 2x2 of paired counts is wrong — it ignores the pairing.
- Report the number of discordant pairs; this drives the test's power.

## Software

In the app: Statistics -> Categorical -> McNemar.
