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

CitationStyle = Literal["vancouver", "apa", "harvard"]
AIProviderName = Literal["gemini", "claude", "openai"]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    study_type: StudyType
    citation_style: CitationStyle = "vancouver"
    ai_provider: AIProviderName = "gemini"
    target_journal: str | None = None
    prospero_number: str | None = None
    clinicaltrials_number: str | None = None
    template_journal: str | None = None


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
    created_at: datetime
    updated_at: datetime
