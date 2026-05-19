"""Phase 19 (MP19) — Cross-database search translator."""
from __future__ import annotations

import pytest

from research_api.services.ingest.search_translator import translate


def test_mesh_terms_to_embase_de():
    res = translate('"hip arthroplasty"[MeSH Terms]', target="embase")
    assert "'hip arthroplasty'/de" in res.translated_query
    assert res.warnings == []


def test_mesh_terms_to_cochrane():
    res = translate('"hip arthroplasty"[MeSH Terms]', target="cochrane")
    assert "MeSH descriptor: [hip arthroplasty]" in res.translated_query
    assert "this term only" not in res.translated_query


def test_mesh_terms_to_wos():
    res = translate('"hip arthroplasty"[MeSH Terms]', target="wos")
    assert 'TS=("hip arthroplasty")' in res.translated_query


def test_mesh_major_topic_to_embase_exp():
    res = translate('"hip"[MeSH Major Topic]', target="embase")
    assert "'hip'/exp" in res.translated_query


def test_mesh_major_topic_to_cochrane_this_term_only():
    res = translate('"hip"[MeSH Major Topic]', target="cochrane")
    assert "MeSH descriptor: [hip] this term only" in res.translated_query


def test_title_abstract_to_embase_ab_ti():
    res = translate("anesthesia[tiab]", target="embase")
    assert "'anesthesia':ab,ti" in res.translated_query


def test_title_only_to_wos():
    res = translate("anesthesia[ti]", target="wos")
    assert 'TI=("anesthesia")' in res.translated_query


def test_boolean_operators_passthrough():
    res = translate(
        '"hip"[MeSH Terms] AND "anesthesia"[MeSH Terms] NOT "child"[MeSH Terms]',
        target="cochrane",
    )
    assert "AND" in res.translated_query
    assert "NOT" in res.translated_query


def test_compound_query_with_or():
    res = translate(
        '"hip"[MeSH Terms] OR "knee"[MeSH Terms]',
        target="embase",
    )
    assert "'hip'/de" in res.translated_query
    assert "'knee'/de" in res.translated_query
    assert "OR" in res.translated_query


def test_unsupported_tag_emits_warning_passthrough():
    res = translate('"hip"[FooBar]', target="embase")
    assert any("FooBar" in w for w in res.warnings)
    assert "[FooBar]" in res.translated_query


def test_dropped_tag_emits_warning_keeps_term():
    res = translate('"english"[lang]', target="cochrane")
    assert any("lang" in w for w in res.warnings)
    # Term stays even though tag is dropped
    assert "english" in res.translated_query


def test_proximity_operator_warning_on_pubmed_input():
    res = translate("hip NEAR/3 anesthesia", target="embase")
    assert any("proximity" in w.lower() or "NEAR" in w for w in res.warnings)


def test_invalid_source_emits_warning():
    res = translate('"hip"[MeSH Terms]', source="wos", target="embase")
    assert any("supported" in w.lower() for w in res.warnings)


def test_unquoted_word_with_tag_translates():
    res = translate("hip[MeSH]", target="cochrane")
    assert "MeSH descriptor: [hip]" in res.translated_query
