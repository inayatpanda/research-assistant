---
slug: disability-adjusted-life-year
title: Disability-adjusted life-year (DALY)
concept_family: outcomes-measurement
formula: "DALY = YLL + YLD; YLL = N × L; YLD = I × DW × L"
units: "DALYs (years of healthy life lost)"
worked_example_domain: medicine
related_concepts:
  - quality-adjusted-life-year
  - global-burden-of-disease
  - cost-effectiveness-ratio
---

## Definition

A DALY is a year of healthy life lost — to either premature mortality (Years of Life Lost, YLL) or disability while alive (Years Lived with Disability, YLD). One DALY equals one healthy year forgone. DALYs are the headline metric of the WHO Global Burden of Disease study and the preferred outcome for low- and middle-income-country cost-effectiveness analyses.

## Formula

```
DALY = YLL + YLD
YLL  = N × L                  (deaths × standard life expectancy at age of death)
YLD  = I × DW × L             (incident cases × disability weight × duration)
```

## Interpretation

Unlike the QALY (a benefit, "more is better"), the DALY is a loss ("fewer is better"). The disability weight (DW) runs 0 (perfect health) to 1 (equivalent to death). Disability weights are global panel estimates from the GBD study.

## Worked example (medicine)

A multi-drug-resistant tuberculosis programme in a high-burden country averts an estimated 4,200 deaths (mean age at death 38, standard life expectancy 32 years) and 6,500 incident disability-years at DW 0.33 for an average 1.5 years. YLL = 4,200 × 32 = 134,400; YLD = 6,500 × 0.33 × 1.5 ≈ 3,217. Total DALYs averted ≈ 137,617.

## How to report

Report disability weights and their source (GBD year), the standard life expectancy used (e.g. GBD 2019 reference), and whether age-weighting or discounting were applied. GBD 2010 onwards no longer applies age weighting by default; many older analyses still do.
