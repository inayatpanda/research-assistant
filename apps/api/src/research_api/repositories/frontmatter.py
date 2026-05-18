"""Phase 10 — ICMJE front-matter repositories.

Three coordinated repositories sharing one AsyncSession:
  - AuthorRepository — CRUD + reorder + corresponding-author single-row
    enforcement.
  - AffiliationRepository — CRUD + reorder + author-affiliation m2m
    link/unlink + contribution set/clear (since the joins live on
    author_id/affiliation_id, they're logically owned here).
  - FrontmatterRepository — GET / PATCH the single per-project row.

All methods scope by user_id; cross-tenant attempts return None / 0 rows.

Reorder uses the same +1000 two-step UPDATE trick as `figures.py` so the
contiguous-position invariant survives the round-trip without tripping the
implicit ordering constraint mid-statement.
"""
from __future__ import annotations

from typing import Iterable, Protocol

from sqlalchemy import delete as sa_delete, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    Affiliation,
    Author,
    AuthorAffiliation,
    Contribution,
    ProjectFrontmatter,
    new_id,
)


# ── Authors ───────────────────────────────────────────────────────────


class AuthorRepository(Protocol):
    async def list(self, *, project_id: str, user_id: str) -> list[Author]: ...
    async def get(self, author_id: str, user_id: str) -> Author | None: ...
    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        full_name: str,
        given_name: str = "",
        family_name: str = "",
        orcid: str | None = None,
        email: str | None = None,
        is_corresponding: bool = False,
    ) -> Author: ...
    async def update(
        self,
        author_id: str,
        user_id: str,
        *,
        full_name: str | None = None,
        given_name: str | None = None,
        family_name: str | None = None,
        orcid: str | None = ...,
        email: str | None = ...,
        is_corresponding: bool | None = None,
    ) -> Author | None: ...
    async def reorder(
        self, *, project_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[Author]: ...
    async def set_corresponding(
        self, author_id: str, user_id: str
    ) -> Author | None: ...
    async def delete(self, author_id: str, user_id: str) -> Author | None: ...


# Sentinel for "leave unchanged" on Optional[str] fields in update().
_UNSET = object()


class SqliteAuthorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, *, project_id: str, user_id: str) -> list[Author]:
        stmt = (
            select(Author)
            .where(Author.project_id == project_id, Author.user_id == user_id)
            .order_by(Author.position.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, author_id: str, user_id: str) -> Author | None:
        stmt = select(Author).where(
            Author.id == author_id, Author.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _next_position(self, *, project_id: str, user_id: str) -> int:
        stmt = (
            select(Author.position)
            .where(Author.project_id == project_id, Author.user_id == user_id)
            .order_by(Author.position.desc())
            .limit(1)
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        return (existing or 0) + 1

    async def _clear_corresponding(
        self, *, project_id: str, user_id: str, exclude_id: str | None = None
    ) -> None:
        """Set is_corresponding=False for every author in the project scope.

        This single-shot UPDATE is the at-most-one-corresponding enforcement
        point. The repository runs it before any insert/update sets the flag
        true so a project can never end up with two corresponding authors.
        `exclude_id` lets `set_corresponding` skip the target row when
        clearing so the subsequent UPDATE doesn't bounce against the same
        row twice.
        """
        stmt = sa_update(Author).where(
            Author.project_id == project_id,
            Author.user_id == user_id,
            Author.is_corresponding == True,  # noqa: E712 — SQL bool literal
        )
        if exclude_id is not None:
            stmt = stmt.where(Author.id != exclude_id)
        await self.session.execute(stmt.values(is_corresponding=False))

    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        full_name: str,
        given_name: str = "",
        family_name: str = "",
        orcid: str | None = None,
        email: str | None = None,
        is_corresponding: bool = False,
    ) -> Author:
        if is_corresponding:
            await self._clear_corresponding(project_id=project_id, user_id=user_id)
        position = await self._next_position(project_id=project_id, user_id=user_id)
        author = Author(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            full_name=full_name,
            given_name=given_name,
            family_name=family_name,
            orcid=orcid,
            email=email,
            is_corresponding=is_corresponding,
            position=position,
        )
        self.session.add(author)
        await self.session.commit()
        await self.session.refresh(author)
        return author

    async def update(
        self,
        author_id: str,
        user_id: str,
        *,
        full_name: str | None = None,
        given_name: str | None = None,
        family_name: str | None = None,
        orcid: str | None = _UNSET,  # type: ignore[assignment]
        email: str | None = _UNSET,  # type: ignore[assignment]
        is_corresponding: bool | None = None,
    ) -> Author | None:
        existing = await self.get(author_id, user_id)
        if existing is None:
            return None
        if full_name is not None:
            existing.full_name = full_name
        if given_name is not None:
            existing.given_name = given_name
        if family_name is not None:
            existing.family_name = family_name
        if orcid is not _UNSET:
            existing.orcid = orcid  # type: ignore[assignment]
        if email is not _UNSET:
            existing.email = email  # type: ignore[assignment]
        if is_corresponding is True:
            await self._clear_corresponding(
                project_id=existing.project_id,
                user_id=user_id,
                exclude_id=existing.id,
            )
            existing.is_corresponding = True
        elif is_corresponding is False:
            existing.is_corresponding = False
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def set_corresponding(
        self, author_id: str, user_id: str
    ) -> Author | None:
        existing = await self.get(author_id, user_id)
        if existing is None:
            return None
        await self._clear_corresponding(
            project_id=existing.project_id,
            user_id=user_id,
            exclude_id=existing.id,
        )
        existing.is_corresponding = True
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def reorder(
        self, *, project_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[Author]:
        current = await self.list(project_id=project_id, user_id=user_id)
        if {a.id for a in current} != set(ordered_ids) or len(current) != len(ordered_ids):
            raise ValueError("ordered_author_ids does not match the project's author set")
        # Two-step shift to avoid any transient ordering collision.
        await self.session.execute(
            sa_update(Author)
            .where(Author.project_id == project_id, Author.user_id == user_id)
            .values(position=Author.position + 1000)
        )
        for idx, aid in enumerate(ordered_ids, start=1):
            await self.session.execute(
                sa_update(Author)
                .where(Author.id == aid, Author.user_id == user_id)
                .values(position=idx)
            )
        await self.session.commit()
        return await self.list(project_id=project_id, user_id=user_id)

    async def delete(self, author_id: str, user_id: str) -> Author | None:
        existing = await self.get(author_id, user_id)
        if existing is None:
            return None
        project_id = existing.project_id
        snapshot = Author(
            id=existing.id,
            user_id=existing.user_id,
            project_id=existing.project_id,
            full_name=existing.full_name,
            given_name=existing.given_name,
            family_name=existing.family_name,
            orcid=existing.orcid,
            email=existing.email,
            is_corresponding=existing.is_corresponding,
            position=existing.position,
        )
        await self.session.execute(
            sa_delete(Author).where(
                Author.id == author_id, Author.user_id == user_id
            )
        )
        # Recompact remaining positions.
        remaining_stmt = (
            select(Author)
            .where(Author.project_id == project_id, Author.user_id == user_id)
            .order_by(Author.position.asc())
        )
        remaining = list((await self.session.execute(remaining_stmt)).scalars().all())
        await self.session.execute(
            sa_update(Author)
            .where(Author.project_id == project_id, Author.user_id == user_id)
            .values(position=Author.position + 1000)
        )
        for idx, a in enumerate(remaining, start=1):
            await self.session.execute(
                sa_update(Author)
                .where(Author.id == a.id, Author.user_id == user_id)
                .values(position=idx)
            )
        await self.session.commit()
        return snapshot


# ── Affiliations ──────────────────────────────────────────────────────


class SqliteAffiliationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, *, project_id: str, user_id: str) -> list[Affiliation]:
        stmt = (
            select(Affiliation)
            .where(
                Affiliation.project_id == project_id,
                Affiliation.user_id == user_id,
            )
            .order_by(Affiliation.position.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, affiliation_id: str, user_id: str) -> Affiliation | None:
        stmt = select(Affiliation).where(
            Affiliation.id == affiliation_id, Affiliation.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _next_position(self, *, project_id: str, user_id: str) -> int:
        stmt = (
            select(Affiliation.position)
            .where(
                Affiliation.project_id == project_id,
                Affiliation.user_id == user_id,
            )
            .order_by(Affiliation.position.desc())
            .limit(1)
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        return (existing or 0) + 1

    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        name: str,
        address: str | None = None,
        city: str | None = None,
        country: str | None = None,
    ) -> Affiliation:
        position = await self._next_position(project_id=project_id, user_id=user_id)
        aff = Affiliation(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            name=name,
            address=address,
            city=city,
            country=country,
            position=position,
        )
        self.session.add(aff)
        await self.session.commit()
        await self.session.refresh(aff)
        return aff

    async def update(
        self,
        affiliation_id: str,
        user_id: str,
        *,
        name: str | None = None,
        address: str | None = _UNSET,  # type: ignore[assignment]
        city: str | None = _UNSET,  # type: ignore[assignment]
        country: str | None = _UNSET,  # type: ignore[assignment]
    ) -> Affiliation | None:
        existing = await self.get(affiliation_id, user_id)
        if existing is None:
            return None
        if name is not None:
            existing.name = name
        if address is not _UNSET:
            existing.address = address  # type: ignore[assignment]
        if city is not _UNSET:
            existing.city = city  # type: ignore[assignment]
        if country is not _UNSET:
            existing.country = country  # type: ignore[assignment]
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def reorder(
        self, *, project_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[Affiliation]:
        current = await self.list(project_id=project_id, user_id=user_id)
        if {a.id for a in current} != set(ordered_ids) or len(current) != len(ordered_ids):
            raise ValueError(
                "ordered_affiliation_ids does not match the project's affiliation set"
            )
        await self.session.execute(
            sa_update(Affiliation)
            .where(
                Affiliation.project_id == project_id,
                Affiliation.user_id == user_id,
            )
            .values(position=Affiliation.position + 1000)
        )
        for idx, fid in enumerate(ordered_ids, start=1):
            await self.session.execute(
                sa_update(Affiliation)
                .where(
                    Affiliation.id == fid, Affiliation.user_id == user_id
                )
                .values(position=idx)
            )
        await self.session.commit()
        return await self.list(project_id=project_id, user_id=user_id)

    async def delete(
        self, affiliation_id: str, user_id: str
    ) -> Affiliation | None:
        existing = await self.get(affiliation_id, user_id)
        if existing is None:
            return None
        project_id = existing.project_id
        snapshot = Affiliation(
            id=existing.id,
            user_id=existing.user_id,
            project_id=existing.project_id,
            name=existing.name,
            address=existing.address,
            city=existing.city,
            country=existing.country,
            position=existing.position,
        )
        await self.session.execute(
            sa_delete(Affiliation).where(
                Affiliation.id == affiliation_id,
                Affiliation.user_id == user_id,
            )
        )
        remaining_stmt = (
            select(Affiliation)
            .where(
                Affiliation.project_id == project_id,
                Affiliation.user_id == user_id,
            )
            .order_by(Affiliation.position.asc())
        )
        remaining = list((await self.session.execute(remaining_stmt)).scalars().all())
        await self.session.execute(
            sa_update(Affiliation)
            .where(
                Affiliation.project_id == project_id,
                Affiliation.user_id == user_id,
            )
            .values(position=Affiliation.position + 1000)
        )
        for idx, a in enumerate(remaining, start=1):
            await self.session.execute(
                sa_update(Affiliation)
                .where(
                    Affiliation.id == a.id, Affiliation.user_id == user_id
                )
                .values(position=idx)
            )
        await self.session.commit()
        return snapshot

    # ── m2m links ─────────────────────────────────────────────────────

    async def list_links_for_author(
        self, author_id: str, user_id: str
    ) -> list[AuthorAffiliation]:
        stmt = (
            select(AuthorAffiliation)
            .where(
                AuthorAffiliation.author_id == author_id,
                AuthorAffiliation.user_id == user_id,
            )
            .order_by(AuthorAffiliation.position.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_links_for_project(
        self, *, author_ids: Iterable[str], user_id: str
    ) -> list[AuthorAffiliation]:
        ids = list(author_ids)
        if not ids:
            return []
        stmt = (
            select(AuthorAffiliation)
            .where(
                AuthorAffiliation.user_id == user_id,
                AuthorAffiliation.author_id.in_(ids),
            )
            .order_by(AuthorAffiliation.position.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def link(
        self, *, author_id: str, affiliation_id: str, user_id: str
    ) -> AuthorAffiliation | None:
        """Create a m2m link if both sides exist and share user_id.

        Returns the existing link if one already exists (idempotent), or None
        if either side doesn't resolve under the calling user.
        """
        # Verify author + affiliation both belong to this user.
        author = (await self.session.execute(
            select(Author).where(
                Author.id == author_id, Author.user_id == user_id
            )
        )).scalar_one_or_none()
        if author is None:
            return None
        aff = (await self.session.execute(
            select(Affiliation).where(
                Affiliation.id == affiliation_id,
                Affiliation.user_id == user_id,
                Affiliation.project_id == author.project_id,
            )
        )).scalar_one_or_none()
        if aff is None:
            return None

        existing = (await self.session.execute(
            select(AuthorAffiliation).where(
                AuthorAffiliation.author_id == author_id,
                AuthorAffiliation.affiliation_id == affiliation_id,
                AuthorAffiliation.user_id == user_id,
            )
        )).scalar_one_or_none()
        if existing is not None:
            return existing

        # Append to the end of the author's affiliation list.
        last = (await self.session.execute(
            select(AuthorAffiliation.position)
            .where(
                AuthorAffiliation.author_id == author_id,
                AuthorAffiliation.user_id == user_id,
            )
            .order_by(AuthorAffiliation.position.desc())
            .limit(1)
        )).scalar_one_or_none()
        link = AuthorAffiliation(
            id=new_id(),
            user_id=user_id,
            author_id=author_id,
            affiliation_id=affiliation_id,
            position=(last or 0) + 1,
        )
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def unlink(
        self, *, author_id: str, affiliation_id: str, user_id: str
    ) -> bool:
        result = await self.session.execute(
            sa_delete(AuthorAffiliation).where(
                AuthorAffiliation.author_id == author_id,
                AuthorAffiliation.affiliation_id == affiliation_id,
                AuthorAffiliation.user_id == user_id,
            )
        )
        await self.session.commit()
        return (result.rowcount or 0) > 0


# ── Contributions ─────────────────────────────────────────────────────


class SqliteContributionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_author(
        self, author_id: str, user_id: str
    ) -> list[Contribution]:
        stmt = (
            select(Contribution)
            .where(
                Contribution.author_id == author_id,
                Contribution.user_id == user_id,
            )
            .order_by(Contribution.role.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_authors(
        self, *, author_ids: Iterable[str], user_id: str
    ) -> list[Contribution]:
        ids = list(author_ids)
        if not ids:
            return []
        stmt = select(Contribution).where(
            Contribution.user_id == user_id,
            Contribution.author_id.in_(ids),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def set(
        self, *, author_id: str, role: str, user_id: str
    ) -> Contribution | None:
        author = (await self.session.execute(
            select(Author).where(
                Author.id == author_id, Author.user_id == user_id
            )
        )).scalar_one_or_none()
        if author is None:
            return None
        existing = (await self.session.execute(
            select(Contribution).where(
                Contribution.author_id == author_id,
                Contribution.role == role,
                Contribution.user_id == user_id,
            )
        )).scalar_one_or_none()
        if existing is not None:
            return existing
        c = Contribution(
            id=new_id(),
            user_id=user_id,
            author_id=author_id,
            role=role,
        )
        self.session.add(c)
        await self.session.commit()
        await self.session.refresh(c)
        return c

    async def clear(
        self, *, author_id: str, role: str, user_id: str
    ) -> bool:
        result = await self.session.execute(
            sa_delete(Contribution).where(
                Contribution.author_id == author_id,
                Contribution.role == role,
                Contribution.user_id == user_id,
            )
        )
        await self.session.commit()
        return (result.rowcount or 0) > 0


# ── ProjectFrontmatter ────────────────────────────────────────────────


class SqliteFrontmatterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get(
        self, *, project_id: str, user_id: str
    ) -> ProjectFrontmatter | None:
        stmt = select(ProjectFrontmatter).where(
            ProjectFrontmatter.project_id == project_id,
            ProjectFrontmatter.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_or_create(
        self, *, project_id: str, user_id: str
    ) -> ProjectFrontmatter:
        existing = await self._get(project_id=project_id, user_id=user_id)
        if existing is not None:
            return existing
        row = ProjectFrontmatter(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            funders=[],
            structured_abstract_enabled=False,
            structured_abstract={
                "background": "",
                "methods": "",
                "results": "",
                "conclusions": "",
            },
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get(
        self, *, project_id: str, user_id: str
    ) -> ProjectFrontmatter | None:
        return await self._get(project_id=project_id, user_id=user_id)

    async def update(
        self,
        *,
        project_id: str,
        user_id: str,
        patch: dict,
    ) -> ProjectFrontmatter | None:
        existing = await self.get_or_create(
            project_id=project_id, user_id=user_id
        )
        for key, value in patch.items():
            if value is None and key not in {
                "funding_statement",
                "ethics_irb",
                "ethics_approval_number",
                "ethics_consent",
                "conflicts_statement",
            }:
                continue
            setattr(existing, key, value)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
