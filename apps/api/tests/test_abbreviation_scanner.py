from research_api.services.abbreviation_scanner import scan_abbreviations


def test_extracts_simple_pair():
    text = "We measured the Harris Hip Score (HHS) at six weeks."
    assert scan_abbreviations(text) == [("HHS", "Harris Hip Score")]


def test_ignores_unrelated_parentheticals():
    text = "Patients (n=412) were enrolled."
    assert scan_abbreviations(text) == []


def test_deduplicates():
    """First occurrence wins for the long_form — preserved verbatim."""
    text = "Total hip arthroplasty (THA) and total hip arthroplasty (THA) again."
    assert scan_abbreviations(text) == [("THA", "Total hip arthroplasty")]


def test_multi_word_acronym_with_plural_s():
    text = "Patient reported outcome measures (PROMs) were used."
    out = scan_abbreviations(text)
    assert ("PROMs", "Patient reported outcome measures") in out


def test_empty_input():
    assert scan_abbreviations("") == []


def test_rejects_mismatched_initials():
    text = "The quick brown fox (XYZ) jumps."
    assert scan_abbreviations(text) == []


def test_multiple_abbreviations():
    text = "Total hip arthroplasty (THA) and Harris Hip Score (HHS) were tracked."
    out = scan_abbreviations(text)
    pairs = dict(out)
    assert pairs["THA"] == "Total hip arthroplasty"
    assert pairs["HHS"] == "Harris Hip Score"
