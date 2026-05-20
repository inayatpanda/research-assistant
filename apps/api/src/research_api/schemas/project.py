from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StudyType = Literal[
    "Before/After Intervention",
    "Outcome Study",
    "Risk Factor Analysis",
    "Group Comparison",
    "Prospective Cohort",
    "Retrospective Case Series",
    "Systematic Review",
    "Randomised Controlled Trial",
]

# Phase 16 (MP16) — Extended citation style catalogue.
# Vancouver-family journal variants are appended; the 4 originals stay first
# so existing tests / persisted ``projects.citation_style`` values keep
# validating without migration.
CitationStyle = Literal[
    "vancouver",
    "apa",
    "harvard",
    "ieee",
    "lancet",
    "nejm",
    "bjj",
    "jbjs_am",
    "bjsm",
    "jama",
]
AIProviderName = Literal["gemini", "claude", "openai"]

# Phase 16 (MP16) — Inline citation rendering mode.
InlineCitationMode = Literal[
    "bracket_numeric",
    "superscript_numeric",
    "author_year_parens",
]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    study_type: StudyType
    citation_style: CitationStyle = "vancouver"
    ai_provider: AIProviderName = "gemini"
    target_journal: str | None = None
    prospero_number: str | None = None
    clinicaltrials_number: str | None = None
    template_journal: str | None = None
    inline_citation_mode: InlineCitationMode = "bracket_numeric"


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    study_type: StudyType | None = None
    citation_style: CitationStyle | None = None
    ai_provider: AIProviderName | None = None
    target_journal: str | None = None
    prospero_number: str | None = None
    clinicaltrials_number: str | None = None
    # `template_journal` may be unset, explicit-null (to clear), or a catalogue key.
    template_journal: str | None = None
    inline_citation_mode: InlineCitationMode | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    study_type: StudyType
    citation_style: CitationStyle
    ai_provider: AIProviderName
    target_journal: str | None
    prospero_number: str | None
    clinicaltrials_number: str | None
    template_journal: str | None = None
    inline_citation_mode: InlineCitationMode = "bracket_numeric"
    created_at: datetime
    updated_at: datetime
