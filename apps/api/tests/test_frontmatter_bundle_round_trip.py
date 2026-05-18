"""Phase 10 — bundle export → import round-trip for ICMJE front-matter.

Drives the live ASGI app: create authors/affiliations/contributions/frontmatter
on project A, export the bundle, swap user, re-import into a fresh project,
then assert all the rows arrived with fresh PKs and the right cross-table
linkage. Mirrors `test_bundle_import.py`.
"""
from __future__ import annotations

import json

import pytest

from research_api.container import get_container


def _switch_user(uid: str) -> None:
    get_container().settings.local_user_id = uid


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_bundle_round_trip_carries_frontmatter(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)

    # Two affiliations
    aff1 = (
        await client.post(
            f"/api/projects/{pid}/affiliations",
            json={"name": "Oxford", "city": "Oxford", "country": "UK"},
        )
    ).json()
    aff2 = (
        await client.post(
            f"/api/projects/{pid}/affiliations",
            json={"name": "Cambridge"},
        )
    ).json()

    # Two authors, with linked affiliations + corresponding
    a1 = (
        await client.post(
            f"/api/projects/{pid}/authors",
            json={
                "full_name": "Inayat Choudhary",
                "email": "inayat@example.com",
                "is_corresponding": True,
                "orcid": "0000-0002-1825-0097",
            },
        )
    ).json()
    a2 = (
        await client.post(
            f"/api/projects/{pid}/authors",
            json={"full_name": "Sarah Johnson"},
        )
    ).json()

    await client.post(f"/api/authors/{a1['id']}/affiliations/{aff1['id']}")
    await client.post(f"/api/authors/{a2['id']}/affiliations/{aff2['id']}")

    # Contributions on a1
    for role in ("Conceptualization", "Methodology"):
        await client.post(
            f"/api/authors/{a1['id']}/contributions", json={"role": role}
        )

    # Front matter
    await client.patch(
        f"/api/projects/{pid}/frontmatter",
        json={
            "funding_statement": "Supported by NIH.",
            "funders": [{"name": "NIH", "grant_id": "R01-123"}],
            "ethics_irb": "Local IRB",
            "conflicts_statement": "None declared.",
            "structured_abstract_enabled": True,
            "structured_abstract": {
                "background": "B",
                "methods": "M",
                "results": "R",
                "conclusions": "C",
            },
        },
    )

    # Export bundle as alice
    bundle_resp = await client.post(f"/api/projects/{pid}/export/bundle")
    assert bundle_resp.status_code == 200
    bundle = json.loads(bundle_resp.content)

    # Sanity-check the bundle has the new keys with the right cardinalities
    assert len(bundle["authors"]) == 2
    assert len(bundle["affiliations"]) == 2
    assert len(bundle["author_affiliations"]) == 2
    assert len(bundle["contributions"]) == 2
    assert bundle["project_frontmatter"] is not None
    assert bundle["project_frontmatter"]["structured_abstract_enabled"] is True

    # Now re-import as bob (different user).
    _switch_user("bob")
    body = json.dumps(bundle)
    imp = await client.post(
        "/api/projects/import/bundle",
        files={"file": ("bundle.json", body.encode(), "application/json")},
    )
    assert imp.status_code == 200, imp.text
    counts = imp.json()["counts"]
    assert counts["authors"] == 2
    assert counts["affiliations"] == 2
    assert counts["author_affiliations"] == 2
    assert counts["contributions"] == 2
    assert counts["project_frontmatter"] == 1

    new_pid = imp.json()["project_id"]

    # The fresh project has 2 authors and the corresponding flag is preserved
    bob_authors = (await client.get(f"/api/projects/{new_pid}/authors")).json()
    assert len(bob_authors) == 2
    correspondings = [a for a in bob_authors if a["is_corresponding"]]
    assert len(correspondings) == 1
    assert correspondings[0]["full_name"] == "Inayat Choudhary"
    # ORCID survived
    assert correspondings[0]["orcid"] == "0000-0002-1825-0097"

    # Affiliations carried with positions
    bob_affs = (await client.get(f"/api/projects/{new_pid}/affiliations")).json()
    assert [a["name"] for a in bob_affs] == ["Oxford", "Cambridge"]

    # Contributions on the corresponding author survived
    bob_a1_id = correspondings[0]["id"]
    contributions = (
        await client.get(f"/api/authors/{bob_a1_id}/contributions")
    ).json()
    assert {c["role"] for c in contributions} == {"Conceptualization", "Methodology"}

    # Frontmatter carried
    fm = (await client.get(f"/api/projects/{new_pid}/frontmatter")).json()
    assert fm["funding_statement"] == "Supported by NIH."
    assert fm["funders"] == [{"name": "NIH", "grant_id": "R01-123"}]
    assert fm["structured_abstract_enabled"] is True
    assert fm["structured_abstract"]["background"] == "B"

    # Cross-user isolation: bob's new author IDs differ from alice's.
    assert {a["id"] for a in bob_authors}.isdisjoint({a1["id"], a2["id"]})


@pytest.mark.asyncio
async def test_bundle_import_caps_corresponding_to_one(client) -> None:
    """Even if the bundle smuggles two is_corresponding=True authors, the
    import path must respect the single-corresponding invariant."""
    _switch_user("alice")
    # Build a minimal bundle by hand to inject two correspondings.
    bundle = {
        "schema_version": 1,
        "project": {
            "title": "Imported",
            "study_type": "Outcome Study",
            "citation_style": "vancouver",
            "ai_provider": "gemini",
        },
        "articles": [],
        "highlights": [],
        "article_notes": [],
        "manuscript_sections": [],
        "abbreviations": [],
        "datasets": [],
        "dataset_variables": [],
        "analyses": [],
        "analysis_results": [],
        "review": None,
        "search_records": [],
        "screening_records": [],
        "rob_assessments": [],
        "extraction_records": [],
        "figures": [],
        "consort_data": None,
        "meta_analyses": [],
        "meta_inputs": [],
        "authors": [
            {
                "id": "x1",
                "full_name": "A",
                "position": 1,
                "is_corresponding": True,
            },
            {
                "id": "x2",
                "full_name": "B",
                "position": 2,
                "is_corresponding": True,
            },
        ],
        "affiliations": [],
        "author_affiliations": [],
        "contributions": [],
        "project_frontmatter": None,
    }
    body = json.dumps(bundle)
    imp = await client.post(
        "/api/projects/import/bundle",
        files={"file": ("b.json", body.encode(), "application/json")},
    )
    assert imp.status_code == 200, imp.text
    new_pid = imp.json()["project_id"]
    rows = (await client.get(f"/api/projects/{new_pid}/authors")).json()
    correspondings = [r for r in rows if r["is_corresponding"]]
    assert len(correspondings) == 1
