from __future__ import annotations

from research_api.services.review.extraction_schema import (
    EXTRACTION_SCHEMA,
    Field,
    FieldGroup,
    validate,
)


def test_all_groups_present():
    keys = [g.key for g in EXTRACTION_SCHEMA]
    assert keys == [
        "basic", "population", "intervention", "comparator",
        "outcomes", "funding", "notes",
    ]
    for g in EXTRACTION_SCHEMA:
        assert isinstance(g, FieldGroup)
        assert g.label
        assert g.fields


def test_required_fields_marked_required():
    required_by_group = {g.key: [f.key for f in g.fields if f.required] for g in EXTRACTION_SCHEMA}
    assert "first_author" in required_by_group["basic"]
    assert "year" in required_by_group["basic"]
    assert "n_total" in required_by_group["population"]
    assert "name" in required_by_group["intervention"]


def test_field_dataclass_shape():
    for group in EXTRACTION_SCHEMA:
        for f in group.fields:
            assert isinstance(f, Field)
            assert f.key
            assert f.label
            assert f.type in {"text", "number", "enum", "list"}
            if f.type == "enum":
                assert f.choices is not None
                assert len(f.choices) >= 1
            else:
                assert f.choices is None or len(f.choices) >= 0


def _complete_fields() -> dict:
    return {
        "basic": {
            "first_author": "Smith",
            "year": 2020,
            "country": "UK",
            "design": "RCT",
        },
        "population": {
            "n_total": 120,
            "mean_age": 55.0,
            "sex_male_pct": 60.0,
            "inclusion": "adults",
            "exclusion": "pregnant",
        },
        "intervention": {
            "name": "Drug A",
            "dose_or_protocol": "10mg/day",
            "duration_weeks": 12,
        },
        "comparator": {"name": "Placebo", "dose_or_protocol": "matched"},
        "outcomes": [
            {"name": "VAS", "timepoint": "12w", "estimate": 2.1,
             "ci_low": 1.5, "ci_high": 2.7, "p_value": 0.001, "units": "score"},
        ],
        "funding": {"source": "NIH", "coi_disclosed": "yes"},
        "notes": {"free_text": "n/a"},
    }


def test_validate_passes_for_complete_record():
    errors = validate(_complete_fields())
    assert errors == {}


def test_validate_fails_for_missing_first_author():
    data = _complete_fields()
    del data["basic"]["first_author"]
    errors = validate(data)
    assert "basic" in errors
    assert any("first_author" in e for e in errors["basic"])


def test_validate_fails_for_missing_year():
    data = _complete_fields()
    del data["basic"]["year"]
    errors = validate(data)
    assert "basic" in errors
    assert any("year" in e for e in errors["basic"])


def test_validate_fails_for_invalid_design_enum():
    data = _complete_fields()
    data["basic"]["design"] = "not_a_design"
    errors = validate(data)
    assert "basic" in errors
    assert any("design" in e for e in errors["basic"])


def test_validate_fails_for_negative_n_total():
    data = _complete_fields()
    data["population"]["n_total"] = -1
    errors = validate(data)
    assert "population" in errors
    assert any("n_total" in e for e in errors["population"])


def test_outcomes_list_can_be_empty():
    data = _complete_fields()
    data["outcomes"] = []
    errors = validate(data)
    assert errors == {}


def test_validate_coerces_numeric_strings():
    data = _complete_fields()
    data["basic"]["year"] = "2020"
    data["population"]["n_total"] = "42"
    errors = validate(data)
    assert errors == {}


def test_validate_fails_for_non_numeric_string():
    data = _complete_fields()
    data["population"]["n_total"] = "not_a_number"
    errors = validate(data)
    assert "population" in errors


def test_validate_fails_for_outcomes_not_list():
    data = _complete_fields()
    data["outcomes"] = {"name": "VAS"}
    errors = validate(data)
    assert "outcomes" in errors


def test_validate_empty_required_string_is_error():
    data = _complete_fields()
    data["basic"]["first_author"] = ""
    errors = validate(data)
    assert "basic" in errors


def test_validate_coi_enum_membership():
    data = _complete_fields()
    data["funding"]["coi_disclosed"] = "maybe"
    errors = validate(data)
    assert "funding" in errors
