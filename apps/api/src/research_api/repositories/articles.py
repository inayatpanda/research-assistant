from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete as sa_delete, select, text, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Article, new_id
from ..schemas.article import ArticleCreate, ArticleFilters, ArticleUpdate
from ..services.dedupe import is_duplicate


class ArticleRepository(Protocol):
    async def create(
        self, *, project_id: str, data: ArticleCreate, user_id: str
    ) -> Article: ...
    async def get(self, article_id: str, user_id: str) -> Article | None: ...
    async def list_for_project(
        self, project_id: str, user_id: str, filters: ArticleFilters
    ) -> list[Article]: ...
    async def update(
        self, article_id: str, patch: ArticleUpdate, user_id: str
    ) -> Article | None: ...
    async def delete(self, article_id: str, user_id: str) -> None: ...
    async def find_duplicate(
        self, *, project_id: str, doi: str | None, title: str, user_id: str
    ) -> Article | None: ...


class SqliteArticleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, project_id: str, data: ArticleCreate, user_id: str
    ) -> Article:
        payload = data.model_dump()
        # StorageRefSchema -> dict (already model_dumped if nested model)
        if isinstance(payload.get("file_ref"), dict) is False and payload.get("file_ref") is not None:
            payload["file_ref"] = data.file_ref.model_dump() if data.file_ref else None
        article = Article(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            **payload,
        )
        self.session.add(article)
        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def get(self, article_id: str, user_id: str) -> Article | None:
        stmt = select(Article).where(
            Article.id == article_id, Article.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_project(
        self, project_id: str, user_id: str, filters: ArticleFilters
    ) -> list[Article]:
        stmt = select(Article).where(
            Article.project_id == project_id, Article.user_id == user_id
        )
        if filters.q:
            like = f"%{filters.q.lower()}%"
            stmt = stmt.where(Article.title.ilike(like))
        if filters.review_status:
            stmt = stmt.where(Article.review_status == filters.review_status)
        if filters.study_design:
            stmt = stmt.where(Article.study_design == filters.study_design)

        match filters.sort:
            case "year_desc":
                stmt = stmt.order_by(Article.year.desc().nulls_last(), Article.created_at.desc())
            case "year_asc":
                stmt = stmt.order_by(Article.year.asc().nulls_last(), Article.created_at.asc())
            case "title":
                stmt = stmt.order_by(Article.title.asc())
            case "created_desc":
                stmt = stmt.order_by(Article.created_at.desc())

        return list((await self.session.execute(stmt)).scalars().all())

    async def update(
        self, article_id: str, patch: ArticleUpdate, user_id: str
    ) -> Article | None:
        existing = await self.get(article_id, user_id)
        if existing is None:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, article_id: str, user_id: str) -> None:
        stmt = sa_delete(Article).where(
            Article.id == article_id, Article.user_id == user_id
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def merge(
        self, *, keep_id: str, drop_ids: list[str], user_id: str
    ) -> Article:
        """Merge ``drop_ids`` into ``keep_id``.

        All foreign keys that currently point at any drop article are
        rewritten to ``keep_id``; the drop rows are then deleted. Single
        transaction (the request-scoped session is committed at the end).

        Composite-UNIQUE-bearing tables (article_notes UQ(user, article);
        screening_records UQ(review, article, stage); rob_assessments
        UQ(review, article, tool); extraction_records UQ(review, article);
        meta_inputs UQ(meta, article)) require a per-row collision check
        — when keep already has a sibling row in the same UQ-tuple as a
        drop row, the drop row is deleted rather than rewritten.

        Raises ``ValueError`` (caught by the route → 422) for the four
        refusal conditions: same id, missing keep / missing drop, and
        cross-project merge.
        """
        if keep_id in drop_ids:
            raise ValueError("cannot merge an article into itself")

        keep = await self.get(keep_id, user_id)
        if keep is None:
            raise ValueError("keep article not found")

        drops: list[Article] = []
        for did in drop_ids:
            d = await self.get(did, user_id)
            if d is None:
                raise ValueError("drop article not found")
            drops.append(d)

        for d in drops:
            if d.project_id != keep.project_id:
                raise ValueError("cross-project merge refused")

        async def _rewire_simple(table: str, fk_col: str) -> None:
            for d in drops:
                await self.session.execute(
                    text(
                        f"UPDATE {table} SET {fk_col} = :keep "
                        f"WHERE {fk_col} = :drop AND user_id = :u"
                    ),
                    {"keep": keep_id, "drop": d.id, "u": user_id},
                )

        async def _rewire_with_unique(
            table: str,
            fk_col: str,
            other_cols: tuple[str, ...],
        ) -> None:
            for d in drops:
                select_cols = ", ".join(("id",) + other_cols)
                drop_rows = (
                    await self.session.execute(
                        text(
                            f"SELECT {select_cols} FROM {table} "
                            f"WHERE {fk_col} = :drop AND user_id = :u"
                        ),
                        {"drop": d.id, "u": user_id},
                    )
                ).all()
                for row in drop_rows:
                    drop_row_id = row[0]
                    other_vals = dict(zip(other_cols, row[1:]))
                    where = " AND ".join(
                        [f"{col} = :{col}" for col in other_cols]
                    )
                    params: dict[str, object] = {
                        "keep": keep_id,
                        "u": user_id,
                        **other_vals,
                    }
                    sibling = (
                        await self.session.execute(
                            text(
                                f"SELECT id FROM {table} "
                                f"WHERE {fk_col} = :keep AND user_id = :u "
                                + (f"AND {where}" if other_cols else "")
                            ),
                            params,
                        )
                    ).first()
                    if sibling is not None:
                        await self.session.execute(
                            text(f"DELETE FROM {table} WHERE id = :id"),
                            {"id": drop_row_id},
                        )
                    else:
                        await self.session.execute(
                            text(
                                f"UPDATE {table} SET {fk_col} = :keep "
                                f"WHERE id = :id"
                            ),
                            {"keep": keep_id, "id": drop_row_id},
                        )

        # Highlights — no UNIQUE on article_id, plain rewire.
        await _rewire_simple("highlights", "article_id")
        # article_notes — UQ(article_id, user_id).
        await _rewire_with_unique(
            "article_notes", "article_id", ("user_id",)
        )
        # screening_records — UQ(review_id, article_id, stage).
        await _rewire_with_unique(
            "screening_records", "article_id", ("review_id", "stage")
        )
        # rob_assessments — UQ(review_id, article_id, tool).
        await _rewire_with_unique(
            "rob_assessments", "article_id", ("review_id", "tool")
        )
        # extraction_records — UQ(review_id, article_id).
        await _rewire_with_unique(
            "extraction_records", "article_id", ("review_id",)
        )
        # meta_inputs — UQ(meta_id, article_id) — Phase 7.5 cross-link.
        await _rewire_with_unique(
            "meta_inputs", "article_id", ("meta_id",)
        )

        for d in drops:
            await self.session.execute(
                sa_delete(Article).where(
                    Article.id == d.id, Article.user_id == user_id
                )
            )

        await self.session.commit()
        await self.session.refresh(keep)
        return keep

    async def find_duplicate(
        self, *, project_id: str, doi: str | None, title: str, user_id: str
    ) -> Article | None:
        # Fast path: DOI exact match scoped to this user. Use .first() because the
        # DB may already contain multiple rows for the same DOI — we just need ONE
        # to report a duplicate.
        if doi:
            stmt = (
                select(Article)
                .where(Article.user_id == user_id, Article.doi == doi)
                .limit(1)
            )
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                return existing
        # Fallback: fuzzy title match against this user's articles in the same project
        stmt = select(Article).where(
            Article.user_id == user_id, Article.project_id == project_id
        )
        candidates = list((await self.session.execute(stmt)).scalars().all())

        class _Probe:
            def __init__(self, t: str, d: str | None) -> None:
                self.title = t
                self.doi = d

        probe = _Probe(title, doi)
        for c in candidates:
            if is_duplicate(probe, c):
                return c
        return None
