---
slug: systematic-review-from-scratch
title: Running a systematic review from scratch
worked_example_domain: orthopaedics
estimated_reading_minutes: 22
study_type: systematic_review
related_concepts:
  - prisma
  - moose
  - cochrane-handbook
  - rob2
  - grade
  - cinema
  - mesh
  - cover-letter
  - picking-a-journal
  - reporting-guideline-selection
sections:
  - PICO and the protocol
  - Search strategy
  - Title and abstract screening
  - Full text screening and exclusion log
  - Risk of bias assessment
  - Data extraction and effect sizes
  - PRISMA flow and dedup
  - Meta-analysis and heterogeneity
  - GRADE certainty
  - Writing the manuscript
  - Submission and reporting
---

# Running a systematic review from scratch

You are a third-year orthopaedic resident with a clinical question that has been bothering you: **does anterior cruciate ligament (ACL) reconstruction with a hamstring autograft give better two-year patient-reported outcomes than with a bone–patellar tendon–bone (BPTB) autograft in adults under 35?** A consultant on your unit asked if you could put together a systematic review for the next sub-specialty meeting. You have nine weeks. This walkthrough takes that question end-to-end through the app — protocol, search, screening, extraction, synthesis, manuscript and submission.

## PICO and the protocol

Open the **Systematic Review** tab. The first thing the app asks for is your PICO: Population, Intervention, Comparator, Outcomes. Be specific. Fill in:

- **P**: skeletally mature adults aged 18–35 undergoing primary ACL reconstruction.
- **I**: hamstring (semitendinosus ± gracilis) autograft.
- **C**: bone–patellar tendon–bone (BPTB) autograft.
- **O (primary)**: IKDC subjective score at 24 months.
- **O (secondary)**: KOOS sport/recreation, graft re-rupture rate, donor-site morbidity, anterior knee pain on kneeling.

Beneath PICO is the **Protocol** card. Use the PROSPERO helper (it is right next to the PICO box) to generate a draft of every field PROSPERO asks for: review title, anticipated review start/end, named team members, inclusion/exclusion criteria, planned databases and limits, planned analysis. Export the draft as a `.txt` block and paste it into the PROSPERO web form — the app does not register on your behalf because the registry requires a real e-mail signature.

While you are still in the protocol stage, decide which reporting guideline you will follow. Open the **Learn** hub and read the entry on PRISMA 2020 — it is the standard for an intervention review, so you will end up writing against the 27-item checklist. If your review were of observational studies you would follow MOOSE instead.

## Search strategy

Switch to the **Search log** card under the Systematic Review tab. The minimum is three databases: **PubMed**, **Embase** and the **Cochrane CENTRAL** trial register. You can add CINAHL or SPORTDiscus if you want to be comprehensive — for a knee surgery review most of the yield comes from the big three.

Write the PubMed query with explicit MeSH and free-text terms. The app's MeSH expansion button takes a seed term like "Anterior Cruciate Ligament Reconstruction" and pulls in the exploded MeSH tree plus common synonyms:

```
("Anterior Cruciate Ligament Reconstruction"[MeSH] OR
 "ACL reconstruction"[tiab] OR "ACLR"[tiab])
AND
("Tendons/transplantation"[MeSH] OR "hamstring"[tiab] OR
 "semitendinosus"[tiab] OR "patellar tendon"[tiab] OR "BPTB"[tiab])
AND
("Random Allocation"[MeSH] OR "Clinical Trial"[Publication Type] OR
 randomi*[tiab] OR "controlled trial"[tiab])
```

Save the query in the Search log along with the date you ran it, the number of hits (say 1,742) and the file you uploaded — the app stores PubMed XML, Embase `.ris` and Cochrane `.bib` natively. The Library tab will pick them all up as the same article shape.

Run the equivalent search in Embase via the Emtree mapping suggestions and in Cochrane CENTRAL via its built-in operators. Drop each export into the Library. Use the **Deduplicate** action — it matches on DOI first, then on (last-name-first-author + year + title-similarity ≥ 0.92). Expect about 28% removed; you should end up around 1,260 unique records.

## Title and abstract screening

