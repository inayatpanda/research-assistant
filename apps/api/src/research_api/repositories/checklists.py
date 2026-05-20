"""Phase 20 (MP20) — Repository for ``checklist_runs``."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ChecklistRun, new_id
from ..services.checklists.auto_check import compute_compliance_pct


class ChecklistRepository(Protocol):
    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[ChecklistRun]: ...
    async def get(self, run_id: str, user_id: str) -> ChecklistRun | None: ...
    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        checklist_key: str,
        title: str,
        items: list[dict[str, Any]],
    ) -> ChecklistRun | None: ...
    async def replace_items(
        self,
        *,
        run_id: str,
        user_id: str,
        items: list[dict[str, Any]],
    ) -> ChecklistRun | None: ...
    async def patch_item(
        self,
        *,
        run_id: str,
        user_id: str,
        item_id: str,
        patch: dict[str, Any],
    ) -> ChecklistRun | None: ...
    async def delete(self, run_id: str, user_id: str) -> bool: ...


class SqliteChecklistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[ChecklistRun]:
        stmt = (
            select(ChecklistRun)
            .where(
                ChecklistRun.project_id == project_id,
                ChecklistRun.user_id == user_id,
            )
            .order_by(ChecklistRun.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, run_id: str, user_id: str) -> ChecklistRun | None:
        stmt = select(ChecklistRun).where(
            ChecklistRun.id == run_id,
            ChecklistRun.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        checklist_key: str,
        title: str,
        items: list[dict[str, Any]],
    ) -> ChecklistRun | None:
        row = ChecklistRun(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            checklist_key=checklist_key,
            title=title,
            items=items,
            overall_compliance_pct=compute_compliance_pct(items),
        )
        self.session.add(row)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return None
        await self.session.refresh(row)
        return row

    async def replace_items(
        self,
        *,
        run_id: str,
        user_id: str,
        items: list[dict[str, Any]],
    ) -> ChecklistRun | None:
        row = await self.get(run_id, user_id)
        if row is None:
            return None
        row.items = items
        row.overall_compliance_pct = compute_compliance_pct(items)
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def patch_item(
        self,
        *,
        run_id: str,
        user_id: str,
        item_id: str,
        patch: dict[str, Any],
    ) -> ChecklistRun | None:
        row = await self.get(run_id, user_id)
        if row is None:
            return None
        new_items: list[dict[str, Any]] = []
        found = False
        for raw in (row.items or []):
            entry = dict(raw or {})
            if str(entry.get("item_id")) == str(item_id):
                found = True
                for key, val in patch.items():
                    if val is not None:
                        entry[key] = val
            new_items.append(entry)
        if not found:
            return None
        row.items = new_items
        row.overall_compliance_pct = compute_compliance_pct(new_items)
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, run_id: str, user_id: str) -> bool:
        row = await self.get(run_id, user_id)
        if row is None:
            return False
        await self.session.execute(
            sa_delete(ChecklistRun).where(
                ChecklistRun.id == run_id,
                ChecklistRun.user_id == user_id,
            )
        )
        await self.session.commit()
        return True
