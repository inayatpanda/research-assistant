---
slug: moose
title: MOOSE — Meta-analyses of observational studies
reporting_standard: MOOSE
applies_to_study_types:
  - meta-analysis of observational studies (cohort, case-control)
  - systematic review with quantitative synthesis (non-RCT)
applies_to_study_types_short: Meta-analyses of observational studies
version: "2000"
official_url: https://www.equator-network.org/reporting-guidelines/moose/
worked_example_domain: surgery
related_concepts:
  - heterogeneity
  - publication-bias
  - random-effects-model
  - confounding
---

# MOOSE reporting checklist (35 items)

## Scope

MOOSE was developed in 2000 by the Meta-analysis Of Observational Studies in Epidemiology group. Use MOOSE alongside PRISMA when synthesising observational evidence — PRISMA gives the modern reporting backbone, MOOSE adds the items unique to non-randomised syntheses (confounding, exposure misclassification, ecological fallacy). The 35 items below summarise the canonical list and are organised by section.

## Key items the user must report

### Reporting of background should include
- [ ] 1. Problem definition.
- [ ] 2. Hypothesis statement.
- [ ] 3. Description of study outcome(s).
- [ ] 4. Type of exposure or intervention used.
- [ ] 5. Type of study designs used.
- [ ] 6. Study population.

### Reporting of search strategy should include
- [ ] 7. Qualifications of searchers (e.g. librarians and investigators).
- [ ] 8. Search strategy, including time period included in the synthesis and key words.
- [ ] 9. Effort to include all available studies, including contact with authors.
- [ ] 10. Databases and registries searched.
- [ ] 11. Search software used, name and version, including special features used (e.g. explosion).
- [ ] 12. Use of hand searching (e.g. reference lists of obtained articles).
- [ ] 13. List of citations located and those excluded, including justification.
- [ ] 14. Method of addressing articles published in languages other than English.
- [ ] 15. Method of handling abstracts and unpublished studies.
- [ ] 16. Description of any contact with authors.

### Reporting of methods should include
- [ ] 17. Description of relevance or appropriateness of studies assembled for assessing the hypothesis to be tested.
- [ ] 18. Rationale for the selection and coding of data (e.g. sound clinical principles or convenience).
- [ ] 19. Documentation of how data were classified and coded (e.g. multiple raters, blinding, and inter-rater reliability).
- [ ] 20. Assessment of confounding (e.g. comparability of cases and controls in studies where appropriate).
- [ ] 21. Assessment of study quality, including blinding of quality assessors; stratification or regression on possible predictors of study results.
- [ ] 22. Assessment of heterogeneity.
- [ ] 23. Description of statistical methods (e.g. complete description of fixed or random effects models, justification of whether the chosen models account for predictors of study results, dose-response models, or cumulative meta-analysis) in sufficient detail to be replicated.
- [ ] 24. Provision of appropriate tables and graphics.

### Reporting of results should include
- [ ] 25. Graphic summarising individual study estimates and overall estimate.
- [ ] 26. Table giving descriptive information for each study included.
- [ ] 27. Results of sensitivity testing (e.g. subgroup analysis).
- [ ] 28. Indication of statistical uncertainty of findings.

### Reporting of discussion should include
- [ ] 29. Quantitative assessment of bias (e.g. publication bias).
- [ ] 30. Justification for exclusion (e.g. exclusion of non-English-language citations).
- [ ] 31. Assessment of quality of included studies.

### Reporting of conclusions should include
- [ ] 32. Consideration of alternative explanations for observed results.
- [ ] 33. Generalisation of the conclusions (i.e. appropriate for the data presented and within the domain of the literature review).
- [ ] 34. Guidelines for future research.
- [ ] 35. Disclosure of funding source.

## Common mistakes

- Treating observational meta-analyses like RCT syntheses — confounding (item 20) demands explicit attention.
- No assessment of publication bias (item 29) despite forest plot showing small-study effects.
- Pooling adjusted estimates from studies with different confounder sets without acknowledging it.

## How this maps to manuscript sections in our app

- Meta-analysis module -> Forest + funnel plot covers items 25 and 29.
- Systematic Review module -> Risk-of-bias assessment (Newcastle-Ottawa or ROBINS-I) covers item 21.
- Frontmatter -> Funding statement covers item 35.
