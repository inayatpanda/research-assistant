from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

FieldType = Literal["text", "number", "enum", "list"]


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    type: FieldType
    required: bool = False
    choices: tuple[str, ...] | None = None
    allow_negative: bool = False


@dataclass(frozen=True)
class FieldGroup:
    key: str
    label: str
    fields: tuple[Field, ...]


_DESIGN_CHOICES = (
    "RCT", "cohort", "case_control", "case_series",
    "cross_sectional", "qualitative", "other",
)


_COI_CHOICES = ("yes", "no", "unclear")


EXTRACTION_SCHEMA: tuple[FieldGroup, ...] = (
    FieldGroup(
        key="basic",
        label="Basic study info",
        fields=(
            Field("first_author", "First author", "text", required=True),
            Field("year", "Year", "number", required=True),
            Field("country", "Country", "text"),
            Field("design", "Study design", "enum", choices=_DESIGN_CHOICES),
        ),
    ),
    FieldGroup(
        key="population",
        label="Population",
        fields=(
            Field("n_total", "Total participants", "number", required=True),
            Field("mean_age", "Mean age", "number", allow_negative=False),
            Field("sex_male_pct", "Sex (% male)", "number"),
            Field("inclusion", "Inclusion criteria", "text"),
            Field("exclusion", "Exclusion criteria", "text"),
        ),
    ),
    FieldGroup(
        key="intervention",
        label="Intervention",
        fields=(
            Field("name", "Intervention name", "text", required=True),
            Field("dose_or_protocol", "Dose or protocol", "text"),
            Field("duration_weeks", "Duration (weeks)", "number"),
        ),
    ),
    FieldGroup(
        key="comparator",
        label="Comparator",
        fields=(
            Field("name", "Comparator name", "text"),
            Field("dose_or_protocol", "Dose or protocol", "text"),
        ),
    ),
    FieldGroup(
        key="outcomes",
        label="Outcomes",
        fields=(
            Field("outcomes", "Outcomes list", "list"),
        ),
    ),
    FieldGroup(
        key="funding",
        label="Funding & conflicts",
        fields=(
            Field("source", "Funding source", "text"),
            Field("coi_disclosed", "Conflict of interest disclosed", "enum",
                  choices=_COI_CHOICES),
        ),
    ),
    FieldGroup(
        key="notes",
        label="Notes",
        fields=(
            Field("free_text", "Free-text notes", "text"),
        ),
    ),
)


_GROUP_BY_KEY: dict[str, FieldGroup] = {g.key: g for g in EXTRACTION_SCHEMA}


def _coerce_number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            if "." in s or "e" in s or "E" in s:
                return float(s)
            return int(s)
        except ValueError:
            return None
    return None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _validate_field(f: Field, value: Any) -> str | None:
    if _is_empty(value):
        if f.required:
            return f"{f.key} is required"
        return None
    if f.type == "text":
        if not isinstance(value, str):
            return f"{f.key} must be text"
        return None
    if f.type == "number":
        coerced = _coerce_number(value)
        if coerced is None:
            return f"{f.key} must be a number"
        if not f.allow_negative and isinstance(coerced, (int, float)) and coerced < 0:
            return f"{f.key} must be non-negative"
        return None
    if f.type == "enum":
        if f.choices is None or value not in f.choices:
            return f"{f.key} must be one of {f.choices}"
        return None
    if f.type == "list":
        if not isinstance(value, list):
            return f"{f.key} must be a list"
        return None
    return None


def _validate_outcomes_group(value: Any) -> list[str]:
    errors: list[str] = []
    if value is None:
        return errors
    if not isinstance(value, list):
        return ["outcomes must be a list"]
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"outcomes[{i}] must be an object")
            continue
        if not item.get("name"):
            errors.append(f"outcomes[{i}].name is required")
    return errors


def validate(fields: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    for group in EXTRACTION_SCHEMA:
        group_value = fields.get(group.key)
        if group.key == "outcomes":
            outcomes_value = group_value
            if isinstance(group_value, dict) and "outcomes" in group_value:
                outcomes_value = group_value["outcomes"]
            group_errors = _validate_outcomes_group(outcomes_value)
            if group_errors:
                errors[group.key] = group_errors
            continue
        if group_value is None:
            group_value = {}
        if not isinstance(group_value, dict):
            errors[group.key] = [f"{group.key} must be an object"]
            continue
        group_errors: list[str] = []
        for f in group.fields:
            err = _validate_field(f, group_value.get(f.key))
            if err:
                group_errors.append(err)
        if group_errors:
            errors[group.key] = group_errors
    return errors
