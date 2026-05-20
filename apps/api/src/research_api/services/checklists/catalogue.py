"""Reporting-guideline checklist definitions (CHEERS 2022 first).

The shape of each entry is:

    {
        "key": str,                   # short slug
        "name": str,                  # display name
        "version": str,
        "source_citation": str,
        "items": list[{
            "n": str,                 # item number (e.g. "5", "5a")
            "section": str,           # CHEERS section / heading
            "topic": str,             # short topic label
            "recommendation": str,    # the actual recommendation text
        }],
    }

This is intentionally a JSON-shaped Python module rather than an external
file so it ships with the package + works in tests without IO.
"""
from __future__ import annotations

from typing import Any


CHEERS_2022: dict[str, Any] = {
    "key": "cheers_2022",
    "name": "CHEERS 2022 — Consolidated Health Economic Evaluation Reporting Standards",
    "version": "2022",
    "source_citation": (
        "Husereau D, Drummond M, Augustovski F, et al. Consolidated Health "
        "Economic Evaluation Reporting Standards 2022 (CHEERS 2022) Statement. "
        "Value Health 2022;25(1):3-9."
    ),
    "items": [
        {
            "n": "1",
            "section": "Title",
            "topic": "Title",
            "recommendation": "Identify the study as an economic evaluation and specify the interventions being compared.",
        },
        {
            "n": "2",
            "section": "Abstract",
            "topic": "Abstract",
            "recommendation": "Provide a structured summary that highlights context, key methods, results, and alternative analyses.",
        },
        {
            "n": "3",
            "section": "Introduction",
            "topic": "Background and objectives",
            "recommendation": "Give the context for the study, the study question, and its practical relevance for decision-making in policy or practice.",
        },
        {
            "n": "4",
            "section": "Methods",
            "topic": "Health economic analysis plan",
            "recommendation": "Indicate whether a health economic analysis plan was developed and where available.",
        },
        {
            "n": "5",
            "section": "Methods",
            "topic": "Study population",
            "recommendation": "Describe characteristics of the study population (such as age range, demographics, socioeconomic, or clinical characteristics).",
        },
        {
            "n": "6",
            "section": "Methods",
            "topic": "Setting and location",
            "recommendation": "Provide relevant contextual information that may influence findings.",
        },
        {
            "n": "7",
            "section": "Methods",
            "topic": "Comparators",
            "recommendation": "Describe the interventions or strategies being compared and why chosen.",
        },
        {
            "n": "8",
            "section": "Methods",
            "topic": "Perspective",
            "recommendation": "State the perspective(s) adopted by the study and why chosen.",
        },
        {
            "n": "9",
            "section": "Methods",
            "topic": "Time horizon",
            "recommendation": "State the time horizon for the study and why appropriate.",
        },
        {
            "n": "10",
            "section": "Methods",
            "topic": "Discount rate",
            "recommendation": "Report the discount rate(s) and reason chosen.",
        },
        {
            "n": "11",
            "section": "Methods",
            "topic": "Selection of outcomes",
            "recommendation": "Describe what outcomes were used as the measure(s) of benefit(s) and harm(s).",
        },
        {
            "n": "12",
            "section": "Methods",
            "topic": "Measurement of outcomes",
            "recommendation": "Describe how outcomes used to capture benefit(s) and harm(s) were measured.",
        },
        {
            "n": "13",
            "section": "Methods",
            "topic": "Valuation of outcomes",
            "recommendation": "Describe the population and methods used to measure and value outcomes.",
        },
        {
            "n": "14",
            "section": "Methods",
            "topic": "Measurement and valuation of resources and costs",
            "recommendation": "Describe how costs were valued.",
        },
        {
            "n": "15",
            "section": "Methods",
            "topic": "Currency, price date, and conversion",
            "recommendation": "Report the dates of the estimated resource quantities and unit costs, plus the currency and year of conversion.",
        },
        {
            "n": "16",
            "section": "Methods",
            "topic": "Rationale and description of model",
            "recommendation": "If modelling is used, describe in detail and why used. Report if the model is publicly available and where it can be accessed.",
        },
        {
            "n": "17",
            "section": "Methods",
            "topic": "Analytics and assumptions",
            "recommendation": "Describe any methods for analyses or statistical analyses; describe any structural or other assumptions underpinning the analysis.",
        },
        {
            "n": "18",
            "section": "Methods",
            "topic": "Characterising heterogeneity",
            "recommendation": "Describe any methods used for estimating how the results of the study vary for sub-groups.",
        },
        {
            "n": "19",
            "section": "Methods",
            "topic": "Characterising distributional effects",
            "recommendation": "Describe how impacts are distributed across different individuals or adjustments made to reflect priority populations.",
        },
        {
            "n": "20",
            "section": "Methods",
            "topic": "Characterising uncertainty",
            "recommendation": "Describe methods for characterising any sources of uncertainty.",
        },
        {
            "n": "21",
            "section": "Methods",
            "topic": "Approach to engagement with patients and others",
            "recommendation": "Describe any approaches to engage patients or service recipients, the general public, communities, or stakeholders in the design.",
        },
        {
            "n": "22",
            "section": "Results",
            "topic": "Study parameters",
            "recommendation": "Report the values, ranges, references, and probability distributions for all parameters.",
        },
        {
            "n": "23",
            "section": "Results",
            "topic": "Summary of main results",
            "recommendation": "Report the mean values for the main categories of costs and outcomes of interest and summarise them in the most appropriate overall measure.",
        },
        {
            "n": "24",
            "section": "Results",
            "topic": "Effect of uncertainty",
            "recommendation": "Describe how uncertainty about analytic judgments, inputs, or projections affect findings.",
        },
        {
            "n": "25",
            "section": "Results",
            "topic": "Effect of engagement with patients and others",
            "recommendation": "Report on any difference patient/service recipient, general public, community, or stakeholder engagement made.",
        },
        {
            "n": "26",
            "section": "Discussion",
            "topic": "Study findings, limitations, generalisability, and current knowledge",
            "recommendation": "Report key findings, limitations, ethical or equity considerations, and how patients/the public could benefit.",
        },
        {
            "n": "27",
            "section": "Other",
            "topic": "Funding & conflicts of interest",
            "recommendation": "Describe how the study was funded and any role of the funder; identify any conflicts of interest.",
        },
        {
            "n": "28",
            "section": "Other",
            "topic": "Data availability",
            "recommendation": "Describe to what extent data, code, or other materials underlying the analysis are publicly available.",
        },
    ],
}


CHECKLISTS: dict[str, dict[str, Any]] = {
    "cheers_2022": CHEERS_2022,
}


__all__ = ["CHECKLISTS", "CHEERS_2022"]
