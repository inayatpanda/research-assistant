from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Highlight, new_id
from ..schemas.highlight import (
    HighlightColour,
    HighlightCreate,
    HighlightUpdate,
)


class HighlightRepository(Protocol):
    async def create(
        self, *, article_id: str, data: HighlightCreate, user_id: str
    ) -> Highlight: ...
    async def get(self, highlight_id: str, user_id: str) -> Highlight | None: ...
    async def list_for_article(
        self,
        article_id: str,
        user_id: str,
        *,
        colour: HighlightColour | None = None,
        page: int | None = None,
    ) -> list[Highlight]: ...
    async def update(
        self, highlight_id: str, patch: HighlightUpdate, user_id: str
    ) -> Highlight | None: ...
    async def delete(self, highlight_id: str, user_id: str) -> None: ...


class SqliteHighlightRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, article_id: str, data: HighlightCreate, user_id: str
    ) -> Highlight:
        payload = data.model_dump()
        # BoundingCoords nested model needs explicit dump. ``exclude_none``
        # keeps the legacy {rects:[…]} shape byte-identical to what the
        # M2 mobile reader and the desktop reader emit, instead of
        # back-filling Phase D3's optional ``type``/``page``/``text``
        # discriminator keys with ``None`` (which would surprise the FE
        # zod parser and bloat the JSON column).
        payload["bounding_coords"] = data.bounding_coords.model_dump(
            exclude_none=True
        )
        h = Highlight(id=new_id(), user_id=user_id, article_id=article_id, **payload)
        self.session.add(h)
        await self.session.commit()
        await self.session.refresh(h)
        return h

    async def get(self, highlight_id: str, user_id: str) -> Highlight | None:
        stmt = select(Highlight).where(
            Highlight.id == highlight_id, Highlight.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_article(
        self,
        article_id: str,
        user_id: str,
        *,
        colour: HighlightColour | None = None,
        page: int | None = None,
    ) -> list[Highlight]:
        stmt = (
            select(Highlight)
            .where(Highlight.article_id == article_id, Highlight.user_id == user_id)
            .order_by(
                Highlight.sort_order.asc(),
                Highlight.page_number.asc(),
                Highlight.created_at.asc(),
            )
        )
        if colour is not None:
            stmt = stmt.where(Highlight.colour == colour)
        if page is not None:
            stmt = stmt.where(Highlight.page_number == page)
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(
        self, highlight_id: str, patch: HighlightUpdate, user_id: str
    ) -> Highlight | None:
        existing = await self.get(highlight_id, user_id)
        if existing is None:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, highlight_id: str, user_id: str) -> None:
        stmt = sa_delete(Highlight).where(
            Highlight.id == highlight_id, Highlight.user_id == user_id
        )
        await self.session.execute(stmt)
        await self.session.commit()
