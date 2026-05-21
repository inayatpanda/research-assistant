---
slug: meta-analysis-walkthrough
title: Running a focused meta-analysis
worked_example_domain: orthopaedics
estimated_reading_minutes: 19
study_type: meta_analysis
related_concepts:
  - prisma
  - rob2
  - grade
  - cinema
  - cochrane-handbook
  - heterogeneity
  - publication-bias
  - meta-regression
  - cover-letter
  - picking-a-journal
sections:
  - Scope and the included studies
  - Library and effect size extraction
  - Choosing the model — fixed vs random
  - Forest plot and heterogeneity
  - Subgroup analysis and meta-regression
  - Sensitivity — leave-one-out and small-study bias
  - GRADE / CINeMA certainty
  - Writing the meta-analysis section
  - Submission to BJSM
---

# Running a focused meta-analysis

You already have the included studies — that work was done in a sister project. Your task is to run the pooled analysis for **early (≤2 weeks) versus delayed (≥6 weeks) weight-bearing after Achilles tendon repair**, write the meta-analysis section, and submit to the British Journal of Sports Medicine (BJSM). The protocol is registered, the search and screening are finished, and 12 RCTs (1,608 patients) have made the final cut. The outcomes are: re-rupture rate, Achilles Tendon Total Rupture Score (ATRS) at 12 months, return-to-sport rate, and complication composite (DVT/skin/sural neuropraxia). This walkthrough takes you from imported effect sizes to a polished BJSM manuscript.

## Scope and the included studies

Open the **Systematic Review** tab and load the project. The 12 RCTs already appear in the Extraction table. Run the **PRISMA flow** widget — the box-counts (identified, deduped, screened, full-text assessed, included) should already match what your protocol said. Push the diagram to **Figure 1**.

Open the **Risk of Bias** card to confirm RoB 2.0 is the chosen tool. Verify the traffic-light figure renders: most cells should be green or yellow; one or two trials may be high-risk for blinding (orthotic-versus-cast trials cannot blind patients). Push the RoB summary figure to the Figures workspace as **Figure 2**.

## Library and effect size extraction

Switch to **Meta-analysis**. The Extraction table feeds the Per-Study Inputs panel. For each of the 12 studies, you need the right effect-size shape per outcome:

- **Re-rupture (binary)**: events in early arm / total; events in delayed arm / total. The app computes **log risk ratio** and its SE under Mantel–Haenszel by default.
- **ATRS at 12 months (continuous)**: mean ± SD per arm and n per arm. The effect measure is **mean difference** (the same instrument and scale across studies).
- **Return-to-sport (binary)**: events and totals, log RR.
- **Complication composite (binary)**: events and totals, log RR.

If a trial reports an effect estimate without raw counts, click "Solve for SE from CI" and confirm the imputation flag. If it reports median + IQR for ATRS, use the Wan / Hozo conversion — the app marks the row as **approximate**. If a trial pre-randomised and then lost a few patients in each arm, use the as-randomised denominators for the intention-to-treat synthesis, not the per-protocol numbers.

## Choosing the model — fixed vs random

Toggle between **Fixed-effect** and **Random-effects** on the meta-analysis card. The distinction matters in your write-up:

- **Fixed-effect (Mantel–Haenszel for binary, inverse-variance for continuous)** assumes one true effect across studies; differences are sampling error only. Use only when between-study variance τ² is genuinely near zero — rare in clinical interventions across centres with varying populations.
- **Random-effects (DerSimonian–Laird default; the app also offers REML, Paule–Mandel, and Hartung–Knapp adjusted CIs)** assumes the per-study true effects are drawn from a distribution. The pooled estimate is the mean of that distribution; the 95% CI is wider, especially with high heterogeneity.

For Achilles weight-bearing, recommend **random-effects with the Hartung–Knapp adjustment**. That choice should be stated in your protocol and reflected in the manuscript methods.

## Forest plot and heterogeneity

Open the forest plot. Per outcome, the picture for our worked example looks like:

- **Re-rupture**: pooled RR 0.94 (95% CI 0.62–1.42, I² 0%, τ² 0, Q-p 0.84). No heterogeneity; effects are statistically indistinguishable from null.
- **ATRS at 12 months**: pooled MD 4.6 points favouring early (95% CI 1.8 to 7.4, I² 38%, τ² 5.1, 12 trials, 1,492 patients). Statistically and clinically meaningful — MCID for ATRS is ~7 points so the lower CI sits below MCID.
- **Return-to-sport**: pooled RR 1.21 favouring early (95% CI 1.06–1.39, I² 12%).
- **Complication composite**: pooled RR 0.78 favouring early (95% CI 0.55–1.10, I² 5%).

Read the heterogeneity statistics carefully:

- **I²** — proportion of total variance due to between-study heterogeneity rather than sampling error. <25% low, 25–50% moderate, 50–75% substantial, >75% considerable.
- **τ²** — the actual between-study variance on the effect-size scale. A non-zero τ² with small I² can still matter if the studies are imprecise; conversely a high I² with tight CIs around it deserves more attention than a high I² with wide CIs.
- **Q statistic and its p-value** — Cochran's chi-square test of heterogeneity. It is underpowered with few studies, so do not rely on the p-value alone.
- **Prediction interval** — the 95% interval within which the effect of a *future* trial would be expected to fall. Always wider than the CI; the app shows it as a dashed band around the summary diamond. A prediction interval that crosses zero, even when the CI does not, is the right cue for tempered claims.

Push the forest plots to Figures 3a–3d.

## Subgroup analysis and meta-regression

