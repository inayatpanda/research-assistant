"""Phase 20 (MP20) — Checklist routes — CRUD happy paths + 404s."""
from __future__ import annotations

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "MP20 Project", "study_type": "Randomised Controlled Trial"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_list_catalogue_returns_metadata(client) -> None:
    r = await client.get("/api/checklists/catalogue")
    assert r.status_code == 200
    body = r.json()
    keys = {row["key"] for row in body}
    assert "CONSORT_2010" in keys
    assert "PRISMA_2020" in keys
    assert "CHEERS_2022" in keys
    consort = next(row for row in body if row["key"] == "CONSORT_2010")
    assert consort["item_count"] == 25


@pytest.mark.asyncio
async def test_get_catalogue_404_for_unknown_key(client) -> None:
    r = await client.get("/api/checklists/catalogue/NOPE")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_run_seeds_items_as_unclear(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CONSORT_2010", "title": "v1"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["checklist_key"] == "CONSORT_2010"
    assert body["title"] == "v1"
    assert len(body["items"]) == 25
    assert all(it["status"] == "unclear" for it in body["items"])
    assert body["overall_compliance_pct"] == 0.0


@pytest.mark.asyncio
async def test_patch_item_updates_status_and_compliance(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CARE", "title": "case 1"},
    )
    run = r.json()
    rid = run["id"]

    # Mark item 1 as pass and item 2 as na.
    p = await client.patch(
        f"/api/projects/{pid}/checklists/{rid}/items/1",
        json={"status": "pass", "comment": "Title fine"},
    )
    assert p.status_code == 200
    p = await client.patch(
        f"/api/projects/{pid}/checklists/{rid}/items/2",
        json={"status": "na"},
    )
    assert p.status_code == 200
    body = p.json()
    # 1 pass / (13 - 1 na) = 1/12 = 8.3
    assert body["overall_compliance_pct"] == 8.3
    by_id = {it["item_id"]: it for it in body["items"]}
    assert by_id["1"]["status"] == "pass"
    assert by_id["1"]["comment"] == "Title fine"
    assert by_id["2"]["status"] == "na"


@pytest.mark.asyncio
async def test_auto_check_route_maps_section_from_manuscript(client) -> None:
    pid = await _make_project(client)
    # Seed a Methodology section that mentions randomisation.
    sec = await client.put(
        f"/api/projects/{pid}/sections/Methodology",
        json={
            "section_name": "Methodology",
            "content": (
                "Randomisation was performed by computer-generated "
                "allocation sequence."
            ),
        },
    )
    assert sec.status_code == 200, sec.text

    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CONSORT_2010", "title": "v1"},
    )
    rid = r.json()["id"]
    a = await client.post(
        f"/api/projects/{pid}/checklists/{rid}/auto-check"
    )
    assert a.status_code == 200
    items = a.json()["items"]
    by_id = {i["item_id"]: i for i in items}
    assert by_id["8"]["mapped_section"] == "Methodology"
    assert by_id["8"]["mapped_text_excerpt"] is not None


@pytest.mark.asyncio
async def test_delete_run_returns_204_then_404(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "PRISMA_S", "title": "search v1"},
    )
    rid = r.json()["id"]
    d = await client.delete(f"/api/projects/{pid}/checklists/{rid}")
    assert d.status_code == 204
    g = await client.get(f"/api/projects/{pid}/checklists/{rid}")
    assert g.status_code == 404


@pytest.mark.asyncio
async def test_create_run_with_unknown_checklist_key_404(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "NOPE", "title": "v1"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_run_title_returns_409(client) -> None:
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CARE", "title": "v1"},
    )
    r2 = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CARE", "title": "v1"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_export_pdf_returns_pdf_bytes(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CARE", "title": "case 42"},
    )
    rid = r.json()["id"]
    e = await client.post(
        f"/api/projects/{pid}/checklists/{rid}/export?format=pdf"
    )
    assert e.status_code == 200
    assert e.headers["content-type"] == "application/pdf"
    assert e.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_export_docx_returns_docx_bytes(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CARE", "title": "case 42"},
    )
    rid = r.json()["id"]
    e = await client.post(
        f"/api/projects/{pid}/checklists/{rid}/export?format=docx"
    )
    assert e.status_code == 200
    assert "openxmlformats" in e.headers["content-type"]
    assert e.content[:2] == b"PK"
