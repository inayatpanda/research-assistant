"""Seed fixture for meta-analysis tests: project + review + 4 included articles."""
from __future__ import annotations

from research_api.db.models import (
    Article,
    ExtractionRecord,
    Project,
    Review,
    ScreeningRecord,
)


async def seed_review_with_articles(
    session,
    *,
    user_id: str = "user-a",
    n_articles: int = 4,
    title_prefix: str = "Study",
    with_extractions: bool = False,
):
    """Returns (project, review, list[articles])."""
    p = Project(user_id=user_id, title="P", study_type="Systematic Review")
    session.add(p)
    await session.flush()

    r = Review(user_id=user_id, project_id=p.id)
    session.add(r)
    await session.flush()

    arts: list[Article] = []
    for i in range(n_articles):
        a = Article(
            user_id=user_id,
            project_id=p.id,
            title=f"{title_prefix} {i+1}",
            authors=[f"Author {i+1}"],
            year=2020 + i,
        )
        session.add(a)
        await session.flush()
        arts.append(a)
        # Mark each as fully included
        session.add(ScreeningRecord(
            user_id=user_id, review_id=r.id, article_id=a.id,
            stage="full_text", decision="include",
        ))
        if with_extractions:
            session.add(ExtractionRecord(
                user_id=user_id, review_id=r.id, article_id=a.id,
                fields={
                    "basic": {"design": "RCT" if i % 2 == 0 else "Cohort"},
                    "intervention": {"name": "Intervention A"},
                    "population": {"n_total": 100 + i * 10},
                },
            ))
    await session.flush()
    return p, r, arts
