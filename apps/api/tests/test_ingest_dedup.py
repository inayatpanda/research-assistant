"""Phase 8.6 — services/ingest/dedup.py: group finder over articles."""
from __future__ import annotations

from research_api.services.ingest.dedup import (
    DuplicateCandidate,
    find_duplicates,
)


def _cand(
    *,
    id: str,
    title: str = "",
    year: int | None = None,
    doi: str | None = None,
    pmid: str | None = None,
) -> DuplicateCandidate:
    return DuplicateCandidate(
        article_id=id, title=title, year=year, doi=doi, pmid=pmid
    )


def test_find_duplicates_doi_exact():
    a = _cand(id="a", title="One", doi="10.1/x")
    b = _cand(id="b", title="Other", doi="10.1/x")
    [grp] = find_duplicates([a, b])
    assert grp.reason == "doi_exact"
    assert grp.score == 1.0
    assert set(grp.candidate_ids) == {"a", "b"}
    assert grp.keep_candidate_id == "a"  # oldest in the input order


def test_find_duplicates_doi_exact_case_insensitive():
    a = _cand(id="a", title="x", doi="10.1/X")
    b = _cand(id="b", title="y", doi="10.1/x")
    [grp] = find_duplicates([a, b])
    assert grp.reason == "doi_exact"


def test_find_duplicates_pmid_exact_when_no_doi():
    a = _cand(id="a", title="x", pmid="111")
    b = _cand(id="b", title="y", pmid="111")
    [grp] = find_duplicates([a, b])
    assert grp.reason == "pmid_exact"
    assert grp.score == 1.0


def test_find_duplicates_title_fuzzy_above_threshold():
    a = _cand(
        id="a",
        title="Anterior vs Posterior Approach in THA",
        year=2023,
    )
    b = _cand(
        id="b",
        title="Anterior vs. posterior approach in total hip arthroplasty",
        year=2023,
    )
    [grp] = find_duplicates([a, b])
    assert grp.reason == "title_fuzzy"
    assert grp.score >= 0.92


def test_find_duplicates_year_outside_tolerance_does_not_match():
    a = _cand(id="a", title="Anterior vs Posterior Approach in THA", year=2018)
    b = _cand(
        id="b",
        title="Anterior vs Posterior Approach in THA",
        year=2024,
    )
    assert find_duplicates([a, b]) == []


def test_find_duplicates_doi_takes_precedence_over_fuzzy():
    a = _cand(id="a", title="Total Hip A", year=2023, doi="10.1/x")
    b = _cand(id="b", title="Total Hip A", year=2023, doi="10.1/x")
    [grp] = find_duplicates([a, b])
    assert grp.reason == "doi_exact"


def test_find_duplicates_transitive_fuzzy_via_union_find():
    base = "Anterior versus posterior approach in total hip arthroplasty"
    a = _cand(id="a", title=base, year=2023)
    b = _cand(id="b", title=base + " — single centre", year=2023)
    c = _cand(id="c", title=base + " (sub-study)", year=2024)
    grps = find_duplicates([a, b, c])
    # Union-find collapses A~B and B~C into a single group of 3
    assert len(grps) == 1
    assert set(grps[0].candidate_ids) == {"a", "b", "c"}


def test_find_duplicates_no_duplicates_returns_empty():
    a = _cand(id="a", title="Foo bar baz", year=2020)
    b = _cand(id="b", title="Quux quack qaz", year=2020)
    assert find_duplicates([a, b]) == []


def test_find_duplicates_handles_missing_title_falls_through_to_doi():
    a = _cand(id="a", title="", doi="10.1/x")
    b = _cand(id="b", title="", doi="10.1/x")
    [grp] = find_duplicates([a, b])
    assert grp.reason == "doi_exact"


def test_find_duplicates_deterministic_ordering():
    # First arg is the oldest → keep_candidate_id is "a"
    a = _cand(id="a", title="X", doi="10.1/x")
    b = _cand(id="b", title="Y", doi="10.1/x")
    c = _cand(id="c", title="Z", doi="10.1/y")
    d = _cand(id="d", title="W", doi="10.1/y")
    grps = find_duplicates([a, b, c, d])
    assert [g.keep_candidate_id for g in grps] == ["a", "c"]


def test_find_duplicates_year_tolerance_one_matches():
    a = _cand(id="a", title="Anterior vs Posterior in THA", year=2022)
    b = _cand(id="b", title="Anterior vs. posterior in THA", year=2023)
    [grp] = find_duplicates([a, b])
    assert grp.reason == "title_fuzzy"


def test_find_duplicates_returns_empty_for_empty_input():
    assert find_duplicates([]) == []
