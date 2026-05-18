from __future__ import annotations

from typing import Iterable, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Dataset, DatasetVariable, new_id
from ..services.stats.ingest import InferredColumn


class DatasetRepository(Protocol):
    async def create(
        self,
        *,
        project_id: str,
        filename: str,
        file_ref: dict,
        file_type: str,
        n_rows: int,
        n_columns: int,
        variables: Iterable[InferredColumn],
        user_id: str,
    ) -> Dataset: ...
    async def get(self, dataset_id: str, user_id: str) -> Dataset | None: ...
    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[Dataset]: ...
    async def list_variables(
        self, dataset_id: str, user_id: str
    ) -> list[DatasetVariable]: ...
    async def update_variable_type(
        self, *, variable_id: str, user_type: str | None, user_id: str
    ) -> DatasetVariable | None: ...
    async def delete(self, dataset_id: str, user_id: str) -> None: ...


class SqliteDatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        project_id: str,
        filename: str,
        file_ref: dict,
        file_type: str,
        n_rows: int,
        n_columns: int,
        variables: Iterable[InferredColumn],
        user_id: str,
    ) -> Dataset:
        ds = Dataset(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            filename=filename,
            file_ref=file_ref,
            file_type=file_type,
            n_rows=n_rows,
            n_columns=n_columns,
        )
        self.session.add(ds)
        await self.session.flush()

        for col in variables:
            row = DatasetVariable(
                id=new_id(),
                user_id=user_id,
                dataset_id=ds.id,
                name=col.name,
                position=col.position,
                inferred_type=col.inferred_type,
                user_type=None,
                n_missing=col.n_missing,
                sample_values=list(col.sample_values),
            )
            self.session.add(row)

        await self.session.commit()
        await self.session.refresh(ds)
        return ds

    async def get(self, dataset_id: str, user_id: str) -> Dataset | None:
        stmt = select(Dataset).where(
            Dataset.id == dataset_id, Dataset.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[Dataset]:
        stmt = (
            select(Dataset)
            .where(Dataset.project_id == project_id, Dataset.user_id == user_id)
            .order_by(Dataset.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_variables(
        self, dataset_id: str, user_id: str
    ) -> list[DatasetVariable]:
        stmt = (
            select(DatasetVariable)
            .where(
                DatasetVariable.dataset_id == dataset_id,
                DatasetVariable.user_id == user_id,
            )
            .order_by(DatasetVariable.position.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def update_variable_type(
        self, *, variable_id: str, user_type: str | None, user_id: str
    ) -> DatasetVariable | None:
        stmt = select(DatasetVariable).where(
            DatasetVariable.id == variable_id,
            DatasetVariable.user_id == user_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            return None
        existing.user_type = user_type
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def create_derived(
        self,
        *,
        project_id: str,
        filename: str,
        file_ref: dict,
        file_type: str,
        n_rows: int,
        n_columns: int,
        variables: Iterable[InferredColumn],
        user_id: str,
        derived_from_dataset_id: str,
        dataset_metadata: dict | None,
    ) -> Dataset:
        """Phase 13 — Create a dataset that points to a source via the
        derived_from_dataset_id FK and carries PSM balance JSON.
        """
        ds = Dataset(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            filename=filename,
            file_ref=file_ref,
            file_type=file_type,
            n_rows=n_rows,
            n_columns=n_columns,
            derived_from_dataset_id=derived_from_dataset_id,
            dataset_metadata=dataset_metadata,
        )
        self.session.add(ds)
        await self.session.flush()
        for col in variables:
            row = DatasetVariable(
                id=new_id(),
                user_id=user_id,
                dataset_id=ds.id,
                name=col.name,
                position=col.position,
                inferred_type=col.inferred_type,
                user_type=None,
                n_missing=col.n_missing,
                sample_values=list(col.sample_values),
            )
            self.session.add(row)
        await self.session.commit()
        await self.session.refresh(ds)
        return ds

    async def delete(self, dataset_id: str, user_id: str) -> None:
        # Manually cascade since SQLite FK PRAGMA isn't always on in tests.
        ds = await self.get(dataset_id, user_id)
        if ds is None:
            return
        await self.session.execute(
            sa_delete(DatasetVariable).where(
                DatasetVariable.dataset_id == dataset_id,
                DatasetVariable.user_id == user_id,
            )
        )
        await self.session.execute(
            sa_delete(Dataset).where(
                Dataset.id == dataset_id, Dataset.user_id == user_id
            )
        )
        await self.session.commit()
