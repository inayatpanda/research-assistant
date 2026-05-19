"""Phase 19 (MP19) repositories for SR depth tables.

- MeshTermsRepository (cache MeSH descriptors per-project)
- SearchStrategyRepository (CRUD on per-review query rows)
- NarrativeSynthesisRepository (CRUD on outcome-narrative rows)
- OutcomeInstrumentsRepository (CRUD on instruments x studies grid)
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    MeshTerm,
    NarrativeSynthesisEntry,
    OutcomeInstrument,
    SearchStrategy,
    new_id,
)


class SqliteMeshTermsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[MeshTerm]:
        stmt = (
            select(MeshTerm)
            .where(
                MeshTerm.project_id == project_id,
                MeshTerm.user_id == user_id,
            )
            .order_by(MeshTerm.descriptor_name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, mesh_id: str, user_id: str) -> MeshTerm | None:
        stmt = select(MeshTerm).where(
            MeshTerm.id == mesh_id, MeshTerm.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_descriptor_ui(
        self, *, project_id: str, descriptor_ui: str, user_id: str
    ) -> MeshTerm | None:
        stmt = select(MeshTerm).where(
            MeshTerm.project_id == project_id,
            MeshTerm.descriptor_ui == descriptor_ui,
            MeshTerm.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert(
        self,
        *,
        project_id: str,
        user_id: str,
        descriptor_ui: str,
        descriptor_name: str,
        scope_note: str | None,
        tree_numbers: list[str],
        entry_terms: list[str],
        source: str = "ncbi_lookup",
    ) -> MeshTerm:
        existing = await self.get_by_descriptor_ui(
            project_id=project_id,
            descriptor_ui=descriptor_ui,
            user_id=user_id,
        )
        if existing is not None:
            existing.descriptor_name = descriptor_name
            existing.scope_note = scope_note
            existing.tree_numbers = list(tree_numbers)
            existing.entry_terms = list(entry_terms)
            existing.source = source
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        row = MeshTerm(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            descriptor_ui=descriptor_ui,
            descriptor_name=descriptor_name,
            scope_note=scope_note,
            tree_numbers=list(tree_numbers),
            entry_terms=list(entry_terms),
            source=source,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, mesh_id: str, user_id: str) -> bool:
        row = await self.get(mesh_id, user_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True


class SqliteSearchStrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_review(
        self, review_id: str, user_id: str
    ) -> list[SearchStrategy]:
        stmt = (
            select(SearchStrategy)
            .where(
                SearchStrategy.review_id == review_id,
                SearchStrategy.user_id == user_id,
            )
            .order_by(SearchStrategy.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, strategy_id: str, user_id: str) -> SearchStrategy | None:
        stmt = select(SearchStrategy).where(
            SearchStrategy.id == strategy_id, SearchStrategy.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        review_id: str,
        user_id: str,
        name: str,
        database: str,
        query_text: str,
        mesh_term_ids: list[str],
        translated_from_id: str | None = None,
        is_locked: bool = False,
        warnings: list[str] | None = None,
    ) -> SearchStrategy:
        row = SearchStrategy(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            review_id=review_id,
            name=name,
            database=database,
            query_text=query_text,
            mesh_term_ids=list(mesh_term_ids or []),
            translated_from_id=translated_from_id,
            is_locked=is_locked,
            warnings=warnings,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self, strategy_id: str, patch: dict[str, Any], user_id: str
    ) -> SearchStrategy | None:
        row = await self.get(strategy_id, user_id)
        if row is None:
            return None
        for k, v in patch.items():
            if v is None:
                continue
            setattr(row, k, v)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, strategy_id: str, user_id: str) -> bool:
        row = await self.get(strategy_id, user_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True


class SqliteNarrativeSynthesisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_review(
        self, review_id: str, user_id: str
    ) -> list[NarrativeSynthesisEntry]:
        stmt = (
            select(NarrativeSynthesisEntry)
            .where(
                NarrativeSynthesisEntry.review_id == review_id,
                NarrativeSynthesisEntry.user_id == user_id,
            )
            .order_by(NarrativeSynthesisEntry.created_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, entry_id: str, user_id: str
    ) -> NarrativeSynthesisEntry | None:
        stmt = select(NarrativeSynthesisEntry).where(
            NarrativeSynthesisEntry.id == entry_id,
            NarrativeSynthesisEntry.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        review_id: str,
        user_id: str,
        outcome_label: str,
        instrument: str,
        range_text: str | None,
        direction: str,
        narrative_html: str,
        study_citations: list[str],
    ) -> NarrativeSynthesisEntry:
        row = NarrativeSynthesisEntry(
            id=new_id(),
            user_id=user_id,
            review_id=review_id,
            outcome_label=outcome_label,
            instrument=instrument,
            range_text=range_text,
            direction=direction,
            narrative_html=narrative_html,
            study_citations=list(study_citations or []),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self, entry_id: str, patch: dict[str, Any], user_id: str
    ) -> NarrativeSynthesisEntry | None:
        row = await self.get(entry_id, user_id)
        if row is None:
            return None
        for k, v in patch.items():
            if v is None:
                continue
            setattr(row, k, v)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, entry_id: str, user_id: str) -> bool:
        row = await self.get(entry_id, user_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True


class SqliteOutcomeInstrumentsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_review(
        self, review_id: str, user_id: str
    ) -> list[OutcomeInstrument]:
        stmt = (
            select(OutcomeInstrument)
            .where(
                OutcomeInstrument.review_id == review_id,
                OutcomeInstrument.user_id == user_id,
            )
            .order_by(OutcomeInstrument.created_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, instrument_id: str, user_id: str
    ) -> OutcomeInstrument | None:
        stmt = select(OutcomeInstrument).where(
            OutcomeInstrument.id == instrument_id,
            OutcomeInstrument.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        review_id: str,
        user_id: str,
        outcome_label: str,
        instrument_name: str,
        score_range_low: float | None,
        score_range_high: float | None,
        mid: float | None,
        study_values: list[dict],
    ) -> OutcomeInstrument:
        row = OutcomeInstrument(
            id=new_id(),
            user_id=user_id,
            review_id=review_id,
            outcome_label=outcome_label,
            instrument_name=instrument_name,
            score_range_low=score_range_low,
            score_range_high=score_range_high,
            mid=mid,
            study_values=list(study_values or []),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self, instrument_id: str, patch: dict[str, Any], user_id: str
    ) -> OutcomeInstrument | None:
        row = await self.get(instrument_id, user_id)
        if row is None:
            return None
        for k, v in patch.items():
            if v is None:
                continue
            setattr(row, k, v)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, instrument_id: str, user_id: str) -> bool:
        row = await self.get(instrument_id, user_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True
