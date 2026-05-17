from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AbbreviationItem(BaseModel):
    short_form: str = Field(min_length=1, max_length=32)
    long_form: str = Field(min_length=1, max_length=500)


class AbbreviationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str
    short_form: str
    long_form: str
    created_at: datetime


class AbbreviationsReplace(BaseModel):
    items: list[AbbreviationItem] = Field(max_length=200)