The Library defaults to a screening view once it sees the records came from a search log. Each record gets three radio actions: **Include**, **Exclude**, **Maybe**. The AI suggestion panel on the right uses your PICO to propose a label — read its reasoning before accepting, especially when it suggests Exclude.

Aim for two independent reviewers. The app supports a "blind" mode that hides your colleague's decisions until both have voted; conflicts then appear in a queue for adjudication. If your colleague drops out (the resident below you might be on call), you can switch to single-reviewer mode but you must declare that as a methodological limitation in the manuscript.

Title-abstract typically reduces 1,260 to about 110.

## Full text screening and exclusion log

For each of the 110 records, click **Get full text**. The app tries the open-access PDF first, then the local proxy if you have one configured in Settings, and finally surfaces a "manual upload" slot if neither hits. Read the PDF inside the **Reader** tab — highlight outcomes, sample size, follow-up duration, and graft details.

Exclusions at full-text must be **logged with a reason**, because PRISMA requires you to publish that table. The app prompts you for one of: wrong population (paediatric, revision, multi-ligament), wrong intervention, wrong comparator, wrong outcome, wrong study design (case series, registry, single-arm cohort), or duplicate. Aim for a final yield of 14 RCTs.

## Risk of bias assessment

Open the **Risk of Bias** card. For RCTs in 2026 use **RoB 2.0** — pick it from the tool picker (the alternatives are ROBINS-I for non-randomised studies, AMSTAR-2 for reviews-of-reviews, and the JBI tools for prevalence and qualitative work).

RoB 2.0 has five domains: randomisation, deviations from intended interventions, missing outcome data, measurement of the outcome, and selection of the reported result. Each is graded **low**, **some concerns**, or **high**. The app stores per-domain comments and auto-generates the **traffic-light summary figure**. You will paste that figure into the manuscript later.

## Data extraction and effect sizes

The **Extraction table** is the workhorse. The columns are pre-seeded from your PICO. For each of the 14 trials, record:

- Study ID, country, recruiting centres, funding source.
- Total randomised, mean age, female%, BMI.
- Time to surgery, mean follow-up.
- Mean ± SD IKDC at 24 months for each arm.
- Re-rupture events (n/N) at last follow-up.
- KOOS-sport mean ± SD.
- Anterior knee pain on kneeling (n/N).

If a study reports median + IQR, click the "Convert" affordance — the app applies the Wan / Hozo formulas to estimate mean and SD with a warning that this is an approximation. If a study reports only an effect estimate, click "Solve for SD from CI". Always tag the row as **imputed** so the meta-analysis can run a sensitivity analysis later.

## PRISMA flow and dedup

The **PRISMA flow** chart in the Figures tab populates itself from the Search log and the Extraction table. The box-counts (identified, deduped, screened, full-text assessed, included) update live. You do not draw the diagram by hand — you only need to add the narrative around it.

Push the PRISMA flow into the manuscript with **Push to Figures → Figure 1**. The Figures tab assigns it a stable identifier and a caption you can edit.

## Meta-analysis and heterogeneity

Open the **Meta-analysis** card. The 14 trials are already loaded as effect-size rows. For IKDC, the effect measure is **mean difference (MD)**. For re-rupture, it is **risk ratio (RR)** with the Mantel–Haenszel method.

Choose the **random-effects** model (DerSimonian–Laird as a default; the app also offers REML and Paule–Mandel). Inspect the **forest plot** — each row shows the per-study estimate with its 95% confidence interval and its weight. The summary diamond sits at the bottom. For our worked example you should see the pooled IKDC MD favours hamstring by about 1.4 points with a 95% CI that just crosses zero; the pooled re-rupture RR is 1.46 favouring BPTB (CI 1.04–2.05).

Read the heterogeneity statistics carefully. **I²** quantifies the proportion of variability not explained by sampling error; values above 50% mean substantial heterogeneity. **τ²** is the variance of the underlying true effects on the same scale as your outcome. **Q** is the Cochran chi-square test of heterogeneity — its p-value is underpowered with few studies, so do not rely on it alone.

