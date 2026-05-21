---
slug: chi-square-goodness-of-fit
title: Chi-square goodness-of-fit
family: categorical_association
when_to_use: Test whether the distribution of a single categorical variable matches a hypothesised set of proportions.
assumptions:
  - Variable is categorical
  - Observations are independent
  - Expected count in every category is at least 5
alternatives:
  - exact-multinomial-test
worked_example_domain: medicine
worked_example_dataset: clinic_referrals_by_specialty
related_concepts:
  - expected-counts
  - reference-distribution
---

# Chi-square goodness-of-fit

## When to use

Use this test to compare an observed distribution against an expected or theoretical one — for example, comparing the specialty mix of GP referrals at a new clinic against the national average, or comparing observed genotype counts against Hardy-Weinberg equilibrium.

## Assumptions

Each observation contributes to exactly one category, observations are independent, and the expected count under the null in every category is at least 5. With small expected counts, an exact multinomial test is preferable.

## Hypotheses

- H0: observed proportions equal the hypothesised proportions
- H1: at least one proportion differs

## Worked example (medicine — specialty mix of urgent GP referrals)

In a sample of 600 urgent referrals from one general practice, the breakdown was cardiology 210, respiratory 150, neurology 60, gastroenterology 120, other 60. The national reference proportions were 30%, 25%, 15%, 20%, 10%.

## Reporting

> "The clinic's referral mix differed significantly from the national reference (chi-squared(4)=22.0, p<0.001). Cardiology referrals were over-represented (35% observed vs 30% expected) and neurology referrals were under-represented (10% vs 15%)."

## Pitfalls

- The hypothesised proportions must be specified before looking at the data.
- A significant p value doesn't tell you which category drove the result; inspect standardised residuals.

## Software

In the app: Statistics -> Categorical -> Goodness of fit.
