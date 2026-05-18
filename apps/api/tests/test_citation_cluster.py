"""Inline citation cluster consolidation (BUG #15).

`consolidate_inline_clusters(html, style)` walks adjacent `<sup data-citation>`
tokens (only whitespace between them counts as adjacent) and collapses them:

- Vancouver / IEEE (numeric inline): contiguous runs of 3+ → `[1-3]`;
  runs of 2 stay as `[1,2]`; non-contiguous merges (e.g. `[3][1][2]`) sort and
  apply the same rules.
- APA / Harvard (author-year inline): merge into a single `(Smith, 2024;
  Patel, 2022)` paren, dedup, preserving original adjacency order.

A cluster ends at the first non-whitespace, non-`<sup data-citation>` content.
"""
import pytest

from research_api.services.citation_format import consolidate_inline_clusters


def _sup_numeric(n: int) -> str:
    return f'<sup data-citation data-article-id="a{n}">[{n}]</sup>'


def _sup_authoryear(article_id: str, inner: str) -> str:
    return f'<sup data-citation data-article-id="{article_id}">({inner})</sup>'


# --- Vancouver / IEEE numeric -----------------------------------------------

@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_two_contiguous_numerics_collapse_to_comma(style):
    html = f"<p>foo {_sup_numeric(1)}{_sup_numeric(2)} bar</p>"
    out = consolidate_inline_clusters(html, style)
    assert "[1,2]" in out
    # Original separate sup tags removed.
    assert out.count("<sup data-citation") == 1


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_three_contiguous_numerics_collapse_to_range(style):
    html = f"<p>foo {_sup_numeric(1)}{_sup_numeric(2)}{_sup_numeric(3)} bar</p>"
    out = consolidate_inline_clusters(html, style)
    assert "[1-3]" in out
    assert out.count("<sup data-citation") == 1


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_whitespace_only_between_sups_still_counts_as_adjacent(style):
    html = f"<p>foo {_sup_numeric(1)} {_sup_numeric(2)}\n{_sup_numeric(3)} bar</p>"
    out = consolidate_inline_clusters(html, style)
    assert "[1-3]" in out


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_text_between_sups_breaks_cluster(style):
    """A sentence between clusters splits them into two separate clusters."""
    html = (
        f"<p>foo {_sup_numeric(1)}{_sup_numeric(2)} sentence "
        f"{_sup_numeric(3)}{_sup_numeric(4)} bar</p>"
    )
    out = consolidate_inline_clusters(html, "vancouver")
    assert "[1,2]" in out
    assert "[3,4]" in out


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_out_of_order_numerics_are_sorted(style):
    """[3][1][2] is contiguous after sort and renders [1-3]."""
    html = f"<p>{_sup_numeric(3)}{_sup_numeric(1)}{_sup_numeric(2)}</p>"
    out = consolidate_inline_clusters(html, style)
    assert "[1-3]" in out


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_non_contiguous_numerics_collapse_to_comma_list(style):
    """[1][3][5] should render [1,3,5] — no false range."""
    html = f"<p>{_sup_numeric(1)}{_sup_numeric(3)}{_sup_numeric(5)}</p>"
    out = consolidate_inline_clusters(html, style)
    assert "[1,3,5]" in out
    assert "[1-5]" not in out


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_mixed_contiguous_and_gap(style):
    """[1][2][3][5] should render [1-3,5]."""
    html = (
        f"<p>{_sup_numeric(1)}{_sup_numeric(2)}{_sup_numeric(3)}{_sup_numeric(5)}</p>"
    )
    out = consolidate_inline_clusters(html, style)
    assert "[1-3,5]" in out


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_single_sup_unchanged(style):
    html = f"<p>only {_sup_numeric(1)} here</p>"
    out = consolidate_inline_clusters(html, style)
    # Single tokens are not consolidated.
    assert _sup_numeric(1) in out


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_numeric_dedup_within_cluster(style):
    """Adjacent dup [1][1] dedupes to [1]."""
    html = f"<p>{_sup_numeric(1)}{_sup_numeric(1)}</p>"
    out = consolidate_inline_clusters(html, style)
    # After dedup only one number; renders as single sup.
    assert out.count("<sup data-citation") == 1


# --- APA / Harvard author-year ---------------------------------------------

@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_two_adjacent_merge_with_semicolon(style):
    html = (
        "<p>"
        + _sup_authoryear("a1", "Smith, 2024")
        + _sup_authoryear("a2", "Patel, 2022")
        + "</p>"
    )
    out = consolidate_inline_clusters(html, style)
    # Merged into single paren with semicolon separator.
    assert "(Smith, 2024; Patel, 2022)" in out
    # Only one sup remains (merged span).
    assert out.count("<sup data-citation") == 1


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_three_adjacent_merge(style):
    html = (
        "<p>"
        + _sup_authoryear("a1", "Smith, 2024")
        + _sup_authoryear("a2", "Patel, 2022")
        + _sup_authoryear("a3", "Brown, 2021")
        + "</p>"
    )
    out = consolidate_inline_clusters(html, style)
    assert "(Smith, 2024; Patel, 2022; Brown, 2021)" in out


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_dedup_within_cluster(style):
    """If the same author-year appears twice adjacently it should appear once."""
    html = (
        "<p>"
        + _sup_authoryear("a1", "Smith, 2024")
        + _sup_authoryear("a1", "Smith, 2024")
        + "</p>"
    )
    out = consolidate_inline_clusters(html, style)
    assert "(Smith, 2024)" in out
    # Only one (Smith, 2024) inside the merged paren.
    assert out.count("Smith, 2024") == 1


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_text_between_sups_does_not_merge(style):
    html = (
        "<p>"
        + _sup_authoryear("a1", "Smith, 2024")
        + " however "
        + _sup_authoryear("a2", "Patel, 2022")
        + "</p>"
    )
    out = consolidate_inline_clusters(html, style)
    # Both sups remain separate.
    assert out.count("<sup data-citation") == 2


def test_no_change_when_no_clusters():
    html = "<p>Plain prose with no citations.</p>"
    assert consolidate_inline_clusters(html, "vancouver") == html


def test_consolidator_idempotent():
    """Running twice yields the same result."""
    html = f"<p>{_sup_numeric(1)}{_sup_numeric(2)}{_sup_numeric(3)}</p>"
    once = consolidate_inline_clusters(html, "vancouver")
    twice = consolidate_inline_clusters(once, "vancouver")
    assert once == twice


def test_consolidator_preserves_surrounding_html():
    html = (
        f"<p>Before {_sup_numeric(1)}{_sup_numeric(2)} after.</p>"
        f"<p>Second paragraph.</p>"
    )
    out = consolidate_inline_clusters(html, "ieee")
    assert "Before " in out
    assert " after." in out
    assert "Second paragraph." in out
    assert "[1,2]" in out


def test_consolidator_handles_trailing_period():
    """Citation at end of sentence — the period stays outside the cluster."""
    html = f"<p>End of sentence {_sup_numeric(1)}{_sup_numeric(2)}.</p>"
    out = consolidate_inline_clusters(html, "vancouver")
    assert "[1,2]" in out
    assert ".</p>" in out
