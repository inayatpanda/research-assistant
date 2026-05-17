from dataclasses import dataclass

from research_api.services.citation_format import (
    extract_used_citations,
    format_inline,
    replace_cite_tokens,
    tag_for_index,
    vancouver_inline,
)


@dataclass
class A:
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    journal: str | None = None
    doi: str | None = None

    def __post_init__(self) -> None:
        if self.authors is None:
            self.authors = []


def test_vancouver_one_author():
    assert vancouver_inline(A(authors=["John Doe"], year=2024)) == "Doe, 2024"


def test_vancouver_two_authors():
    assert vancouver_inline(A(authors=["John Doe", "Jane Smith"], year=2024)) == "Doe & Smith, 2024"


def test_vancouver_three_plus_authors():
    assert vancouver_inline(A(authors=["A B", "C D", "E F"], year=2024)) == "B et al., 2024"


def test_vancouver_no_year_uses_nd():
    assert vancouver_inline(A(authors=["John Doe"], year=None)) == "Doe, n.d."


def test_vancouver_no_authors():
    assert vancouver_inline(A(authors=[], year=2024)) == "Unknown source, 2024"
    assert vancouver_inline(A(authors=[], year=None)) == "Unknown source"


def test_format_inline_dispatches_on_style():
    a = A(authors=["John Doe"], year=2024)
    assert format_inline("vancouver", a) == "Doe, 2024"
    assert format_inline("apa", a) == "Doe, 2024"
    assert format_inline("harvard", a) == "Doe, 2024"


def test_tag_for_index_is_stable():
    assert tag_for_index(1) == "a1"
    assert tag_for_index(7) == "a7"


def test_replace_cite_tokens_substitutes_known_tags():
    text = "Anterior was faster [CITE_a1] and easier [CITE_a2]."
    a1 = A(authors=["Doe"], year=2024)
    a2 = A(authors=["Smith", "Lee"], year=2023)
    out = replace_cite_tokens(text, {"a1": a1, "a2": a2}, style="vancouver")
    assert out == "Anterior was faster (Doe, 2024) and easier (Smith & Lee, 2023)."


def test_replace_cite_tokens_leaves_unknown_untouched():
    """Hallucinated tags must stay visible so reviewers spot them."""
    text = "Real ref [CITE_a1]. Made-up ref [CITE_x99]."
    out = replace_cite_tokens(text, {"a1": A(authors=["Doe"], year=2024)})
    assert "(Doe, 2024)" in out
    assert "[CITE_x99]" in out  # left visible


def test_extract_used_citations_distinct_ordered():
    text = "Foo [CITE_a1] bar [CITE_a2] baz [CITE_a1]."
    a1 = A(authors=["Doe"], year=2024)
    a2 = A(authors=["Smith"], year=2023)
    used = extract_used_citations(text, {"a1": a1, "a2": a2})
    assert used == ["Doe, 2024", "Smith, 2023"]
