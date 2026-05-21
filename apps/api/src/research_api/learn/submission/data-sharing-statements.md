---
slug: data-sharing-statements
title: Data sharing statements
topic: data-sharing-statements
topic_family: writing
worked_example_domain: medicine
related_concepts:
  - registration
  - copyright-and-licensing
---

## What

A data-sharing statement is a short paragraph (often at the end of the methods or as a dedicated section) describing what data underlying the article will be shared, when, with whom, and under what conditions. ICMJE requires data-sharing statements for all clinical-trial reports.

## When

- At registration for clinical trials (ClinicalTrials.gov has a structured data-sharing field).
- At submission for every article (data-sharing statement field).
- At publication, with the live link to the deposited dataset.

## How — required elements

1. Will individual-participant data (IPD) be shared? (yes / no / undecided / no, with reason)
2. What data specifically?
3. What other documents will be available? (protocol, statistical analysis plan, ICF, analytic code)
4. When will data become available? (immediately / 6 months / never)
5. By what access criteria? (open / on request / via committee review)
6. By what mechanism? (repository URL, contact email)

## Repositories

- General: OSF (osf.io), Dryad, Figshare, Zenodo.
- Bio-omics: GEO, SRA, ENA, ArrayExpress.
- Medical imaging: TCIA, OpenNeuro, XNAT Central.
- Code: GitHub + Zenodo for DOI; never code-only-on-request unless legally constrained.
- Restricted-access (IPD): Vivli, YODA, ClinicalStudyDataRequest.com.

## Pitfalls

- "Available on request" is treated by many funders (NIH, MRC, Wellcome) as no sharing at all. Use a repository with a DOI.
- Sharing without a data-use agreement when data are sensitive (genomic, paediatric, mental-health).
- Code shared without a licence — defaults to "all rights reserved", which blocks reuse. Add an OSI-approved licence (MIT, Apache-2.0).
- Forgetting to share the analysis plan (SAP) alongside the data — code without context is rarely useful.

## Template

```
Data sharing
De-identified individual-participant data underlying the results reported in this article, together with the protocol, statistical analysis plan, and analytic R/Python code, will be made available without restriction at the Open Science Framework (DOI 10.17605/OSF.IO/XXXXX) within 12 months of publication. Requests beyond the publicly available files should be addressed to [corresponding author email].
```
