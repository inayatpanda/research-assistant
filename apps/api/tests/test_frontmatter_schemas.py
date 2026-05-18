"""Phase 10 — Pydantic schema validation: ORCID checksum + email + roles."""
from __future__ import annotations

import pytest

from pydantic import ValidationError

from research_api.schemas.frontmatter import (
    AuthorCreate,
    ContributionSetRequest,
    CREDIT_ROLES,
    Funder,
    ProjectFrontmatterUpdate,
    StructuredAbstract,
    validate_orcid,
)


# ── ORCID checksum ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "orcid",
    [
        "0000-0002-1825-0097",  # canonical orcid.org example
        "0000-0001-5109-3700",
        "0000-0002-9079-593X",  # X = checksum 10
    ],
)
def test_validate_orcid_accepts_valid(orcid: str) -> None:
    assert validate_orcid(orcid) == orcid


def test_validate_orcid_accepts_lowercase_x_and_uppercases() -> None:
    # ORCID iDs only emit uppercase X; we normalise eagerly.
    assert validate_orcid("0000-0002-9079-593x") == "0000-0002-9079-593X"


@pytest.mark.parametrize(
    "bad",
    [
        "0000-0000-0000-0000",  # checksum mismatch (would need 4)
        "0000-0002-1825-009X",  # right shape, wrong last char
        "1234-5678-9012-3456",  # wrong checksum
        "not-an-orcid",
        "0000 0002 1825 0097",  # spaces instead of hyphens
        "",
    ],
)
def test_validate_orcid_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        validate_orcid(bad)


def test_author_create_accepts_known_orcid() -> None:
    a = AuthorCreate(
        full_name="Jane Doe", orcid="0000-0002-1825-0097", email="j@example.com"
    )
    assert a.orcid == "0000-0002-1825-0097"


def test_author_create_rejects_bad_orcid() -> None:
    with pytest.raises(ValidationError):
        AuthorCreate(full_name="Jane Doe", orcid="0000-0000-0000-0000")


def test_author_create_rejects_bad_email() -> None:
    with pytest.raises(ValidationError):
        AuthorCreate(full_name="Jane Doe", email="not-an-email")


def test_author_create_orcid_optional() -> None:
    a = AuthorCreate(full_name="Jane Doe")
    assert a.orcid is None and a.email is None


def test_author_create_empty_orcid_str_normalises_to_none() -> None:
    a = AuthorCreate(full_name="Jane Doe", orcid="")
    assert a.orcid is None


# ── CRediT roles ──────────────────────────────────────────────────────


def test_credit_roles_has_14() -> None:
    assert len(CREDIT_ROLES) == 14


def test_contribution_set_request_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        ContributionSetRequest(role="Bogus role")  # type: ignore[arg-type]


def test_contribution_set_request_accepts_all_14() -> None:
    for role in CREDIT_ROLES:
        r = ContributionSetRequest(role=role)
        assert r.role == role


# ── Funder + StructuredAbstract ───────────────────────────────────────


def test_funder_minimum_name_required() -> None:
    with pytest.raises(ValidationError):
        Funder(name="")


def test_structured_abstract_defaults_blank() -> None:
    s = StructuredAbstract()
    assert s.background == s.methods == s.results == s.conclusions == ""


def test_project_frontmatter_update_partial() -> None:
    p = ProjectFrontmatterUpdate(funding_statement="NIH grant 123")
    dumped = p.model_dump(exclude_unset=True)
    assert dumped == {"funding_statement": "NIH grant 123"}
