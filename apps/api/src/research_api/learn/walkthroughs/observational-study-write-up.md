---
slug: observational-study-write-up
title: Writing up a retrospective cohort study
worked_example_domain: surgery
estimated_reading_minutes: 18
study_type: observational_cohort
related_concepts:
  - strobe
  - propensity-score-matching
  - logistic-regression
  - multiple-linear-regression
  - cox-proportional-hazards
  - e-value
  - cover-letter
  - picking-a-journal
  - data-sharing-statements
  - reporting-guideline-selection
sections:
  - Background and the dataset
  - Defining the cohort and exclusions
  - Outcomes and covariates
  - Descriptive analysis — Table 1
  - Propensity-score matching
  - Primary analysis — adjusted logistic regression
  - Sensitivity — e-value and subgroup
  - Writing against STROBE
  - Journal template and submission
---

# Writing up a retrospective cohort study

A consultant has asked you to look at **30-day complications after elective laparoscopic cholecystectomy** in your hospital's surgical database, comparing patients aged ≥70 with those <70. There are 1,420 cases over a four-year window. You have eight weeks; the writing target is the British Journal of Surgery. The data are observational, so you must use STROBE for the write-up and you must address confounding head-on. This walkthrough covers the full pipeline.

## Background and the dataset

Open the **Statistics** tab and upload the CSV exported from the surgical audit database. The relevant columns:

- `patient_id`, `op_date`, `surgeon_id`, `consultant_grade`
- `age`, `age_ge70` (1/0), `sex`, `ethnicity`, `bmi`, `smoker`, `alcohol_units`
- `asa_grade` (1–4), `charlson_score`, `diabetes`, `cardiac_disease`, `copd`, `ckd_stage`
- `acute_or_elective` (this analysis restricts to elective)
- `indication` (biliary colic / chronic cholecystitis / polyp / other)
- `intraop_findings`, `conversion_to_open` (1/0), `operative_time_min`, `blood_loss_ml`
- `length_of_stay_days`, `readmission_30d` (1/0)
- `complication_30d` (1/0 — composite), and the sub-components: `bile_leak`, `bleed`, `wound_infection`, `port_site_hernia`, `vte`, `bile_duct_injury`
- `mortality_30d` (rare event — 7 deaths in the period)

Override `age_ge70`, `sex`, `ethnicity`, `smoker`, `asa_grade`, `diabetes`, `cardiac_disease`, `copd`, `ckd_stage`, `conversion_to_open`, `complication_30d`, `mortality_30d` to **categorical**. Keep `age`, `bmi`, `alcohol_units`, `charlson_score`, `operative_time_min`, `blood_loss_ml`, `length_of_stay_days` as continuous.

## Defining the cohort and exclusions

In **Data View**, build the exclusion stack as a transformation chain so the steps are reproducible:

1. Drop rows where `acute_or_elective` ≠ elective.
2. Drop rows where the operation was an attempted laparoscopy that was abandoned (you keep conversions to open because they are the result of the same procedure).
3. Drop rows where age is missing.
4. Drop rows where complication status is missing (a key outcome).

The transformation stack panel saves each step with a comment. After the four steps the cohort is 1,304 patients (584 ≥70, 720 <70). The flow diagram you build later in STROBE mirrors this chain.

## Outcomes and covariates

The primary outcome is the binary `complication_30d`. Secondary outcomes are `length_of_stay_days` (continuous, expect right-skew), `readmission_30d`, and the individual complication sub-components. Mortality is too rare for inference but is tabulated.

Pre-specify your covariates: age, sex, BMI, ASA grade, Charlson score, diabetes, cardiac disease, COPD, CKD stage, surgeon experience grade, and operative time. Operative time is on the **causal pathway** between age and complications (older patients have longer operations), so you must not adjust for it in the primary analysis. Save it for a sensitivity analysis.

## Descriptive analysis — Table 1

