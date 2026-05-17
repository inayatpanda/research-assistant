from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

WritingAction = Literal["improve", "shorten", "formalise", "add_transition"]


class WritingAssistRequest(BaseModel):
    action: WritingAction
    text: str = Field(min_length=1, max_length=4_000)


class WritingAssistResponse(BaseModel):
    revised: str
