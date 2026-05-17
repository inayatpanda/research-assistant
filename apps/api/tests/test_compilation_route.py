"""E2E for the compilation pipeline."""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


async def _setup_two_articles(client):
    proj = (
        await client.post("/api/projects", json={"title": "P", "study_type": "Outcome Study"})
    ).json()
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    a1 = (
        await client.post(
            f"/api/projects/{proj['id']}/articles/upload",
            files={"file": ("a.pdf", pdf, "application/pdf")},
        )
    ).json()["article"]
    a2 = (
        await client.post(
            f"/api/projects/{proj['id']}/articles/upload",
            files={"file": ("b.pdf", pdf, "application/pdf")},
        )
    ).json()["article"]
    # Each upload returns metadata from the FakeAI; both will have the same
    # authors/year ('First Author','Second Author', 2024). Patch one so they
    # produce distinct citations.
    await client.patch(
        f"/api/articles/{a2['id']}",
        json={"title": "Other Study", "authors": ["Smith", "Lee"], "year": 2023},
    )
    a2_after = (await client.get(f"/api/articles/{a2['id']}")).json()
    return proj["id"], a1, a2_after


def _payload(text: str, colour: str = "results", section: str = "Results") -> dict:
    return {
        "page_number": 1,
        "selected_text": text,
        "colour": colour,
        "section": section,
        "bounding_coords": {"rects": [{"x0": 0, "y0": 0, "x1": 0.1, "y1": 0.05}]},
        "user_note": f"paraphrase for {text[:10]}",
    }


@pytest.mark.asyncio
async def test_compilation_view_aggregates_with_formatted_citation(client):
    project_id, a1, a2 = await _setup_two_articles(client)
    await client.post(
        f"/api/articles/{a1['id']}/highlights", json=_payload("first result")
    )
    await client.post(
        f"/api/articles/{a2['id']}/highlights", json=_payload("second result")
    )
    await client.post(
        f"/api/articles/{a1['id']}/highlights",
        json=_payload("intro context", colour="intro", section="Introduction"),
    )

    r = await client.get(f"/api/projects/{project_id}/compilation/results")
    assert r.status_code == 200
    body = r.json()
    assert body["colour"] == "results"
    assert body["section"] == "Results"
    assert len(body["cards"]) == 2
    # Citation must be formatted server-side from the article's authors/year
    citations = [c["citation"] for c in body["cards"]]
    assert any("Smith & Lee, 2023" in c for c in citations)


@pytest.mark.asyncio
async def test_compilation_view_unknown_project_404s(client):
    r = await client.get("/api/projects/nonexistent/compilation/results")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_card_draft_replaces_cite_token(client):
    project_id, a1, _ = await _setup_two_articles(client)
    h = (
        await client.post(
            f"/api/articles/{a1['id']}/highlights", json=_payload("anterior faster")
        )
    ).json()
    r = await client.post(f"/api/highlights/{h['id']}/draft")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["highlight_id"] == h["id"]
    # FakeAI returns 'This study reported on the topic [CITE_a1].'
    # The server must have replaced [CITE_a1] → (Author, Year)
    assert "[CITE_" not in body["draft"]
    assert "(" in body["draft"] and ")" in body["draft"]
    assert body["used_citation"]


@pytest.mark.asyncio
async def test_section_draft_aggregates_all_cards(client):
    project_id, a1, a2 = await _setup_two_articles(client)
    await client.post(
        f"/api/articles/{a1['id']}/highlights", json=_payload("finding A")
    )
    await client.post(
        f"/api/articles/{a2['id']}/highlights", json=_payload("finding B")
    )
    r = await client.post(f"/api/projects/{project_id}/compilation/results/draft")
    assert r.status_code == 200
    body = r.json()
    assert "[CITE_" not in body["draft"]
    assert len(body["used_citations"]) == 2


@pytest.mark.asyncio
async def test_section_draft_empty_section_422s(client):
    project_id, _, _ = await _setup_two_articles(client)
    r = await client.post(f"/api/projects/{project_id}/compilation/discussion/draft")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_reorder_updates_sort_order(client):
    project_id, a1, _ = await _setup_two_articles(client)
    h1 = (
        await client.post(
            f"/api/articles/{a1['id']}/highlights", json=_payload("A")
        )
    ).json()
    h2 = (
        await client.post(
            f"/api/articles/{a1['id']}/highlights", json=_payload("B")
        )
    ).json()
    r = await client.patch(
        f"/api/projects/{project_id}/compilation/results/order",
        json={
            "items": [
                {"highlight_id": h1["id"], "sort_order": 10},
                {"highlight_id": h2["id"], "sort_order": 5},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    # h2 had sort_order=5 → comes first
    assert [c["selected_text"] for c in body["cards"]] == ["B", "A"]


@pytest.mark.asyncio
async def test_unknown_colour_422(client):
    project_id, _, _ = await _setup_two_articles(client)
    r = await client.get(f"/api/projects/{project_id}/compilation/purple")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_reorder_ignores_out_of_scope_highlights(client):
    """Security regression: passing a highlight_id from a different project/colour
    must NOT mutate that highlight's sort_order."""
    project_a, a1, _ = await _setup_two_articles(client)
    # Create a separate project + article + highlight
    proj_b = (
        await client.post(
            "/api/projects", json={"title": "OtherProject", "study_type": "Outcome Study"}
        )
    ).json()
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    a3 = (
        await client.post(
            f"/api/projects/{proj_b['id']}/articles/upload",
            files={"file": ("c.pdf", pdf, "application/pdf")},
        )
    ).json()["article"]
    foreign_h = (
        await client.post(
            f"/api/articles/{a3['id']}/highlights",
            json=_payload("foreign", colour="intro", section="Introduction"),
        )
    ).json()

    home_h = (
        await client.post(
            f"/api/articles/{a1['id']}/highlights", json=_payload("home")
        )
    ).json()

    # Try to mutate the foreign highlight's sort_order via project A's results reorder
    await client.patch(
        f"/api/projects/{project_a}/compilation/results/order",
        json={
            "items": [
                {"highlight_id": foreign_h["id"], "sort_order": 999},
                {"highlight_id": home_h["id"], "sort_order": 7},
            ]
        },
    )
    # Foreign highlight unchanged
    foreign_now = (
        await client.get(f"/api/projects/{proj_b['id']}/compilation/intro")
    ).json()["cards"][0]
    assert foreign_now["sort_order"] != 999
    # Home highlight got its update
    home_now = (
        await client.get(f"/api/projects/{project_a}/compilation/results")
    ).json()["cards"][0]
    assert home_now["sort_order"] == 7