If I² is high, run pre-specified subgroup analyses: by graft fixation method, by follow-up duration, by femoral tunnel technique (transtibial vs anteromedial). The app shows you sub-group forest plots and an interaction p-value. Do not data-dredge — if a subgroup was not in your protocol, declare it as exploratory.

For publication bias, the **funnel plot** is the visual cue and **Egger's regression test** is the formal one. With only 14 studies you are under the recommended threshold (≥10 is the bare minimum; ≥20 is more reliable), so report the funnel plot but caveat the test.

## GRADE certainty

Open the **GRADE** tab. For each outcome (IKDC, re-rupture, KOOS-sport, anterior knee pain), the app proposes a starting certainty of **high** because every included study is an RCT. You then downgrade across five domains:

- **Risk of bias** — start with the proportion of high-RoB studies. Downgrade one level if more than 25% of the weight comes from high-risk trials.
- **Inconsistency** — I² > 60% or non-overlapping CIs trigger a downgrade.
- **Indirectness** — your PICO matches the included studies, so this is usually "not serious" unless surrogate outcomes dominate.
- **Imprecision** — does the CI cross the clinically important threshold? For IKDC, the MCID is 11.5 points; a CI of −2 to +4 is precise but uninformative.
- **Publication bias** — funnel-plot asymmetry plus suspicion of unpublished negative trials.

The app produces a **Summary of Findings** table you can paste into the manuscript. For our example you might end up with: IKDC moderate certainty (downgraded for imprecision), re-rupture moderate (downgraded for inconsistency), KOOS-sport low (downgraded for both), anterior knee pain low (downgraded for risk of bias and imprecision).

## Writing the manuscript

Switch to the **Manuscript** tab. Pick the **systematic review template** — it scaffolds Introduction, Methods (with PRISMA item references), Results, Discussion, Conclusion, and a Methodological Quality section.

Type `@` anywhere to drop in a citation. Use the visible figure-reference menu to insert `Figure 1`, `Figure 2`, etc. — the numbering is auto-maintained. When you write the Results section, you can copy the summary line out of the Meta-analysis card directly: "The pooled MD for IKDC at 24 months was 1.4 (95% CI −0.8 to 3.6, I² 52%, 14 trials, 2,184 patients, moderate certainty)."

The Bubble AI assist on selected text lets you re-write in third-person, expand a paragraph with a citation cluster, or tighten the discussion. It will not invent citations — it draws only from your Library.

Switch the **Bibliography style** to **Bone & Joint Journal** in Settings → Citation style. The app reformats inline citations and the bibliography on the fly. Verify the first author surnames are correctly title-cased and that journal abbreviations use the BJJ short form.

## Submission and reporting

Open the **Submission** tab. Pick the target journal — for an ACL meta-analysis a sensible aim-high choice is **The Bone & Joint Journal**, with a fallback list of **Arthroscopy**, **AJSM**, and **KSSTA**.

Generate the **cover letter** with the cover-letter helper. The template explicitly mentions PRISMA adherence, PROSPERO registration ID, dual independent screening, and no conflicts of interest. Edit the corresponding author block and the conflict-of-interest declaration before locking the letter.

Compile the **submission package**: title page (with ICMJE authorship statements), main manuscript, figures (PRISMA flow + RoB summary + forest plots + funnel plot), tables (study characteristics, RoB per domain, SoF), supplementary appendix with the full search strings and exclusion log. The bundle exports as a single zip whose folder structure matches what BJJ asks for.

Final checks before you hit upload:

- PROSPERO ID is in the methods section.
- PRISMA flow shows the same numbers as the text.
- Every claim in the discussion has a citation or is flagged as opinion.
- The reporting guideline checklist (PRISMA 2020) has every item ticked or has a "not applicable" justification.

The reviewer-response editor is empty for now. When the journal comes back with comments, you will open it again and use the structured "comment → response → manuscript change" format that journals love.

That is the full pipeline, from PICO to PDF, in about nine weeks of effort. A second walkthrough in this Learn hub covers the same journey for a single RCT write-up; a third covers an observational cohort; and the fourth walks you through a focused meta-analysis where the included studies have already been screened. Pick the one closest to your current project and use it as your weekly checklist.
