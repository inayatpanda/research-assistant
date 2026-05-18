"""Phase 8.7 Task 0 — verify 'Randomised Controlled Trial' is an accepted StudyType."""
from __future__ import annotations

import pytest

from research_api.schemas.project import ProjectCreate, ProjectUpdate


def test_project_create_accepts_rct_study_type() -> None:
    pc = ProjectCreate(title="An RCT", study_type="Randomised Controlled Trial")
    assert pc.study_type == "Randomised Controlled Trial"


def test_project_update_accepts_rct_study_type() -> None:
    pu = ProjectUpdate(study_type="Randomised Controlled Trial")
    assert pu.study_type == "Randomised Controlled Trial"


def test_project_create_rejects_unknown_study_type() -> None:
    with pytest.raises(Exception):
        ProjectCreate(title="bad", study_type="Bogus Type")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_route_persists_rct(client) -> None:
    r = await client.post(
        "/api/projects",
        json={"title": "Trial 1", "study_type": "Randomised Controlled Trial"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["study_type"] == "Randomised Controlled Trial"
