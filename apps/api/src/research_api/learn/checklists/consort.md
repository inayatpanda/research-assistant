---
slug: consort
title: CONSORT 2010 — Randomised controlled trials
reporting_standard: CONSORT
applies_to_study_types:
  - parallel-group RCT
  - cluster RCT (CONSORT extension)
  - crossover RCT (CONSORT extension)
  - non-inferiority / equivalence RCT (CONSORT extension)
applies_to_study_types_short: RCTs
version: "2010"
official_url: https://www.equator-network.org/reporting-guidelines/consort/
worked_example_domain: surgery
related_concepts:
  - randomisation
  - allocation-concealment
  - blinding
  - intention-to-treat
  - cluster-rct
---

# CONSORT 2010 reporting checklist (25 items)

## Scope

Use CONSORT for every randomised controlled trial. Extensions exist for cluster, crossover, non-inferiority, pilot/feasibility, herbal, non-pharmacologic, and PRO-specific trials — apply both the parent and the extension. CONSORT pairs a 25-item checklist with a participant flow diagram (the "CONSORT diagram") that we generate from the Statistics module.

## Key items the user must report

### Title and abstract
- [ ] 1a. Identification as a randomised trial in the title.
- [ ] 1b. Structured summary of trial design, methods, results, and conclusions.

### Introduction
- [ ] 2a. Scientific background and explanation of rationale.
- [ ] 2b. Specific objectives or hypotheses.

### Methods — trial design
- [ ] 3a. Description of trial design (parallel, factorial, crossover) including allocation ratio.
- [ ] 3b. Important changes to methods after trial commencement, with reasons.

### Methods — participants
- [ ] 4a. Eligibility criteria for participants.
- [ ] 4b. Settings and locations where the data were collected.

### Methods — interventions
- [ ] 5. Interventions for each group with sufficient detail to allow replication, including how and when they were administered.

### Methods — outcomes
- [ ] 6a. Completely defined pre-specified primary and secondary outcome measures.
- [ ] 6b. Any changes to trial outcomes after the trial commenced, with reasons.

### Methods — sample size
- [ ] 7a. How sample size was determined.
- [ ] 7b. When applicable, explanation of any interim analyses and stopping guidelines.

### Methods — randomisation
- [ ] 8a. Method used to generate the random allocation sequence.
- [ ] 8b. Type of randomisation; details of any restriction (such as blocking and block size).
- [ ] 9. Mechanism used to implement the random allocation sequence (e.g. sequentially numbered containers), describing any steps taken to conceal the sequence until interventions were assigned.
- [ ] 10. Who generated the random allocation sequence, who enrolled participants, and who assigned participants to interventions.

### Methods — blinding
- [ ] 11a. If done, who was blinded after assignment to interventions and how.
- [ ] 11b. If relevant, description of the similarity of interventions.

### Methods — statistical methods
- [ ] 12a. Statistical methods used to compare groups for primary and secondary outcomes.
- [ ] 12b. Methods for additional analyses, such as subgroup analyses and adjusted analyses.

### Results
- [ ] 13a. For each group, the numbers of participants who were randomly assigned, received intended treatment, and were analysed for the primary outcome.
- [ ] 13b. For each group, losses and exclusions after randomisation, together with reasons.
- [ ] 14a. Dates defining the periods of recruitment and follow-up.
- [ ] 14b. Why the trial ended or was stopped.
- [ ] 15. A table showing baseline demographic and clinical characteristics for each group.
- [ ] 16. For each group, number of participants (denominator) included in each analysis and whether the analysis was by original assigned groups.
- [ ] 17a. For each primary and secondary outcome, results for each group and the estimated effect size and its precision (such as 95% confidence interval).
- [ ] 17b. For binary outcomes, presentation of both absolute and relative effect sizes is recommended.
- [ ] 18. Results of any other analyses performed, including subgroup analyses and adjusted analyses, distinguishing pre-specified from exploratory.
- [ ] 19. All important harms or unintended effects in each group.

### Discussion
- [ ] 20. Trial limitations, addressing sources of potential bias, imprecision, and (if relevant) multiplicity of analyses.
- [ ] 21. Generalisability (external validity, applicability) of the trial findings.
- [ ] 22. Interpretation consistent with results, balancing benefits and harms, and considering other relevant evidence.

### Other information
- [ ] 23. Registration number and name of trial registry.
- [ ] 24. Where the full trial protocol can be accessed, if available.
- [ ] 25. Sources of funding and other support (such as supply of drugs), role of funders.

## Common mistakes

- Reporting per-protocol analysis as the headline result; CONSORT expects intention-to-treat.
- Burying the allocation concealment description in two words ("randomised, blinded") with no mechanism.
- Omitting absolute effects for binary outcomes (item 17b) and only quoting odds ratios.
- A CONSORT diagram that doesn't reconcile randomised vs analysed counts.

## How this maps to manuscript sections in our app

- Methods -> Frontmatter -> *Trial design* and *Randomisation* slots cover items 3, 8, 9.
- Statistics -> CONSORT diagram generator produces the figure for item 13.
- Manuscript -> Tables -> "Baseline characteristics" snippet covers item 15.
- Frontmatter -> Registration and funding fields cover items 23 and 25.
