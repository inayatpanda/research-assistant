---
slug: welch-t-test
title: Welch's t-test (unequal variances)
family: comparison_of_means
when_to_use: Compare the means of two independent groups when the variances are unequal or sample sizes differ markedly.
assumptions:
  - Outcome is continuous
  - Approximately normal in each group (or large n)
  - Observations are independent
  - Variances may differ between groups (no equal-variance assumption)
alternatives:
  - independent-t-test
  - mann-whitney-u
worked_example_domain: medicine
worked_example_dataset: crp_two_antibiotic_regimens
related_concepts:
  - levenes-test
  - degrees-of-freedom-satterthwaite
---

# Welch's t-test

## When to use

Welch's t-test is the safer default for comparing means of two independent groups: it does not assume equal variances and is virtually identical to Student's t-test when variances happen to be equal. Use it whenever Levene's test is borderline, sample sizes are unequal, or there is biological reason to expect unequal spread.

## Assumptions

Normality in each group (or large enough samples that the CLT applies) and independence. Variances may differ. Degrees of freedom are estimated via the Satterthwaite approximation, so reported df is often non-integer.

## Hypotheses

- H0: mean(Group A) = mean(Group B)
- H1: mean(Group A) != mean(Group B)

## Worked example (medicine — CRP at 48h on two antibiotic regimens)

In a pragmatic trial of community-acquired pneumonia, CRP at 48 hours was 78 +/- 22 mg/L on regimen A (n=44) and 65 +/- 38 mg/L on regimen B (n=39). Levene's test was significant (p=0.01), so Welch's correction was applied.

## Reporting

> "Mean 48-hour CRP was 13 mg/L lower on regimen B (95% CI 1 to 25 mg/L; Welch's t(60.4)=2.08, p=0.041)."

## Pitfalls

- Don't pick Student's vs Welch's based on the p value Levene returns — many statisticians recommend Welch's by default.
- If outcomes are clearly skewed (e.g. CRP), consider a rank-based alternative.

## Software

In the app: Statistics -> t-test -> Independent (toggle "Equal variances" off).
