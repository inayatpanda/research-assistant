---
slug: rct-write-up
title: Writing up a randomised controlled trial
worked_example_domain: medicine
estimated_reading_minutes: 20
study_type: rct
related_concepts:
  - consort
  - ancova
  - independent-t-test
  - chi-square-independence
  - kaplan-meier-log-rank
  - cox-proportional-hazards
  - multiple-imputation
  - itt-analysis
  - cover-letter
  - picking-a-journal
  - authorship-criteria
sections:
  - Background and the dataset
  - Pre-analysis plan and registration
  - Building the CONSORT flow
  - Table 1 — baseline characteristics
  - Primary analysis — ITT and ANCOVA
  - Secondary analyses — time-to-event
  - Missing data and sensitivity
  - Writing against CONSORT 2025
  - Journal template and submission
---

# Writing up a randomised controlled trial

You ran a 12-month, double-blind, placebo-controlled trial of **lisinopril-style ACE inhibitor "ACEi-X" 10 mg daily versus placebo** in 412 adults with newly diagnosed stage-1 hypertension (clinic SBP 140–159 mmHg). Recruitment finished a month ago, the database is locked, and you have nine weeks to deliver the manuscript to your supervisor. This walkthrough takes you from data export to submission package using only what the app already gives you.

## Background and the dataset

Open the **Statistics** tab and upload the locked CSV. The columns the analysis plan calls for are:

- `subject_id`, `site_id`, `treatment` (1 = ACEi-X, 0 = placebo)
- `age`, `sex`, `ethnicity`, `bmi`, `smoker`, `diabetes`
- `sbp_baseline`, `dbp_baseline` (mean of two seated readings)
- `sbp_12wk`, `dbp_12wk`
- `sbp_12mo` (the primary outcome), `dbp_12mo`
- `serum_creatinine_12mo`, `potassium_12mo`
- `aes_any`, `aes_serious`, `aes_cough`, `aes_angioedema`
- `discontinued`, `discontinuation_reason`, `time_to_discontinuation_days`
- `time_to_major_event_days`, `major_event_observed` (composite MI/stroke/CV death)

Click into the dataset; the app will infer types. Override the `treatment`, `sex`, `ethnicity`, `smoker`, `diabetes` and outcome columns as **categorical** so analyses treat them correctly. Tag SBP/DBP and creatinine as continuous, time-to-event as duration in days.

## Pre-analysis plan and registration

Open the **Analysis Plan** card on the Statistics page. Paste the pre-registered Statistical Analysis Plan (SAP) — the trial was registered on ClinicalTrials.gov at study start, so what you do now must match the registered analyses. Anything you add later must be flagged as **post-hoc**.

The pre-specified plan reads:

1. **Primary**: 12-month change in clinic SBP, **ANCOVA** adjusted for baseline SBP, site, age.
2. **Key secondary**: 12-month DBP (same ANCOVA), proportion achieving SBP < 130 (chi-square / logistic), time to first major CV event (Cox).
3. **Safety**: rates of any AE, serious AE, cough, angioedema, creatinine rise > 30%, K+ > 5.5.
4. **Missing data**: primary uses **multiple imputation** (m = 20 chained equations). Sensitivity: tipping-point analysis and complete-case.
5. **Analysis population**: **modified intention-to-treat (mITT)** — all randomised who took at least one dose. The full ITT and per-protocol populations are sensitivity analyses.

Lock the plan. Once locked the app stamps every analysis you run with its registered identifier, which is what reviewers will check.

## Building the CONSORT flow

Switch to the **Figures** tab and open the **CONSORT diagram** widget. The five rows you fill in:

