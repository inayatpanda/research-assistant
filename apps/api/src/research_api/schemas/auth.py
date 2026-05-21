"""Phase S1 — Pydantic schemas for the auth subsystem."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["owner", "editor", "viewer"]


# Tight enough for our purposes — full RFC 5322 validation lives behind
# pydantic[email] (an unwanted new dep).
_EMAIL_LOCAL = r"[A-Za-z0-9._%+\-]+"
_EMAIL_DOMAIN = r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
import re as _re

_EMAIL_RE = _re.compile(rf"^{_EMAIL_LOCAL}@{_EMAIL_DOMAIN}$")


def _validate_email(v: str) -> str:
    s = v.strip()
    if not _EMAIL_RE.match(s):
        raise ValueError("must be a valid email address")
    return s


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    is_admin: bool
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return _validate_email(v)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return _validate_email(v)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=10, max_length=200)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_agent: str | None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class InvitationCreate(BaseModel):
    email: str
    role: Role = "viewer"

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return _validate_email(v)


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    project_id: str
    role: Role
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None


class InvitationCreateResponse(BaseModel):
    invitation: InvitationRead
    invite_url: str
    token: str  # raw token, only returned ONCE at creation time


class InvitationLanding(BaseModel):
    project_id: str
    project_title: str
    role: Role
    inviter_display_name: str
    email: str


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    display_name: str
    role: Role
    created_at: datetime


class MemberCreate(BaseModel):
    user_id: str | None = None
    email: str | None = None
    role: Role = "viewer"


class MemberUpdate(BaseModel):
    role: Role


class LegacyDataStatus(BaseModel):
    has_legacy: bool
    legacy_user_id: str | None = None
    project_count: int = 0
    article_count: int = 0
    dataset_count: int = 0
