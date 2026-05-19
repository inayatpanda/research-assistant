"""Phase 17 (MP17) — SAP integrity hash + DOCX/PDF export tests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from research_api.services.export.sap import (
    build_sap_document,
    compute_integrity_hash,
)


@dataclass
class _FakeProject:
    title: str
    study_type: str = "rct"


@dataclass
class _FakePlan:
    name: str
    steps: list[dict]
    integrity_hash: str | None = None
    locked_at: datetime | None = None


# ── Integrity hash determinism ──────────────────────────────────────────────


def test_integrity_hash_is_deterministic_across_dict_key_order():
    steps_a = [{"type": "test", "args": {"test_key": "independent_t", "alpha": 0.05}}]
    steps_b = [{"args": {"alpha": 0.05, "test_key": "independent_t"}, "type": "test"}]
    assert compute_integrity_hash(steps_a) == compute_integrity_hash(steps_b)


def test_integrity_hash_changes_when_step_added():
    base = [{"type": "test", "args": {"test_key": "independent_t"}}]
    extended = base + [{"type": "plot", "args": {"geom": "box"}}]
    assert compute_integrity_hash(base) != compute_integrity_hash(extended)


def test_integrity_hash_rounds_floats_to_eight_places():
    """Two payloads that only differ in the 12th decimal place hash identically."""
    steps_a = [{"type": "test", "args": {"alpha": 0.05000000000001}}]
    steps_b = [{"type": "test", "args": {"alpha": 0.0500000000000002}}]
    assert compute_integrity_hash(steps_a) == compute_integrity_hash(steps_b)


def test_integrity_hash_distinguishes_floats_at_seventh_place():
    """The 8-decimal-place rounding cut-off means two floats differing in
    the 7th decimal place produce different hashes."""
    steps_a = [{"type": "test", "args": {"alpha": 0.0500001}}]
    steps_b = [{"type": "test", "args": {"alpha": 0.0500002}}]
    assert compute_integrity_hash(steps_a) != compute_integrity_hash(steps_b)


def test_integrity_hash_list_order_matters():
    """Steps are an ordered sequence; reordering must change the hash."""
    steps_a = [{"type": "test", "args": {}}, {"type": "plot", "args": {}}]
    steps_b = [{"type": "plot", "args": {}}, {"type": "test", "args": {}}]
    assert compute_integrity_hash(steps_a) != compute_integrity_hash(steps_b)


def test_integrity_hash_handles_nan_inf():
    """NaN/Inf should encode to fixed tokens so hashes are stable across hosts."""
    h1 = compute_integrity_hash([{"type": "test", "args": {"v": float("nan")}}])
    h2 = compute_integrity_hash([{"type": "test", "args": {"v": float("nan")}}])
    assert h1 == h2
    h_inf = compute_integrity_hash([{"type": "test", "args": {"v": float("inf")}}])
    assert h_inf != h1


def test_integrity_hash_empty_steps_is_stable():
    h1 = compute_integrity_hash([])
    h2 = compute_integrity_hash([])
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


# ── SAP document builder ────────────────────────────────────────────────────


def test_build_sap_document_docx_returns_zip_bytes():
    project = _FakeProject(title="Hip Replacement RCT")
    plan = _FakePlan(
        name="Primary Analysis",
        steps=[
            {"type": "test", "args": {"test_key": "independent_t", "hypothesis": "H1"}},
            {"type": "test", "args": {"test_key": "cox_ph", "primary_or_secondary": "secondary"}},
        ],
    )
    payload = build_sap_document(project, plan, fmt="docx")
    assert payload[:2] == b"PK"  # DOCX is a zip


def test_build_sap_document_pdf_starts_with_pdf_magic():
    project = _FakeProject(title="Hip Replacement RCT")
    plan = _FakePlan(name="Primary", steps=[{"type": "test", "args": {}}])
    payload = build_sap_document(project, plan, fmt="pdf")
    assert payload.startswith(b"%PDF")


def test_build_sap_document_includes_integrity_hash_when_present():
    project = _FakeProject(title="X")
    plan = _FakePlan(
        name="P",
        steps=[{"type": "test", "args": {}}],
        integrity_hash="abcdef" * 10 + "1234",
    )
    payload = build_sap_document(project, plan, fmt="docx")
    # Search for the hash substring in the DOCX bytes (it's stored in
    # document.xml inside the zip; substring match is reliable).
    import zipfile, io
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
    assert "abcdef" in document_xml


def test_build_sap_document_rejects_unknown_format():
    project = _FakeProject(title="X")
    plan = _FakePlan(name="P", steps=[])
    with pytest.raises(ValueError):
        build_sap_document(project, plan, fmt="rtf")
