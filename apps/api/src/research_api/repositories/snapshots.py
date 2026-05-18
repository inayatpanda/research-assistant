"""Phase 11 — Manuscript snapshot repository.

Snapshots are immutable point-in-time JSON blobs of every table the
manuscript writer cares about: sections, ICMJE front-matter (authors,
affiliations, links, contributions, project_frontmatter), figures,
abbreviations, meta_analyses, extraction_records.

`create_from_current` assembles the blob by reading the live tables for
the project, so the caller only supplies a label + optional description.
There is no `update` — to "edit" a snapshot, delete and recreate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    Abbreviation,
    Affiliation,
    Article,
    Author,
    AuthorAffiliation,
    Contribution,
    ExtractionRecord,
    Figure,
    ManuscriptSection,
    ManuscriptSnapshot,
    MetaAnalysis,
    ProjectFrontmatter,
    Review,
    new_id,
)


class SnapshotLabelConflict(ValueError):
    """Raised when (project_id, user_id, label) already exists."""


class SnapshotRepository(Protocol):
    async def list_for_project(
        self, *, project_id: str, user_id: str
    ) -> list[ManuscriptSnapshot]: ...
    async def get(
        self, snapshot_id: str, user_id: str
    ) -> ManuscriptSnapshot | None: ...
    async def create_from_current(
        self,
        *,
        project_id: str,
        user_id: str,
        label: str,
        description: str | None,
    ) -> ManuscriptSnapshot: ...
    async def delete(
        self, snapshot_id: str, user_id: str
    ) -> ManuscriptSnapshot | None: ...


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _row_to_jsonable(row: Any) -> dict[str, Any]:
    """Mirror bundle_export._row_to_dict but inlined to avoid a circular import."""
    out: dict[str, Any] = {}
    for col in row.__table__.columns:
        value = getattr(row, col.name)
        if isinstance(value, datetime):
            out[col.name] = _iso(value)
        else:
            out[col.name] = value
    return out


class SqliteSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, *, project_id: str, user_id: str
    ) -> list[ManuscriptSnapshot]:
        stmt = (
            select(ManuscriptSnapshot)
            .where(
                ManuscriptSnapshot.project_id == project_id,
                ManuscriptSnapshot.user_id == user_id,
            )
            .order_by(ManuscriptSnapshot.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, snapshot_id: str, user_id: str
    ) -> ManuscriptSnapshot | None:
        stmt = select(ManuscriptSnapshot).where(
            ManuscriptSnapshot.id == snapshot_id,
            ManuscriptSnapshot.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _assemble_blob(
        self, *, project_id: str, user_id: str
    ) -> dict[str, Any]:
        """Read every project-scoped table the snapshot should capture.

        Each list is sorted by a stable key (position / id) so two snapshots
        of the same state diff cleanly when serialised line-by-line.
        """
        sections = list((await self.session.execute(
            select(ManuscriptSection).where(
                ManuscriptSection.project_id == project_id,
                ManuscriptSection.user_id == user_id,
            ).order_by(ManuscriptSection.section_name.asc())
        )).scalars().all())

        authors = list((await self.session.execute(
            select(Author).where(
                Author.project_id == project_id,
                Author.user_id == user_id,
            ).order_by(Author.position.asc())
        )).scalars().all())
        author_ids = [a.id for a in authors]

        affiliations = list((await self.session.execute(
            select(Affiliation).where(
                Affiliation.project_id == project_id,
                Affiliation.user_id == user_id,
            ).order_by(Affiliation.position.asc())
        )).scalars().all())

        author_affiliations: list[AuthorAffiliation] = []
        contributions: list[Contribution] = []
        if author_ids:
            author_affiliations = list((await self.session.execute(
                select(AuthorAffiliation).where(
                    AuthorAffiliation.user_id == user_id,
                    AuthorAffiliation.author_id.in_(author_ids),
                ).order_by(AuthorAffiliation.position.asc())
            )).scalars().all())
            contributions = list((await self.session.execute(
                select(Contribution).where(
                    Contribution.user_id == user_id,
                    Contribution.author_id.in_(author_ids),
                ).order_by(Contribution.role.asc())
            )).scalars().all())

        frontmatter = (await self.session.execute(
            select(ProjectFrontmatter).where(
                ProjectFrontmatter.project_id == project_id,
                ProjectFrontmatter.user_id == user_id,
            )
        )).scalar_one_or_none()

        figures = list((await self.session.execute(
            select(Figure).where(
                Figure.project_id == project_id,
                Figure.user_id == user_id,
            ).order_by(Figure.figure_number.asc())
        )).scalars().all())

        abbreviations = list((await self.session.execute(
            select(Abbreviation).where(
                Abbreviation.project_id == project_id,
                Abbreviation.user_id == user_id,
            ).order_by(Abbreviation.short_form.asc())
        )).scalars().all())

        # Reviews + meta + extractions: the snapshot captures the
        # systematic-review-side outputs that journals expect to live or die
        # with a specific manuscript version.
        review = (await self.session.execute(
            select(Review).where(
                Review.project_id == project_id,
                Review.user_id == user_id,
            )
        )).scalar_one_or_none()

        meta_analyses: list[MetaAnalysis] = []
        extraction_records: list[ExtractionRecord] = []
        if review is not None:
            meta_analyses = list((await self.session.execute(
                select(MetaAnalysis).where(
                    MetaAnalysis.review_id == review.id,
                    MetaAnalysis.user_id == user_id,
                ).order_by(MetaAnalysis.created_at.asc())
            )).scalars().all())
            extraction_records = list((await self.session.execute(
                select(ExtractionRecord).where(
                    ExtractionRecord.review_id == review.id,
                    ExtractionRecord.user_id == user_id,
                ).order_by(ExtractionRecord.created_at.asc())
            )).scalars().all())

        return {
            "schema_version": 1,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "manuscript_sections": [_row_to_jsonable(s) for s in sections],
            "authors": [_row_to_jsonable(a) for a in authors],
            "affiliations": [_row_to_jsonable(a) for a in affiliations],
            "author_affiliations": [
                _row_to_jsonable(a) for a in author_affiliations
            ],
            "contributions": [_row_to_jsonable(c) for c in contributions],
            "project_frontmatter": (
                _row_to_jsonable(frontmatter) if frontmatter is not None else None
            ),
            "figures": [_row_to_jsonable(f) for f in figures],
            "abbreviations": [_row_to_jsonable(a) for a in abbreviations],
            "meta_analyses": [_row_to_jsonable(m) for m in meta_analyses],
            "extraction_records": [
                _row_to_jsonable(e) for e in extraction_records
            ],
        }

    async def create_from_current(
        self,
        *,
        project_id: str,
        user_id: str,
        label: str,
        description: str | None,
    ) -> ManuscriptSnapshot:
        blob = await self._assemble_blob(project_id=project_id, user_id=user_id)
        snap = ManuscriptSnapshot(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            label=label,
            description=description,
            full_blob=blob,
        )
        self.session.add(snap)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise SnapshotLabelConflict(
                f"A snapshot named {label!r} already exists for this project"
            ) from exc
        await self.session.refresh(snap)
        return snap

    async def delete(
        self, snapshot_id: str, user_id: str
    ) -> ManuscriptSnapshot | None:
        existing = await self.get(snapshot_id, user_id)
        if existing is None:
            return None
        await self.session.execute(
            sa_delete(ManuscriptSnapshot).where(
                ManuscriptSnapshot.id == snapshot_id,
                ManuscriptSnapshot.user_id == user_id,
            )
        )
        await self.session.commit()
        return existing
