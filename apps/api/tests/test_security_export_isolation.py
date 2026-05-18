"""Phase 8 security regression: prove every export/import/bibliography endpoint
is scoped by `user_id`. Also verifies that imported bundles are re-stamped to
the importing user regardless of `user_id` fields baked into the payload.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from research_api.container import get_container
from research_api.db.models import (
    Article,
    ManuscriptSection,
    Project,
)
from research_api.services.export.bundle_export import BundleInputs, build_bundle


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(
    client, title: str = "P", style: str = "vancouver",
) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Outcome Study", "citation_style": style},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(*, title: str, project_id: str, user_id: str) -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            user_id=user_id, project_id=project_id, title=title,
            authors=["Doe J"], year=2024, journal="J",
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


async def _seed_section(
    *, project_id: str, section_name: str, content: str, user_id: str,
) -> None:
    container = get_container()
    async with container.session_factory() as session:
        s = ManuscriptSection(
            user_id=user_id, project_id=project_id,
            section_name=section_name, content=content,
            word_count=len(content.split()),
        )
        session.add(s)
        await session.commit()


def _bundle_with_attacker_user(user_id_in_payload: str = "attacker") -> dict:
    p = Project(
        id="proj-orig", user_id=user_id_in_payload,
        title="Attacker bundle", study_type="Outcome Study",
        citation_style="vancouver", ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    a = Article(
        id="art-orig", user_id=user_id_in_payload, project_id="proj-orig",
        title="Article A", authors=["Doe J"], year=2024,
    )
    a.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    sec = ManuscriptSection(
        id="s-orig", user_id=user_id_in_payload, project_id="proj-orig",
        section_name="Introduction", content="<p>[CITE_art-orig]</p>",
        word_count=1,
    )
    sec.updated_at = datetime(2025, 1, 3, tzinfo=timezone.utc)
    return build_bundle(
        BundleInputs(project=p, articles=[a], manuscript_sections=[sec])
    )


# ── Cross-user 404 ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_docx_isolated_across_users(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/export/docx")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_pdf_isolated_across_users(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/export/pdf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_bundle_isolated_across_users(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/export/bundle")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_bibliography_isolated_across_users(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/bibliography")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_bibliography_isolated_with_style_param(client):
    _switch_user("user-a")
    pid = await _make_project(client, title="A")

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/bibliography?style=apa")
    assert r.status_code == 404


# ── Cross-user bundle export does not leak data ────────────────────────


@pytest.mark.asyncio
async def test_export_bundle_only_returns_own_data(client):
    _switch_user("user-a")
    pa = await _make_project(client, title="A-proj")
    await _seed_article(title="A-article", project_id=pa, user_id="user-a")

    _switch_user("user-b")
    pb = await _make_project(client, title="B-proj")

    # User B cannot export user A's bundle.
    r = await client.post(f"/api/projects/{pa}/export/bundle")
    assert r.status_code == 404

    # User B's own bundle has nothing from A.
    r2 = await client.post(f"/api/projects/{pb}/export/bundle")
    body = json.loads(r2.content)
    assert body["project"]["title"] == "B-proj"
    assert body["articles"] == []


# ── Import re-stamps to importing user ─────────────────────────────────


@pytest.mark.asyncio
async def test_import_re_assigns_user_id_to_current_user(client):
    _switch_user("user-a")
    bundle = _bundle_with_attacker_user(user_id_in_payload="user-b")
    files = {"file": ("b.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 200, r.text
    new_pid = r.json()["project_id"]

    container = get_container()
    async with container.session_factory() as session:
        for table in (Project, Article, ManuscriptSection):
            rows = (await session.execute(select(table))).scalars().all()
            for row in rows:
                assert row.user_id == "user-a", f"{table.__name__} not re-stamped"

        proj = (
            await session.execute(
                select(Project).where(Project.id == new_pid)
            )
        ).scalar_one()
        assert proj.user_id == "user-a"


@pytest.mark.asyncio
async def test_import_ignores_attacker_user_id_in_bundle_payload(client):
    _switch_user("victim")
    bundle = _bundle_with_attacker_user(user_id_in_payload="attacker")
    bundle["project"]["user_id"] = "attacker"
    files = {"file": ("b.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 200, r.text

    container = get_container()
    async with container.session_factory() as session:
        proj = (await session.execute(select(Project))).scalar_one()
        assert proj.user_id == "victim"


@pytest.mark.asyncio
async def test_import_does_not_clobber_existing_user_projects(client):
    _switch_user("user-b")
    own_pid = await _make_project(client, title="MINE")

    bundle = _bundle_with_attacker_user(user_id_in_payload="user-a")
    files = {"file": ("b.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 200
    new_pid = r.json()["project_id"]
    assert new_pid != own_pid

    container = get_container()
    async with container.session_factory() as session:
        rows = (await session.execute(select(Project))).scalars().all()
        titles = sorted(p.title for p in rows)
        assert "MINE" in titles
        for p in rows:
            assert p.user_id == "user-b"


# ── Import size & content caps ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_size_cap_enforced(client):
    payload = b"{" + b" " * (51 * 1024 * 1024) + b"}"
    files = {"file": ("big.json", payload, "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_import_rejects_garbage_content(client):
    files = {"file": ("garbage.bin", b"\x00\x01\x02\x03\x04", "application/octet-stream")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code in (415, 400)


@pytest.mark.asyncio
async def test_import_rejects_missing_schema_version(client):
    bundle = _bundle_with_attacker_user()
    del bundle["schema_version"]
    files = {"file": ("b.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_import_rejects_wrong_schema_version(client):
    bundle = _bundle_with_attacker_user()
    bundle["schema_version"] = 99
    files = {"file": ("b.json", json.dumps(bundle).encode(), "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_import_rejects_non_json_text(client):
    files = {"file": ("readme.txt", b"This is plain text, not a bundle.", "text/plain")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_import_rejects_top_level_array(client):
    files = {"file": ("b.json", b"[1, 2, 3]", "application/json")}
    r = await client.post("/api/projects/import/bundle", files=files)
    assert r.status_code == 415


# ── Filename slugification ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_filename_strips_path_traversal(client):
    pid = await _make_project(client, title="../../etc/passwd")
    r = await client.post(f"/api/projects/{pid}/export/docx")
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    fn = cd.split("filename=")[1].strip('"')
    assert "/" not in fn
    assert ".." not in fn
    assert "\\" not in fn
    assert fn.endswith(".docx")


@pytest.mark.asyncio
async def test_export_filename_safe_for_pdf(client):
    pid = await _make_project(client, title="<script>alert(1)</script>")
    r = await client.post(f"/api/projects/{pid}/export/pdf")
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    fn = cd.split("filename=")[1].strip('"')
    assert "<" not in fn
    assert ">" not in fn
    assert "/" not in fn


@pytest.mark.asyncio
async def test_export_filename_safe_for_bundle(client):
    pid = await _make_project(client, title="cd /; rm -rf *")
    r = await client.post(f"/api/projects/{pid}/export/bundle")
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    fn = cd.split("filename=")[1].strip('"')
    assert "/" not in fn
    assert " " not in fn
    assert "*" not in fn


# ── Cross-project isolation, same user ────────────────────────────────


@pytest.mark.asyncio
async def test_bibliography_isolated_across_projects(client):
    pid_x = await _make_project(client, title="X")
    pid_y = await _make_project(client, title="Y")
    a_x = await _seed_article(title="X-art", project_id=pid_x, user_id="local-user")
    await _seed_section(
        project_id=pid_x, section_name="Introduction",
        content=f"<p>[CITE_{a_x}]</p>",
        user_id="local-user",
    )
    r = await client.get(f"/api/projects/{pid_y}/bibliography")
    assert r.status_code == 200
    assert r.json()["entries"] == []
