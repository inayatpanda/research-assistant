"""Phase 12 — Submission-package builder unit tests (pure function)."""
from __future__ import annotations

import io
import zipfile

from research_api.services.export.submission_package import (
    CoverLetterPayload,
    FigurePackageItem,
    ReviewerResponsePayload,
    build_submission_zip,
    slugify_for_zip,
)


class _Project:
    def __init__(self, title: str, citation_style: str = "vancouver") -> None:
        self.title = title
        self.study_type = "Outcome Study"
        self.citation_style = citation_style


class _Section:
    __slots__ = ("section_name", "content")

    def __init__(self, name: str, content: str) -> None:
        self.section_name = name
        self.content = content


def _basic_sections() -> list[_Section]:
    return [
        _Section("Abstract", "<p>Hello world.</p>"),
        _Section(
            "Methodology",
            "<p>Methods text.</p>"
            "<table><tr><th>Var</th><th>n</th></tr><tr><td>A</td><td>10</td></tr></table>",
        ),
        _Section(
            "Results",
            "<p>Results.</p>"
            "<table><tr><td>x</td></tr></table>",
        ),
    ]


def test_slugify_strips_path_traversal() -> None:
    assert slugify_for_zip("../../etc/passwd") == "etcpasswd"
    assert slugify_for_zip("hello world") == "hello-world"
    assert slugify_for_zip("") == "project"
    assert slugify_for_zip(None) == "project"
    # Special chars stripped.
    assert slugify_for_zip("My/Project: Title") == "MyProject-Title"


def test_build_submission_zip_basic_layout() -> None:
    project = _Project("Knee OA RCT")
    sections = _basic_sections()
    figures = [
        FigurePackageItem(figure_number=1, ext="png", data=b"\x89PNG\r\n"),
        FigurePackageItem(figure_number=2, ext="jpg", data=b"\xff\xd8\xff"),
    ]
    cl = CoverLetterPayload(
        body_html="<p>Dear Editor</p>", target_journal_label="JBJS"
    )
    rr = [
        ReviewerResponsePayload(
            reviewer_label="Reviewer 1",
            comments=[
                {"comment_text": "Add power calc.", "response_html": "<p>Done.</p>"}
            ],
        )
    ]
    filename, blob = build_submission_zip(
        project=project,
        sections=sections,
        articles=[],
        frontmatter=None,
        figures=figures,
        cover_letter=cl,
        reviewer_responses=rr,
        bibliography=[],
        style="vancouver",
    )
    assert filename == "Knee-OA-RCT_vdraft.zip"
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = sorted(zf.namelist())
    slug = "Knee-OA-RCT"
    assert f"{slug}/manuscript.docx" in names
    assert f"{slug}/Figure_1.png" in names
    assert f"{slug}/Figure_2.jpg" in names
    # Two tables in the manuscript → Table_1.docx and Table_2.docx.
    assert f"{slug}/Table_1.docx" in names
    assert f"{slug}/Table_2.docx" in names
    assert f"{slug}/cover_letter.docx" in names
    assert f"{slug}/response_to_reviewers.docx" in names


def test_build_submission_zip_omits_response_when_no_reviewers() -> None:
    project = _Project("Plain Study")
    filename, blob = build_submission_zip(
        project=project,
        sections=[_Section("Abstract", "<p>x</p>")],
        articles=[],
        frontmatter=None,
        figures=[],
        cover_letter=None,
        reviewer_responses=[],
        bibliography=[],
        style="vancouver",
    )
    assert filename == "Plain-Study_vdraft.zip"
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
    assert any(n.endswith("/cover_letter.docx") for n in names)
    assert not any(n.endswith("/response_to_reviewers.docx") for n in names)


def test_build_submission_zip_versions_from_snapshot_label() -> None:
    project = _Project("Demo")
    filename, _ = build_submission_zip(
        project=project,
        sections=[],
        articles=[],
        frontmatter=None,
        figures=[],
        cover_letter=None,
        reviewer_responses=[],
        bibliography=[],
        style="vancouver",
        snapshot_label="v1 — initial submission",
    )
    # The em-dash and spaces in the label are stripped (em-dash → hyphen
    # plus the existing surrounding spaces collapse into double hyphens).
    assert filename.startswith("Demo_v")
    assert filename.endswith(".zip")
    # Slug should have collapsed spaces to hyphens and stripped the em-dash.
    # Expected: "v1--initial-submission" — adjacent hyphens are preserved
    # because the slugifier only strips characters outside [A-Za-z0-9_-].
    assert "v1" in filename and "initial-submission" in filename


def test_build_submission_zip_rejects_path_traversal_ext() -> None:
    project = _Project("Demo")
    figures = [
        FigurePackageItem(figure_number=1, ext="../etc/passwd", data=b"x"),
    ]
    _, blob = build_submission_zip(
        project=project,
        sections=[],
        articles=[],
        frontmatter=None,
        figures=figures,
        cover_letter=None,
        reviewer_responses=[],
        bibliography=[],
        style="vancouver",
    )
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
    # Sanitised → bin extension, no traversal.
    assert any(n.endswith("/Figure_1.bin") for n in names)
    assert not any(".." in n for n in names)
