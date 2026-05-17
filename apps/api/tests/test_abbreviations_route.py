import pytest


async def _make_project(client) -> str:
    r = await client.post("/api/projects", json={"title": "P", "study_type": "Outcome Study"})
    return r.json()["id"]


@pytest.mark.asyncio
async def test_list_empty_initially(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/abbreviations")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_replace_then_list(client):
    pid = await _make_project(client)
    r = await client.put(
        f"/api/projects/{pid}/abbreviations",
        json={
            "items": [
                {"short_form": "THA", "long_form": "Total hip arthroplasty"},
                {"short_form": "HHS", "long_form": "Harris Hip Score"},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert {a["short_form"] for a in body} == {"THA", "HHS"}

    listing = await client.get(f"/api/projects/{pid}/abbreviations")
    assert {a["short_form"] for a in listing.json()} == {"THA", "HHS"}


@pytest.mark.asyncio
async def test_replace_is_idempotent_overwriting(client):
    pid = await _make_project(client)
    await client.put(
        f"/api/projects/{pid}/abbreviations",
        json={"items": [{"short_form": "THA", "long_form": "Total hip arthroplasty"}]},
    )
    # Replace with a different set entirely — old row must be gone
    await client.put(
        f"/api/projects/{pid}/abbreviations",
        json={"items": [{"short_form": "HHS", "long_form": "Harris Hip Score"}]},
    )
    listing = await client.get(f"/api/projects/{pid}/abbreviations")
    abbrs = {a["short_form"] for a in listing.json()}
    assert abbrs == {"HHS"}


@pytest.mark.asyncio
async def test_unknown_project_404s(client):
    r = await client.get("/api/projects/nope/abbreviations")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_individual(client):
    pid = await _make_project(client)
    created = await client.put(
        f"/api/projects/{pid}/abbreviations",
        json={"items": [{"short_form": "THA", "long_form": "Total hip arthroplasty"}]},
    )
    aid = created.json()[0]["id"]
    r = await client.delete(f"/api/abbreviations/{aid}")
    assert r.status_code == 204
    listing = await client.get(f"/api/projects/{pid}/abbreviations")
    assert listing.json() == []


@pytest.mark.asyncio
async def test_dedupe_short_form_in_request(client):
    pid = await _make_project(client)
    r = await client.put(
        f"/api/projects/{pid}/abbreviations",
        json={
            "items": [
                {"short_form": "THA", "long_form": "Total hip arthroplasty"},
                {"short_form": "THA", "long_form": "dupe"},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["long_form"] == "Total hip arthroplasty"  # first wins
