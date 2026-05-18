import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from research_api.db.models import (
    Analysis,
    AnalysisResult,
    Dataset,
    DatasetVariable,
    Project,
)


async def _make_project(session, user_id: str = "user-a") -> Project:
    p = Project(
        user_id=user_id,
        title="P",
        study_type="Outcome Study",
    )
    session.add(p)
    await session.flush()
    return p


@pytest.mark.asyncio
async def test_dataset_round_trip(session):
    p = await _make_project(session)
    ds = Dataset(
        user_id="user-a",
        project_id=p.id,
        filename="data.csv",
        file_ref={"backend": "local", "key": "datasets/abc"},
        file_type="text/csv",
        n_rows=10,
        n_columns=3,
    )
    session.add(ds)
    await session.flush()

    row = (await session.execute(select(Dataset).where(Dataset.id == ds.id))).scalar_one()
    assert row.filename == "data.csv"
    assert row.file_ref == {"backend": "local", "key": "datasets/abc"}
    assert row.n_rows == 10
    assert row.n_columns == 3
    assert row.user_id == "user-a"
    assert row.created_at is not None


@pytest.mark.asyncio
async def test_dataset_variable_unique_constraint(session):
    p = await _make_project(session)
    ds = Dataset(
        user_id="user-a", project_id=p.id, filename="d.csv",
        file_ref={"backend": "local", "key": "k"}, file_type="text/csv",
        n_rows=1, n_columns=1,
    )
    session.add(ds)
    await session.flush()

    session.add(DatasetVariable(
        user_id="user-a", dataset_id=ds.id, name="age",
        position=0, inferred_type="numeric", n_missing=0, sample_values=["1", "2"],
    ))
    await session.flush()

    session.add(DatasetVariable(
        user_id="user-a", dataset_id=ds.id, name="age",
        position=1, inferred_type="numeric", n_missing=0, sample_values=["3"],
    ))
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


@pytest.mark.asyncio
async def test_dataset_variables_cascade_on_dataset_delete(session):
    p = await _make_project(session)
    ds = Dataset(
        user_id="user-a", project_id=p.id, filename="d.csv",
        file_ref={"backend": "local", "key": "k"}, file_type="text/csv",
        n_rows=1, n_columns=2,
    )
    session.add(ds)
    await session.flush()
    session.add(DatasetVariable(
        user_id="user-a", dataset_id=ds.id, name="age",
        position=0, inferred_type="numeric", n_missing=0, sample_values=[],
    ))
    session.add(DatasetVariable(
        user_id="user-a", dataset_id=ds.id, name="sex",
        position=1, inferred_type="nominal", n_missing=0, sample_values=["M", "F"],
    ))
    await session.flush()

    await session.commit()
    await session.execute(text("DELETE FROM datasets WHERE id = :id"), {"id": ds.id})
    await session.commit()

    remaining = (await session.execute(select(DatasetVariable))).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_analysis_and_result_round_trip(session):
    p = await _make_project(session)
    ds = Dataset(
        user_id="user-a", project_id=p.id, filename="d.csv",
        file_ref={"backend": "local", "key": "k"}, file_type="text/csv",
        n_rows=12, n_columns=2,
    )
    session.add(ds)
    await session.flush()

    a = Analysis(
        user_id="user-a",
        project_id=p.id,
        dataset_id=ds.id,
        question_type="group_comparison",
        chosen_test="independent_t",
        recommendation_rationale="numeric outcome vs nominal grouping with normal data",
        variables={"outcome": "score", "groups": "group"},
        status="ready",
    )
    session.add(a)
    await session.flush()

    r = AnalysisResult(
        user_id="user-a",
        analysis_id=a.id,
        summary={"statistic": 4.0, "p_value": 0.001, "n": 12},
        assumptions={"shapiro": {"p": 0.5, "ok": True}},
        chart=None,
        ai_interpretation=None,
    )
    session.add(r)
    await session.flush()

    fetched = (await session.execute(
        select(AnalysisResult).where(AnalysisResult.analysis_id == a.id)
    )).scalar_one()
    assert fetched.summary["p_value"] == 0.001
    assert fetched.assumptions["shapiro"]["ok"] is True


@pytest.mark.asyncio
async def test_analysis_result_unique_per_analysis(session):
    p = await _make_project(session)
    ds = Dataset(
        user_id="user-a", project_id=p.id, filename="d.csv",
        file_ref={"backend": "local", "key": "k"}, file_type="text/csv",
        n_rows=1, n_columns=1,
    )
    session.add(ds)
    await session.flush()
    a = Analysis(
        user_id="user-a", project_id=p.id, dataset_id=ds.id,
        question_type="group_comparison", chosen_test="independent_t",
        recommendation_rationale="r", variables={}, status="ready",
    )
    session.add(a)
    await session.flush()
    session.add(AnalysisResult(
        user_id="user-a", analysis_id=a.id,
        summary={}, assumptions={}, chart=None, ai_interpretation=None,
    ))
    await session.flush()
    session.add(AnalysisResult(
        user_id="user-a", analysis_id=a.id,
        summary={}, assumptions={}, chart=None, ai_interpretation=None,
    ))
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


@pytest.mark.asyncio
async def test_analysis_cascades_to_result_on_delete(session):
    p = await _make_project(session)
    ds = Dataset(
        user_id="user-a", project_id=p.id, filename="d.csv",
        file_ref={"backend": "local", "key": "k"}, file_type="text/csv",
        n_rows=1, n_columns=1,
    )
    session.add(ds)
    await session.flush()
    a = Analysis(
        user_id="user-a", project_id=p.id, dataset_id=ds.id,
        question_type="group_comparison", chosen_test="independent_t",
        recommendation_rationale="r", variables={}, status="ready",
    )
    session.add(a)
    await session.flush()
    session.add(AnalysisResult(
        user_id="user-a", analysis_id=a.id,
        summary={"p_value": 0.01}, assumptions={}, chart=None, ai_interpretation=None,
    ))
    await session.flush()

    await session.commit()
    await session.execute(text("DELETE FROM analyses WHERE id = :id"), {"id": a.id})
    await session.commit()

    remaining = (await session.execute(select(AnalysisResult))).scalars().all()
    assert remaining == []
