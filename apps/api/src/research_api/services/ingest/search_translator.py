"""Best-effort cross-database search query translator (Phase 19 / MP19).

Translates a PubMed-flavoured query into Embase / Cochrane / Web of
Science syntax. Returns the translated string AND a list of warnings
listing fragments that couldn't be cleanly mapped — the user is expected
to review-before-running.

The translator is intentionally conservative: anything it doesn't
understand passes through verbatim with a warning, rather than silently
re-interpreting the fragment. The transformations focus on the most
common PubMed surface forms:

- ``"…"[MeSH Major Topic]`` / ``[Mesh:noexp]``       (MeSH Major Topic)
- ``"…"[MeSH Terms]`` / ``[MH]`` / ``[Mesh]``        (MeSH Terms)
- ``"…"[Title/Abstract]`` / ``[tiab]``               (free text)
- ``"…"[Title]`` / ``[ti]``                          (title only)
- ``[tw]``                                           (text word)
- Boolean operators ``AND`` / ``OR`` / ``NOT``       (passthrough)
- Proximity ``NEAR/n`` (Embase/Cochrane/WoS-only — flagged unsupported on PubMed input)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


TranslationTarget = Literal["embase", "cochrane", "wos"]


@dataclass(frozen=True)
class TranslationResult:
    translated_query: str
    warnings: list[str]


# Pattern matches `"term"[tag]` or `term[tag]` where the tag is one of
# the supported PubMed qualifiers. The tag itself is case-insensitive.
_TAGGED = re.compile(
    r"""
    (?:
        "(?P<phrase>[^"]+)"
        |
        (?P<word>[A-Za-z][\w\-\.\']*)
    )
    \s*
    \[\s*(?P<tag>[A-Za-z\s/:]+?)\s*\]
    """,
    flags=re.VERBOSE,
)


def _norm_tag(tag: str) -> str:
    return tag.strip().lower().replace(" ", "").replace("/", "")


def _mesh_terms(term: str, *, target: TranslationTarget) -> str:
    if target == "embase":
        return f"'{term}'/de"
    if target == "cochrane":
        return f"MeSH descriptor: [{term}]"
    if target == "wos":
        return f"TS=(\"{term}\")"
    return term


def _mesh_major(term: str, *, target: TranslationTarget) -> str:
    if target == "embase":
        return f"'{term}'/exp"
    if target == "cochrane":
        return f"MeSH descriptor: [{term}] this term only"
    if target == "wos":
        return f"TS=(\"{term}\")"
    return term


def _title_abstract(term: str, *, target: TranslationTarget) -> str:
    if target == "embase":
        return f"'{term}':ab,ti"
    if target == "cochrane":
        return f"({term}):ti,ab"
    if target == "wos":
        return f"TS=(\"{term}\")"
    return term


def _title_only(term: str, *, target: TranslationTarget) -> str:
    if target == "embase":
        return f"'{term}':ti"
    if target == "cochrane":
        return f"({term}):ti"
    if target == "wos":
        return f"TI=(\"{term}\")"
    return term


def _text_word(term: str, *, target: TranslationTarget) -> str:
    if target == "embase":
        return f"'{term}'"
    if target == "cochrane":
        return f"({term})"
    if target == "wos":
        return f"TS=(\"{term}\")"
    return term


_HANDLERS = {
    "meshmajortopic": _mesh_major,
    "meshmajor": _mesh_major,
    "majr": _mesh_major,
    "meshnoexp": _mesh_major,
    "meshterms": _mesh_terms,
    "mesh": _mesh_terms,
    "mh": _mesh_terms,
    "titleabstract": _title_abstract,
    "tiab": _title_abstract,
    "title": _title_only,
    "ti": _title_only,
    "tw": _text_word,
    "textword": _text_word,
}


# Unsupported but recognised tags that we want to drop with a warning
# rather than mangle.
_DROP_WITH_WARNING = {
    "dp", "pdat", "pt", "publicationtype", "lang", "language",
    "au", "author", "fau", "ad", "affiliation", "jn", "journal",
}


def translate(
    query: str,
    *,
    source: str = "pubmed",
    target: TranslationTarget,
) -> TranslationResult:
    """Best-effort PubMed → target translator.

    Returns a ``TranslationResult`` carrying the translated query and a
    list of warnings describing untranslatable fragments. ``source`` is
    accepted for forward-compatibility but only PubMed is supported in
    v1 (any other value yields a warning).
    """
    warnings: list[str] = []
    src = (source or "pubmed").lower()
    if src != "pubmed":
        warnings.append(
            f"Source '{source}' is not supported as a translation origin; "
            "treating as PubMed."
        )
    text = query or ""

    # PubMed has no proximity operator; if user typed one anyway, flag.
    if "NEAR/" in text.upper():
        warnings.append(
            "PubMed does not support proximity (NEAR/n). Translation left "
            "the operator in place but it will not behave identically in "
            f"{target}."
        )

    def repl(match: re.Match) -> str:
        term = match.group("phrase") or match.group("word") or ""
        tag = _norm_tag(match.group("tag"))
        handler = _HANDLERS.get(tag)
        if handler is None:
            if tag in _DROP_WITH_WARNING:
                warnings.append(
                    f"Tag [{match.group('tag')}] dropped — no equivalent in {target}."
                )
                return term
            warnings.append(
                f"Unknown tag [{match.group('tag')}] on '{term}' — left unchanged."
            )
            return match.group(0)
        return handler(term, target=target)

    translated = _TAGGED.sub(repl, text)

    # Final pass: AND/OR/NOT are universal but WoS prefers ' AND '/' OR '/' NOT '
    # exact-cased; Cochrane is the same. Nothing to do.

    return TranslationResult(
        translated_query=translated, warnings=warnings,
    )


__all__ = ["TranslationResult", "TranslationTarget", "translate"]
