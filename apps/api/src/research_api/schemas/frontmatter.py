"""Phase 10 — ICMJE structured front-matter Pydantic schemas.

Five logical resources:
  - Author / AuthorCreate / AuthorUpdate / AuthorRead
  - Affiliation / AffiliationCreate / AffiliationUpdate / AffiliationRead
  - AuthorAffiliationLink / AuthorAffiliationRead
  - ContributionRead (POST/DELETE use path params; no body schema required)
  - ProjectFrontmatterRead / ProjectFrontmatterUpdate

CRediT role list is the canonical 14 from
https://credit.niso.org/. ORCID is validated against the iD pattern
`^\\d{4}-\\d{4}-\\d{4}-\\d{3}[\\dX]$` plus a mod-11-2 checksum
(uppercase X = checksum value 10).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Light-weight email format check (avoids the optional `pydantic[email]` dep).
# Accepts "<local>@<domain>" with at least one dot in the domain. Sufficient
# for ICMJE corresponding-author metadata; not RFC-strict.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    v = value.strip()
    if not _EMAIL_PATTERN.match(v):
        raise ValueError("Invalid email address")
    return v


CreditRole = Literal[
    "Conceptualization",
    "Data curation",
    "Formal analysis",
    "Funding acquisition",
    "Investigation",
    "Methodology",
    "Project administration",
    "Resources",
    "Software",
    "Supervision",
    "Validation",
    "Visualization",
    "Writing – original draft",
    "Writing – review & editing",
]
CREDIT_ROLES: tuple[str, ...] = (
    "Conceptualization",
    "Data curation",
    "Formal analysis",
    "Funding acquisition",
    "Investigation",
    "Methodology",
    "Project administration",
    "Resources",
    "Software",
    "Supervision",
    "Validation",
    "Visualization",
    "Writing – original draft",
    "Writing – review & editing",
)


_ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def validate_orcid(value: str) -> str:
    """Return canonical ORCID (uppercased X) or raise ValueError.

    Validates the iD shape AND the ISO/IEC 7064 MOD 11-2 checksum used by
    orcid.org (https://support.orcid.org/hc/en-us/articles/360006897674). The
    final character is `0–9` or `X`; `X` represents the checksum value 10.
    """
    if not isinstance(value, str):
        raise ValueError("ORCID must be a string")
    v = value.strip().upper()
    if not _ORCID_PATTERN.match(v):
        raise ValueError("ORCID must match 0000-0000-0000-000X")
    digits = v.replace("-", "")
    total = 0
    # First 15 chars are pure digits; verify checksum on the 16th.
    for ch in digits[:15]:
        total = (total + int(ch)) * 2
    remainder = total % 11
    expected = (12 - remainder) % 11
    expected_char = "X" if expected == 10 else str(expected)
    if digits[15] != expected_char:
        raise ValueError("ORCID checksum is invalid")
    return v


# ── Author ────────────────────────────────────────────────────────────


class AuthorBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=500)
    given_name: str = Field(default="", max_length=255)
    family_name: str = Field(default="", max_length=255)
    orcid: str | None = None
    email: str | None = None
    is_corresponding: bool = False

    @field_validator("orcid")
    @classmethod
    def _check_orcid(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        return validate_orcid(v)

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str | None) -> str | None:
        return _validate_email(v)


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=500)
    given_name: str | None = Field(default=None, max_length=255)
    family_name: str | None = Field(default=None, max_length=255)
    orcid: str | None = None
    email: str | None = None
    is_corresponding: bool | None = None

    @field_validator("orcid")
    @classmethod
    def _check_orcid(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        return validate_orcid(v)

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str | None) -> str | None:
        return _validate_email(v)


class AuthorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    full_name: str
    given_name: str
    family_name: str
    orcid: str | None
    email: str | None
    is_corresponding: bool
    position: int
    created_at: datetime
    updated_at: datetime
    affiliation_ids: list[str] = Field(default_factory=list)


class AuthorReorderRequest(BaseModel):
    ordered_author_ids: list[str] = Field(min_length=1)


# ── Affiliation ───────────────────────────────────────────────────────


class AffiliationBase(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    address: str | None = None
    city: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=255)


class AffiliationCreate(AffiliationBase):
    pass


class AffiliationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    address: str | None = None
    city: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=255)


class AffiliationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    address: str | None
    city: str | None
    country: str | None
    position: int
    created_at: datetime


class AffiliationReorderRequest(BaseModel):
    ordered_affiliation_ids: list[str] = Field(min_length=1)


# ── Author-Affiliation m2m ────────────────────────────────────────────


class AuthorAffiliationLink(BaseModel):
    author_id: str
    affiliation_id: str


# ── Contribution ──────────────────────────────────────────────────────


class ContributionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    author_id: str
    role: CreditRole


class ContributionSetRequest(BaseModel):
    role: CreditRole


# ── Funder ────────────────────────────────────────────────────────────


class Funder(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    grant_id: str | None = Field(default=None, max_length=255)


class StructuredAbstract(BaseModel):
    background: str = ""
    methods: str = ""
    results: str = ""
    conclusions: str = ""


# ── Project Frontmatter ───────────────────────────────────────────────


class ProjectFrontmatterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    funding_statement: str | None
    funders: list[Funder]
    ethics_irb: str | None
    ethics_approval_number: str | None
    ethics_consent: str | None
    conflicts_statement: str | None
    structured_abstract_enabled: bool
    structured_abstract: StructuredAbstract
    updated_at: datetime


class ProjectFrontmatterUpdate(BaseModel):
    funding_statement: str | None = None
    funders: list[Funder] | None = None
    ethics_irb: str | None = None
    ethics_approval_number: str | None = None
    ethics_consent: str | None = None
    conflicts_statement: str | None = None
    structured_abstract_enabled: bool | None = None
    structured_abstract: StructuredAbstract | None = None