Run **Descriptive statistics by group** with `age_ge70` as the grouping variable. Continuous variables: mean ± SD or median (IQR) depending on skew (the app flags it via Shapiro-Wilk). Categorical: n (%). Add **standardised mean differences (SMD)** to Table 1 instead of p-values — observational data with thousands of patients gives trivially significant p-values even for clinically irrelevant differences. An SMD > 0.1 flags meaningful imbalance.

For our cohort the older group is heavier on Charlson (3.1 vs 1.2, SMD 1.0), ASA grade (62% ASA 3+ vs 23%, SMD 0.86), cardiac disease (38% vs 11%, SMD 0.66), diabetes (24% vs 12%, SMD 0.31), and operative time (78 min vs 65 min, SMD 0.40). Everything above SMD 0.1 enters the adjustment / matching model.

Push Table 1 into the manuscript via the articles-table dialog.

## Propensity-score matching

The imbalance forces you to do more than naïve regression. Open **PSM Wizard** in the Statistics workbench.

- **Treatment**: `age_ge70`.
- **Covariates in the propensity model**: sex, BMI, ASA grade, Charlson score, diabetes, cardiac disease, COPD, CKD stage, smoker. (Do not include the outcome or the operative time.)
- **Matching method**: 1:1 nearest-neighbour without replacement, caliper 0.2 × SD of the logit.

The wizard fits a logistic regression of `age_ge70` on the covariates, predicts each patient's propensity score, and pairs each older patient with the closest younger patient. After matching, 510 pairs survive (1,020 patients).

The wizard then prints **balance diagnostics**: SMDs in the matched cohort, the standardised box-plot of propensity, the distribution of the score across the two arms. Every SMD should be < 0.1 post-match. If any remains > 0.1, refit including an interaction term or use exact matching on that covariate.

The matched cohort becomes a new dataset in the Library. From now on all primary analyses run on the matched cohort; the full cohort is a sensitivity analysis.

## Primary analysis — adjusted logistic regression

Open **New analysis → Logistic regression** on the matched dataset. Outcome `complication_30d`, predictor `age_ge70`. Even after matching, residual imbalance can remain, so include the same covariates as the propensity model in the outcome model — "doubly robust" adjustment.

The result card prints:

- Adjusted odds ratio (95% CI), e.g. **OR 1.86 (1.32–2.62) for age ≥70**.
- The likelihood-ratio test p-value.
- A pseudo-R² (McFadden).
- Hosmer-Lemeshow goodness-of-fit p-value.
- A forest plot with one row per covariate so you can describe the adjusted effect of each.

For length-of-stay (continuous, right-skew), do a **multiple linear regression** on log-transformed LOS with the same covariates. Back-transform the coefficient on `age_ge70` to get a **geometric mean ratio** (e.g. 1.21, 95% CI 1.12–1.31 — older patients stay 21% longer).

For 30-day readmission, repeat the logistic regression.

If you wanted time to first complication you would switch to **Cox proportional hazards** with time-from-operation to event/censoring. Test proportional hazards via Schoenfeld residuals; if it fails, present cumulative incidence functions instead.

## Sensitivity — e-value and subgroup

Open the **Sensitivity** card. Run the **E-value** for the primary effect. The E-value answers: how strong would an unmeasured confounder need to be to nullify the observed OR? For OR 1.86 the E-value on the point estimate is about 3.1 and on the lower CI is about 1.97. Report both. State that confounders such as informal sarcopenia, frailty index, or anti-coagulant use could plausibly reach these strengths, so the finding is not entirely robust.

Run pre-specified **subgroup analyses**: by ASA grade (1–2 vs 3+), by sex, by surgeon experience (consultant vs registrar). Each subgroup forest plot shows the per-group adjusted OR with interaction p-values. Do not chase interactions that were not pre-specified.

Run a **complete-case** sensitivity to check the matched analysis isn't an artefact of how you handled missing data. If you used multiple imputation for any missing covariate (CKD stage often has missingness), report the imputation diagnostics.

## Writing against STROBE

