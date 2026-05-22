"""Fix-E2E/4 — A fresh SR-typed project must boot without any 500.

The live walkthrough captured a single 500 when navigating to
``/projects/<id>/systematic-review`` on a fresh project. The SR page fans
out to a handful of optional endpoints — GRADE, PROSPERO, MeSH, search
strategies, sr_depth (narrative / instruments), living review, etc. — and
one of them was returning 500 on empty data. This regression hits every
SR-related GET that the page exercises on first load to make sure they
all return 200 (or 404) instead of a server error.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_sr_page_boot_all_optional_endpoints_no_500(client):
    # Create a fresh Systematic-Review project.
    res = await client.post(
        "/api/projects",
        json={
            "title": "Fresh SR project",
            "study_type": "Systematic Review",
            "citation_style": "vancouver",
            "ai_provider": "gemini",
        },
    )
    assert res.status_code in (200, 201), res.text
    pid = res.json()["id"]

    # The SR page fires these GETs on mount (cf. SystematicReviewPage.tsx +
    # the various sub-tab components). Each must come back without a 500;
    # 200 / 404 / 422 are all OK for "no data yet".
    paths = [
        f"/api/projects/{pid}/reviews",
        f"/api/projects/{pid}/reviews/search",
        f"/api/projects/{pid}/reviews/screening",
        f"/api/projects/{pid}/reviews/screening?stage=title_abstract",
        f"/api/projects/{pid}/reviews/screening?stage=full_text",
        f"/api/projects/{pid}/reviews/rob",
        f"/api/projects/{pid}/reviews/rob/tools",
        f"/api/projects/{pid}/reviews/extraction",
        f"/api/projects/{pid}/reviews/extraction/schema",
        f"/api/projects/{pid}/reviews/prisma",
        f"/api/projects/{pid}/reviews/meta",
        f"/api/projects/{pid}/review/grade",
        f"/api/projects/{pid}/review/prospero",
        f"/api/projects/{pid}/review/living",
        f"/api/projects/{pid}/review/living/hits",
        f"/api/projects/{pid}/review/mesh/cache",
        f"/api/projects/{pid}/review/search-strategies",
        f"/api/projects/{pid}/review/narrative-synthesis",
        f"/api/projects/{pid}/review/outcome-instruments",
    ]

    failures: list[tuple[str, int, str]] = []
    for p in paths:
        r = await client.get(p)
        if r.status_code >= 500:
            failures.append((p, r.status_code, r.text[:200]))

    assert not failures, f"SR-page boot returned 5xx on:\n" + "\n".join(
        f"  {p} -> {s}: {body}" for p, s, body in failures
    )
