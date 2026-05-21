---
slug: prisma
title: PRISMA 2020 — Systematic reviews and meta-analyses
reporting_standard: PRISMA
applies_to_study_types:
  - systematic review
  - meta-analysis
  - systematic review of interventions
applies_to_study_types_short: Systematic reviews
version: "2020"
official_url: https://www.equator-network.org/reporting-guidelines/prisma/
worked_example_domain: orthopaedics
related_concepts:
  - prospero
  - prisma-flow-diagram
  - risk-of-bias
  - grade
  - meta-analysis
---

# PRISMA 2020 reporting checklist (27 items)

## Scope

PRISMA 2020 supersedes PRISMA 2009. It applies to any systematic review regardless of the question (intervention, diagnostic, prognostic). Pair it with PRISMA-S for searching, PRISMA-DTA for diagnostic-accuracy reviews, PRISMA-ScR for scoping reviews, and PRISMA-IPD for individual-patient-data syntheses.

## Key items the user must report

### Title and abstract
- [ ] 1. Identify the report as a systematic review.
- [ ] 2. See the PRISMA 2020 for Abstracts checklist (12 sub-items).

### Introduction
- [ ] 3. Rationale: describe the rationale for the review in the context of existing knowledge.
- [ ] 4. Objectives: provide an explicit statement of the objective(s) or question(s) the review addresses.

### Methods
- [ ] 5. Eligibility criteria: specify the inclusion and exclusion criteria for the review and how studies were grouped for the syntheses.
- [ ] 6. Information sources: specify all databases, registers, websites, organisations, reference lists, and other sources searched or consulted, with the date when each source was last searched.
- [ ] 7. Search strategy: present the full search strategies for all databases, registers, and websites, including any filters and limits used.
- [ ] 8. Selection process: specify the methods used to decide whether a study met the inclusion criteria (how many reviewers screened each record, whether they worked independently, and processes for resolving disagreements).
- [ ] 9. Data collection process: specify the methods used to collect data from reports, including how many reviewers collected data, whether they worked independently, and any processes for obtaining or confirming data from study investigators.
- [ ] 10a. Data items — outcomes: list and define all outcomes for which data were sought; specify whether all results compatible with each outcome domain were sought.
- [ ] 10b. Data items — other variables: list and define all other variables for which data were sought.
- [ ] 11. Study risk of bias assessment: specify the methods used to assess risk of bias in the included studies, including details of the tool(s) used.
- [ ] 12. Effect measures: specify for each outcome the effect measure(s) (e.g. risk ratio, mean difference) used in the synthesis or presentation of results.
- [ ] 13a. Synthesis methods — eligibility for synthesis: describe the processes used to decide which studies were eligible for each synthesis.
- [ ] 13b. Describe any methods required to prepare the data for presentation or synthesis, such as handling of missing summary statistics.
- [ ] 13c. Describe any methods used to tabulate or visually display results.
- [ ] 13d. Describe any methods used to synthesise results and provide a rationale; if meta-analysis was performed, describe the model(s), method(s) to identify presence and extent of statistical heterogeneity, and software used.
- [ ] 13e. Describe any methods used to explore possible causes of heterogeneity among study results (e.g. subgroup analysis, meta-regression).
- [ ] 13f. Describe any sensitivity analyses to assess robustness of the synthesised results.
- [ ] 14. Reporting bias assessment: describe any methods used to assess risk of bias due to missing results in a synthesis (arising from reporting biases).
- [ ] 15. Certainty assessment: describe any methods used to assess certainty (or confidence) in the body of evidence for an outcome.

### Results
- [ ] 16a. Study selection: describe the results of the search and selection process, from the number of records identified through to those included in the review, ideally using a flow diagram.
- [ ] 16b. Cite studies that might appear to meet the inclusion criteria but which were excluded, and explain why they were excluded.
- [ ] 17. Study characteristics: cite each included study and present its characteristics.
- [ ] 18. Risk of bias in studies: present assessments of risk of bias for each included study.
- [ ] 19. Results of individual studies: for all outcomes, present, for each study, summary statistics for each group (where appropriate) and an effect estimate and its precision (e.g. confidence interval).
- [ ] 20a. Results of syntheses: for each synthesis, briefly summarise the characteristics and risk of bias among contributing studies.
- [ ] 20b. Present results of all statistical syntheses conducted; if meta-analysis was performed, present the summary estimate and its precision and measures of statistical heterogeneity.
- [ ] 20c. Present results of all investigations of possible causes of heterogeneity.
- [ ] 20d. Present results of all sensitivity analyses.
- [ ] 21. Reporting biases: present assessments of risk of bias due to missing results for each synthesis assessed.
- [ ] 22. Certainty of evidence: present assessments of certainty (or confidence) in the body of evidence for each outcome assessed.

### Discussion
- [ ] 23a. Provide a general interpretation of the results in the context of other evidence.
- [ ] 23b. Discuss any limitations of the evidence included in the review.
- [ ] 23c. Discuss any limitations of the review processes used.
- [ ] 23d. Discuss implications of the results for practice, policy, and future research.

### Other information
- [ ] 24a. Registration and protocol: provide registration information for the review, including the register name and registration number, or state that the review was not registered.
- [ ] 24b. Indicate where the review protocol can be accessed, or state that a protocol was not prepared.
- [ ] 24c. Describe and explain any amendments to information provided at registration or in the protocol.
- [ ] 25. Support: describe sources of financial or non-financial support for the review, and the role of the funders or sponsors in the review.
- [ ] 26. Competing interests: declare any competing interests of review authors.
- [ ] 27. Availability of data, code, and other materials: report which of the following are publicly available and where they can be found — template data collection forms, data extracted, data used for analyses, analytic code, any other materials used in the review.

## Common mistakes

- Reporting "PRISMA 2009" in 2026 manuscripts — most journals now require the 2020 update.
- Pasting only one database's search string and saying "adapted for the others"; PRISMA 2020 item 7 wants every full strategy.
- Missing the certainty-of-evidence row (item 22) — usually a GRADE Summary of Findings table.
- A flow diagram with mismatched counts between identified, screened, and included.

## How this maps to manuscript sections in our app

- Systematic Review -> Search history page produces the search strategy for item 7.
- Systematic Review -> Screening pipeline produces the flow diagram for item 16.
- GRADE module produces the Summary of Findings table for item 22.
- Frontmatter -> Registration (PROSPERO) covers item 24a.
