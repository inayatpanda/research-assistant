"""Server-side declarative catalogue of orthopaedics journal templates.

These caps reflect publisher author guidelines as of the Phase 8.7 cut date
and will drift as journals revise their instructions to authors. They are
data, not code — easy to update without a migration. The frontend
WordCountBar reads `max_words_by_section` for per-section gauges and
`max_total_words` for the overall total.
"""
from __future__ import annotations

from ...schemas.journal_template import JournalTemplate


JOURNALS: dict[str, JournalTemplate] = {
    "jbjs": JournalTemplate(
        key="jbjs",
        label="JBJS (Journal of Bone & Joint Surgery)",
        max_total_words=4000,
        max_words_by_section={
            "Abstract": 300,
            "Introduction": 600,
            "Methodology": 1200,
            "Results": 1000,
            "Discussion": 900,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=True,
        reference_style="vancouver",
        max_figures=8,
        max_tables=4,
    ),
    "bjj": JournalTemplate(
        key="bjj",
        label="Bone & Joint Journal",
        max_total_words=3500,
        max_words_by_section={
            "Abstract": 250,
            "Introduction": 500,
            "Methodology": 1100,
            "Results": 900,
            "Discussion": 800,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=True,
        reference_style="vancouver",
        max_figures=6,
        max_tables=4,
    ),
    "bjsm": JournalTemplate(
        key="bjsm",
        label="British Journal of Sports Medicine",
        max_total_words=4000,
        max_words_by_section={
            "Abstract": 300,
            "Introduction": 700,
            "Methodology": 1200,
            "Results": 900,
            "Discussion": 800,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=True,
        reference_style="vancouver",
        max_figures=6,
        max_tables=4,
    ),
    "jaaos": JournalTemplate(
        key="jaaos",
        label="JAAOS (Journal of the American Academy of Orthopaedic Surgeons)",
        max_total_words=4500,
        max_words_by_section={
            "Abstract": 250,
            "Introduction": 700,
            "Methodology": 1300,
            "Results": 1100,
            "Discussion": 950,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=False,
        reference_style="vancouver",
        max_figures=8,
        max_tables=5,
    ),
    "jor": JournalTemplate(
        key="jor",
        label="Journal of Orthopaedic Research",
        max_total_words=5000,
        max_words_by_section={
            "Abstract": 250,
            "Introduction": 800,
            "Methodology": 1500,
            "Results": 1200,
            "Discussion": 1050,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=False,
        reference_style="vancouver",
        max_figures=8,
        max_tables=4,
    ),
    "ota-int": JournalTemplate(
        key="ota-int",
        label="OTA International",
        max_total_words=3500,
        max_words_by_section={
            "Abstract": 250,
            "Introduction": 500,
            "Methodology": 1100,
            "Results": 850,
            "Discussion": 600,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=True,
        reference_style="vancouver",
        max_figures=6,
        max_tables=4,
    ),
    "arthroscopy": JournalTemplate(
        key="arthroscopy",
        label="Arthroscopy: The Journal of Arthroscopic & Related Surgery",
        max_total_words=4000,
        max_words_by_section={
            "Abstract": 250,
            "Introduction": 600,
            "Methodology": 1300,
            "Results": 950,
            "Discussion": 700,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=True,
        reference_style="vancouver",
        max_figures=8,
        max_tables=5,
    ),
    "ajsm": JournalTemplate(
        key="ajsm",
        label="American Journal of Sports Medicine",
        max_total_words=4500,
        max_words_by_section={
            "Abstract": 350,
            "Introduction": 700,
            "Methodology": 1300,
            "Results": 1000,
            "Discussion": 950,
            "Conclusion": 200,
        },
        required_sections=[
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        structured_abstract=True,
        reference_style="apa",
        max_figures=8,
        max_tables=5,
    ),
}


def list_templates() -> list[JournalTemplate]:
    return list(JOURNALS.values())


def get_template(key: str) -> JournalTemplate | None:
    return JOURNALS.get(key)
