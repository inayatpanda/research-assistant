---
slug: chi-square-independence
title: Chi-square test of independence
family: categorical_association
when_to_use: Test whether two categorical variables are independent in a contingency table.
assumptions:
  - Variables are categorical (nominal or ordinal treated as nominal)
  - Observations are independent
  - Expected count in every cell is at least 5
alternatives:
  - fisher-exact
  - g-test
worked_example_domain: surgery
worked_example_dataset: ssi_by_prophylaxis_type
related_concepts:
  - contingency-table
  - effect-size-cramer-v
---

# Chi-square test of independence

## When to use

Use this test for the relationship between two categorical variables — for example, whether the rate of surgical site infection (yes/no) depends on the antibiotic prophylaxis regimen (single dose vs extended). It compares observed counts in a contingency table to those expected under independence.

## Assumptions

Independent observations (one row per patient, never repeated measurements), categorical variables, and an expected count of at least 5 in every cell. If sparse cells violate that rule, use Fisher's exact test instead.

## Hypotheses

- H0: the two variables are independent
- H1: they are associated

## Worked example (surgery — SSI by antibiotic prophylaxis regimen)

In 320 elective colorectal resections, surgical site infection occurred in 22/160 (13.8%) of patients on single-dose prophylaxis and 12/160 (7.5%) on extended prophylaxis.

## Reporting

> "SSI rate was 13.8% on single-dose vs 7.5% on extended prophylaxis (chi-squared(1)=3.62, p=0.057, Cramer's V=0.11). The 95% CI for the absolute difference was -0.2% to 12.8%."

## Pitfalls

- Don't apply this test to paired binary data — use McNemar's instead.
- The chi-squared p value doesn't tell you the magnitude or direction; report rates and a confidence interval for the difference.

## Software

In the app: Statistics -> Categorical -> Chi-square.
