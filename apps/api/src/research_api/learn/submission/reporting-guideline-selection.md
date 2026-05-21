---
slug: reporting-guideline-selection
title: Reporting guideline selection
topic: reporting-guideline-selection
topic_family: planning
worked_example_domain: surgery
related_concepts:
  - consort
  - strobe
  - prisma
  - care
  - squire
  - coreq
  - srqr
  - tripod
  - cheers
  - stard
  - moose
  - arrive
---

## What

The EQUATOR Network catalogues 600+ reporting guidelines. The right one for your manuscript is the one (or two — parent + extension) that matches your study design. Picking the wrong checklist wastes effort and frustrates reviewers.

## Quick decision tree

Start with one question: what is the design?

1. Randomised intervention -> [CONSORT](?cat=checklists&slug=consort).
   - Cluster, crossover, or pilot trial -> relevant CONSORT extension on top.
2. Observational cohort, case-control, or cross-sectional -> [STROBE](?cat=checklists&slug=strobe).
3. Systematic review or meta-analysis -> [PRISMA](?cat=checklists&slug=prisma).
   - Meta-analysis of observational studies -> also use [MOOSE](?cat=checklists&slug=moose).
   - Diagnostic-test accuracy SR -> PRISMA-DTA.
   - Scoping review -> PRISMA-ScR.
   - Searching -> PRISMA-S.
4. Case report (n = 1) -> [CARE](?cat=checklists&slug=care). For 3+ surgical patients, PROCESS or SCARE.
5. Quality improvement / implementation -> [SQUIRE](?cat=checklists&slug=squire).
6. Qualitative interviews / focus groups -> [COREQ](?cat=checklists&slug=coreq). Broader qualitative methods -> [SRQR](?cat=checklists&slug=srqr).
7. Multivariable prediction model -> [TRIPOD](?cat=checklists&slug=tripod). AI/ML model -> TRIPOD+AI.
8. Diagnostic accuracy -> [STARD](?cat=checklists&slug=stard).
9. Health economic evaluation -> [CHEERS](?cat=checklists&slug=cheers).
10. Animal experiment -> [ARRIVE](?cat=checklists&slug=arrive).

## What if my study has features of two designs?

Pair guidelines:

- RCT + economic evaluation: CONSORT + CHEERS.
- Mixed-methods (RCT + qualitative arm): CONSORT + COREQ (or SRQR).
- SR of diagnostic accuracy: PRISMA + PRISMA-DTA + (for primary studies) STARD.
- Cluster RCT of an implementation intervention: CONSORT cluster extension + SQUIRE.

## When

At protocol stage — the checklist informs the study design, not just the writing. At submission, fill in the full checklist with page/line numbers and upload it as a supplementary file (most journals now mandate this).

## Pitfalls

- Picking a checklist after the manuscript is written and trying to retrofit. Methods choices made without the checklist in mind almost always leave gaps.
- Using CONSORT for a non-randomised intervention. Use TREND instead.
- Using PRISMA for a narrative review. Use SANRA.

## Template

For each manuscript, store the chosen guideline name, version, full checklist with page/line references, and any deviations. Our app's Frontmatter -> Reporting guideline slot stores this for compile-time inclusion in the submission package.
