---
slug: one-sample-t-test
title: One-sample t-test
family: comparison_of_means
when_to_use: Compare the mean of a single continuous sample to a known or hypothesised reference value.
assumptions:
  - Outcome is continuous
  - Approximately normal in the sample (or n large enough for CLT)
  - Observations are independent
alternatives:
  - wilcoxon-signed-rank
worked_example_domain: medicine
worked_example_dataset: ldl_cholesterol_clinic_vs_target
related_concepts:
  - reference-values
  - confidence-intervals
---

# One-sample t-test

## When to use

Use this test when you want to know whether a single sample mean differs from a fixed reference value — for example, comparing LDL cholesterol in a clinic cohort against a guideline target, or comparing average waiting time against a service-level threshold.

## Assumptions

The sample is independent and the outcome is approximately normal; for n > 30 the test is robust to moderate non-normality. The reference value must be specified a priori — not chosen from the data.

## Hypotheses

- H0: mean(sample) = mu_0
- H1: mean(sample) != mu_0

## Worked example (medicine — LDL cholesterol vs guideline target)

In 80 adults attending a lipid clinic, mean LDL cholesterol was 3.4 mmol/L (SD 0.9). The clinical target is 2.6 mmol/L.

## Reporting

> "Mean LDL cholesterol in the clinic cohort (3.4 +/- 0.9 mmol/L; n=80) was significantly higher than the 2.6 mmol/L target (mean difference 0.8 mmol/L, 95% CI 0.6 to 1.0; t(79)=7.95, p<0.001)."

## Pitfalls

- Don't pick the reference after seeing the data — that invalidates the test.
- A statistically significant difference may still be clinically trivial; always report the magnitude and CI.

## Software

In the app: Statistics -> t-test -> One sample.
