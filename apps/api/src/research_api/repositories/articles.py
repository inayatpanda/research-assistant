from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete as sa_delete, select
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
