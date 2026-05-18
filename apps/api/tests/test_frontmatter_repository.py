"""Phase 10 — repository unit tests for authors/affiliations/contributions/
frontmatter.

Exercises:
  - author position assigned + recompacted on delete
  - corresponding-author single-row enforcement
  - reorder fails when ids don't match the scope
  - affiliations m2m link/unlink + cross-project rejection
  - contributions set/clear, idempotent
  - frontmatter auto-creates on first GET
"""
from __future__ import annotations

import pytest

from research_api.db.models import Project, new_id
from research_api.repositories.frontmatter import (
    SqliteAffiliationRepository,
    SqliteAuthorRepository,
    SqliteContributionRepository,
    SqliteFrontmatterRepository,
)


async def _seed_project(session, *, user_id: str = "alice", title: str = "P") -> Project:
    p = Project(
        id=new_id(),
        user_id=user_id,
        title=title,
        study_type="Outcome Study",
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest.mark.asyncio
async def test_create_author_assigns_position_1(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(
        project_id=proj.id, user_id="alice", full_name="Jane Doe"
    )
    assert a.position == 1
    assert a.is_corresponding is False


@pytest.mark.asyncio
async def test_create_author_positions_are_sequential(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(project_id=proj.id, user_id="alice", full_name="A")
    b = await repo.create(project_id=proj.id, user_id="alice", full_name="B")
    c = await repo.create(project_id=proj.id, user_id="alice", full_name="C")
    assert [a.position, b.position, c.position] == [1, 2, 3]


@pytest.mark.asyncio
async def test_only_one_corresponding_per_project(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(
        project_id=proj.id, user_id="alice", full_name="A",
        is_corresponding=True,
    )
    b = await repo.create(
        project_id=proj.id, user_id="alice", full_name="B",
        is_corresponding=True,
    )
    rows = await repo.list(project_id=proj.id, user_id="alice")
    correspondings = [r for r in rows if r.is_corresponding]
    assert len(correspondings) == 1
    assert correspondings[0].id == b.id
    assert a.id != correspondings[0].id


@pytest.mark.asyncio
async def test_set_corresponding_clears_others(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(
        project_id=proj.id, user_id="alice", full_name="A",
        is_corresponding=True,
    )
    b = await repo.create(project_id=proj.id, user_id="alice", full_name="B")
    await repo.set_corresponding(b.id, "alice")
    rows = await repo.list(project_id=proj.id, user_id="alice")
    assert {r.id: r.is_corresponding for r in rows} == {a.id: False, b.id: True}


@pytest.mark.asyncio
async def test_corresponding_isolation_across_projects(session) -> None:
    """A corresponding author in project A must not be cleared when project B
    sets its own corresponding author.
    """
    p1 = await _seed_project(session, title="P1")
    p2 = await _seed_project(session, title="P2")
    repo = SqliteAuthorRepository(session)
    a1 = await repo.create(
        project_id=p1.id, user_id="alice", full_name="A1",
        is_corresponding=True,
    )
    await repo.create(
        project_id=p2.id, user_id="alice", full_name="B1",
        is_corresponding=True,
    )
    a1_fresh = await repo.get(a1.id, "alice")
    assert a1_fresh is not None
    assert a1_fresh.is_corresponding is True


@pytest.mark.asyncio
async def test_reorder_authors_rejects_foreign_ids(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(project_id=proj.id, user_id="alice", full_name="A")
    b = await repo.create(project_id=proj.id, user_id="alice", full_name="B")
    with pytest.raises(ValueError):
        await repo.reorder(
            project_id=proj.id,
            user_id="alice",
            ordered_ids=[a.id, b.id, "nonexistent"],
        )


@pytest.mark.asyncio
async def test_reorder_authors_renumbers_positions(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(project_id=proj.id, user_id="alice", full_name="A")
    b = await repo.create(project_id=proj.id, user_id="alice", full_name="B")
    c = await repo.create(project_id=proj.id, user_id="alice", full_name="C")
    out = await repo.reorder(
        project_id=proj.id,
        user_id="alice",
        ordered_ids=[c.id, a.id, b.id],
    )
    assert [r.id for r in out] == [c.id, a.id, b.id]
    assert [r.position for r in out] == [1, 2, 3]


@pytest.mark.asyncio
async def test_delete_author_recompacts_positions(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(project_id=proj.id, user_id="alice", full_name="A")
    b = await repo.create(project_id=proj.id, user_id="alice", full_name="B")
    c = await repo.create(project_id=proj.id, user_id="alice", full_name="C")
    await repo.delete(b.id, "alice")
    rows = await repo.list(project_id=proj.id, user_id="alice")
    assert [r.id for r in rows] == [a.id, c.id]
    assert [r.position for r in rows] == [1, 2]


@pytest.mark.asyncio
async def test_update_author_orcid_can_be_cleared(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAuthorRepository(session)
    a = await repo.create(
        project_id=proj.id,
        user_id="alice",
        full_name="Jane",
        orcid="0000-0002-1825-0097",
    )
    assert a.orcid == "0000-0002-1825-0097"
    # Explicit None should clear ORCID.
    updated = await repo.update(a.id, "alice", orcid=None)
    assert updated is not None
    assert updated.orcid is None


# ── Affiliations + m2m ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_affiliation_create_and_list(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteAffiliationRepository(session)
    a = await repo.create(
        project_id=proj.id, user_id="alice", name="Oxford"
    )
    b = await repo.create(
        project_id=proj.id, user_id="alice", name="Cambridge"
    )
    rows = await repo.list(project_id=proj.id, user_id="alice")
    assert [r.id for r in rows] == [a.id, b.id]
    assert [r.position for r in rows] == [1, 2]


@pytest.mark.asyncio
async def test_link_author_to_affiliation(session) -> None:
    proj = await _seed_project(session)
    author = await SqliteAuthorRepository(session).create(
        project_id=proj.id, user_id="alice", full_name="Jane"
    )
    aff = await SqliteAffiliationRepository(session).create(
        project_id=proj.id, user_id="alice", name="Oxford"
    )
    aff_repo = SqliteAffiliationRepository(session)
    link = await aff_repo.link(
        author_id=author.id, affiliation_id=aff.id, user_id="alice"
    )
    assert link is not None
    # Idempotent.
    link2 = await aff_repo.link(
        author_id=author.id, affiliation_id=aff.id, user_id="alice"
    )
    assert link2 is not None
    assert link.id == link2.id


@pytest.mark.asyncio
async def test_link_rejects_cross_project_affiliation(session) -> None:
    """An author in project A cannot be linked to an affiliation in project B
    (even if both belong to the same user)."""
    p1 = await _seed_project(session, title="P1")
    p2 = await _seed_project(session, title="P2")
    author = await SqliteAuthorRepository(session).create(
        project_id=p1.id, user_id="alice", full_name="Jane"
    )
    aff_in_p2 = await SqliteAffiliationRepository(session).create(
        project_id=p2.id, user_id="alice", name="Other"
    )
    aff_repo = SqliteAffiliationRepository(session)
    link = await aff_repo.link(
        author_id=author.id,
        affiliation_id=aff_in_p2.id,
        user_id="alice",
    )
    assert link is None


@pytest.mark.asyncio
async def test_link_rejects_other_users_author(session) -> None:
    p_alice = await _seed_project(session, user_id="alice", title="A")
    p_bob = await _seed_project(session, user_id="bob", title="B")
    alice_author = await SqliteAuthorRepository(session).create(
        project_id=p_alice.id, user_id="alice", full_name="Jane"
    )
    bob_aff = await SqliteAffiliationRepository(session).create(
        project_id=p_bob.id, user_id="bob", name="Bob U"
    )
    aff_repo = SqliteAffiliationRepository(session)
    # Bob tries to link Alice's author to his affiliation.
    link = await aff_repo.link(
        author_id=alice_author.id,
        affiliation_id=bob_aff.id,
        user_id="bob",
    )
    assert link is None


@pytest.mark.asyncio
async def test_unlink_returns_false_when_missing(session) -> None:
    proj = await _seed_project(session)
    aff_repo = SqliteAffiliationRepository(session)
    removed = await aff_repo.unlink(
        author_id="nope", affiliation_id="nope", user_id="alice"
    )
    assert removed is False


# ── Contributions ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_contribution_set_is_idempotent(session) -> None:
    proj = await _seed_project(session)
    author = await SqliteAuthorRepository(session).create(
        project_id=proj.id, user_id="alice", full_name="J"
    )
    repo = SqliteContributionRepository(session)
    c1 = await repo.set(
        author_id=author.id, role="Conceptualization", user_id="alice"
    )
    c2 = await repo.set(
        author_id=author.id, role="Conceptualization", user_id="alice"
    )
    assert c1 is not None and c2 is not None
    assert c1.id == c2.id
    rows = await repo.list_for_author(author.id, "alice")
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_contribution_clear(session) -> None:
    proj = await _seed_project(session)
    author = await SqliteAuthorRepository(session).create(
        project_id=proj.id, user_id="alice", full_name="J"
    )
    repo = SqliteContributionRepository(session)
    await repo.set(author_id=author.id, role="Methodology", user_id="alice")
    removed = await repo.clear(
        author_id=author.id, role="Methodology", user_id="alice"
    )
    assert removed is True
    rows = await repo.list_for_author(author.id, "alice")
    assert rows == []


@pytest.mark.asyncio
async def test_contribution_set_rejects_other_users_author(session) -> None:
    p_alice = await _seed_project(session, user_id="alice", title="A")
    alice_author = await SqliteAuthorRepository(session).create(
        project_id=p_alice.id, user_id="alice", full_name="J"
    )
    repo = SqliteContributionRepository(session)
    out = await repo.set(
        author_id=alice_author.id, role="Methodology", user_id="bob"
    )
    assert out is None


# ── Frontmatter ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_frontmatter_get_or_create_initialises_row(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFrontmatterRepository(session)
    row = await repo.get_or_create(project_id=proj.id, user_id="alice")
    assert row.structured_abstract_enabled is False
    assert row.funders == []


@pytest.mark.asyncio
async def test_frontmatter_get_or_create_is_idempotent(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFrontmatterRepository(session)
    a = await repo.get_or_create(project_id=proj.id, user_id="alice")
    b = await repo.get_or_create(project_id=proj.id, user_id="alice")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_frontmatter_update_patches_fields(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFrontmatterRepository(session)
    await repo.update(
        project_id=proj.id,
        user_id="alice",
        patch={
            "funding_statement": "NIH grant",
            "funders": [{"name": "NIH", "grant_id": "R01-1234"}],
            "ethics_irb": "Local IRB",
            "structured_abstract_enabled": True,
            "structured_abstract": {
                "background": "B",
                "methods": "M",
                "results": "R",
                "conclusions": "C",
            },
        },
    )
    row = await repo.get(project_id=proj.id, user_id="alice")
    assert row is not None
    assert row.funding_statement == "NIH grant"
    assert row.funders == [{"name": "NIH", "grant_id": "R01-1234"}]
    assert row.structured_abstract_enabled is True
    assert row.structured_abstract == {
        "background": "B",
        "methods": "M",
        "results": "R",
        "conclusions": "C",
    }