- **Assessed for eligibility**: 612.
- **Excluded**: 200 (reasons: didn't meet inclusion 142, declined 38, other 20).
- **Randomised**: 412 (206 ACEi-X / 206 placebo).
- **Allocated to intervention and received it**: 206 / 200 (six placebo participants did not receive any tablet).
- **Lost to follow-up / discontinued**: ACEi-X 14 (10 AE-related, 4 withdrew consent); placebo 9 (3 AE, 6 withdrew).
- **Analysed (mITT)**: ACEi-X 206 / placebo 200; with primary outcome available 198 / 191.

The diagram updates live as you tweak the boxes. Push it to **Figure 1** via the "Send to Figures" action.

## Table 1 — baseline characteristics

In the Statistics workbench, run a **Descriptive statistics by group** card. The grouping variable is `treatment`. Continuous variables (age, BMI, baseline SBP/DBP, baseline creatinine) appear as mean ± SD; categorical ones (sex, ethnicity, smoker, diabetes) appear as n (%). The app's defaults — no p-values in Table 1 — match modern CONSORT guidance. Tables in Table 1 should describe imbalance qualitatively rather than test for it.

Click **Push to Manuscript → Table 1**. The articles-table dialog lets you pick which columns to show and whether to format the table for Word, LaTeX, or both. The app remembers the choice so re-running the descriptive card later updates Table 1 in place.

## Primary analysis — ITT and ANCOVA

Open **New analysis → ANCOVA** in the wizard. Pick `sbp_12mo` as the outcome, `treatment` as the grouping factor, and `sbp_baseline`, `age`, `site_id` as covariates. Choose **Type III sum of squares** (the trial is balanced enough that Type I and Type III converge, but for an unbalanced trial Type III is the convention).

The result card shows:

- Adjusted mean (95% CI) per arm.
- Adjusted between-arm difference with 95% CI.
- F-statistic and the p-value.
- Per-assumption pills: linearity of the covariate, homogeneity of regression slopes (the critical assumption — the app fits an interaction model in the background and warns if the slopes differ), normality of residuals, equal variance.

For our example the adjusted difference is **−8.4 mmHg favouring ACEi-X (95% CI −10.6 to −6.2; p<0.001)**.

Run the same ANCOVA on `dbp_12mo` and `sbp_12wk`. For the secondary "proportion < 130 mmHg" outcome, open **New analysis → Logistic regression** with `treatment` and the same baseline adjustment set, and the report card will give you an odds ratio and 95% CI.

When the primary outcome would normally be analysed with an independent **t-test** — for example if the trial were not adjusted for baseline — you would pick that instead. The Learn entry on t-tests covers the assumption checks; the Learn entry on ANCOVA covers why it is preferred for parallel-group trials with a baseline.

## Secondary analyses — time-to-event

The composite CV-event endpoint is a survival outcome. Open **New analysis → Kaplan–Meier** with `time_to_major_event_days` as the time, `major_event_observed` as the event indicator, and `treatment` as the stratifier. The KM card shows the two survival curves, the log-rank p-value, the number at risk under the time axis, and the cumulative event counts.

Push the KM curve to Figure 2. Set the y-axis to "Cumulative incidence (%)" if the reviewer prefers that to "Event-free survival" — it inverts the curve but conveys the same information.

For the adjusted analysis run **Cox proportional hazards** with `treatment` plus age, sex, baseline SBP, smoking status. The result card prints the hazard ratio (e.g. HR 0.78, 95% CI 0.55–1.10) and runs the **Schoenfeld residuals** test for proportional hazards — if it fails (p<0.05), the card prompts you to refit using a time-varying coefficient or to switch to restricted-mean survival.

## Missing data and sensitivity

Click into the **Imputation** card and run **multiple imputation by chained equations (MICE)**, m = 20, using all baseline covariates plus the on-treatment values at 12 weeks (12wk SBP improves the imputation quality dramatically for the 12-month outcome).

After pooling via Rubin's rules, the app shows the adjusted difference with the imputation-pooled CI. Compare with the complete-case result. If the two differ by more than ~1 mmHg or by direction, you must discuss why.

Run a **tipping-point sensitivity analysis** — the app shifts the imputed values in the active arm by 0, 2, 4, 6 mmHg towards the placebo mean and reports how big a shift is needed to nullify the result. Report the shift in the methods and the supplementary appendix.

## Writing against CONSORT 2025

Switch to **Manuscript**. Pick the **RCT template**. The skeleton has every CONSORT 2025 item as an in-line comment in the section it belongs to, including the "registration number" tag in the methods opener and the "funding source" tag in the funding paragraph. Where a comment says "CONSORT 11a — interventions for each group", make sure the paragraph beneath actually describes both arms in detail.

Use the **CONSORT checklist** widget in the Submission tab to verify each item is ticked. When you click a ticked item it scrolls the manuscript to the relevant paragraph; when you click an unticked item the app prompts you for the manuscript line that satisfies it, then ticks it.

A few rules worth reinforcing because reviewers love to comment on them:

- Report **adjusted** primary effect with CI, not just p-value.
- Report **absolute** event rates per arm alongside any relative measure.
- Distinguish the **mITT** (analysis population) from the **safety** population in the body of every results paragraph.
- Sub-group analyses should be displayed as a forest plot with formal interaction p-values.
- A trial that stopped early for benefit should reference the data safety monitoring board's pre-specified stopping rule.

Switch the **Bibliography style** to **NEJM** in Settings. The first author surnames appear in small-caps; volume number is bold; the journal abbreviation follows the NLM list. The app's citation engine handles all three.

## Journal template and submission

NEJM, JAMA and The Lancet are the realistic aim-high targets for a moderate-sized trial of a re-purposed drug. NEJM in particular wants a precise structured abstract; the **Structured abstract** widget in Frontmatter has the NEJM field layout (Background, Methods, Results, Conclusions; with the trial registration number after Methods).

Authorship must satisfy **ICMJE** — three criteria, all four must be met: substantial contribution; drafting or critical revision; final approval; agreement to be accountable. The app's authorship-criteria radio set under Frontmatter enforces this; you cannot leave a name on the author list with only "drafting" checked.

Generate the **cover letter** via the Submission tab. The template references trial registration, CONSORT compliance, conflicts of interest, prior presentations, the corresponding author block, and a 3-sentence "why this trial matters" pitch. Edit the pitch — boilerplate cover letters get rejected at editorial triage.

Compile the **submission package**: title page (ICMJE-compliant authorship); abstract; main manuscript; CONSORT flow (Figure 1); KM curve (Figure 2); supplementary appendix containing the full SAP, the complete CONSORT checklist with line numbers, the imputation diagnostics, the per-site sensitivity analyses, and the protocol amendment history.

A final pre-flight check:

- Registration number visible in the methods opening line and on the title page.
- The two figures and three tables match the article references in the text.
- The data sharing statement (NEJM requires one) is in the frontmatter, not just the appendix.
- The conflict-of-interest declarations match the disclosure forms each author has signed.

Once the bundle exports clean, head to the journal portal. The reviewer-response editor will be empty until the first decision letter — at that point you'll come back and use the structured "comment → response → manuscript change" three-column format.

That is a complete trial write-up. A sister walkthrough in this Learn hub describes the same process for a meta-analysis of trials, and a third walkthrough covers an observational cohort using the STROBE checklist where the analysis discipline is similar but the bias risks are different.
