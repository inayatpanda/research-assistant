from .card_draft import CARD_DRAFT_PROMPT
from .citation_extraction import EXTRACTION_PROMPT, SUMMARISE_PROMPT
from .cover_letter import (
    COVER_LETTER_SYSTEM_PROMPT,
    COVER_LETTER_USER_PROMPT,
    build_cover_letter_prompt,
)
from .economic_interpretation import (
    ECONOMIC_INTERPRETATION_PROMPT,
    build_economic_interpretation_prompt,
)
from .meta_interpretation import (
    META_INTERPRETATION_PROMPT,
    build_meta_interpretation_prompt,
)
from .result_interpretation import (
    RESULT_INTERPRETATION_PROMPT,
    build_result_interpretation_prompt,
)
from .reviewer_response import (
    REVIEWER_RESPONSE_SYSTEM_PROMPT,
    REVIEWER_RESPONSE_USER_PROMPT,
    build_reviewer_response_prompt,
)
from .screening_suggestion import (
    SCREENING_SUGGESTION_SYSTEM_PROMPT,
    SCREENING_SUGGESTION_USER_PROMPT,
    build_screening_suggestion_prompt,
)
from .section_draft import SECTION_DRAFT_PROMPT, format_card_for_prompt
from .writing_assist import WRITING_ASSIST_PROMPT

__all__ = [
    "EXTRACTION_PROMPT",
    "SUMMARISE_PROMPT",
    "CARD_DRAFT_PROMPT",
    "SECTION_DRAFT_PROMPT",
    "WRITING_ASSIST_PROMPT",
    "META_INTERPRETATION_PROMPT",
    "build_meta_interpretation_prompt",
    "RESULT_INTERPRETATION_PROMPT",
    "ECONOMIC_INTERPRETATION_PROMPT",
    "build_economic_interpretation_prompt",
    "SCREENING_SUGGESTION_SYSTEM_PROMPT",
    "SCREENING_SUGGESTION_USER_PROMPT",
    "COVER_LETTER_SYSTEM_PROMPT",
    "COVER_LETTER_USER_PROMPT",
    "build_cover_letter_prompt",
    "REVIEWER_RESPONSE_SYSTEM_PROMPT",
    "REVIEWER_RESPONSE_USER_PROMPT",
    "build_reviewer_response_prompt",
    "build_result_interpretation_prompt",
    "build_screening_suggestion_prompt",
    "format_card_for_prompt",
]
