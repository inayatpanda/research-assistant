"""Phase 10 — happy-path frontmatter route tests via the live ASGI app."""
from __future__ import annotations

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "P", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_authors_crud_round_trip(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/authors",
        json={
            "full_name": "Jane Doe",
            "given_name": "Jane",
            "family_name": "Doe",
            "orcid": "0000-0002-1825-0097",
            "email": "jane@example.com",
            "is_corresponding": True,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    aid = body["id"]
    assert body["position"] == 1
    assert body["is_corresponding"] is True
    assert body["affiliation_ids"] == []

    # List
    r = await client.get(f"/api/projects/{pid}/authors")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Patch
    r = await client.patch(
        f"/api/authors/{aid}", json={"family_name": "DoeX"}
    )
    assert r.status_code == 200
    assert r.json()["family_name"] == "DoeX"
    # ORCID intentionally cleared
    r = await client.patch(f"/api/authors/{aid}", json={"orcid": None})
    assert r.status_code == 200
    assert r.json()["orcid"] is None

    # Delete
    r = await client.delete(f"/api/authors/{aid}")
    assert r.status_code == 204
    r = await client.get(f"/api/projects/{pid}/authors")
    assert r.json() == []


@pytest.mark.asyncio
async def test_orcid_validation_422_via_route(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/authors",
        json={"full_name": "Jane", "orcid": "0000-0000-0000-0000"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_set_corresponding_route_flips_unique(client) -> None:
    pid = await _make_project(client)
    a = (
        await client.post(
            f"/api/projects/{pid}/authors",
            json={"full_name": "A", "is_corresponding": True},
        )
    ).json()
    b = (
        await client.post(
            f"/api/projects/{pid}/authors",
            json={"full_name": "B"},
        )
    ).json()
    r = await client.post(f"/api/authors/{b['id']}/set-corresponding")
    assert r.status_code == 200
    rows = (await client.get(f"/api/projects/{pid}/authors")).json()
    correspondings = [r for r in rows if r["is_corresponding"]]
    assert len(correspondings) == 1
    assert correspondings[0]["id"] == b["id"]


@pytest.mark.asyncio
async def test_link_unlink_author_affiliation(client) -> None:
    pid = await _make_project(client)
    aid = (
        await client.post(
            f"/api/projects/{pid}/authors", json={"full_name": "Jane"}
        )
    ).json()["id"]
    fid = (
        await client.post(
            f"/api/projects/{pid}/affiliations",
            json={"name": "Oxford", "city": "Oxford", "country": "UK"},
        )
    ).json()["id"]
    r = await client.post(f"/api/authors/{aid}/affiliations/{fid}")
    assert r.status_code == 200
    assert r.json()["affiliation_ids"] == [fid]
    r = await client.delete(f"/api/authors/{aid}/affiliations/{fid}")
    assert r.status_code == 200
    assert r.json()["affiliation_ids"] == []


@pytest.mark.asyncio
async def test_contributions_matrix_round_trip(client) -> None:
    pid = await _make_project(client)
    aid = (
        await client.post(
            f"/api/projects/{pid}/authors", json={"full_name": "Jane"}
        )
    ).json()["id"]
    # Set 3 roles.
    for role in ["Conceptualization", "Methodology", "Validation"]:
        r = await client.post(
            f"/api/authors/{aid}/contributions", json={"role": role}
        )
        assert r.status_code == 201, r.text
    listed = await client.get(f"/api/authors/{aid}/contributions")
    assert listed.status_code == 200
    assert {c["role"] for c in listed.json()} == {
        "Conceptualization", "Methodology", "Validation"
    }
    # Clear one.
    r = await client.delete(f"/api/authors/{aid}/contributions/Validation")
    assert r.status_code == 204
    listed = (await client.get(f"/api/authors/{aid}/contributions")).json()
    assert {c["role"] for c in listed} == {"Conceptualization", "Methodology"}


@pytest.mark.asyncio
async def test_contribution_rejects_unknown_role(client) -> None:
    pid = await _make_project(client)
    aid = (
        await client.post(
            f"/api/projects/{pid}/authors", json={"full_name": "J"}
        )
    ).json()["id"]
    r = await client.post(
        f"/api/authors/{aid}/contributions", json={"role": "Bogus"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_frontmatter_get_auto_creates(client) -> None:
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/frontmatter")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["structured_abstract_enabled"] is False
    assert body["structured_abstract"] == {
        "background": "", "methods": "", "results": "", "conclusions": ""
    }
    assert body["funders"] == []


@pytest.mark.asyncio
async def test_frontmatter_patch_round_trip(client) -> None:
    pid = await _make_project(client)
    r = await client.patch(
        f"/api/projects/{pid}/frontmatter",
        json={
            "funding_statement": "NIH",
            "funders": [{"name": "NIH", "grant_id": "R01-123"}],
            "ethics_irb": "Local IRB",
            "ethics_approval_number": "IRB-2024-01",
            "ethics_consent": "Written informed consent",
            "conflicts_statement": "None declared",
            "structured_abstract_enabled": True,
            "structured_abstract": {
                "background": "B",
                "methods": "M",
                "results": "R",
                "conclusions": "C",
            },
        },
    )
    assert r.status_code == 200, r.text
    out = (await client.get(f"/api/projects/{pid}/frontmatter")).json()
    assert out["funding_statement"] == "NIH"
    assert out["funders"] == [{"name": "NIH", "grant_id": "R01-123"}]
    assert out["structured_abstract_enabled"] is True
    assert out["structured_abstract"]["methods"] == "M"
    assert out["conflicts_statement"] == "None declared"


@pytest.mark.asyncio
async def test_authors_reorder_route(client) -> None:
    pid = await _make_project(client)
    aid_a = (
        await client.post(
            f"/api/projects/{pid}/authors", json={"full_name": "A"}
        )
    ).json()["id"]
    aid_b = (
        await client.post(
            f"/api/projects/{pid}/authors", json={"full_name": "B"}
        )
    ).json()["id"]
    aid_c = (
        await client.post(
            f"/api/projects/{pid}/authors", json={"full_name": "C"}
        )
    ).json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/authors/reorder",
        json={"ordered_author_ids": [aid_c, aid_a, aid_b]},
    )
    assert r.status_code == 200
    rows = r.json()
    assert [a["id"] for a in rows] == [aid_c, aid_a, aid_b]
    assert [a["position"] for a in rows] == [1, 2, 3]
