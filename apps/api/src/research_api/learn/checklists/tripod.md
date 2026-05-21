---
slug: tripod
title: TRIPOD — Prediction model studies
reporting_standard: TRIPOD
applies_to_study_types:
  - prediction model development
  - prediction model validation
  - combined development and validation
applies_to_study_types_short: Prediction model studies
version: "2015"
official_url: https://www.equator-network.org/reporting-guidelines/tripod-statement/
worked_example_domain: orthopaedics
related_concepts:
  - discrimination
  - calibration
  - shrinkage
  - external-validation
  - logistic-regression
  - cox-proportional-hazards
---

# TRIPOD reporting checklist (22 items)

## Scope

TRIPOD applies to studies developing, validating, or updating a multivariable prediction model — for either a diagnostic outcome (e.g. presence of fracture) or a prognostic outcome (e.g. 1-year revision risk). For machine-learning models prefer TRIPOD+AI (2024); the original 22-item TRIPOD remains valid for regression-based models.

## Key items the user must report

### Title and abstract
- [ ] 1. Title: identify the study as developing and/or validating a multivariable prediction model, the target population, and the outcome to be predicted.
- [ ] 2. Abstract: provide a summary of objectives, study design, setting, participants, sample size, predictors, outcome, statistical analysis, results, and conclusions.

### Introduction — background and objectives
- [ ] 3a. Explain the medical context (including whether diagnostic or prognostic) and rationale for developing or validating the multivariable prediction model, including references to existing models.
- [ ] 3b. Specify the objectives, including whether the study describes the development or validation of the model, or both.

### Methods
- [ ] 4a. Source of data: describe the study design or source of data (e.g. randomised trial, cohort, or registry data), separately for the development and validation data sets, if applicable.
- [ ] 4b. Specify the key study dates, including start of accrual; end of accrual; and, if applicable, end of follow-up.
- [ ] 5a. Participants: specify key elements of the study setting (e.g. primary care, secondary care, general population) including number and location of centres.
- [ ] 5b. Describe eligibility criteria for participants.
- [ ] 5c. Give details of treatments received, if relevant.
- [ ] 6a. Outcome: clearly define the outcome that is predicted by the prediction model, including how and when assessed.
- [ ] 6b. Report any actions to blind assessment of the outcome to be predicted.
- [ ] 7a. Predictors: clearly define all predictors used in developing or validating the multivariable prediction model, including how and when they were measured.
- [ ] 7b. Report any actions to blind assessment of predictors for the outcome and other predictors.
- [ ] 8. Sample size: explain how the study size was arrived at.
- [ ] 9. Missing data: describe how missing data were handled (e.g. complete-case analysis, single imputation, multiple imputation) with details of any imputation method.
- [ ] 10a. Statistical analysis methods: describe how predictors were handled in the analyses.
- [ ] 10b. Specify type of model, all model-building procedures (including any predictor selection), and method for internal validation.
- [ ] 10c. For validation, describe how the predictions were calculated.
- [ ] 10d. Specify all measures used to assess model performance and, if relevant, to compare multiple models.
- [ ] 10e. Describe any model updating (e.g. recalibration) arising from the validation, if done.
- [ ] 11. Risk groups: provide details on how risk groups were created, if done.
- [ ] 12. Development vs. validation: for validation, identify any differences from the development data in setting, eligibility criteria, outcome, and predictors.

### Results
- [ ] 13a. Participants: describe the flow of participants through the study, including the number of participants with and without the outcome and, if applicable, a summary of the follow-up time. A diagram may be helpful.
- [ ] 13b. Describe the characteristics of the participants (basic demographics, clinical features, available predictors), including the number of participants with missing data for predictors and outcome.
- [ ] 13c. For validation, show a comparison with the development data of the distribution of important variables (demographics, predictors and outcome).
- [ ] 14a. Model development: specify the number of participants and outcome events in each analysis.
- [ ] 14b. If done, report the unadjusted association between each candidate predictor and outcome.
- [ ] 15a. Model specification: present the full prediction model to allow predictions for individuals (i.e. all regression coefficients, and model intercept or baseline survival at a given time point).
- [ ] 15b. Explain how to use the prediction model.
- [ ] 16. Model performance: report performance measures (with CIs) for the prediction model.
- [ ] 17. Model-updating: if done, report the results from any model updating (i.e. model specification, model performance).

### Discussion
- [ ] 18. Limitations: discuss any limitations of the study (such as non-representative sample, few events per predictor, missing data).
- [ ] 19a. Interpretation: for validation, discuss the results with reference to performance in the development data, and any other validations.
- [ ] 19b. Give an overall interpretation of the results, considering objectives, limitations, results from similar studies, and other relevant evidence.
- [ ] 20. Implications: discuss the potential clinical use of the model and implications for future research.

### Other information
- [ ] 21. Supplementary information: provide information about the availability of supplementary resources, such as study protocol, web calculator, and data sets.
- [ ] 22. Funding: give the source of funding and the role of the funders for the present study.

## Common mistakes

- Reporting AUC alone with no calibration plot (item 16).
- Omitting the full regression equation, so others cannot apply the model (item 15a).
- Using stepwise selection without disclosing it (item 10b).
- For external validation, not comparing case-mix between development and validation cohorts (item 13c).

## How this maps to manuscript sections in our app

- Statistics -> Logistic / Cox regression coefficients table covers item 15a.
- Statistics -> Calibration plot + ROC curve covers item 16.
- Frontmatter -> Data availability covers item 21.
