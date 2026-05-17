from __future__ import annotations

from typing import Iterable, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Abbreviation, new_id


class AbbreviationRepository(Protocol):
    async def list_for_project(self, project_id: str, user_id: str) -> list[Abbreviation]: ...
    async def replace_all(
        self,
        *,
        project_id: str,
        user_id: str,
        items: Iterable[tuple[str, str]],  # (short_form, long_form)
    ) -> list[Abbreviation]: ...
    async def delete(self, abbreviation_id: str, user_id: str) -> None: ...


class SqliteAbbreviationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(self, project_id: str, user_id: str) -> list[Abbreviation]:
        stmt = (
            select(Abbreviation)
            .where(Abbreviation.project_id == project_id, Abbreviation.user_id == user_id)
            .order_by(Abbreviation.short_form.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def replace_all(
        self,
        *,
        project_id: str,
        user_id: str,
        items: Iterable[tuple[str, str]],
    ) -> list[Abbreviation]:
        # Delete current rows for (project, user), then insert fresh. Single transaction.
        await self.session.execute(
            sa_delete(Abbreviation).where(
                Abbreviation.project_id == project_id,
                Abbreviation.user_id == user_id,
            )
        )
        rows: list[Abbreviation] = []
        seen: set[str] = set()
        for short, long_ in items:
            if short in seen:
                continue  # dedupe within request
            seen.add(short)
            row = Abbreviation(
                id=new_id(),
                user_id=user_id,
                project_id=project_id,
                short_form=short,
                long_form=long_,
            )
            self.session.add(row)
            rows.append(row)
        await self.session.commit()
        for r in rows:
            await self.session.refresh(r)
        return rows

    async def delete(self, abbreviation_id: str, user_id: str) -> None:
        stmt = sa_delete(Abbreviation).where(
            Abbreviation.id == abbreviation_id, Abbreviation.user_id == user_id
        )
        await self.session.execute(stmt)
        await self.session.commit()