Switch to the **Manuscript** tab. Pick the **observational-study template** — the headings map onto STROBE: Introduction (rationale, objectives, hypotheses), Methods (study design, setting, participants, variables, data sources, bias, study size, quantitative variables, statistical methods, sensitivity), Results (descriptive, outcome, main results, other analyses), Discussion (key results, limitations, interpretation, generalisability), and the Other-information block (funding, registration if applicable).

The **STROBE checklist** widget under the Submission tab has all 22 items. Click each one when you have written the corresponding paragraph; click an unticked item to get a pop-up asking which line satisfies it.

Several items earn extra reviewer attention:

- **Bias (item 9)** — describe efforts to address selection bias (the inclusion criteria filter), information bias (database completeness), and confounding (PSM + adjustment).
- **Study size (item 10)** — for a single-centre audit you can't pre-specify a power calculation, but state the available sample size and its implication for the precision of your CIs.
- **Quantitative variables (item 11)** — every continuous covariate should be reported as you analysed it, not "categorised for convenience".
- **Statistical methods (item 12)** — describe the propensity model, the matching method and caliper, the adjustment set, the missing-data approach, and the sensitivity analyses.
- **Generalisability (item 21)** — your single-centre cohort generalises to other centres with a similar case mix; mention what would change in a higher-acuity setting.

Set the **bibliography style** to **British Journal of Surgery** in Settings → Citation style.

## Journal template and submission

BJS uses Vancouver, has a structured abstract, asks for an in-line statement of ethics approval, a data sharing statement, and explicit STROBE compliance. The journal template in the Submission tab provides each of these scaffolds.

Open the **Cover letter** editor. State that the study is a single-centre retrospective cohort, that you have complied with STROBE, the period the data span, the institutional approval reference, and that no funding or commercial interests apply. Keep it under one page.

Compile the **submission package**: title page (ICMJE authorship), structured abstract, main manuscript, STROBE flow figure (Figure 1), KM curve or forest plot (Figure 2), Table 1, Table 2 (matched-cohort balance), and the supplementary appendix with the propensity-score model, balance diagnostics, E-value calculation, subgroup forest plot, sensitivity analyses, and the data-extraction syntax exported as a .syntax file.

Pre-flight checks:

- The cohort numbers in the figure match the text and the tables.
- "Limitations" explicitly names residual confounding, single-centre design, and the retrospective nature.
- The data-sharing statement is more specific than "available on request" — name the local research office and a contact e-mail.
- The conflict-of-interest declaration matches each author's ICMJE form.

That covers the observational pathway. The corresponding RCT walkthrough in this Learn hub handles trial-specific items (CONSORT, ITT, blinding), and the systematic-review walkthrough covers what happens when you pool multiple observational studies.

## After the first decision

If BJS comes back with major revisions, the reviewer-response editor in the Submission tab walks you through every comment in a three-column structure: comment, response, manuscript change with line number reference. Reviewers in observational research will reliably ask three questions: (1) what stops residual confounding from explaining your result? — point to the E-value paragraph and the propensity model balance table; (2) why pick this matching method? — point to the methods justification and the sensitivity using inverse-probability weighting; (3) is the cohort generalisable? — point to the discussion paragraph on case-mix.

When you accept a reviewer suggestion that changes the analysis (for example, "add operative duration to the adjustment set"), re-run the analysis card, push the updated result back to the manuscript, then snapshot the manuscript via the Snapshots panel before sending the revised version. Snapshots are versioned, diffable, and round-trip through bundle export — invaluable if a reviewer later disputes what changed between rounds.

If the journal rejects without revision, open the Submission tab again and use the **Journal selection** helper. The picker filters by impact factor, scope, average time to first decision, and APC. Switch the bibliography style with one click and re-export the package; the actual manuscript prose generally needs only minor adjustments (abstract length, structured-abstract field names) between journals in the same field. A good fallback set for a single-centre cohort in general surgery is BJS Open, Annals of Surgery (if the cohort is large enough), Surgery, World Journal of Surgery, and the open-access surgical sub-specialty titles.
