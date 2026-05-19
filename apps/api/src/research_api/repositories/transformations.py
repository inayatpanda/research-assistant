"""Phase 13 (MP13) — DatasetTransformation repository.

Owns the CRUD on the ordered transformation stack for a dataset. Reorder is
implemented as a transactional "replace_all" so positions remain dense and
collision-free.
"""
from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DatasetTransformation, new_id


class TransformationRepository(Protocol):
    async def list_for_dataset(
        self, dataset_id: str, user_id: str
    ) -> list[DatasetTransformation]: ...
    async def create(
        self,
        *,
        dataset_id: str,
        user_id: str,
        op_type: str,
        op_args: dict[str, Any],
        label: str,
        position: int | None,
    ) -> DatasetTransformation: ...
    async def get(
        self, transformation_id: str, user_id: str
    ) -> DatasetTransformation | None: ...
    async def update(
        self,
        *,
        transformation_id: str,
        user_id: str,
        op_args: dict[str, Any] | None,
        label: str | None,
        position: int | None,
    ) -> DatasetTransformation | None: ...
    async def delete(self, transformation_id: str, user_id: str) -> bool: ...
    async def replace_all(
        self, *, dataset_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[DatasetTransformation]: ...


class SqliteTransformationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_dataset(
        self, dataset_id: str, user_id: str
    ) -> list[DatasetTransformation]:
        stmt = (
            select(DatasetTransformation)
            .where(
                DatasetTransformation.dataset_id == dataset_id,
                DatasetTransformation.user_id == user_id,
            )
            .order_by(DatasetTransformation.position.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _next_position(self, dataset_id: str, user_id: str) -> int:
        rows = await self.list_for_dataset(dataset_id, user_id)
        return (max((r.position for r in rows), default=-1)) + 1

    async def create(
        self,
        *,
        dataset_id: str,
        user_id: str,
        op_type: str,
        op_args: dict[str, Any],
        label: str,
        position: int | None,
    ) -> DatasetTransformation:
        if position is None:
            position = await self._next_position(dataset_id, user_id)
        else:
            # Shift any row at >= requested position by +1 to make room.
            current = await self.list_for_dataset(dataset_id, user_id)
            for r in current:
                if r.position >= position:
                    r.position = r.position + 1
        row = DatasetTransformation(
            id=new_id(),
            user_id=user_id,
            dataset_id=dataset_id,
            position=position,
            op_type=op_type,
            op_args=op_args,
            label=label,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get(
        self, transformation_id: str, user_id: str
    ) -> DatasetTransformation | None:
        stmt = select(DatasetTransformation).where(
            DatasetTransformation.id == transformation_id,
            DatasetTransformation.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update(
        self,
        *,
        transformation_id: str,
        user_id: str,
        op_args: dict[str, Any] | None,
        label: str | None,
        position: int | None,
    ) -> DatasetTransformation | None:
        row = await self.get(transformation_id, user_id)
        if row is None:
            return None
        if op_args is not None:
            row.op_args = op_args
        if label is not None:
            row.label = label
        if position is not None and position != row.position:
            # Swap-pack: remove this row's position, then re-insert at new
            # slot while shifting siblings to preserve density.
            current = await self.list_for_dataset(row.dataset_id, user_id)
            without_self = [r for r in current if r.id != row.id]
            new_order: list[DatasetTransformation] = []
            for i, r in enumerate(without_self):
                if i == position:
                    new_order.append(row)
                new_order.append(r)
            if len(new_order) < len(without_self) + 1:
                new_order.append(row)
            for i, r in enumerate(new_order):
                r.position = i
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, transformation_id: str, user_id: str) -> bool:
        row = await self.get(transformation_id, user_id)
        if row is None:
            return False
        ds_id = row.dataset_id
        await self.session.execute(
            sa_delete(DatasetTransformation).where(
                DatasetTransformation.id == transformation_id,
                DatasetTransformation.user_id == user_id,
            )
        )
        # Densify remaining positions.
        remaining = await self.list_for_dataset(ds_id, user_id)
        for i, r in enumerate(remaining):
            r.position = i
        await self.session.commit()
        return True

    async def replace_all(
        self, *, dataset_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[DatasetTransformation]:
        """Reorder the entire stack to exactly the given id sequence.

        Raises ValueError if the id set doesn't match the dataset's current
        set of transformations.
        """
        current = await self.list_for_dataset(dataset_id, user_id)
        current_ids = {r.id for r in current}
        if set(ordered_ids) != current_ids:
            raise ValueError(
                "replace_all: ordered_ids must match current transformation ids exactly"
            )
        by_id = {r.id: r for r in current}
        for i, oid in enumerate(ordered_ids):
            by_id[oid].position = i
        await self.session.commit()
        return await self.list_for_dataset(dataset_id, user_id)