You pre-specified two subgroup analyses: by acute versus chronic rupture, and by surgical technique (open vs percutaneous). Click **Subgroup analysis**, pick the moderator, and the forest plot re-renders with sub-totals and an interaction p-value.

For our example the percutaneous subgroup shows a slightly larger ATRS benefit (MD 6.1 vs 3.5), but the interaction p is 0.31 — not convincing evidence of effect modification. State the subgroup finding as exploratory.

If you want to investigate a continuous moderator (e.g. mean age across trials), run **meta-regression**. The app fits an inverse-variance weighted regression with restricted maximum likelihood and reports the residual heterogeneity. With only 12 trials, meta-regression is power-limited — flag any meta-regression finding as hypothesis-generating, not confirmatory.

## Sensitivity — leave-one-out and small-study bias

Click **Leave-one-out**. The card refits the meta-analysis 12 times, each time omitting one study. The output is a forest plot of pooled estimates with each study removed. If one trial dominates (very large weight, like a multi-centre 600-patient trial), check that the pooled effect is not solely driven by it.

Click **Cumulative meta-analysis**. The card pools the trials chronologically. This shows when the evidence "tipped" and is reviewer-friendly when describing how the field reached its current consensus.

For **publication bias**, check the **funnel plot**. With 12 trials the visual asymmetry test is the primary cue; the formal **Egger's regression test** can be reported with its caveat that ≥10 studies is the bare minimum and the test is under-powered. If the funnel is asymmetric and the test is borderline, add a **trim-and-fill** sensitivity — the card imputes hypothetical missing studies and recomputes the pooled estimate.

## GRADE / CINeMA certainty

Switch to the **GRADE** tab. For each outcome the starting certainty is **high** because every study is an RCT. Walk through the five downgrade domains:

- **Risk of bias** — for the ATRS outcome, the weight from high-RoB trials matters. If <25% of weight comes from high-risk studies, do not downgrade. The traffic-light figure makes the calculation transparent.
- **Inconsistency** — I² is 38% with a prediction interval that crosses MCID. Downgrade one level.
- **Indirectness** — the studies are in adults with primary Achilles rupture, exactly the population you care about. Do not downgrade.
- **Imprecision** — the lower CI sits at MD 1.8, well below MCID 7. Downgrade one level for imprecision; the effect could be clinically negligible.
- **Publication bias** — funnel is symmetric, Egger p 0.42. Do not downgrade.

Result: ATRS certainty is **low** (two downgrades). Repeat for the other outcomes. Re-rupture you would call **moderate** (downgraded once for imprecision around the no-effect estimate). Return-to-sport is **moderate** (one downgrade for inconsistency from sub-group exploration). Complications **moderate** (one downgrade for imprecision).

If your unit prefers **CINeMA** for confidence, the same downgrade logic applies but the rating is "confidence in the network estimate" rather than certainty. The Learn entry on CINeMA explains the differences.

The app generates the **Summary of Findings** table — push it into the manuscript as Table 1.

## Writing the meta-analysis section

Switch to the **Manuscript** tab. Pick the **meta-analysis template**. The Methods section has slots for: protocol registration, eligibility, search strategy reference, data extraction, RoB tool, effect-size measures, pooling method, heterogeneity assessment, sub-group/meta-regression plan, sensitivity plan, publication-bias plan, GRADE.

In Results, write one paragraph per primary outcome:

> "Across 12 trials (n = 1,608), early weight-bearing reduced 12-month ATRS by a pooled mean difference of 4.6 points (95% CI 1.8 to 7.4; I² 38%, τ² 5.1; 95% prediction interval −2.4 to 11.6; moderate-to-low certainty by GRADE) compared with delayed weight-bearing. The prediction interval crosses the minimal clinically important difference of 7 points, indicating uncertainty about whether the benefit would replicate in a new trial."

Use the visible figref menu to insert "Figure 3a", "Figure 3b" etc. — numbering is auto-maintained. The articles-table dialog inserts a study-characteristics table directly from the Extraction table; you do not transcribe it by hand.

Switch the **Bibliography style** to **British Journal of Sports Medicine** in Settings → Citation style. BJSM uses Vancouver with full journal names; the app's citation engine handles it.

## Submission to BJSM

Open the **Submission** tab. BJSM specifically asks for the PRISMA 2020 checklist as a supplementary file. The Submission tab attaches it automatically when you tick "PRISMA-compliant" in the package configuration.

Generate the cover letter — emphasise the clinical question, the registration ID, the AMSTAR-2-grade methodological rigour of your review, and the novelty (no recent meta-analysis on this exact comparison). The submission packager compiles: title page, structured abstract, manuscript, PRISMA flow (Figure 1), RoB summary (Figure 2), forest plots (Figures 3a–3d), funnel plot (Figure 4), Summary-of-Findings table (Table 1), study-characteristics table (Table 2), and a supplementary appendix containing the full search strategy, the per-domain RoB rationale, the leave-one-out plot, the cumulative meta-analysis, the meta-regression output, and the PRISMA 2020 checklist.

Pre-flight checks:

- Numbers in PRISMA flow match the text.
- Each forest plot legend names the model (random-effects, DerSimonian–Laird with Hartung–Knapp).
- The GRADE certainty in the abstract matches the SoF table.
- Conflicts of interest, funding, and data-sharing statement are in Frontmatter.

That is a full focused meta-analysis. If you have not done the screening yourself, the systematic-review walkthrough in this Learn hub picks the story up earlier; if your data are individual-participant rather than aggregate, the analysis becomes a mixed-effects model and the Learn entry on mixed-effects covers it.
