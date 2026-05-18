"""Phase 8.6 — GET /duplicates + POST /merge-duplicates."""
from __future__ import annotations

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


async def _seed(client, pid: str, items: list[dict]) -> list[str]:
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={"items": items},
    )
    assert r.status_code == 201, r.text
    return [a["id"] for a in r.json()["created"]]


def _md(**overrides) -> dict:
    base = {"title": "T", "authors": [], "year": 2023, "source": "doi"}
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_get_duplicates_returns_groups_for_doi_exact(client):
    pid = await _make_project(client)
    await _seed(
        client,
        pid,
        [
            _md(doi="10.1/x", title="A", source="doi"),
        ],
    )
    # Force a second row with the same DOI through the back door so
    # import-from-metadata can't auto-skip. We'll bypass dedup by importing
    # under a different DOI then patching the second row's DOI via the
    # generic articles PATCH endpoint.
    [id2] = await _seed(
        client,
        pid,
        [_md(doi="10.1/y", title="B", source="ris")],
    )
    pr = await client.patch(
        f"/api/articles/{id2}", json={"doi": "10.1/x"}
    )
    assert pr.status_code == 200, pr.text

    r = await client.get(f"/api/projects/{pid}/articles/duplicates")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["reason"] == "doi_exact"
    assert body[0]["score"] == 1.0


@pytest.mark.asyncio
async def test_get_duplicates_returns_groups_for_title_fuzzy(client):
    pid = await _make_project(client)
    await _seed(
        client,
        pid,
        [
            _md(
                title="Anterior versus Posterior in Total Hip Arthroplasty",
                year=2023,
                source="ris",
            ),
            _md(
                title="Anterior vs. posterior in total hip arthroplasty",
                year=2023,
                source="bibtex",
            ),
        ],
    )
    r = await client.get(f"/api/projects/{pid}/articles/duplicates")
    body = r.json()
    assert len(body) == 1
    assert body[0]["reason"] == "title_fuzzy"


@pytest.mark.asyncio
async def test_get_duplicates_returns_empty_when_no_duplicates(client):
    pid = await _make_project(client)
    await _seed(
        client,
        pid,
        [
            _md(title="Foo bar baz", source="ris"),
            _md(title="Quux quack qaz", source="bibtex"),
        ],
    )
    r = await client.get(f"/api/projects/{pid}/articles/duplicates")
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_duplicates_404_on_other_user_project(client):
    r = await client.get("/api/projects/missing/articles/duplicates")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_merge_duplicates_returns_kept_row(client):
    pid = await _make_project(client)
    ids = await _seed(
        client,
        pid,
        [
            _md(title="Keep", source="doi"),
            _md(title="Drop", source="ris"),
        ],
    )
    keep, drop = ids
    r = await client.post(
        f"/api/projects/{pid}/articles/merge-duplicates",
        json={"keep_id": keep, "drop_ids": [drop]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == keep


@pytest.mark.asyncio
async def test_merge_duplicates_422_on_cross_project(client):
    pid1 = await _make_project(client)
    pid2 = await _make_project(client)
    [keep] = await _seed(client, pid1, [_md(title="K")])
    [drop] = await _seed(client, pid2, [_md(title="D")])
    # Request the merge through project1's URL — keep belongs there, drop
    # belongs to project2 → 422 cross-project.
    r = await client.post(
        f"/api/projects/{pid1}/articles/merge-duplicates",
        json={"keep_id": keep, "drop_ids": [drop]},
    )
    assert r.status_code == 422
    assert "cross-project" in r.json()["detail"]


@pytest.mark.asyncio
async def test_merge_duplicates_422_on_self_merge(client):
    pid = await _make_project(client)
    [a] = await _seed(client, pid, [_md(title="A")])
    r = await client.post(
        f"/api/projects/{pid}/articles/merge-duplicates",
        json={"keep_id": a, "drop_ids": [a]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_merge_duplicates_rewires_highlights(client):
    """End-to-end: seed a highlight on a drop row; merge; assert it
    now belongs to the keep article."""
    pid = await _make_project(client)
    ids = await _seed(
        client,
        pid,
        [_md(title="Keep"), _md(title="Drop")],
    )
    keep, drop = ids
    # Create a highlight via the public API for the drop row.
    rh = await client.post(
        f"/api/articles/{drop}/highlights",
        json={
            "page_number": 1,
            "selected_text": "anchor text",
            "colour": "results",
            "section": "Results",
            "bounding_coords": {
                "rects": [{"x0": 0.0, "y0": 0.0, "x1": 0.5, "y1": 0.5}],
            },
        },
    )
    assert rh.status_code in (200, 201), rh.text
    highlight_id = rh.json()["id"]

    # Merge.
    mr = await client.post(
        f"/api/projects/{pid}/articles/merge-duplicates",
        json={"keep_id": keep, "drop_ids": [drop]},
    )
    assert mr.status_code == 200

    # The highlight now points at the keep article.
    list_r = await client.get(f"/api/articles/{keep}/highlights")
    assert list_r.status_code == 200
    ids_now = [h["id"] for h in list_r.json()]
    assert highlight_id in ids_now


@pytest.mark.asyncio
async def test_merge_duplicates_404_on_other_user(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/merge-duplicates",
        json={"keep_id": "ghost", "drop_ids": ["ghost2"]},
    )
    assert r.status_code == 404
