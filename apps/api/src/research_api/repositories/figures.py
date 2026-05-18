"""Phase 8.7 — SqliteFigureRepository: list/get/create/update/reorder/delete.

Reorder + delete recompact `figure_number` to stay contiguous (1..N). Because
the table has UNIQUE(project_id, user_id, figure_number), naive in-place
updates can transiently violate the constraint mid-statement; we work around
that with a two-step UPDATE that first offsets every row by +1000 and then
writes the final numbers in a second pass — both in one transaction.
"""
from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete as sa_delete, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Figure, new_id


class FigureRepository(Protocol):
    async def list(self, *, project_id: str, user_id: str) -> list[Figure]: ...
    async def get(self, figure_id: str, user_id: str) -> Figure | None: ...
    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        file_ref: dict,
        file_type: str,
        width_px: int | None,
        height_px: int | None,
        byte_size: int,
        caption: str = "",
        alt_text: str = "",
    ) -> Figure: ...
    async def update(
        self,
        figure_id: str,
        user_id: str,
        *,
        caption: str | None = None,
        alt_text: str | None = None,
    ) -> Figure | None: ...
    async def reorder(
        self, *, project_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[Figure]: ...
    async def delete(self, figure_id: str, user_id: str) -> Figure | None: ...


class SqliteFigureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, *, project_id: str, user_id: str) -> list[Figure]:
        stmt = (
            select(Figure)
            .where(Figure.project_id == project_id, Figure.user_id == user_id)
            .order_by(Figure.figure_number.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, figure_id: str, user_id: str) -> Figure | None:
        stmt = select(Figure).where(
            Figure.id == figure_id, Figure.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _next_number(self, *, project_id: str, user_id: str) -> int:
        stmt = (
            select(Figure.figure_number)
            .where(Figure.project_id == project_id, Figure.user_id == user_id)
            .order_by(Figure.figure_number.desc())
            .limit(1)
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        return (existing or 0) + 1

    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        file_ref: dict,
        file_type: str,
        width_px: int | None,
        height_px: int | None,
        byte_size: int,
        caption: str = "",
        alt_text: str = "",
    ) -> Figure:
        n = await self._next_number(project_id=project_id, user_id=user_id)
        fig = Figure(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            file_ref=file_ref,
            file_type=file_type,
            figure_number=n,
            caption=caption,
            alt_text=alt_text,
            width_px=width_px,
            height_px=height_px,
            byte_size=byte_size,
        )
        self.session.add(fig)
        await self.session.commit()
        await self.session.refresh(fig)
        return fig

    async def update(
        self,
        figure_id: str,
        user_id: str,
        *,
        caption: str | None = None,
        alt_text: str | None = None,
    ) -> Figure | None:
        existing = await self.get(figure_id, user_id)
        if existing is None:
            return None
        if caption is not None:
            existing.caption = caption
        if alt_text is not None:
            existing.alt_text = alt_text
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def reorder(
        self, *, project_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[Figure]:
        current = await self.list(project_id=project_id, user_id=user_id)
        if {f.id for f in current} != set(ordered_ids) or len(current) != len(ordered_ids):
            raise ValueError("ordered_figure_ids does not match the project's figure set")

        # Step 1: offset every row by +1000 so the UNIQUE constraint can't trip mid-pass.
        await self.session.execute(
            sa_update(Figure)
            .where(Figure.project_id == project_id, Figure.user_id == user_id)
            .values(figure_number=Figure.figure_number + 1000)
        )
        # Step 2: assign final numbers in the requested order.
        for idx, fid in enumerate(ordered_ids, start=1):
            await self.session.execute(
                sa_update(Figure)
                .where(Figure.id == fid, Figure.user_id == user_id)
                .values(figure_number=idx)
            )
        await self.session.commit()
        return await self.list(project_id=project_id, user_id=user_id)

    async def delete(self, figure_id: str, user_id: str) -> Figure | None:
        existing = await self.get(figure_id, user_id)
        if existing is None:
            return None
        # Snapshot before deletion — the caller uses .file_ref to evict the file.
        project_id = existing.project_id
        snapshot_ref = dict(existing.file_ref)
        snapshot_filetype = existing.file_type
        snapshot_number = existing.figure_number
        snapshot_id = existing.id
        snapshot_caption = existing.caption
        snapshot_alt = existing.alt_text
        snapshot_size = existing.byte_size

        await self.session.execute(
            sa_delete(Figure).where(Figure.id == figure_id, Figure.user_id == user_id)
        )
        # Recompact remaining: offset + reassign.
        remaining_stmt = (
            select(Figure)
            .where(Figure.project_id == project_id, Figure.user_id == user_id)
            .order_by(Figure.figure_number.asc())
        )
        remaining = list((await self.session.execute(remaining_stmt)).scalars().all())
        await self.session.execute(
            sa_update(Figure)
            .where(Figure.project_id == project_id, Figure.user_id == user_id)
            .values(figure_number=Figure.figure_number + 1000)
        )
        for idx, fig in enumerate(remaining, start=1):
            await self.session.execute(
                sa_update(Figure)
                .where(Figure.id == fig.id, Figure.user_id == user_id)
                .values(figure_number=idx)
            )
        await self.session.commit()

        # Re-hydrate a detached snapshot so the caller can clean up storage.
        snap = Figure(
            id=snapshot_id,
            user_id=user_id,
            project_id=project_id,
            file_ref=snapshot_ref,
            file_type=snapshot_filetype,
            figure_number=snapshot_number,
            caption=snapshot_caption,
            alt_text=snapshot_alt,
            byte_size=snapshot_size,
        )
        return snap
