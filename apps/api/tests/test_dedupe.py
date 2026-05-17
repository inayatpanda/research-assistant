from dataclasses import dataclass

from research_api.services.dedupe import is_duplicate, score_match


@dataclass
class Stub:
    title: str | None = None
    doi: str | None = None


def test_doi_exact_match_is_one():
    a = Stub(doi="10.1234/foo")
    b = Stub(doi="10.1234/foo")
    assert score_match(a, b) == 1.0


def test_doi_match_case_insensitive():
    a = Stub(doi="10.1234/Foo")
    b = Stub(doi="10.1234/foo")
    assert score_match(a, b) == 1.0


def test_different_dois_falls_through_to_title():
    a = Stub(title="Anterior approach in hip", doi="10.1/a")
    b = Stub(title="anterior approach in hip", doi="10.1/b")
    s = score_match(a, b)
    assert s >= 0.9


def test_high_title_similarity_above_threshold():
    a = Stub(title="Anterior approach in total hip arthroplasty")
    b = Stub(title="anterior approach in TOTAL hip arthroplasty")
    assert is_duplicate(a, b)


def test_unrelated_titles_below_threshold():
    a = Stub(title="Anterior approach in total hip arthroplasty")
    b = Stub(title="Bone healing in pediatric tibial fractures")
    assert not is_duplicate(a, b)
    assert score_match(a, b) < 0.5


def test_missing_titles_score_zero():
    a = Stub(title=None)
    b = Stub(title="Anything")
    assert score_match(a, b) == 0.0


def test_punctuation_invariance():
    a = Stub(title="Outcomes: a 5-year follow-up.")
    b = Stub(title="outcomes a 5 year follow up")
    assert is_duplicate(a, b)
